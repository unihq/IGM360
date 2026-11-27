"""Y50 (QĐ298, QĐ301 = A; CDA KT-Y50 05 điều kiện): đổi 02 chữ dấu kiểu cũ đã lưu trên máy chủ sang kiểu mới.

1. Tên lịch `nhac_khoa_tygia_thang` (Bot · `lich_baocao`, có phiên bản): thêm 01 phiên bản bằng `phienban.phienban_moi`,
   `nguoi_khai = 'hethong'` (giữ phiên bản cũ, không sửa đè).
2. Câu lỗi `ketnoi.loi_cuoi` do mục Két khóa ghi khi khóa bị xóa: đổi bằng `WHERE loi_cuoi = <chữ cũ>`.

05 điều kiện: (1) chỉ đổi khi chữ đang dùng còn đúng nguyên chữ cũ (anh đã tự đổi tên lịch thì không đụng); (2) lịch dùng
`phienban_moi`; (3) phiên bản đang dùng bắt đầu đúng hôm nay thì bỏ qua, không lỗi; lỗi không làm hỏng khởi động (người
gọi bọc lỗi); (4) chạy lại không đổi gì, có đổi thì ghi 01 dòng F04; (5) `loi_cuoi` chỉ đổi theo đúng chữ cũ.
Không đổi dòng F04 cũ, tin chuông cũ. 0 đổi lược đồ. Chữ cũ viết bằng mã ký tự để tệp không còn chữ kiểu cũ (QĐ302).
"""
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, phienban

LICH_MA = "nhac_khoa_tygia_thang"
LICH_CU = "Nhắc kho\u00e1 tỷ giá tháng"
LICH_MOI = "Nhắc khóa tỷ giá tháng"
LOI_CU = "Kho\u00e1 đã bị xo\u00e1 ở Két kho\u00e1"
LOI_MOI = "Khóa đã bị xóa ở Két khóa"


def _doi_lich(thumuc: Path | None, hom_nay: str) -> int:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        dang = cn.execute("SELECT ten, hieuluc_tu FROM lich_baocao WHERE ma = ? AND COALESCE(hieuluc_tu, '') <= ?"
                          " AND (hieuluc_den IS NULL OR hieuluc_den > ?) LIMIT 1", (LICH_MA, hom_nay, hom_nay)).fetchone()
        if not dang or dang[0] != LICH_CU:          # đk 1: anh đã đổi tên, hoặc đã là chữ mới, hoặc chưa có lịch
            return 0
        if (dang[1] or "")[:10] >= hom_nay:          # đk 3: phiên bản đang dùng bắt đầu hôm nay → bỏ qua, không lỗi
            return 0
        phienban.phienban_moi(cn, "lich_baocao", LICH_MA, hom_nay, {"ten": LICH_MOI}, nguoi_khai="hethong")   # đk 2
        return 1
    finally:
        cn.close()


def _doi_loi_ketnoi(thumuc: Path | None) -> int:
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        try:
            so = cn.execute("UPDATE ketnoi SET loi_cuoi = ? WHERE loi_cuoi = ?", (LOI_MOI, LOI_CU)).rowcount   # đk 5
            cn.execute("COMMIT")
        except Exception:
            cn.execute("ROLLBACK")
            raise
        return so
    finally:
        cn.close()


def doi_khi_khoidong(thumuc: Path | None = None) -> dict:
    """Gọi 01 lần lúc khởi động, ngoài chế độ an toàn (khoidong). Trả {lich, ketnoi}: số dòng đã đổi."""
    hom_nay = muigio.hom_nay()   # ② QĐ636
    kq = {"lich": _doi_lich(thumuc, hom_nay), "ketnoi": _doi_loi_ketnoi(thumuc)}
    if kq["lich"] or kq["ketnoi"]:                    # đk 4: 01 dòng F04, ghi số dòng đổi ở mỗi bảng
        from maychu.hethong import nhatky
        nhatky.ghi("dulieu", "doi_dau_kieu_moi", f"lich_baocao {kq['lich']:02d} dòng · ketnoi {kq['ketnoi']:02d} dòng",
                   thumuc=thumuc)
    return kq
