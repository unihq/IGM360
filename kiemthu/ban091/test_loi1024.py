"""Bài kiểm 0.9.1 – LOI-1024-CAIDAT: màn Cài đặt › Thông số ở khổ 1024, cột tên thông số bị co còn 0–2 px, chữ đè lên giá trị.

Gốc lỗi: thẻ nhóm 02 cột (`.luoi2`) chỉ rộng ~340 px; `.ts` không xuống dòng, `.ts-gt` (`flex:none`) và nhãn khóa
(`.khoa-ts` + `.nw`) không co, nên `.ts-ten` (`flex:1;min-width:0`) bị ép về 0. Sửa theo mức CDO chọn (SC-LOI-1024, mức 160):
dòng thông số được xuống dòng, cột tên giữ cơ sở 160 px, cột giá trị luôn dạt phải. Khổ điện thoại giữ quy tắc `.mb` cũ.
Bài này trượt trên main 94496c6 (03 quy tắc cũ), đạt trên bản sửa.
"""
import re
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


def _quy_tac(css: str, chon: str) -> str:
    """Thân 01 quy tắc CSS viết trên 01 dòng, bắt đầu đúng bằng bộ chọn `chon`."""
    m = re.findall(r"(?m)^" + re.escape(chon) + r"\{([^}]*)\}", css)
    if len(m) != 1:
        raise AssertionError(f"{chon}: tìm thấy {len(m)} quy tắc, cần đúng 01")
    return m[0]


class KiemLoi1024(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_dong_thong_so_duoc_xuong_dong(self):
        self.assertIn("flex-wrap:wrap", _quy_tac(self.html, ".ts").split(";"))

    def test_cot_ten_giu_co_so_160(self):
        than = _quy_tac(self.html, ".ts-ten").split(";")
        self.assertIn("flex:1 1 160px", than)
        self.assertIn("min-width:0", than)

    def test_cot_gia_tri_dat_phai(self):
        than = _quy_tac(self.html, ".ts-gt").split(";")
        self.assertIn("margin-left:auto", than)
        self.assertIn("flex:none", than)

    def test_kho_dien_thoai_giu_nguyen(self):
        self.assertEqual(_quy_tac(self.html, ".mb .ts"), "flex-wrap:wrap")
        self.assertEqual(_quy_tac(self.html, ".mb .ts-ten"), "flex-basis:100%")
        self.assertEqual(_quy_tac(self.html, ".mb .ts-gt"), "align-items:flex-start;text-align:left;flex:1")


if __name__ == "__main__":
    unittest.main()
