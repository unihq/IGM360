"""Thông số P01 (thiết kế Phần 2; nhãn theo bản vẽ đợt 1, QĐ88).

Sửa = thêm 01 dòng mới có ngày áp dụng, đóng `hieuluc_den` của dòng đang dùng; không xoá dòng cũ.
Thông số trống: không chặn lưu, phần mềm làm cách an toàn nhất (nhật ký mục 5.57 D câu 05).
"""
from datetime import date, datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN

NHOM = ("Tiền và giá", "Máy chủ và bảo mật", "AI", "Báo cáo và lấy dữ liệu")

# ten, nhóm, nhãn, kiểu, đơn vị, mặc định, lựa chọn {giá trị: chữ}, câu khi trống
DANHMUC = [
    ("phuongphap_giaxuat", 0, "Cách tính giá xuất kho", "chu", "", "binhquan_giaquyen",
     {"binhquan_giaquyen": "Bình quân gia quyền"}, ""),
    ("thue_quangcao_khautru", 0, "Khấu trừ thuế trên tiền nạp quảng cáo", "codong", "", "0", {"1": "Có", "0": "Không"}, ""),
    ("loai_gia_tygia", 0, "Loại tỷ giá dùng để quy đổi", "chu", "", "mua_chuyenkhoan",
     {"mua_chuyenkhoan": "Mua chuyển khoản", "ban": "Bán"}, ""),
    ("cach_phanbo_chiphimua", 0, "Cách chia chi phí mua hàng", "chu", "", "theo_sochiec",
     {"theo_sochiec": "Theo số chiếc", "theo_giatri": "Theo giá trị"}, ""),
    ("nguong_ocung", 1, "Báo khi ổ cứng máy chủ dùng quá", "so", "%", "70", None, ""),
    ("nguong_cho_day_drive", 1, "Dữ liệu chờ đẩy lên Drive tối đa", "so", "GB", "5", None, ""),
    ("songay_giu_banghigoc_vps", 1, "Số ngày giữ bản ghi gốc trên máy chủ", "so", "ngày", None, None,
     "Đang giữ mãi, không tự xoá"),
    ("songay_baotruoc_khoa_hethan", 1, "Báo trước khi khoá kết nối hết hạn", "so", "ngày", "5", None, ""),
    ("so_viec_ai_songsong", 2, "Số việc AI chạy cùng lúc", "so", "việc", "3", None, ""),
    ("phut_ket_viec_ai", 2, "Việc AI chạy quá bao lâu thì báo kẹt", "so", "phút", "30", None, ""),
    ("nguong_tien_ai_tuapdung", 2, "Ngưỡng tiền để AI được tự áp dụng", "so", "đ", None, None,
     "GĐ 1: AI chỉ đề xuất, mọi việc chờ anh bấm."),
    ("tran_tien_thang_khoa_api", 2, "Trần tiền mỗi tháng của khoá API", "so", "USD", None, None,
     "Không gọi AI bằng khoá API, chỉ dùng gói"),
    ("nhip_gui_baocao", 3, "Nhịp gửi báo cáo định kỳ", "chu", "", None, {"hangngay": "Mỗi ngày", "hangtuan": "Mỗi tuần"},
     "Không gửi báo cáo định kỳ, tin báo sự kiện vẫn gửi"),
    ("nhip_lay_dulieu", 3, "Nhịp lấy dữ liệu", "danhsach", "", None, None,
     "Không tự lấy, chỉ Lấy ngay ở Nguồn dữ liệu"),
]
# Không sửa ở ngăn Thông số: giá xuất kho chưa cho đổi ở GĐ 1 (bản vẽ đợt 1); nhịp lấy đặt từng loại ở màn 11.
KHONG_SUA = {"phuongphap_giaxuat": "Chưa cho đổi ở GĐ 1", "nhip_lay_dulieu": "Đặt ở Nguồn dữ liệu",
             "nguong_tien_ai_tuapdung": "Từ GĐ 2"}
# Thông số của phần làm ở giai đoạn sau: hiện mờ, không tính vào số đã đặt / tổng (GĐ 1 AI chỉ đề xuất, thẻ duyệt
# gửi cho mọi việc chờ; luồng Giám đốc sản phẩm quyết 20:55 ngày 21/11/2026).
GIAIDOAN_SAU = {"nguong_tien_ai_tuapdung"}
THEO_TEN = {d[0]: d for d in DANHMUC}


def _hom_nay() -> str:
    return datetime.now(MUIGIO_VN).date().isoformat()


def khoi_tao(thumuc: Path | None = None) -> int:
    """Ghi giá trị mặc định cho thông số chưa có dòng nào (chạy lại không sao). Trả về số dòng thêm."""
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    them = 0
    try:
        cn.execute("BEGIN IMMEDIATE")
        for ten, _n, _nh, kieu, donvi, macdinh, _l, _t in DANHMUC:
            if macdinh is None or cn.execute("SELECT 1 FROM thongso WHERE ten = ? AND congty_id IS NULL", (ten,)).fetchone():
                continue
            cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, donvi, hieuluc_tu, nguoi_dat, ghichu, tao_luc)"
                       " VALUES (?, ?, ?, ?, ?, ?, 'hethong', 'Giá trị khởi tạo theo thiết kế', ?)",
                       (maso.tao(), ten, macdinh, kieu, donvi, _hom_nay(), datetime.now(MUIGIO_VN).isoformat(timespec="seconds")))
            them += 1
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return them


