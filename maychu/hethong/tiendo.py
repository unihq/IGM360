"""Tiến độ 01 lần cập nhật theo 08 bước (QĐ249, QĐ251; CDA KT-QĐ249 phương án B). 0 bảng, 0 cột.

Bước: 1 kiểm ổ trống · 2 chụp 07 tệp · 3 bản sao Drive · 4 gửi lệnh · 5 tải gói · 6 khởi động bản mới · 7 nâng lược đồ ·
8 kiểm sau cập nhật. Bước 1–4 do bản đang chạy làm, 6–8 do bản mới làm. Bước 5 (watchtower kéo gói, thay vùng chứa) không
tiến trình IGM360 nào đo được (app không có quyền Docker): % bước 5–7 là ƯỚC TÍNH theo thời gian các lần trước.

- Tiến độ đang chạy: khoá phụ `tien_do` trong tệp trạng thái `capnhat_trangthai.json`, ghi qua `antoan.ghi` (khoá, ghi
  nguyên tử), nhịp ≤ 01 lần/giây; ghi lỗi thì bỏ qua, không chặn cập nhật. Bản cũ (0.7.9) đọc bằng `doc` + gộp nên giữ
  khoá lạ này.
- Lịch sử thời gian: hết mỗi lần cập nhật ghi 01 dòng F04 `capnhat` / `tiendo` (chỉ ghi thêm, có sao lưu, qua quay về nhờ
  QĐ237); trọng số các bước = trung bình 05 lần gần nhất; chưa có thì dùng số mặc định (ước lượng, chưa đo).
"""
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN

BUOC = ("o_trong", "chup", "drive", "gui", "tai", "khoidong", "nang", "kiem")
UOC_TINH = ("tai", "khoidong", "nang")   # bước 5–7: trang ghi rõ "ước tính"
# Thời gian mặc định mỗi bước (giây) khi chưa có lần đo nào: ước lượng, chưa đo
MAC_DINH_GIAY = {"o_trong": 1, "chup": 20, "drive": 0, "gui": 2, "tai": 300, "khoidong": 15, "nang": 30, "kiem": 40}
NHIP_GHI_GIAY = 1.0
SO_LAN_TB = 5
# Y41b N1 (CDA KT-Y41): lượt dài nhất hợp lệ ≈ Drive 10 phút + chờ việc AI 30 phút + watchtower 30 phút (QĐ252) + khởi động,
# nâng, kiểm vài phút ≈ 75 phút; lấy 02 giờ có dư. Lượt bắt đầu quá 02 giờ mà chưa xong = lượt treo: bản mới không nối lại;
# dòng F04 tổng quá 02 giờ không dùng tính trung bình.
TOI_DA_LUOT_GIAY = 2 * 3600
# Trần từng bước khi tính trung bình = giới hạn chờ cứng của chính bước + phần dư. Vượt trần là có chờ người, chờ việc khác
# hoặc lượt treo (N2: bước Drive gồm lúc chờ bạn chọn, bước gửi lệnh gồm lúc chờ việc AI), không phản ánh thời gian làm bước.
TRAN_GIAY = {"o_trong": 300, "chup": 1800, "drive": 10 * 60 + 60, "gui": 120, "tai_khoidong": 30 * 60 + 300, "nang": 1800, "kiem": 600}
_NHO = {"td": None, "ghi_luc": 0.0}
_KHOA = threading.Lock()
_log = logging.getLogger(__name__)


