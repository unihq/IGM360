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
        "#app:not(.mb) #p08 .tc-trai,#app:not(.mb) #p08 .tc-giua", ".lop .o-nhap:focus-within"}


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
        self.assertIn(("#app:not(.mb) .vung", "margin:8px 8px 8px 0;border:1px solid #DEE0E3;border-radius:12px;overflow:hidden;"
                       "background:rgba(255,255,255,.72);box-shadow:0 1px 2px rgba(31,35,41,.04),0 12px 32px -16px rgba(14,68,196,.25)"),
                      quy_tac(self.pn))

    def test_bong_chi_o_danh_sach_muc_3(self):
        self.assertEqual({s for s, b in quy_tac(self.moi) if "box-shadow" in b}, BONG)
        self.assertNotIn("dang-viet", self.moi)                                                    # không bóng trên chữ chạy dần

    def test_bang_tha_xuong_noi_va_thu_gon(self):                                                # KH-090 2.2 (c), (d)
        qt = dict(quy_tac(self.moi))
        self.assertEqual(qt["#app:not(.mb) nav.menu .tha"], "position:fixed;left:8px;right:auto;z-index:90;max-width:calc(100vw - 16px)")
        self.assertIn("display:none", qt["#app.thu:not(.mb) nav.menu>.vi-tri #tk-ten,#app.thu:not(.mb) nav.menu>.vi-tri .tk>svg"])
        self.assertIn(".mb .tha{position:fixed;left:8px;right:8px;width:auto;top:120px}", self.html)   # điện thoại giữ như nay
        self.assertIn("datTha(e); if (v) demSo(true);", self.app)

    def test_a3_a4_a5_dung_lop_ve(self):                                                         # KH-090 2.9 (QĐ397)
        for d in (".o-tk .nut-gat{min-height:44px;min-width:44px;display:inline-flex;align-items:center;justify-content:center}",
                  'body.dien-thoai [data-s="tab:taikhoan"] .btn,body.dien-thoai .lop .btn,body.dien-thoai .lop .nut-ico,body.dien-thoai .bao-vang .btn{min-height:44px;min-width:44px}',
                  "body:not(.dien-thoai) .luoi-tk{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}",
                  ".lop .o-nhap:focus-within{border-color:#1456F0;box-shadow:0 0 0 3px rgba(20,86,240,.2)}",
                  ".o-tk .nut-gat:focus-visible,.bao-vang .btn:focus-visible,.lop .btn:focus-visible,.lop .nut-ico:focus-visible{outline:2px solid #1456F0;outline-offset:2px}"):
            self.assertIn(d, self.moi)
        self.assertIn('<div class="lop" id="h-matkhau"', self.html)                               # A4 áp cả hộp Đổi mật khẩu (.lop)

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
        cls.vt = a[i:a.index("\n}\n", a.index("function datTha(e) {")) + 3]
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
const PHAN = {'#vong-2lop': o('vong'), '#ico-2lop-tat': o('ico'), '#f1-2lop': o('f1'), '#bao-2lop': o('bao'), '#the-2lop [data-mo="h-2lop"]': o('doi')};
const $ = q => PHAN[q] || null, D = {};
"""

    def test_ve_2lop_dang_bat_dang_tat_an_toan(self):
        ma = self.GIA + self.chu + self.ico + self.tat
        bat = self.chay(ma + "ve2Lop({da_bat_2lop: true, co_khoa_2lop: true});", "[PHAN['#f1-2lop'].innerHTML, PHAN['#bao-2lop'].hidden, PHAN['#the-2lop [data-mo=\"h-2lop\"]'].hidden, PHAN['#vong-2lop'].hidden, D.tat2lop]")
        self.assertIn('aria-checked="true" aria-label="Bật đăng nhập 02 lớp"', bat[0])
        self.assertIn('<div class="nhan n-dat"><i></i>Đang bật</div>', bat[0])
        self.assertIn("Đăng nhập trên máy mới cần thêm mã 06&nbsp;số trên điện thoại.", bat[0])
        self.assertEqual(bat[1:], [True, False, False, False])                                     # không cảnh báo, nút đổi máy hiện
        tat = self.chay(ma + "ve2Lop({da_bat_2lop: false, co_khoa_2lop: true});", "[PHAN['#f1-2lop'].innerHTML, PHAN['#bao-2lop'].hidden, PHAN['#bao-2lop'].innerHTML, PHAN['#the-2lop [data-mo=\"h-2lop\"]'].hidden, PHAN['#vong-2lop'].hidden, PHAN['#ico-2lop-tat'].hidden, D.tat2lop]")
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

    def test_doi_vi_tri_va_bang_tha(self):
        ma = r"""
const S = {xem: 'dt'};
const nav = {ten: 'nav'}, tt = {ten: 'thanh', append(x) { x.parentElement = tt; }};
const vt = {parentElement: tt}, lg = {parentElement: nav, after(x) { x.parentElement = nav; }};
const nut = {getBoundingClientRect: () => ({bottom: 112})}, tha = {hidden: false, style: {}};
const $ = q => ({'.vi-tri': vt, 'nav.menu .logo': lg, '.thanh-tren': tt, '[data-chuong]': nut})[q];
""" + self.vt
        kq = self.chay(ma + "doiViTri(); const a = vt.parentElement.ten; datTha(tha); const top = tha.style.top;"
                       " S.xem = 'mb'; doiViTri(); const b = vt.parentElement.ten; datTha(tha);", "[a, top, b, tha.style.top]")
        self.assertEqual(kq, ["nav", "120px", "thanh", ""])                                         # dưới logo; ngay dưới chuông 08 px

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
