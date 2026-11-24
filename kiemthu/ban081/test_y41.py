"""Bài kiểm 0.8.1 (Y41; QĐ249, QĐ251): thẻ Cập nhật.

Phần 1 (GAP-080): `choCapNhat` hỏi /suckhoe nhiều lần; bản đổi thì tải lại trang; quá giờ thì báo hỏng.
(0.7.9–0.8.0: câu `const het` bị nối vào chú thích nên vòng hỏi dừng sau 01 lần, thẻ quay mãi.)
Phần 2 (QĐ251, CDA phương án B): tiến độ 08 bước ở khoá phụ `tien_do` của tệp trạng thái; 01 dòng F04 tóm tắt mỗi lượt;
đủ 05 điều kiện CDA (qua antoan.ghi, ≤ 01 lần/giây, ghi lỗi không chặn, bản 0.7.9 đọc được, không ghi đôi dòng tóm tắt).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"
MA_079 = Path(__file__).resolve().parent / "ma_079"

# Môi trường giả cho choCapNhat: đồng hồ ảo, hàng đợi hẹn giờ, /suckhoe trả bản theo kịch bản
NEN_JS = r"""
let T = 0, hen = [], hoi = 0, taiLai = 0;
const S = {}, D = {capnhat: {}}, CHU_CN = {sao: {tai: 'Bước 2/2 · Đang tải bản '}, cho: 'cho'};
const phan = {textContent: ''}, $ = () => phan;
const tieuDangCn = () => {}, ve = () => {}, veQuayVe = () => {}, moHopDrive = () => {};
const location = {reload: () => { taiLai++; }};
const dongHo = {now: () => T};
const setTimeout = (f, ms) => { hen.push({luc: T + ms, f}); };
const fetch = async () => ({json: async () => { hoi++; return {phienban: KICH_BAN(hoi)}; }});
const api = async () => ({dang_sao: 'tai'});
"""
CHAY_JS = r"""
(async () => {
  choCapNhat('0.8.0', '0.8.1');
  for (let i = 0; i < 400 && hen.length; i++) {
    hen.sort((a, b) => a.luc - b.luc); const h = hen.shift(); T = h.luc; await h.f();
  }
  console.log(JSON.stringify({hoi, taiLai, cn: S.cn, phut: Math.round(T / 60e3)}));
})().catch(e => console.log(JSON.stringify({loi: String(e)})));
"""


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemChoCapNhat(unittest.TestCase):
    def chay(self, kich_ban: str) -> dict:
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("function choCapNhat("))
        b = next(i for i in range(a, len(js)) if js[i] == "}")
        ham = "\n".join(js[a:b + 1]).replace("Date.now()", "dongHo.now()")
        ma = NEN_JS + f"const KICH_BAN = {kich_ban};\n" + ham + CHAY_JS
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "cho.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertNotIn("loi", kq, kq)
        return kq

    def test_ban_doi_thi_tai_lai_trang(self):
        kq = self.chay("n => n < 25 ? '0.8.0' : '0.8.1'")             # 24 lần còn bản cũ (khoảng 02 phút), lần 25 có bản mới
        self.assertEqual((kq["hoi"], kq["taiLai"]), (25, 1))
        self.assertEqual(kq["cn"], "dangcn")

    def test_qua_gio_thi_bao_hong(self):
        kq = self.chay("n => '0.8.0'")                                # không bao giờ lên bản mới
        self.assertEqual((kq["taiLai"], kq["cn"]), (0, "hong"))
        self.assertGreater(kq["hoi"], 100)                            # hỏi suốt 15 phút (mỗi 05 giây), không dừng sau 01 lần
        self.assertEqual(kq["phut"], 15)

    def test_khong_con_khai_bao_nam_trong_chu_thich(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        for dong in js.split("\n"):
            if "//" in dong:
                self.assertNotRegex(dong.split("//", 1)[1], r"\b(const|let) het\b", dong)


# ---------------- Phần 2: tiến độ 08 bước ----------------
class NenTD(unittest.TestCase):
    def setUp(self):
        from maychu.dulieu import khoitao
        from maychu.hethong import capnhat, tiendo
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.g = Path(self.tam.name)
        self.dl = self.g / "dulieu"
        self.dl.mkdir()
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            "IGM360_CLAUDE_CLI": str(self.g / "khong_co_cli_claude"),
                                            "IGM360_CODEX_CLI": str(self.g / "khong_co_cli_codex")})
        bien.start()
        self.addCleanup(bien.stop)
        khoitao.tao_het(self.dl)
        tiendo._NHO.update(td=None, ghi_luc=0.0)
        self.addCleanup(tiendo._NHO.update, td=None, ghi_luc=0.0)
        nhip = mock.patch.object(tiendo, "NHIP_GHI_GIAY", 0.0)   # bài kiểm nhịp ghi đặt lại 01 giây riêng
        nhip.start()
        self.addCleanup(nhip.stop)
        cu = dict(capnhat._SAO)
        self.addCleanup(lambda: (capnhat._SAO.clear(), capnhat._SAO.update(cu)))

    def f04(self, lenhcon: str) -> list:
        from maychu.dulieu import ketnoi
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return [r[0] for r in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat'"
                                             " AND lenhcon = ? ORDER BY luc", (lenhcon,))]
        finally:
            cn.close()


class KiemTienDo(NenTD):
    def test_buoc_1_den_5_ban_dang_chay(self):
        from maychu.dulieu import maso
        from maychu.hethong import capnhat, tiendo
        with mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.8.9"}), \
                mock.patch.object(capnhat, "cap_nhat_ngay", return_value={"ok": True}), \
                mock.patch("maychu.ketnoi.drive.dang_noi", return_value=False):
            self.assertTrue(capnhat.yeu_cau(maso.tao(), "ngay", thumuc=self.dl, van_capnhat=True)["ok"])
            het = time.time() + 30
            while capnhat._SAO["buoc"] != "tai" and time.time() < het:
                time.sleep(0.1)
        self.assertEqual(capnhat._SAO["buoc"], "tai")
        td = tiendo.doc(self.dl)
        self.assertEqual(td["den"], "0.8.9")
        self.assertEqual([b for b in tiendo.BUOC if b in td["moc"]], ["o_trong", "chup", "gui", "tai"])   # Drive chưa nối: 0 bước 3
        self.assertEqual(td["chi_tiet"]["chup"], {"da": 7, "tong": 7, "xong": True})            # số thật: 07/07 tệp
        h = tiendo.hien(self.dl)
        self.assertEqual((h["buoc"], h["so_buoc"], h["uoc_tinh"]), ("tai", 5, True))            # bước 5 là ước tính
        self.assertTrue(0 < h["phan_tram"] < 100)

    def test_buoc_6_den_8_ban_moi_va_dong_f04(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", "2026-11-24T10:00:00+07:00", self.dl)
        for b in ("gui", "tai"):
            tiendo.sang(b, self.dl)
        tiendo._NHO["td"] = None                                       # bản mới là tiến trình khác: đọc từ tệp
        self.assertFalse(tiendo.vao_ban_moi("0.8.8", self.dl))         # lượt không phải của bản này
        self.assertTrue(tiendo.vao_ban_moi("0.8.9", self.dl))
        self.assertIn("khoidong", tiendo.doc(self.dl)["moc"])
        tiendo.chi_tiet("nang", self.dl, da=7, tong=7, xong=True)
        tiendo.sang("kiem", self.dl, da=0, tong=6)
        self.assertEqual(tiendo.hien(self.dl)["so_buoc"], 8)
        tiendo.chi_tiet("kiem", self.dl, da=6, tong=6, xong=True)
        tiendo.xong("0.8.9", self.dl)
        tiendo.xong("0.8.9", self.dl)                                  # gọi lại không ghi đôi
        tiendo._ghi_f04(tiendo.doc(self.dl), self.dl)                  # ghi thẳng lần nữa: vẫn 01 dòng
        dong = self.f04("tiendo")
        self.assertEqual(len(dong), 1)
        for k in ("0.8.0 → 0.8.9", "o_trong=", "chup=", "gui=", "tai_khoidong=", "nang=", "kiem=", "tong=",
                  "bat_dau=2026-11-24T10:00:00+07:00"):
            self.assertIn(k, dong[0])
        self.assertEqual(tiendo.hien(self.dl)["phan_tram"], 100)

    def test_lan_kiem_khong_do_cap_nhat_khong_dung(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.xong("0.8.7", self.dl)                                  # bản khác: không kết thúc lượt
        self.assertFalse(tiendo.doc(self.dl).get("xong"))
        self.assertEqual(self.f04("tiendo"), [])

    def test_trong_so_tu_f04_cac_lan_truoc(self):
        from maychu.hethong import capnhat, tiendo
        self.assertEqual(tiendo.trong_so(self.dl), {k: float(v) for k, v in tiendo.MAC_DINH_GIAY.items()})   # lần đầu: mặc định
        for i, (tk, ng) in enumerate(((200, 40), (400, 60))):
            capnhat._ghi_f04("tiendo", f"0.8.{i} → 0.8.{i + 1} · o_trong=1 chup=10 gui=2 tai_khoidong={tk} nang={ng} kiem=40"
                                       f" · tong=0 giây · bat_dau=2026-11-2{i}T10:00:00+07:00", "dat", thumuc=self.dl)
        du = tiendo.trong_so(self.dl)
        self.assertEqual((du["nang"], du["chup"], du["kiem"]), (50.0, 10.0, 40.0))
        self.assertEqual(du["tai"] + du["khoidong"], 300.0)            # trung bình (200 + 400) / 2
        self.assertEqual(du["khoidong"], float(tiendo.MAC_DINH_GIAY["khoidong"]))
        self.assertEqual(du["drive"], float(tiendo.MAC_DINH_GIAY["drive"]))   # bước chưa có số: mặc định

    def test_hien_so_do_that_va_uoc_tinh(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.chi_tiet("chup", self.dl, da=3, tong=7)
        h = tiendo.hien(self.dl)
        self.assertEqual((h["so_buoc"], h["uoc_tinh"], h["chi_tiet"]), (2, False, {"da": 3, "tong": 7}))   # có số đo thật
        tiendo.sang("nang", self.dl)
        h2 = tiendo.hien(self.dl)
        self.assertEqual((h2["so_buoc"], h2["uoc_tinh"]), (7, True))   # bước 7 chưa có số đo: ước tính theo giờ
        self.assertGreater(h2["phan_tram"], h["phan_tram"])
        tiendo.loi("tai", self.dl)
        self.assertEqual(tiendo.hien(self.dl)["loi"], "tai")

    def test_nhip_ghi_toi_da_01_lan_moi_giay(self):
        from maychu.hethong import antoan, tiendo
        with mock.patch.object(tiendo, "NHIP_GHI_GIAY", 1.0), mock.patch.object(antoan, "ghi", wraps=antoan.ghi) as g:
            tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)   # ghi 01
            t0 = time.monotonic()
            for i in range(1, 6):
                tiendo.chi_tiet("chup", self.dl, da=i, tong=7)         # không bắt buộc: trong 01 giây thì bỏ qua
            self.assertEqual(g.call_count, 1)
            tiendo.sang("gui", self.dl)                                # bắt buộc: chờ đủ 01 giây rồi ghi
            self.assertGreaterEqual(time.monotonic() - t0, 0.9)
            self.assertEqual(g.call_count, 2)
        self.assertEqual(tiendo.doc(self.dl)["chi_tiet"]["chup"]["da"], 5)   # số mới nhất trong bộ nhớ được ghi kèm

    def test_ghi_loi_khong_chan(self):
        from maychu.hethong import antoan, tiendo
        with mock.patch.object(antoan, "ghi", side_effect=OSError("đĩa giả lỗi")):
            tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
            tiendo.sang("gui", self.dl)
            tiendo.xong("0.8.9", self.dl)
        self.assertIsNone(tiendo.doc(self.dl))

    def test_api_tra_tien_do(self):
        from maychu.hethong import tiendo
        from maychu.web import api
        self.assertIsNone(api._tien_do())
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        self.assertEqual(api._tien_do()["buoc"], "chup")
        with mock.patch.object(tiendo, "hien", side_effect=ValueError("giả lỗi")):
            self.assertIsNone(api._tien_do())                          # đọc lỗi không chặn màn

    def test_chay_ghi_moc_khoi_dong(self):
        from maychu import chay
        from maychu.hethong import tiendo
        g = self.g / "app"
        g.mkdir()
        (g / "VERSION").write_text("0.8.9", encoding="utf-8")
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.sang("tai", self.dl)
        chay.moc_khoidong(self.dl, self.g / "khac")                    # ảnh khác bản: không ghi
        self.assertNotIn("khoidong", tiendo.doc(self.dl)["moc"])
        chay.moc_khoidong(self.dl, g)
        td = tiendo.doc(self.dl)
        self.assertEqual((td["buoc"], "khoidong" in td["moc"]), ("khoidong", True))
        chay.moc_khoidong(self.g / "khong_co", g)                      # không có tệp: bỏ qua, không lỗi

    def test_khoi_dong_ban_moi_ghi_buoc_7_va_ket_thuc(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.7.9", khoidong.PHIENBAN, "2026-11-24T10:00:00+07:00", self.dl)
        tiendo.sang("tai", self.dl)
        tiendo._NHO["td"] = None
        with TestClient(khoidong.app) as c:
            c.get("/suckhoe")
        td = tiendo.doc(self.dl)
        self.assertIn("nang", td["moc"])
        self.assertTrue(td.get("xong"))                                # lịch tắt: không chạy kiểm, kết thúc sau bước 7
        self.assertEqual(len(self.f04("tiendo")), 1)


class KiemWatchtower30Phut(unittest.TestCase):
    """QĐ252: watchtower chờ lệnh cập nhật tối đa 30 phút; chỉ đặt ở dịch vụ watchtower, không đụng dịch vụ igm360."""

    def test_dong_compose(self):
        dc = (GOC / "docker-compose.yml").read_text(encoding="utf-8")
        wt = dc[dc.index("\n  watchtower:"):]
        self.assertIn("\n      WATCHTOWER_HTTP_API_UPDATE_TIMEOUT: 30m\n", wt)
        self.assertEqual(dc.count("WATCHTOWER_HTTP_API_UPDATE_TIMEOUT:"), 1)


class KiemBan079DocDuoc(NenTD):
    """Điều kiện CDA: bản quay về 0.7.9 gặp tệp trạng thái có khoá phụ `tien_do` vẫn chạy và không làm mất khoá."""

    def nap(self, ten: str):
        spec = importlib.util.spec_from_file_location(f"ma079_{ten}", MA_079 / f"{ten}_079.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_antoan_079_giu_khoa_tien_do(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.1", "0.8.2", tiendo._bay(), self.dl)
        cu = self.nap("antoan")
        self.assertEqual(cu.doc(self.dl)["tien_do"]["den"], "0.8.2")
        cu.ghi(self.dl, kiem_ban="0.7.9")                              # 0.7.9 ghi mục của nó
        self.assertEqual(tiendo.doc(self.dl)["den"], "0.8.2")

    def test_chay_079_chon_va_giu_khoa(self):
        from maychu.hethong import antoan, tiendo
        tiendo.bat_dau("0.8.1", "0.8.2", tiendo._bay(), self.dl)
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "khac", "ban_truoc": "0.8.1"})   # cờ lệch ảnh: 0.7.9 bỏ cờ, ghi lại tệp
        cu = self.nap("chay")
        g = self.g / "app"
        g.mkdir()
        self.assertEqual(cu.chon(self.dl, g), g)
        tt = antoan.doc(self.dl)
        self.assertNotIn("chay_ban_truoc", tt)
        self.assertEqual(tt["tien_do"]["den"], "0.8.2")


if __name__ == "__main__":
    unittest.main()
