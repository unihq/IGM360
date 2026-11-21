"""Mã dòng ULID: 26 ký tự, không trùng giữa các file, sắp được theo thời gian tạo.

Viết bằng thư viện chuẩn: 48 bit thời gian (mili giây) + 80 bit ngẫu nhiên, mã hoá Crockford base32.
"""
import os
import time

_BANGCHU = "01234" "56789" "ABCDEFGHJKMNPQRSTVWXYZ"


def tao(luc_ms: int | None = None) -> str:
    """Tạo 01 mã ULID mới."""
    ms = int(time.time() * 1000) if luc_ms is None else int(luc_ms)
    if not 0 <= ms < (1 << 48):
        raise ValueError("thời gian ngoài khoảng ULID")
    so = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    kytu = []
    for _ in range(26):
        kytu.append(_BANGCHU[so & 31])
        so >>= 5
    return "".join(reversed(kytu))
