"""Bài kiểm 0.10.1 phần P4 – thanh trái mới (QĐ671 (1)(2)(3)(6), QĐ674–QĐ676, QĐ678, QĐ684; phiếu PD12–PD17, PD26, PD27).

Thứ tự: logo → "Trò chuyện AI" ghim → khối giữa (QUẢN TRỊ TMĐT · NĂNG LỰC · KẾT NỐI, cuộn riêng) → "Hiện thêm khi tới giai đoạn"
→ HỆ THỐNG → chân (02 dòng "IGM360 {bản}" / "by UNI TECH" + nút panel-left). Icon nhóm bộ A 16 px cùng màu chữ. Thu gọn 68 px:
chân "0.10.1" trên nút. Lưới hàng: logo 12–62, mục ghim 74–114, chân 52 cách đáy 51 (VE0101_13). Màn Cài đặt QĐ684: đệm dưới 42,
dải chân 52 chỉ ở ngăn có dòng ghi chú chân khối (.gd-dong).
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from kiemthu.ban0101.test_baihoc_0100 import quy_tac

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"
NHOM_A = {"QUẢN TRỊ TMĐT": "shopping-bag", "NĂNG LỰC": "cpu", "KẾT NỐI": "link", "HỆ THỐNG": "settings-2"}   # QĐ674 bộ A


def do_manh(chon):
    """Độ mạnh bộ chọn CSS (id, lớp / thuộc tính / lớp giả, thẻ / phần tử giả); :not(x) tính theo x."""
    c = re.sub(r":not\(([^)]*)\)", r" \1", chon)
    c = re.sub(r"\[[^\]]*\]", " .a", c)
    id_ = len(re.findall(r"#[\w-]+", c))
    lop = len(re.findall(r"\.[\w-]+", c)) + len(re.findall(r"(?<!:):[\w-]+", c))
    the = len(re.findall(r"::[\w-]+", c)) + len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", c))
    return (id_, lop, the)


def luat_le(qt):
    """[(thứ tự, 01 bộ chọn, thân)] – tách danh sách bộ chọn có dấu phẩy."""
    return [(i, x.strip(), b) for i, (s, b) in enumerate(qt) for x in s.split(",") if x.strip()]


class KiemLuatAnThuGon(unittest.TestCase):   # CDO LOI-THU-GDSAU: chặn loại lỗi "luật mới mạnh hơn luật ẩn cũ"
    def test_luat_an_thu_gon_khong_bi_de(self):
        """Mỗi lớp bị ẩn khi thanh trái thu gọn (`.thu … .X{display:none}`): mọi luật máy tính đặt display khác none cho .X
        phải có 01 luật ẩn thu gọn mạnh hơn (hoặc bằng mà đứng sau)."""
        html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        ds = luat_le(quy_tac(html))
        an = {}
        for i, c, b in ds:
            if re.search(r"\.thu\b", c) and re.search(r"display:none", b):
                cuoi = re.sub(r":not\([^)]*\)|::?[\w-]+", "", re.split(r"[\s>+~]+", c)[-1])
                for lop in re.findall(r"\.([\w-]+)", cuoi):
                    an.setdefault(lop, []).append((do_manh(c), i, "!important" in b))
        self.assertIn("gd-sau", an)
        loi = []
        for i, c, b in ds:
            m = re.search(r"display:\s*([\w-]+)", b)
            if not m or m.group(1) == "none" or re.search(r"\.thu\b|\.mb\b|dien-thoai", re.sub(r":not\([^)]*\)", "", c)):   # luật điện thoại bỏ qua; :not(.mb) là luật máy tính
                continue
            cuoi = re.sub(r":not\([^)]*\)|::?[\w-]+", "", re.split(r"[\s>+~]+", c)[-1])
            for lop in re.findall(r"\.([\w-]+)", cuoi):
                if lop in an and not any(((dm, j) > (do_manh(c), i) or (qt and "!important" not in b)) and (qt or "!important" not in b)
                                         for dm, j, qt in an[lop]):
                    loi.append(f"{c}{{{b.strip()}}} đè .thu .{lop}")
        self.assertEqual(loi, [])

    def test_do_manh_dung(self):   # bài tự chứng minh: luật C01 mạnh hơn luật ẩn cũ dòng 136
        self.assertGreater(do_manh("#app:not(.mb) nav.menu .gd-sau"), do_manh(".thu .gd-sau"))
        self.assertGreater(do_manh("#app.thu:not(.mb) nav.menu .gd-sau"), do_manh("#app:not(.mb) nav.menu .gd-sau"))
        self.assertEqual(do_manh("#app:not(.mb) nav.menu .gd-sau"), (1, 3, 1))


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)
        cls.nav = cls.html[cls.html.index('<nav class="menu">'):cls.html.index("</nav>", cls.html.index('<nav class="menu">')) + 6]

    def luat(self, chon):
        return " ".join(b for s, b in self.qt if s == chon)

    def test_pd12_thu_tu_thanh_trai(self):   # QĐ671 (6) ghim Trò chuyện AI; QĐ675 Hiện thêm trên HỆ THỐNG; PD26 khối giữa
        n = self.nav
        moc = ['<div class="logo">', '<div class="nhom">TRÒ CHUYỆN</div>', 'data-trang="08"', '<div class="menu-giua">',
               '<div class="nhom">QUẢN TRỊ TMĐT</div>', '<div class="nhom">NĂNG LỰC</div>', '<div class="nhom">KẾT NỐI</div>',
               '<div class="gd-sau">', '<div class="nhom">HỆ THỐNG</div>', '<div class="chan-menu">']
        vt = [n.index(x) for x in moc]
        self.assertEqual(vt, sorted(vt), "thứ tự thanh trái")
        self.assertTrue(n.index('<div class="nhom">HỆ THỐNG</div>') > n.index("</div>", n.index('<div class="menu-giua">')))   # HỆ THỐNG ngoài khối giữa

    def test_pd13_icon_nhom(self):
        self.assertIn("const NHOM_IC = " + json.dumps(NHOM_A, ensure_ascii=False).replace('"', "'").replace("': '", "': '"), self.js)
        for ten in list(NHOM_A.values()) + ["panel-left"]:
            self.assertIn("ICON['" + ten + "'] = ICON['" + ten + "'] || svgLucide('" + ten + "'", self.js)
        self.assertIn("icoNhom(ten) + '<span class=\"nhom-ten\">'", self.js)
        self.assertNotIn("color", self.luat("#app:not(.mb) .nhom-nut .nhom-ic"))   # cùng màu chữ tên nhóm: không đặt màu riêng (QA S03)

    def test_pd14_he_thong_ghim_day(self):
        self.assertIn("margin-top:auto", self.luat('#app.thu:not(.mb) nav.menu .nhom-ds[data-nhom="HỆ THỐNG"]'))
        self.assertIn("border-top:1px solid var(--ke)", self.luat('#app.thu:not(.mb) nav.menu .nhom-ds[data-nhom="HỆ THỐNG"]::before'))
        self.assertIn("ds.dataset.nhom = ten;", self.js)

    def test_pd15_chan_menu(self):   # QĐ671 (1), QĐ547, QĐ678 (1); CDO PD15; QA S14
        trang = "https://" + "tech." + "unihq" + ".vn/igm360"   # ghép lúc chạy: chuỗi trang công khai chỉ có ngoại lệ máy quét ở index.html
        self.assertIn('<div class="chan-menu"><a class="nav-ban" id="nav-ban" href="' + trang + '" target="_blank" rel="noopener noreferrer">'
                      '<span class="ban-so" id="nav-ban-so"></span><span class="ban-tg">by UNI TECH</span></a><span class="ban-thu" id="nav-ban-thu"></span>'
                      '<button class="nut-thu" data-thu><i data-ic="panel-left" data-co="16"></i></button></div></nav>', self.html)
        chan = self.nav[self.nav.index('<div class="chan-menu">'):]
        self.assertNotIn("Thu gọn menu", re.sub(r"<[^>]+>", "", chan))   # chữ không hiện trên chân (QA SOAT-PD0101b; chỉ ở title / aria)
        self.assertNotIn('class="muc thu-gon"', self.html)
        self.assertIn("const nt = $('.chan-menu [data-thu]'); if (nt) { const c = S.thu ? 'Mở rộng menu' : 'Thu gọn menu';", self.js)
        self.assertIn("$('#nav-ban-so').textContent = 'IGM360 ' + D.tbBan; $('#nav-ban-thu').textContent = D.tbBan;", self.js)
        c = self.luat(".chan-menu")
        for x in ("height:52px", "border-top:1px solid var(--ke)", "margin:8px 12px 0 18px", "flex:none"):
            self.assertIn(x, c)
        for chon, x in ((".ban-so", "font-size:12px;font-weight:600;color:var(--chu)"), (".ban-tg", "font-size:11px;color:var(--xanh-chu)"),
                        (".nut-thu", "width:32px;height:28px"), (".nut-thu", "border:1px solid var(--ke);border-radius:8px"), (".nut-thu", "color:var(--phu)")):
            self.assertIn(x, self.luat(chon), chon)
        self.assertIn("padding-bottom:51px", self.luat("#app:not(.mb) nav.menu"))
        p08 = self.html[self.html.index('<div class="trang" id="p08"'):self.html.index('<div class="trang" id="p13"')]
        for x in ("panel-left-close", "panel-left-open"):   # QĐ678 (1): 02 icon này chỉ ở cột hội thoại
            self.assertEqual(self.html.count(x), p08.count(x), x)

    def test_pd16_chan_thu_gon(self):   # QĐ676 B + CDO: chân 52, "0.10.1" 11 px trên nút, không "by UNI TECH"
        self.assertIn("flex-direction:column", self.luat(".thu .chan-menu"))
        self.assertIn("display:block;font-size:11px", self.luat(".thu .ban-thu"))
        self.assertIn("display:none", self.luat(".ban-thu"))
        self.assertIn("display:none", self.luat(".thu .nav-ban,.mb .nav-ban"))

    def test_pd17_luoi_hang(self):   # VE0101_13 + CDO PD17
        self.assertIn("padding-top:12px", self.luat("#app:not(.mb) nav.menu"))
        self.assertIn("padding-top:19px", self.luat("#app.thu:not(.mb) nav.menu"))
        lg = self.luat("#app:not(.mb) nav.menu .logo")
        for x in ("height:50px", "padding-bottom:0"):
            self.assertIn(x, lg)
        self.assertIn("height:36px", self.luat("#app.thu:not(.mb) nav.menu .logo"))
        self.assertIn("margin-top:12px", self.luat("#app:not(.mb) nav.menu .nhom-ds.rieng"))
        self.assertIn("margin-top:19px", self.luat("#app.thu:not(.mb) nav.menu .nhom-ds.rieng"))

    def test_pd26_khoi_giua_cuon_rieng(self):
        g = self.luat("#app:not(.mb) nav.menu .menu-giua")
        for x in ("flex:1", "min-height:min(120px,20vh)", "overflow-y:auto"):   # QA C01: khối giữa không co về 0 ở màn 1024×600
            self.assertIn(x, g)
        self.assertNotIn("#app:not(.mb) nav.menu{overflow-y:auto}", self.html)
        self.assertIn("nav.querySelectorAll('.nhom')", self.js)

    def test_pd27_day_caidat(self):   # QĐ684: đáy 42, trái / phải 28; dải 52 chỉ ở ngăn có .gd-dong
        self.assertIn("padding-bottom:42px", self.luat("#app:not(.mb) #p09"))
        self.assertIn('<div class="cd-chan" id="cd-chan"></div></section>', self.html)
        d = self.luat("#app:not(.mb) #p09.co-chan .cd-chan")
        for x in ("display:flex", "height:51px", "border-top:1px solid var(--ke)", "padding:0 20px", "font-size:12px", "color:var(--phu)", "flex:none"):
            self.assertIn(x, d)
        m = self.luat("#app:not(.mb) #p09.co-chan .cd-menu::after")
        for x in ("height:51px", "margin-top:auto", "border-top:1px solid var(--ke)"):
            self.assertIn(x, m)
        self.assertIn("display:none", self.luat("#app:not(.mb) #p09.co-chan .cd-than .gd-dong.o-chan"))   # QA C05: chỉ dòng đưa xuống dải
        self.assertEqual(self.luat("#app:not(.mb) #p09.co-chan .cd-than .gd-dong"), "")
        self.assertIn("display:none", self.luat(".cd-chan"))

    def test_qa_c01_hien_them_man_thap(self):   # QA C01: danh sách "Hiện thêm" ngoài khối giữa – màn thấp tự co, cuộn riêng
        g = self.luat("#app:not(.mb) nav.menu .gd-sau")
        for x in ("flex:0 1 auto", "min-height:0", "flex-direction:column"):
            self.assertIn(x, g)
        d = self.luat("#app:not(.mb) nav.menu .gd-ds")
        for x in ("min-height:0", "overflow-y:auto"):
            self.assertIn(x, d)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    def chay(self, ma, cau):
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify(" + cau + "));"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_pd13_icon_16_cung_mau(self):
        a = self.a
        ma = ("const ICON = {}; " + a[a.index("const svgLucide = "):a.index(";\n", a.index("const svgLucide = ")) + 2]
              + a[a.index("ICON['shopping-bag'] = "):a.index("\n", a.index("ICON['panel-left'] = ")) + 1]
              + a[a.index("const NHOM_IC = "):a.index(";\n", a.index("const icoNhom = ")) + 2])
        kq = self.chay(ma, "Object.keys(NHOM_IC).map(t => icoNhom(t)).concat([icoNhom('TRÒ CHUYỆN')])")
        for t, h in zip(NHOM_A.values(), kq):
            self.assertIn("lucide-" + t, h)
            self.assertIn('width="16"', h)
            self.assertIn('height="16"', h)
            self.assertIn('stroke="currentColor"', h)
            self.assertIn("color:currentColor", h)
            self.assertIn('class="nhom-ic', h)
        self.assertEqual(kq[-1], "")   # nhóm 01 mục (Trò chuyện AI ghim) không icon nhóm

    def test_pd27_chon_dong_ghi_chu(self):
        a = self.a
        ham = a[a.index("function datChanCd() {"):a.index("\n}\n", a.index("function datChanCd() {")) + 3]
        ma = ("const g = (t, an) => { const o = {innerHTML: t, lop: new Set(), closest: q => an ? {} : null}; o.classList = {add: c => o.lop.add(c), remove: c => o.lop.delete(c)}; return o; };"
              "let lop = null; const p9 = {classList: {toggle: (c, b) => { lop = [c, b]; }}}; const d = {innerHTML: ''};"
              "let DS = []; const S = {xem: 'dt', trang: '09'};"
              "const $ = q => ({'#p09': p9, '#cd-chan': d})[q]; const $$ = q => q.includes('.o-chan') ? DS.filter(x => x.lop.has('o-chan')) : DS;"
              "const an = () => DS.map(x => x.lop.has('o-chan'));\n" + ham)
        kq = self.chay(ma, "[(DS = [g('A', false), g('B', false)], datChanCd(), [d.innerHTML, lop, an()]),"   # 02 dòng: chỉ dòng cuối xuống dải (QA C05)
                           " (DS = [g('A', true)], datChanCd(), [d.innerHTML, lop, an()]),"
                           " (DS = [g('C', false)], S.xem = 'mb', datChanCd(), [d.innerHTML, lop, an()])]")
        self.assertEqual(kq, [["B", ["co-chan", True], [False, True]], ["", ["co-chan", False], [False]], ["", ["co-chan", False], [False]]])


if __name__ == "__main__":
    unittest.main()
