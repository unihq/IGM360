"""Danh sách giá trị mở rộng được (thiết kế mục 0.6; QĐ68 khởi tạo; QĐ109 L03 trigger).

- 20 thông số `ds_<tên>` ở P01, kiểu `danhsach`, `giatri` là mảng JSON. Thêm giá trị = thêm phiên bản thông số,
  không đổi cấu trúc bảng. Không hiện ở ngăn Thông số màn 09 (bản vẽ đợt 1 chỉ có 13 thông số).
- Kiểm 02 lớp: lớp 1 ở lớp ghi trong mã (`kiem`); lớp 2 là trigger trước khi thêm, sửa cho bảng nằm cùng file
  `Dulieu_Chinh` với P01 (SQLite không cho CHECK đọc bảng khác; trigger không đọc được file gắn thêm, nên bảng ở
  `Hotho`, `Ketnoi`, `Bot` chỉ kiểm ở lớp 1). Giá trị bị bỏ khỏi danh sách thì dòng cũ vẫn giữ, chỉ chặn ghi mới.
- Mục chứa `*` là mẫu (GLOB): `file_*` khớp `file_donhang`… (thiết kế ghi `file_<loại>` cho A10 `nguon`).
"""
import json
import sqlite3
from datetime import datetime

from maychu.dulieu import maso
from maychu.dulieu.saoluu import MUIGIO_VN

# Giá trị khởi tạo theo thiết kế mục 0.6 (danh sách trống: chờ anh duyệt hoặc lấy theo nguồn khi nối).
KHOITAO = {
    "ds_thitruong": ["VN", "MY"],
    "ds_tien": ["VND", "MYR"],
    "ds_loai_kenh": ["tiktokshop", "shopee", "trangbanhang", "tructiep", "khac"],
    "ds_nguon_mangoai": ["tiktokshop", "shopee", "pancake", "file_*", "zalo", "telegram", "whatsapp", "mail"],
    "ds_loai_gia_tygia": ["mua_chuyenkhoan", "ban"],
    "ds_nguon_tygia": ["VCB", "nhaptay"],
    "ds_nhom_khoanchi": ["banhang", "quanly", "khuyenmai", "tonthat", "khac"],
    "ds_nhom_lydo_shopchet": [],
    "ds_nguon_ketnoi": ["pancake", "tiktokshop", "shopee", "tiktok_quangcao"],
    "ds_loai_vanban": ["uyquyen", "vipham", "nhanhieu", "hoadon", "baogia", "khac"],
    "ds_loai_loi_cuacho": ["file_la", "thieu_ma", "ghep_ma", "lech_soluong", "lech_ton", "xungdot_sua", "vanban_choduyet", "khac"],
    "ds_loai_chiphimua": ["ship_noidia", "ship_quocte", "thue", "thongquan", "khac"],
    "ds_loai_giaodich_tien": ["tien_san_ve", "tra_ncc", "nap_quangcao", "chi_chung", "luong", "coc", "khac"],
    "ds_khoan_tiensan": ["doanhthu", "phi_san", "phi_thanhtoan", "phi_vanchuyen", "dieuchinh", "khac"],
    "ds_chiso_shop": [],
    "ds_cach_phanbo_chiphi": ["theo_doanhthu", "theo_don", "chia_deu", "chidinh"],
    "ds_loai_hoso": ["uyquyen", "vipham", "nhanhieu"],
    "ds_donvi_vanchuyen": [],
    "ds_kenh_nhan": ["telegram", "zalo", "mail", "whatsapp"],
    "ds_loai_nguoi": ["anh", "nhanvien", "khach"],
}

# Cột → thông số cho bảng trong Dulieu_Chinh (lớp 2). Cột chung số liệu (nhóm C có `thitruong`) thêm tự động.
ANH_XA = {
    "ds_thitruong": [("shop", "thitruong"), ("khuvuc", "thitruong")],
    "ds_tien": [("congty", "tien_goc"), ("shop", "tien_ma"), ("taikhoan", "tien_ma"), ("nhacungcap", "tien_ma")],
    "ds_loai_kenh": [("kenh", "loai")],
    "ds_nguon_mangoai": [("ghep_mangoai", "nguon")],
    "ds_loai_gia_tygia": [("tygia_ngay", "loai_gia")],
    "ds_nguon_tygia": [("tygia_ngay", "nguon"), ("tygia_quantri", "nguon")],
    "ds_nhom_khoanchi": [("khoanchi", "nhom")],
    "ds_nhom_lydo_shopchet": [("lydo_shopchet", "nhom")],
    "ds_loai_loi_cuacho": [("cuacho", "loai_loi")],
    "ds_loai_chiphimua": [("chiphimua", "loai")],
    "ds_loai_giaodich_tien": [("giaodich_tien", "loai")],
    "ds_khoan_tiensan": [("tien_trensan", "khoan")],
    "ds_chiso_shop": [("chiso_shop", "ma_chiso")],
    "ds_cach_phanbo_chiphi": [("chiphi_chung", "cach_phanbo")],
    "ds_loai_hoso": [("hoso_phaply", "loai")],
    "ds_donvi_vanchuyen": [("vandon", "donvi_vanchuyen"), ("doisoat_cod", "donvi_vanchuyen")],
    "ds_loai_nguoi": [("nguoi", "loai")],
}

