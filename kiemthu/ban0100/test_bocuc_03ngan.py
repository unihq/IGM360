"""Bài kiểm 0.10.0 – bố cục 03 ngăn Tài khoản, Cập nhật (bản DM-03NGAN-0100): QĐ658 Tài khoản 1440 03 khối 01 hàng,
1024 và 390 01 cột; QĐ659 nút "Kiểm tra lại" trong thẻ; QĐ660 Công cụ AI 1440 bảng 05 cột, 1024 và 390 danh sách."""

import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemBoCuc(unittest.TestCase):
    def setUp(self):
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_qd658_tai_khoan(self):
        self.assertIn("#app:not(.mb) .cd-than .luoi-tk{grid-template-columns:minmax(0,1fr)}", self.h)
        self.assertIn("@media (min-width:1200px){#app:not(.mb) .cd-than .luoi-tk{grid-template-columns:repeat(3,minmax(0,1fr))}", self.h)
        # nút "Đổi mật khẩu" nằm dưới chữ (trong khối chữ) như nút "Đổi máy nhận mã"
        self.assertIn('<span id="mk-luc"></span></div><button class="btn btn-phu" data-mo="h-matkhau" style="margin-top:10px">', self.h)

    def test_qd659_nut_trong_the(self):
        i = self.h.index('<div class="the cn" data-s="cn:moinhat">')
        the = self.h[i:self.h.index('<div class="the cn" data-s="cn:coban">', i)]
        self.assertIn('<div class="cn-nut"><button class="btn btn-phu" data-kiemtra>', the)
        self.assertIn("#p09 .the.cn>.cn-nut{grid-column:2;flex-direction:row;", self.h)   # hẹp: nút dưới chữ, trong thẻ

    def test_qd660_cong_cu_ai(self):
        self.assertIn(".cl-hang.cl5{grid-template-columns:140px 1fr 1fr 1fr 120px}", self.h)   # ≥ 1200: bảng 05 cột giữ
        i = self.h.index("@media (max-width:1199px){\n #p09 .the.cn")
        doan = self.h[i:self.h.index("\n}\n", i)]
        for x in ("#khoi-cl .cl-hang.tieu-de{display:none}", "#khoi-cl .cl-hang.cl5>.phai{grid-column:2;grid-row:1;",
                  "#khoi-cl .cl-hang.cl5>[data-l]::before{content:attr(data-l) \" \";display:inline;"):
            self.assertIn(x, doan, x)   # danh sách: "Về bản trước" ở đầu khối, nhãn đứng trước số


if __name__ == "__main__":
    unittest.main()
