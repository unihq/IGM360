"""Bài kiểm 0.10.0 bước 8b – ngăn Thông báo (bản DM-CAIDAT-010; QĐ553 (5), QĐ573 L05, QĐ653 icon bell, QĐ664, QĐ665;
chữ QĐ666 dòng 14 "{n} loại · {k} đang tắt", 15 tên loại, 17 "Luôn báo")."""

import re
import unittest
from pathlib import Path

from maychu.hethong.giamsat import thongbao

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemNganThongBao(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_menu_va_cho_ngan(self):
        self.assertIn("['thongso', 'sliders-horizontal', 'Thông số'], ['thongbao', 'bell', 'Thông báo']", self.js)   # ngay sau Thông số
        self.assertIn('<div data-s="tab:thongbao" class="cot-doc" id="ngan-thongbao"></div>', self.h)
        self.assertIn("else if (S.tab === 'thongbao') await napThongBaoCd();", self.js)

    def test_du_ten_21_loai_dung_bang_loai(self):
        i = self.js.index("const CHU_TBL = {")
        ten = dict(re.findall(r"(\w+): '([^']+)'", self.js[self.js.index("ten: {", i):self.js.index("}};", i)]))
        self.assertEqual(set(ten), set(thongbao.LOAI))   # mọi loại máy chủ có đều có tên 02–04 tiếng (QĐ666 dòng 15)
        for k, v in {"capnhat_xong": "Cập nhật xong", "tenmien_doi": "Đổi tên miền riêng", "muigio_doi": "Đổi múi giờ",
                     "dangnhap_2lop_tat": "02 lớp đang tắt"}.items():
            self.assertEqual(ten[k], v)

    def test_chu_qd666(self):
        for c in ("dem: (n, k) => hai(n) + ' loại' + (k ? ' · ' + hai(k) + ' đang tắt' : '')", "luon: 'Luôn báo'",
                  "chan: 'Từ GĐ 2: Chỉ số vượt ngưỡng.'"):
            self.assertIn(c, self.js, c)
        self.assertIn("(x.luon ? '<span class=\"tbl-luon\">'", self.js)   # loại đỏ: chữ + khóa, không công tắc
        self.assertIn("api('/thongbao/loai', {loai: x.loai, bat: x.tat})", self.js)
        self.assertIn("ICON['package-check'] = ICON['package-check'] || svgLucide('package-check',", self.js)

    def test_khong_vach_trai_va_dong_dien_thoai(self):
        self.assertIn(".tbl-h{display:flex;align-items:center;gap:12px;padding:8px 4px;min-height:56px}", self.h)
        self.assertIn(".mb .tbl-h{min-height:60px}", self.h)


if __name__ == "__main__":
    unittest.main()
