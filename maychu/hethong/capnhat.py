"""Ngăn Cập nhật (màn 09): bản đang chạy, bản mới nhất trên kho ảnh GHCR (công khai), nội dung thay đổi,
lệnh "Cập nhật ngay" gửi watchtower (chỉ nghe trong mạng nội bộ Docker), lịch sử ghi ở F04."""
import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN

ANH = os.environ.get("IGM360_IMAGE", "unihq/igm360")
KHO_MA = os.environ.get("IGM360_KHO_MA", "unihq/IGM360")
# QĐ174, QĐ175 (Y29): dò bản mới cố định 05 phút, không làm thông số (nguồn học cách làm: tailieu/Songuongoc.md).
# Nhịp chỉ viết ở 01 chỗ này; nơi khác đọc qua `nhip_kiem_giay()`.
NHIP_KIEM_GIAY = 5 * 60
_NHO = {"luc": 0.0, "luc_dat": 0.0, "ban_moi": None, "thaydoi": [], "tomtat": {}, "loi": None, "nhan_thaydoi": None}


def nhip_kiem_giay() -> int:
    return NHIP_KIEM_GIAY
_SO = re.compile(r"^\d+\.\d+\.\d+$")


def _khoa_so(b: str):
    return tuple(int(x) for x in b.split("."))


