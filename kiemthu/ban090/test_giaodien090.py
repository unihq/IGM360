"""Bài kiểm giao diện 0.9.0 – phông nền Mẫu 1, khung (ii-c2), 02 bảng thả xuống nổi, ngăn Tài khoản và 02 lớp
(QĐ370, QĐ375, QĐ378, QĐ382, QĐ387, QĐ390, QĐ397, QĐ398; KH-090 mục 2.1–2.3, 2.6, 2.7, 2.9, 3, 5; CDA 16b điều 16).

Phần chuỗi kiểm thẳng index.html, app.js; phần hành vi chạy đoạn app.js bằng node với DOM giả tối thiểu (0 thư viện).
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"
# Bảng chữ màn 09, khối "Công tắc đăng nhập 02 lớp", cột A – anh duyệt QĐ397 (đúng từng ký tự; số dòng ở cuối)
CHU_2LOP = {
    "dangBat": "Đang bật", "dangTat": "Đang tắt",                                                              # 1
    "gat": "Bật đăng nhập 02 lớp",                                                                              # 2
    "giaiBat": "Đăng nhập trên máy mới cần thêm mã 06 số trên điện thoại.",                                     # 3
    "giaiTat": "Chỉ cần mật khẩu là vào được phần mềm.",                                                        # 4
    "baoTat": "Đăng nhập 02 lớp đang tắt: ai có mật khẩu của bạn là vào được phần mềm, gồm cả khóa kết nối và số liệu tài chính.",   # 5
    "nutBatLai": "Bật lại",                                                                                     # 5
    "hopTatTieu": "Tắt đăng nhập 02 lớp?",                                                                      # 6
    "hopTatThan": "Khi tắt, ai có mật khẩu của bạn là vào được phần mềm. Bạn nhập mật khẩu và mã 06 số đang hiện trên điện thoại để xác nhận.",   # 7
    "oMk": "Mật khẩu đang dùng", "oMa": "Mã 06 số", "huy": "Hủy", "nutTat": "Tắt 02 lớp",                      # 8
    "saiTat": "Mật khẩu hoặc mã 06 số chưa đúng.",                                                              # 9
    "hopBatTieu": "Bật lại đăng nhập 02 lớp",                                                                   # 10
    "hopBatThan": "Nhập mã 06 số đang hiện trên ứng dụng xác thực của điện thoại (máy đã cài lần trước, không cần quét lại mã QR).",   # 10
    "nutBat": "Bật lại",                                                                                        # 10
    "antoan": "Đang ở chế độ an toàn: chưa tắt được đăng nhập 02 lớp.",                                         # 11
    "daTat": "Đã tắt đăng nhập 02 lớp.", "daBat": "Đã bật lại đăng nhập 02 lớp.",                                # 13
    "hopBatDx": "Bật lại xong, mọi máy khác tự đăng xuất.",                                                     # 15
}
# Quy tắc có box-shadow trong phần CSS 0.9.0 (KH-090 mục 3; CDA 16j điểm 5: bóng thẻ đúng ảnh anh duyệt)
BONG = {".the", "#app:not(.mb) nav.menu .muc.on", "#app:not(.mb) .vung", "#app:not(.mb) .vung:has(#p08:not([hidden]))",
        "#app:not(.mb) #p08 .tc-trai,#app:not(.mb) #p08 .tc-giua", ".lop .o-nhap:focus-within",
        ".mg-p"}   # 0.10.0: bảng chọn múi giờ nổi trên khối (bản DM Chung_Banthu ĐẠT, QĐ636)


def quy_tac(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.app = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        h = cls.html
        cls.moi = h[h.index("/* 0.9.0 – phông nền Mẫu 1"):h.index("</style><link rel=\"icon\"")]
        cls.pn = h[h.index("/* <PHONGNEN> */"):h.index("/* </PHONGNEN> */")]
        cls.lop = h[h.index('<div class="pn pn1"'):h.index('<div id="san">')]

    def test_lop_phong_dung_yen_khong_nhan_bam_khong_tai_ngoai(self):
        self.assertIn('<body>\n<!-- 0.9.0 (QĐ375)', self.html)                                   # ngay sau thẻ mở body, trước #san
        self.assertTrue(self.lop.startswith('<div class="pn pn1" aria-hidden="true">'))
        self.assertLessEqual(set(re.findall(r"https?://[^\"' ]+", self.lop)), {"http://www.w3.org/2000/svg"})   # 0 địa chỉ ngoài
        self.assertNotRegex(self.lop, r">[^<\s]+<")                                               # không chữ
        qt = dict(quy_tac(self.pn))
        self.assertIn("position:fixed", qt[".pn"])
        self.assertIn("pointer-events:none", qt[".pn"])
        for cam in ("@keyframes", "animation", "transition", "backdrop-filter", "blur("):
            self.assertNotIn(cam, self.moi)
        for tep in ("index.html", "dangnhap3d.css"):
            self.assertNotIn("backdrop-filter", (GD / tep).read_text(encoding="utf-8"))
        self.assertEqual(len(quy_tac(self.pn)), 38)                                               # chép nguyên 38 quy tắc DM-05i

    def test_quy_tac_khung_chi_ap_may_tinh(self):
        ngoai = [s for s, _ in quy_tac(self.pn) if re.search(r"nav\.menu|\.vung|\.cuon|#p08|\.kh\b|#san", s) and "#app:not(.mb)" not in s
                 and "body:not(.dien-thoai)" not in s]
        self.assertEqual(ngoai, [])
        self.assertIn(("#app:not(.mb) .thanh-tren", "display:none"), quy_tac(self.pn))                 # khổ máy tính bỏ thanh trên
        self.assertIn(("#app:not(.mb) .vung", "margin:8px 8px 8px 0;border:1px solid var(--ke);border-radius:12px;overflow:hidden;"
                       "background:rgba(var(--khoi-rgb),.72);box-shadow:0 1px 2px rgba(var(--bong),.04),0 12px 32px -16px rgba(var(--bong-xanh),.25)"),
                      quy_tac(self.pn))

    def test_bong_chi_o_danh_sach_muc_3(self):
        self.assertEqual({s for s, b in quy_tac(self.moi) if "box-shadow" in b}, BONG)
        self.assertNotIn("dang-viet", self.moi)                                                    # không bóng trên chữ chạy dần

    def test_bang_tha_xuong_noi_va_thu_gon(self):                                                # KH-090 2.2 (c), (d)
        qt = dict(quy_tac(self.moi))
        self.assertEqual(qt["#app:not(.mb) nav.menu .tha"], "position:fixed;left:8px;right:auto;z-index:90;max-width:calc(100vw - 16px)")
        self.assertIn("display:none", qt["#app.thu:not(.mb) nav.menu>.vi-tri #tk-ten,#app.thu:not(.mb) nav.menu>.vi-tri .tk>svg"])
        self.assertIn(".mb .tha{position:fixed;left:8px;right:8px;width:auto;top:120px}", self.html)   # điện thoại giữ như nay
        self.assertIn("datTha(e, t); if (v) demSo(true);", self.app)   # QĐ548 B: canh theo nút bấm

    def test_a3_a4_a5_dung_lop_ve(self):                                                         # KH-090 2.9 (QĐ397)
        for d in (".o-tk .nut-gat{min-height:44px;min-width:44px;display:inline-flex;align-items:center;justify-content:center}",
                  'body.dien-thoai [data-s="tab:taikhoan"] .btn,body.dien-thoai .lop .btn,body.dien-thoai .lop .nut-ico,body.dien-thoai .bao-vang .btn{min-height:44px;min-width:44px}',
                  "body:not(.dien-thoai) .luoi-tk{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}",
                  ".lop .o-nhap:focus-within{border-color:var(--xanh-chu);box-shadow:0 0 0 3px rgba(var(--xanh-rgb),.2)}",
                  ".o-tk .nut-gat:focus-visible,.bao-vang .btn:focus-visible,.lop .btn:focus-visible,.lop .nut-ico:focus-visible{outline:2px solid var(--xanh-chu);outline-offset:2px}"):
            self.assertIn(d, self.moi)
        self.assertIn('<div class="lop" id="h-matkhau"', self.html)                               # A4 áp cả hộp Đổi mật khẩu (.lop)

    def test_l1_trang_dang_nhap_cao_du_man(self):                                                # SUA-090-L1 (CDO BT-090), ảnh chốt QĐ369 tràn sát mép
        self.assertIn("#s01{display:flex;min-height:max(640px,100vh)}", self.html)
        self.assertNotIn("100vh - 42px", self.html)
        self.assertIn("#app:not(.mb) .cuon:has(#s01:not([hidden])){overflow-y:auto}", self.html)

    def test_dieu16_chu_cong_tac_dung_bang_chu(self):
        a = self.app
        k = a[a.index("const CHU_2LOP = {"):a.index("};", a.index("const CHU_2LOP = {")) + 2]
        thay = dict(re.findall(r'^  (\w+): ("[^"]*"),', k, re.M))
        self.assertEqual({x: json.loads(y) for x, y in thay.items()}, CHU_2LOP)
        self.assertNotIn("Đang bật · bắt buộc", self.html + a)                                    # nhãn cũ đã thay (dòng 1)
        self.assertIn('<button class="btn btn-phu" data-mo="h-2lop" style="margin-top:10px">Đổi máy nhận mã</button>', self.html)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.chu = a[a.index("const esc = "):a.index("const cau = ")] + a[a.index("const cau = "):a.index("\n", a.index("const cau = ")) + 1]
        cls.ico = a[a.index("const icoMau = "):a.index("\n", a.index("const icoMau = ")) + 1]
        cls.tat = a[a.index("// <TAT2LOP>"):a.index("// </TAT2LOP>")]
        i = a.index("function doiViTri() {")
        cls.vt = a[i:a.index("\n}\n", a.index("function datTha(e, nut) {")) + 3]
        i = a.index("const vungCuon = ")
        cls.cuon = a[i:a.index("};\n", i) + 3]

    def chay(self, ma, cau):
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify(" + cau + "));"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    GIA = r"""
const ICON = {lock: '<svg stroke="#000" width="1" height="1">k</svg>', 'shield-alert': '<svg stroke="#000" width="1" height="1">sa</svg>',
  'shield-check': '<svg stroke="#000" width="1" height="1">sc</svg>'};
