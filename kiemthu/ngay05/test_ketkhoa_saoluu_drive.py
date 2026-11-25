"""Bài kiểm ngày 05: két khóa (danh sách, hạn, đổi, xóa), mã hóa sao lưu, hàng chờ đẩy Drive, kết nối Google Drive
(giả lập Google bằng httpx.MockTransport, không gọi mạng), đường gọi màn 09, màn 11, logo hãng."""
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

import httpx

from maychu.dulieu import khoitao, ketnoi, saoluu
from maychu.hethong.kekhoa import khoachu, kho
from maychu.ketnoi import drive

MK = "matkhau-kiem-thu-05"
ID_UD = "123-abc.apps.googleusercontent.com"


class GoogleGia:
    """Giả lập 03 cửa của Google: đổi mã, danh sách/tạo thư mục, tải tệp (resumable)."""

    def __init__(self, phamvi=drive.PHAMVI, loi_tai=False):
        self.phamvi, self.loi_tai, self.tep, self.goi = phamvi, loi_tai, {}, []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.goi.append((req.method, str(req.url)))
        u = req.url
        if str(u).startswith(drive.URL_MA):
            f = parse_qs(req.content.decode())
            if f["grant_type"] == ["authorization_code"]:
                assert f["code"] == ["ma-tu-google"] and f["client_id"] == [ID_UD]
                return httpx.Response(200, json={"access_token": "truycap-1", "expires_in": 3600,
                                                 "refresh_token": "lammoi-bimat-9876", "scope": self.phamvi})
            assert f["refresh_token"] == ["lammoi-bimat-9876"]
            return httpx.Response(200, json={"access_token": "truycap-2", "expires_in": 3600})
        if str(u).startswith(drive.URL_API):
            assert req.headers["authorization"].startswith("Bearer truycap-")
            if req.method == "GET":
                return httpx.Response(200, json={"files": []})
            return httpx.Response(200, json={"id": "thumuc-igm360"})
        if str(u).startswith(drive.URL_TAI):
            if self.loi_tai:
                return httpx.Response(503)
            meta = json.loads(req.content)
            assert meta["parents"] == ["thumuc-igm360"]
            return httpx.Response(200, headers={"Location": "https://phien.tai/" + meta["name"]})
        if str(u).startswith("https://phien.tai/"):
            self.tep[str(u).rsplit("/", 1)[1]] = req.content
            return httpx.Response(200, json={"id": "tep"})
        return httpx.Response(404)


