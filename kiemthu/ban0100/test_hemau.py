"""Bài kiểm 0.10.0 – hệ màu Sáng · Tối · Theo hệ thống (QĐ562, QĐ411; CDO Bien_Mau_Vaitro.md; phông Tối QĐ555; logo QĐ588).

0 mã màu viết thẳng ngoài khối biến (trừ ngoại lệ ghi tên: phông Sáng, hình trang đăng nhập trên khối xanh QĐ554, logo
hãng QĐ92) · mọi `var(--…)` đang dùng đã khai báo · mã Sáng / Tối đúng bảng CDO · tương phản WCAG đo bằng công thức ·
05 lớp không dùng đã bỏ · chedo.js: chưa chọn = theo máy, chọn tay thì máy nhớ, logo nền tối · tệp phông, logo có thật.
"""

import json
import re
import shutil
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"
HEX = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")
CO_NODE = shutil.which("node") is not None


def _doc(ten: str) -> str:
    return re.sub(r"data:[a-z/+0-9-]+;base64,[A-Za-z0-9+/=]+", "DATA", (GD / ten).read_text(encoding="utf-8"))


def _bien(khoi: str) -> dict:
    return dict(re.findall(r"(--[\w-]+):([^;}]+)", khoi))


def _sang_toi():
    s = _doc("index.html")
    return (_bien(re.search(r":root\{([^}]*)\}", s).group(1)), _bien(re.search(r"html\.toi\{([^}]*)\}", s).group(1)))


def _do_sang(hx: str) -> float:
    hx = hx.lstrip("#")
    kq = []
    for i in (0, 2, 4):
        c = int(hx[i:i + 2], 16) / 255
        kq.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kq[0] + 0.7152 * kq[1] + 0.0722 * kq[2]


