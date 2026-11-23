"""Bài kiểm bản 0.7.8 (QĐ198, QĐ200, PTD-09 Đ1–Đ8; Y37): mã dài hạn gói Claude. Chỉ dùng mã GIẢ, CLI giả, không gọi
CLI thật, không đọc tệp đăng nhập thật. Mã giả không được lọt ra F04, G04, D03, câu trả lời API, tệp dữ liệu."""
import json
import os
import stat
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.giamsat import thongbao
from maychu.hethong.kekhoa import che as chemod, kho
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, madaihan
from kiemthu.ban075.test_y31 import Nen

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"
MA_GIA = "sk-ant-oat01-" + "Q" * 30 + "gia9KIEM"      # mã giả, đúng dạng
CUOI = MA_GIA[-4:]


class NenMa(Nen):
    def setUp(self):
        super().setUp()
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_CLAUDE": str(self.g / "claude")})
        bien.start()
        self.addCleanup(bien.stop)
        madaihan._PHIEN.clear()
        dg._NHO_TRANGTHAI.clear()

    def han(self, **kw):
        cn = ketnoi.mo("Baomat")
        try:
            cn.execute("UPDATE kekhoa SET han = ? WHERE dichvu = 'goi_claude_01'",
                       ((datetime.now(MUIGIO_VN) + timedelta(**kw)).isoformat(timespec="seconds"),))
        finally:
            cn.close()

    def khong_lot(self):
        """Mã giả không nằm chữ rõ trong tệp dữ liệu nào (Baomat chỉ có bản mã)."""
        for p in (self.g / "dulieu").rglob("*"):
            if p.is_file():
                self.assertNotIn(MA_GIA.encode(), p.read_bytes(), p.name)
                self.assertNotIn(MA_GIA[13:].encode(), p.read_bytes(), p.name)


