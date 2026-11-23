"""Bài kiểm bản 0.7.5 (QĐ178–QĐ184, PTD-08, Y31): ô chọn mô hình. Danh sách G08 theo nguồn, mặc định theo loại việc,
cổng AI gọi đúng mô hình ghim, ghim hỏng thì dùng mặc định (QĐ183), giao diện, tên mô hình ngắn. Dữ liệu giả, không gọi
CLI thật, không gọi mạng thật."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from maychu.dulieu import khoitao, ketnoi, maso
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, danhmuc_mohinh as dm, trochuyen

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        g = self.g = Path(self.tam.name)
        self.cu = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_THUMUC_CHATGPT", "CODEX_HOME")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(g / "dulieu"), IGM360_THUMUC_CHATGPT=str(g / "codex"))
        os.environ.pop("CODEX_HOME", None)
        khoitao.tao_het(g / "dulieu")
        dm._NHO.clear()
        dm._DANG_TAI.clear()
        dg._NHO_TRANGTHAI.clear()
        self.vas = [mock.patch.object(dg, "trang_thai", return_value={"da_noi": True, "goi_dang_dung": "max"})]
        for v in self.vas:
            v.start()

    def tearDown(self):
        for v in self.vas:
            v.stop()
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def nguon(self, ma, loai, uu, hang, tran=None):
        cn = ketnoi.mo("Viecnen")
        try:
            nid = maso.tao()
            cn.execute("INSERT INTO nguon_ai (id, ma, ten, loai, uutien, tran_tien_thang, hang, cach_goi, trangthai)"
                       " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dung')", (nid, ma, "Tên lưu " + ma, loai, uu, tran, hang, "cli" if loai == "goi" else hang))
        finally:
            cn.close()
        return nid

    def mh(self, nid, ma, gia=None):
        cn = ketnoi.mo("Viecnen")
        try:
            mid = maso.tao()
            cn.execute("INSERT INTO mohinh_ai (id, nguon_ai_id, ma_mohinh, gia_vao, gia_ra, tien_ma, trangthai) VALUES (?, ?, ?, ?, ?, 'USD', 'dung')",
                       (mid, nid, ma, *(gia or (None, None))))
        finally:
            cn.close()
        return mid

    def g08(self, nid):
        cn = ketnoi.mo("Viecnen")
        try:
            return [r[0] for r in cn.execute("SELECT ma_mohinh FROM mohinh_ai WHERE nguon_ai_id = ? ORDER BY rowid", (nid,))]
        finally:
            cn.close()

    def g04(self):
        cn = ketnoi.mo("Nhatky")
        try:
            return cn.execute("SELECT nguon_ai_id, mohinh_id, ketqua FROM nhatky_ai ORDER BY rowid").fetchall()
        finally:
            cn.close()


class KiemDanhSach(Nen):
    def test_goi_claude_theo_bi_danh_khong_lap(self):
        nid = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        ds = dm.danh_sach()
        self.assertEqual(self.g08(nid), ["haiku", "sonnet", "opus", "fable"])
        self.assertEqual([m["ma"] for m in ds["nhom"][0]["mohinh"]], ["haiku", "sonnet", "opus", "fable"])
        self.assertTrue(ds["nhom"][0]["chinh"])
        dm._NHO.clear()
        dm.danh_sach()
        self.assertEqual(len(self.g08(nid)), 4)   # nạp lại không thêm dòng trùng

    def test_codex_doc_tep_nho_cua_codex(self):
        nid = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        self.assertEqual(dm.danh_sach()["nhom"][0]["mohinh"], [])   # chưa có tệp: không tự đặt bảng cố định
        (self.g / "codex").mkdir()
        (self.g / "codex" / "models_cache.json").write_text(json.dumps({"fetched_at": "2026-11-23T00:00:00Z", "models": [
            {"slug": "gpt-b", "visibility": "list", "priority": 2}, {"slug": "gpt-an", "visibility": "hide", "priority": 0},
            {"slug": "gpt-a", "visibility": "list", "priority": 1}]}), encoding="utf-8")
        dm._NHO.clear()
        self.assertEqual([m["ma"] for m in dm.danh_sach()["nhom"][0]["mohinh"]], ["gpt-a", "gpt-b"])
        self.assertEqual(self.g08(nid), ["gpt-a", "gpt-b"])

    def test_khoa_api_hoi_hang_nho_24_gio(self):
        nid = self.nguon("khoa_anthropic_01", "khoa_api", 1, "anthropic", tran=10)
        luot = []

        def xu_ly(req):
            luot.append(str(req.url))
            if "anthropic" in req.url.host:
                return httpx.Response(200, json={"data": [{"id": "claude-opus-4-1"}, {"id": "claude-opus-4"}]})
            return httpx.Response(200, json={"data": [{"id": "gpt-5"}, {"id": "o3"}, {"id": "text-embedding-3"}, {"id": "gpt-4o-audio"}]})
        c = httpx.Client(transport=httpx.MockTransport(xu_ly))
        with mock.patch.object(dm.kho, "tim", return_value="k1"), mock.patch.object(dm.kho, "doc", return_value="sk-gia"):
            self.assertTrue(dm.nap({"id": nid, "ma": "khoa_anthropic_01", "loai": "khoa_api"}, client=c))
            self.assertEqual(self.g08(nid), ["claude-opus-4-1", "claude-opus-4"])
            ds = dm.danh_sach(nap_nen=False)   # còn mới (dưới 24 giờ): không hỏi lại
            self.assertEqual(len(luot), 1)
            self.assertFalse(ds["nhom"][0]["dang_tai"])
            nid2 = self.nguon("khoa_openai_01", "khoa_api", 2, "openai", tran=10)
            dm.nap({"id": nid2, "ma": "khoa_openai_01", "loai": "khoa_api"}, client=c)
            self.assertEqual(self.g08(nid2), ["gpt-5", "o3"])   # bỏ mô hình không phải trò chuyện
            loi = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
            dm._NHO.clear()
            self.assertFalse(dm.nap({"id": nid, "ma": "khoa_anthropic_01", "loai": "khoa_api"}, client=loi))
            self.assertEqual(self.g08(nid), ["claude-opus-4-1", "claude-opus-4"])   # hỏi không được: giữ danh sách cũ

    def test_chi_nguon_da_ket_noi(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.nguon("khoa_openai_01", "khoa_api", 2, "openai", tran=10)
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": False}), mock.patch.object(dm.kho, "tim", return_value=None):
            self.assertEqual(dm.danh_sach()["nhom"], [])

    def test_mac_dinh_theo_loai_viec(self):
        nid = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        dm.danh_sach()
        ids = {m["ma"]: m["id"] for m in dm.danh_sach()["nhom"][0]["mohinh"]}
        dm.dat_macdinh("trochuyen", ids["sonnet"])
        dm.dat_macdinh("dexuat", ids["opus"])
        self.assertEqual(dm.macdinh(), {"trochuyen": ids["sonnet"], "dexuat": ids["opus"]})
        dm.dat_macdinh("trochuyen", ids["opus"])   # 01 loại việc chỉ 01 mô hình
        self.assertEqual(dm.macdinh(), {"trochuyen": ids["opus"], "dexuat": ids["opus"]})
        dm.dat_macdinh("dexuat", None)
        self.assertEqual(dm.macdinh(), {"trochuyen": ids["opus"]})
        with self.assertRaises(ValueError):
            dm.dat_macdinh("khong_co", ids["opus"])
        with self.assertRaises(ValueError):
            dm.dat_macdinh("trochuyen", "khong-co-ma")
        self.assertTrue(nid)


class KiemMacDinhNguon(Nen):
    """Y31c S6 (Z10c): "Mặc định của nguồn" ở hộp "Đổi" màn 13."""

    def test_mac_dinh_cua_nguon(self):
        claude = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        khoa = self.nguon("khoa_anthropic_01", "khoa_api", 2, "anthropic", tran=10)
        self.mh(khoa, "claude-opus-4")                                   # chưa có giá
        co_gia = self.mh(khoa, "claude-sonnet-4-5", (3_000_000, 15_000_000))
        dm.dat_macdinh("dexuat", None, nguon_id=khoa)
        ct = dm.macdinh_chi_tiet()["dexuat"]
        self.assertEqual((ct["nguon_id"], ct["ma"]), (khoa, None))
        dm.dat_macdinh("trichvanban", None, nguon_id=khoa)               # dùng lại 01 dòng mặc định của nguồn
        self.assertEqual(dm.macdinh_chi_tiet()["trichvanban"]["mohinh_id"], ct["mohinh_id"])
        with mock.patch.object(dm.kho, "tim", return_value="k1"):
            ds = dm.danh_sach(nap_nen=False)
        self.assertNotIn(None, [m["ma"] for g in ds["nhom"] for m in g["mohinh"]])   # dòng mặc định không hiện là mô hình
        self.assertEqual(ds["macdinh_ct"]["dexuat"]["nguon_id"], khoa)
        ng = congai._nguon(None, "dexuat")
        self.assertEqual((ng[0]["id"], ng[0]["mohinh"]["id"]), (khoa, co_gia))   # khoá: mô hình đầu tiên đã có giá
        dm.dat_macdinh("dexuat", None, nguon_id=claude)
        ng = congai._nguon(None, "dexuat")
        self.assertEqual((ng[0]["id"], ng[0]["mohinh"]), (claude, None))         # gói: mặc định CLI
        with self.assertRaisesRegex(ValueError, "Nguồn không còn dùng được"):
            dm.dat_macdinh("dexuat", None, nguon_id="khong-co")
        dm.dat_macdinh("dexuat", None)                                   # bỏ đặt
        self.assertNotIn("dexuat", dm.macdinh_chi_tiet())

    def test_ghim_dong_mac_dinh_coi_nhu_khong_ghim(self):
        claude = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        dm.dat_macdinh("dexuat", None, nguon_id=claude)
        md = dm.macdinh_chi_tiet()["dexuat"]["mohinh_id"]
        with mock.patch.object(congai, "_goi_claude", return_value={"chu": "x", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None,
                                                                    "tien_ma": "USD", "hanmuc": {}, "mohinh_bao": None}) as g:
            kq = congai.goi("hỏi", mohinh_id=md)
        self.assertEqual(kq["ghim_hong"]["lydo"], "không còn dùng được")
        self.assertEqual(g.call_args[0][2], None)


class KiemCongAI(Nen):
    def setUp(self):
        super().setUp()
        self.claude = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.khoa = self.nguon("khoa_anthropic_01", "khoa_api", 2, "anthropic", tran=10)
        dm.danh_sach()
        self.ids = {m["ma"]: m["id"] for m in dm.danh_sach()["nhom"][0]["mohinh"]}
        self.goi = []

        def claude(tk, cau, mohinh):
            self.goi.append(("claude", mohinh))
            if mohinh == "opus" and getattr(self, "het_opus", False):
                raise congai.HetHanMuc("Opus weekly limit reached", {"tyle_tuan": 60})
            return {"chu": "Trả lời " + str(mohinh), "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {},
                    "mohinh_bao": "claude-" + (mohinh or "macdinh") + "-gia"}
        self.vas2 = [mock.patch.object(congai, "_goi_claude", side_effect=claude),
                     mock.patch.object(congai, "_goi_khoa", side_effect=lambda *a, **k: self.goi.append(("khoa", None)) or {
                         "chu": "khoá", "vao": 1, "ra": 1, "sotien": 1, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {}}),
                     mock.patch.object(congai.kho, "tim", return_value="k1")]
        for v in self.vas2:
            v.start()

    def tearDown(self):
        for v in self.vas2:
            v.stop()
        super().tearDown()

    def test_khong_ghim_goi_mac_dinh_cli(self):
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual((self.goi, kq["mohinh"], kq["ghim_hong"]), ([("claude", None)], None, None))   # gói: không truyền --model
        self.assertEqual(kq["mohinh_bao"], "claude-macdinh-gia")   # Y31c S4: mô hình công cụ báo về

    def test_mac_dinh_loai_viec(self):
        dm.dat_macdinh("trochuyen", self.ids["sonnet"])
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual((self.goi, kq["mohinh"], kq["mohinh_id"]), ([("claude", "sonnet")], "sonnet", self.ids["sonnet"]))
        congai.goi("hỏi", loai_viec="baocaosang")   # loại việc khác chưa đặt: mặc định của nguồn
        self.assertEqual(self.goi[-1], ("claude", None))

    def test_ghim_dung_mo_hinh_ghim_ghi_g04(self):
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id=self.ids["opus"])
        self.assertEqual((self.goi, kq["mohinh"], kq["ghim_hong"]), ([("claude", "opus")], "opus", None))
        self.assertEqual(self.g04()[-1], (self.claude, self.ids["opus"], "xong"))

    def test_ghim_het_han_muc_dung_mac_dinh_cung_goi(self):
        dm.dat_macdinh("trochuyen", self.ids["sonnet"])
        self.het_opus = True
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id=self.ids["opus"])
        self.assertEqual(self.goi, [("claude", "opus"), ("claude", "sonnet")])   # không chuyển sang khoá API
        self.assertEqual((kq["mohinh"], kq["nguon_id"]), ("sonnet", self.claude))
        self.assertEqual(kq["ghim_hong"], {"khoa": "goi_claude|opus", "ma": "opus", "het_hanmuc": True, "lydo": "hết hạn mức"})   # 0.7.6: khoá loại|mã
        self.assertEqual([r[2] for r in self.g04()], ["het_hanmuc", "xong"])

    def test_ghim_khoa_chua_co_gia_khong_goi(self):
        mid = self.mh(self.khoa, "claude-opus-4")   # chưa có giá (QĐ161)
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id=mid)
        self.assertEqual(self.goi, [("claude", None)])
        self.assertEqual((kq["ghim_hong"]["lydo"], kq["ghim_hong"]["het_hanmuc"]), ("chưa có giá mô hình", False))
        mid2 = self.mh(self.khoa, "claude-sonnet-4-5", (3_000_000, 15_000_000))
        self.goi.clear()
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id=mid2)
        self.assertEqual((self.goi, kq["mohinh"]), ([("khoa", None)], "claude-sonnet-4-5"))

    def test_ghim_khong_con_dung(self):
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="ma-da-xoa")
        self.assertEqual((kq["ghim_hong"]["lydo"], kq["mohinh"]), ("không còn dùng được", None))
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET trangthai = 'ngung' WHERE id = ?", (self.claude,))   # nguồn đã gỡ
        finally:
            cn.close()
        kq = congai.goi("hỏi", mohinh_id=self.ids["opus"])   # còn khoá API chưa có giá: không nguồn nào gọi được
        self.assertEqual((kq["ghim_hong"]["lydo"], "loi" in kq), ("không còn dùng được", True))
        self.assertIn({"nguon": "Mô hình đã chọn", "lydo": "không còn dùng được"}, kq["bo_qua"])

    def test_tro_chuyen_gui_kem_ghim_viec_khac_khong_doc(self):
        kq = trochuyen.gui(None, "nguoi_gia", "Chào", mohinh_id=self.ids["haiku"])
        self.assertEqual((kq["tra_loi"]["mohinh"], kq["tra_loi"]["mohinh_id"]), ("haiku", self.ids["haiku"]))
        nguon = "".join((GOC / f).read_text(encoding="utf-8") for f in ("maychu/web/api.py", "maychu/hethong/mohinh/trochuyen.py"))
        self.assertEqual(len(re.findall(r"congai\.goi\(", nguon)), 2)
        self.assertEqual(len(re.findall(r"mohinh_id=mohinh_id\)", nguon)), 1)   # Đ3: chỉ trò chuyện gửi ghim


class KiemMoHinhBaoVe(unittest.TestCase):
    """Y31c S4: đọc mô hình công cụ báo về (Claude dòng khởi đầu, Codex tệp phiên, khoá API phản hồi)."""

    def test_claude_dong_khoi_dau(self):
        ra = "\n".join(json.dumps(o) for o in (
            {"type": "system", "subtype": "init", "model": "claude-sonnet-4-5-20250929"},
            {"type": "result", "subtype": "success", "is_error": False, "result": "Chào", "usage": {"input_tokens": 1, "output_tokens": 1}}))
        with mock.patch.object(congai, "_chay", return_value=subprocess.CompletedProcess([], 0, ra, "")), \
                mock.patch.object(dg, "_env", return_value={}):
            self.assertEqual(congai._goi_claude(1, "hỏi", None)["mohinh_bao"], "claude-sonnet-4-5-20250929")
        ra2 = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "Chào", "usage": {}})
        with mock.patch.object(congai, "_chay", return_value=subprocess.CompletedProcess([], 0, ra2, "")), \
                mock.patch.object(dg, "_env", return_value={}):
            self.assertIsNone(congai._goi_claude(1, "hỏi", None)["mohinh_bao"])   # không báo: None (giao diện ghi "Mặc định")

    def test_codex_tep_phien(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sessions" / "2026" / "11" / "23"
            p.mkdir(parents=True)
            (p / "rollout-1.jsonl").write_text("\n".join(json.dumps(o) for o in (
                {"type": "session_meta", "payload": {}}, {"type": "turn_context", "payload": {"model": "gpt-5-codex"}},
                {"type": "event_msg", "payload": {"type": "token_count"}})) + "\n", encoding="utf-8")
            self.assertEqual(congai._mohinh_codex(Path(t)), "gpt-5-codex")
            (p / "rollout-1.jsonl").write_text("không phải json\n", encoding="utf-8")
            self.assertIsNone(congai._mohinh_codex(Path(t)))
        self.assertIsNone(congai._mohinh_codex(Path(tempfile.gettempdir()) / "khong_co_thu_muc_nay"))

    def test_khoa_api_phan_hoi(self):
        c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            "model": "claude-opus-4-1-20250805", "content": [{"type": "text", "text": "Chào"}], "usage": {"input_tokens": 1, "output_tokens": 1}})))
        d = {"ma": "khoa_anthropic_01", "mohinh": {"id": "m", "ma": "claude-opus-4-1", "gia_vao": 1, "gia_ra": 1, "tien_ma": "USD"}}
        with mock.patch.object(congai.kho, "tim", return_value="k"), mock.patch.object(congai.kho, "doc", return_value="sk-gia"):
            self.assertEqual(congai._goi_khoa(d, "hỏi", client=c)["mohinh_bao"], "claude-opus-4-1-20250805")


class KiemGiaoDien(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.html = (GD / "index.html").read_text(encoding="utf-8")

    def test_o_chon_theo_ban_ve(self):
        self.assertNotIn('id="tc-nguon"', self.html)                       # bỏ ô chọn nguồn đầu cuộc
        self.assertIn('<div class="tc-duoi"><div class="mh-chon" id="mh-chat"></div></div>', self.html)
        for chu in ("Tìm nguồn, mô hình…", "Chọn ở đây chỉ áp cho cuộc trò chuyện này", "Thêm nguồn AI ở mục Mô hình AI",
                    "Đang tải danh sách mô hình…", "Mô hình mặc định cho loại việc này · chỉ hiện nguồn đã kết nối",
                    "cho cuộc trò chuyện này. Cuộc khác vẫn theo mặc định.'", "Nguồn chính · ưu tiên 1", 'title="Bản cụ thể: ',
                    "' (mặc định) cho tới khi đặt lại'", "'Chọn mô hình · '", "data-doimd", "api('/mohinh/macdinh'"):
            self.assertIn(chu, self.js, chu)
        self.assertIn("#8F5F00", self.js)                                   # chữ vàng tương phản 5,5:1
        self.assertIn(".tn-meta.mh-vang{color:#8F5F00}", self.html)
        self.assertNotIn("effort", self.js.lower())                         # QĐ182: không có nút mức suy nghĩ
        ico = (GD / "icon.js").read_text(encoding="utf-8")
        self.assertIn("lucide-pin", ico)

    def test_y31b_s1_s5(self):
        self.assertIn("""$('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-chonmh" hidden>""", self.js)   # S1
        self.assertNotIn("document.body.insertAdjacentHTML", self.js)
        self.assertIn('id="h-them"', self.html)
        dong = next(x for x in self.js.splitlines() if x.startswith("const icoMau"))                       # S5
        self.assertEqual(dong, """const icoMau = (svg, mau, co) => svg.replace(/stroke="[^"]*"/, 'stroke="' + mau + '"').replace(/width="\d+"/, 'width="' + co + '"').replace(/height="\d+"/, 'height="' + co + '"');""")
        self.assertIn("icoMau(ICON.plus, '#1456F0', 16)", self.js)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_y31b_s5_chay_that(self):
        ico = (GD / "icon.js").read_text(encoding="utf-8")
        dong = next(x for x in self.js.splitlines() if x.startswith("const icoMau"))
        ma = ico + "\n" + dong + "\nconsole.log(JSON.stringify(icoMau(ICON.plus, '#1456F0', 16)));"
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        svg = json.loads(r.stdout)
        self.assertIn('stroke="#1456F0"', svg)
        self.assertNotIn('stroke="#fff"', svg)
        self.assertIn('width="16"', svg)

    def test_ghim_o_trinh_duyet_gui_kem_moi_tin(self):
        self.assertIn("const KHO_GHIM = 'igm360.ghim_mohinh';", self.js)
        self.assertIn("api('/trochuyen', {hoithoai_id: D.htId, noidung: nd, mohinh_id: gh})", self.js)
        self.assertIn("try { const g = docGhim();", self.js)               # trình duyệt chặn lưu: không lỗi

    def test_g2_g3_g5(self):
        self.assertIn("Cất&nbsp;ở&nbsp;mục&nbsp;Két&nbsp;khoá · ưu&nbsp;tiên&nbsp;", self.js)
        self.assertIn("'&nbsp;·&nbsp;<span class=\"nw\">' + esc(x.goi_ten)", self.js)
        self.assertIn("'Đăng nhập lúc&nbsp;' + esc(luc(x.dangnhap_luc))", self.js)

    def test_y31c_s3_s4(self):
        self.assertIn("'Tài' + NB + 'khoản' + NB + n.taikhoan", self.js)
        self.assertIn("const mhThucDung = x => x.mohinh_bao || x.mohinh || null;", self.js)
        self.assertIn("(mh ? tenMh(mh, n.id, n, true) : 'Mặc định')", self.js)   # 0.7.6 N3: tên ngắn
        self.assertNotIn("x.mohinh || n.mohinh_gannhat", self.js)   # không lấy mô hình gần nhất cũ
        tc = (GOC / "maychu/hethong/mohinh/trochuyen.py").read_text(encoding="utf-8")
        self.assertIn('tl["mohinh_bao"] = kq.get("mohinh_bao")', tc)

    def test_y31c_s6(self):
        for chu in ("const CHU_MD = 'Mặc định của nguồn';", "data-mhmd=", "CHU_MD.toLowerCase().includes(q)",
                    "'Đã bỏ ghim: cuộc trò chuyện này theo mặc định chung ('",
                    "'\" về mặc định của nguồn ' + tn + '.'", "{loai_viec: lv, khoa: g.khoa_md}",
                    "const onMd = dang.g && dang.g.nhom === g.nhom && (noi === 'chat' ? !dang.ghim : !dang.m);",
                    "(noi !== 'chat' || dang.ghim)", "(x && x.m ? esc(tenMh(x.m.ma, x.g.nhom, x.g)) : 'Mặc định của nguồn')"):
            self.assertIn(chu, self.js, chu)

    def test_ban(self):
        self.assertGreaterEqual(tuple(map(int, (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))), (0, 7, 5))
        muc = (GOC / "THAYDOI.md").read_text(encoding="utf-8").split("## 0.7.5", 1)[1].split("\n## ", 1)[0]
        tt = re.search(r"Tóm tắt:(.*)", muc).group(1).strip()
        self.assertLess(len(tt), 50)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemTenMoHinh(unittest.TestCase):
    """QĐ179, QĐ181: chạy đúng các hàm đặt tên trong app.js bằng node."""

    def test_ten_ngan(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        lay = lambda ten: js[js.index("const " + ten + " "):js.index("\nconst ", js.index("const " + ten + " ") + 5)]
        ham = "\n".join(lay(t) for t in ("NB", "TEN_NGUON_GOI", "TEN_NGUON_HANG", "tenNguon", "chuHoa", "laSo", "phanMh",
                                          "hangCua", "gocMh", "nhomMh", "tenHang", "tenMh", "timNguon"))
        nhom = [{"nhom": "k", "nguon_id": "k", "loai": "khoa_api", "hang": "anthropic", "mohinh": [{"ma": "claude-opus-4-1"}, {"ma": "claude-opus-4"}, {"ma": "claude-sonnet-4-5"}]},
                {"nhom": "c", "nguon_id": "c", "goi": "claude", "mohinh": [{"ma": "sonnet"}, {"ma": "opus"}]},
                {"nhom": "g", "nguon_id": "g", "goi": "chatgpt", "mohinh": [{"ma": "gpt-5.5"}, {"ma": "gpt-5"}, {"ma": "gpt-5-codex"}, {"ma": "gpt-4.1"}]}]
        thu = [["opus", "c"], ["claude-opus-4-1", "k"], ["claude-opus-4", "k"], ["claude-sonnet-4-5", "k"],
               ["gpt-5.5", "g"], ["anthropic/claude-3.5-haiku", "k"], [None, "c"],
               ["gpt-5", "g"], ["gpt-5-codex", "g"], ["gpt-4.1", "g"], ["gpt-4o", "g"], ["o3-mini", "g"]]   # Y31b S2
        ma = ("const esc = s => s; const D = {md: null, dsmh: {nhom: " + json.dumps(nhom) + "}};\n" + ham
              + "\nconsole.log(JSON.stringify(" + json.dumps(thu) + ".map(([m, n]) => tenMh(m, n))));")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["Opus", "Opus 4.1", "Opus 4", "Sonnet", "GPT-5.5", "Claude 3.5 Haiku", "mô hình mặc định",
                                                "GPT-5", "GPT-5 Codex", "GPT-4.1", "GPT-4o", "o3 Mini"])


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemTenNguonTaiKhoan(unittest.TestCase):
    """Y31c S3, S4: chạy thật tenNguon, nhanTraLoi bằng node."""

    def test_s3_s4(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        lay = lambda ten: js[js.index("const " + ten + " "):js.index("\nconst ", js.index("const " + ten + " ") + 5)]
        ham = "\n".join(lay(t) for t in ("NB", "TEN_NGUON_GOI", "TEN_NGUON_HANG", "tenNguon", "chuHoa", "laSo", "phanMh", "hangCua",
                                          "gocMh", "nhomMh", "tenHang", "tenMh", "moHinhDong", "timNguon", "mhThucDung", "tenLoai", "nhanTraLoi"))
        nguon = [{"id": "c1", "goi": "claude", "taikhoan": 1, "mohinh_gannhat": "opus"}, {"id": "c2", "goi": "claude", "taikhoan": 2}]
        ma = ("const esc = s => s; const D = {md: {nguon: " + json.dumps(nguon) + "}, dsmh: null};\n" + ham
              + "\nconst ra = [tenNguon(D.md.nguon[0]), tenNguon(D.md.nguon[1]), nhanTraLoi({nguon_id: 'c1'}),"
              + " nhanTraLoi({nguon_id: 'c1', mohinh: 'opus'}), nhanTraLoi({nguon_id: 'c2', mohinh: 'sonnet', mohinh_bao: 'claude-sonnet-4-5-20250929'})];"
              + "\nconsole.log(JSON.stringify(ra.map(s => s.replace(/\u00a0/g, ' '))));")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["Claude · Code", "Claude · Code · Tài khoản 2", "Claude · Code · Mặc định",
                                                "Claude · Code · Opus", "Claude · Code · Sonnet"])   # 0.7.6 QĐ189: dòng nguồn không ghi tài khoản


if __name__ == "__main__":
    unittest.main()