def _dong_dang_dung(cn, ten: str, ngay: str):
    return cn.execute("SELECT id, giatri, hieuluc_tu, nguoi_dat FROM thongso WHERE ten = ? AND congty_id IS NULL"
                      " AND hieuluc_tu <= ? AND (hieuluc_den IS NULL OR hieuluc_den > ?) ORDER BY hieuluc_tu DESC LIMIT 1",
                      (ten, ngay, ngay)).fetchone()


def doc_mot(ten: str, macdinh: str | None = None, thumuc: Path | None = None) -> str | None:
    """Giá trị đang áp dụng hôm nay của 01 thông số (trống thì trả `macdinh`)."""
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        d = _dong_dang_dung(cn, ten, _hom_nay())
    finally:
        cn.close()
    return d[1] if d and d[1] not in (None, "") else macdinh


def doc_het(thumuc: Path | None = None) -> dict:
    ngay = _hom_nay()
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        ds = []
        for ten, nhom, nhan, kieu, donvi, _m, lua, trong in DANHMUC:
            d = _dong_dang_dung(cn, ten, ngay)
            sap = cn.execute("SELECT giatri, hieuluc_tu FROM thongso WHERE ten = ? AND congty_id IS NULL AND hieuluc_tu > ?"
                             " ORDER BY hieuluc_tu LIMIT 1", (ten, ngay)).fetchone()
            gt = d[1] if d else None
            ds.append({"ten": ten, "nhom": NHOM[nhom], "nhan": nhan, "kieu": kieu, "donvi": donvi,
                       "giatri": gt, "giatri_chu": (lua or {}).get(gt, gt) if gt is not None else None,
                       "hieuluc_tu": d[2] if d else None, "nguoi_dat": d[3] if d else None,
                       "luachon": [{"giatri": k, "chu": v} for k, v in (lua or {}).items()],
                       "khi_trong": trong, "khong_sua": KHONG_SUA.get(ten), "sap_ap_dung": {"giatri": sap[0], "tu": sap[1]} if sap else None})
    finally:
        cn.close()
    tinh = [x for x in ds if x["ten"] not in GIAIDOAN_SAU]
    return {"thongso": ds, "da_dat": sum(1 for x in tinh if x["giatri"] not in (None, "")), "tong": len(tinh)}


def lich_su(ten: str, thumuc: Path | None = None) -> list[dict]:
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        dong = cn.execute("SELECT giatri, hieuluc_tu, hieuluc_den, nguoi_dat, ghichu FROM thongso WHERE ten = ?"
                          " AND congty_id IS NULL ORDER BY hieuluc_tu DESC", (ten,)).fetchall()
    finally:
        cn.close()
    return [dict(zip(("giatri", "hieuluc_tu", "hieuluc_den", "nguoi_dat", "ghichu"), d)) for d in dong]


def kiem_giatri(ten: str, giatri: str) -> str | None:
    d = THEO_TEN.get(ten)
    if not d:
        return "Không có thông số này"
    kieu, lua = d[3], d[6]
    if lua and giatri not in lua:
        return "Giá trị không nằm trong danh sách chọn"
    if kieu == "so":
        try:
            if float(giatri) < 0:
                return "Giá trị phải từ 0 trở lên"
        except ValueError:
            return "Giá trị phải là số"
    return None


def dat(ten: str, giatri: str, hieuluc_tu: str, ghichu: str = "", nguoi: str = "anh", thumuc: Path | None = None) -> dict:
    """Thêm 01 phiên bản thông số. Ngày áp dụng phải sau ngày bắt đầu của dòng mới nhất (không chồng lấn)."""
    giatri = (giatri or "").strip()
    if ten in KHONG_SUA:
        return {"loi": KHONG_SUA[ten], "o": "giatri"}
    loi = kiem_giatri(ten, giatri) if giatri else ("Thông số này không để trống được" if THEO_TEN.get(ten, [0] * 8)[5] else None)
    if loi:
        return {"loi": loi, "o": "giatri"}
    try:
        tu = date.fromisoformat(hieuluc_tu).isoformat()
    except (TypeError, ValueError):
        return {"loi": "Ngày áp dụng chưa đúng", "o": "tu"}
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        moi_nhat = cn.execute("SELECT id, hieuluc_tu FROM thongso WHERE ten = ? AND congty_id IS NULL"
                              " ORDER BY hieuluc_tu DESC LIMIT 1", (ten,)).fetchone()
        if moi_nhat and tu <= moi_nhat[1]:
            cn.execute("ROLLBACK")
            return {"loi": f"Ngày áp dụng phải sau {date.fromisoformat(moi_nhat[1]).strftime('%d/%m/%Y')} (ngày bắt đầu của giá trị đang có)", "o": "tu"}
        if moi_nhat:
            cn.execute("UPDATE thongso SET hieuluc_den = ? WHERE id = ?", (tu, moi_nhat[0]))
        d = THEO_TEN[ten]
        cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, donvi, hieuluc_tu, nguoi_dat, ghichu, tao_luc)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (maso.tao(), ten, giatri or None, d[3], d[4], tu, nguoi, ghichu or None,
                    datetime.now(MUIGIO_VN).isoformat(timespec="seconds")))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return {"ok": True}