class KiemLuuVaMoiTruong(NenMa):
    def test_che_va_hop_le(self):
        self.assertEqual(chemod.che("lỗi " + MA_GIA + " xong"), "lỗi sk-ant-oat01-•••• xong")
        self.assertTrue(madaihan.hop_le(MA_GIA))
        for sai in ("sk-ant-api03-" + "Q" * 30, "sk-ant-oat01-ngan", "", None, MA_GIA + " x"):
            self.assertFalse(madaihan.hop_le(sai), sai)

    def test_luu_lay_thay_xoa(self):
        t = madaihan.luu(1, MA_GIA)
        self.assertEqual((t["kytu_cuoi"], t["con_ngay"], t["het"], t["vang"]), (CUOI, 365, False, False))
        self.assertAlmostEqual(datetime.fromisoformat(t["han"]).timestamp(), time.time() + 365 * 86400, delta=60)
        self.assertEqual(madaihan.lay(1), MA_GIA)
        self.assertIsNone(madaihan.lay(2))
        self.khong_lot()
        moi = "sk-ant-oat01-" + "R" * 30 + "moi2"
        madaihan.luu(1, moi)                                   # Đ7: thay, không thêm dòng thứ 02
        cn = ketnoi.mo("Baomat")
        try:
            self.assertEqual(cn.execute("SELECT count(*) FROM kekhoa WHERE dichvu = 'goi_claude_01'").fetchone()[0], 1)
        finally:
            cn.close()
        self.assertEqual(madaihan.lay(1), moi)
        self.assertTrue(madaihan.xoa(1))
        self.assertIsNone(madaihan.thong_tin(1))
        with self.assertRaises(ValueError):
            madaihan.luu(1, "sk-ant-api03-" + "Q" * 30)         # Đ8: khoá API không nhận nhầm
        self.assertEqual(kho.ten_dichvu("goi_claude_02"), "Claude · Code · Tài khoản 2 · mã dài hạn")

    def test_moi_truong_dung_tai_khoan(self):
        madaihan.luu(1, MA_GIA)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "khoa-gia", "ANTHROPIC_AUTH_TOKEN": "khoa-gia-2",
                                          madaihan.BIEN: "sk-ant-oat01-" + "C" * 30}):
            e1 = dg._env("claude", 1)
            self.assertEqual(e1[madaihan.BIEN], MA_GIA)
            self.assertNotIn("ANTHROPIC_API_KEY", e1)
            self.assertNotIn("ANTHROPIC_AUTH_TOKEN", e1)
            e2 = dg._env("claude", 2)
            self.assertNotIn(madaihan.BIEN, e2)                # tài khoản 02 không dùng nhầm mã tài khoản 01
            self.assertNotIn("ANTHROPIC_API_KEY", e2)
            self.assertNotIn(madaihan.BIEN, dg._env("claude", 1, ma_daihan=False))   # đăng nhập, lấy mã: không mang mã
            self.assertEqual(dg._env("chatgpt", 1)["ANTHROPIC_API_KEY"], "khoa-gia")   # Codex không đụng

    def test_het_han_khong_goi(self):
        madaihan.luu(1, MA_GIA)
        self.han(days=6)
        t = madaihan.thong_tin(1)
        self.assertEqual((t["con_ngay"], t["vang"], t["het"]), (6, True, False))
        self.han(minutes=-1)
        self.assertTrue(madaihan.thong_tin(1)["het"])
        self.assertIsNone(madaihan.lay(1))
        nid = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        d = next(x for x in congai._nguon() if x["id"] == nid)
        self.assertEqual(congai.dung_duoc(d), (False, "mã dài hạn hết hạn"))   # Đ6

    def test_go_xoa_ma(self):
        madaihan.luu(1, MA_GIA)
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        with mock.patch.object(dg, "_dang_xuat", return_value=True):
            kq = dg.go("claude", 1)
        self.assertTrue(kq["ok"])
        self.assertIsNone(madaihan.thong_tin(1))               # Đ5

    def test_trang_thai_co_ma_la_da_noi(self):
        self.vas[0].stop()
        self.vas.remove(self.vas[0])
        madaihan.luu(1, MA_GIA)
        r = mock.Mock(stdout=json.dumps({"loggedIn": False}), stderr="", returncode=1)
        with mock.patch.object(dg.subprocess, "run", return_value=r):
            tt = dg.trang_thai("claude", 1, bo_nho=True)
        self.assertEqual((tt["da_noi"], tt.get("ma_daihan")), (True, True))


class KiemChuong(NenMa):
    def mo(self):
        cn = ketnoi.mo("Dulieu_Chinh")
        try:
            return [r[0] for r in cn.execute("SELECT khoa_chongtrung FROM canhbao WHERE trangthai IN ('moi', 'dabao', 'dagiao_task')")]
        finally:
            cn.close()

    def test_nhac_moi_ngay_07_ngay_cuoi(self):
        madaihan.luu(1, MA_GIA)
        self.han(days=8)
        thongbao.quet_madaihan()
        self.assertEqual(self.mo(), [])
        self.han(days=7)
        with thongbao._Ghi(None) as w:   # dòng của hôm qua còn mở
            thongbao._mo(w, "madaihan_saphethan:goi_claude_01:2000-01-01", "kekhoa", "goi_claude_01", nguong=7, giatri=8)
        thongbao.quet_madaihan()
        thongbao.quet_khoa()
        hom_nay = datetime.now(MUIGIO_VN).date().isoformat()
        self.assertEqual(self.mo(), [f"madaihan_saphethan:goi_claude_01:{hom_nay}"])   # 01 dòng mỗi ngày; không có dòng khoá Drive
        ds = thongbao.danh_sach()["ds"]
        self.assertEqual((ds[0]["chu"], ds[0]["di"], ds[0]["muc"]),
                         ("Mã dài hạn Gói Claude · Tài khoản 1 còn 07 ngày hết hạn", "13", "xem"))
        self.han(minutes=-1)
        thongbao.quet_madaihan()
        self.assertEqual(self.mo(), ["madaihan_hethan:goi_claude_01"])
        madaihan.xoa(1)
        thongbao.quet_madaihan()
        self.assertEqual(self.mo(), [])
        self.assertEqual(madaihan.SO_NGAY_NHAC, 7)            # QĐ200; khoá Drive vẫn 05 (thông số chung)