def _bay() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _giay(a: str | None, b: str | None) -> float | None:
    try:
        return max(0.0, (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds())
    except (TypeError, ValueError):
        return None


def _ghi(thumuc: Path | None, td: dict | None, bat_buoc: bool) -> None:
    """Ghi khoá `tien_do` (None = xoá). Không bắt buộc mà chưa đủ 01 giây từ lần ghi trước thì để lần sau."""
    from maychu.hethong import antoan
    with _KHOA:
        _NHO["td"] = td
        cach = time.monotonic() - _NHO["ghi_luc"]
        if cach < NHIP_GHI_GIAY:
            if not bat_buoc:
                return
            time.sleep(NHIP_GHI_GIAY - cach)
        try:
            antoan.ghi(thumuc, tien_do=td)
        except Exception as e:  # noqa: BLE001 - ghi tiến độ lỗi không chặn cập nhật
            _log.warning("không ghi được tiến độ cập nhật: %s", type(e).__name__)
        _NHO["ghi_luc"] = time.monotonic()


def doc(thumuc: Path | None = None) -> dict | None:
    from maychu.hethong import antoan
    td = antoan.doc(thumuc).get("tien_do")
    return td if isinstance(td, dict) else None


# ---------------- Ghi các mốc ----------------
def bat_dau(tu: str, den: str | None, luc_o_trong: str, thumuc: Path | None = None) -> None:
    """Bước 1 xong (ổ trống đủ), bắt đầu bước 2. `luc_o_trong`: lúc bắt đầu kiểm ổ trống."""
    td = {"tu": tu, "den": den, "bat_dau": luc_o_trong, "buoc": "chup", "moc": {"o_trong": luc_o_trong, "chup": _bay()},
          "chi_tiet": {}, "du_kien": trong_so(thumuc)}
    _ghi(thumuc, td, True)


def _hien_tai(thumuc: Path | None) -> dict | None:
    return _NHO["td"] if isinstance(_NHO["td"], dict) else doc(thumuc)


def sang(buoc: str, thumuc: Path | None = None, luc: str | None = None, **chi_tiet) -> None:
    """Sang bước `buoc` (ghi mốc bắt đầu, 01 lần)."""
    td = _hien_tai(thumuc)
    if not td or td.get("xong") or td.get("loi"):
        return
    td = dict(td)
    td["moc"] = {**td.get("moc", {})}
    td["moc"].setdefault(buoc, luc or _bay())
    td["buoc"] = buoc
    if chi_tiet:
        td["chi_tiet"] = {**td.get("chi_tiet", {}), buoc: chi_tiet}
    _ghi(thumuc, td, True)


def chi_tiet(buoc: str, thumuc: Path | None = None, **so) -> None:
    """Số đo thật trong bước (ví dụ tệp i/07, byte); ghi theo nhịp ≤ 01 lần/giây."""
    td = _hien_tai(thumuc)
    if not td or td.get("buoc") != buoc:
        return
    td = {**td, "chi_tiet": {**td.get("chi_tiet", {}), buoc: so}}
    _ghi(thumuc, td, bool(so.get("xong")))


def loi(lydo: str, thumuc: Path | None = None, chi_tiet: str | None = None) -> None:
    """Dừng ở bước đang chạy. `chi_tiet`: phần trong ngoặc của dòng "Dừng ở bước k/8: … chưa được (…)" (QĐ253)."""
    td = _hien_tai(thumuc)
    if td and not td.get("xong"):
        _ghi(thumuc, {**td, "loi": lydo[:120], "loi_luc": _bay(), **({"loi_ct": chi_tiet[:120]} if chi_tiet else {})}, True)


def huy(thumuc: Path | None = None) -> None:
    if _hien_tai(thumuc) is not None:
        _ghi(thumuc, None, True)


def dat(thumuc: Path | None = None, **muc) -> None:
    """Gộp thêm khoá vào tiến độ đang chạy (ví dụ `drive_noi`: thư mục bản chụp chờ đẩy Drive nền, QĐ258). Không hiện ra trang."""
    td = _hien_tai(thumuc)
    if td and not td.get("xong") and not td.get("loi"):
        _ghi(thumuc, {**td, **muc}, True)


def drive_nen(td: dict | None, thumuc: Path | None = None) -> dict | None:
    """QĐ258, QĐ261: bản chụp trước cập nhật đẩy Drive nền sau khi bản mới lên. Đọc hàng chờ cho_day_drive đúng thư mục bản
    chụp: số tệp đã lên, tổng, có lần đẩy lỗi chưa (đang chờ thử lại), số lần thử nhiều nhất. Không trả đường dẫn."""
    noi = (td or {}).get("drive_noi")
    if not noi:
        return None
    dau = os.path.join(str(noi), "")
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        tong, da, loi, lan, hen = cn.execute(
            "SELECT count(*), coalesce(sum(trangthai = 'xong'), 0), coalesce(sum(trangthai = 'loi'), 0),"
            " coalesce(max(CASE WHEN trangthai != 'xong' THEN so_lan_thu END), 0),"
            " min(CASE WHEN trangthai = 'loi' THEN lan_thu_ke END)"   # QĐ273: giờ hẹn đẩy lại sớm nhất (giờ Việt Nam)
            " FROM cho_day_drive WHERE substr(duongdan_tam, 1, ?) = ?", (len(dau), dau)).fetchone()
    finally:
        cn.close()
    return {"da": da, "tong": tong, "loi": bool(loi), "lan": lan or 0, "hen": hen}


def vao_ban_moi(ban: str, thumuc: Path | None = None) -> bool:
    """Bản mới khởi động (trước khi nâng lược đồ): lượt cập nhật đang chờ đúng bản này thì sang bước 7. Trả True khi có lượt.
    Mốc bước 6 do lệnh chạy `chay.py` ghi lúc vùng chứa bắt đầu; thiếu thì lấy lúc này."""
    try:
        td = doc(thumuc)
        if not td or td.get("xong") or td.get("loi") or td.get("den") != ban:
            return False
        if (_giay(td.get("bat_dau"), _bay()) or 0) > TOI_DA_LUOT_GIAY:   # N1: lượt treo cũ, không nối lại, không ghi F04
            huy(thumuc)
            return False
        _NHO["td"] = td
        if "khoidong" not in (td.get("moc") or {}):
            sang("khoidong", thumuc)
        sang("nang", thumuc)
        return True
    except Exception:  # noqa: BLE001 - tiến độ không chặn khởi động
        return False


def xong(ban: str | None = None, thumuc: Path | None = None) -> None:
    """Bước 8 xong: ghi mốc kết thúc và 01 dòng F04 tóm tắt thời gian từng bước (01 lần cho mỗi lượt).
    `ban`: chỉ kết thúc lượt cập nhật lên đúng bản này (lần kiểm không do cập nhật thì không đụng)."""
    td = _hien_tai(thumuc)
    if not td or td.get("xong") or td.get("loi") or (ban and td.get("den") not in (None, ban)):
        return
    td = {**td, "xong": _bay(), "buoc": "xong"}
    _ghi(thumuc, td, True)
    try:
        _ghi_f04(td, thumuc)
    except Exception as e:  # noqa: BLE001
        _log.warning("không ghi được dòng tóm tắt tiến độ: %s", type(e).__name__)


# ---------------- Thời gian từng bước, trọng số ----------------
def thoi_gian(td: dict) -> dict:
    """Số giây đo được của từng bước đã qua (bước 5 và 6 đo chung thành "tai_khoidong")."""
    moc = td.get("moc", {})
    thu_tu = [b for b in BUOC if b in moc] + (["xong"] if td.get("xong") else [])
    gio = {**moc, "xong": td.get("xong")}
    ra = {}
    for a, b in zip(thu_tu, thu_tu[1:]):
        g = _giay(gio[a], gio[b])
        if g is not None:
            ra[a] = round(g)
    if "tai" in ra or "khoidong" in ra:
        ra["tai_khoidong"] = ra.pop("tai", 0) + ra.pop("khoidong", 0)
    return ra


def _ghi_f04(td: dict, thumuc: Path | None) -> None:
    from maychu.hethong import capnhat
    tg = thoi_gian(td)
    if _da_co_f04(td["bat_dau"], thumuc):
        return
    # QĐ258 (PTD-13 nghiệm thu): chay_moi = giây từ lúc bấm tới lúc bản mới chạy (hết bước 7; kiểm 06 điểm chạy nền sau đó)
    moc = td.get("moc") or {}
    chay = _giay(td.get("bat_dau"), moc.get("kiem") or td.get("xong"))
    chu = (f"{td.get('tu')} → {td.get('den')} · " + " ".join(f"{k}={v}" for k, v in tg.items())
           + f" · tong={sum(tg.values())} giây" + (f" · chay_moi={round(chay)}" if chay is not None else "")
           + f" · bat_dau={td['bat_dau']}")
    capnhat._ghi_f04("tiendo", chu[:300], "dat", None, thumuc=thumuc)


def _da_co_f04(bat_dau: str, thumuc: Path | None) -> bool:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        return bool(cn.execute("SELECT 1 FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'tiendo'"
                               " AND instr(thamso_tomtat, ?) > 0", (f"bat_dau={bat_dau}",)).fetchone())
    finally:
        cn.close()


def trong_so(thumuc: Path | None = None) -> dict:
    """Thời gian dự kiến mỗi bước (giây): trung bình SO_LAN_TB dòng F04 `tiendo` gần nhất, bỏ lượt tổng quá
    TOI_DA_LUOT_GIAY và giá trị vượt TRAN_GIAY (Y41b N1); bước nào chưa có số thì lấy mặc định. "tai_khoidong" chia lại: bước 6 lấy mặc định (tối đa nửa), bước 5 phần còn lại."""
    du = dict(MAC_DINH_GIAY)
    try:
        cn = ketnoi.mo("Nhatky", thumuc)
        try:
            dong = [r[0] for r in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat'"
                                             " AND lenhcon = 'tiendo' ORDER BY luc DESC LIMIT ?", (SO_LAN_TB,))]
        finally:
            cn.close()
    except Exception:  # noqa: BLE001 - đọc lịch sử lỗi thì dùng mặc định
        dong = []
    gom: dict[str, list] = {}
    for d in dong:
        so = {k: int(v) for k, v in re.findall(r"(?:^|\s)([a-z_]+)=(\d+)(?=\s|$)", d or "")}
        if so.get("tong", 0) > TOI_DA_LUOT_GIAY:   # N1: lượt treo, bỏ cả dòng
            continue
        for k, v in so.items():
            if k != "tong" and v <= TRAN_GIAY.get(k, TOI_DA_LUOT_GIAY):   # N1: bỏ giá trị vượt trần của bước
                gom.setdefault(k, []).append(v)
    for k, ds in gom.items():
        tb = sum(ds) / len(ds)
        if k == "tai_khoidong":
            du["khoidong"] = min(MAC_DINH_GIAY["khoidong"], tb / 2)
            du["tai"] = tb - du["khoidong"]
        elif k in du:
            du[k] = tb
    return {k: round(v, 1) for k, v in du.items()}