def tuong_phan(a: str, b: str) -> float:
    x, y = sorted((_do_sang(a), _do_sang(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


class KiemCamMaVietThang(unittest.TestCase):
    def test_index_chi_con_ngoai_le(self):
        s = _doc("index.html")
        s = re.sub(r":root\{[^}]*\}|html\.toi\{[^}]*\}", "", s)
        # ngoại lệ 1: lớp phông Sáng (QĐ375) + hình trang đăng nhập (linh vật, khối bay – QĐ554 giữ 02 chế độ)
        s = s[:s.index('<div class="pn pn1"')] + s[s.index('<div class="dn-phai">'):]
        # ngoại lệ 2: khối xanh trang đăng nhập (QĐ554); ngoại lệ 3: logo Claude của hãng (QĐ92)
        s = re.sub(r"#s01 \.kx\{[^}]*\}", "", s)
        s = s.replace('fill="#D97757"', "")
        # ngoại lệ 4: ô logo trên khối xanh (QĐ554) và ô mã QR 02 lớp (CDA 16o R4) luôn nền trắng ở 02 chế độ
        self.assertEqual(s.count("background:#FFFFFF"), 2)
        self.assertIn("#s01 .khung-logo{background:#FFFFFF;", s)
        self.assertIn("#s01 .qr{padding:8px;border:1px solid var(--ke);border-radius:8px;background:#FFFFFF;", s)
        s = s.replace("background:#FFFFFF", "")
        self.assertEqual(HEX.findall(s), [])
        self.assertEqual(re.findall(r"rgba?\((?!var\()[^)]*\)", s), [])

    def test_app_js_0_ma(self):
        self.assertEqual(HEX.findall(_doc("app.js")), [])

    def test_icon_js_chi_logo_hang(self):
        s = _doc("icon.js")
        self.assertEqual(HEX.findall(s), ["#D97757"])   # logo Claude (QĐ92)
        for the in re.findall(r"<svg\b(?:[^>\\]|\\.)*>", s):
            if "stroke=" in the:   # nét icon theo currentColor; màu ở style (icon gốc đã currentColor thì theo chữ chứa nó)
                self.assertIn('stroke=\\"currentColor\\"', the)

    def test_05_lop_khong_dung_da_bo(self):
        s = _doc("index.html")
        for lop in (".bb", ".dx", ".mo-gd", ".logo-cho", ".logo-shop"):
            self.assertNotRegex(s, re.escape(lop) + r"[\s.:{,]", lop)


class KiemBien(unittest.TestCase):
    def test_moi_bien_dang_dung_da_khai_bao(self):
        sang, toi = _sang_toi()
        self.assertLessEqual(set(toi), set(sang))
        dung = set()
        for ten in ("index.html", "app.js", "icon.js", "chedo.js"):
            dung |= set(re.findall(r"var\((--[\w-]+)", _doc(ten)))
        rieng = {"--D", "--k", "--co", "--tre", "--xoay"}   # biến cục bộ của hình trang đăng nhập (đặt ở style từng thẻ)
        self.assertEqual(sorted(dung - set(sang) - rieng), [])

    def test_ma_dung_bang_cdo(self):
        sang, toi = _sang_toi()
        BANG = {"--khoi": ("#FFFFFF", "#1F2125"), "--xam": ("#F5F6F7", "#141518"), "--xanh": ("#1456F0", "#1456F0"),
                "--chu": ("#1F2329", "#E6E8EB"), "--phu": ("#646A73", "#A3A8B0"), "--xanh-chu": ("#1456F0", "#7EA2FF"),
                "--ke": ("#DEE0E3", "#34373D"), "--vien": ("#858B94", "#787E87"), "--dat": ("#258832", "#4CB860"),
                "--xem": ("#8F5F00", "#E0A63A"), "--canh": ("#E22E28", "#FF6B66"), "--h-chinh": ("#1456F0", "#3D7DFC"),
                "--h-xem": ("#D99A00", "#D9A62E"), "--ai-ic": ("#8E44C9", "#A57BE8"), "--vien-xem": ("#C9A766", "#6A552D")}
        for k, (a, b) in BANG.items():
            self.assertEqual((sang[k], toi.get(k, sang[k])), (a, b), k)

    def test_tuong_phan_wcag(self):
        sang, toi = _sang_toi()
        for ten, bo in (("Sáng", sang), ("Tối", {**sang, **toi})):
            for chu in ("--chu", "--phu", "--xanh-chu", "--dat", "--xem", "--canh", "--goi-y"):
                self.assertGreaterEqual(tuong_phan(bo[chu], bo["--khoi"]), 4.5, (ten, chu))
            self.assertGreaterEqual(tuong_phan(bo["--chu-tren-nut"], bo["--xanh"]), 4.5, ten)
            self.assertGreaterEqual(tuong_phan(bo["--vien"], bo["--khoi"]), 3, ten)   # viền ô nhập (WCAG 1.4.11)
        self.assertLess(tuong_phan("#1456F0", toi["--khoi"]), 3)   # vì sao Tối không dùng --xanh làm chữ (2,78)


class KiemTep(unittest.TestCase):
    def test_tep_phong_logo_co_that(self):
        for ten in ("phongnen_toi_ngang.jpg", "phongnen_toi_doc.jpg", "logo/igm360_ngang_toi.svg"):
            p = GD / ten
            self.assertGreater(p.stat().st_size, 1000, ten)
        self.assertEqual((GD / "phongnen_toi_ngang.jpg").read_bytes()[:2], b"\xff\xd8")
        logo = (GD / "logo/igm360_ngang_toi.svg").read_text(encoding="utf-8")
        self.assertIn('fill="#1456F0"', logo)   # QĐ588: chữ 360 xanh

    def test_chedo_nap_truoc_khi_ve(self):
        s = _doc("index.html")
        self.assertLess(s.index('<script src="/tainguyen/chedo.js"></script>'), s.index("<style>"))
        self.assertIn("html.toi .pn1{background:var(--phong) url(/tainguyen/phongnen_toi_ngang.jpg)", s)
        from maychu import khoidong
        self.assertIn(f'src="/tainguyen/chedo.js?v={khoidong.PHIENBAN}"', khoidong.TRANG_CHINH)


class KiemThanhCuonC(unittest.TestCase):
    """QĐ612 + Bổ sung QĐ612 (Quychuan 5.20): 01 khối CSS, 24 hình mũi tên (04 hướng × 03 trạng thái × 02 chế độ)."""

    def setUp(self):
        from urllib.parse import unquote
        s = _doc("index.html")
        self.k = s[s.index("/* QĐ612 thanh cuộn kiểu C"):s.index("/* QĐ562, QĐ411 (0.10.0): hệ màu Tối")]
        self.anh = [unquote(x) for x in re.findall(r'url\("data:image/svg\+xml,([^"]+)"\)', self.k)]

    def test_than_va_nut(self):
        g = "body:not(.dien-thoai) "   # điện thoại dùng thanh của máy
        self.assertIn(g + "::-webkit-scrollbar{width:12px;height:12px}", self.k)
        self.assertIn("border:2px solid transparent;background-clip:padding-box;border-radius:6px;min-height:40px", self.k)
        for tt, bien in (("", "--vien"), (":hover", "--phu"), (":active", "--xanh-chu")):
            self.assertIn(f"::-webkit-scrollbar-thumb{tt}{{background:var({bien})", self.k)
        self.assertIn("{display:block;width:12px;height:24px;", self.k)   # nút dọc 12 × 24
        self.assertIn("{display:block;width:24px;height:12px;", self.k)   # nút ngang 24 × 12
        self.assertIn("@supports not selector(::-webkit-scrollbar){" + g + "*{scrollbar-width:thin;scrollbar-color:var(--vien) transparent}}", self.k)

    def test_24_hinh_dung_mau_bien(self):
        sang, toi = _sang_toi()
        toi = {**sang, **toi}
        self.assertEqual(len(self.anh), 24)
        mau = [re.search(r"fill='(#[0-9A-F]{6})'", x).group(1) for x in self.anh]
        mong = []
        for bo in (sang, toi):
            for _h in range(4):
                mong += [bo["--vien"], bo["--phu"], bo["--xanh-chu"]]
        self.assertEqual(mau, mong)
        for x in self.anh:
            self.assertRegex(x, r"width='(12|24)' height='(24|12)'")
        self.assertEqual(self.k.count("html.toi body:not(.dien-thoai)"), 12)


@unittest.skipUnless(CO_NODE, "máy không có node")
class KiemCheDo(unittest.TestCase):
    def chay(self, luu, toi_may, buoc):
        ma = ("let LS = " + json.dumps(luu) + "; const nghe = [];"
              "global.localStorage = {getItem: k => LS[k] ?? null, setItem: (k, v) => { LS[k] = v; }, removeItem: k => { delete LS[k]; }};"
              "const may = {matches: " + json.dumps(toi_may) + ", addEventListener: (e, f) => nghe.push(f)};"
              "global.window = {matchMedia: () => may};"
              "const lop = new Set(); const anh = [{src: ''}, {src: ''}];"
              "global.document = {documentElement: {classList: {toggle: (c, b) => b ? lop.add(c) : lop.delete(c)}},"
              " querySelectorAll: () => anh, addEventListener: () => {}};"
              + (GD / "chedo.js").read_text(encoding="utf-8") +
              "\nconst kq = []; const chup = () => kq.push([window.CHEDO.doc(), lop.has('toi'), anh[0].src, JSON.stringify(LS)]);"
              "chup();" + buoc + "\nconsole.log(JSON.stringify(kq));")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "cd.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_chua_chon_theo_may_va_doi_theo(self):
        kq = self.chay({}, True, "may.matches = false; nghe.forEach(f => f()); chup();")
        self.assertEqual(kq[0][:3], ["hethong", True, "/tainguyen/logo/igm360_ngang_toi.svg"])
        self.assertEqual(kq[1][:3], ["hethong", False, "/tainguyen/logo/igm360_ngang.svg"])   # máy đổi sang sáng: theo ngay

    def test_chon_tay_may_nho(self):
        kq = self.chay({}, False, "window.CHEDO.dat('toi'); chup(); window.CHEDO.dat('sang'); may.matches = true;"
                                  " nghe.forEach(f => f()); chup(); window.CHEDO.dat('hethong'); chup();")
        self.assertEqual(kq[1], ["toi", True, "/tainguyen/logo/igm360_ngang_toi.svg", '{"igm360_chedo":"toi"}'])
        self.assertEqual(kq[2][:2], ["sang", False])                      # chọn Sáng: máy tối vẫn giữ Sáng
        self.assertEqual(kq[3], ["hethong", True, "/tainguyen/logo/igm360_ngang_toi.svg", "{}"])
        self.assertEqual(self.chay({"igm360_chedo": "la"}, False, "")[0][:2], ["hethong", False])   # giá trị lạ = theo máy


if __name__ == "__main__":
    unittest.main()
