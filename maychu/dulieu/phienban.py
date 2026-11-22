"""Lớp ghi danh mục có phiên bản (QĐ142, QĐ143; thiết kế mục 0.4, 0.7 quy tắc Q1-Q3).

- 29 bảng có `ma`, `hieuluc_tu`, `phienban` (01 dòng = 01 phiên bản; G15 `quytrinh_lanchay` là bảng sự kiện, không thuộc).
- Khoá bền là `ma`: bắt buộc, không sửa được. Gõ sai thì đóng mã cũ, mở mã mới qua mục Chờ duyệt.
- Cùng 01 mã không chồng lấn khoảng hiệu lực [hieuluc_tu, hieuluc_den) (trống `hieuluc_den` = đang hiệu lực).
  A15 `nhanvien` thêm khoá bền của người là `nguoi_id` (A18): cùng 01 người không chồng lấn.
- Chặn 02 lớp: lớp ghi trong mã (hàm dưới); lưới an toàn trong lược đồ (`ma` NOT NULL, trigger chặn mã trống và
  chặn sửa `ma`, tạo ở `tao_trigger`). Không chồng lấn không làm được bằng ràng buộc nên chỉ ở lớp ghi.
- Mọi lần thêm dòng vào 29 bảng đi qua `them` hoặc `phienban_moi` (bài kiểm quét mã chặn câu ghi thẳng).
"""
import contextlib
import sqlite3
from datetime import date, datetime

from maychu.dulieu import maso
from maychu.dulieu.saoluu import MUIGIO_VN

# Khoá bền thêm ngoài `ma` (không chồng lấn hiệu lực theo cột này). QĐ143: A15 tách phiên bản theo người.
KHOA_THEM = {"nhanvien": ("nguoi_id",)}
# Cột không cho đổi khi sửa tại chỗ hoặc khi mở phiên bản mới (cộng thêm cột ở KHOA_THEM của bảng đó, Y18b).
KHONG_DOI = ("id", "ma")


class LoiPhienBan(ValueError):
    """Ghi sai quy tắc danh mục có phiên bản; thông báo tiếng Việt, không chứa dữ liệu cá nhân ngoài mã."""


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _ngay(gt, ten: str) -> str:
    try:
        return date.fromisoformat(str(gt)).isoformat()
    except (TypeError, ValueError):
        raise LoiPhienBan(f"{ten} phải là ngày dạng năm-tháng-ngày") from None


def _cot(cn: sqlite3.Connection, bang: str) -> list[str]:
    return [r[1] for r in cn.execute(f"PRAGMA table_info({bang})")]


def cac_bang(cn: sqlite3.Connection) -> list[str]:
    """Bảng có phiên bản trong file đang mở (có đủ `ma`, `hieuluc_tu`, `phienban`)."""
    ds = [r[0] for r in cn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                                   " ORDER BY name")]
    return [b for b in ds if {"ma", "hieuluc_tu", "phienban"} <= set(_cot(cn, b))]


def _kiem_bang(cn: sqlite3.Connection, bang: str) -> list[str]:
    cot = _cot(cn, bang)
    if not {"ma", "hieuluc_tu", "phienban"} <= set(cot):
        raise LoiPhienBan(f"bảng {bang} không phải danh mục có phiên bản")
    return cot


@contextlib.contextmanager
def giao_dich(cn: sqlite3.Connection):
    """Dùng giao dịch người gọi đang mở; chưa có thì tự mở BEGIN IMMEDIATE (đọc kiểm và ghi trong cùng 01 giao dịch)."""
    if cn.in_transaction:
        yield
        return
    cn.execute("BEGIN IMMEDIATE")
    try:
        yield
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise


def _chong_lan(cn, bang: str, cot: str, giatri, tu: str, den: str | None, tru_id: str | None = None) -> str | None:
    """`id` dòng cùng giá trị `cot` có khoảng hiệu lực giao [tu, den); không có thì None."""
    sql = (f"SELECT id FROM {bang} WHERE {cot} = ? AND (hieuluc_den IS NULL OR hieuluc_den > ?)"
           " AND (? IS NULL OR COALESCE(hieuluc_tu, '') < ?)")
    thamso = [giatri, tu, den, den]
    if tru_id:
        sql += " AND id <> ?"
        thamso.append(tru_id)
    d = cn.execute(sql + " LIMIT 1", thamso).fetchone()
    return d[0] if d else None


