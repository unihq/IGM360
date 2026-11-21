"""Bài kiểm ngày 04 (phần dữ liệu): lược đồ bản 2, nâng cấp file bản 1, cảnh báo tệp hoán đổi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso
from maychu.hethong.giamsat import domay

# Lược đồ bản 1 của 06 bảng đổi ở bản 2 (chép từ commit c63410f), để dựng lại file bản 1 khi kiểm.
V1 = {
    ('Bot', 'kenh'): "CREATE TABLE IF NOT EXISTS kenh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  vai TEXT CHECK (vai IS NULL OR vai IN ('anh_nhan_baocao', 'bot_giaoviec')),\n  co_nutbam INTEGER,\n  co_nhom INTEGER,\n  cuaso_gui_gio INTEGER,\n  ketnoi_id TEXT\n);",
    ('Dulieu_Chinh', 'taikhoan'): "CREATE TABLE IF NOT EXISTS taikhoan (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('banhang', 'quangcao', 'nganhang')),\n  shop_id TEXT REFERENCES shop(id),\n  tien_ma TEXT,\n  phapnhan_dungten_id TEXT REFERENCES congty(id),\n  sotk_4socuoi TEXT\n);",
    ('Dulieu_Chinh', 'barcode'): "CREATE TABLE IF NOT EXISTS barcode (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  barcode TEXT,\n  sku_id TEXT REFERENCES sku(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('nhacungcap', 'noibo'))\n);",
    ('Dulieu_Chinh', 'combo_thanhphan'): 'CREATE TABLE IF NOT EXISTS combo_thanhphan (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  combo_id TEXT REFERENCES sku(id),\n  sku_id TEXT REFERENCES sku(id),\n  so_chiec INTEGER\n);',
    ('Dulieu_Chinh', 'ghep_mangoai'): "CREATE TABLE IF NOT EXISTS ghep_mangoai (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nguon TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  ma_ngoai TEXT,\n  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('sku', 'combo', 'taikhoan', 'kho', 'shop')),\n  doituong_id TEXT\n);",
    ('Nhatky', 'theodoi_maychu'): 'CREATE TABLE IF NOT EXISTS theodoi_maychu (\n  id TEXT PRIMARY KEY NOT NULL,\n  luc TEXT,\n  tyle_ocung INTEGER,\n  ram_dung INTEGER,\n  so_viec_dangchay INTEGER,\n  so_viec_ai_dangchay INTEGER,\n  thoigian_cho_ghi_ms INTEGER\n);',
}


def dung_ban1(thumuc: Path) -> None:
    khoitao.tao_het(thumuc)
    for (ten, bang), ddl in V1.items():
        cn = ketnoi.mo(ten, thumuc)
        try:
            cn.execute("PRAGMA foreign_keys=OFF")
            cn.execute(f"DROP TABLE {bang}")
            cn.execute(ddl)
            cn.execute("PRAGMA user_version=1")
        finally:
            cn.close()
    for ten in ketnoi.CAC_FILE:
        cn = ketnoi.mo(ten, thumuc)
        try:
            cn.execute("PRAGMA user_version=1")
        finally:
            cn.close()


class KiemBan2(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)

    def tearDown(self):
        self.tam.cleanup()

    def mo(self, ten):
        return ketnoi.mo(ten, self.thumuc)

    def test_file_moi_ban_2_va_cot_bat_buoc(self):
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 104)
        for ten in ketnoi.CAC_FILE:
            cn = self.mo(ten)
            try:
                self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], 2)
            finally:
                cn.close()
        cn = self.mo("Bot")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO kenh (id) VALUES (?)", (maso.tao(),))
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO kenh (id, vai) VALUES (?, 'cahai')", (maso.tao(),))
            cn.execute("INSERT INTO kenh (id, vai) VALUES (?, 'bot_giaoviec')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            ma = maso.tao()
            cn.execute("INSERT INTO taikhoan (id, loai) VALUES (?, 'nganhang')", (ma,))
            self.assertEqual(cn.execute("SELECT trangthai FROM taikhoan WHERE id = ?", (ma,)).fetchone()[0], "dung")
            for bang in ("barcode", "combo_thanhphan", "ghep_mangoai"):
                with self.assertRaises(sqlite3.IntegrityError):
                    cn.execute(f"INSERT INTO {bang} (id) VALUES (?)", (maso.tao(),))
                cn.execute(f"INSERT INTO {bang} (id, hieuluc_tu) VALUES (?, '2026-11-21')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            self.assertIn("swap_dung", {r[1] for r in cn.execute("PRAGMA table_info(theodoi_maychu)")})
        finally:
            cn.close()

    def test_nang_cap_tu_ban_1_giu_du_lieu(self):
        dung_ban1(self.thumuc)
        ma_kenh, ma_tk, ma_n02 = maso.tao(), maso.tao(), maso.tao()
        cn = self.mo("Bot")
        try:
            cn.execute("INSERT INTO kenh (id, ten, vai) VALUES (?, 'Kênh báo anh', 'anh_nhan_baocao')", (ma_kenh,))
            cn.execute("INSERT INTO lich_baocao (id, kenhnhan_id) VALUES (?, ?)", (maso.tao(), ma_kenh))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            cn.execute("INSERT INTO taikhoan (id, loai, sotk_4socuoi) VALUES (?, 'banhang', '1234')", (ma_tk,))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            cn.execute("INSERT INTO theodoi_maychu (id, ram_dung) VALUES (?, 639)", (ma_n02,))
        finally:
            cn.close()
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 104)
        cn = self.mo("Bot")
        try:
            self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(cn.execute("SELECT ten, vai FROM kenh WHERE id = ?", (ma_kenh,)).fetchone(),
                             ("Kênh báo anh", "anh_nhan_baocao"))
            self.assertEqual(cn.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):  # khoá ngoại tới bảng dựng lại vẫn chạy
                cn.execute("INSERT INTO lich_baocao (id, kenhnhan_id) VALUES (?, 'khongco')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            self.assertEqual(cn.execute("SELECT sotk_4socuoi, trangthai FROM taikhoan WHERE id = ?", (ma_tk,)).fetchone(),
                             ("1234", "dung"))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            self.assertEqual(cn.execute("SELECT ram_dung, swap_dung FROM theodoi_maychu WHERE id = ?", (ma_n02,)).fetchone(),
                             (639, None))
        finally:
            cn.close()
        for ten in ketnoi.CAC_FILE:
            self.assertTrue((self.thumuc / "saoluu" / "truoc_nangcap_v02" / f"{ten}.sqlite3").exists())

    def test_nang_cap_loi_thi_tra_nguyen_trang(self):
        dung_ban1(self.thumuc)
        ma = maso.tao()
        cn = self.mo("Bot")
        try:
            cn.execute("INSERT INTO kenh (id, ten) VALUES (?, 'Kênh chưa có vai')", (ma,))
        finally:
            cn.close()
        with self.assertRaises(sqlite3.IntegrityError):
            khoitao.tao_het(self.thumuc)
        cn = self.mo("Bot")
        try:
            self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(cn.execute("SELECT ten FROM kenh WHERE id = ?", (ma,)).fetchone()[0], "Kênh chưa có vai")
            self.assertNotIn("vai TEXT NOT NULL", cn.execute("SELECT sql FROM sqlite_master WHERE name = 'kenh'").fetchone()[0])
        finally:
            cn.close()


class KiemCanhBaoSwap(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        khoitao.tao_het(self.thumuc)

    def tearDown(self):
        self.tam.cleanup()

    def dem(self):
        cn = ketnoi.mo("Dulieu_Chinh", self.thumuc)
        try:
            return cn.execute("SELECT count(*), max(giatri) FROM canhbao WHERE khoa_chongtrung = 'swap_vuot_nguong'").fetchone()
        finally:
            cn.close()

    def ghi(self, swap_mb):
        that = domay.do_may
        with mock.patch.object(domay, "do_may", lambda t=None: {**that(t), "may_hoandoi_dung_mb": swap_mb}):
            return domay.ghi_n02(self.thumuc)

    def test_duoi_nguong_khong_bao(self):
        self.assertEqual(self.ghi(100)["swap_dung"], 100)
        self.assertEqual(self.dem()[0], 0)

    def test_qua_nguong_bao_01_lan(self):
        self.ghi(150)
        self.ghi(180)
        self.assertEqual(self.dem(), (1, 150))


if __name__ == "__main__":
    unittest.main()
