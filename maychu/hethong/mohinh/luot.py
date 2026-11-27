"""N0 – sổ lượt trò chuyện chạy nền + luồng sự kiện (QĐ344, QĐ347, QĐ348, QĐ350, QĐ352; kế hoạch Kehoach_Luot_Chaynen
mục 2, 8; điều kiện CDA KT-N0 (1)–(6), S1–S5, X1–X4, C1–C2).

- Mỗi lượt có 01 dòng G02 `viecnen` (`loai = 'trochuyen'`, `goi_ai = 1`): cập nhật chế độ chờ, dọn CLI cũ, đo máy đếm
  được lượt đang trả lời mà không sửa câu đếm (`capnhat.so_viec_ai_dangchay`).
- Sổ lượt trong bộ nhớ (01 tiến trình uvicorn) giữ sự kiện có số thứ tự để phát cho trang (SSE), phát lại khi nối lại.
  Lượt vào sổ TRƯỚC khi ghi G02, rời sổ SAU khi đóng G02 (S1); lượt xong giữ sự kiện 05 phút.
- Đóng G02 luôn bằng `WHERE id = ? AND trangthai = 'dangchay'` và ghi `xong_luc` (S5, X2).
- Khởi động lại (`don_khi_khoidong`) và lượt kẹt (`dong_luot_ket`, lịch mỗi phút) dùng chung `doi_chieu_dong` (S2, C1, C2).
- Xóa dòng G02 `trochuyen` đã đóng quá 24 giờ (`xoa_dong_cu`, lịch mỗi giờ; QĐ348, X1–X4).
"""
import json
import threading
import time
from datetime import timedelta

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso

BOOT_ID = maso.tao()   # mã lần khởi động: dòng G02 `dangchay` mang mã khác là lượt bị cắt do khởi động lại
GIU_SU_KIEN_GIAY = 300
GIAY_TOIDA_XEM = 600   # `giu_den` = bắt đầu + 600 giây: chỉ để xem, không dùng làm điều kiện đóng (SOAT-H2 S1)
LOAI = "trochuyen"
# QĐ352 (anh "Duyệt A cả 02"), đúng chữ bảng "Câu báo trò chuyện 0.8.7"
CHU_CAT = "Câu trả lời bị ngắt vì phần mềm khởi động lại. Bạn gửi lại câu hỏi."
CHU_CHO_CAPNHAT = "Phần mềm đang chờ cập nhật nên chưa nhận câu hỏi mới. Câu hỏi vẫn ở ô nhập, bạn gửi lại sau khi cập nhật xong."
PHU_CAT = {"loai": "luot_cat"}   # QĐ350: tin bị cắt không hiện nút "Mở Mô hình AI"
KET_THUC = ("xong", "dung", "loi")


def bay_gio() -> str:
    return muigio.gio_luu()


class Luot:
    def __init__(self, luot_id: str, hoithoai_id: str, nguoidung_id: str):
        self.id, self.hoithoai_id, self.nguoidung_id = luot_id, hoithoai_id, nguoidung_id
        self.su_kien: list[dict] = []
        self.dieu = threading.Condition()
        self.ket_thuc = False
        self.xong_mono = 0.0
        self.nghe = None          # congai.Nghe khi có người nghe
        self.ket_qua = None       # dict trả cho `trochuyen.gui` (đường đồng bộ)
        self.loi_ngoai = None     # lỗi không lường trước của luồng nền (đường đồng bộ ném lại)
        self.luong = None

    def phat(self, loai: str, **du) -> None:
        with self.dieu:
            self.su_kien.append({"so": len(self.su_kien) + 1, "loai": loai, **du})
            if loai in KET_THUC:
                self.ket_thuc, self.xong_mono = True, time.monotonic()
            self.dieu.notify_all()

    def doi(self, tu: int, giay: float) -> list[dict]:
        """Sự kiện có số > `tu`; chưa có thì chờ tối đa `giay` giây."""
        with self.dieu:
            if len(self.su_kien) <= tu and not self.ket_thuc:
                self.dieu.wait(giay)
            return list(self.su_kien[tu:])


