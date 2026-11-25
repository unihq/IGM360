"""Bài kiểm ghim chữ bản 0.8.8 – bản sửa lỗi bảo mật (QĐ374; chữ QĐ376, anh "Duyệt A bỏ \"và bot\""; bảng chữ CDO CGM-BM):
VERSION, mục THAYDOI 0.8.8 đúng từng ký tự, mục mới đứng đầu.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu088BaoMat(unittest.TestCase):
    def test_version_va_muc_088_nguyen_van_qd376(self):
        self.assertEqual((GOC / "VERSION").read_text(encoding="utf-8").strip(), "0.8.8")
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.8")
        self.assertEqual(dong[i:i + 7], [
            "## 0.8.8",
            "Tóm tắt: Tăng bảo mật AI",
            "Nâng dữ liệu: không",
            "- Tăng bảo mật cho công cụ AI: mỗi nơi dùng AI chỉ được dùng đúng công cụ cần cho việc đó.",
            "- AI không nhận mật khẩu và mã quản trị.",
            "- Trò chuyện AI, Gọi thử, việc chạy nền dùng bộ công cụ đã giới hạn.",
            "",
        ])                                                                        # QĐ376, đúng từng ký tự
        self.assertEqual(dong[i + 7], "## 0.8.7")
        self.assertEqual([d for d in dong if d.startswith("## ")][0], "## 0.8.8")   # mục mới ở đầu
        self.assertNotIn("và bot", " ".join(dong[i:i + 7]))                    # QĐ376: bỏ 02 chữ "và bot"


if __name__ == "__main__":
    unittest.main()
