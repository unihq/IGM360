"""Mở 07 file SQLite đúng cài đặt chung (thiết kế cơ sở dữ liệu mục 0.1).

- Chế độ ghi WAL cho mọi file.
- Độ bền FULL cho Dulieu_Chinh, Ketnoi, Baomat; NORMAL cho 04 file còn lại.
- Chờ file bận 5.000 ms; riêng Viecnen 30.000 ms.
- Bật khoá ngoại trong từng file.
"""
import os
import sqlite3
from pathlib import Path

CAC_FILE = ("Dulieu_Chinh", "Hotho", "Ketnoi", "Viecnen", "Bot", "Nhatky", "Baomat")
# Bản 4 (QĐ229, V3): đếm `type='table'` gồm cả 06 dòng cụm tìm chữ H08 (bảng ảo + 04 bảng phụ + bảng nối) → tổng 124
SO_BANG = {"Dulieu_Chinh": 55, "Hotho": 5, "Ketnoi": 6, "Viecnen": 20, "Bot": 25, "Nhatky": 5, "Baomat": 8}
DO_BEN_FULL = {"Dulieu_Chinh", "Ketnoi", "Baomat"}
CHO_BAN_MS = {"Viecnen": 30000}


def thumuc_dulieu() -> Path:
    return Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))


def duongdan(ten: str, thumuc: Path | None = None) -> Path:
    if ten not in CAC_FILE:
        raise ValueError(f"không có file dữ liệu tên {ten}")
    return (thumuc or thumuc_dulieu()) / f"{ten}.sqlite3"


def cai_dat(cn: sqlite3.Connection, ten: str) -> sqlite3.Connection:
    cn.execute("PRAGMA journal_mode=WAL")
    cn.execute(f"PRAGMA synchronous={'FULL' if ten in DO_BEN_FULL else 'NORMAL'}")
    cn.execute(f"PRAGMA busy_timeout={CHO_BAN_MS.get(ten, 5000)}")
    cn.execute("PRAGMA foreign_keys=ON")
    return cn


def mo(ten: str, thumuc: Path | None = None) -> sqlite3.Connection:
    """Mở 01 file dữ liệu. Giao dịch do người gọi tự mở (BEGIN IMMEDIATE khi ghi)."""
    cn = sqlite3.connect(duongdan(ten, thumuc), isolation_level=None, timeout=CHO_BAN_MS.get(ten, 5000) / 1000)
    return cai_dat(cn, ten)
