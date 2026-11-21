"""Tạo 07 file dữ liệu và 104 bảng theo lược đồ trong `luocdo/`.

Chạy lại nhiều lần không sao: bảng đã có thì giữ nguyên. Số phiên bản lược đồ ghi ở
PRAGMA user_version của từng file (không thêm bảng phụ).
"""
import os
from pathlib import Path

from maychu.dulieu import ketnoi

PHIENBAN_LUOCDO = 1
THUMUC_LUOCDO = Path(__file__).resolve().parent / "luocdo"


def tao_mot(ten: str, thumuc: Path) -> int:
    """Tạo 01 file; trả về số bảng đang có trong file."""
    duong = ketnoi.duongdan(ten, thumuc)
    moi = not duong.exists()
    cn = ketnoi.mo(ten, thumuc)
    try:
        ban = cn.execute("PRAGMA user_version").fetchone()[0]
        if ban < PHIENBAN_LUOCDO:
            cn.executescript((THUMUC_LUOCDO / f"{ten}.sql").read_text(encoding="utf-8"))
            cn.execute(f"PRAGMA user_version={PHIENBAN_LUOCDO}")
        so = cn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        cn.close()
    if moi:
        os.chmod(duong, 0o600)
    return so


def tao_het(thumuc: Path | None = None) -> dict:
    """Tạo đủ 07 file. Trả về {tên file: số bảng}; lệch thiết kế thì báo lỗi."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    thumuc.mkdir(parents=True, exist_ok=True)
    ketqua = {ten: tao_mot(ten, thumuc) for ten in ketnoi.CAC_FILE}
    lech = {t: (so, ketnoi.SO_BANG[t]) for t, so in ketqua.items() if so != ketnoi.SO_BANG[t]}
    if lech:
        raise RuntimeError(f"số bảng lệch thiết kế: {lech}")
    return ketqua