class KiemKetNoi(NenMa):
    def chay(self, dat=True):
        tt = [{"loggedIn": True, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"}]
        hs = {"ten_hien": "Nguoi Gia", "goi_ten": "Ultra", "mota_goi": None}
        goi = mock.Mock(return_value={"hanmuc": {"5gio": {"pct": 3, "datlai": None}}}) if dat else \
            mock.Mock(side_effect=congai.LoiAI("Claude", "lỗi khi chạy", "error_during_execution: " + MA_GIA))
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt), \
                mock.patch.object(dg, "ho_so", return_value=hs), \
                mock.patch.object(dg, "_dang_xuat", return_value=True) as dx, \
                mock.patch.object(congai, "_goi_claude", goi):
            return madaihan.ket_noi(1, MA_GIA), dx

    def f04(self):
        cn = ketnoi.mo("Nhatky")
        try:
            return [r for r in cn.execute("SELECT lenhcon, thamso_tomtat, ketqua, lydo_chan FROM nhatky_thaotac")]
        finally:
            cn.close()

    def test_kiem_that_ghi_f04_khong_lo_ma(self):
        kq, dx = self.chay()
        self.assertNotIn(MA_GIA, json.dumps(kq, ensure_ascii=False))
        self.assertEqual((kq["goi_thu"], kq["kytu_cuoi"], kq["con_ngay"]), (True, CUOI, 365))
        dx.assert_called_once()                                 # Đ8: gọi thử đạt rồi mới đăng xuất kiểu cũ
        dong = [r for r in self.f04() if r[0] == "kiem_madaihan"]
        self.assertEqual(len(dong), 1)
        for chu in ("gọi thử đạt", "authMethod oauth_token", "rate_limit_event có", "tên có/có, gói có/có", "kiểu cũ đã đăng xuất"):
            self.assertIn(chu, dong[0][1])
        self.assertNotIn("@", dong[0][1])                       # không ghi email
        self.khong_lot()

    def test_goi_thu_loi_khong_dang_xuat_che_ma(self):
        kq, dx = self.chay(dat=False)
        dx.assert_not_called()
        self.assertFalse(kq["goi_thu"])
        self.assertIn("sk-ant-oat01-••••", kq["loi_goi_thu"])
        self.assertNotIn(MA_GIA, json.dumps(kq, ensure_ascii=False))
        self.assertNotIn(MA_GIA, json.dumps(self.f04(), ensure_ascii=False))
        self.khong_lot()

    def test_api_dan_ma(self):
        from maychu.web import api
        p = {"nguoidung_id": maso.tao()}
        with self.assertRaises(HTTPException) as e:
            api.md_dan(api.MaGoi(taikhoan=1, ma="sk-ant-api03-" + "Q" * 30), p)
        self.assertEqual(e.exception.status_code, 400)
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=[{"loggedIn": False, "authMethod": ""}] * 2), \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {}}):
            kq = api.md_dan(api.MaGoi(taikhoan=1, ma=MA_GIA), p)
        self.assertNotIn(MA_GIA, json.dumps(kq, ensure_ascii=False))
        self.assertEqual(kq["kytu_cuoi"], CUOI)
        lenh = [r[0] for r in self.f04()]
        for x in ("kiem_madaihan", "luu_madaihan", "dangnhap_goi"):
            self.assertIn(x, lenh)
        self.assertFalse(hasattr(api, "md_ngat"))                 # N14: bỏ "Ngắt", dùng "Gỡ tài khoản" (QĐ164)
        self.assertNotIn(MA_GIA, json.dumps(self.f04(), ensure_ascii=False))
        self.khong_lot()

    def test_api_loi_chi_tieng_viet(self):                         # N17: câu gốc của Claude tách riêng để rê chuột
        from maychu.web import api
        p = {"nguoidung_id": maso.tao()}
        with mock.patch.object(madaihan, "gui_ma", return_value={"loi": "Mã chưa đúng hoặc đã hết hạn. Bấm Lấy link mới rồi dán mã mới.",
                                                                 "chi_tiet": "Error: invalid code"}):
            with self.assertRaises(HTTPException) as e:
                api.md_gui_ma(api.MaGoi(taikhoan=1, ma="ma-sai"), p)
        d = e.exception.detail
        self.assertEqual((d["chi_tiet"], "invalid" in d["loi"]), ("Error: invalid code", False))