_KHOA = threading.Lock()
_DANG: dict[str, Luot] = {}      # lượt đang chạy (S1: H2 chỉ đóng dòng không còn ở đây)
_DA_XONG: dict[str, Luot] = {}   # lượt xong, giữ sự kiện GIU_SU_KIEN_GIAY để trang nối lại


def _don_sau() -> None:
    het = time.monotonic() - GIU_SU_KIEN_GIAY
    for k in [k for k, v in _DA_XONG.items() if v.xong_mono < het]:
        _DA_XONG.pop(k, None)


def vao_so(lt: Luot) -> None:
    with _KHOA:
        _don_sau()
        _DANG[lt.id] = lt


def roi_so(lt: Luot, giu: bool = True) -> None:
    """Bỏ khỏi sổ lượt đang chạy (sau khi đã đóng G02); `giu` = giữ sự kiện cho trang nối lại."""
    with _KHOA:
        _DANG.pop(lt.id, None)
        if giu:
            if not lt.xong_mono:
                lt.xong_mono = time.monotonic()
            _DA_XONG[lt.id] = lt


def lay(luot_id: str, nguoidung_id: str) -> Luot | None:
    with _KHOA:
        _don_sau()
        lt = _DANG.get(luot_id) or _DA_XONG.get(luot_id)
    return lt if lt is not None and lt.nguoidung_id == nguoidung_id else None


def dang_chay_cua(hoithoai_id: str) -> str | None:
    with _KHOA:
        return next((k for k, v in _DANG.items() if v.hoithoai_id == hoithoai_id), None)


def dang_trong_so(luot_id: str) -> bool:
    with _KHOA:
        return luot_id in _DANG


# ---------------- G02 ----------------
def mo_g02(luot_id: str, hoithoai_id: str, tin_hoi_id: str, thumuc=None) -> str | None:
    """Ghi 01 dòng G02 `dangchay`. Cuộc đang có lượt chạy (cùng `khoa_chongtrung`) thì không ghi, trả mã lượt đó."""
    bd = muigio.bay()
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cu = cn.execute("SELECT id FROM viecnen WHERE loai = ? AND trangthai = 'dangchay' AND khoa_chongtrung = ?",
                        (LOAI, LOAI + ":" + hoithoai_id)).fetchone()
        if cu:
            cn.execute("ROLLBACK")
            return cu[0]
        cn.execute("INSERT INTO viecnen (id, loai, goi_ai, trangthai, khoa_chongtrung, giu_boi, giu_den, ketqua_json,"
                   " tao_luc, batdau_luc) VALUES (?, ?, 1, 'dangchay', ?, ?, ?, ?, ?, ?)",
                   (luot_id, LOAI, LOAI + ":" + hoithoai_id, BOOT_ID,
                    (bd + timedelta(seconds=GIAY_TOIDA_XEM)).isoformat(timespec="seconds"),
                    json.dumps({"hoithoai_id": hoithoai_id, "tin_hoi_id": tin_hoi_id}),
                    bd.isoformat(timespec="seconds"), bd.isoformat(timespec="seconds")))
        cn.execute("COMMIT")
        return None
    except BaseException:
        if cn.in_transaction:
            cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()