const o = id => ({id, hidden: false, innerHTML: '', append(x) { this.con = x; }});
// #f1-2lop: gán innerHTML thì mất các phần tử con cũ (như trình duyệt) – nút đổi máy đã chuyển vào trong mất khỏi cây
const f1 = {hidden: false, _h: '', con: null, append(x) { this.con = x; x.cha = this; },
  get innerHTML() { return this._h; }, set innerHTML(v) { this._h = v; if (this.con) { this.con.cha = null; this.con = null; } }};
const nutDoi = o('doi');
const PHAN = {'#vong-2lop': o('vong'), '#ico-2lop-tat': o('ico'), '#f1-2lop': f1, '#bao-2lop': o('bao')};
const $ = q => q === '#the-2lop [data-mo="h-2lop"]' ? (nutDoi.cha === undefined || nutDoi.cha === f1 ? nutDoi : null) : (PHAN[q] || null), D = {};
"""

    def test_ve_2lop_dang_bat_dang_tat_an_toan(self):
        ma = self.GIA + self.chu + self.ico + self.tat
        bat = self.chay(ma + "ve2Lop({da_bat_2lop: true, co_khoa_2lop: true});", "[PHAN['#f1-2lop'].innerHTML, PHAN['#bao-2lop'].hidden, nutDoi.hidden, PHAN['#vong-2lop'].hidden, D.tat2lop]")
        self.assertIn('aria-checked="true" aria-label="Bật đăng nhập 02 lớp"', bat[0])
        self.assertIn('<div class="nhan n-dat"><i></i>Đang bật</div>', bat[0])
        self.assertIn("Đăng nhập trên máy mới cần thêm mã 06&nbsp;số trên điện thoại.", bat[0])
        self.assertEqual(bat[1:], [True, False, False, False])                                     # không cảnh báo, nút đổi máy hiện
        tat = self.chay(ma + "ve2Lop({da_bat_2lop: false, co_khoa_2lop: true});", "[PHAN['#f1-2lop'].innerHTML, PHAN['#bao-2lop'].hidden, PHAN['#bao-2lop'].innerHTML, nutDoi.hidden, PHAN['#vong-2lop'].hidden, PHAN['#ico-2lop-tat'].hidden, D.tat2lop]")
        self.assertIn('aria-checked="false"', tat[0])
        self.assertIn('<div class="nhan n-canh"><i></i>Đang tắt</div>', tat[0])
        self.assertEqual((tat[1], tat[3], tat[4], tat[5], tat[6]), (False, True, True, False, True))   # QĐ398: ẩn "Đổi máy nhận mã"
        self.assertIn("data-bat2lopmo", tat[2])
        self.assertIn("số liệu tài chính.", tat[2])
        at = self.chay(ma + "D.anToan = true; ve2Lop({da_bat_2lop: true, co_khoa_2lop: true});", "PHAN['#f1-2lop'].innerHTML")
        self.assertIn(" disabled style=\"margin-left:0;opacity:.4;cursor:not-allowed\"", at)
        self.assertIn("<span>Đang ở chế độ an&nbsp;toàn: chưa tắt được đăng&nbsp;nhập 02&nbsp;lớp.</span>", at)
        at2 = self.chay(ma + "D.anToan = true; ve2Lop({da_bat_2lop: false, co_khoa_2lop: true});", "PHAN['#f1-2lop'].innerHTML")
        self.assertNotIn("disabled", at2)                                                          # đang tắt: bật vẫn được

    def test_app_js_dung_cu_phap(self):                                                        # cả tệp chạy được (node --check)
        r = subprocess.run(["node", "--check", str(GD / "app.js")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_ve_2lop_ve_lai_nhieu_lan_khong_mat_nut_doi_may(self):                           # lỗi bắt được khi xem thử
        ma = self.GIA + self.chu + self.ico + self.tat
        kq = self.chay(ma + "ve2Lop({da_bat_2lop: true, co_khoa_2lop: true}); ve2Lop({da_bat_2lop: false, co_khoa_2lop: true});"
                       " const a = [nutDoi.hidden, PHAN['#bao-2lop'].hidden]; ve2Lop({da_bat_2lop: true, co_khoa_2lop: true});",
                       "[a, nutDoi.hidden, f1.con === nutDoi]")
        self.assertEqual(kq, [[True, False], False, True])

    GIA_HOP = r"""