CLI_GIA = r'''
import sys, os
if sys.argv[1:2] != ["setup-token"]:
    print('{"loggedIn": false}'); sys.exit(0)
link = "https://claude.ai/oauth/authorize?code=true&client_id=gia&state=gia"
sys.stdout.write("\x1b]8;;" + link + "\x07Mo trang dang nhap\x1b]8;;\x07\r\n")
sys.stdout.write("Paste code here if prompted > "); sys.stdout.flush()
ma = sys.stdin.readline().strip()
if ma != "ma-web-dung":
    sys.stdout.write("\r\nError: invalid code\r\n"); sys.stdout.flush(); sys.exit(1)
sys.stdout.write("\r\nYour OAuth token (valid for 1 year):\r\n\r\n" + os.environ["MA_GIA_IN"] + "\r\n\r\nStore this token securely.\r\n")
sys.stdout.flush()
'''


@unittest.skipUnless(madaihan.ho_tro(), "máy không có khung giả lập dòng lệnh (pty): Linux CI kiểm")
class KiemLayMaPty(NenMa):
    def setUp(self):
        super().setUp()
        p = self.g / "claude_gia"
        p.write_text(f"#!{sys.executable}\n" + textwrap.dedent(CLI_GIA))
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        bien = mock.patch.dict(os.environ, {"IGM360_CLAUDE_CLI": str(p), "MA_GIA_IN": MA_GIA})
        bien.start()
        self.addCleanup(bien.stop)
        self.addCleanup(madaihan.huy_lay, 1)

    def test_lay_ma_dung(self):
        kq = madaihan.bat_dau_lay(1, dg._env("claude", 1, ma_daihan=False))
        self.assertTrue(kq["url"].startswith("https://claude.ai/oauth/authorize"), kq)
        r = madaihan.gui_ma(1, "ma-web-dung")
        self.assertEqual(r, {"ma": MA_GIA})
        madaihan.huy_lay(1)
        self.assertFalse(madaihan.dang_lay(1))

    def test_ma_web_sai(self):
        madaihan.bat_dau_lay(1, dg._env("claude", 1, ma_daihan=False))
        r = madaihan.gui_ma(1, "ma-sai")
        self.assertIn("loi", r)
        self.assertNotIn("ma", r)
        self.assertNotIn("invalid", r["loi"].lower())               # N17: câu báo chỉ tiếng Việt
        self.assertIn("invalid code", r.get("chi_tiet", "").lower())


