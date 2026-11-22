"""Giá trị "ai bấm" cho 54 cột người thao tác (thiết kế mục 0.4, 0.7; QĐ108).

Chỉ nhận `id` tài khoản F01 (mã dòng ULID 26 ký tự) hoặc 01 trong 04 mã máy cố định. Không ghi chữ `anh`,
không ghi tên đăng nhập: F01 nối 01-01 với A18 nên vẫn tra ra người. Mọi chỗ ghi cột "ai bấm" gọi `kiem`.
"""
import re

MA_MAY = ("hethong", "bot", "viecnen", "ai")
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def la_hop_le(giatri) -> bool:
    return isinstance(giatri, str) and (giatri in MA_MAY or bool(_ULID.match(giatri)))


def kiem(giatri) -> str:
    """Trả lại giá trị nếu hợp lệ; sai thì ValueError (không ghi im lặng giá trị lạ)."""
    if not la_hop_le(giatri):
        raise ValueError(f"giá trị 'ai bấm' phải là mã tài khoản hoặc 01 trong {', '.join(MA_MAY)}")
    return giatri
