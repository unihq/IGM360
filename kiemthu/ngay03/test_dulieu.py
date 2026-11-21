"""Bài kiểm ngày 03: 07 file dữ liệu, 104 bảng, cài đặt file, cột chung, sao lưu, đo máy."""
import json
import os
import sqlite3
import stat
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, khoitao, maso, saoluu
from maychu.hethong.giamsat import domay


class KiemTaoFile(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)

    def tearDown(self):
        self.tam.cleanup()

    def test_du_07_file_104_bang(self):
        kq = khoitao.tao_het(self.thumuc)
        self.assertEqual(kq, ketnoi.SO_BANG)
        self.assertEqual(sum(kq.values()), 104)
        for ten in ketnoi.CAC_FILE:
            duong = ketnoi.duongdan(ten, self.thumuc)
            self.assertTrue(duong.exists())
            self.assertEqual(stat.S_IMODE(duong.stat().st_mode), 0o600)

    def test_chay_lai_khong_sao(self):
        khoitao.tao_het(self.thumuc)
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 104)

    def test_cai_dat_file(self):
        khoitao.tao_het(self.thumuc)
        for ten in ketnoi.CAC_FILE:
            cn = ketnoi.mo(ten, self.thumuc)
            try:
                self.assertEqual(cn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                self.assertEqual(cn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                dobien = cn.execute("PRAGMA synchronous").fetchone()[0]
                self.assertEqual(dobien, 2 if ten in ketnoi.DO_BEN_FULL else 1)
                self.assertEqual(cn.execute("PRAGMA busy_timeout").fetchone()[0], 30000 if ten == "Viecnen" else 5000)
                self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], khoitao.PHIENBAN_LUOCDO)
            finally:
                cn.close()

    def test_rang_buoc_danh_sach_co_dinh(self):
        khoitao.tao_het(self.thumuc)
        cn = ketnoi.mo("Dulieu_Chinh", self.thumuc)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO vongdoi_shop (id, trangthai) VALUES (?, 'sai')", (maso.tao(),))
            cn.execute("INSERT INTO vongdoi_shop (id, trangthai) VALUES (?, 'dangban')", (maso.tao(),))
        finally:
            cn.close()

    def test_khoa_ngoai_trong_file(self):
        khoitao.tao_het(self.thumuc)
        cn = ketnoi.mo("Dulieu_Chinh", self.thumuc)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO vongdoi_shop (id, shop_id) VALUES (?, 'khong_co')", (maso.tao(),))
        finally:
            cn.close()

    def test_cot_them_qd82(self):
        khoitao.tao_het(self.thumuc)
        mong = {("Nhatky", "nhatky_ai"): {"sotien_thamkhao", "ketqua"},
                ("Viecnen", "nguon_ai"): {"tyle_5gio", "tyle_tuan", "datlai_5gio_luc", "datlai_tuan_luc", "do_luc", "da_het_luc"},
                ("Dulieu_Chinh", "cuacho"): {"nhatky_ai_id", "ketqua_dexuat"},
                ("Hotho", "vanban"): {"nhatky_ai_id"}}
        for (ten, bang), cot in mong.items():
            cn = ketnoi.mo(ten, self.thumuc)
            try:
                co = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
            finally:
                cn.close()
            self.assertTrue(cot <= co, (bang, cot - co))


    def test_cot_chung_nhom_a_va_vai_kenh(self):
        khoitao.tao_het(self.thumuc)
        danhmuc = {"id", "ma", "ten", "hieuluc_tu", "hieuluc_den", "phienban", "trangthai", "nguoi_khai", "tao_luc"}
        ghep = {"id", "hieuluc_tu", "hieuluc_den", "nguoi_khai", "tao_luc"}
        mong = {("Dulieu_Chinh", "taikhoan"): danhmuc, ("Dulieu_Chinh", "barcode"): ghep,
                ("Dulieu_Chinh", "combo_thanhphan"): ghep, ("Dulieu_Chinh", "ghep_mangoai"): ghep,
                ("Bot", "kenh"): {"vai"}}
        for (ten, bang), cot in mong.items():
            cn = ketnoi.mo(ten, self.thumuc)
            try:
                co = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
            finally:
                cn.close()
            self.assertTrue(cot <= co, (bang, cot - co))
        cn = ketnoi.mo("Bot", self.thumuc)
        try:
            for vai in ("anh_nhan_baocao", "bot_giaoviec"):
                cn.execute("INSERT INTO kenh (id, vai) VALUES (?, ?)", (maso.tao(), vai))
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO kenh (id, vai) VALUES (?, ?)", (maso.tao(), "cahai"))
        finally:
            cn.close()

class KiemSaoLuuDoMay(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        khoitao.tao_het(self.thumuc)

    def tearDown(self):
        self.tam.cleanup()

    def test_sao_luu_07_file(self):
        luc = datetime(2026, 11, 22, 2, 5, tzinfo=saoluu.MUIGIO_VN)
        kq = saoluu.chay(self.thumuc, luc)
        self.assertEqual(kq["ketqua"], "xong_tren_may")
        self.assertEqual(len(kq["file"]), 7)
        self.assertTrue(saoluu.da_co_hom_nay(self.thumuc, luc))
        for d in kq["file"]:
            self.assertEqual(d["kiemtra"], "ok")
            buoc = json.loads(d["ketqua_tungbuoc_json"])
            self.assertEqual(buoc["4_mahoa"], "cho_khoa_saoluu")
            self.assertEqual(stat.S_IMODE(os.stat(d["noi_luu"]).st_mode), 0o600)
        self.assertFalse(list(saoluu.thumuc_saoluu(self.thumuc).rglob("*.tam")))
        cn = ketnoi.mo("Nhatky", self.thumuc)
        try:
            self.assertEqual(cn.execute("SELECT count(*) FROM saoluu").fetchone()[0], 7)
        finally:
            cn.close()

    def test_giu_03_ngay(self):
        for ngay in range(18, 23):
            saoluu.chay(self.thumuc, datetime(2026, 11, ngay, 3, tzinfo=saoluu.MUIGIO_VN))
        con = sorted(p.name for p in saoluu.thumuc_saoluu(self.thumuc).iterdir())
        self.assertEqual(con, ["2026-11-20", "2026-11-21", "2026-11-22"])

    def test_ghi_n02(self):
        dong = domay.ghi_n02(self.thumuc)
        self.assertGreaterEqual(dong["tyle_ocung"], 0)
        self.assertEqual(dong["so_viec_ai_dangchay"], 0)
        cn = ketnoi.mo("Nhatky", self.thumuc)
        try:
            self.assertEqual(cn.execute("SELECT count(*) FROM theodoi_maychu").fetchone()[0], 1)
        finally:
            cn.close()


class KiemMaSo(unittest.TestCase):
    def test_ulid(self):
        a, b = maso.tao(1_000), maso.tao(2_000)
        self.assertEqual(len(a), 26)
        self.assertLess(a, b)
        self.assertEqual(len({maso.tao() for _ in range(1000)}), 1000)


if __name__ == "__main__":
    unittest.main()