class KiemGiaoDien(unittest.TestCase):
    """Y37b (CDO U12, bản vẽ Z13): N11–N22."""
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.html = (GD / "index.html").read_text(encoding="utf-8")

    def test_chu_va_nut(self):
        js = self.js
        for chu in ("const CHU_MDH = 'Mã dài hạn';", "'Kết nối Claude</button>", "data-md-dan=\"' + chua.taikhoan + '\">'",   # N21
                    "'<span class=\"nhan n-canh\"><i></i>Mã hết hạn</span>'",                                                # N13
                    ">Xác nhận mã</button>", "'Lấy link mới</button>",                                                       # N16
                    "'<div class=\"bao-xanh t13\">' + ICON.info",                                                            # N18
                    "if (kq.khong_ho_tro) { D.mdh[tk] = null; veMoHinh(); moMdDan(tk, kq.loi); return; }",
                    "(k.ct ? ' title=\"' + esc(k.ct) + '\"' : '')",                                                          # N17
                    'type="password"', "if (o) o.value = '';", "tenMh(hong.dung, hong.nguon_id, null, true)",
                    " bị xoá khỏi Két&nbsp;khoá; mã vẫn còn hiệu lực ở Claude"):                                                                           # N14 + Đ5
            self.assertIn(chu, js, chu)
        self.assertNotIn("data-md-ngat", js)                                                                                  # N14
        self.assertNotIn("setup-token", js)                                                                                   # N20, QĐ135
        doan = js[js.index("const CHU_MDH"):js.index("function theGoi")].lower()
        self.assertNotIn("token", doan)
        for chu in (".mb .lop{position:fixed!important}", ".mb #h-xacnhan,.mb #h-mdh{align-items:center;padding:16px}",      # N22
                    ".md-chip.canh{border-color:#F2A7A5;color:var(--canh)}", ".md-han.canh{color:var(--canh);font-weight:600}",  # N12
                    ".md-nut{display:flex;flex-direction:column;"):                                                          # N11
            self.assertIn(chu, self.html, chu)

    @unittest.skipUnless(__import__("shutil").which("node"), "máy không có node")
    def test_ve_the_bang_node(self):
        import subprocess as sp
        doan = self.js[self.js.index("const CHU_MDH"):self.js.index("// Z13 trạng thái 6")]
        ma = ("const D = {}; const ICON = new Proxy({}, {get: () => '<svg/>'}); const icoMau = (s, m) => '[' + m + ']'; const esc = s => String(s);"
              "const ngay = iso => iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) + '/' + iso.slice(0, 4) : '';"
              "const hai = n => n < 10 && n >= 0 ? '0' + n : String(n); const cum = s => s; const cau = s => s;\n" + doan
              + "\nconst han = '2027-11-23T23:00:00+07:00', go = '<GO>';"
              + "\nconst a = theMd({taikhoan: 1, da_noi: true, ma_daihan: {kytu_cuoi: 'ab12', han, con_ngay: 5, het: false, vang: true}}, go);"
              + "\nconst a2 = theMd({taikhoan: 1, da_noi: true, ma_daihan: {kytu_cuoi: 'ab12', han, con_ngay: 200, het: false, vang: false}}, go);"
              + "\nconst b = theMd({taikhoan: 2, da_noi: true, ma_daihan: null}, go);"
              + "\nconst x = {taikhoan: 1, da_noi: false, ma_daihan: {kytu_cuoi: 'ab12', han, con_ngay: -1, het: true, vang: true}};"
              + "\nconst c = theMd(x, go), c2 = theMdHet(x);"
              + "\nconst k = theMdKetNoi(1, {url: 'https://claude.ai/oauth/authorize?x=1', loi: 'Mã chưa đúng', ct: 'Error: invalid code'});"
              + "\nconsole.log(JSON.stringify(["
              + " a.includes('md-chip canh'), a.includes('[#E22E28]'), a.includes('••••ab12'), a.includes('hết hạn 23/11/2027'), a.includes('còn 05&nbsp;ngày'),"
              + " a.includes('md-nut') && a.indexOf('md-nut') > a.indexOf('còn 05'), a.endsWith(go + '</div>'), !a.includes('data-md-ngat'),"
              + " !a2.includes('canh'), a2.includes('[#258832]'),"
              + " b.includes('Đăng nhập kiểu&nbsp;cũ'), b.includes('Chuyển sang'),"
              + " c.includes('Mã dài hạn hết hạn 23/11/2027'), c.includes('ngừng&nbsp;chạy'), c2.includes('md-het'), c2.includes('data-md-lay=\"1\"'),"
              + " k.includes('Xác nhận mã'), k.includes('Lấy link mới'), k.includes('title=\"Error: invalid code\"'), !k.includes('>Error')]));")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "the.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [True] * 20)


if __name__ == "__main__":
    unittest.main()