def them(cn: sqlite3.Connection, bang: str, dong: dict) -> str:
    """Thêm 01 dòng phiên bản. Bắt buộc `ma`, `hieuluc_tu`; tự điền `id`, `phienban` (lớn nhất của mã + 1), `tao_luc`.
    Chồng lấn hiệu lực cùng mã (A15: cùng người) thì từ chối. Trả `id`."""
    cot = _kiem_bang(cn, bang)
    dong = dict(dong)
    ma = dong.get("ma")
    if not isinstance(ma, str) or not ma.strip():
        raise LoiPhienBan(f"{bang}: thiếu mã (QĐ142: mã bắt buộc)")
    dong["ma"] = ma.strip()
    tu = _ngay(dong.get("hieuluc_tu"), f"{bang}.hieuluc_tu")
    den = _ngay(dong["hieuluc_den"], f"{bang}.hieuluc_den") if dong.get("hieuluc_den") else None
    if den and den <= tu:
        raise LoiPhienBan(f"{bang} mã {dong['ma']}: ngày hết hiệu lực phải sau ngày bắt đầu")
    dong["hieuluc_tu"], dong["hieuluc_den"] = tu, den
    la = sorted(set(dong) - set(cot))
    if la:
        raise LoiPhienBan(f"{bang}: không có cột {', '.join(la)}")
    with giao_dich(cn):
        if _chong_lan(cn, bang, "ma", dong["ma"], tu, den):
            raise LoiPhienBan(f"{bang} mã {dong['ma']}: chồng lấn khoảng hiệu lực với phiên bản đang có")
        for k in KHOA_THEM.get(bang, ()):
            if dong.get(k) is None:
                raise LoiPhienBan(f"{bang}: thiếu {k}")
            if _chong_lan(cn, bang, k, dong[k], tu, den):
                raise LoiPhienBan(f"{bang}: cùng {k} đã có phiên bản hiệu lực chồng lấn")
            # Khoá bền gắn cố định với mã (Y18b, QĐ143): 01 mã nhân viên chỉ thuộc 01 người, kể cả ở khoảng không chồng lấn.
            if cn.execute(f"SELECT 1 FROM {bang} WHERE ma = ? AND {k} IS NOT ? LIMIT 1", (dong["ma"], dong[k])).fetchone():
                raise LoiPhienBan(f"{bang} mã {dong['ma']}: đã gắn với {k} khác; không đổi {k} của 01 mã")
        if dong.get("phienban") is None:
            lon = cn.execute(f"SELECT max(phienban) FROM {bang} WHERE ma = ?", (dong["ma"],)).fetchone()[0]
            dong["phienban"] = (lon or 0) + 1
        dong.setdefault("id", maso.tao())
        dong.setdefault("tao_luc", _bay_gio())
        ten_cot = list(dong)
        cn.execute(f"INSERT INTO {bang} ({', '.join(ten_cot)}) VALUES ({', '.join('?' for _ in ten_cot)})",
                   [dong[c] for c in ten_cot])
    return dong["id"]


def phienban_moi(cn: sqlite3.Connection, bang: str, ma: str, tu_ngay, thaydoi: dict, nguoi_khai: str) -> str:
    """Đổi nội dung có ngày hiệu lực (thiết kế mục 0.4): đóng phiên bản đang hiệu lực tại `tu_ngay` (phải là phiên bản
    mới nhất), thêm phiên bản kế tiếp cùng mã từ `tu_ngay`, chép cột cũ rồi áp `thaydoi`. Trả `id` mới."""
    cot = _kiem_bang(cn, bang)
    doi = sorted(set(thaydoi) & set(KHONG_DOI + KHOA_THEM.get(bang, ()) + ("hieuluc_tu", "hieuluc_den", "phienban",
                                                                          "tao_luc", "nguoi_khai")))
    if doi:
        raise LoiPhienBan(f"{bang}: không đổi {', '.join(doi)} khi mở phiên bản mới (QĐ142, QĐ143: khoá bền không sửa được)")
    tu = _ngay(tu_ngay, "ngày áp dụng")
    with giao_dich(cn):
        dang = cn.execute(f"SELECT * FROM {bang} WHERE ma = ? AND COALESCE(hieuluc_tu, '') <= ?"
                          " AND (hieuluc_den IS NULL OR hieuluc_den > ?) LIMIT 1", (ma, tu, tu)).fetchone()
        if not dang:
            raise LoiPhienBan(f"{bang} mã {ma}: không có phiên bản hiệu lực ngày {tu}")
        cu = dict(zip(cot, dang))
        if cu["hieuluc_tu"] and cu["hieuluc_tu"] >= tu:
            raise LoiPhienBan(f"{bang} mã {ma}: ngày áp dụng phải sau ngày bắt đầu của phiên bản đang có")
        if cn.execute(f"SELECT 1 FROM {bang} WHERE ma = ? AND COALESCE(hieuluc_tu, '') > ?", (ma, tu)).fetchone():
            raise LoiPhienBan(f"{bang} mã {ma}: đã có phiên bản bắt đầu sau ngày {tu}")
        cn.execute(f"UPDATE {bang} SET hieuluc_den = ? WHERE id = ?", (tu, cu["id"]))
        moi = {c: v for c, v in cu.items() if c not in ("id", "tao_luc")}
        moi.update(thaydoi)
        moi.update(hieuluc_tu=tu, hieuluc_den=cu["hieuluc_den"], phienban=(cu["phienban"] or 0) + 1, nguoi_khai=nguoi_khai)
        return them(cn, bang, moi)