def dong_g02(luot_id: str, trangthai: str, loi: str | None = None, thumuc=None) -> bool:
    """Đóng dòng G02 đang chạy (S5): chỉ lật dòng `dangchay`, ghi `xong_luc` (X2). Trả True nếu đã lật 01 dòng."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        so = cn.execute("UPDATE viecnen SET trangthai = ?, xong_luc = ?, loi = ? WHERE id = ? AND trangthai = 'dangchay'",
                        (trangthai, bay_gio(), loi, luot_id)).rowcount
        cn.execute("COMMIT")
        return so == 1
    except BaseException:
        if cn.in_transaction:
            cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()


def _dong_dang_chay(thumuc=None) -> list[tuple]:
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        return cn.execute("SELECT id, giu_boi, ketqua_json FROM viecnen WHERE loai = ? AND trangthai = 'dangchay'",
                          (LOAI,)).fetchall()
    finally:
        cn.close()


def doi_chieu_dong(luot_id: str, ketqua_json: str | None, thumuc=None) -> str | None:
    """Hàm chung của khởi động và H2 (S2). (a) Đã có tin `ai` hoặc `hethong` trả lời tin hỏi (C1) → đóng `xong`.
    (b) Chưa có: giành dòng trước (đóng `hong`), chỉ khi lật được 01 dòng mới ghi 01 tin báo bị cắt (C2).
    Trả "xong" | "cat" | None (dòng đã được nơi khác đóng)."""
    from maychu.hethong.mohinh import trochuyen
    try:
        kq = json.loads(ketqua_json or "{}")
    except ValueError:
        kq = {}
    hoi, ht = kq.get("tin_hoi_id"), kq.get("hoithoai_id")
    if hoi:
        cn = ketnoi.mo("Bot", thumuc)
        try:
            da_tra_loi = cn.execute("SELECT 1 FROM tinnhan WHERE tra_loi_cho = ? AND vai IN ('ai', 'hethong') LIMIT 1",
                                    (hoi,)).fetchone()
            co_hoi = cn.execute("SELECT 1 FROM tinnhan WHERE id = ?", (hoi,)).fetchone()
        finally:
            cn.close()
        if da_tra_loi:
            return "xong" if dong_g02(luot_id, "xong", thumuc=thumuc) else None
    else:
        co_hoi = None
    if not dong_g02(luot_id, "hong", "bỏ lượt dở", thumuc=thumuc):
        return None
    if co_hoi and ht:   # tin hỏi đã ghi mà không có trả lời → 01 tin báo bị cắt (QĐ352 Đ2, QĐ350)
        cn = ketnoi.mo("Bot", thumuc)
        try:
            trochuyen._ghi_tin(cn, ht, "hethong", CHU_CAT, trangthai="loi", tra_loi_cho=hoi, phu=PHU_CAT)
        finally:
            cn.close()
    return "cat"


def _ghi_f04_bo(so: int, noi: str, thumuc=None) -> None:
    if so:
        from maychu.hethong import nhatky
        nhatky.ghi(LOAI, "bo_luot_do", f"{noi}: đóng {so:02d} lượt trò chuyện dở", thumuc=thumuc)


def don_khi_khoidong(thumuc=None) -> int:
    """Khởi động lại: mọi dòng `trochuyen` `dangchay` mang mã khởi động khác là lượt bị cắt. 01 dòng F04 khi đóng ≥ 01."""
    so = 0
    for ma, boi, kq in _dong_dang_chay(thumuc):
        if boi != BOOT_ID and doi_chieu_dong(ma, kq, thumuc):
            so += 1
    _ghi_f04_bo(so, "khởi động", thumuc)
    return so


def dong_luot_ket(thumuc=None) -> int:
    """H2 (SOAT-H2 S1–S4, lịch mỗi phút, `asyncio.to_thread`): dòng mang mã khởi động hiện tại mà lượt không còn trong
    sổ (luồng đã kết thúc nhưng đóng G02 lỗi). Lượt còn trong sổ (đang chờ chỗ, đang ở nguồn thứ 02) không đụng."""
    so = 0
    for ma, boi, kq in _dong_dang_chay(thumuc):
        if boi == BOOT_ID and not dang_trong_so(ma) and doi_chieu_dong(ma, kq, thumuc):
            so += 1
    _ghi_f04_bo(so, "lượt kẹt", thumuc)
    return so


def xoa_dong_cu(thumuc=None) -> int:
    """QĐ348 (X1–X4): xóa dòng G02 `trochuyen` đã đóng quá 24 giờ, bỏ qua dòng còn được G05 `suco` trỏ tới.
    01 lệnh DELETE trong BEGIN IMMEDIATE; chạy lại không đổi gì; không ghi F04. H08, G04 không đụng."""
    moc = muigio.gio_luu(muigio.bay() - timedelta(hours=24))
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        so = cn.execute("DELETE FROM viecnen WHERE loai = ? AND trangthai IN ('xong', 'huy', 'hong')"
                        " AND xong_luc IS NOT NULL AND xong_luc < ?"
                        " AND NOT EXISTS (SELECT 1 FROM suco WHERE suco.viecnen_id = viecnen.id)", (LOAI, moc)).rowcount
        cn.execute("COMMIT")
        return so
    except BaseException:
        if cn.in_transaction:
            cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
