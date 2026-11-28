"""Bài kiểm 0.10.1 phần P3 – kéo độ rộng và thu gọn cột hội thoại (QĐ426, QĐ427, QĐ672; Quychuan dòng 418; phiếu dựng
PD10, PD11; CDA SOAT-PD0101-CDA: khóa trình duyệt, giá trị hỏng về mặc định).

Độ rộng: nhỏ nhất 240, mặc định 260, lớn nhất 420 và luôn chừa khung chat ≥ 480 (khe 08); phím ← / → 16 px; bấm đúp về 260;
nhớ ở khóa igm360_tc_cot (số px). Thu gọn: dải 56 px còn 03 nút; nhớ ở khóa igm360_tc_thu "1" / "0", giá trị lạ coi là mở.
Trạng thái đặt trên #p08 (không trên #app – app.className bị ve() ghi đè, bài G09). Chỉ máy tính.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from kiemthu.ban0101.test_baihoc_0100 import quy_tac

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


def khoi_cot(a):
    return a[a.index("// <COTHT>"):a.index("// </COTHT>")]


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)

    def luat(self, chon):
        return " ".join(b for s, b in self.qt if s == chon)

    def test_pd10_vach_keo(self):
        self.assertIn('<div class="tc-vach" role="separator" aria-orientation="vertical" tabindex="0"', self.html)
        v = self.luat("#app:not(.mb) #p08 .tc-vach")
        for x in ("display:block", "position:absolute", "left:var(--tc-cot,260px)", "width:8px", "cursor:col-resize"):
            self.assertIn(x, v)
        g = self.luat("#app:not(.mb) #p08 .tc-vach::after")
        for x in ("left:3px", "width:2px", "border-radius:1px"):   # CDO PD10: vạch 2 px, bo 1, giữa khe 08
            self.assertIn(x, g)
        self.assertIn("background:var(--xanh)", self.luat("#app:not(.mb) #p08 .tc-vach:hover::after,#app:not(.mb) #p08 .tc-vach.keo::after,#app:not(.mb) #p08 .tc-vach:focus-visible::after"))
        self.assertIn("width:var(--tc-cot,260px)", self.luat("#app:not(.mb) #p08 .tc-trai"))
        self.assertIn("display:none", self.luat(".tc-vach"))   # điện thoại: không có mép kéo

    def test_pd11_dai_thu_gon(self):
        self.assertIn('<button class="tc-nut" data-tc-thu>', self.html)
        i = self.html.index('<div class="tc-dai">')
        dai = self.html[i:self.html.index('<div class="tc-giua">', i)]   # dải nằm cuối cột hội thoại
        for x in ("data-tc-mo", "data-tc-moi", "data-tc-timdai"):
            self.assertIn(x, dai)
        self.assertIn("width:56px", self.luat("#app:not(.mb) #p08.thu-cot .tc-trai"))
        self.assertIn("display:none", self.luat("#app:not(.mb) #p08.thu-cot .tc-trai>:not(.tc-dai)"))
        self.assertIn("display:flex", self.luat("#app:not(.mb) #p08.thu-cot .tc-dai"))
        self.assertIn("height:56px", self.luat(".tc-dai-dau"))
        self.assertIn("ICON['panel-left-open']", self.js)

    def test_pd11_chu_da_duyet_het_tam(self):   # QĐ686, QĐ687, QĐ455: 04 chữ đã duyệt, P3 hết chữ TẠM
        k = khoi_cot(self.js)
        for x in ("thu: 'Thu gọn cột'", "mo: 'Mở lại cột'", "keo: 'Kéo đổi độ rộng danh sách'", "tim: 'Tìm hội thoại cũ'"):
            self.assertIn(x, k)
        self.assertNotIn("Hiện lịch sử", k)   # QĐ686 thay "Hiện lịch sử" (QĐ571) cho nút mở lại cột
        self.assertNotIn("TẠM", k)
        for x in ("Thu gọn cột", "Mở lại cột", "Tìm hội thoại cũ", "Kéo đổi độ rộng danh sách"):   # chữ trọn trong dấu nháy, 01 chỗ (CHU_COT)
            self.assertEqual(self.js.count("'" + x + "'"), 1, x)
        for x in ("Thu gọn cột", "Mở lại cột", "Kéo đổi độ rộng danh sách"):   # nhãn gắn bằng ganChuCot(), không viết sẵn ở HTML
            self.assertNotIn('"' + x + '"', self.html)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = khoi_cot((GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n"))

    def chay(self, truoc, cau):
        ma = ("const kho = {}; let chan = false; const localStorage = {getItem: k => { if (chan) throw new Error('chặn'); return k in kho ? kho[k] : null; },"
              " setItem: (k, v) => { if (chan) throw new Error('chặn'); kho[k] = String(v); }};"
              "const lop = new Set(); const p08 = {style: {setProperty: (k, v) => { p08.bien = v; }}, classList: {toggle: (c, b) => b ? lop.add(c) : lop.delete(c)}};"
              "const $ = q => null; const S = {xem: 'dt', trang: '08'}; const document = {addEventListener() {}}; const window = {addEventListener() {}};\n" + self.k + "\n" + truoc + "\nconsole.log(JSON.stringify(" + cau + "));")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_pd10_kep_cot(self):
        kq = self.chay("", "[kepCot(100, 1200), kepCot(600, 1600), kepCot(600, 760), kepCot(300, 1600), kepCot(260, 700)]")
        self.assertEqual(kq, [240, 420, 272, 300, 240])   # 760: 760 − 08 − 480 = 272; khung quá hẹp thì giữ 240

    def test_pd10_luu_cot(self):
        kq = self.chay("", "[kepCot(null, 1600), kepCot('', 1600), kepCot('abc', 1600), kepCot('9999', 1600), kepCot('100', 1600),"
                           " (luuCot(312), kho.igm360_tc_cot), docCot(), (chan = true, luuCot(330), docCot())]")
        self.assertEqual(kq, [260, 260, 260, 420, 240, "312", "312", None])   # máy chặn lưu: không lỗi, đọc về rỗng → 260

    def test_pd11_thu_cot(self):
        kq = self.chay("", "[(datThu(true, p08), kho.igm360_tc_thu), lop.has('thu-cot'), docThu(), (datThu(false, p08), kho.igm360_tc_thu),"
                           " lop.has('thu-cot'), docThu()]")
        self.assertEqual(kq, ["1", True, True, "0", False, False])

    def test_pd11_gia_tri_la(self):
        kq = self.chay("", "[(kho.igm360_tc_thu = 'x', docThu()), (kho.igm360_tc_thu = '2', docThu()), (kho.igm360_tc_thu = '', docThu()),"
                           " (chan = true, docThu())]")
        self.assertEqual(kq, [False, False, False, False])


if __name__ == "__main__":
    unittest.main()
