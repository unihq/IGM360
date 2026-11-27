"""Thông số P01 (thiết kế Phần 2; nhãn theo bản vẽ đợt 1, QĐ88).

Sửa = thêm 01 dòng mới có ngày áp dụng, đóng `hieuluc_den` của dòng đang dùng; không xóa dòng cũ.
Thông số trống: không chặn lưu, phần mềm làm cách an toàn nhất (nhật ký mục 5.57 D câu 05).
"""
from datetime import date, datetime
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import aibam, ketnoi, maso

NHOM = ("Tài chính", "Máy chủ, sao lưu", "AI", "Báo cáo, dữ liệu")   # QĐ139; QĐ586: "Máy chủ, sao lưu" (nhóm Bộ não ẩn ở 0.10.0 – L16)

# ten, nhóm, nhãn, kiểu, đơn vị, mặc định, lựa chọn {giá trị: chữ}, câu khi trống
DANHMUC = [
    ("phuongphap_giaxuat", 0, "Cách tính giá xuất kho", "chu", "", "binhquan_giaquyen",
     {"binhquan_giaquyen": "Bình quân gia quyền"}, ""),
    ("thue_quangcao_khautru", 0, "Khấu trừ thuế trên tiền nạp quảng cáo", "codong", "", "0", {"1": "Có", "0": "Không"}, ""),
    ("loai_gia_tygia", 0, "Loại tỷ giá dùng để quy đổi", "chu", "", "mua_chuyenkhoan",
     {"mua_chuyenkhoan": "Mua chuyển khoản", "ban": "Bán"}, ""),
    ("cach_phanbo_chiphimua", 0, "Tiêu thức phân bổ", "chu", "", "theo_sochiec",
     {"theo_sochiec": "Theo số lượng", "theo_giatri": "Theo giá trị"}, ""),
    ("nguong_ocung", 1, "Báo khi ổ cứng máy chủ dùng quá", "so", "%", "70", None, ""),
    ("saoluu_drive", 1, "Sao lưu Google Drive", "codong", "", "0", {"0": "Tắt", "1": "Bật"}, ""),   # QĐ277, QĐ278 (Z21)
    ("nguong_cho_day_drive", 1, "Dữ liệu chờ đẩy lên Drive tối đa", "so", "GB", "5", None, ""),
    ("songay_giu_banghigoc_vps", 1, "Số ngày giữ bản ghi gốc trên máy chủ", "so", "ngày", None, None,
     "Đang giữ mãi, không tự xóa"),
    ("songay_baotruoc_khoa_hethan", 3, "Báo trước khi khóa kết nối hết hạn", "so", "ngày", "5", None, ""),
    # QĐ263, QĐ271 (Z20 dòng 1): công tắc "Tự nâng mỗi ngày" của khối Công cụ AI, mặc định bật; hiện ở màn Cập nhật,
    # không hiện ở ngăn Thông số (AN_O_THONGSO)
    ("tunang_congcu_ai", 2, "Tự nâng mỗi ngày", "codong", "", "1", {"0": "Tắt", "1": "Bật"}, ""),
    ("so_viec_ai_songsong", 2, "Số việc AI chạy cùng lúc", "so", "việc", "3", None, ""),
    ("phut_ket_viec_ai", 2, "Việc AI chạy quá bao lâu thì báo kẹt", "so", "phút", "30", None, ""),
    # QĐ627 (3), QĐ649: công tắc "Giữ dấu ảnh AI" ở ngăn Chung, mặc định bật; không hiện ở ngăn Thông số (AN_O_THONGSO)
    ("anh_ai_giu_dau_c2pa", 2, "Giữ dấu ảnh AI", "codong", "", "1", {"0": "Tắt", "1": "Bật"}, ""),
    ("tyle_bao_hanmuc_tuan", 2, "Báo khi gói AI dùng quá hạn mức tuần", "so", "%", "80", None, ""),   # QĐ165, PTD-06 mục 10
    ("nguong_tien_ai_tuapdung", 2, "Ngưỡng tự duyệt", "so", "đ", None, None,
     "GĐ 1: AI chỉ đề xuất, mọi việc chờ bạn bấm."),
    ("tran_tien_thang_khoa_api", 2, "Hạn mức chi tháng", "so", "USD", None, None,
     "Không gọi AI bằng khóa API, chỉ dùng gói"),
    ("nhip_gui_baocao", 3, "Nhịp gửi báo cáo định kỳ", "chu", "", None, {"hangngay": "Mỗi ngày", "hangtuan": "Mỗi tuần"},
     "Không gửi báo cáo định kỳ, tin báo sự kiện vẫn gửi"),
    ("nhip_lay_dulieu", 3, "Nhịp lấy dữ liệu", "danhsach", "", None, None,
     "Không tự lấy, chỉ Lấy ngay ở mục Nguồn dữ liệu"),
    # QĐ636 (D-a, CDA PTD-20 mục 5): 01 múi giờ chung cho cả phần mềm (② ngày số liệu, ③ giờ hiện, lịch) + múi đối
    # soát với sàn. Đổi ở thẻ Chung qua đường riêng (chỉ Chủ, mật khẩu + mã 02 lớp) – không hiện ở ngăn Thông số.
    ("muigio", 1, "Múi giờ", "chu", "", "Asia/Ho_Chi_Minh", None, ""),   # nhãn nội bộ, không hiện ở màn nào (AN_O_THONGSO)
    ("muigio_doisoat", 1, "Múi giờ đối soát với sàn", "chu", "", "Asia/Ho_Chi_Minh", None, ""),
    # QĐ634 (B): tên miền riêng, trống = chỉ tên gốc (.env). Đổi ở thẻ Chung qua đường riêng `doi_tenmien` (chỉ Chủ,
    # mật khẩu + mã 02 lớp) – không hiện ở ngăn Thông số. Không có giá trị khởi tạo.
    ("tenmien_rieng", 1, "Tên miền riêng", "chu", "", None, None, ""),   # nhãn nội bộ (AN_O_THONGSO)
]
# Không sửa ở ngăn Thông số: giá xuất kho chưa cho đổi ở GĐ 1 (bản vẽ đợt 1); nhịp lấy đặt từng loại ở màn 11.
KHONG_SUA = {"phuongphap_giaxuat": "Chưa cho đổi ở GĐ 1", "nhip_lay_dulieu": "Đặt ở mục Nguồn dữ liệu",
             "nguong_tien_ai_tuapdung": "Từ GĐ 2"}
