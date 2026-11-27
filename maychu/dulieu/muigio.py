"""Múi giờ (0.10.0; QĐ636 – D-a; CDA PTD-20 mục 5, 5.5): 01 thông số chung cho cả phần mềm.

Ba loại giờ:
① Giờ lưu: mọi chuỗi `*_luc` lưu ISO 8601 kèm độ lệch CỐ ĐỊNH `+07:00` (thiết kế mục 0.2) – không đổi theo cài đặt,
  nên mọi câu so, sắp chuỗi giờ (26 `ORDER BY …luc`, 04 so khoảng) vẫn đúng; đổi múi không viết lại dòng nào.
  Chỉ ghi giờ qua `gio_luu()` (hoặc `bay()` khi cần làm phép tính giờ).
② Ngày số liệu: ngày, kỳ, ngày hiệu lực tính theo múi đã chọn qua `ngay_so_lieu()` / `hom_nay()` / `ngay_cua()`.
  Số liệu theo ngày / kỳ lấy từ cột `ky` / ngày đã ghi sẵn, không tính lại từ giờ lưu (kỳ đã chốt không đổi – QĐ43).
③ Giờ hiện và lịch: giờ trên màn, "hôm nay", giờ chạy lịch theo múi đã chọn qua `gio_hien()` / `bay_chon()`.
Thông số P01 `muigio` (mặc định Asia/Ho_Chi_Minh) và `muigio_doisoat` (đối soát với sàn theo giờ sàn). Bài kiểm cấm
lấy giờ, ngày ngoài tệp này (`kiemthu/ban0100/test_muigio.py`, danh sách chỗ được phép).
"""
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from maychu.dulieu import ketnoi

MUIGIO_LUU = timezone(timedelta(hours=7))   # ① chuẩn lưu cố định, không đổi theo cài đặt
MAC_DINH = "Asia/Ho_Chi_Minh"
TEN = "muigio"
TEN_DOISOAT = "muigio_doisoat"
GIAY_DEM = 60   # đệm múi đã đọc; đổi múi làm mới ngay (`xoa_dem`)
_DEM: dict[tuple, tuple[float, object]] = {}
_KHOA = threading.Lock()


def bay() -> datetime:
    """Lúc này, mang độ lệch lưu +07:00 (dùng cho phép tính giờ; ghi xuống thì qua `gio_luu`)."""
    return datetime.now(MUIGIO_LUU)


def gio_luu(luc: datetime | None = None) -> str:
    """Chuỗi giờ để LƯU: ISO giây, độ lệch +07:00. `luc` phải có múi (không múi thì coi là giờ lưu)."""
    luc = luc or bay()
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=MUIGIO_LUU)
    return luc.astimezone(MUIGIO_LUU).isoformat(timespec="seconds")


def tu_so_giay(giay: float) -> str:
    """Số giây tuyệt đối (time.time, mốc của CLI) → chuỗi giờ lưu."""
    return datetime.fromtimestamp(giay, MUIGIO_LUU).isoformat(timespec="seconds")


def kiem_ten(ten: str | None) -> bool:
    """Tên múi hợp lệ: có trong cơ sở múi giờ của máy (ảnh có sẵn – CDA đo 486 múi). Tên lạ thì từ chối.
    Múi mặc định luôn hợp lệ (máy không có cơ sở múi giờ thì dùng +07:00 cố định – `_mac_dinh`)."""
    if ten == MAC_DINH:
        return True
    if not ten or ten not in available_timezones():
        return False
    try:
        ZoneInfo(ten)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _doc_p01(ten: str, thumuc: Path | None) -> str | None:
    """Giá trị đang mở mới nhất của 01 thông số múi giờ (không dùng ngày hiệu lực – tránh vòng lặp với `hom_nay`)."""
    duong = ketnoi.duongdan("Dulieu_Chinh", thumuc)
    if not duong.exists():
        return None
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        d = cn.execute("SELECT giatri FROM thongso WHERE ten = ? AND congty_id IS NULL AND hieuluc_den IS NULL"
                       " ORDER BY tao_luc DESC, rowid DESC LIMIT 1", (ten,)).fetchone()
    except Exception:  # noqa: BLE001 - bảng chưa có (tệp đang tạo): theo mặc định
        return None
    finally:
        cn.close()
    return d[0] if d else None