class KiemNgay05(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU",)}
        os.environ["IGM360_THUMUC_DULIEU"] = str(self.thumuc)
        khoitao.tao_het(self.thumuc)
        drive._TRANGTHAI.clear()
        drive._MA_TRUYCAP.clear()
        self.enterContext(mock.patch("maychu.hethong.caidat.thongso.drive_bat", return_value=True))   # 0.8.3 (QĐ277): bài cũ giả Drive bật

    def tearDown(self):
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    # ---- Két khóa ----
    def test_ket_khoa_danh_sach_han_doi_xoa(self):
        hom = date(2026, 11, 22)
        a = kho.cat("pancake", "pk-bimat-aaaa1111", self.thumuc, han="2026-11-30")
        b = kho.cat("groq", "gsk-bimat-bbbb2222", self.thumuc, han="2026-11-25")
        c = kho.cat("composio", "cp-bimat-cccc3333", self.thumuc, han="2026-11-20")
        kho.cat("khongthoihan", "kh-bimat-dddd4444", self.thumuc)
        kho.cat("totp_2lop", "noibo-khong-hien", self.thumuc)
        ds = {x["id"]: x for x in kho.danh_sach(self.thumuc, 5, hom)}
        self.assertEqual(len(ds), 4)                                  # khóa nội bộ 02 lớp không hiện
        self.assertEqual((ds[a]["tinhtrang"], ds[a]["con_ngay"]), ("dung", 8))
        self.assertEqual((ds[b]["tinhtrang"], ds[b]["con_ngay"]), ("saphet", 3))
        self.assertEqual(ds[c]["tinhtrang"], "hethan")
        self.assertIn("khong_han", {x["tinhtrang"] for x in ds.values()})
        self.assertEqual(ds[a]["kytu_cuoi"], "1111")
        self.assertNotIn("banma", ds[a])
        self.assertNotIn("bimat", json.dumps(list(ds.values())))
        kho.doi(a, "pk-moi-eeee5555", self.thumuc, han=None)
        self.assertEqual(kho.doc(a, self.thumuc), "pk-moi-eeee5555")
        self.assertEqual({x["id"]: x for x in kho.danh_sach(self.thumuc, 5, hom)}[a]["tinhtrang"], "khong_han")
        cn = ketnoi.mo("Baomat", self.thumuc)
        try:
            ban = cn.execute("SELECT banma FROM kekhoa WHERE id = ?", (a,)).fetchone()[0]
        finally:
            cn.close()
        self.assertNotIn(b"pk-moi", ban)
        kho.xoa(a, self.thumuc)
        self.assertNotIn(a, {x["id"] for x in kho.danh_sach(self.thumuc)})

    # ---- Sao lưu mã hóa ----
    def test_sao_luu_ma_hoa_giai_bang_tep_khoa_chu(self):
        luc = datetime(2026, 11, 22, 2, 5, tzinfo=saoluu.MUIGIO_VN)
        kq = saoluu.chay(self.thumuc, luc)
        self.assertEqual(kq["ketqua"], "xong_tren_may")
        noi = saoluu.thumuc_saoluu(self.thumuc) / "2026-11-22"
        tep = sorted(noi.glob("*.mahoa"))
        self.assertEqual(len(tep), 7)
        for t in tep:
            self.assertEqual(stat.S_IMODE(t.stat().st_mode), 0o600)
            self.assertFalse(t.read_bytes().startswith(b"SQLite format 3"))
        # Khôi phục ở "máy khác": chỉ có tệp .mahoa và 01 bản khóa chủ anh đã chép về
        khac = Path(tempfile.mkdtemp())
        try:
            shutil.copy(khoachu.duong(self.thumuc), khac / "IGM360_Khoachu.key")
            ra = saoluu.giai_ma_tep(noi / "Baomat.sqlite3.mahoa", khac / "IGM360_Khoachu.key", khac / "Baomat.sqlite3")
            self.assertEqual(ra.read_bytes(), (noi / "Baomat.sqlite3").read_bytes())
            cn = sqlite3.connect(ra)
            self.assertEqual(cn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            cn.close()
            (khac / "sai.key").write_bytes(b"A" * 43 + b"=")
            with self.assertRaises(Exception):
                saoluu.giai_ma_tep(noi / "Baomat.sqlite3.mahoa", khac / "sai.key", khac / "x.sqlite3")
        finally:
            shutil.rmtree(khac)
        h = ketnoi.mo("Hotho", self.thumuc)
        try:
            self.assertEqual(h.execute("SELECT count(*) FROM cho_day_drive WHERE trangthai = 'cho' AND loai = 'saoluu'").fetchone()[0], 7)
        finally:
            h.close()
        for d in kq["file"]:
            b = json.loads(d["ketqua_tungbuoc_json"])
            self.assertEqual((b["4_mahoa"], b["5_day_drive"]), ("dat", "cho_day"))

    def test_don_ban_cu_giu_tep_chua_day_drive(self):
        self.enterContext(mock.patch.object(drive, "dang_noi", return_value=True))   # 0.8.3 (QĐ283): chỉ giữ tệp chờ khi Drive đã nối
        for ngay in (18, 19, 20, 21, 22):
            saoluu.chay(self.thumuc, datetime(2026, 11, ngay, 2, 5, tzinfo=saoluu.MUIGIO_VN))
        goc = saoluu.thumuc_saoluu(self.thumuc)
        con = sorted(p.name for p in goc.iterdir() if p.is_dir() and len(p.name) == 10)
        self.assertEqual(con, ["2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"])
        self.assertEqual(sorted(x.name for x in (goc / "2026-11-18").iterdir())[0], "Baomat.sqlite3.mahoa")
        self.assertFalse(list((goc / "2026-11-18").glob("*.sqlite3")))   # bản chưa mã hóa ngày cũ đã xóa

    # ---- Google Drive ----
    def noi_drive(self, gia):
        drive.luu_ungdung(ID_UD, "bimat-ungdung", self.thumuc)
        url = drive.bat_dau("https://igm.vidu.vn/api/ketnoi/drive/vetrang", "01JDRVTEST0000000000000000", self.thumuc)
        q = parse_qs(urlparse(url).query)
        self.assertEqual(q["scope"], [drive.PHAMVI])
        self.assertEqual(q["access_type"], ["offline"])
        drive.ve_trang("ma-tu-google", q["state"][0], self.thumuc, client=httpx.Client(transport=httpx.MockTransport(gia)))
        return q["state"][0]

    def test_ket_noi_drive_cat_ket_khoa_va_chong_gia(self):
        with self.assertRaises(ValueError):
            drive.luu_ungdung("sai", "x", self.thumuc)
        with self.assertRaises(LookupError):
            drive.bat_dau("https://igm.vidu.vn/v", "01JDRVTEST0000000000000000", self.thumuc)
        gia = GoogleGia()
        st = self.noi_drive(gia)
        self.assertTrue(drive.dang_noi(self.thumuc))
        with self.assertRaises(PermissionError):                       # mã chống giả chỉ dùng 01 lần
            drive.ve_trang("ma-tu-google", st, self.thumuc, client=httpx.Client(transport=httpx.MockTransport(gia)))
        with self.assertRaises(PermissionError):
            drive.ve_trang("ma-tu-google", "gia-mao", self.thumuc)
        ds = {x["dichvu"]: x for x in kho.danh_sach(self.thumuc)}
        self.assertEqual(ds[drive.DV_LAMMOI]["kytu_cuoi"], "9876")
        self.assertEqual(kho.doc(ds[drive.DV_LAMMOI]["id"], self.thumuc), "lammoi-bimat-9876")
        tt = drive.tinh_hinh(self.thumuc)
        self.assertEqual((tt["trangthai"], tt["phien"], tt["co_ungdung"]), ("dung", "dang_noi", True))

    def test_tu_choi_khi_google_cap_sai_quyen(self):
        drive.luu_ungdung(ID_UD, "bimat-ungdung", self.thumuc)
        url = drive.bat_dau("https://igm.vidu.vn/v", "01JDRVTEST0000000000000000", self.thumuc)
        st = parse_qs(urlparse(url).query)["state"][0]
        with self.assertRaises(RuntimeError):
            drive.ve_trang("ma-tu-google", st, self.thumuc,
                           client=httpx.Client(transport=httpx.MockTransport(GoogleGia(phamvi="https://www.googleapis.com/auth/drive"))))
        self.assertFalse(drive.dang_noi(self.thumuc))

    def test_day_hang_cho_len_drive_roi_xoa_tep_tam(self):
        saoluu.chay(self.thumuc, datetime(2026, 11, 22, 2, 5, tzinfo=saoluu.MUIGIO_VN))
        self.assertEqual(drive.day_hang_cho(self.thumuc)["lydo"], "chua_ket_noi")
        gia = GoogleGia()
        self.noi_drive(gia)
        drive._MA_TRUYCAP.clear()                                       # buộc lấy mã truy cập bằng quyền dài hạn
        kq = drive.day_hang_cho(self.thumuc, client=httpx.Client(transport=httpx.MockTransport(gia)))
        self.assertEqual(kq, {"day": 7, "loi": 0})
        self.assertEqual(len(gia.tep), 7)
        self.assertIn("2026-11-22_Dulieu_Chinh.sqlite3.mahoa", gia.tep)
        noi = saoluu.thumuc_saoluu(self.thumuc) / "2026-11-22"
        self.assertFalse(list(noi.glob("*.mahoa")))                     # đẩy xong mới xóa tệp tạm
        self.assertEqual(len(list(noi.glob("*.sqlite3"))), 7)           # bản trên máy 03 ngày vẫn còn
        self.assertEqual(drive.tinh_hinh(self.thumuc)["hang_cho"], {"cho": 0, "loi": 0, "xong": 7})

    def test_day_loi_thi_thu_lai_sau(self):
        saoluu.chay(self.thumuc, datetime(2026, 11, 22, 2, 5, tzinfo=saoluu.MUIGIO_VN))
        gia = GoogleGia(loi_tai=True)
        self.noi_drive(gia)
        kq = drive.day_hang_cho(self.thumuc, client=httpx.Client(transport=httpx.MockTransport(gia)))
        self.assertEqual(kq, {"day": 0, "loi": 7})
        h = ketnoi.mo("Hotho", self.thumuc)
        try:
            d = h.execute("SELECT trangthai, so_lan_thu, lan_thu_ke, loi_ganhat FROM cho_day_drive LIMIT 1").fetchone()
        finally:
            h.close()
        self.assertEqual((d[0], d[1]), ("loi", 1))
        self.assertIn("HTTPStatusError", d[3])
        self.assertEqual(drive.day_hang_cho(self.thumuc, client=httpx.Client(transport=httpx.MockTransport(gia))),
                         {"day": 0, "loi": 0})                          # chưa tới giờ thử lại
        self.assertEqual(len(list((saoluu.thumuc_saoluu(self.thumuc) / "2026-11-22").glob("*.mahoa"))), 7)


class KiemDuongGoi(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH", "IGM360_ADMIN_USER",
                                                   "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE")}
        os.environ.update(IGM360_THUMUC_DULIEU=self.tam.name, IGM360_LICH="tat", IGM360_ADMIN_USER="chu",
                          IGM360_ADMIN_PASSWORD=MK, IGM360_COOKIE_SECURE="0")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.hethong.taikhoan import totp
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}
        kq = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": totp.ma_cua_buoc(kq["khoa"], totp.buoc())},
                    headers=self.h).raise_for_status()
        drive._TRANGTHAI.clear()

    def tearDown(self):
        from maychu.hethong.taikhoan import nguoidung
        self.c.__exit__(None, None, None)
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        nguoidung._MA_TAM.clear()
        nguoidung._BUOC_DA_DUNG.clear()
        self.tam.cleanup()

    def test_ket_khoa_qua_duong_goi(self):
        self.assertEqual(self.c.get("/api/kekhoa").json()["tong"], 0)                 # khóa 02 lớp không hiện
        self.assertEqual(self.c.post("/api/kekhoa", json={"dichvu": "groq", "giatri": "x"}).status_code, 403)   # thiếu dấu trang
        r = self.c.post("/api/kekhoa", json={"dichvu": "groq", "giatri": "gsk-bimat-12345678", "han": "2099-01-01"}, headers=self.h)
        ma = r.json()["id"]
        kq = self.c.get("/api/kekhoa").json()
        self.assertEqual((kq["tong"], kq["ds"][0]["kytu_cuoi"], kq["songay_baotruoc"]), (1, "5678", 5))
        self.assertNotIn("bimat", self.c.get("/api/kekhoa").text)
        self.assertEqual(self.c.post("/api/kekhoa", json={"dichvu": "groq", "giatri": "x", "han": "sai"}, headers=self.h).status_code, 400)
        self.assertEqual(self.c.post(f"/api/kekhoa/{ma}/doi", json={"giatri": "gsk-moi-87654321"}, headers=self.h).status_code, 200)
        self.assertEqual(self.c.get("/api/kekhoa").json()["ds"][0]["tinhtrang"], "khong_han")
        self.assertEqual(self.c.post(f"/api/kekhoa/{ma}/xoa", headers=self.h).json()["so_nguon_ngung"], 0)
        self.assertEqual(self.c.get("/api/kekhoa").json()["tong"], 0)

    def test_nguon_va_ve_trang_drive(self):
        self.assertFalse(self.c.get("/api/nguon").json()["drive"]["co_ungdung"])
        self.assertEqual(self.c.post("/api/ketnoi/drive/batdau", headers=self.h).status_code, 400)
        self.c.post("/api/ketnoi/drive/ungdung", json={"client_id": ID_UD, "client_secret": "bimat"}, headers=self.h).raise_for_status()
        url = self.c.post("/api/ketnoi/drive/batdau", headers=self.h).json()["url"]
        self.assertTrue(url.startswith(drive.URL_XIN))
        self.assertIn("redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fketnoi%2Fdrive%2Fvetrang", url)
        r = self.c.get("/api/ketnoi/drive/vetrang", params={"code": "x", "state": "gia-mao"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("/#nguon-loi", r.text)
        r = self.c.get("/api/ketnoi/drive/vetrang", params={"error": "access_denied"})
        self.assertIn("chưa cấp quyền", r.text)
        self.assertNotIn("<script", r.text)

    def test_logo_hang(self):
        r = self.c.get("/tainguyen/logo/tiktok.svg")
        self.assertEqual(r.status_code, 200)
        self.assertIn("image/svg+xml", r.headers["content-type"])
        self.assertTrue(r.text.startswith("<svg"))


if __name__ == "__main__":
    unittest.main()
