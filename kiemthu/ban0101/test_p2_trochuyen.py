"""Bài kiểm 0.10.1 phần P2 – Trò chuyện AI khóa khung (QĐ671 (5), QĐ678 (2), QĐ677; phiếu dựng PD05–PD09).

Máy tính: hàng đầu 56 px ở cả cột hội thoại ([Trò chuyện mới …]) và khung chat ([tên cuộc … cụm 03 nút]); danh sách hội thoại
và vùng tin cuộn riêng, trang không cuộn; ô nhập + chọn mô hình ở khối đáy .tc-day đứng yên; ô "Tìm hội thoại cũ" cao 40 cùng
hàng mục "Trò chuyện AI" ở thanh trái. Điện thoại: khối đáy bám trên thanh tab dưới. Mép nhạt 16 px, nút tròn xuống tin
mới nhất để 0.11.0 (CPO chốt F2).
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from kiemthu.ban0101.test_baihoc_0100 import quy_tac

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)

    def luat(self, chon):
        return " ".join(b for s, b in self.qt if s == chon)

    def test_pd05_hang_dau_56(self):
        self.assertIn('<div class="tc-trai"><div class="tc-hang"><button class="btn btn-chinh rong" data-tc-moi>', self.html)
        h = self.luat("#app:not(.mb) #p08 .tc-hang")
        for x in ("height:56px", "padding:0 10px 0 12px", "gap:8px", "border-bottom:1px solid var(--ke)", "flex:none"):
            self.assertIn(x, h)
        self.assertIn("height:36px", self.luat("#app:not(.mb) #p08 .tc-hang [data-tc-moi]"))
        d = self.luat("#app:not(.mb) #p08 .tc-dau")
        for x in ("height:56px", "padding:0 16px 0 24px", "gap:16px", "flex:none"):
            self.assertIn(x, d)

    def test_pd06_cuon_rieng_trang_khong_cuon(self):
        self.assertIn("overflow:hidden", self.luat("#app:not(.mb) .cuon-trong:has(#p08:not([hidden]))"))
        self.assertIn("min-height:0", self.luat("#app:not(.mb) #p08"))
        ds = self.luat("#app:not(.mb) #p08 #ds-ht")
        for x in ("flex:1", "min-height:0", "overflow-y:auto"):
            self.assertIn(x, ds)
        t = self.luat("#app:not(.mb) #p08 .tc-than")
        for x in ("flex:1", "min-height:0", "overflow-y:auto", "max-width:none", "padding:24px max(24px,calc((100% - 860px)/2))"):
            self.assertIn(x, t)   # cột chữ tin tối đa 860, đặt giữa (CDO PD06)
        self.assertIn("padding:0", self.luat("#app:not(.mb) #p08 .tc-trai"))

    def test_pd07_khoi_day_dung_yen(self):
        h = self.html
        i = h.index('<div class="tc-day">')
        self.assertTrue(i < h.index('<div class="tc-nhap">', i) < h.index('<div class="tc-duoi">', i))
        self.assertIn("flex:none", self.luat(".tc-day"))

    def test_o_go_che_do_toi(self):   # CPO QĐ687 kèm (CDO đo bd069da: Tối ô gõ nền rgb(59,59,59) trên khối rgb(31,33,37))
        t = self.luat(".tc-nhap input")
        for x in ("background:transparent", "color:var(--chu)"):
            self.assertIn(x, t)

    def test_pd08_o_nhap_dien_thoai(self):   # QĐ677 + CDO: nền --khoi, kẻ trên --ke, đệm 8 / 4, trên thanh tab dưới
        t = self.luat(".mb #p08 .tc-day")
        for x in ("position:sticky", "bottom:var(--cao-tab,0px)", "background:var(--khoi)", "border-top:1px solid var(--ke)", "padding:8px 0 4px"):
            self.assertIn(x, t)
        self.assertIn("document.documentElement.style.setProperty('--cao-tab'", self.js)

    def test_pd09_o_tim_cung_hang_tro_chuyen_ai(self):   # QĐ678 (2): 74–114, cao 40
        t = self.luat("#app:not(.mb) #p08 #tc-tim")
        for x in ("height:40px", "margin:9px 12px 6px", "flex:none", "width:auto"):   # width:auto: không tràn mép cột (CPO P2-COT)
            self.assertIn(x, t)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    def test_pd06_vung_cuon_la_tc_than(self):   # bám đáy khi chạy lượt đo đúng vùng tin (vungCuon có sẵn)
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        i = a.index("const vungCuon = ")
        ma = ("const khung = {scrollHeight: 2000, clientHeight: 600}, ct = {scrollHeight: 700, clientHeight: 700};"
              "const document = {scrollingElement: {}}; const S = {xem: 'dt'};"
              "const $ = q => ({'.tc-than': khung, '#app .cuon-trong': ct})[q];" + a[i:a.index("};\n", i) + 3])
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify(vungCuon() === khung));"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout))


if __name__ == "__main__":
    unittest.main()
