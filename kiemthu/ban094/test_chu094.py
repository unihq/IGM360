"""Bài kiểm ghim chữ bản 0.9.4 – bản sửa lỗi LOI-NANGCLI-8 (CPO duyệt nguyên văn THAYDOI, khuôn QĐ270).
Cách ghim mới: số bản >= 0.9.4, ghim nguyên văn mục, mục 0.9.4 đứng trên 0.9.3.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu094(unittest.TestCase):
    def test_version_va_muc_094_nguyen_van(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 9, 4))
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.9.4")
        self.assertEqual(dong[i:i + 5], [
            "## 0.9.4",
            "Tóm tắt: Sửa lỗi nâng công cụ AI không cài được",
            "Nâng dữ liệu: không",
            "- Sửa lỗi nâng công cụ AI luôn dừng ở bước cài đặt do 02 tệp cấu hình npm trùng nhau; "
            "Claude · Code 2.1.332 được thử lại 01 lần.",
            "",
        ])
        self.assertEqual(dong[i + 5], "## 0.9.3")
        self.assertLess(dong.index("## 0.9.4"), dong.index("## 0.9.3"))


if __name__ == "__main__":
    unittest.main()
