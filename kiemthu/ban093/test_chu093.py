"""Bài kiểm ghim chữ bản 0.9.3 – bản sửa lỗi QĐ593 (LOI-NANGCLI-4; CPO duyệt nguyên văn THAYDOI, khuôn QĐ270).
Cách ghim mới (CPO LOI-NANGCLI-3 (b)): số bản >= 0.9.3, ghim nguyên văn mục, mục 0.9.3 đứng trên 0.9.2.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu093(unittest.TestCase):
    def test_version_va_muc_093_nguyen_van(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 9, 3))
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.9.3")
        self.assertEqual(dong[i:i + 5], [
            "## 0.9.3",
            "Tóm tắt: Sửa lỗi nâng công cụ AI khi mạng chập chờn",
            "Nâng dữ liệu: không",
            "- Sửa lỗi nâng công cụ AI bị ghi hỏng vì lỗi mạng hoặc quá giờ: nay hoãn và tự thử lại, tối đa 03 lần; "
            "Claude · Code 2.1.332 được thử lại 01 lần.",
            "",
        ])
        self.assertEqual(dong[i + 5], "## 0.9.2")
        self.assertLess(dong.index("## 0.9.3"), dong.index("## 0.9.2"))


if __name__ == "__main__":
    unittest.main()
