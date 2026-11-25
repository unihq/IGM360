"""Bài kiểm bản 0.8.8 – logo C3 và trang đăng nhập 3D (QĐ345, QĐ369, QĐ371; kế hoạch KH-088, CDA SOAT-KH-088).

L1 thư viện · L2 nguồn tệp · L3 đăng nhập được khi đồ họa lỗi · L4 cỡ tải · L5 chuyển động, máy yếu ·
trạng thái linh vật qua biến riêng S.lv (S.dn giữ 07 giá trị) · chữ đúng bảng chữ đã duyệt.
Phần JS chạy bằng node với DOM giả tối thiểu (0 thư viện), không gọi mạng, không ghi /dulieu.
"""
import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"
KHAU_HIEU = "Quản trị vận hành 360 cho TMĐT"                       # QĐ369 (2), nguyên văn anh
S_DN = {"matkhau", "sai", "khoa", "khoatk", "hethan", "ma2lop", "batdau2lop"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self' data:; frame-ancestors 'none'")


def doc(p):
    return Path(p).read_text(encoding="utf-8").replace("\r\n", "\n")


def phan_s01(ix):
    a = ix.index('<section id="s01"')
    return ix[a:ix.index("</section>", a) + 10]


def quy_tac(css):
    """(chọn, khối) của mọi quy tắc thường, kể cả trong @media; bỏ @keyframes."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    ra = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        chon = m.group(1).strip()
        if chon.startswith("@media"):
            chon = chon[chon.index("{") + 1:] if "{" in chon else chon
        chon = re.sub(r"^@media[^{]*\{", "", chon).strip()
        ra.append((chon, m.group(2)))
    return ra


class KiemTep088(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ix = doc(GD / "index.html")
        cls.js = doc(GD / "app.js")
        cls.css = doc(GD / "dangnhap3d.css")
        cls.s01 = phan_s01(cls.ix)

    # ---- L1: 0 thư viện, 0 tệp JS ngoài
    def test_l1_dung_02_the_script(self):
        self.assertEqual(re.findall(r"<script[^>]*>", self.ix),
                         ['<script src="/tainguyen/icon.js">', '<script src="/tainguyen/app.js">'])

    # ---- L2: mọi tệp cùng nguồn, CSP không nới
    def test_l2_khong_dia_chi_ngoai(self):
        self.assertEqual(re.findall(r"https?://", self.css), [])
        ngoai = [m for m in re.findall(r"https?://[^\"' )]*", self.s01) if m != "http://www.w3.org/2000/svg"]
        self.assertEqual(ngoai, [])                                                # chỉ khai báo xmlns của SVG
        moi = re.findall(r'(?:src|href)="([^"#]+)"', self.s01 + self.ix[:self.ix.index("</head>")])
        for d in moi:
            if d.startswith("data:"):
                continue
            self.assertTrue(d.startswith("/tainguyen/"), d)
        for t in ("igm360_bieutuong.svg", "igm360_ngang.svg", "favicon.ico", "igm360_180.png"):
            self.assertTrue((GD / "logo" / t).is_file(), t)
        self.assertIn('<link rel="icon" href="/tainguyen/logo/favicon.ico">', self.ix)
        self.assertIn('<link rel="apple-touch-icon" href="/tainguyen/logo/igm360_180.png">', self.ix)
        self.assertIn('<link rel="stylesheet" href="/tainguyen/dangnhap3d.css">', self.ix)

    def test_l2_logo_svg_khong_tai_ngoai(self):
        for t in ("igm360_bieutuong.svg", "igm360_ngang.svg"):
            s = doc(GD / "logo" / t)
            self.assertEqual([m for m in re.findall(r"https?://[^\"' ]*", s) if m != "http://www.w3.org/2000/svg"], [], t)
            self.assertNotIn("<script", s)
            self.assertNotIn("<image", s)

    # ---- L3: ô đăng nhập không phụ thuộc đồ họa
    def test_l3_do_hoa_an_va_khong_nhan_bam(self):
        for lop in ('class="nen"', 'class="sk-dt"', 'class="kx-bay"', 'class="kx-sk"'):
            i = self.s01.index(lop)
            the = self.s01[self.s01.rindex("<", 0, i):self.s01.index(">", i)]
            self.assertIn('aria-hidden="true"', the, lop)
        for chon in ("#s01 .nen", "#s01 .sk", "#s01 .kb", "#s01 .kx-bay"):
            khoi = [k for c, k in quy_tac(self.css) if c == chon]
            self.assertTrue(any("pointer-events:none" in k for k in khoi), chon)
        # 09 icon trang trí trong ô đăng nhập có aria-hidden (bản chốt)
        phai = self.s01[self.s01.index('<div class="dn-phai">'):]
        self.assertEqual(phai.count('<svg aria-hidden="true"\n  style="flex:none;vertical-align:middle"'), 9)

    def test_l3_css_o_dang_nhap_nam_trong_index(self):
        st = self.ix[self.ix.index("<style>/* 0.8.8"):self.ix.index("</head>")]
        for chon in ("#s01 .o-nhap{", "#s01 .btn{", "#s01 .nhan-o{", "#s01 .o6{", "#s01 .the-doi{", "#s01 .dn-phai{"):
            self.assertIn(chon, st)
            self.assertNotIn(chon, self.css)
        # thiếu dangnhap3d.css: đồ họa ẩn; tệp tải được thì hiện (tệp nằm sau khối style trong <head>)
        self.assertIn("#s01 .nen,#s01 .kx-bay,#s01 .kx-sk,#s01 .sk-dt{display:none}", st)
        self.assertTrue(self.css.split("*/", 1)[1].lstrip().startswith("#s01 .nen,#s01 .kx-bay{display:block}"))
        self.assertGreater(self.ix.index('href="/tainguyen/dangnhap3d.css"'), self.ix.rindex("</style>", 0, self.ix.index("</head>")))
        from maychu.hethong import antoan
        self.assertTrue(antoan.duoc_mo("/"))
        self.assertTrue(antoan.duoc_mo("/tainguyen/dangnhap3d.css"))
        self.assertTrue(antoan.duoc_mo("/tainguyen/logo/favicon.ico"))

    def test_l3_giu_id_va_data_s_man_01(self):
        for x in ('id="dn-ten"', 'id="mk"', 'id="o-mk"', 'id="dn-loi"', 'id="dn-con"', 'id="dn-con-cau"', 'id="k-thoigian"',
                  'id="qr-2lop"', 'data-s="dn:matkhau sai khoa khoatk hethan"', 'data-s="dn:hethan"', 'data-s="dn:sai"',
                  'data-s="dn:khoa"', 'data-s="dn:khoatk"', 'data-s="dn:ma2lop"', 'data-s="dn:batdau2lop"', "data-dangnhap",
                  "data-xacnhan", "data-mat"):
            self.assertEqual(self.s01.count(x) >= 1, True, x)
        self.assertEqual(len(re.findall(r'data-s="', self.s01)), 7)             # 07 khối trạng thái, không thêm

    def test_l3_ten_lop_khong_trung_ma_chinh(self):
        # ve() ẩn mọi .cham rỗng; .kh, .canh, .dat… là lớp chung của phần mềm → đồ họa dùng tên riêng
        lop = set()
        for m in re.finditer(r'class="([^"]*)"', self.s01[:self.s01.index('<div class="dn-phai">')]):
            lop |= set(m.group(1).split())
        for cu in ("cham", "kh", "canh", "dat", "goc", "cau", "nguoi", "vai", "xanh", "cho", "loi", "xong", "chay", "dang"):
            self.assertNotIn(cu, lop, cu)
        kf_chinh = re.findall(r"@keyframes ([\w-]+)", self.ix)
        for k in re.findall(r"@keyframes ([\w-]+)", self.css):
            self.assertTrue(k.startswith("dn3-"), k)
            self.assertNotIn(k, kf_chinh)

    # ---- L4: cỡ tải (số đo mã dựng 0.8.8, có biên)
    def test_l4_tran_co(self):
        c = (GD / "dangnhap3d.css").read_bytes().replace(b"\r\n", b"\n")
        self.assertLess(len(c), 18000)                                            # đo 15.639 B
        self.assertLess(len(gzip.compress(c, 9)), 4500)                           # đo 3.648 B
        s = self.s01.encode("utf-8")
        self.assertLess(len(s), 68000)                                            # đo 61.102 B
        self.assertLess(len(gzip.compress(s, 9)), 18500)                          # đo 16.407 B

    # ---- L5: chuyển động
    def test_l5_keyframes_chi_transform_opacity(self):
        for m in re.finditer(r"@keyframes ([\w-]+)\{((?:[^{}]*\{[^{}]*\})*)\}", self.css):
            thuoc = set(re.findall(r"([a-z-]+)\s*:", re.sub(r"\([^)]*\)", "", m.group(2))))
            self.assertTrue(thuoc <= {"transform", "opacity", "animation-timing-function"}, (m.group(1), thuoc))
            self.assertNotIn("filter", m.group(2))
            self.assertNotIn("box-shadow", m.group(2))

    def test_l5_giam_chuyen_dong_va_may_yeu_bao_moi_lop_co_animation(self):
        dung = []
        for m in re.finditer(r"@media \(prefers-reduced-motion:reduce\)\{(.*?\})\}", self.css):
            for c, k in quy_tac(m.group(1)):
                if "animation:none" in k:
                    dung += [x.strip() for x in c.split(",")]
        tinh = [x.strip() for c, k in quy_tac(self.css) if "#s01.tinh" in c and "animation:none" in k for x in c.split(",")]
        self.assertEqual(sorted(t.replace("#s01.tinh ", "#s01 ") for t in tinh), sorted(dung))   # máy yếu = giảm chuyển động
        bao = {}                                                                   # lớp → (gồm cả con cháu?)
        for d in dung:
            ten = d.replace("#s01 .", "")
            bao[ten.rstrip(" *")] = ten.endswith(" *")
        # mỗi phần tử mang lớp có animation phải nằm trong 01 lớp được tắt (chính nó, hoặc con cháu của lớp có " *")
        from html.parser import HTMLParser
        rong = {"input", "img", "br", "meta", "link", "use", "path", "circle", "rect", "ellipse", "stop", "line", "polyline"}

        class Doc(HTMLParser):
            def __init__(s):
                super().__init__(); s.ngan = []; s.ds = []

            def handle_starttag(s, tag, at):
                lop = set((dict(at).get("class") or "").split())
                s.ds.append((lop, [set(x) for x in s.ngan]))
                if tag not in rong:
                    s.ngan.append(lop)

            def handle_startendtag(s, tag, at):
                s.ds.append((set((dict(at).get("class") or "").split()), [set(x) for x in s.ngan]))

            def handle_endtag(s, tag):
                if tag not in rong and s.ngan:
                    s.ngan.pop()
        p = Doc(); p.feed(self.s01)
        for chon, khoi in quy_tac(self.css):
            if "animation:" not in khoi or "animation:none" in khoi:
                continue
            for x in chon.split(","):
                c = re.findall(r"\.([\w-]+)", x.strip().split()[-1])[-1]
                pt = [(lop, cha) for lop, cha in p.ds if c in lop]
                self.assertTrue(pt, x)
                for lop, cha in pt:
                    ok = any(t in lop for t in bao) or any(t in l and bao[t] for l in cha for t in bao)
                    self.assertTrue(ok, ("không tắt được khi giảm chuyển động / máy yếu", x))

    # ---- Ngoại lệ màu chỉ trong #s01
    def test_ngoai_le_mau_chi_trong_s01(self):
        for chon, khoi in quy_tac(self.css):
            for x in chon.split(","):
                self.assertTrue(x.strip().startswith("#s01"), x)
        st = re.findall(r"<style>(.*?)</style>", self.ix, flags=re.S)
        for chon, khoi in quy_tac("\n".join(st)):
            if "#0E44C4" in khoi.upper() or "linear-gradient(160deg" in khoi:
                for x in chon.split(","):
                    self.assertTrue(x.strip().startswith("#s01"), x)

    # ---- Chữ (QĐ369, CGM-088)
    def test_chu_khau_hieu_va_nhan(self):
        hien = [m.replace("&nbsp;", " ").replace(" ", " ") for m in re.findall(r'<div class="(?:khau-hieu|phu-de)">([^<]*)</div>', self.s01)]
        self.assertEqual(hien, [KHAU_HIEU, KHAU_HIEU])                           # khối xanh + phụ đề khổ hẹp
        self.assertNotIn("cho shop TMĐT", self.ix)
        for c in ("Số liệu các sàn về một chỗ", "AI làm, bạn duyệt rồi mới ghi sổ", "Khóa và dữ liệu được mã hóa"):
            self.assertIn("<span>" + c + "</span>", self.s01)                    # QĐ369 (3)
        self.assertIn('data-mat aria-label="Hiện mật khẩu"', self.s01)
        self.assertIn("const CHU_DN = {hien: 'Hiện mật khẩu', an: 'Ẩn mật khẩu', dang: 'Đang xử lý…'};", self.js)
        self.assertIn("t.setAttribute('aria-label', hien ? CHU_DN.an : CHU_DN.hien)", self.js)
        self.assertIn("ICON[hien ? 'eye-off' : 'eye']", self.js)
        ic = doc(GD / "icon.js")
        self.assertIn('"eye-off": "<svg', ic)
        self.assertIn("lucide-eye-off", ic)

    def test_logo_thanh_trai_sc2(self):
        self.assertNotIn("<b>IGM</b>", self.ix)
        self.assertIn('<img class="logo-ngang" src="/tainguyen/logo/igm360_ngang.svg" alt="IGM360" height="28">', self.ix)
        self.assertIn('<img class="logo-bt" src="/tainguyen/logo/igm360_bieutuong.svg" alt="IGM360" width="36" height="36">', self.ix)
        self.assertIn("<div class=\"t12 phu nw\">Quản trị vận hành 360</div>", self.ix)
        self.assertIn("nav.menu .logo{gap:14px;padding-left:20px}", self.ix)        # SC-3, SC-4

    def test_logo_hang_dung_net_tep_goc(self):
        for t, mau in (("tiktok.svg", "#000000"), ("shopee.svg", "#EE4D2D")):    # QĐ92
            d = re.search(r' d="([^"]+)"', doc(GD / "logo" / t)).group(1)
            self.assertIn('fill="' + mau + '" aria-hidden="true"><path d="' + d + '"/>', self.s01, t)

    def test_s_dn_giu_07_gia_tri(self):
        gan = set(re.findall(r"S\.dn = '(\w+)'", self.js))
        for cap in re.findall(r"S\.dn = [^;]*\? '(\w+)' : '(\w+)'", self.js):
            gan |= set(cap)
        self.assertTrue(gan <= S_DN, gan - S_DN)
        self.assertNotRegex(self.js, r"S\.dn = '(dang|xong)'")
        self.assertIn("S.lv === 'dang'", self.js)


class KiemPhucVu088(unittest.TestCase):
    def test_tainguyen_tra_200_no_cache(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.dulieu import khoitao
        tam = tempfile.TemporaryDirectory()
        self.addCleanup(tam.cleanup)
        with mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": tam.name, "IGM360_LICH": "tat"}):
            khoitao.tao_het(Path(tam.name))
            kh = TestClient(khoidong.app)
            for d, kieu in (("/tainguyen/dangnhap3d.css", "text/css"), ("/tainguyen/logo/favicon.ico", "image/"),
                            ("/tainguyen/logo/igm360_180.png", "image/png"), ("/tainguyen/logo/igm360_ngang.svg", "image/svg+xml"),
                            ("/tainguyen/logo/igm360_bieutuong.svg", "image/svg+xml")):
                r = kh.get(d)
                self.assertEqual(r.status_code, 200, d)
                self.assertTrue(r.headers["content-type"].startswith(kieu), (d, r.headers["content-type"]))
                self.assertEqual(r.headers["cache-control"], "no-cache", d)
                self.assertEqual(r.headers["content-security-policy"], CSP, d)


GIA_DOM = r"""
const S = {g: '01', dn: 'matkhau', lv: null}, D = {};
const lop = new Set(), vet = [], hen = [];
const setTimeout = (f, ms) => { hen.push([ms, f]); };
const s01 = {classList: {toggle: (c, v) => { v ? lop.add(c) : lop.delete(c); }, contains: c => lop.has(c)}, style: {setProperty() {}}};
const lvo = [{className: ''}, {className: ''}];
const nutCl = new Set();
const nutDn = {disabled: false, innerHTML: 'Đăng nhập', classList: {contains: c => nutCl.has(c), toggle: (c, v) => { v ? nutCl.add(c) : nutCl.delete(c); }}};
const o6 = [1, 2, 3, 4, 5, 6].map(v => ({value: String(v)}));
const O = {'#s01': s01, '#dn-ten': {value: 'chu.shop'}, '#mk': {value: 'mk-thu'}, '#dn-loi': {textContent: ''}, '#dn-con': {textContent: ''},
  '#dn-con-cau': {hidden: false}, '#k-thoigian': {textContent: ''}, '#qr-2lop': {innerHTML: ''}, '[data-dangnhap]': nutDn};
const $ = q => (q in O ? O[q] : null), $$ = q => q === '.lv-o' ? lvo : q === '.o6' ? o6 : [];
let navigator = {hardwareConcurrency: 8}, giam = false;
const matchMedia = () => ({matches: giam});
const addEventListener = () => {};
const ICON = {loader: '<svg stroke="#000" width="24" height="24"></svg>'};
const icoMau = (svg, mau, co) => svg.replace(/stroke="[^"]*"/, 'stroke="' + mau + '"');
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);
const ma6 = goc => $$('.o6', goc).map(i => i.value).join(''), xoa6 = goc => $$('.o6', goc).forEach(i => i.value = '');
const bao = m => vet.push('bao:' + m);
let api = async () => ({});
let vaoPhanMem = async () => { vet.push('vao:' + S.lv + ':' + lvo[0].className); };
function ve() {
NUT
  if (S.g === '01') dongTacLv();
  vet.push([S.lv, S.dn, nutDn.disabled, nutDn.innerHTML.includes('Đang xử lý…'), lvo[0].className].join('|'));
}
"""


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemLinhVat088(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = doc(GD / "app.js")
        cls.man01 = a[a.index("// ---- Màn 01"):a.index("// ---- Màn 02")]
        cls.nut = a[a.index("  const nutDn = $('[data-dangnhap]');"):a.index("  if (S.g === '01') dongTacLv();   // 0.8.8")]
        cls.dau = GIA_DOM.replace("NUT", cls.nut)

    def chay(self, truoc, ma, cau):
        r = subprocess.run(["node", "-e", self.dau + truoc + "\n" + self.man01 + "\n(async () => {" + ma +
                            "\nconsole.log(JSON.stringify(" + cau + "));})();"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_mat_ket_noi_luc_dang_tra_lai_nut(self):
        # CDA SOAT-KH-088 điểm 3: fetch ném lỗi không có e.status → finally trả S.lv = null, nút bấm lại được
        kq = self.chay("", "LVC.da = true; api = async () => { throw new Error('Mất kết nối'); }; await dangNhap();",
                       "{S, vet, nut: nutDn.disabled, chu: nutDn.innerHTML, lv: lvo[0].className}")
        self.assertIn("dang|matkhau|true|true|lv-o lv-xanh dt-danglam", kq["vet"])   # lúc đang chạy: nút tắt, linh vật đang làm
        self.assertEqual(kq["S"]["lv"], None)
        self.assertEqual(kq["S"]["dn"], "matkhau")                                    # ô đăng nhập vẫn hiện
        self.assertEqual((kq["nut"], kq["chu"]), (False, "Đăng nhập"))
        self.assertEqual(kq["lv"], "lv-o lv-xanh dt-cho")

    def test_dang_dat_linh_vat_dang_lam(self):
        kq = self.chay("", "LVC.da = true; let lv_luc_goi = ''; api = async () => { lv_luc_goi = lvo[0].className; return {ma_tam: 't', buoc: 'ma2lop'}; };"
                       " await dangNhap();", "{S, lv_luc_goi, lv: lvo[0].className, nut: nutDn.disabled}")
        self.assertEqual(kq["lv_luc_goi"], "lv-o lv-xanh dt-danglam")
        self.assertEqual((kq["S"]["dn"], kq["S"]["lv"], kq["lv"], kq["nut"]), ("ma2lop", None, "lv-o lv-xanh dt-chay", False))

    def test_sai_mat_khau_linh_vat_loi(self):
        kq = self.chay("", "LVC.da = true; api = async () => { const e = new Error('Mật khẩu chưa đúng.'); e.status = 401; e.ct = {con_lai: 3}; throw e; };"
                       " await dangNhap();", "{S, lv: lvo[0].className, con: O['#dn-con'].textContent}")
        self.assertEqual((kq["S"]["dn"], kq["S"]["lv"], kq["lv"], kq["con"]), ("sai", None, "lv-o lv-xanh dt-loi", "03"))

    def test_bam_lai_khi_dang_khong_goi_2_lan(self):
        kq = self.chay("", "LVC.da = true; let goi = 0; let tha; api = () => { goi++; return new Promise(r => { tha = r; }); };"
                       " const p = dangNhap(); await dangNhap(); tha({ma_tam: 't', buoc: 'ma2lop'}); await p;", "{goi, S}")
        self.assertEqual(kq["goi"], 1)

    def test_xac_nhan_ma_xong_roi_loi_tra_null(self):
        kq = self.chay("", "LVC.da = true; S.dn = 'ma2lop'; vaoPhanMem = async () => { vet.push('vao:' + S.lv + ':' + lvo[0].className); throw new Error('Mất kết nối'); };"
                       " await xacNhanMa({closest: () => ({}), dataset: {}});", "{S, vet, lv: lvo[0].className}")
        self.assertIn("vao:xong:lv-o lv-xanh dt-xong", kq["vet"])                     # đặt xong trước vaoPhanMem
        self.assertEqual(kq["S"]["lv"], None)
        self.assertEqual(kq["lv"], "lv-o lv-xanh dt-chay")

    def test_bang_gan_07_trang_thai_s_dn(self):
        kq = self.chay("", "LVC.da = true; const ra = {}; for (const t of ['matkhau','sai','khoa','khoatk','hethan','ma2lop','batdau2lop']) { S.dn = t; dongTacLv(); ra[t] = lvo[1].className; }",
                       "ra")
        self.assertEqual(kq, {"matkhau": "lv-o lv-xanh dt-cho", "sai": "lv-o lv-xanh dt-loi", "khoa": "lv-o lv-xanh dt-loi",
                              "khoatk": "lv-o lv-xanh dt-loi", "hethan": "lv-o lv-xanh dt-loi", "ma2lop": "lv-o lv-xanh dt-chay",
                              "batdau2lop": "lv-o lv-xanh dt-chay"})

    def test_chao_mung_vao_chao_cho(self):
        kq = self.chay("", "dongTacLv(); const a = lvo[0].className; hen.find(h => h[0] === 1800)[1](); const b = lvo[0].className;"
                       " hen.find(h => h[0] === 3600)[1](); const c = lvo[0].className; S.dn = 'sai'; LVC.pha = 'chao'; dongTacLv();",
                       "[a, b, c, lvo[0].className, hen.length]")
        self.assertEqual(kq, ["lv-o lv-xanh dt-vao", "lv-o lv-xanh dt-chao", "lv-o lv-xanh dt-cho", "lv-o lv-xanh dt-loi", 2])

    def test_may_yeu_va_giam_chuyen_dong_hinh_tinh(self):
        ca = {"navigator = {hardwareConcurrency: 2};": True, "navigator = {hardwareConcurrency: 8, deviceMemory: 2};": True,
              "navigator = {hardwareConcurrency: 8};": False, "navigator = {hardwareConcurrency: 8, deviceMemory: 8};": False,
              "navigator = {}; giam = true;": True}
        for truoc, tinh in ca.items():
            kq = self.chay(truoc, "dongTacLv();", "{tinh: lop.has('tinh'), hen: hen.length, lv: lvo[0].className}")
            self.assertEqual(kq["tinh"], tinh, truoc)
            self.assertEqual(kq["hen"], 0 if tinh else 2, truoc)                     # tĩnh: bỏ chào mừng
            if tinh:
                self.assertEqual(kq["lv"], "lv-o lv-xanh dt-cho", truoc)

    def test_linh_vat_loi_khong_chan_ve(self):
        kq = self.chay("", "O['#s01'] = null; S.lv = 'dang'; ve(); S.lv = null; ve();", "{vet, nut: nutDn.disabled}")
        self.assertEqual(len(kq["vet"]), 2)
        self.assertFalse(kq["nut"])

    def test_nut_dang_xu_ly_va_tra_chu_goc(self):
        kq = self.chay("", "LVC.da = true; S.lv = 'dang'; ve(); const a = nutDn.innerHTML, b = nutDn.disabled; S.lv = null; ve();",
                       "[a, b, nutDn.innerHTML, nutDn.disabled, nutCl.has('dang')]")
        self.assertTrue(kq[0].startswith('<svg aria-hidden="true" stroke="#FFFFFF"'), kq[0])
        self.assertTrue(kq[0].endswith("Đang xử lý…"))
        self.assertEqual(kq[1:], [True, "Đăng nhập", False, False])


if __name__ == "__main__":
    unittest.main()