# Thông số của phần làm ở giai đoạn sau: hiện mờ, không tính vào số đã đặt / tổng (GĐ 1 AI chỉ đề xuất, thẻ duyệt
# gửi cho mọi việc chờ; luồng Giám đốc sản phẩm quyết 20:55 ngày 21/11/2026).
GIAIDOAN_SAU = {"nguong_tien_ai_tuapdung"}
THEO_TEN = {d[0]: d for d in DANHMUC}
# QĐ278 (Z21 dòng 1): thông số gạt công tắc, đổi có hiệu lực ngay trong ngày (không qua hộp "Sửa" chọn ngày áp dụng)
CONG_TAC = {"saoluu_drive", "tunang_congcu_ai", "anh_ai_giu_dau_c2pa"}   # + QĐ627 (3)
AN_O_THONGSO = {"tunang_congcu_ai",   # công tắc đặt ở chỗ khác theo bản vẽ (Z20: khối Công cụ AI màn Cập nhật)
                "muigio", "muigio_doisoat",   # QĐ636: đặt ở thẻ Chung
                "tenmien_rieng",              # QĐ634: đặt ở thẻ Chung
                "anh_ai_giu_dau_c2pa"}        # QĐ627 (3): đặt ở thẻ Chung
GIAI_THICH = {"saoluu_drive": "Tắt khi đang phát triển. Khi dùng thật, bật và nối Drive."}   # QĐ278 Z21 dòng 1
# QĐ390 (phương án A, CDA 16g), SOAT-KH090 (a): cờ "Đăng nhập 02 lớp" là thông số hệ thống P01, không nằm trong DANHMUC
# (không hiện ở ngăn Thông số, không đếm vào số đã đặt). Chỉ đổi qua 02 đường riêng /api/2lop/tat, /api/2lop/bat và lệnh
# datlai, ghi bằng 01 hàm `ghi_co_2lop`; `dat()`, `gat()` (đường sửa chung, đường gạt chung) từ chối mọi tên trong tập này.
CO_2LOP = "dangnhap_2lop"
CHI_DUONG_RIENG = {CO_2LOP, "muigio", "muigio_doisoat",   # QĐ636: múi giờ chỉ đổi qua `doi_muigio`
                   "tenmien_rieng"}                         # QĐ634: tên miền chỉ đổi qua `doi_tenmien`


