"""Bài kiểm bản 0.7.6 (QĐ187, PTD-08 Đ1, Đ5, Đ6; CDA K-MH5; bản vẽ Z11): chọn theo mô hình, không chia tài khoản.
Mã loại nguồn 01 hàm, thứ tự 03 tầng, danh sách gộp theo loại, mặc định đọc theo loại + mã, ghim thử lần lượt tài khoản
cùng loại, ghim dạng cũ đổi sang khoá; N1–N3. Dữ liệu giả, không gọi CLI thật."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, danhmuc_mohinh as dm, trochuyen
from kiemthu.ban075.test_y31 import Nen

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"


class KiemThuTu(unittest.TestCase):
    def test_ma_loai_nguon_01_ham(self):
        self.assertEqual([dg.loai_nguon({"ma": m}) for m in ("goi_claude_01", "goi_claude_02", "goi_chatgpt_01", "khoa_anthropic_01",
                                                             "khoa_openai_02", "nguon_tu_khai")],
                         ["goi_claude", "goi_claude", "goi_chatgpt", "khoa_anthropic", "khoa_openai", "nguon_tu_khai"])

    def test_thu_tu_03_tang(self):
        ds = [{"ma": "goi_claude_01", "loai": "goi", "uutien": 1}, {"ma": "goi_chatgpt_01", "loai": "goi", "uutien": 2},
              {"ma": "goi_claude_02", "loai": "goi", "uutien": 3}, {"ma": "khoa_anthropic_01", "loai": "khoa_api", "uutien": 0}]
        self.assertEqual([d["ma"] for d in dg.thu_tu(ds)], ["goi_claude_01", "goi_claude_02", "goi_chatgpt_01", "khoa_anthropic_01"])


class KiemTheoMoHinh(Nen):
    def setUp(self):
        super().setUp()
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.g1 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        self.c2 = self.nguon("goi_claude_02", "goi", 3, "anthropic")
        self.goi, self.het, self.hm_het = [], set(), {}

        def claude(tk, cau, mohinh):
            self.goi.append((tk, mohinh))
            if (tk, mohinh) in self.het or (tk, "*") in self.het:
                raise congai.HetHanMuc("limit reached", self.hm_het)
            return {"chu": "ok", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {},
                    "mohinh_bao": None}
        self.vas2 = [mock.patch.object(congai, "_goi_claude", side_effect=claude),
                     mock.patch.object(congai, "_goi_chatgpt", side_effect=lambda tk, cau, mh: self.goi.append(("gpt", mh)) or {
                         "chu": "gpt", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {},
                         "mohinh_bao": None})]
        for v in self.vas2:
            v.start()

    def tearDown(self):
        for v in self.vas2:
            v.stop()
        super().tearDown()

    def ngung(self, nid):
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET trangthai = 'ngung' WHERE id = ?", (nid,))
        finally:
            cn.close()

    def test_gop_nhom_theo_loai(self):
        ds = dm.danh_sach()
        self.assertEqual([g["nhom"] for g in ds["nhom"]], ["goi_claude", "goi_chatgpt"])   # 01 nhóm mỗi loại, thứ tự Đ5
        cl = ds["nhom"][0]
        self.assertEqual((cl["nguon_ids"], cl["khoa_md"], cl["chinh"]), ([self.c1, self.c2], "goi_claude|", True))
        self.assertEqual([m["khoa"] for m in cl["mohinh"]], ["goi_claude|haiku", "goi_claude|sonnet", "goi_claude|opus", "goi_claude|fable"])
        self.assertEqual(len(cl["mohinh"][1]["ids"]), 2)                    # sonnet của cả 02 tài khoản

    def test_mac_dinh_theo_loai_va_ma_D6(self):
        dm.danh_sach()
        dm.dat_macdinh("trochuyen", khoa="goi_claude|sonnet")
        ct = dm.macdinh_chi_tiet()["trochuyen"]
        self.assertEqual((ct["khoa"], ct["nhom"], ct["ma"], ct["mat"]), ("goi_claude|sonnet", "goi_claude", "sonnet", False))
        self.ngung(self.c1)                                                 # gỡ tài khoản đang giữ dấu
        self.assertFalse(dm.macdinh_chi_tiet()["trochuyen"]["mat"])        # tài khoản cùng loại còn: mặc định còn
        congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi[-1], (2, "sonnet"))                       # chạy trên Claude 2
        self.ngung(self.c2)
        self.assertTrue(dm.macdinh_chi_tiet()["trochuyen"]["mat"])         # cả nhóm mất: về nguồn ưu tiên 1, có báo
        self.assertIsNone(dm.macdinh_khoa("trochuyen"))
        congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi[-1], ("gpt", None))
        dm.dat_macdinh("dexuat", khoa="goi_chatgpt|")                       # mặc định của loại nguồn
        self.assertEqual(dm.macdinh_chi_tiet()["dexuat"]["khoa"], "goi_chatgpt|")
        with self.assertRaisesRegex(ValueError, "Nguồn không còn dùng được"):
            dm.dat_macdinh("dexuat", khoa="goi_claude|sonnet")

    def test_het_han_muc_sang_tai_khoan_cung_loai_D5(self):
        self.het.add((1, "*"))
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi, [(1, None), (2, None)])                  # Claude 1 hết → Claude 2, chưa sang ChatGPT
        self.assertEqual(kq["nguon_id"], self.c2)

    def test_tai_khoan_thuc_chay_QD189(self):
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual((kq["chay_tk"], kq["du_phong"]), (1, None))
        self.het.add((1, "*"))
        self.hm_het = {"5gio": {"pct": 100, "datlai": 4102444800}}       # 01/01/2100 00:00 UTC
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(kq["chay_tk"], 2)
        self.assertEqual(kq["du_phong"]["tk"], 1)
        self.assertTrue(kq["du_phong"]["den"].startswith("2100-01-01T07:00"))   # giờ Việt Nam
        tl = trochuyen.gui(None, "nguoi_gia", "Chào")["tra_loi"]
        self.assertEqual((tl["chay_tk"], tl["du_phong"]["tk"]), (2, 1))

    def test_ghim_thu_moi_tai_khoan_cung_loai_D1(self):
        dm.danh_sach()
        self.het.add((1, "opus"))
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [(1, "opus"), (2, "opus")])
        self.assertEqual((kq["nguon_id"], kq["mohinh"], kq["ghim_hong"], kq["ghim_khoa"]), (self.c2, "opus", None, "goi_claude|opus"))
        cn = ketnoi.mo("Nhatky")
        try:
            moi = cn.execute("SELECT nguon_ai_id, mohinh_id FROM nhatky_ai ORDER BY rowid DESC LIMIT 1").fetchone()
        finally:
            cn.close()
        self.assertEqual(moi, (self.c2, dm.dong_cua(self.c2, "opus")["id"]))   # G04 ghi đúng tài khoản thực chạy
        self.goi.clear()
        self.het.add((2, "opus"))
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [(1, "opus"), (2, "opus"), (1, None)])  # hết mọi tài khoản cùng loại mới về mặc định (QĐ183)
        self.assertEqual(kq["ghim_hong"], {"khoa": "goi_claude|opus", "ma": "opus", "het_hanmuc": True, "lydo": "hết hạn mức"})

    def test_ghim_dang_cu_doi_sang_khoa(self):
        dm.danh_sach()
        cu = dm.dong_cua(self.c1, "haiku")["id"]                             # id G08 của 0.7.5
        self.assertEqual(dm.chuan_khoa(cu), "goi_claude|haiku")
        self.assertIsNone(dm.chuan_khoa("goi_claude|"))                     # khoá mặc định không phải ghim
        kq = trochuyen.gui(None, "nguoi_gia", "Chào", mohinh_id=cu)
        self.assertEqual((kq["tra_loi"]["mohinh"], kq["tra_loi"]["ghim_khoa"]), ("haiku", "goi_claude|haiku"))


class KiemGiaoDien076(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")

    def test_z11_n1_n3(self):
        for chu in ("'Nhiều tài khoản cùng loại: dùng tài khoản đang chạy, hết hạn mức mới sang tài khoản dự phòng\">'",
                    "data-mhnhom=\"' + esc(g.nhom) + '\"", "data-mhchon=\"' + esc(m.khoa) + '\"", "{loai_viec: lv, khoa: x.m.khoa}",
                    "{loai_viec: lv, khoa: g.khoa_md}", "const ghimKhoa = () =>", "gh = ghimKhoa();",
                    "(MH.dich && mdLoai(MH.dich)) || {g: nhomChinh(), m: null}",                     # N1
                    "const onMd = !dang.m && dang.g && dang.g.nhom === g.nhom;",                     # N2 → U10b F1
                    "(mh ? tenMh(mh, n.id, n, true) : 'Mặc định')", "tenMh(mhThucDung(x), x.nguon_id, n, true)",   # N3
                    "' title=\"' + esc(tieuTraLoi(x)) + '\"'",
                    "const tenLoai = n => n && n.goi ? TEN_NGUON_GOI[n.goi] : tenNguon(n);",      # QĐ189: không ghi tài khoản
                    "'chạy bằng tài khoản ' + x.chay_tk", "' (dự phòng, tài khoản ' + dp.tk + ' hết hạn mức'",
                    "trên cùng phần mềm, hãng có thể khoá tài&nbsp;khoản.",                         # Z11b
                    "khác&nbsp;nhau.<br><br>Đăng nhập lại tài khoản đang kết nối thì phần mềm báo trùng, không tạo ô mới.' + canhTk(ten)",
                    "(dn.tk >= 2 ? canhTk(ten) : '')"):
            self.assertIn(chu, self.js, chu)
        self.assertNotIn("g.nguon_id === g.nguon_id", self.js)
        self.assertEqual((GOC / "VERSION").read_text(encoding="utf-8").strip(), "0.7.6")

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_n3_ten_ngan_chay_that(self):
        lay = lambda ten: self.js[self.js.index("const " + ten + " "):self.js.index("\nconst ", self.js.index("const " + ten + " ") + 5)]
        ham = "\n".join(lay(t) for t in ("NB", "TEN_NGUON_GOI", "TEN_NGUON_HANG", "tenNguon", "chuHoa", "laSo", "phanMh", "hangCua",
                                         "gocMh", "nhomMh", "tenHang", "tenMh", "timNguon"))
        nhom = [{"nhom": "goi_claude", "nguon_ids": ["c1", "c2"], "goi": "claude",
                 "mohinh": [{"ma": "sonnet"}, {"ma": "claude-sonnet-4-5"}]}]
        ma = ("const esc = s => s; const D = {md: null, dsmh: {nhom: " + json.dumps(nhom) + "}};\n" + ham
              + "\nconsole.log(JSON.stringify([tenMh('claude-sonnet-4-5-20250929', 'c2', null, true), tenMh('claude-sonnet-4-5', 'goi_claude'),"
              + " tenMh('sonnet', 'goi_claude')]));")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["Sonnet", "Sonnet 4.5", "Sonnet"])   # dòng nguồn: tên ngắn; bảng: số bản khi trùng


class KiemY34(unittest.TestCase):
    """Y34: lỗi máy chủ 0.7.5 "bấm mô hình không đổi được". Gốc lỗi: chọn mô hình ở khung chat khi loại việc "Trò chuyện AI"
    chưa đặt mặc định thì đọc `md.m.id` với `md.m` trống (TypeError, app.js:528 bản b0f6328). Thêm: bảng đang mở chỉ vẽ
    lại khi danh sách đổi; lượt tải về muộn thì bỏ. QĐ190: chọn ở khung chat đổi luôn mặc định "Trò chuyện AI"."""

    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")

    def test_u10_g1_g3(self):
        self.assertIn("Cất&nbsp;ở&nbsp;mục&nbsp;Két&nbsp;khoá</div><div class=\"t12 phu\">Ưu&nbsp;tiên&nbsp;", self.js)   # "·" không đứng đầu dòng
        html = (GD / "index.html").read_text(encoding="utf-8")
        self.assertIn(".hm{display:grid;grid-template-columns:92px 1fr minmax(40px,max-content);", html)   # "chưa đo" không tràn

    def test_khong_doc_md_m_khi_trong(self):
        self.assertNotIn("md.m.id", self.js)
        self.assertNotIn("!!md && md.m", self.js)
        khoi = self.js[self.js.index("  if (d.mhchon) {"):self.js.index("  if (d.mhmd) {")]
        self.assertNotIn("md.m", khoi)                                   # nhánh chọn mô hình không còn đọc mặc định
        for chu in ("datGhim(x.m.khoa);", "api('/mohinh/macdinh', {loai_viec: 'trochuyen', khoa: x.m.khoa})"):   # QĐ190
            self.assertIn(chu, khoi)
        khoi2 = self.js[self.js.index("  if (d.mhmd) {"):self.js.index("  if (d.doimd) {")]
        self.assertIn("api('/mohinh/macdinh', {loai_viec: 'trochuyen', khoa: g.khoa_md})", khoi2)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_chi_ve_lai_khi_doi_chay_that(self):
        i = self.js.index("let luotDs = 0;")
        ham = self.js[i:self.js.index("\n// Ghim tạm ở trình duyệt", i)]
        ma = ("const D = {dsmh: null}; let tra = []; const api = async () => { const x = tra.shift(); await new Promise(r => setTimeout(r, x.cho)); return x.d; };\n"
              + ham + "\n(async () => { const A = {nhom: [{nhom: 'goi_claude', dang_tai: false, mohinh: []}]};"
              + " const B = {nhom: [{nhom: 'goi_claude', dang_tai: false, mohinh: [{khoa: 'goi_claude|opus'}]}]};"
              + " const kq = [];"
              + " tra = [{d: A, cho: 0}]; kq.push(await napDsMh());"          # lần đầu: đổi
              + " tra = [{d: A, cho: 0}]; kq.push(await napDsMh());"          # giống hệt: không vẽ lại
              + " tra = [{d: B, cho: 50}, {d: A, cho: 0}]; const p1 = napDsMh(), p2 = napDsMh(); kq.push(await p1, await p2);"   # lượt về muộn bị bỏ
              + " kq.push(D.dsmh.nhom[0].mohinh.length); console.log(JSON.stringify(kq)); })();")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [True, False, False, False, 0])

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_md_chat_khi_chua_dat_chay_that(self):
        lay = lambda ten: self.js[self.js.index("const " + ten + " "):self.js.index("\nconst ", self.js.index("const " + ten + " ") + 5)]
        ham = "\n".join(lay(t) for t in ("nhomMh", "timMh", "nhomChinh", "mdLoai", "mdChat"))
        ma = ("const D = {dsmh: {nhom: [{nhom: 'goi_claude', chinh: true, mohinh: [{khoa: 'goi_claude|opus', ma: 'opus'}]}], macdinh_ct: {}}};\n"
              + ham + "\nconst md = mdChat(); console.log(JSON.stringify([md.g.nhom, md.m]));")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["goi_claude", None])   # đúng trạng thái làm 0.7.5 lỗi: m trống


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemU10b(unittest.TestCase):
    """U10b F1 (QĐ190): ✓ đúng mô hình nút đang ghi, "Mặc định của nguồn" chỉ ✓ khi mặc định là mặc định của nguồn.
    F2: công cụ không báo mô hình thì dòng vàng ghi tên nguồn thực chạy. Chạy thật các hàm trong app.js bằng node."""

    def chay(self, macdinh_ct: dict, sau: str) -> list:
        js = (GD / "app.js").read_text(encoding="utf-8")
        def lay(ten):
            i = js.index("const " + ten + " ")
            return js[i:js.index("\nconst ", i + 5)]
        def ham(ten):
            i = js.index("function " + ten + "(")
            j = min(x for x in (js.find("\nconst ", i), js.find("\nfunction ", i + 5), js.find("\nasync function ", i)) if x > 0)
            return js[i:j]
        phan = [lay(t) for t in ("NB", "TEN_NGUON_GOI", "TEN_NGUON_HANG", "tenNguon", "chuHoa", "laSo", "phanMh", "hangCua", "gocMh",
                                 "nhomMh", "tenHang", "tenMh", "timNguon", "mhThucDung", "tenLoai", "MH", "icoMau", "KHO_GHIM", "docGhim",
                                 "luuGhim", "ghimId", "timMh", "datGhim", "ghimKhoa", "nhomChinh", "mdLoai", "mdChat", "nbsp", "logoNhom",
                                 "chonDang", "CHU_MD", "nhomDangMo")]
        phan += [ham(t) for t in ("dangChonChat", "chuGhimHong", "dsMhHtml")]
        nhom = [{"nhom": "goi_claude", "khoa_md": "goi_claude|", "nguon_ids": ["c1"], "goi": "claude", "chinh": True, "dang_tai": False,
                 "mohinh": [{"khoa": "goi_claude|sonnet", "ma": "sonnet"}, {"khoa": "goi_claude|opus", "ma": "opus"}]},
                {"nhom": "goi_chatgpt", "khoa_md": "goi_chatgpt|", "nguon_ids": ["g1"], "goi": "chatgpt", "chinh": False, "dang_tai": False,
                 "mohinh": []}]
        nguon = [{"id": "c1", "goi": "claude", "taikhoan": 1}, {"id": "g1", "goi": "chatgpt", "taikhoan": 1}]
        ma = ("const esc = s => String(s); const ICON = new Proxy({}, {get: () => '<svg stroke=\"#000\" width=\"1\" height=\"1\"></svg>'});\n"
              "const localStorage = {d: {}, getItem(k) { return this.d[k] || null; }, setItem(k, v) { this.d[k] = v; }};\n"
              "const D = {htId: 'h1', ghimMoi: null, hong: {}, md: {nguon: " + json.dumps(nguon) + "}, dsmh: {nhom: " + json.dumps(nhom)
              + ", macdinh_ct: " + json.dumps(macdinh_ct) + "}};\n" + "\n".join(phan) + "\n" + sau)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    DEM = ("const h = dsMhHtml('chat'); const on = [...h.matchAll(/class=\"mh-dong on\" data-(mhchon|mhmd)=\"([^\"]+)\"/g)].map(m => m[2]);"
           " console.log(JSON.stringify(on));")

    def test_f1_chua_ghim_mac_dinh_la_mo_hinh(self):
        md = {"trochuyen": {"khoa": "goi_claude|opus", "nhom": "goi_claude", "ma": "opus", "mat": False}}
        self.assertEqual(self.chay(md, self.DEM), ["goi_claude|opus"])          # ✓ Opus (nút ghi Opus), không ✓ "Mặc định của nguồn"

    def test_f1_chua_ghim_mac_dinh_cua_nguon(self):
        md = {"trochuyen": {"khoa": "goi_claude|", "nhom": "goi_claude", "ma": None, "mat": False}}
        self.assertEqual(self.chay(md, self.DEM), ["goi_claude"])               # ✓ "Mặc định của nguồn"

    def test_f1_da_ghim(self):
        md = {"trochuyen": {"khoa": "goi_claude|opus", "nhom": "goi_claude", "ma": "opus", "mat": False}}
        sau = "luuGhim('h1', 'goi_claude|sonnet'); " + self.DEM
        self.assertEqual(self.chay(md, sau), ["goi_claude|sonnet"])             # ghim Sonnet: chỉ ✓ Sonnet

    def test_z10d_chu(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("' title=\"Bỏ ghim · cuộc này và các cuộc mới dùng mô hình mặc định của nguồn\"'", js)
        self.assertIn("'Đã bỏ ghim: cuộc này và các cuộc mới theo mặc định của nguồn ' + tn + '.'", js)

    def test_f2_khong_bao_mo_hinh_ghi_ten_nguon(self):
        sau = ("console.log(JSON.stringify([chuGhimHong({nguon_id: 'g1', mohinh: null, mohinh_bao: null, "
               "ghim_hong: {khoa: 'goi_claude|opus', ma: 'opus', het_hanmuc: true}})].map(s => s.replace(/\u00a0/g, ' '))));")
        self.assertEqual(self.chay({}, sau), ["Opus đang hết hạn mức, đã dùng ChatGPT · Codex (mặc định)"])


if __name__ == "__main__":
    unittest.main()