def _drive_nen_an_toan(td: dict, thumuc: Path | None) -> dict | None:
    try:
        return drive_nen(td, thumuc)
    except Exception:  # noqa: BLE001 - đọc hàng chờ lỗi thì không hiện dòng Drive, không chặn thẻ
        return None


def hien(thumuc: Path | None = None, bay_gio: datetime | None = None) -> dict | None:
    """Cho trang: bước đang chạy (01–08), % tổng thể, có phải ước tính không. Bước có số đo (tệp i/n, điểm k/6, tệp chờ
    Drive) tính theo số đo; bước không đo được tính theo thời gian đã trôi / thời gian dự kiến (tối đa 95% của bước)."""
    td = doc(thumuc)
    if not td:
        return None
    du = {b: max(0.0, float((td.get("du_kien") or {}).get(b, MAC_DINH_GIAY[b]))) for b in BUOC}
    tong = sum(du.values()) or 1.0
    buoc = td.get("buoc")
    bay = (bay_gio or datetime.now(MUIGIO_VN)).isoformat(timespec="seconds")
    chung = {"moc": td.get("moc", {}), "du_kien": du, "tu": td.get("tu"), "den": td.get("den"), "bat_dau": td.get("bat_dau"),
             "luc": bay,   # luc: giờ máy chủ, trang tự tính % giữa 02 lần hỏi và lúc máy chủ đang thay bản (QĐ253)
             "drive": (td.get("chi_tiet") or {}).get("drive"),   # QĐ255 điểm 3: số tệp đã lên Drive / tổng, kể cả khi đã qua bước 3
             "drive_nen": _drive_nen_an_toan(td, thumuc),          # QĐ261: Drive đẩy nền sau khi lên bản (số sống từ hàng chờ)
             # QĐ255 điểm 2 (CDA N5-B): máy chủ là nguồn duy nhất của ngưỡng treo; trang chỉ đọc cờ này
             "treo": not td.get("xong") and (_giay(td.get("bat_dau"), bay) or 0) > TOI_DA_LUOT_GIAY}
    if td.get("xong"):
        return {"buoc": "xong", "so_buoc": len(BUOC), "phan_tram": 100, "uoc_tinh": False, "xong": td["xong"], **chung}
    vi_tri = BUOC.index(buoc) if buoc in BUOC else 0
    da = sum(du[b] for b in BUOC[:vi_tri])
    ct = (td.get("chi_tiet") or {}).get(buoc) or {}
    uoc = buoc in UOC_TINH
    if ct.get("tong"):
        phan = min(1.0, float(ct.get("da", 0)) / float(ct["tong"]))
    else:
        troi = _giay((td.get("moc") or {}).get(buoc), bay) or 0
        phan = min(0.95, troi / du[buoc]) if du[buoc] else 0.95
        uoc = True
    pt = int(100 * (da + phan * du[buoc]) / tong)
    return {"buoc": buoc, "so_buoc": vi_tri + 1, "phan_tram": max(0, min(99, pt)), "uoc_tinh": uoc, "chi_tiet": ct, **chung,
            **{k: td[k] for k in ("loi", "loi_ct", "loi_luc") if td.get(k)}}