def ban_dang_chay() -> str:
    try:
        return (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


_KIEU_GOI = ", ".join(("application/vnd.oci.image.index.v1+json", "application/vnd.oci.image.manifest.v1+json",
                        "application/vnd.docker.distribution.manifest.list.v2+json",
                        "application/vnd.docker.distribution.manifest.v2+json"))


def _hoi_ghcr(dang: str | None = None) -> tuple[str | None, str | None]:
    """(bản mới nhất DÙNG ĐƯỢC, nhãn số lớn nhất trên kho). 02 lượt hỏi: khoá đọc ẩn danh + danh sách nhãn. Nhãn lớn
    hơn bản đang chạy thì hỏi thêm đúng nhãn đó (QĐ174 điểm 04): gói đóng xong (trả 200) mới tính là bản mới; đang đóng
    thì lùi về nhãn trước, lần sau hỏi lại."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        ve = c.get("https://ghcr.io/token", params={"scope": f"repository:{ANH}:pull"}).json()["token"]
        nhan = c.get(f"https://ghcr.io/v2/{ANH}/tags/list", headers={"Authorization": f"Bearer {ve}"}).json().get("tags") or []
        so = sorted((t for t in nhan if _SO.match(t)), key=_khoa_so)
        if not so:
            return None, None
        moi_hon = [t for t in so if dang is None or _khoa_so(t) > _khoa_so(dang)]
        for t in reversed(moi_hon[-2:]):   # tối đa 02 nhãn mới nhất
            r = c.head(f"https://ghcr.io/v2/{ANH}/manifests/{t}", headers={"Authorization": f"Bearer {ve}", "Accept": _KIEU_GOI})
            if r.status_code == 200:
                return t, so[-1]
        cu = [t for t in so if t not in moi_hon]
        return (cu[-1] if cu else None), so[-1]


def _tai_thaydoi_kq() -> tuple[list[dict], int]:
    """Đọc THAYDOI.md trên kho mã (tệp không nằm trong ảnh máy chủ). Trả (các mục, mã trả về)."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        r = c.get(f"https://raw.githubusercontent.com/{KHO_MA}/main/THAYDOI.md")
    return (phan_tich_thaydoi(r.text) if r.status_code == 200 else []), r.status_code


def _tai_thaydoi() -> list[dict]:
    return _tai_thaydoi_kq()[0]


def _doc_thaydoi(tu_ban: str, het: list[dict] | None = None) -> list[dict]:
    return [m for m in (_tai_thaydoi() if het is None else het) if _khoa_so(m["ban"]) > _khoa_so(tu_ban)]


def phan_tich_thaydoi(chu: str) -> list[dict]:
    """Mỗi bản 01 mục '## x.y.z'; dòng 'Tóm tắt: ...' là chữ ngắn cho lịch sử cập nhật (N07);
    các dòng '- ...' là nội dung có gì mới."""
    muc, ds = None, []
    for dong in chu.splitlines():
        m = re.match(r"^##\s+(\d+\.\d+\.\d+)", dong)
        if m:
            muc = {"ban": m.group(1), "tomtat": None, "dong": []}
            ds.append(muc)
        elif muc and dong.strip().startswith("Tóm tắt:"):
            muc["tomtat"] = dong.strip()[len("Tóm tắt:"):].strip() or None
        elif muc and dong.strip().startswith("- "):
            muc["dong"].append(dong.strip()[2:])
    return ds


def kiem_tra(bat_buoc: bool = False) -> dict:
    """Kết quả nhớ `nhip_kiem_giay()` (QĐ174: 05 phút); `bat_buoc` (nút Kiểm tra lại) thì hỏi ngay.
    Mỗi lần hỏi: 02 lượt ghcr.io; THAYDOI.md (raw.githubusercontent.com) chỉ tải khi kho có nhãn mới so với lần tải
    trước, hoặc lần trước tải chưa được. Kho từ chối, lỗi mạng: giữ kết quả cũ, không báo lỗi, lượt sau hỏi lại;
    chưa từng kiểm được lần nào thì mới báo."""
    bay = time.time()
    dang = ban_dang_chay()
    if bat_buoc or bay - _NHO["luc"] > nhip_kiem_giay():
        _NHO["luc"] = bay
        try:
            moi, nhan_lon = _hoi_ghcr(dang)
            _NHO["ban_moi"], _NHO["luc_dat"] = moi, bay
            _NHO["loi"] = None
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            nhan_lon = None
            if not _NHO["luc_dat"]:
                _NHO["loi"] = "Chưa kiểm được bản mới vì không kết nối được kho ảnh, anh bấm Kiểm tra lại sau"
        if nhan_lon and nhan_lon != _NHO["nhan_thaydoi"]:
            try:
                het, ma_tra = _tai_thaydoi_kq()
            except httpx.HTTPError:
                het, ma_tra = [], 0
            if ma_tra == 200:
                _NHO["thaydoi"] = _doc_thaydoi(dang, het)
                _NHO["tomtat"] = {m["ban"]: m["tomtat"] for m in het if m["tomtat"]}
                _NHO["nhan_thaydoi"] = nhan_lon
            elif not _NHO["tomtat"]:   # Y17 (e): chưa có nội dung cũ thì nói rõ; có rồi thì giữ, lượt sau tải lại
                _NHO["loi"] = f"Chưa tải được nội dung thay đổi (mã trả về {ma_tra}), số bản mới vẫn đúng"
    moi = _NHO["ban_moi"]
    return {"ban_dang": dang, "ban_moi": moi, "co_ban_moi": bool(moi and _khoa_so(moi) > _khoa_so(dang)),
            "luc_kiem": datetime.fromtimestamp(_NHO["luc_dat"], MUIGIO_VN).isoformat(timespec="seconds") if _NHO["luc_dat"] else None,
            "nhip_phut": nhip_kiem_giay() // 60,
            "thaydoi": _NHO["thaydoi"] if moi else [], "tomtat": _NHO["tomtat"], "loi": _NHO["loi"]}


def _ghi_f04(lenhcon: str, tomtat: str, ketqua: str, lydo: str | None = None, nguoi_id=None, thumuc=None) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua, lydo_chan)"
                   " VALUES (?, ?, ?, ?, 'capnhat', ?, ?, ?, ?)",
                   (maso.tao(), datetime.now(MUIGIO_VN).isoformat(timespec="seconds"), "anh" if nguoi_id else None,
                    nguoi_id, lenhcon, tomtat, ketqua, lydo))
    finally:
        cn.close()