def _mac_dinh():
    """Asia/Ho_Chi_Minh; máy không có cơ sở múi giờ (Windows không cài tzdata) thì +07:00 cố định – cùng giờ vì Việt
    Nam không đổi giờ theo mùa. Ảnh Linux có sẵn cơ sở múi giờ (CDA đo 486 múi)."""
    try:
        return ZoneInfo(MAC_DINH)
    except (ZoneInfoNotFoundError, ValueError):
        return MUIGIO_LUU


def _vung(ten: str, thumuc: Path | None):
    khoa = (ten, str(thumuc or ketnoi.thumuc_dulieu()))
    with _KHOA:
        d = _DEM.get(khoa)
        if d and time.monotonic() - d[0] < GIAY_DEM:
            return d[1]
    gt = _doc_p01(ten, thumuc)
    vung = ZoneInfo(gt) if gt != MAC_DINH and kiem_ten(gt) else _mac_dinh()
    with _KHOA:
        _DEM[khoa] = (time.monotonic(), vung)
    return vung


def chon(thumuc: Path | None = None):
    """Múi đã chọn (③, ②). Chưa đặt hoặc giá trị hỏng: Asia/Ho_Chi_Minh."""
    return _vung(TEN, thumuc)


def doisoat(thumuc: Path | None = None):
    """Múi đối soát với sàn (PTD-20 mục 5.3 điểm 3)."""
    return _vung(TEN_DOISOAT, thumuc)


# QĐ652 (bảng chữ MGC.a): câu từ chối đổi múi – dùng khi nối mẻ nạp (0.12.0) và chốt kỳ (GĐ 2) vào `ly_do_ban`
CHU_BAN = {"nap": "Chưa đổi được múi giờ: đang nạp dữ liệu ({lo}). Đổi lại khi mẻ nạp xong.",
           "chot": "Chưa đổi được múi giờ: đang chốt kỳ {ky}. Đổi lại khi chốt kỳ xong."}


def ly_do_ban(thumuc: Path | None = None) -> str | None:
    """QĐ636 (CDA 5.3 điểm 5): từ chối đổi múi khi đang có mẻ nạp số liệu hoặc thao tác chốt kỳ. 0.10.0 chưa có bộ nạp
    (0.12.0) và chốt kỳ (GĐ 2) nên luôn rỗng; bản có tính năng nối điều kiện vào đúng hàm này."""
    return None


def danh_sach() -> list[str]:
    """Các múi chọn được (cơ sở múi giờ của máy; ảnh Linux có sẵn). Máy không có cơ sở múi giờ: chỉ múi mặc định."""
    ds = sorted(available_timezones())
    return ds or [MAC_DINH]


def xoa_dem() -> None:
    with _KHOA:
        _DEM.clear()


def bay_chon(thumuc: Path | None = None) -> datetime:
    """Lúc này theo múi đã chọn – dùng cho lịch (giờ chạy sao lưu, kiểm công cụ AI, gửi báo cáo, nhắc)."""
    return datetime.now(chon(thumuc))


def ngay_so_lieu(luc: datetime | None = None, thumuc: Path | None = None) -> date:
    """② Ngày theo múi đã chọn của 01 thời điểm (mặc định lúc này)."""
    luc = luc or bay()
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=MUIGIO_LUU)
    return luc.astimezone(chon(thumuc)).date()


def hom_nay(thumuc: Path | None = None) -> str:
    """② "Hôm nay" (YYYY-MM-DD) theo múi đã chọn."""
    return ngay_so_lieu(None, thumuc).isoformat()


def gio_hien(luc: str | datetime, thumuc: Path | None = None) -> datetime:
    """③ Chuỗi giờ lưu (hoặc thời điểm) → thời điểm theo múi đã chọn, để hiện."""
    if isinstance(luc, str):
        luc = datetime.fromisoformat(luc)
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=MUIGIO_LUU)
    return luc.astimezone(chon(thumuc))


def ngay_cua(luc: str, thumuc: Path | None = None) -> str:
    """② / ③ Ngày (YYYY-MM-DD) theo múi đã chọn của 01 chuỗi giờ lưu; chuỗi chỉ có ngày thì giữ nguyên."""
    return luc[:10] if len(luc) <= 10 else gio_hien(luc, thumuc).date().isoformat()
