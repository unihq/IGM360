"""Bài kiểm 0.10.1 phần P5 – 03 thẻ nguồn AI màn Mô hình AI (QĐ679, QĐ680, QĐ682; CDO VE-0101-CUOI-b; phiếu PD18–PD21).

Chữ thống nhất "Kết nối" / "Chưa kết nối" cho thẻ ChatGPT như thẻ Claude (chỉ 05 chỗ ở theGoi – không sửa "Chưa đăng nhập" của
api.py, nangcli.py: đó là việc khác, CDA KT-0101b). 03 thẻ luôn 01 hàng, rộng bằng nhau; cao bằng nhau và hàng nút / dòng Chi phí
chung 01 dòng lưới (lưới con subgrid, 0 đo bằng JS); thẻ hẹp hơn 430 px dòng tài khoản xếp lại (@container).
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from kiemthu.ban0101.test_baihoc_0100 import quy_tac

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"


def doan_ham(a, dau):
    i = a.index(dau)
    return a[i:a.index("\n}\n", i) + 3]


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)
        cls.goi = doan_ham(cls.js, "function theGoi(g, ds, nguon, uu) {")

    def luat(self, chon):
        return " ".join(b for s, b in self.qt if s == chon)

    def test_pd18_chu_qd679(self):
        self.assertNotIn("Chưa đăng nhập", self.goi)
        self.assertNotIn("Đăng nhập để dùng", self.goi)
        self.assertNotIn("'Đăng nhập</button>", self.goi)
        self.assertIn("'Kết nối ChatGPT</button>", self.goi)
        self.assertIn("'Kết nối bằng tài khoản gói ChatGPT để dùng làm nguồn dự&nbsp;phòng'", self.goi)
        self.assertIn("'Kết nối Claude</button>", self.goi)
        self.assertIn("Đã kết nối", self.goi)                       # giữ
        for tep in ("maychu/web/api.py", "maychu/hethong/mohinh/nangcli.py"):   # không sửa lan (CPO PD-0101 bổ sung)
            p = GOC / tep
            if p.exists():
                self.assertIn("Chưa đăng nhập", p.read_text(encoding="utf-8"), tep)

    def test_pd19_ba_the_mot_hang(self):
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", self.luat(".luoi3"))
        self.assertIn("grid-template-columns:1fr", self.luat(".mb .goi3"))      # điện thoại 01 cột (giữ)

    def test_pd20_the_hep(self):
        self.assertIn("container-type:inline-size", self.luat("#p13 .than-goi"))   # không đặt ở thẻ: mất lưới con (đo 1280: grid-template-rows none)
        self.assertNotIn("container-type", self.luat("#p13 .goi3>.the.o-goi"))
        self.assertNotIn("@container (max-width:392px)", self.html)   # QA C06: thẻ đúng 430 (thân 392) giữ 01 hàng
        k = self.html[self.html.index("@container (width < 392px){"):]   # thẻ hẹp hơn 430 = thân hẹp hơn 392
        k = k[:k.index("}\n}") + 3] if "}\n}" in k else k[:2000]
        for x in ("#p13 .tk-dong{display:grid;grid-template-columns:28px minmax(0,1fr)", "#p13 .tk-dong>.f1{display:contents}",
                  "#p13 .tk-dong>.nhan,#p13 .tk-dong>.ttag{grid-column:1/-1;justify-self:start"):
            self.assertIn(x, k)
        self.assertNotRegex(self.html, r"(^|[}\s])\.f1\{display:contents")   # không đụng .f1 dùng chung (index.html dòng 13)

    def test_pd21_luoi_con(self):   # QĐ682 + CDO CUOI-b: cao bằng nhau, nút chính cùng đường đáy, Chi phí cùng đáy hàng nút
        self.assertIn("align-items:stretch", self.luat(".goi3"))
        t = self.luat("#p13 .goi3>.the.o-goi")
        for x in ("display:grid", "grid-row:span 3", "grid-template-rows:subgrid", "row-gap:12px"):
            self.assertIn(x, t)
        self.assertIn("align-self:start", self.luat("#p13 .o-goi>.chan-goi"))
        self.assertIn("align-self:end", self.luat("#p13 .o-goi>.kv"))
        self.assertIn("row-gap:12px", self.luat("#app:not(.mb) #p13 .goi3"))
        self.assertNotRegex(self.js, r"function canThe|offsetHeight.*chan-goi")   # 0 đo chiều cao bằng JS
        self.assertIn("'<div class=\"than-goi\">'", self.goi)
        mh = doan_ham(self.js, "function veMoHinh() {")
        self.assertIn('Phí theo lượt</div></div></div><div class="than-goi">', mh)
        self.assertIn("'</div><div class=\"kv\">", mh)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    def test_pd21_the_dung_03_con(self):   # mỗi thẻ gói đúng 03 con: đầu thẻ · thân · hàng nút
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        goi = doan_ham(a, "function theGoi(g, ds, nguon, uu) {")
        ma = ("const D = {dn: {}, mdh: {}, trung: {}, trungTk: {}, trungChu: {}}; const GOI_NGAN = {claude: 'Gói Claude', chatgpt: 'Gói ChatGPT'};"
              "const GOI_TEN = {claude: 'Claude · Code', chatgpt: 'ChatGPT · Codex'}; const CHU_MDH = 'Mã dài hạn'; const ICON = new Proxy({}, {get: () => '<svg></svg>'});"
              "const esc = s => String(s); const logoGoi = g => '<i></i>'; const oTrong = ds => 1;\n" + goi)
        dem = ("(h => { let d = 0; const con = []; const re = /<(\\/?)div\\b([^>]*)>/g; let m; while ((m = re.exec(h))) { if (m[1]) d--; else {"
               " if (d === 1) con.push((m[2].match(/class=\"([^\"]*)\"/) || [])[1] || ''); d++; } } return [con, d]; })")
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify([" + dem + "(theGoi('claude', [], [], 1)), " + dem + "(theGoi('chatgpt', [], [], 2))]));"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [[["dong", "than-goi", "dong chan-goi"], 0]] * 2)

    def test_qa_c06_03_con_moi_trang_thai(self):   # QA C06: đủ 03 con ở mọi trạng thái thẻ (lưới con 03 dòng không lệch)
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        goi = doan_ham(a, "function theGoi(g, ds, nguon, uu) {")
        khoi = "s => '<div class=\"k\">' + s + '</div>'"
        ma = ("let D; const GOI_NGAN = {claude: 'Gói Claude', chatgpt: 'Gói ChatGPT'}; const GOI_TEN = {claude: 'Claude · Code', chatgpt: 'ChatGPT · Codex'};"
              "const CHU_MDH = 'Mã dài hạn'; const ICON = new Proxy({}, {get: () => '<svg></svg>'}); const esc = s => String(s); const logoGoi = g => '<i></i>';"
              "const oTrong = ds => 1; const tieuHetMh = () => ''; const tenTk = x => 'Tài khoản ' + x.taikhoan; const dnLuc = () => 'lúc 1'; const gio = s => s; const luc = s => s;"
              "const K = " + khoi + "; const theMd = () => K('md'); const coBaoLayLai = () => true; const baoLayLai = () => K('lay'); const thanhHm = () => K('hm');"
              "const theMdHet = () => K('het'); const theMdKetNoi = () => K('mdh'); const giuTienTo = s => s; const cum = s => s; const cau = s => s; const canhTk = () => K('canh');\n" + goi)
        dem = ("(h => { let d = 0; const con = []; const re = /<(\\/?)div\\b([^>]*)>/g; let m; while ((m = re.exec(h))) { if (m[1]) d--; else {"
               " if (d === 1) con.push((m[2].match(/class=\"([^\"]*)\"/) || [])[1] || ''); d++; } } return [con, d]; })")
        moi = "() => ({dn: {}, mdh: {}, trung: {}, trungTk: {}, trungChu: {}})"
        noi = "[{taikhoan: 1, da_noi: true, ma: 'c1', mota_goi: 'Max'}]"
        ng = "[{ma: 'c1', id: 'n1', trangthai: 'dung', tyle_5gio: 10, tyle_tuan: 20, do_luc: 'x'}, {ma: 'c2', id: 'n2', trangthai: 'dung'}]"
        ca = [   # tên ca, chuẩn bị D, lời gọi
            ("chua_co", "", "theGoi('claude', [], [], 1)"),
            ("da_ket_noi", "", "theGoi('claude', " + noi + ", " + ng + ", 1)"),
            ("dang_ket_noi_md", "D.mdh = {1: {buoc: 1}};", "theGoi('claude', [], [], 1)"),
            ("dang_nhap_chatgpt", "D.dn = {chatgpt: {url: 'https://a.b', tk: 1, ma: 'AB'}};", "theGoi('chatgpt', [], [], 2)"),
            ("loi_dang_nhap_claude", "D.dn = {claude: {url: 'https://a.b', tk: 2, loi: 'Sai mã'}};", "theGoi('claude', " + noi + ", " + ng + ", 1)"),
            ("loi_chatgpt", "D.dn = {chatgpt: {url: 'https://a.b', tk: 1, ma: 'AB', loi: 'Hết giờ'}};", "theGoi('chatgpt', [], [], 2)"),
            ("hai_tai_khoan", "", "theGoi('chatgpt', [{taikhoan: 1, da_noi: true, ma: 'c1'}, {taikhoan: 2, da_noi: true, ma: 'c2'}], " + ng + ", 2)"),
            ("trung", "D.trung = {chatgpt: 1}; D.trungChu = {chatgpt: 'Trùng'};", "theGoi('chatgpt', " + noi + ", " + ng + ", 2)"),
            ("ma_het_han", "", "theGoi('claude', [{taikhoan: 1, ma: 'c1', ma_daihan: {het: true}}], [], 1)"),
        ]
        goi_ca = ", ".join("(D = (" + moi + ")(), " + (c[1].rstrip(";").replace(";", ",") if c[1] else "0") + ", " + dem + "(" + c[2] + "))" for c in ca)
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify([" + goi_ca + "]));"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout)
        for (ten, _, _), x in zip(ca, kq):
            self.assertEqual(x, [["dong", "than-goi", "dong chan-goi"], 0], ten)


if __name__ == "__main__":
    unittest.main()
