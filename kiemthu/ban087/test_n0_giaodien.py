"""Bài kiểm N0 mốc 4 (QĐ344, QĐ350, QĐ352, QĐ355; CDO HINH-TC45 H1–H9; CDA T1–T4, M2, N3): giao diện lượt chạy nền,
chữ chạy dần, câu báo đang chờ cập nhật, tin bị cắt không có nút "Mở Mô hình AI".

Chạy khối `// <LUOT>` và `tinHtml` của app.js bằng node với DOM giả tối thiểu (0 thư viện); phần còn lại kiểm chuỗi.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"
CHU_CHO = "Phần mềm đang chờ cập nhật nên chưa nhận câu hỏi mới. Câu hỏi vẫn ở ô nhập, bạn gửi lại sau khi cập nhật xong."

GIA_DOM = r"""
const ICON = {tn_ai: '<svg>ai</svg>', 'circle-alert': '<svg>!</svg>', 'cloud-download': '<svg stroke="#000">cd</svg>'};
const icoMau = (svg, mau) => svg.replace(/stroke="[^"]*"/, 'stroke="' + mau + '"');
const noi = {innerHTML: ''}, bong = {querySelector: () => noi};
const khung = {scrollHeight: 1000, scrollTop: 900, clientHeight: 100};
const PHAN = {'#tn-chay': bong, '.tc-than': khung};
const trang = {scrollHeight: 2000, scrollTop: 1100, clientHeight: 900}, document = {scrollingElement: trang};
const $ = q => PHAN[q] || null;
let khung_hinh = [];
const requestAnimationFrame = f => { khung_hinh.push(f); return khung_hinh.length; };
const cancelAnimationFrame = () => {};
const chay_khung = () => { const ds = khung_hinh; khung_hinh = []; ds.forEach(f => f()); };
const D = {htId: 'cuoc-1'}, S = {}, ve = () => {};
let goi_moHt = [], goi_xong = [];
async function moHt(id) { goi_moHt.push(id); }
const ghiHong = () => {}, veNutMh = () => {}, veDsHt = () => {}, api = async () => ({hoithoai: []});
let es_cuoi = null;
class EventSource { constructor(url) { this.url = url; this.readyState = 1; es_cuoi = this; } close() { this.readyState = 2; } }
"""


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemGiaoDienLuot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (GD / "app.js").read_text(encoding="utf-8")
        cls.html = (GD / "index.html").read_text(encoding="utf-8")
        a = cls.app
        cls.chu = a[a.index("const esc = "):a.index("const cau = ")] + a[a.index("const cau = "):a.index("\n", a.index("const cau = ")) + 1]   # 0.10.1 PD25: báo lỗi qua cau()
        cls.luot = a[a.index("// <LUOT>"):a.index("// </LUOT>")]
        cls.tin = a[a.index("function tinHtml(x) {"):a.index("function veTin(ds, giu)")]

    def chay(self, ma, cau):
        r = subprocess.run(["node", "-e", GIA_DOM + self.chu + self.luot + ma + "\nconsole.log(JSON.stringify(" + cau + "));"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_h1_h7_h9_bong_bong_mo_ngay_chi_co_con_tro(self):
        h = self.chay("", "htmlChay()")
        self.assertIn('class="tn ai" id="tn-chay" aria-busy="true"', h)        # H1, H7
        self.assertIn('<p><span class="dang-viet"></span></p>', h)              # H2: chỉ con trỏ trước chữ đầu
        self.assertNotIn("tn-meta", h)                                            # H9: chưa có dòng mô hình, nút Chép
        self.assertFalse("Đang trả lời…" in self.app + self.html)                # H9: bỏ bong bóng mẫu tĩnh

    def test_t4_h3_h4_chu_thoat_tach_doan_con_tro_cuoi(self):
        kq = self.chay("LUOT.chu = '<b>x</b> & 1\\n\\nĐoạn 02'; henVe(); henVe(); const so = khung_hinh.length; chay_khung();",
                       "[so, noi.innerHTML]")
        self.assertEqual(kq[0], 1)                                                # H4: gộp mẩu, vẽ 01 lần mỗi khung hình
        self.assertEqual(kq[1], '<p>&lt;b&gt;x&lt;/b&gt; &amp; 1</p><p>Đoạn 02<span class="dang-viet"></span></p>')
        self.assertNotIn('<p class="dang-viet"', kq[1])                           # H3: không tô cả đoạn màu chữ phụ

    def test_h5_chi_bam_day_khi_dang_o_day(self):
        kq = self.chay("LUOT.chu = 'a'; veChay(); const o_day = khung.scrollTop; khung.scrollTop = 800; khung.scrollHeight = 1000;"
                       " veChay(); const da_cuon = khung.scrollTop;", "[o_day, da_cuon]")
        self.assertEqual(kq, [1000, 800])                                         # ≤ 40 px thì bám đáy; đã cuộn lên thì giữ

    def test_sua_h5_ca_trang_cuon_khi_khung_chat_khong_cuon_rieng(self):
        """CDO BT04: .tc-than không có thanh cuộn riêng (cao = nội dung) → đo và cuộn cả trang; vẫn chỉ bám khi ở đáy."""
        kq = self.chay("khung.scrollHeight = 500; khung.clientHeight = 500; khung.scrollTop = 0; LUOT.chu = 'a';"
                       " veChay(); const o_day = [trang.scrollTop, khung.scrollTop];"
                       " trang.scrollTop = 600; veChay(); const da_cuon = trang.scrollTop;", "[o_day, da_cuon]")
        self.assertEqual(kq, [[2000, 0], 600])                                    # ở đáy: bám đáy trang; đã cuộn lên: giữ
        self.assertIn("const c = vungCuon(); if (c) c.scrollTop = c.scrollHeight;   // vừa gửi: đưa tới đáy", self.app)

    def test_sua_bt7_loi_gui_ve_lai_va_tra_cau_hoi(self):
        """CDO BT25: lỗi 409, mất kết nối, 500 → vẽ lại như trước khi gửi (không treo câu hỏi, bong bóng), câu hỏi về ô nhập."""
        a = self.app
        gui = a[a.index("async function guiTin(chu) {"):a.index("\n}\n", a.index("async function guiTin(chu) {")) + 3]
        loi = {"409": "Object.assign(new Error('AI đang trả lời câu hỏi trước'), {status: 409})",
               "mang": "new TypeError('Failed to fetch')",
               "500": "Object.assign(new Error('Internal Server Error'), {status: 500})"}
        for ten, e in loi.items():
            ma = ("const o = {value: 'Câu mới'}, ds = {innerHTML: ''}; PHAN['#tc-o'] = o; PHAN['#ds-tin'] = ds;"
                  " const tinHtml = x => '<tin:' + x.noidung + '>'; const ghimKhoa = () => 'k1', luuGhim = () => {}; let bao_ra = [];"
                  " const bao = t => bao_ra.push(t); api = async () => { throw " + e + "; }; D.htId = 'h1';"
                  " D.tin = [{vai: 'nguoi', noidung: 'Cũ'}]; S.tc = 'co';" + gui +
                  " (async () => { await guiTin(); console.log(JSON.stringify({ds: ds.innerHTML, o: o.value, tc: S.tc, bao: bao_ra, es: es_cuoi === null})); })();")
            r = subprocess.run(["node", "-e", GIA_DOM.replace("api = async () => ({hoithoai: []});", "_api_bo = 0; let api = async () => ({hoithoai: []});")
                                + self.chu + self.luot + ma], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            kq = json.loads(r.stdout)
            self.assertEqual(kq["ds"], "<tin:Cũ>", ten)                           # không còn câu hỏi mới, không còn #tn-chay
            self.assertEqual((kq["o"], kq["tc"], kq["es"]), ("Câu mới", "co", True), ten)
            self.assertEqual(len(kq["bao"]), 1, ten)
            self.assertTrue(kq["bao"][0].endswith("."), ten)                       # chữ báo giữ nguyên, báo nổi thêm dấu chấm

    def test_qd361_mat_mang_bao_cau_tieng_viet(self):
        """QĐ361: fetch không tới máy chủ → api() ném lỗi mang câu đã duyệt, dải đỏ bật; guiTin báo nổi đúng câu, câu hỏi về ô nhập."""
        a = self.app
        ham_api = a[a.index("async function api(duong, than) {"):a.index("// ---- Vẽ theo trạng thái")]
        gui = a[a.index("async function guiTin(chu) {"):a.index("\n}\n", a.index("async function guiTin(chu) {")) + 3]
        ma = ("const o = {value: 'Câu mới'}, ds = {innerHTML: ''}; PHAN['#tc-o'] = o; PHAN['#ds-tin'] = ds;"
              " const tinHtml = x => '<tin>'; const ghimKhoa = () => 'k1', luuGhim = () => {}; let bao_ra = []; const bao = t => bao_ra.push(t);"
              " const fetch = async () => { throw new TypeError('Failed to fetch'); }; S.k = 'binhthuong'; S.g = '08'; D.tin = []; S.tc = 'rong';"
              + ham_api + gui +
              " (async () => { await guiTin(); console.log(JSON.stringify({bao: bao_ra, k: S.k, o: o.value, ds: ds.innerHTML})); })();")
        r = subprocess.run(["node", "-e", GIA_DOM.replace("api = async () => ({hoithoai: []});", "_bo = 0;") + self.chu + self.luot + ma],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout)
        self.assertEqual(kq["bao"], ["Mất kết nối máy chủ, thao tác này chưa lưu được. Bạn thử lại khi đã nối\u00a0lại."])   # SUA-NBSP
        self.assertEqual((kq["k"], kq["o"], kq["ds"]), ("matketnoi", "Câu mới", ""))

    def test_sua_p3_xong_luot_bam_day_hoac_giu(self):
        """CDO BT-N0b P3: xong lượt vẽ lại dài thêm (dòng nhãn, nút Chép) – đang bám đáy thì đưa xuống đáy, đã cuộn lên thì giữ."""
        a = self.app
        ve_tin = a[a.index("function veTin(ds, giu) {"):a.index("// <LUOT>")]
        xong = a[a.index("async function xongLuot("):a.index("function theoLuot(")]
        ma = ("const tinHtml = x => '<tin>'; PHAN['#ds-tin'] = {innerHTML: ''}; khung.scrollHeight = 500; khung.clientHeight = 500;"
              + ve_tin + xong.replace("async function xongLuot(", "async function xongLuot2(") +
              " const ket = [];"
              " (async () => { trang.scrollHeight = 2000; trang.scrollTop = 1100; await xongLuot2([], {}, null); ket.push(trang.scrollTop);"
              " trang.scrollTop = 300; await xongLuot2([], {}, null); ket.push(trang.scrollTop);"
              " console.log(JSON.stringify(ket)); })();")
        r = subprocess.run(["node", "-e", GIA_DOM + self.chu + self.luot + ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [2000, 300])                       # ở đáy → đáy; đã cuộn lên → giữ

    def test_t2_t3_m2_n3_su_kien_luot(self):
        ma = ("async function xongLuot(ds, tl, gh) { goi_xong.push([ds.length, tl.noidung, gh]); }"
              " theoLuot('l1', [{vai: 'nguoi'}], 'k1'); const es = es_cuoi;"
              " const gui = o => es.onmessage({data: JSON.stringify(o)});"
              " gui({loai: 'chu', them: 'Xin '}); gui({loai: 'chu', them: 'chào'}); const a = LUOT.chu;"
              " gui({loai: 'lam_lai'}); const b = LUOT.chu;"
              " gui({loai: 'chu', them: 'Mới'}); gui({loai: 'xong', tra_loi: {noidung: 'Bản đã lưu'}});"
              " const sau_xong = [LUOT.id, es.readyState];"
              " theoLuot('l2', [], null); es_cuoi.onmessage({data: JSON.stringify({loai: 'loi'})});"
              " theoLuot('l3', [], null); es_cuoi.readyState = 2; es_cuoi.onerror();")
        kq = self.chay(ma, "{url: es.url, a, b, sau_xong, goi_xong, goi_moHt}")
        self.assertEqual(kq["url"], "/api/trochuyen/luot/l1/sukien")
        self.assertEqual((kq["a"], kq["b"]), ("Xin chào", ""))                    # T3: làm lại xóa sạch chữ dở
        self.assertEqual(kq["goi_xong"], [[1, "Bản đã lưu", "k1"]])               # T2: thay bằng câu đã lưu
        self.assertEqual(kq["sau_xong"], [None, 2])                               # đóng luồng sự kiện
        self.assertEqual(kq["goi_moHt"], ["cuoc-1", "cuoc-1"])                    # N3, M2: lỗi / luồng đóng → tải lại cuộc

    def test_h1_qd352_cau_bao_cho_cap_nhat(self):
        h = self.chay("", "htmlChoCn(" + json.dumps(CHU_CHO, ensure_ascii=False) + ")")
        self.assertTrue(h.startswith('<div class="tn-bao">'))                     # khung "Cần xem", không phải tn-bao do
        self.assertIn('stroke="var(--xem)"', h)
        self.assertIn("Phần mềm đang chờ cập&nbsp;nhật nên chưa nhận câu hỏi mới. Câu hỏi vẫn ở ô nhập, bạn gửi lại sau khi"
                      " cập&nbsp;nhật xong.</span></div>", h)                  # đúng chữ QĐ352 qua cum(), không thêm dấu
        self.assertIn("if (e.ma === 'cho_capnhat') { $('#ds-tin').innerHTML = cu.map(tinHtml).join('') + toi + htmlChoCn(e.message);"
                      "\n      o.value = nd; S.tc = 'co'; ve(); return; }", self.app.replace("\r\n", "\n"))   # giữ câu hỏi ở ô nhập
        self.assertIn("e.ma = d.ma;", self.app)

    def test_qd350_tin_bi_cat_khong_co_nut(self):
        ma = self.tin.replace("function tinHtml(x) {", "function tinHtml(x) {", 1)
        kq = self.chay(ma, "[tinHtml({vai: 'hethong', noidung: 'Bị ngắt', phu: {loai: 'luot_cat'}}),"
                           " tinHtml({vai: 'hethong', noidung: 'Lỗi AI', phu: null}), tinHtml({vai: 'hethong', noidung: 'Cũ'})]")
        self.assertNotIn("Mở Mô hình AI", kq[0])
        self.assertIn("Mở Mô hình AI", kq[1])
        self.assertIn("Mở Mô hình AI", kq[2])                                     # tin cũ giữ nguyên

    def test_n5_cuoc_dang_co_luot_chay(self):
        """CDA SOAT-N0-4 N5 (cách a): máy chủ trả `trung` → câu hỏi về lại ô nhập, vẽ cuộc thật, không nghe lượt mới."""
        a = self.app
        gui = a[a.index("async function guiTin(chu) {"):a.index("\n}\n", a.index("async function guiTin(chu) {")) + 3]
        ma = ("const o = {value: 'Câu mới'}, ds = {innerHTML: ''}; PHAN['#tc-o'] = o; PHAN['#ds-tin'] = ds;"
              " const tinHtml = x => '<tin>'; const ghimKhoa = () => 'k1', luuGhim = () => {}, bao = t => { throw new Error(t); };"
              " api = async () => ({hoithoai_id: 'cuoc-2', hoi: null, luot_id: 'l-cu', trung: true}); D.tin = []; S.tc = 'co';"
              + gui +
              " (async () => { await guiTin(); console.log(JSON.stringify({o: o.value, mo: goi_moHt, es: es_cuoi === null})); })();")
        r = subprocess.run(["node", "-e", GIA_DOM.replace("const ghiHong = () => {}, veNutMh = () => {}, veDsHt = () => {}, api = async () => ({hoithoai: []});",
                                                          "const ghiHong = () => {}, veNutMh = () => {}, veDsHt = () => {}; let api = async () => ({hoithoai: []});")
                            + self.chu + self.luot + ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"o": "Câu mới", "mo": ["cuoc-2"], "es": True})

    def test_gui_nen_noi_lai_giam_chuyen_dong(self):
        self.assertIn("if (duong === '/trochuyen' && than) than = {...than, nen: true};", self.app)
        self.assertIn("if (d.luot_dang) {", self.app)                             # mở lại cuộc còn lượt chạy: nối lại
        self.assertIn("else if ('tcMoi' in d) { boLuot();", self.app)
        self.assertIn("@media (prefers-reduced-motion:reduce){.dang-viet::after{animation:none}}", self.html)   # H6
        self.assertNotIn("localStorage", self.luot)


if __name__ == "__main__":
    unittest.main()
