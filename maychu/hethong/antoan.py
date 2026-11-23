"""05 lớp an toàn khi cập nhật (QĐ163, QĐ202, QĐ213; kế hoạch Y38a `Kehoach_Capnhat_Antoan.md`).

Lớp 1  ổ trống trước khi cập nhật: `o_trong()`.
Lớp 2  chế độ an toàn khi nâng dữ liệu không thành hoặc lần nâng trước bị ngắt: `vao_an_toan()`, cờ ở tệp trạng thái.
Lớp 4  kiểm sau cập nhật: `kiem_sau_capnhat()`, 06 điểm, ghi F04 `capnhat` / `kiem_saunang`.
Lớp 5  bản sao Drive trước khi cập nhật: `capnhat.yeu_cau` gọi `saoluu.chay` vào thư mục riêng (xem capnhat.py).
Lớp 3  quay về bản trước (QĐ215, cách 2): mã bản liền trước để sẵn trong ảnh ở `/app/ban_truoc`; `quay_ve()` ghi cờ
       rồi tự dừng, Docker bật lại, `maychu.chay` chạy bản trước. Không khoá mới, không cần mạng, lùi đúng 01 bản.

0 bảng, 0 cột: trạng thái cập nhật nằm ở 01 tệp `capnhat_trangthai.json` trên ổ dữ liệu (không có dữ liệu cá nhân,
không có mã). Ngưỡng và chữ hiện viết ở 01 chỗ này (như nhịp 05 phút QĐ174), không phải thông số.
Nguồn học cách làm: tailieu/Songuongoc.md (mục 0.7.9).
"""
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN

# ---- Ngưỡng (01 chỗ) ----
HE_SO_DULIEU = 3                  # bản chụp trước khi nâng + bản sao + bản mã hoá (học kiemtruoc_ban3: ≥ 03 lần)
DU_PHONG_BYTE = 2 * 1024 ** 3     # chỗ cho 01 ảnh mới giải nén (ảnh 0.7.7 nén 461,8 MB; cỡ giải nén chưa đo)
CHO_DRIVE_GIAY = 10 * 60          # chờ bản sao đẩy lên Drive tối đa 10 phút rồi mới gửi lệnh cập nhật
GIU_BAN_TRUOC = 2                 # giữ bản sao trước cập nhật của 02 lần gần nhất trên máy

# ---- Chữ hiện cho anh (01 chỗ). Anh duyệt nguyên văn: QĐ218 (bảng Z16 dòng 24–47); số dòng ghi cuối mỗi câu ----
CHU = {
    "o_du": "Ổ trống {trong} · đủ để cập nhật",                                                                  # 24
    "o_thieu": "Ổ trống còn {trong}, cần {can} để cập nhật an toàn.",                                           # 25
    "o_thieu_lam": "Dọn ổ máy chủ rồi bấm Kiểm tra lại.",                                                        # 25
    "an_toan": "Chế độ an toàn: bản {den} nâng dữ liệu chưa được, dữ liệu đã trả về như trước lúc {luc}.",        # 35
    "an_toan_chan": "Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.",                             # 37
    "sao_loi": "Chưa chụp được bản sao trước khi cập nhật: {lydo}",          # câu báo lỗi kỹ thuật, ngoài bảng QĐ218
    "drive_chua_noi": "Drive chưa kết nối. Bản sao chỉ nằm trên máy chủ.",                                        # 31
    "drive_qua_gio": "Đẩy bản sao lên Drive đã quá 10 phút. Bản sao chỉ nằm trên máy chủ.",                        # 32
    "qv_khong_co": "Ảnh này chưa có bản trước để quay về",                   # ngoài bảng: nút không hiện khi không có bản trước
    "qv_mat": "Bản đang dùng đã nâng dữ liệu khi cập nhật. Quay về thì dữ liệu trả về lúc {luc} (trước khi cập nhật); "
              "việc nhập sau lúc đó không giữ được.",                                                             # 40
    "qv_giu": "Lần cập nhật này không nâng dữ liệu: dữ liệu giữ nguyên.",                                         # 41
    "qv_an_toan": "Dữ liệu đã trả về lúc {luc}, quay về không mất thêm.",                                         # 42
    "qv_can_dong_y": "Lần cập nhật này có nâng dữ liệu: anh xác nhận chấp nhận mất dữ liệu nhập sau giờ cập nhật",
}
# Lý do chưa đạt của từng điểm kiểm sau cập nhật (QĐ218 dòng 46, 47: "05/06 · lịch chạy nền chưa bật")
TEN_DIEM = {"ban": "chưa đúng bản đích", "dulieu": "tệp dữ liệu chưa đạt kiểm tra", "luocdo": "lược đồ chưa đúng",
            "lich": "lịch chạy nền chưa bật", "cli": "công cụ AI chưa chạy được", "o_trong": "ổ trống chưa đủ"}

TEN_TEP = "capnhat_trangthai.json"
CHE_DO = {"an_toan": False, "den": None, "luc": None, "lydo": None}   # trạng thái của lần chạy này (bộ nhớ)