def _hom_nay() -> str:
    return muigio.hom_nay()   # ② QĐ636


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
                       (maso.tao(), ten, macdinh, kieu, donvi, _hom_nay(), muigio.gio_luu()))
            them += 1
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return them


# Thông số hệ thống, không hiện ở màn Cài đặt (PTD-06 mục 10): mốc đọc chuông (QĐ165). 01 mốc cho cả hệ thống,
# chỉ đúng khi có 01 người dùng; có nhân viên thì thay bằng bảng "Đã đọc" (bước 2, GĐ 2).
MOC_DOC = "moc_doc_chuong"


def doc_moc_doc(thumuc: Path | None = None) -> str | None:
    """Thời điểm bấm "Đọc hết" gần nhất (giờ Việt Nam), chưa bấm lần nào thì None."""
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        d = cn.execute("SELECT giatri FROM thongso WHERE ten = ? AND congty_id IS NULL AND hieuluc_den IS NULL"
                       " ORDER BY tao_luc DESC, rowid DESC LIMIT 1", (MOC_DOC,)).fetchone()
    finally:
        cn.close()
    return d[0] if d and d[0] else None


def dat_moc_doc(nguoi: str = "hethong", thumuc: Path | None = None, luc: datetime | None = None) -> str:
    """Bấm "Đọc hết": thêm 01 dòng P01 giá trị = lúc bấm, đóng `hieuluc_den` dòng đang dùng (thiết kế P01: không sửa
    dòng cũ). Không đổi trạng thái cảnh báo D03 (QĐ165)."""
    aibam.kiem(nguoi)
    bay = muigio.gio_luu(luc)
    ngay = muigio.ngay_cua(bay, thumuc)   # ② QĐ636 (CDA 5.5)
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cn.execute("UPDATE thongso SET hieuluc_den = ? WHERE ten = ? AND congty_id IS NULL AND hieuluc_den IS NULL",
                   (ngay, MOC_DOC))
        cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, donvi, hieuluc_tu, nguoi_dat, ghichu, tao_luc)"
                   " VALUES (?, ?, ?, 'chu', '', ?, ?, 'Bấm Đọc hết ở chuông', ?)",
                   (maso.tao(), MOC_DOC, bay, ngay, nguoi, bay))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return bay


