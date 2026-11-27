"""Lớp ghi C16 Lương, nhân sự (QĐ143; thiết kế mục 0.7 Q6, PTD-03).

- Không trùng theo (người A18 qua A15, tháng): A15 tách phiên bản (01 người nhiều dòng `nhanvien`), nên khóa là
  `nguoi_id` của dòng A15 mà `nhanvien_id` trỏ tới, không phải `nhanvien_id`. Lược đồ không chặn được (khóa đi qua
  bảng khác), nên chặn ở lớp ghi, đọc kiểm và ghi trong cùng 01 giao dịch BEGIN IMMEDIATE.
- Nạp lại đúng cùng số của người, tháng đã có: trả dòng cũ, không báo lỗi (thiết kế mục 0.7 L02). Khác số: từ chối,
  sửa qua Sổ điều chỉnh C20.
"""
import re
import sqlite3

from maychu.dulieu import muigio
from maychu.dulieu import maso
from maychu.dulieu.phienban import giao_dich

# Cột số so khi nạp lại cùng người, cùng tháng.
COT_SO = ("luong", "thuong", "khac", "tong", "sotien_nguyente", "sotien_quydoi", "tien_ma")
_THANG = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class LoiTrung(ValueError):
    """Đã có lương của người này trong tháng với số khác."""


def ghi_thang(cn: sqlite3.Connection, dong: dict) -> str:
    """Ghi 01 dòng lương (Dulieu_Chinh). Bắt buộc `nhanvien_id`, `thang` dạng năm-tháng. Trả `id` dòng (mới hoặc cũ)."""
    dong = dict(dong)
    thang = dong.get("thang")
    if not isinstance(thang, str) or not _THANG.match(thang):
        raise ValueError("C16: tháng phải dạng năm-tháng, ví dụ 2026-04")
    cot = [r[1] for r in cn.execute("PRAGMA table_info(luong_nhansu)")]
    la = sorted(set(dong) - set(cot))
    if la:
        raise ValueError(f"C16: không có cột {', '.join(la)}")
    with giao_dich(cn):
        nv = cn.execute("SELECT nguoi_id FROM nhanvien WHERE id = ?", (dong.get("nhanvien_id"),)).fetchone()
        if not nv:
            raise ValueError("C16: không có nhân viên này (A15)")
        cu = cn.execute(f"SELECT l.id, {', '.join('l.' + c for c in COT_SO)} FROM luong_nhansu l"
                        " JOIN nhanvien n ON n.id = l.nhanvien_id WHERE n.nguoi_id = ? AND l.thang = ? LIMIT 1",
                        (nv[0], thang)).fetchone()
        if cu:
            if all(dong.get(c) == v for c, v in zip(COT_SO, cu[1:])):
                return cu[0]
            raise LoiTrung(f"C16: người này đã có lương tháng {thang} với số khác; sửa qua Sổ điều chỉnh")
        dong.setdefault("id", maso.tao())
        dong.setdefault("tao_luc", muigio.gio_luu())
        ten_cot = list(dong)
        cn.execute(f"INSERT INTO luong_nhansu ({', '.join(ten_cot)}) VALUES ({', '.join('?' for _ in ten_cot)})",
                   [dong[c] for c in ten_cot])
    return dong["id"]
