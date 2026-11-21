"""Mã 02 lớp theo thời gian (RFC 6238: 06 số, bước 30 giây, SHA-1), viết mới bằng thư viện chuẩn.
Học cách làm của mã gốc (totp.py): cho lệch 01 bước, không nhận lại mã của bước đã dùng."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

BUOC_GIAY = 30
SO_CHU_SO = 6


def sinh_khoa() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _giai(khoa: str) -> bytes:
    return base64.b32decode(khoa + "=" * (-len(khoa) % 8), casefold=True)


def buoc(luc: float | None = None) -> int:
    return int((time.time() if luc is None else luc) // BUOC_GIAY)


def ma_cua_buoc(khoa: str, b: int) -> str:
    h = hmac.new(_giai(khoa), struct.pack(">Q", b), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    so = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** SO_CHU_SO
    return f"{so:0{SO_CHU_SO}d}"


def kiem(khoa: str, ma: str, *, buoc_da_dung: int = -1, luc: float | None = None) -> int | None:
    """Đúng thì trả về số bước của mã (để ghi nhớ, không cho dùng lại); sai thì None."""
    ma = "".join(c for c in (ma or "") if c.isdigit())
    if len(ma) != SO_CHU_SO:
        return None
    hien = buoc(luc)
    for b in (hien - 1, hien, hien + 1):
        if b > buoc_da_dung and hmac.compare_digest(ma_cua_buoc(khoa, b), ma):
            return b
    return None


def duong_dan(khoa: str, ten_dangnhap: str) -> str:
    return (f"otpauth://totp/IGM360:{quote(ten_dangnhap)}?secret={khoa}&issuer=IGM360"
            f"&algorithm=SHA1&digits={SO_CHU_SO}&period={BUOC_GIAY}")


def qr_svg(noi_dung: str) -> str:
    import io
    import segno
    ra = io.BytesIO()
    segno.make(noi_dung, error="m").save(ra, kind="svg", scale=5, border=2, dark="#1F2329", xmldecl=False)
    return ra.getvalue().decode()