def _dong_dang_dung(cn, ten: str, ngay: str):
    return cn.execute("SELECT id, giatri, hieuluc_tu, nguoi_dat FROM thongso WHERE ten = ? AND congty_id IS NULL"
                      " AND hieuluc_tu <= ? AND (hieuluc_den IS NULL OR hieuluc_den > ?) ORDER BY hieuluc_tu DESC, tao_luc DESC, rowid DESC LIMIT 1",
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
        for ten, nhom, nhan, kieu, donvi, _m, lua, trong in (x for x in DANHMUC if x[0] not in AN_O_THONGSO):
            d = _dong_dang_dung(cn, ten, ngay)
            sap = cn.execute("SELECT giatri, hieuluc_tu FROM thongso WHERE ten = ? AND congty_id IS NULL AND hieuluc_tu > ?"
                             " ORDER BY hieuluc_tu LIMIT 1", (ten, ngay)).fetchone()
            gt = d[1] if d else None
            ds.append({"ten": ten, "nhom": NHOM[nhom], "nhan": nhan, "kieu": kieu, "donvi": donvi,
                       "giatri": gt, "giatri_chu": (lua or {}).get(gt, gt) if gt is not None else None,
                       "hieuluc_tu": d[2] if d else None, "nguoi_dat": d[3] if d else None,
                       "luachon": [{"giatri": k, "chu": v} for k, v in (lua or {}).items()],
                       "khi_trong": trong, "khong_sua": KHONG_SUA.get(ten),
                       "cong_tac": ten in CONG_TAC, "giai_thich": GIAI_THICH.get(ten), "sap_ap_dung": {"giatri": sap[0], "tu": sap[1]} if sap else None})
    finally:
        cn.close()
    tinh = [x for x in ds if x["ten"] not in GIAIDOAN_SAU]
    return {"thongso": ds, "da_dat": sum(1 for x in tinh if x["giatri"] not in (None, "")), "tong": len(tinh)}


def lich_su(ten: str, thumuc: Path | None = None) -> list[dict]:
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        dong = cn.execute("SELECT giatri, hieuluc_tu, hieuluc_den, nguoi_dat, ghichu FROM thongso WHERE ten = ?"
                          " AND congty_id IS NULL ORDER BY hieuluc_tu DESC, tao_luc DESC, rowid DESC", (ten,)).fetchall()
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


def cong_tac_bat(ten: str, thumuc: Path | None = None) -> bool:
    """Công tắc đang bật? Chưa có dòng nào thì theo mặc định trong DANHMUC."""
    return doc_mot(ten, THEO_TEN[ten][5], thumuc) == "1"


def co_2lop_bat(thumuc: Path | None = None) -> bool:
    """QĐ390 (CDA 16g điều 5): "Đăng nhập 02 lớp" đang bật? Chỉ giá trị "0" là tắt; chưa có dòng, trống, đọc lỗi → bật."""
    try:
        return doc_mot(CO_2LOP, "1", thumuc) != "0"
    except Exception:   # noqa: BLE001 - đọc cờ lỗi thì coi là bật (an toàn hơn)
        return True


def ghi_co_2lop(bat: bool, nguoi: str, ghichu: str, thumuc: Path | None = None) -> dict:
    """01 hàm nội bộ duy nhất ghi cờ 02 lớp (SOAT-KH090 (a)); gọi từ `nguoidung` (tắt, bật lại, bật lần đầu) và `datlai`."""
    aibam.kiem(nguoi)
    return _ghi_gat(CO_2LOP, "1" if bat else "0", nguoi, ghichu, thumuc)


def doi_muigio(ten: str, giatri: str, nguoi: str, thumuc: Path | None = None) -> dict:
    """QĐ636: 01 hàm duy nhất đổi múi giờ (`muigio` hoặc `muigio_doisoat`). Người gọi đã xác minh Chủ + mật khẩu + mã
    02 lớp (`nguoidung.xac_minh_lai`) và kiểm không đang nạp / chốt kỳ. Tên múi lạ thì từ chối. Ghi 01
    dòng P01 mới (dòng cũ đóng, giữ lịch sử – tra được múi lúc chốt kỳ), 01 dòng F04 múi cũ → múi mới. 0 dòng dữ liệu
    viết lại (giờ lưu +07:00 không đổi)."""
    aibam.kiem(nguoi)
    giatri = (giatri or "").strip()
    if ten not in (muigio.TEN, muigio.TEN_DOISOAT):
        return {"loi": "Không có thông số này"}
    if not muigio.kiem_ten(giatri):
        return {"loi": CHU_MUIGIO["ten_la"]}
    cu = doc_mot(ten, muigio.MAC_DINH, thumuc)
    kq = _ghi_gat(ten, giatri, nguoi, "Đổi múi giờ", thumuc)
    muigio.xoa_dem()
    if kq.get("doi"):
        from maychu.hethong import nhatky
        nhatky.ghi("caidat", "doi_muigio", f"{ten}: {cu} → {giatri}", nguoi_id=nguoi if nguoi != "hethong" else None,
                   thumuc=thumuc)
    return kq


def doi_tenmien(giatri: str, nguoi: str, thumuc: Path | None = None) -> dict:
    """QĐ634: 01 hàm duy nhất đổi tên miền riêng. Người gọi đã xác minh Chủ + mật khẩu + mã 02 lớp
    (`nguoidung.xac_minh_lai`). Trống = bỏ tên riêng. Kiểm: máy chủ đã nâng cấu hình, đúng dạng, khác tên gốc
    (`tenmien.kiem_luu`). Ghi 01 dòng P01 mới (dòng cũ đóng, giữ lịch sử) + 01 dòng F04 tên cũ → tên mới."""
    from maychu.hethong.caidat import tenmien
    aibam.kiem(nguoi)
    ten = tenmien.chuan(giatri)
    loi = tenmien.kiem_luu(ten)
    if loi:
        return {"loi": loi}
    cu = tenmien.ten_rieng(thumuc)
    if ten == cu:
        return {"ok": True, "doi": False, "ten": ten}
    kq = _ghi_gat(tenmien.TEN, ten, nguoi, "Bỏ tên miền riêng" if not ten else "Đổi tên miền", thumuc)
    if kq.get("doi"):
        from maychu.hethong import nhatky
        nhatky.ghi("caidat", "doi_tenmien", f"{tenmien.TEN}: {cu or '(trống)'} → {ten or '(trống)'}",
                   nguoi_id=nguoi if nguoi != "hethong" else None, thumuc=thumuc)
    return {**kq, "ten": ten}


# Chữ đổi múi giờ – Bổ sung QĐ652 (CDO soạn, CPO áp): hiện bằng dòng báo lỗi chung (Quychuan 5.2, role="alert")
CHU_MUIGIO = {"ten_la": "Chưa đổi được múi giờ: múi vừa chọn không có trên máy chủ. Tải lại trang rồi chọn lại."}


def drive_bat(thumuc: Path | None = None) -> bool:
    """QĐ277: công tắc "Sao lưu Google Drive". Chưa có dòng nào thì coi là TẮT (mặc định thiết kế)."""
    return doc_mot("saoluu_drive", "0", thumuc) == "1"


def gat(ten: str, bat: bool, nguoi: str = "hethong", thumuc: Path | None = None) -> dict:
    """QĐ278: gạt công tắc, có hiệu lực ngay hôm nay. Giữ đúng luật bảng P01 (không xóa dòng cũ): đóng dòng đang dùng
    (`hieuluc_den` = hôm nay) rồi thêm 01 dòng từ hôm nay; gạt nhiều lần trong 01 ngày thì các dòng cũ cùng ngày có
    hieuluc_tu = hieuluc_den (không còn hiệu lực), lịch sử vẫn đủ."""
    aibam.kiem(nguoi)
    if ten in CHI_DUONG_RIENG or ten not in CONG_TAC:   # SOAT-KH090 (a): cờ 02 lớp chỉ đổi qua đường riêng
        return {"loi": "Thông số này không phải công tắc"}
    return _ghi_gat(ten, "1" if bat else "0", nguoi, "Gạt công tắc", thumuc)


def _ghi_gat(ten: str, gt: str, nguoi: str, ghichu: str, thumuc: Path | None) -> dict:
    """Ghi 01 lần gạt (dùng chung cho `gat` và `ghi_co_2lop`): đóng dòng đang dùng, thêm 01 dòng từ hôm nay."""
    ngay = _hom_nay()
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cu = _dong_dang_dung(cn, ten, ngay)
        if cu and cu[1] == gt:
            cn.execute("ROLLBACK")
            return {"ok": True, "doi": False}
        cn.execute("UPDATE thongso SET hieuluc_den = ? WHERE ten = ? AND congty_id IS NULL AND hieuluc_den IS NULL",
                   (ngay, ten))
        d = THEO_TEN.get(ten) or (ten, 1, "", "codong", "")
        cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, donvi, hieuluc_tu, nguoi_dat, ghichu, tao_luc)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (maso.tao(), ten, gt, d[3], d[4], ngay, nguoi, ghichu, muigio.gio_luu()))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return {"ok": True, "doi": True}


def dat(ten: str, giatri: str, hieuluc_tu: str, ghichu: str = "", nguoi: str = "hethong", thumuc: Path | None = None) -> dict:
    """Thêm 01 phiên bản thông số. Ngày áp dụng phải sau ngày bắt đầu của dòng mới nhất (không chồng lấn).
    `nguoi`: "ai bấm" (mã tài khoản F01 hoặc mã máy, QĐ108)."""
    aibam.kiem(nguoi)
    giatri = (giatri or "").strip()
    if ten in CHI_DUONG_RIENG:   # SOAT-KH090 (a): đường sửa chung không đổi được cờ 02 lớp
        return {"loi": "Không có thông số này", "o": "giatri"}
    if ten in KHONG_SUA:
        return {"loi": KHONG_SUA[ten], "o": "giatri"}
    if ten in CONG_TAC:   # CDA Y49b N3: công tắc chỉ đổi bằng gat() (POST /thongso/{ten}/gat), giữ 01 đường ghi
        return {"loi": "Thông số này đổi bằng công tắc", "o": "giatri"}
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
                    muigio.gio_luu()))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return {"ok": True}
