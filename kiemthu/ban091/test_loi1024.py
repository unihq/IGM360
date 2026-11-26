"""Bài kiểm 0.9.1 – LOI-1024-CAIDAT: màn Cài đặt › Thông số ở khổ 1024, cột tên thông số bị co còn 0–2 px, chữ đè lên giá trị.

Gốc lỗi: thẻ nhóm 02 cột (`.luoi2`) chỉ rộng ~340 px; `.ts` không xuống dòng, `.ts-gt` (`flex:none`) và nhãn khóa
(`.khoa-ts` + `.nw`) không co, nên `.ts-ten` (`flex:1;min-width:0`) bị ép về 0. Sửa theo mức CDO chọn (SC-LOI-1024, mức 160):
dòng thông số được xuống dòng, cột tên giữ cơ sở 160 px, cột giá trị luôn dạt phải. Khổ điện thoại giữ quy tắc `.mb` cũ.
Bài này trượt trên main 94496c6 (03 quy tắc cũ), đạt trên bản sửa.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


def _quy_tac(css: str, chon: str) -> str:
    """Thân 01 quy tắc CSS viết trên 01 dòng, bắt đầu đúng bằng bộ chọn `chon`."""
    m = re.findall(r"(?m)^" + re.escape(chon) + r"\{([^}]*)\}", css)
    if len(m) != 1:
        raise AssertionError(f"{chon}: tìm thấy {len(m)} quy tắc, cần đúng 01")
    return m[0]


def _doc(ten: str) -> str:
    return (GD / ten).read_text(encoding="utf-8").replace("\r\n", "\n")


class KiemLoi1024(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = _doc("index.html")

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


class KiemKhoiPhai1024(unittest.TestCase):
    """LOI-1024-NHANH-2 (CDO NT-1024-NHANH, ảnh 212): khi giá trị xuống hàng, nút Sửa / công tắc không được rơi về đầu dòng
    bên trái. Giá trị + nút nằm trong 01 khối `.ts-phai` canh phải (cách CDO thử đạt: 0 dòng rơi trái); điện thoại khối này
    giãn đủ dòng như cũ. Trượt trên 68dc5bb (chưa có khối bọc), đạt trên bản sửa."""

    @classmethod
    def setUpClass(cls):
        cls.html = _doc("index.html")
        cls.app = _doc("app.js")

    def test_khoi_phai_canh_phai(self):
        than = _quy_tac(self.html, ".ts-phai").split(";")
        for x in ("display:flex", "align-items:center", "margin-left:auto"):
            self.assertIn(x, than)

    def test_khoi_phai_dien_thoai_gian_du_dong(self):
        self.assertEqual(_quy_tac(self.html, ".mb .ts-phai"), "flex:1;margin-left:0")

    def test_ca_hai_mau_dong_deu_boc(self):
        ve_ts = self.app[self.app.index("function veThongSo()"):self.app.index("// QĐ278 (Z21 dòng 1–3)")]
        ve_ct = self.app[self.app.index("function veCongTac("):self.app.index("async function gatCongTac")]
        for ma in (ve_ts, ve_ct):
            self.assertEqual(ma.count('<div class="ts-phai"><div class="ts-gt">'), 1)
            self.assertEqual(ma.count('<div class="ts-gt">'), 1)       # mọi giá trị đều nằm trong khối bọc

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_cong_tac_nut_nam_trong_khoi_phai(self):
        ma = self.app[self.app.index("const CHU_Z21 = "):self.app.index("async function gatCongTac")]
        chay = ("const esc = x => String(x), cum = x => String(x), ngay = x => x;\n"
                "const icoMau = () => '<i></i>';\nconst ICON = {'cloud-alert': ''};\n" + ma
                + "console.log(veCongTac({ten: 'saoluu_drive', nhan: 'Sao lưu', giatri: '1', giai_thich: 'x', "
                "hieuluc_tu: '2026-11-24', nguoi_dat: 'hethong'}, {drive_noi: true}));\n")
        h = subprocess.run(["node", "-e", chay], capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()
        self.assertLess(h.index('<div class="ts-phai">'), h.index('<button class="gat-o nut-gat"'))   # công tắc ở trong khối bọc
        self.assertTrue(h.endswith("</button></div></div>"))                # đóng khối bọc rồi mới đóng dòng
        self.assertEqual(h.count("<div"), h.count("</div>"))


if __name__ == "__main__":
    unittest.main()