const CHU_DN = {dang: 'Đang xử lý…'}, ICON = {loader: '<svg stroke="#000" width="1" height="1">l</svg>'}, NB = '\u00a0', D = {};
const icoMau = s => s, ma6 = () => '123456', xoa6 = () => {}, dongHop = () => {}, demSo = () => {}, napTaiKhoan = () => {};
const bao_ = [], bao = t => bao_.push(t);
const lop = () => { const s = new Set(); return {add: x => s.add(x), remove: x => s.delete(x), contains: x => s.has(x)}; };
const el = () => ({disabled: false, hidden: false, style: {}, innerHTML: 'x', value: 'mk', classList: lop()});
const nut = el(), dong = Object.assign(el(), {hidden: false}), span = el(), onhap = el(), o6 = el();
onhap.classList.add('loi'); o6.style.borderColor = '#E22E28';
const hop = {id: 'h-tat2lop'}, hop2 = {id: 'h-2lop'};
const $ = (q, r) => q === '.hop-chan .btn-chinh' ? nut : q === 'input[type="password"]' ? el() : q === '[data-loi2lop]' ? (r === hop2 ? null : dong)
  : q === 'span' ? span : hop;
const $$ = q => q === '.o-nhap' ? [onhap] : q === '.o6' ? [o6] : [el()];
let luc_goi = null;
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);   // chép app.js dòng 12
"""

    def test_f1_mat_ket_noi_o_hop_2lop_cau_co_dau_cham(self):                               # CDA SOAT-090 F1 (bản đồ 16l)
        ma = self.GIA_HOP + self.chu + self.tat + (
            "const api = async () => { const m = new Error('Mất kết nối máy chủ, thao tác này chưa lưu được. Bạn thử lại khi đã nối\\u00a0lại');"
            " m.matKetNoi = true; throw m; };"
            "(async () => { await gui2Lop(true); await gui2Lop(false); console.log(JSON.stringify(bao_)); })();")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        cau = "Mất kết nối máy chủ, thao tác này chưa lưu được. Bạn thử lại khi đã nối\u00a0lại."   # QĐ361 + dấu chấm cuối
        self.assertEqual(json.loads(r.stdout), [cau, cau])                                         # hộp tắt và hộp bật lại

    def test_l2_l3_dang_xu_ly_khong_mo_va_bo_bao_sai_cu(self):                              # SUA-090-L2, L3 (CDO BT-090)
        self.assertIn(".lop .btn.dang{opacity:1;cursor:progress}", (GD / "index.html").read_text(encoding="utf-8"))
        ma = self.GIA_HOP + self.chu + self.tat + (
            "const api = async () => { luc_goi = {dang: nut.classList.contains('dang'), tat: nut.disabled, an: dong.hidden,"
            " loi: onhap.classList.contains('loi'), vien: o6.style.borderColor}; return {doi: true}; };"
            "(async () => { await gui2Lop(true); console.log(JSON.stringify([luc_goi, nut.classList.contains('dang')])); })();")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [{"dang": True, "tat": True, "an": True, "loi": False, "vien": ""}, False])

    def test_l4_so_di_lien_chu_va_l6_hop_doi_may_khoa_bao_nhanh(self):                       # SUA-090-L4, L6
        ma = self.GIA_HOP + self.chu + self.tat + (
            "loi2Lop(hop, {status: 400, ct: {con_lai: 4}}); const a = span.innerHTML;"
            "loi2Lop(hop2, {status: 429, message: 'khoa', ct: {loi: 'khoa'}}); console.log(JSON.stringify([a, bao_]));")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b = json.loads(r.stdout)
        self.assertIn(" Còn <b>04</b>&nbsp;lần thử: sai <b>05</b>&nbsp;lần trong 15&nbsp;phút sẽ tạm khóa <b>15</b>&nbsp;phút.", a)
        self.assertEqual(b, ["Mã 02\u00a0lớp chưa đúng. Còn 00\u00a0lần thử: sai 05\u00a0lần trong 15\u00a0phút sẽ tạm khóa 15\u00a0phút."])

    def test_doi_vi_tri_va_bang_tha(self):
        ma = r"""