def ghi_khoi_dong(thumuc=None) -> None:
    """Mỗi lần chạy bản khác bản lần trước thì ghi 01 dòng lịch sử cài."""
    ban = ban_dang_chay()
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cu = cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'khoidong'"
                        " ORDER BY luc DESC LIMIT 1").fetchone()
    finally:
        cn.close()
    if not cu or cu[0] != ban:
        _ghi_f04("khoidong", ban, "dat", thumuc=thumuc)


def lich_su(thumuc=None) -> list[dict]:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        dong = cn.execute("SELECT luc, thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'khoidong'"
                          " ORDER BY luc DESC LIMIT 20").fetchall()
        kiem = cn.execute("SELECT thamso_tomtat, ketqua FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'kiem_saunang'"
                          " ORDER BY luc").fetchall()
    finally:
        cn.close()
    # 0.7.9 lớp 4: mỗi bản lấy lượt kiểm sau cập nhật gần nhất ("0.7.9 · 06/06 đạt · chưa đạt: …")
    theo_ban = {k[0].split(" · ")[0]: {"chu": " · ".join(k[0].split(" · ")[1:]), "dat": k[1] == "dat"} for k in kiem if k[0]}
    da, ra = set(), []
    for d in dong:   # Y38d N39: quay về rồi lên lại thì F04 có 02 dòng khởi động cùng bản: giữ dòng mới nhất
        if d[1] not in da:
            da.add(d[1])
            ra.append({"ban": d[1], "luc": d[0], "kiem": theo_ban.get(d[1])})
    return ra


def so_viec_ai_dangchay(thumuc=None) -> int:
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        return cn.execute("SELECT count(*) FROM viecnen WHERE trangthai = 'dangchay' AND goi_ai = 1").fetchone()[0]
    finally:
        cn.close()


_CHO = {"tu": 0.0, "nguoi": None}
CHO_TOIDA_GIAY = 30 * 60


def yeu_cau(nguoi_id: str, che_do: str, thumuc=None, van_capnhat: bool = False) -> dict:
    """che_do 'ngay': gửi lệnh luôn. 'cho': không có việc AI đang chạy thì gửi luôn; có thì chờ việc xong,
    tối đa 30 phút (lịch chạy nền gọi xu_ly_cho mỗi phút). Việc mới không nhận khi đang chờ: dang_cho().
    0.7.9 (QĐ213): lớp 1 ổ trống không đủ thì chặn; "gửi lệnh" = lớp 5 chụp bản sao, đẩy Drive rồi mới gửi."""
    from maychu.hethong import antoan
    kq = kiem_tra()
    if not kq["co_ban_moi"]:   # QĐ174 điểm 04: chỉ cập nhật khi gói bản mới đã đóng xong trên kho
        return {"loi": "Chưa có bản mới đóng gói xong, anh chờ vài phút rồi bấm Kiểm tra lại"}
    o = antoan.o_trong(thumuc)
    if not o["du"]:
        _ghi_f04("chan_otrong", f"còn {antoan.chu_dungluong(o['trong'])}, cần {antoan.chu_dungluong(o['can'])}",
                 "bichan", None, nguoi_id, thumuc)
        return {"loi": o["chu"] + " " + antoan.CHU["o_thieu_lam"], "o_trong": o}
    from maychu.ketnoi import drive
    if not van_capnhat and not drive.dang_noi(thumuc):   # QĐ218 dòng 30, 31: Drive chưa nối thì anh chọn trước
        return {"loi": antoan.CHU["drive_chua_noi"], "can_chon": "drive_chua_noi"}
    # Y38c R4: chụp bản sao, đẩy Drive TRƯỚC; chế độ "cho" chờ việc AI xong (tối đa 30 phút) ngay trước khi gửi lệnh,
    # nên việc AI bắt đầu trong lúc chụp vẫn được chờ. Từ lúc bấm tới lúc gửi lệnh, dang_cho() = True để không nhận việc mới.
    return bat_dau(nguoi_id, kq["ban_moi"], thumuc, cho_viec=che_do == "cho")


