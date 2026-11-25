"""05 lớp an toàn khi cập nhật (QĐ163, QĐ202, QĐ213; kế hoạch Y38a `Kehoach_Capnhat_Antoan.md`).

Lớp 1  ổ trống trước khi cập nhật: `o_trong()`.
Lớp 2  chế độ an toàn khi nâng dữ liệu không thành hoặc lần nâng trước bị ngắt: `vao_an_toan()`, cờ ở tệp trạng thái.
Lớp 4  kiểm sau cập nhật: `kiem_sau_capnhat()`, 06 điểm, ghi F04 `capnhat` / `kiem_saunang`.
Lớp 5  bản sao Drive trước khi cập nhật: `capnhat.yeu_cau` gọi `saoluu.chay` vào thư mục riêng (xem capnhat.py).
Lớp 3  quay về bản trước (QĐ215, cách 2): mã bản liền trước để sẵn trong ảnh ở `/app/ban_truoc`; `quay_ve()` ghi cờ
       rồi tự dừng, Docker bật lại, `maychu.chay` chạy bản trước. Không khóa mới, không cần mạng, lùi đúng 01 bản.

0 bảng, 0 cột: trạng thái cập nhật nằm ở 01 tệp `capnhat_trangthai.json` trên ổ dữ liệu (không có dữ liệu cá nhân,
không có mã). Ngưỡng và chữ hiện viết ở 01 chỗ này (như nhịp 05 phút QĐ174), không phải thông số.
Nguồn học cách làm: tailieu/Songuongoc.md (mục 0.7.9).
"""
import json
import os
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN

# ---- Ngưỡng (01 chỗ) ----
HE_SO_DULIEU = 3                  # bản chụp trước khi nâng + bản sao + bản mã hóa (học kiemtruoc_ban3: ≥ 03 lần)
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
    "sao_loi": "Chưa tạo được bản sao trước khi cập nhật: {lydo}",          # QĐ290 (Z25 dòng 8), ngoài bảng QĐ218
    "drive_chua_noi": "Drive chưa kết nối. Bản sao chỉ nằm trên máy chủ.",                                        # 31
    "drive_qua_gio": "Đẩy bản sao lên Drive đã quá 10 phút. Bản sao chỉ nằm trên máy chủ.",                        # 32
    # QĐ287, QĐ296 (Z24 dòng 1, anh sửa chữ 24/11/2026 19:21): bản sao trước khi nâng đã xóa (QĐ281) → nút Quay về khóa
    "qv_het_han": "Không còn dữ liệu bản sao trước đó (đã xóa ngày {ngay}).",
    # CDA Y49b N1, QĐ296 (Z24 dòng 1b): không có dòng F04 ghi ngày xóa
    "qv_het_han_khong_ngay": "Không tìm thấy ngày xóa dữ liệu bản sao.",
    "qv_khong_co": "Ảnh này chưa có bản trước để quay về",                   # ngoài bảng: nút không hiện khi không có bản trước
    "qv_mat": "Bản đang dùng đã nâng dữ liệu khi cập nhật. Quay về thì dữ liệu trả về lúc {luc} (trước khi cập nhật); "
              "việc nhập sau lúc đó không giữ được.",                                                             # 40
    "qv_giu": "Lần cập nhật này không nâng dữ liệu: dữ liệu giữ nguyên.",                                         # 41
    "qv_an_toan": "Dữ liệu đã trả về lúc {luc}, quay về không mất thêm.",                                         # 42
    "qv_can_dong_y": "Lần cập nhật này có nâng dữ liệu: bạn xác nhận chấp nhận mất dữ liệu nhập sau giờ cập nhật",
    # Quay về hỏng (QĐ219 bảng 15 câu A4–A7): chuông = câu đầu; màn Cập nhật, trang đang chờ = câu đầu + câu sau
    "qv_loi_tra": "Quay về bản {truoc} chưa được: chưa trả được dữ liệu",                                       # A4
    "qv_loi_hong": "Quay về bản {truoc} chưa được: bản này lỗi khởi động {n:02d} lần",                            # A5
    "qv_loi_tra_sau": "Vẫn chạy bản {ban}, dữ liệu giữ nguyên.",                                                # A6
    "qv_loi_hong_sau": "Đã chạy lại bản {ban}.",                                                                 # A7
    "qv_loi_da_tra": "Dữ liệu đã trả về lúc {luc}.",                                                             # A7
}
# Lý do chưa đạt của từng điểm kiểm sau cập nhật (QĐ219 A9–A13; QĐ218 dòng 47: "lịch chạy nền chưa bật")
TEN_DIEM = {"ban": "chưa lên đúng bản", "dulieu": "tệp dữ liệu hỏng", "luocdo": "cấu trúc dữ liệu lệch",
            "lich": "lịch chạy nền chưa bật", "cli": "gói AI chưa chạy được", "o_trong": "chưa đủ ổ trống"}

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


