"""Bài kiểm ghim chữ bản 0.9.2 – bản sửa lỗi LOI-NANGCLI-3 (CPO đồng ý nguyên văn THAYDOI, khuôn QĐ270).
Cách ghim mới (CPO LOI-NANGCLI-3 (b)): số bản >= 0.9.2, ghim nguyên văn mục, mục 0.9.2 đứng trên 0.9.1 – bản sau không phải sửa bài này.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu092(unittest.TestCase):
    def test_version_va_muc_092_nguyen_van(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 9, 2))
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.9.2")
        self.assertEqual(dong[i:i + 5], [
            "## 0.9.2",
            "Tóm tắt: Sửa lỗi nhật ký nâng công cụ AI",
            "Nâng dữ liệu: không",
            "- Sửa lỗi nâng công cụ AI chưa đạt mà nhật ký không ghi bước nào chưa đạt: nay ghi bước và đoạn cuối câu lỗi "
            "(đã che mã).",
            "",
        ])
        self.assertEqual(dong[i + 5], "## 0.9.1")
        self.assertLess(dong.index("## 0.9.2"), dong.index("## 0.9.1"))


if __name__ == "__main__":
    unittest.main()