def dang_cho() -> bool:
    """Đang chuẩn bị cập nhật (chụp, đẩy Drive, chờ việc AI, gửi lệnh): nơi nhận việc AI nền mới hỏi hàm này
    (bộ chạy việc nền chưa có ở GĐ 1: chưa chỗ nào đặt `dangchay`)."""
    return bool(_CHO["tu"]) or _SAO["buoc"] in ("chup", "day", "qua_gio", "cho_viec", "gui")


def xu_ly_cho(thumuc=None) -> None:
    if _CHO["tu"] and (not so_viec_ai_dangchay(thumuc) or time.time() - _CHO["tu"] > CHO_TOIDA_GIAY):
        nguoi = _CHO["nguoi"]
        _CHO.update(tu=0.0, nguoi=None)
        bat_dau(nguoi, kiem_tra()["ban_moi"], thumuc)


# ---------------- 0.7.9 lớp 5: bản sao Drive trước khi gửi lệnh ----------------
_SAO = {"buoc": None, "tu": 0.0, "loi": None, "den": None, "nguoi": None}   # buoc: chup, day, qua_gio, gui
_KHOA_SAO = threading.Lock()


def _chay_nen(viec) -> None:
    threading.Thread(target=viec, daemon=True, name="igm360-truoc-capnhat").start()


def trang_thai_sao() -> dict:
    return {"dang_sao": _SAO["buoc"], "sao_loi": _SAO["loi"], "sao_den": _SAO["den"]}


def tiep_tuc(nguoi_id: str, van: bool, thumuc=None) -> dict:
    """QĐ218 dòng 28, 32, 34: bản sao quá 10 phút chưa lên Drive thì chờ anh chọn Huỷ hay Vẫn cập nhật."""
    if _SAO["buoc"] != "qua_gio":
        return {"loi": "Không có lượt cập nhật nào đang chờ chọn"}
    if not van:
        _SAO.update(buoc=None, loi=None)
        _ghi_f04("capnhat_ngay", ban_dang_chay(), "bichan", "anh huỷ: bản sao Drive quá 10 phút", nguoi_id, thumuc)
        return {"ok": True, "huy": True}
    _SAO["buoc"] = "gui"
    _chay_nen(lambda: _gui(nguoi_id, _SAO["den"], False, thumuc))
    return {"ok": True}


def _gui(nguoi_id: str, ban_moi: str | None, len_drive: bool, thumuc=None) -> None:
    from maychu.hethong import antoan
    if _SAO.get("cho_viec"):   # Y38c R4: chế độ "Chờ xong rồi cập nhật"
        _SAO["buoc"] = "cho_viec"
        het = time.time() + CHO_TOIDA_GIAY
        while so_viec_ai_dangchay(thumuc) and time.time() < het:
            time.sleep(NGHI_DAY_GIAY)
        _SAO["buoc"] = "gui"
    try:
        antoan.ghi(thumuc, yeu_cau={"tu": ban_dang_chay(), "den": ban_moi, "luc": datetime.now(MUIGIO_VN).isoformat(timespec="seconds"),
                                    "drive": len_drive})
        r = cap_nhat_ngay(nguoi_id, thumuc)
        if "loi" in r:
            _SAO.update(loi=r["loi"])
    finally:
        _SAO.update(buoc="tai" if not _SAO["loi"] else None)


