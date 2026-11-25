"""Bài kiểm ghim chữ bản 0.8.9 (QĐ371, anh "Duyệt cả gói"; bảng chữ CDO "Câu Có gì mới 0.8.9" CGM-088, bản A; dời số 0.8.8 → 0.8.9 theo QĐ374, QĐ380):
VERSION, mục THAYDOI 0.8.8 đúng từng ký tự, mục mới đứng đầu (CDA soát mốc 1, SUA-088-1; tiền lệ test_y52, test_n0_chu).
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu089(unittest.TestCase):
    def test_version_va_muc_089_nguyen_van_qd371(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 8, 9))                                    # bản sau giữ mục 0.8.9 nguyên văn (0.8.10, QĐ386)
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.9")
        self.assertEqual(dong[i:i + 8], [
            "## 0.8.9",
            "Tóm tắt: Đăng nhập mới",
            "Nâng dữ liệu: không",
            "- Logo IGM360 mới ở menu bên trái và trang đăng nhập; thẻ trình duyệt và màn hình chính iPhone có biểu tượng IGM360.",
            "- Trang đăng nhập làm mới: nền nhiều lớp có chiều sâu, linh vật chào mừng khi mở trang và đổi động tác khi đang"
            " đăng nhập, khi báo lỗi, khi nhập mã 02 lớp.",
            "- Nút Đăng nhập hiện \"Đang xử lý…\" trong lúc chờ, không bấm lại được; nút xem mật khẩu đổi hình theo lúc hiện"
            " hoặc ẩn mật khẩu.",
            "- Máy đặt giảm chuyển động thì linh vật và nền đứng yên.",
            "",
        ])                                                                        # QĐ371 (CGM-088 bản A), đúng từng ký tự
        self.assertEqual(dong[i + 8], "## 0.8.8")                              # mục bảo mật 0.8.8 (QĐ376) ngay sau
        self.assertLess(dong.index("## 0.8.9"), dong.index("## 0.8.8"))            # mục mới hơn đứng trên (0.8.10 đặt trên 0.8.9)


if __name__ == "__main__":
    unittest.main()
