"""Che mã bí mật trong chữ sắp ghi ra nhật ký, câu lỗi, câu trả lời (PTD-09 Đ3). Không phụ thuộc phần nào khác,
để mọi lớp ghi (F04, câu lỗi cổng AI, câu trả lời API) gọi được mà không vòng nhập."""
import re

# Mã dài hạn gói Claude (`claude setup-token`): tiền tố cố định, phần sau gồm chữ, số, "-", "_"
MA_DAIHAN_RE = re.compile(r"sk-ant-oat01-[A-Za-z0-9_\-]*")
CHE = "sk-ant-oat01-••••"


def che(s):
    """Thay mọi chuỗi giống mã dài hạn bằng dấu che; giữ nguyên kiểu khác chuỗi (None, số)."""
    if not isinstance(s, str) or "sk-ant-oat01-" not in s:
        return s
    return MA_DAIHAN_RE.sub(CHE, s)
