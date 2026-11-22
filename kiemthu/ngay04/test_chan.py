"""Bài kiểm chặn đoán mật khẩu và thời hạn phiên theo QĐ90 (từng số khoá)."""
import stat
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from maychu.dulieu import ketnoi, khoitao
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.taikhoan import chan, phien

PHUT, GIO = 60, 3600
T0 = 1_800_000_000.0


class KiemChan(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.t = Path(self.tam.name)

    def tearDown(self):
        self.tam.cleanup()

    def sai(self, ip, n, tu, cach=1.0):
        kq = None
        for i in range(n):
            kq = chan.ghi_sai(ip, self.t, tu + i * cach)
        return kq

    def test_05_lan_trong_15_phut_khoa_15_phut(self):
        self.assertEqual(self.sai("1.1.1.1", 4, T0), {"con_lai": 1})
        self.assertIsNone(chan.dang_khoa("1.1.1.1", self.t, T0 + 10))
        kq = chan.ghi_sai("1.1.1.1", self.t, T0 + 10)
        self.assertEqual((kq["loai"], kq["phut"]), ("ip", 15))
        self.assertIsNotNone(chan.dang_khoa("1.1.1.1", self.t, T0 + 10 + 15 * PHUT - 1))
        self.assertIsNone(chan.dang_khoa("1.1.1.1", self.t, T0 + 10 + 15 * PHUT + 1))
        self.assertIsNone(chan.dang_khoa("2.2.2.2", self.t, T0 + 20))   # địa chỉ khác không bị khoá

    def test_sai_cach_nhau_qua_15_phut_khong_cong_don(self):
        self.sai("1.1.1.1", 4, T0)
        self.assertEqual(chan.ghi_sai("1.1.1.1", self.t, T0 + 16 * PHUT), {"con_lai": 4})

    def test_dung_thi_dem_lai(self):
        self.sai("1.1.1.1", 4, T0)
        chan.thanh_cong("1.1.1.1", self.t)
        self.assertEqual(chan.ghi_sai("1.1.1.1", self.t, T0 + 10), {"con_lai": 4})

    def test_khoa_lai_trong_24_gio_gap_doi_toi_da_24_gio(self):
        import json
        luc, ds = T0, []
        for _ in range(9):
            self.sai("1.1.1.1", 5, luc)
            r = json.loads((self.t / chan.TEN_TEP).read_text())["ip"]["1.1.1.1"]   # khoá theo địa chỉ (khoá tài khoản tính riêng)
            ds.append(r["phut"])
            luc = r["khoa_den"] + 1
        self.assertEqual(ds, [15, 30, 60, 120, 240, 480, 960, 1440, 1440])

    def test_24_gio_khong_sai_thi_dem_lai(self):
        kq = self.sai("1.1.1.1", 5, T0)
        kq = self.sai("1.1.1.1", 5, kq["den"] + 1)
        self.assertEqual(kq["phut"], 30)
        kq = self.sai("1.1.1.1", 5, kq["den"] + 24 * GIO + 1)
        self.assertEqual(kq["phut"], 15)
        kq2 = self.sai("1.1.1.1", 5, kq["den"] + 23 * GIO)   # lại trong 24 giờ sau lần khoá trước: gấp đôi
        self.assertEqual(kq2["phut"], 30)

    def test_20_lan_moi_dia_chi_khoa_tai_khoan_01_gio(self):
        luc = T0
        for i in range(4):
            self.sai(f"10.0.0.{i}", 4, luc)
            luc += 10 * PHUT
        self.assertIsNone(chan.dang_khoa("10.0.0.9", self.t, luc))
        self.sai("10.0.0.5", 3, luc)
        kq = chan.ghi_sai("10.0.0.6", self.t, luc + 5)   # lần sai thứ 20 trong 24 giờ
        self.assertEqual((kq["loai"], kq["phut"]), ("taikhoan", 60))
        self.assertEqual(chan.dang_khoa("10.0.0.99", self.t, luc + 6)["loai"], "taikhoan")
        self.assertIsNone(chan.dang_khoa("10.0.0.99", self.t, luc + 5 + GIO + 1))

    def test_sai_qua_24_gio_khong_tinh_cho_tai_khoan(self):
        self.sai("1.1.1.1", 4, T0)
        for i in range(15):
            chan.ghi_sai(f"9.9.9.{i}", self.t, T0 + 24 * GIO + 10 + i)
        self.assertIsNone(chan.dang_khoa("8.8.8.8", self.t, T0 + 24 * GIO + 100))

    def test_xoa_het_mo_khoa_ngay_va_tep_quyen_600(self):
        self.sai("1.1.1.1", 5, T0)
        self.assertEqual(stat.S_IMODE((self.t / chan.TEN_TEP).stat().st_mode), 0o600)
        chan.xoa_het(self.t)
        self.assertIsNone(chan.dang_khoa("1.1.1.1", self.t, T0 + 10))


class KiemThoiHanPhien(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.t = Path(self.tam.name)
        khoitao.tao_het(self.t)
        cn = ketnoi.mo("Baomat", self.t)
        try:
            cn.execute("INSERT INTO nguoidung (id, ma, vaitro, nguoi_id) VALUES ('u1', 'chu', 'chu', 'n1')")
        finally:
            cn.close()

    def tearDown(self):
        self.tam.cleanup()

    def dat_lui(self, tao_ngay, dung_ngay):
        bay = datetime.now(MUIGIO_VN)
        cn = ketnoi.mo("Baomat", self.t)
        try:
            cn.execute("UPDATE phien_truycap SET tao_luc = ?, het_han = ?, lan_dung_cuoi = ?",
                       ((bay - timedelta(days=tao_ngay)).isoformat(timespec="seconds"),
                        (bay - timedelta(days=tao_ngay) + timedelta(days=30)).isoformat(timespec="seconds"),
                        (bay - timedelta(days=dung_ngay)).isoformat(timespec="seconds")))
        finally:
            cn.close()

    def test_phien_moi_het_han_sau_30_ngay(self):
        ma = phien.tao("u1", "Chrome · Windows", self.t)
        p = phien.tim(ma, self.t)
        con = datetime.fromisoformat(p["het_luc"]) - datetime.now(MUIGIO_VN)
        self.assertTrue(timedelta(days=29, hours=23) < con <= timedelta(days=30))

    def test_bo_khong_30_ngay_thi_het(self):
        ma = phien.tao("u1", "x", self.t)
        self.dat_lui(tao_ngay=29, dung_ngay=29)
        self.assertIsNotNone(phien.tim(ma, self.t))
        self.dat_lui(tao_ngay=31, dung_ngay=31)
        self.assertIsNone(phien.tim(ma, self.t))

    def test_dung_lien_tuc_van_het_sau_30_ngay(self):
        ma = phien.tao("u1", "x", self.t)
        self.dat_lui(tao_ngay=30, dung_ngay=0)
        self.assertIsNone(phien.tim(ma, self.t))
        self.assertEqual(phien.danh_sach("u1", self.t), [])


if __name__ == "__main__":
    unittest.main()