const S = {xem: 'dt'};
const nav = {ten: 'nav'}, tt = {ten: 'thanh', append(x) { x.parentElement = tt; }};
const vt = {parentElement: tt}, lg = {parentElement: nav, after(x) { x.parentElement = nav; }};
const nut = {getBoundingClientRect: () => ({bottom: 112, right: 1400})}, tha = {hidden: false, style: {}, offsetWidth: 360};
const vung = {ten: 'vung', prepend(x) { x.parentElement = vung; }};
const $ = q => ({'.vi-tri': vt, 'nav.menu .logo': lg, '.thanh-tren': tt, '[data-chuong]': nut, '#app .vung': vung})[q];
""" + self.vt
        kq = self.chay(ma + "doiViTri(); const a = vt.parentElement.ten; datTha(tha); const top = tha.style['top'];"
                       " S.xem = 'mb'; doiViTri(); const b = vt.parentElement.ten; datTha(tha);", "[a, top, b, tha.style['top']]")
        self.assertEqual(kq, ["vung", "118px", "thanh", ""])   # QĐ548 B: góc phải khung nội dung; bảng ngay dưới chuông 06 px

    def test_vung_cuon_may_tinh_lay_cuon_trong(self):                                             # KH-090 2.2 (b)
        ma = r"""
const khung = {scrollHeight: 500, clientHeight: 500}, ct = {scrollHeight: 2000, clientHeight: 800}, tr = {ten: 'trang'};
const document = {scrollingElement: tr}; let S = {xem: 'dt'};
const $ = q => ({'.tc-than': khung, '#app .cuon-trong': ct})[q];
""" + self.cuon
        kq = self.chay(ma + "const a = vungCuon() === ct; S = {xem: 'mb'}; const b = vungCuon() === tr;"
                       " S = {xem: 'dt'}; khung.scrollHeight = 900; const c = vungCuon() === khung;", "[a, b, c]")
        self.assertEqual(kq, [True, True, True])


if __name__ == "__main__":
    unittest.main()