def bat_dau(nguoi_id: str, ban_moi: str | None, thumuc=None, cho_viec: bool = False) -> dict:
    """Chụp bản sao 07 tệp vào thư mục riêng, chờ đẩy lên Drive (tối đa CHO_DRIVE_GIAY), rồi gửi lệnh. Chạy nền vì
    đẩy Drive có thể vài phút; giao diện hỏi lại /api/capnhat để biết bước đang chạy."""
    with _KHOA_SAO:
        if _SAO["buoc"] in ("chup", "day", "qua_gio", "cho_viec", "gui"):
            return {"ok": True, "sao": True}
        _SAO.update(buoc="chup", tu=time.time(), loi=None, den=ban_moi, cho_viec=cho_viec)
    _chay_nen(lambda: _sao_roi_gui(nguoi_id, ban_moi, thumuc))
    return {"ok": True, "sao": True}


def _con_cho_drive(noi: Path, thumuc=None) -> int:
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        dau = os.path.join(str(noi), "")   # Y38c R2: đúng thư mục này (có dấu ngăn cuối), không lẫn thư mục khác
        return cn.execute("SELECT count(*) FROM cho_day_drive WHERE substr(duongdan_tam, 1, ?) = ? AND trangthai != 'xong'",
                          (len(dau), dau)).fetchone()[0]
    finally:
        cn.close()


def _sao_roi_gui(nguoi_id: str, ban_moi: str | None, thumuc=None) -> None:
    from maychu.dulieu import saoluu
    from maychu.hethong import antoan
    from maychu.ketnoi import drive
    dang = ban_dang_chay()
    try:
        kq = saoluu.chay(thumuc, truoc_ban=ban_moi or "moi")
        if kq["ketqua"] == "loi":
            loi = next((x for x in kq["file"] if x["ketqua"] == "loi"), {})
            lydo = (json.loads(loi.get("ketqua_tungbuoc_json") or "{}").get("loi") or "lỗi chụp")[:200]
            _SAO.update(loi=antoan.CHU["sao_loi"].format(lydo=lydo), buoc=None)
            _ghi_f04("capnhat_ngay", dang, "bichan", "chưa chụp được bản sao: " + lydo, nguoi_id, thumuc)
            return
        if drive.dang_noi(thumuc):
            _SAO["buoc"] = "day"
            het = time.time() + antoan.CHO_DRIVE_GIAY
            while _con_cho_drive(kq["noi"], thumuc) and time.time() < het:
                drive.day_hang_cho(thumuc)
                if _con_cho_drive(kq["noi"], thumuc):
                    time.sleep(NGHI_DAY_GIAY)
            if _con_cho_drive(kq["noi"], thumuc):   # QĐ218 dòng 28: quá 10 phút thì chờ anh chọn (tiep_tuc)
                _SAO["buoc"] = "qua_gio"
                return
        _SAO["buoc"] = "gui"
        _gui(nguoi_id, ban_moi, drive.dang_noi(thumuc), thumuc)
    except Exception as e:  # noqa: BLE001 - mọi lỗi đều báo lại, không gửi lệnh khi chưa có bản sao
        _SAO.update(loi=antoan.CHU["sao_loi"].format(lydo=type(e).__name__), buoc=None)
        _ghi_f04("capnhat_ngay", dang, "loi", "trước cập nhật: " + type(e).__name__, nguoi_id, thumuc)


NGHI_DAY_GIAY = 15


def cap_nhat_ngay(nguoi_id: str, thumuc=None) -> dict:
    ma = os.environ.get("WATCHTOWER_TOKEN", "")
    if not ma:
        return {"loi": "Máy chủ chưa có mã cập nhật"}
    try:
        httpx.post("http://watchtower:8080/v1/update", headers={"Authorization": f"Bearer {ma}"}, timeout=5)
    except httpx.TimeoutException:
        pass  # watchtower đang kéo bản mới và khởi động lại phần mềm: bình thường
    except httpx.HTTPError as loi:
        _ghi_f04("capnhat_ngay", ban_dang_chay(), "loi", type(loi).__name__, nguoi_id, thumuc)
        return {"loi": "Chưa gửi được lệnh cập nhật"}
    _ghi_f04("capnhat_ngay", ban_dang_chay(), "dat", None, nguoi_id, thumuc)
    return {"ok": True}
