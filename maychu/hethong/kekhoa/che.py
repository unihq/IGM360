"""Che mã bí mật trong chữ sắp ghi ra nhật ký, câu lỗi, câu trả lời (PTD-09 Đ3). Không phụ thuộc phần nào khác,
để mọi lớp ghi (F04, câu lỗi cổng AI, câu trả lời API) gọi được mà không vòng nhập."""
import re

# Mã dài hạn gói Claude (`claude setup-token`): tiền tố cố định, phần sau gồm chữ, số, "-", "_"
# LOI-NANGCLI-3: CHANGELOG Claude Code 2.1.332 (self-hosted runner) – mã CLAUDE_CODE_OAUTH_TOKEN có thể là oat02-; che cả
# oat0<số>- (che thêm là an toàn). Chỗ NHẬN mã (madaihan.py) vẫn chỉ oat01- khi chưa có tài liệu chính thức.
MA_DAIHAN_RE = re.compile(r"sk-ant-oat0\d-[A-Za-z0-9_\-]*")
CHE = "sk-ant-oat01-••••"


def che(s):
    """Thay mọi chuỗi giống mã dài hạn bằng dấu che; giữ nguyên kiểu khác chuỗi (None, số)."""
    if not isinstance(s, str) or "sk-ant-oat0" not in s:
        return s
    return MA_DAIHAN_RE.sub(CHE, s)