# ---------------- Tệp trạng thái ----------------
def _tep(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / TEN_TEP


def doc(thumuc: Path | None = None) -> dict:
    try:
        d = json.loads(_tep(thumuc).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi(thumuc: Path | None = None, **muc) -> dict:
    """Gộp các mục vào tệp trạng thái (giá trị None = bỏ mục); ghi nguyên tử, quyền 600."""
    d = doc(thumuc)
    for k, v in muc.items():
        d.pop(k, None) if v is None else d.__setitem__(k, v)
    p = _tep(thumuc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + ".tam")
    fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tam, p)
    return d


def _bay() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


# ---------------- Lớp 1: ổ trống ----------------
def chu_dungluong(so_byte: float) -> str:
    gb = so_byte / 1024 ** 3
    if gb >= 1:
        return f"{gb:.1f}".replace(".", ",").replace(",0", "") + " GB"
    return f"{round(so_byte / 1024 ** 2)} MB"


def o_trong(thumuc: Path | None = None) -> dict:
    """{du, trong, can, dulieu} (byte). Ổ dữ liệu trên VPS cài chuẩn dùng chung ổ với kho ảnh Docker (chưa xác minh)."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    dulieu = 0
    for ten in ketnoi.CAC_FILE:
        for duoi in ("", "-wal"):
            p = ketnoi.duongdan(ten, thumuc).with_name(f"{ten}.sqlite3{duoi}")
            if p.exists():
                dulieu += p.stat().st_size
    trong = shutil.disk_usage(thumuc).free
    can = HE_SO_DULIEU * dulieu + DU_PHONG_BYTE
    return {"du": trong >= can, "trong": trong, "can": can, "dulieu": dulieu,
            "chu": CHU["o_du"].format(trong=chu_dungluong(trong)) if trong >= can
            else CHU["o_thieu"].format(trong=chu_dungluong(trong), can=chu_dungluong(can))}


# ---------------- Lớp 2: chế độ an toàn ----------------
def vao_an_toan(loi: BaseException, thumuc: Path | None = None) -> None:
    """Nâng dữ liệu không thành (khoitao đã trả nguyên trạng): chạy hạn chế thay vì khởi động lại mãi."""
    from maychu.dulieu import khoitao
    from maychu.hethong import capnhat
    from maychu.hethong.kekhoa.che import che
    tt = doc(thumuc)
    luc = (tt.get("nang_xong_luc") or tt.get("dang_nang", {}).get("luc") or _bay())
    CHE_DO.update(an_toan=True, den=capnhat.ban_dang_chay(), luc=luc,
                  lydo=che(f"{type(loi).__name__}: {loi}")[:300], luocdo=khoitao.PHIENBAN_LUOCDO)
    try:   # F04 có thể chưa ghi được nếu chính tệp Nhatky hỏng: không chặn chế độ an toàn
        capnhat._ghi_f04("an_toan", CHE_DO["den"], "loi", CHE_DO["lydo"], thumuc=thumuc)
    except Exception:  # noqa: BLE001
        pass


def chu_an_toan() -> str | None:
    if not CHE_DO["an_toan"]:
        return None
    return CHU["an_toan"].format(den=CHE_DO["den"], luc=_gio(CHE_DO["luc"] or ""))


# Đường còn mở ở chế độ an toàn: trang, tài nguyên giao diện, sức khoẻ, đăng nhập – phiên, màn 09 Cập nhật.
DUONG_MO = ("/", "/suckhoe", "/api/dangnhap", "/api/dangxuat", "/api/toi", "/api/2lop", "/api/capnhat")


def duoc_mo(duong: str) -> bool:
    return duong == "/" or duong.startswith("/tainguyen/") or any(duong == d or duong.startswith(d + "/") for d in DUONG_MO[1:])


# ---------------- Lớp 4: kiểm sau cập nhật ----------------
def _kiem_cli(goi: str) -> bool:
    """Có công cụ AI và chạy được: chỉ hỏi số bản, không gọi hãng (QĐ192). Đường CLI như cổng AI dùng."""
    from maychu.hethong.mohinh import dangnhap_goi as dg
    try:
        r = subprocess.run([dg._cli(goi), "--version"], capture_output=True, text=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def kiem_sau_capnhat(lich_bat: bool, thumuc: Path | None = None) -> dict:
    """06 điểm sau khi lên bản mới. Trả {diem: {ma: bool}, dat, tong, ban}; ghi F04 `kiem_saunang`, mở chuông khi lỗi."""
    import sqlite3
    from maychu.dulieu import khoitao
    from maychu.hethong import capnhat
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    ban = capnhat.ban_dang_chay()
    tt = doc(thumuc)
    yc = tt.get("yeu_cau") or {}
    diem = {"ban": (yc.get("den") == ban) if yc.get("den") else True}
    tot, luocdo = True, True
    for ten in ketnoi.CAC_FILE:
        try:
            cn = ketnoi.mo(ten, thumuc)
            try:
                tot = tot and cn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                luocdo = luocdo and cn.execute("PRAGMA user_version").fetchone()[0] == khoitao.PHIENBAN_LUOCDO and \
                    cn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == ketnoi.SO_BANG[ten]
            finally:
                cn.close()
        except sqlite3.Error:
            tot = luocdo = False
    diem.update(dulieu=tot, luocdo=luocdo, lich=bool(lich_bat),
                cli=_kiem_cli("claude") and _kiem_cli("chatgpt"), o_trong=o_trong(thumuc)["du"])
    dat = sum(diem.values())
    loi = [TEN_DIEM[k] for k, v in diem.items() if not v]
    tom = f"{ban} · {dat:02d}/{len(diem):02d} đạt" if not loi else f"{ban} · {dat:02d}/{len(diem):02d} · " + ", ".join(loi)   # 45, 46
    capnhat._ghi_f04("kiem_saunang", tom, "dat" if not loi else "loi", thumuc=thumuc)
    ghi(thumuc, yeu_cau=None, kiem_ban=ban)
    from maychu.hethong.giamsat import thongbao
    thongbao.quet_kiem_capnhat(ban, loi, thumuc)
    return {"diem": diem, "dat": dat, "tong": len(diem), "ban": ban, "loi": loi}


def can_kiem(thumuc: Path | None = None) -> bool:
    """Bản đang chạy chưa có lượt kiểm sau cập nhật."""
    from maychu.hethong import capnhat
    return doc(thumuc).get("kiem_ban") != capnhat.ban_dang_chay()


# ---------------- Lớp 3: quay về bản trước ----------------
GOC_MA = Path(__file__).resolve().parents[2]


def ban_truoc() -> str | None:
    try:
        return (GOC_MA / "ban_truoc" / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _gio(luc: str) -> str:
    """"10:05"; hôm khác thì thêm ngày "10:05 23/11"."""
    if len(luc or "") < 16:
        return luc or ""
    return luc[11:16] if luc[:10] == datetime.now(MUIGIO_VN).date().isoformat() else f"{luc[11:16]} {luc[8:10]}/{luc[5:7]}"


def thong_tin_quayve(thumuc: Path | None = None) -> dict:
    """{co, ban, mat_tu, chu}. Bản này có nâng lược đồ (khoitao ghi `nang_luocdo`) thì quay về phải trả bản chụp trước
    lúc nâng: mất dữ liệu nhập sau `mat_tu`. Chế độ an toàn: dữ liệu đã trả nguyên trạng, không mất thêm."""
    from maychu.hethong import capnhat
    bt = ban_truoc()
    if not bt:
        return {"co": False, "ban": None, "mat_tu": None, "chu": CHU["qv_khong_co"]}
    n = doc(thumuc).get("nang_luocdo") or {}
    mat = n.get("luc") if n.get("ban") == capnhat.ban_dang_chay() and not CHE_DO["an_toan"] else None
    chu = (CHU["qv_mat"].format(luc=_gio(mat)) if mat else
           CHU["qv_an_toan"].format(luc=_gio(CHE_DO["luc"] or "")) if CHE_DO["an_toan"] else CHU["qv_giu"])
    return {"co": True, "ban": bt, "mat_tu": mat, "chu": chu}


def _thoat() -> None:   # pragma: no cover - dừng tiến trình để Docker bật lại vùng chứa
    os._exit(0)


def quay_ve(nguoi_id: str, dong_y_mat: bool = False, thumuc: Path | None = None, tre_giay: float = 1.5) -> dict:
    """Ghi cờ chạy bản trước (trả bản chụp trước lúc nâng nếu bản này có nâng lược đồ), ghi F04 `quayve`, rồi dừng."""
    import threading
    from maychu.dulieu import khoitao
    from maychu.hethong import capnhat
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    q = thong_tin_quayve(thumuc)
    if not q["co"]:
        return {"loi": q["chu"]}
    if q["mat_tu"] and not dong_y_mat:
        return {"loi": CHU["qv_can_dong_y"], "mat_tu": q["mat_tu"]}
    dang = capnhat.ban_dang_chay()
    if q["mat_tu"]:
        noi = khoitao._thumuc_chup(thumuc)
        khoitao._tra_nguyen_trang(thumuc, [t for t in ketnoi.CAC_FILE if (noi / f"{t}.sqlite3").exists()])
    ghi(thumuc, chay_ban_truoc={"ban_anh": dang, "ban_truoc": q["ban"], "luc": _bay()}, nang_luocdo=None)
    capnhat._ghi_f04("quayve", f"{dang} → {q['ban']}" + (f" · dữ liệu trả về lúc {_gio(q['mat_tu'])}" if q["mat_tu"] else
                                                         " · dữ liệu giữ nguyên"), "dat", None, nguoi_id, thumuc)
    threading.Timer(tre_giay, _thoat).start()
    return {"ok": True, "ban": q["ban"]}
