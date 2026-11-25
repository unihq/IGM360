"""Bài kiểm ghim chữ bản 0.8.8 (QĐ371, anh "Duyệt cả gói"; bảng chữ CDO "Câu Có gì mới 0.8.8" CGM-088, bản A):
VERSION, mục THAYDOI 0.8.8 đúng từng ký tự, mục mới đứng đầu (CDA soát mốc 1, SUA-088-1; tiền lệ test_y52, test_n0_chu).
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu088(unittest.TestCase):
    def test_version_va_muc_088_nguyen_van_qd371(self):
        self.assertEqual((GOC / "VERSION").read_text(encoding="utf-8").strip(), "0.8.8")
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.8")
        self.assertEqual(dong[i:i + 8], [
            "## 0.8.8",
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
        self.assertEqual(dong[i + 8], "## 0.8.7")
        self.assertEqual([d for d in dong if d.startswith("## ")][0], "## 0.8.8")   # mục mới ở đầu


if __name__ == "__main__":
    unittest.main()