_KHOA_GHI = threading.Lock()


def ghi_nguyen_tu(p: Path, d: dict) -> None:
    """Ghi JSON kiểu tệp tạm riêng (tên có số tiến trình, luồng) rồi đổi tên; fsync trước khi đổi (Y38c R7, CDA C2)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tam")
    fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tam, p)
    finally:
        tam.unlink(missing_ok=True)
    if hasattr(os, "O_DIRECTORY"):   # Linux: ghi chắc cả lần đổi tên
        dfd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


def ghi(thumuc: Path | None = None, **muc) -> dict:
    """Gộp các mục vào tệp trạng thái (giá trị None = bỏ mục); đọc – gộp – ghi trong 01 khóa (Y38c R7)."""
    with _KHOA_GHI:
        d = doc(thumuc)
        for k, v in muc.items():
            d.pop(k, None) if v is None else d.__setitem__(k, v)
        ghi_nguyen_tu(_tep(thumuc), d)
        return d


def _bay() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


# ---------------- Lớp 1: ổ trống ----------------
def chu_dungluong(so_byte: float) -> str:
    """QĐ311 G3 + QĐ312 ("Bỏ số 0 thừa"): dưới 1.000 MB ghi MB ("819 MB"); từ 1.000 MB ghi GB, tối đa 01 chữ số thập
    phân, bỏ ",0" ("1 GB", "1,2 GB"); từ 1.000 GB có chấm ngăn nghìn ("9.315,2 GB"). Chỉ để hiện chữ; so sánh ổ trống
    vẫn theo byte."""
    mb = round(so_byte / 1024 ** 2)
    if mb < 1000:
        return f"{mb} MB"
    nguyen, thap = f"{so_byte / 1024 ** 3:.1f}".split(".")
    return f"{int(nguyen):,}".replace(",", ".") + ("," + thap if thap != "0" else "") + " GB"


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
    luc = tt.get("chup_luc") or (tt.get("dang_nang") or {}).get("luc") or _bay()   # Y38c R8: khoitao ghi `chup_luc`
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


# Đường còn mở ở chế độ an toàn: trang, tài nguyên giao diện, sức khỏe, đăng nhập – phiên, màn 09 Cập nhật.
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


def _luocdo_ban4_du(tt: dict, ban: str, thumuc: Path) -> bool:
    """K4 (0.8.0): điểm "lược đồ" phủ bản 4, chỉ ở lần kiểm của bản vừa nâng lược đồ (`nang_luocdo.ban` = bản đang chạy):
    số dòng các bảng ghi lúc nâng (`nang_luocdo.so_dong`) không được ít đi; chỉ mục tìm chữ H08 (bảng nối) đủ dòng như H08.
    Không thêm điểm, không thêm câu."""
    import sqlite3
    try:
        n = tt.get("nang_luocdo") or {}
        if n.get("ban") != ban:   # Y40b L2: chỉ so ở lần kiểm của bản vừa nâng; lệch 01 tin về sau không làm mọi lần kiểm báo lỗi
            return True
        for khoa, so in (n.get("so_dong") or {}).items():
            ten, bang = khoa.split(".", 1)
            cn = ketnoi.mo(ten, thumuc)
            try:
                if cn.execute(f"SELECT count(*) FROM {bang}").fetchone()[0] < int(so):
                    return False
            finally:
                cn.close()
        cn = ketnoi.mo("Bot", thumuc)
        try:
            return cn.execute("SELECT count(*) FROM tinnhan").fetchone()[0] == \
                cn.execute("SELECT count(*) FROM tinnhan_tim_noi").fetchone()[0]
        finally:
            cn.close()
    except (sqlite3.Error, ValueError):
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
    from maychu.hethong import tiendo
    diem = {"ban": tiendo.da_len(ban, yc.get("den"))}   # QĐ386: bản chạy ≥ bản yêu cầu là đạt; quay về (< yêu cầu) vẫn chưa đạt
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
    luocdo = luocdo and _luocdo_ban4_du(tt, ban, thumuc)
    from maychu.hethong import tiendo
    tiendo.chi_tiet("kiem", thumuc, da=3, tong=6)   # QĐ251: đã chấm bản, tệp dữ liệu, lược đồ
    diem.update(dulieu=tot, luocdo=luocdo, lich=bool(lich_bat),
                cli=_kiem_cli("claude") and _kiem_cli("chatgpt"), o_trong=o_trong(thumuc)["du"])
    dat = sum(diem.values())
    loi = [TEN_DIEM[k] for k, v in diem.items() if not v]
    tom = f"{ban} · {dat:02d}/{len(diem):02d} đạt" if not loi else f"{ban} · {dat:02d}/{len(diem):02d} · " + ", ".join(loi)   # 45, 46
    capnhat._ghi_f04("kiem_saunang", tom, "dat" if not loi else "loi", thumuc=thumuc)
    if not loi:   # D1-2 (QĐ281): kiểm đạt thì dọn bản sao trước khi nâng cũ hơn ngay (lên 0.8.3: v03 xóa)
        try:
            from maychu.dulieu import saoluu
            saoluu.don_truoc_nangcap(thumuc)
        except Exception:  # noqa: BLE001 - dọn lỗi không làm hỏng lượt kiểm
            import logging
            logging.getLogger(__name__).exception("dọn bản sao trước khi nâng lỗi")
    tiendo.chi_tiet("kiem", thumuc, da=6, tong=6, xong=True)
    tiendo.xong(ban, thumuc)   # QĐ251: hết lượt cập nhật → 01 dòng F04 tóm tắt thời gian từng bước
    ghi(thumuc, yeu_cau=None, kiem_ban=ban)
    from maychu.hethong.giamsat import thongbao
    thongbao.quet_kiem_capnhat(ban, loi, thumuc)
    return {"diem": diem, "dat": dat, "tong": len(diem), "ban": ban, "loi": loi}


CHO_KIEM_LICH_GIAY = 30


def kiem_sau_khi_chay(viec, thumuc: Path | None = None) -> dict:
    """Y38c R6: chờ CHO_KIEM_LICH_GIAY rồi mới chấm điểm "lịch chạy nền" theo việc lịch còn chạy thật (không tự đạt)."""
    import time
    time.sleep(CHO_KIEM_LICH_GIAY)
    return kiem_sau_capnhat(viec is not None and not viec.done(), thumuc)


def chu_quay_ve_loi(loi: dict, ban_dang: str) -> str:
    """Câu màn Cập nhật (A6, A7) từ mục `quayve_loi` lệnh chạy ghi. Câu đầu (trước ". " đầu tiên) là câu chuông (A4, A5)."""
    truoc = loi.get("ban_truoc") or "trước"
    hong = loi.get("kieu") == "khoidong" or (not loi.get("kieu") and "khởi động" in str(loi.get("chu", "")))
    ban = loi.get("ban_anh") or ban_dang
    if not hong:
        return CHU["qv_loi_tra"].format(truoc=truoc) + ". " + CHU["qv_loi_tra_sau"].format(ban=ban)
    s = CHU["qv_loi_hong"].format(truoc=truoc, n=int(loi.get("so_lan") or 3)) + ". " + CHU["qv_loi_hong_sau"].format(ban=ban)
    return s + (" " + CHU["qv_loi_da_tra"].format(luc=_gio(loi["da_tra"])) if loi.get("da_tra") else "")


def cau_chuong(chu_man: str) -> str:
    return str(chu_man).split(". ", 1)[0]


def bao_quay_ve_loi(thumuc: Path | None = None) -> None:
    """Lệnh chạy (maychu/chay.py) ghi `quayve_loi` khi không trả được dữ liệu hoặc bản trước khởi động hỏng: ghi F04 01 lần
    bằng đúng câu màn Cập nhật (QĐ219 A6, A7); lý do kỹ thuật ghi vào nhật ký máy chủ."""
    import logging
    from maychu.hethong import capnhat
    loi = doc(thumuc).get("quayve_loi")
    if loi:
        logging.getLogger(__name__).warning("quay về hỏng: %s", loi.get("chu"))
        capnhat._ghi_f04("quayve", chu_quay_ve_loi(loi, capnhat.ban_dang_chay())[:250], "loi", None, thumuc=thumuc)
        ghi(thumuc, quayve_loi=None)


def quay_ve_loi_gan(thumuc: Path | None = None, luc: str | None = None) -> dict | None:
    """Y38d: lần quay về hỏng gần nhất trong 07 ngày (hoặc đúng lượt `luc`), đọc F04 `quayve` kết quả `loi`.
    `chu_hien` = câu màn Cập nhật (A6, A7), `chu_chuong` = câu chuông (A4, A5)."""
    from datetime import timedelta
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        d = cn.execute("SELECT luc, thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'quayve' AND ketqua = 'loi'"
                       + (" AND luc = ?" if luc else " AND luc >= ?") + " ORDER BY luc DESC LIMIT 1",
                       (luc or (datetime.now(MUIGIO_VN) - timedelta(days=7)).isoformat(timespec="seconds"),)).fetchone()
    finally:
        cn.close()
    return {"luc": d[0], "chu": d[1], "chu_hien": d[1], "chu_chuong": cau_chuong(d[1])} if d else None


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
    if mat:   # QĐ284, QĐ287 (D1-3): bản có nâng lược đồ mà bản sao trước khi nâng đã xóa → nút hiện, khóa, kèm dòng báo
        from maychu.dulieu import khoitao, saoluu
        noi = khoitao._thumuc_chup(thumuc or ketnoi.thumuc_dulieu())
        if not noi.is_dir():
            ngay = saoluu.ngay_xoa_truoc_nangcap(noi.name, thumuc)
            return {"co": True, "khoa": True, "ban": bt, "mat_tu": None,
                    "chu": CHU["qv_het_han"].format(ngay=datetime.fromisoformat(ngay).strftime("%d/%m/%Y")) if ngay
                    else CHU["qv_het_han_khong_ngay"]}
    chu = (CHU["qv_mat"].format(luc=_gio(mat)) if mat else
           CHU["qv_an_toan"].format(luc=_gio(CHE_DO["luc"] or "")) if CHE_DO["an_toan"] else CHU["qv_giu"])
    return {"co": True, "ban": bt, "mat_tu": mat, "chu": chu}


def _thoat() -> None:   # pragma: no cover - dừng tiến trình để Docker bật lại vùng chứa
    os._exit(0)


def quay_ve(nguoi_id: str, dong_y_mat: bool = False, thumuc: Path | None = None, tre_giay: float = 1.5) -> dict:
    """Ghi cờ chạy bản trước (trả bản chụp trước lúc nâng nếu bản này có nâng lược đồ), ghi F04 `quayve`, rồi dừng."""
    from maychu.dulieu import khoitao
    from maychu.hethong import capnhat
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    q = thong_tin_quayve(thumuc)
    if not q["co"] or q.get("khoa"):   # QĐ287: nút khóa thì máy chủ cũng từ chối
        return {"loi": q["chu"]}
    if q["mat_tu"] and not dong_y_mat:
        return {"loi": CHU["qv_can_dong_y"], "mat_tu": q["mat_tu"]}
    dang = capnhat.ban_dang_chay()
    co = {"ban_anh": dang, "ban_truoc": q["ban"], "luc": _bay(), "nguoi": nguoi_id}
    if q["mat_tu"]:   # Y38c R1, G4: KHÔNG trả dữ liệu lúc phần mềm còn chạy (lịch nền vẫn ghi); chỉ ghi việc cần trả,
        # maychu/chay.py trả 07 tệp trước khi chạy bản trước (không tiến trình nào đang mở tệp), trả đủ hoặc không trả tệp nào
        noi = khoitao._thumuc_chup(thumuc)
        co["tra_du_lieu"] = {"thumuc": noi.name, "tep": [t for t in ketnoi.CAC_FILE if (noi / f"{t}.sqlite3").exists()]}
    try:   # ghi nhật ký trước, rồi mới ghi cờ; lỗi ở bước nào thì không dừng phần mềm
        capnhat._ghi_f04("quayve", f"{dang} → {q['ban']}" + (f" · dữ liệu trả về lúc {_gio(q['mat_tu'])}" if q["mat_tu"] else
                                                             " · dữ liệu giữ nguyên"), "dat", None, nguoi_id, thumuc)
        ghi(thumuc, chay_ban_truoc=co, nang_luocdo=None if not q["mat_tu"] else (doc(thumuc).get("nang_luocdo")))
        try:   # QĐ264 (Y46): quay về thì công cụ AI dùng bản trong gói của bản đó, tự nâng tạm dừng
            from maychu.hethong.mohinh import nangcli
            nangcli.tam_dung(q["ban"], thumuc)
        except Exception:  # noqa: BLE001 - không làm hỏng quay về
            import logging
            logging.getLogger(__name__).exception("tạm dừng tự nâng công cụ AI lỗi")
    except Exception as e:  # noqa: BLE001
        return {"loi": "Chưa quay về được: " + type(e).__name__}
    threading.Timer(tre_giay, _thoat).start()
    return {"ok": True, "ban": q["ban"]}
