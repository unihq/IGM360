"""Bài kiểm 0.10.1 phần P1 – khóa đầu màn (QĐ671 (4), QĐ682, QĐ677; phiếu dựng PD01–PD04).

Máy tính: đầu màn của trang đang mở nằm ở ô #dau-man ngoài vùng cuộn (.cuon-trong), cao 56, mô tả 01 dòng "…";
cụm chuông · âm thanh · chế độ màu ở cuối hàng đầu màn (màn 08: cuối hàng tên cuộc). Điện thoại: đầu màn trả về trang
(cuộn theo nội dung), thanh trên nền đặc, đứng yên. Hành vi chạy đoạn app.js bằng node với DOM giả (0 thư viện).
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from kiemthu.ban0101.test_baihoc_0100 import quy_tac

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"

# DOM giả tối thiểu: phần tử có con, prepend / append chuyển chỗ như trình duyệt
GIA = r"""
class El { constructor(id, lop) { this.id = id; this.lop = lop || ''; this.children = []; this.parentElement = null; this.dataset = {}; this.hidden = false;
    this.classList = {contains: c => this.lop.split(' ').includes(c)}; }
  _bo() { const p = this.parentElement; if (p) p.children.splice(p.children.indexOf(this), 1); }
  prepend(x) { x._bo(); x.parentElement = this; this.children.unshift(x); }
  append(x) { x._bo(); x.parentElement = this; this.children.push(x); }
  querySelector(q) { const lop = q.replace(':scope > .', '').replace('.', ''); const tim = e => { for (const c of e.children) { if (c.classList.contains(lop)) return c;
      if (!q.startsWith(':scope')) { const k = tim(c); if (k) return k; } } return null; }; return tim(this); } }
const S = {xem: 'dt', trang: '13'};
const DOM = {};
const tao = (id, lop, cha) => { const e = new El(id, lop); if (id) DOM['#' + id] = e; if (cha) cha.append(e); return e; };
const vung = tao('vung', 'vung'), tt = tao('', 'thanh-tren', vung), om = tao('dau-man', 'dau-man', vung), ct = tao('', 'cuon-trong', vung);
const vt = tao('', 'vi-tri', tt); const lg = tao('', 'logo');
const p13 = tao('p13', 'trang', ct), d13 = tao('', 'dau-trang', p13), t13 = tao('', 'the', p13);
const p03 = tao('p03', 'trang', ct), d03 = tao('', 'dau-trang', p03);
const p08 = tao('p08', 'trang', ct), tc = tao('', 'tc', p08), tcd = tao('', 'tc-dau', tc);
const $ = q => ({'.vi-tri': vt, 'nav.menu .logo': lg, '.thanh-tren': tt, '#app .vung': vung, '#p08 .tc-dau': tcd})[q] || DOM[q] || null;
const cha = e => e.parentElement ? (e.parentElement.id || e.parentElement.lop) : null;
"""


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)

    def luat(self, chon):
        return " ".join(b for s, b in self.qt if s == chon)

    def test_pd01_o_dau_man_giua_thanh_tren_va_vung_cuon(self):
        h = self.html
        i, j, k = h.index('<header class="thanh-tren">'), h.index('<div class="dau-man" id="dau-man"></div>'), h.index('<div class="cuon-trong">')
        self.assertTrue(i < j < k)
        self.assertIn("datDauMan();", self.js[self.js.index("function ve() {"):self.js.index("function doiViTri() {")])

    def test_pd02_dau_man_56_mo_ta_mot_dong(self):   # QĐ682: cao 56, mô tả 01 dòng cắt "…", icon tròn 36
        o = self.luat("#app:not(.mb) .dau-man")
        for x in ("display:flex", "height:56px", "box-sizing:border-box", "flex:none", "gap:24px"):   # cụm cách nút chính 24 (CDO PD03)
            self.assertIn(x, o)
        self.assertIn("display:none", self.luat("#app:not(.mb) .dau-man[hidden]"))
        mt = self.luat("#app:not(.mb) .dau-man .dau-trang .phu")
        for x in ("white-space:nowrap", "overflow:hidden", "text-overflow:ellipsis"):
            self.assertIn(x, mt)
        self.assertIn("width:36px;height:36px", self.luat("#app:not(.mb) .dau-man .ico-tron"))

    def test_pd03_cum_nut_khong_noi(self):   # cùng G07: không còn luật absolute cũ (QĐ548 B → QĐ671 (4))
        self.assertNotIn("#app:not(.mb) .vung>.vi-tri{position:absolute", self.html)
        self.assertIn("gap:4px", self.luat("#app:not(.mb) .vi-tri"))

    def test_pd04_thanh_tren_dien_thoai(self):   # QĐ677 + CDO: không trôi, nền đặc, kẻ dưới
        self.assertIn("overflow:visible", self.luat("body.dien-thoai #app.mb"))
        t = self.luat("#app.mb .thanh-tren")
        for x in ("background:var(--khoi)!important", "border-bottom:1px solid var(--ke)"):
            self.assertIn(x, t)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        i = a.index("function doiViTri() {")
        cls.ham = a[i:a.index("\n}\n", a.index("function datDauMan() {")) + 3]

    def chay(self, cau):
        r = subprocess.run(["node", "-e", GIA + self.ham + "\nconsole.log(JSON.stringify(" + cau + "));"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_pd01_dau_man_ngoai_vung_cuon(self):
        kq = self.chay("(() => { const kq = []; datDauMan(); kq.push([cha(d13), om.hidden, cha(d03)]);"
                       " S.trang = '03'; datDauMan(); kq.push([cha(d13), cha(d03), om.children.filter(x => x.lop === 'dau-trang').length]);"
                       " S.trang = '08'; datDauMan(); kq.push([cha(d03), om.hidden]);"
                       " S.trang = '13'; datDauMan(); S.xem = 'mb'; datDauMan(); kq.push([cha(d13), om.hidden, p13.children[0] === d13]); return kq; })()")
        self.assertEqual(kq, [["dau-man", False, "p03"],        # máy tính: đầu màn 13 lên ô, màn khác ở nguyên trang
                              ["p13", "dau-man", 1],             # đổi màn: trả đầu màn cũ về đầu trang, ô chỉ chứa 01
                              ["p03", True],                     # màn 08 dùng hàng tên cuộc của khung chat: ô ẩn
                              ["p13", True, True]])              # điện thoại: đầu màn về đầu trang, cuộn theo nội dung

    def test_pd03_cum_nut_cuoi_hang_dau(self):
        kq = self.chay("(() => { const kq = []; datDauMan(); doiViTri(); kq.push(cha(vt), om.children[om.children.length - 1] === vt);"
                       " S.trang = '08'; datDauMan(); doiViTri(); kq.push(cha(vt)); S.xem = 'mb'; datDauMan(); doiViTri(); kq.push(cha(vt)); return kq; })()")
        self.assertEqual(kq, ["dau-man", True, "tc-dau", "thanh-tren"])


if __name__ == "__main__":
    unittest.main()
