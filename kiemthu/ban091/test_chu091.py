"""Bài kiểm ghim chữ bản 0.9.1 – bản sửa lỗi (QĐ577, anh "A. Phát hành ngay"; chữ THAYDOI CPO đồng ý PH-091):
VERSION 0.9.1, mục THAYDOI 0.9.1 đúng từng ký tự, mục mới đứng đầu, mục ngay sau là 0.9.0.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu091(unittest.TestCase):
    def test_version_va_muc_091_nguyen_van(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 9, 1))                                    # bản sau giữ mục 0.9.1 nguyên văn (0.9.2, LOI-NANGCLI-3)
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.9.1")
        self.assertEqual(dong[i:i + 6], [
            "## 0.9.1",
            "Tóm tắt: Sửa ô mật khẩu, màn Thông số",
            "Nâng dữ liệu: không",
            "- Ô mật khẩu: hình con mắt cho biết mật khẩu đang ẩn (mắt gạch chéo) hay đang hiện (mắt mở).",
            "- Cài đặt › Thông số trên cửa sổ hẹp: tên thông số không còn bị chữ đè; giá trị và nút Sửa luôn nằm bên phải, "
            "không bị tràn hay cắt.",
            "",
        ])                                                                        # PH-091, đúng từng ký tự
        self.assertEqual(dong[i + 6], "## 0.9.0")
        self.assertLess(dong.index("## 0.9.1"), dong.index("## 0.9.0"))             # mục mới hơn đứng trên (0.9.2 đặt trên 0.9.1)


if __name__ == "__main__":
    unittest.main()