def sua(cn: sqlite3.Connection, bang: str, ma_dong: str, thaydoi: dict) -> None:
    """Sửa tại chỗ 01 dòng (cột không mang nghĩa phiên bản, ví dụ trạng thái). Không cho đổi `id`, `ma`, khoảng hiệu lực."""
    cot = _kiem_bang(cn, bang)
    cam = sorted(set(thaydoi) & set(KHONG_DOI + KHOA_THEM.get(bang, ()) + ("hieuluc_tu", "hieuluc_den", "phienban")))
    if cam:
        raise LoiPhienBan(f"{bang}: không sửa {', '.join(cam)} tại chỗ (QĐ142, QĐ143: khoá bền không sửa được)")
    la = sorted(set(thaydoi) - set(cot))
    if la:
        raise LoiPhienBan(f"{bang}: không có cột {', '.join(la)}")
    if not thaydoi:
        return
    with giao_dich(cn):
        so = cn.execute(f"UPDATE {bang} SET {', '.join(f'{c} = ?' for c in thaydoi)} WHERE id = ?",
                        [*thaydoi.values(), ma_dong]).rowcount
        if not so:
            raise LoiPhienBan(f"{bang}: không có dòng cần sửa")


def tim_id(cn: sqlite3.Connection, bang: str, giatri: str, ngay=None, cot: str = "ma") -> str | None:
    """Q3: đổi (khoá bền, ngày) ra `id` phiên bản có hiệu lực ngày đó (mặc định hôm nay, giờ Việt Nam).
    `cot` = `ma`, hoặc `nguoi_id` với A15. Không có phiên bản nào thì None: người gọi báo "Tạm tính · thiếu …",
    không bỏ qua im lặng."""
    _kiem_bang(cn, bang)
    if cot != "ma" and cot not in KHOA_THEM.get(bang, ()):
        raise LoiPhienBan(f"{bang}: {cot} không phải khoá bền")
    n = _ngay(ngay, "ngày") if ngay else datetime.now(MUIGIO_VN).date().isoformat()
    d = cn.execute(f"SELECT id FROM {bang} WHERE {cot} = ? AND COALESCE(hieuluc_tu, '') <= ?"
                   " AND (hieuluc_den IS NULL OR hieuluc_den > ?) ORDER BY phienban DESC LIMIT 1", (giatri, n, n)).fetchone()
    return d[0] if d else None


def tao_trigger(cn: sqlite3.Connection) -> int:
    """Lưới an toàn trong lược đồ cho mọi bảng có phiên bản của file (chạy lại không sao): chặn thêm dòng mã trống
    (NOT NULL không chặn chuỗi rỗng) và chặn sửa `ma`. Trả số trigger mã đang có."""
    for bang in cac_bang(cn):
        cn.execute(f"CREATE TRIGGER IF NOT EXISTS ma__{bang}__trong BEFORE INSERT ON {bang} WHEN trim(NEW.ma) = ''"
                   f" BEGIN SELECT RAISE(ABORT, '{bang}.ma: mã không được trống (QĐ142)'); END")
        cn.execute(f"CREATE TRIGGER IF NOT EXISTS ma__{bang}__khoa BEFORE UPDATE OF ma ON {bang} WHEN NEW.ma IS NOT OLD.ma"
                   f" BEGIN SELECT RAISE(ABORT, '{bang}.ma: không sửa mã (QĐ142); đóng mã cũ, mở mã mới qua mục Chờ duyệt'); END")
    return cn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'ma\\_\\_%' ESCAPE '\\'").fetchone()[0]


def dem_ma_trong(cn: sqlite3.Connection) -> dict[str, int]:
    """{bảng: số dòng mã trống} của file đang mở (chỉ bảng có dòng trống). Dùng trước khi nâng bản 3."""
    kq = {}
    for bang in cac_bang(cn):
        so = cn.execute(f"SELECT count(*) FROM {bang} WHERE ma IS NULL OR trim(ma) = ''").fetchone()[0]
        if so:
            kq[bang] = so
    return kq
