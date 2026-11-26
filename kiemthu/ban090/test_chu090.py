"""Bài kiểm ghim chữ bản 0.9.0 (QĐ389 khối A + QĐ397 dòng công tắc 02 lớp; bảng chữ CDO CGM-090-CHOT; CDA 16b điều 16):
VERSION, mục THAYDOI 0.9.0 đúng từng ký tự cả 05 dòng, mục mới đứng đầu, mục ngay sau là 0.8.10; số bản theo QĐ396.
"""
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]


class KiemChu090(unittest.TestCase):
    def test_version_va_muc_090_nguyen_van(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 9, 0))                                    # bản sau giữ mục 0.9.0 nguyên văn (0.9.1, QĐ577; tiền lệ test_chu0810)
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.9.0")
        self.assertEqual(dong[i:i + 9], [
            "## 0.9.0",
            "Tóm tắt: Giao diện mới",
            "Nâng dữ liệu: không",
            "- Các màn trong phần mềm có phông nền xanh nhạt cùng kiểu trang đăng nhập; bảng, số liệu, biểu đồ vẫn nằm trên khối trắng để dễ đọc.",
            "- Trên máy tính: menu bên trái nằm trên phông, mục đang chọn là ô trắng; vùng làm việc thành khung nổi viền mảnh; Trò chuyện AI chia 02 khung: danh sách và hội thoại.",
            "- Chuông và tài khoản chuyển lên ngay dưới logo; bỏ thanh trên cùng, thu gọn menu bằng nút \"Thu gọn menu\" ở cuối menu.",
            "- Cài đặt › Tài khoản và 02 lớp có công tắc tắt, bật đăng nhập 02 lớp: tắt phải nhập mật khẩu và mã 06 số; khi đang tắt, chuông luôn nhắc; bật lại thì mọi máy khác tự đăng xuất.",
            "- Trên điện thoại cũng có phông nền mới.",
            "",
        ])                                                                        # QĐ389 + QĐ397, đúng từng ký tự
        self.assertEqual(dong[i + 9], "## 0.8.10")
        self.assertLess(dong.index("## 0.9.0"), dong.index("## 0.8.10"))             # mục mới hơn đứng trên (0.9.1 đặt trên 0.9.0)

    def test_qd396_quy_uoc_so_ban_ghi_o_agents(self):
        a = (GOC / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- Quy ước số bản (QĐ396): số đầu giữ 0; bản có tính năng mới: +1 số giữa, số cuối về 0", a)


if __name__ == "__main__":
    unittest.main()
