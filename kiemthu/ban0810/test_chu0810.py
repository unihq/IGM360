"""Bài kiểm ghim chữ bản 0.8.10 – bản sửa lỗi màn Cập nhật (QĐ386; chữ QĐ388, anh "Duyệt A"; bảng chữ CDO CGM-0810):
VERSION, mục THAYDOI 0.8.10 đúng từng ký tự, mục mới đứng đầu, mục ngay sau là 0.8.9.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu0810(unittest.TestCase):
    def test_version_va_muc_0810_nguyen_van_qd388(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 8, 10))                                   # bản sau giữ mục 0.8.10 nguyên văn (0.9.0, QĐ382, QĐ396)
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.10")
        self.assertEqual(dong[i:i + 7], [
            "## 0.8.10",
            "Tóm tắt: Sửa màn Cập nhật",
            "Nâng dữ liệu: không",
            "- Máy lên bản mới hơn bản bạn bấm thì \"Kiểm sau cập nhật\" không còn báo nhầm \"chưa lên đúng bản\", phần tiến độ không còn đứng yên.",
            "- Màn Cập nhật không còn tự tải lại liên tục.",
            "- Sau lần cập nhật như vậy, tự nâng công cụ AI chạy lại bình thường.",
            "",
        ])                                                                        # QĐ388, đúng từng ký tự
        self.assertEqual(dong[i + 7], "## 0.8.9")
        self.assertLess(dong.index("## 0.8.10"), dong.index("## 0.8.9"))            # mục mới hơn đứng trên (0.9.0 đặt trên 0.8.10)


if __name__ == "__main__":
    unittest.main()
