"""Băm mật khẩu bằng scrypt có sẵn trong Python (không thêm thư viện)."""
import base64
import hashlib
import hmac
import secrets

N, R, P = 2 ** 15, 8, 1
# QĐ90: không quy định độ dài mật khẩu, chỉ chặn ô trống


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def bam(matkhau: str) -> str:
    muoi = secrets.token_bytes(16)
    h = hashlib.scrypt(matkhau.encode(), salt=muoi, n=N, r=R, p=P, maxmem=64 * 1024 * 1024, dklen=32)
    return f"scrypt${N}${R}${P}${_b64(muoi)}${_b64(h)}"


def kiem(matkhau: str, chuoi: str | None) -> bool:
    try:
        ten, n, r, p, muoi, h = (chuoi or "").split("$")
        if ten != "scrypt":
            return False
        tinh = hashlib.scrypt(matkhau.encode(), salt=base64.b64decode(muoi), n=int(n), r=int(r), p=int(p),
                              maxmem=64 * 1024 * 1024, dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(tinh, base64.b64decode(h))


def loi_matkhau_moi(moi: str, nhap_lai: str) -> str | None:
    """Trả về câu lỗi (lời thường) hoặc None khi mật khẩu mới dùng được."""
    if moi != nhap_lai:
        return "Hai lần nhập mật khẩu mới không khớp"
    if not moi:
        return "Mật khẩu mới không được để trống"
    return None