# Điều kiện "dòng thông số đang áp dụng hôm nay" (giờ Việt Nam, như thongso.py).
_DANG_DUNG = ("t.congty_id IS NULL AND t.hieuluc_tu <= date('now', '+7 hours')"
              " AND (t.hieuluc_den IS NULL OR t.hieuluc_den > date('now', '+7 hours'))")


def _cot(cn: sqlite3.Connection, bang: str) -> set[str]:
    return {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}


def anh_xa_day_du(cn: sqlite3.Connection) -> dict[str, list[tuple[str, str]]]:
    """ANH_XA cộng cột chung số liệu: bảng nào có `thitruong` thì `thitruong`, `tien_ma` (nếu có) theo danh sách."""
    kq = {ten: list(ds) for ten, ds in ANH_XA.items()}
    bang_ds = [r[0] for r in cn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for bang in bang_ds:
        cot = _cot(cn, bang)
        if "thitruong" in cot and bang not in ("shop", "khuvuc"):
            kq["ds_thitruong"].append((bang, "thitruong"))
            if "tien_ma" in cot:
                kq["ds_tien"].append((bang, "tien_ma"))
    return kq


def khoi_tao(cn: sqlite3.Connection) -> int:
    """Ghi 20 thông số danh sách chưa có dòng nào (chạy lại không sao). Người gọi giữ giao dịch hoặc không."""
    bay = datetime.now(MUIGIO_VN)
    them = 0
    for ten, gt in KHOITAO.items():
        if cn.execute("SELECT 1 FROM thongso WHERE ten = ? AND congty_id IS NULL", (ten,)).fetchone():
            continue
        cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, donvi, hieuluc_tu, nguoi_dat, ghichu, tao_luc)"
                   " VALUES (?, ?, ?, 'danhsach', '', ?, 'hethong', 'Giá trị khởi tạo theo thiết kế mục 0.6', ?)",
                   (maso.tao(), ten, json.dumps(gt, ensure_ascii=False), bay.date().isoformat(), bay.isoformat(timespec="seconds")))
        them += 1
    return them


def tao_trigger(cn: sqlite3.Connection) -> int:
    """Tạo trigger trước khi thêm, sửa cho mọi cột trong ánh xạ (chạy lại không sao). Trả về số trigger đang có."""
    for ten, ds in anh_xa_day_du(cn).items():
        for bang, cot in ds:
            if cot not in _cot(cn, bang):
                raise RuntimeError(f"ánh xạ {ten}: bảng {bang} không có cột {cot}")
            khop = (f"SELECT 1 FROM thongso t, json_each(t.giatri) j WHERE t.ten = '{ten}' AND {_DANG_DUNG}"
                    f" AND (j.value = NEW.{cot} OR (instr(j.value, '*') > 0 AND NEW.{cot} GLOB j.value))")
            loi = f"'{bang}.{cot}: giá trị ngoài danh sách {ten}'"
            cn.execute(f"CREATE TRIGGER IF NOT EXISTS ds__{bang}__{cot}__them BEFORE INSERT ON {bang}"
                       f" WHEN NEW.{cot} IS NOT NULL AND NOT EXISTS ({khop}) BEGIN SELECT RAISE(ABORT, {loi}); END")
            cn.execute(f"CREATE TRIGGER IF NOT EXISTS ds__{bang}__{cot}__sua BEFORE UPDATE OF {cot} ON {bang}"
                       f" WHEN NEW.{cot} IS NOT NULL AND NOT EXISTS ({khop}) BEGIN SELECT RAISE(ABORT, {loi}); END")
    return cn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'ds\\_\\_%' ESCAPE '\\'").fetchone()[0]


def doc(cn: sqlite3.Connection, ten: str) -> list[str]:
    """Danh sách đang áp dụng hôm nay (Dulieu_Chinh)."""
    d = cn.execute(f"SELECT t.giatri FROM thongso t WHERE t.ten = ? AND {_DANG_DUNG} ORDER BY t.hieuluc_tu DESC LIMIT 1",
                   (ten,)).fetchone()
    return json.loads(d[0]) if d and d[0] else []


def kiem(cn: sqlite3.Connection, ten: str, giatri: str | None) -> None:
    """Lớp 1: giá trị phải nằm trong danh sách đang áp dụng (trống thì bỏ qua). Sai thì ValueError."""
    if giatri is None:
        return
    for muc in doc(cn, ten):
        if giatri == muc or ("*" in muc and _glob(giatri, muc)):
            return
    raise ValueError(f"giá trị '{giatri}' ngoài danh sách {ten}")


def _glob(chu: str, mau: str) -> bool:
    import fnmatch
    return fnmatch.fnmatchcase(chu, mau)
