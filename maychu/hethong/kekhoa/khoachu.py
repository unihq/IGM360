"""Khóa chủ của két khóa: 01 tệp quyền 600 trong ổ dữ liệu (QĐ89 điểm B4, làm ở ngày 04).

Tệp không nằm trong bản sao lưu 07 file; anh giữ thêm 01 bản riêng (lệnh chép ở kế hoạch GĐ 1 Phần 4).
Mất tệp này thì không giải mã được khóa đã cất: phải nhập lại khóa và bật lại 02 lớp.
"""
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from maychu.dulieu import ketnoi

TEN_TEP = ".khoa_chu"


def duong(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / TEN_TEP


def lay(thumuc: Path | None = None) -> bytes:
    """Đọc khóa chủ; chưa có thì tạo mới (chỉ 01 lần, quyền 600, không bao giờ ghi đè)."""
    p = duong(thumuc)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return p.read_bytes().strip()
        with os.fdopen(fd, "wb") as f:
            f.write(Fernet.generate_key())
    return p.read_bytes().strip()


def ma_hoa(du_lieu: bytes, thumuc: Path | None = None) -> bytes:
    return Fernet(lay(thumuc)).encrypt(du_lieu)


def giai_ma(ban_ma: bytes, thumuc: Path | None = None) -> bytes:
    try:
        return Fernet(lay(thumuc)).decrypt(ban_ma)
    except InvalidToken as loi:
        raise RuntimeError("khóa chủ không khớp: không giải mã được khóa đã cất") from loi
