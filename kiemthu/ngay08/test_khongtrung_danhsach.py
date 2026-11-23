"""Bài kiểm ngày 08 GĐ 1 (lược đồ bản 3, phần 2/5): L02 ràng buộc không trùng 04 bảng nhập liệu; B08 tin lặp
đặt `trung` = 1 (QĐ112); L03 20 thông số danh sách và trigger kiểm danh sách mở rộng (thiết kế mục 0.6)."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kiemthu.ngay07.test_luocdo_ban3 import CoThuMuc, dung_ban2
from maychu.dulieu import dsmorong, ketnoi, khoitao, maso
from maychu.hethong.caidat import thongso
from maychu.ketnoi import hoptin


class KiemKhongTrung(CoThuMuc):
    def setUp(self):
        super().setUp()
        khoitao.tao_het(self.thumuc)

    def test_04_bang_nhap_lieu(self):
        HT = "Hotho"
        self.ghi(HT, "INSERT INTO filegoc (id, mabam_sha256) VALUES (?, 'abc')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(HT, "INSERT INTO filegoc (id, mabam_sha256) VALUES (?, 'abc')", (maso.tao(),))
        for _ in range(2):  # chưa có mã băm thì không chặn
            self.ghi(HT, "INSERT INTO filegoc (id) VALUES (?)", (maso.tao(),))
        b03 = "INSERT INTO banghigoc (id, nguon, loai_dulieu, ma_doituong, mabam) VALUES (?, 'pancake', 'don', 'D1', ?)"
        self.ghi(HT, b03, (maso.tao(), "m1"))
        self.ghi(HT, b03, (maso.tao(), "m2"))  # cùng đơn, nội dung đổi: thêm bản mới
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(HT, b03, (maso.tao(), "m1"))
        shop = maso.tao()
        self.ghi("Dulieu_Chinh", "INSERT INTO shop (id, ma) VALUES (?, 'SHOP01')", (shop,))
        c01 = "INSERT INTO donhang (id, shop_id, ma_don_nguon) VALUES (?, ?, 'DH-01')"
        self.ghi("Dulieu_Chinh", c01, (maso.tao(), shop))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi("Dulieu_Chinh", c01, (maso.tao(), shop))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi("Ketnoi", "INSERT INTO hoptin (id, nguon, ma_sukien) VALUES (?, 'pancake', 'S1'), (?, 'pancake', 'S1')",
                     (maso.tao(), maso.tao()))

    def test_b08_tin_lap_dat_trung_1(self):
        a = hoptin.nhan("pancake", "S1", ma_don="D1", noidung={"a": 1}, thumuc=self.thumuc)
        b = hoptin.nhan("pancake", "S1", ma_don="D1", noidung={"a": 1}, thumuc=self.thumuc)
        c = hoptin.nhan("pancake", "S2", thumuc=self.thumuc)
        self.assertTrue(a["moi"])
        self.assertEqual((b["id"], b["moi"]), (a["id"], False))
        self.assertTrue(c["moi"])
        self.assertEqual(self.lay("Ketnoi", "SELECT ma_sukien, trung FROM hoptin ORDER BY ma_sukien"), [("S1", 1), ("S2", 0)])
        with self.assertRaises(ValueError):
            hoptin.nhan("pancake", "", thumuc=self.thumuc)


class KiemDanhSachMoRong(CoThuMuc):
    def setUp(self):
        super().setUp()
        khoitao.tao_het(self.thumuc)

    def test_20_thong_so_danh_sach_khong_hien_o_ngan_thong_so(self):
        dong = self.lay("Dulieu_Chinh", "SELECT ten, kieu, giatri, nguoi_dat FROM thongso WHERE ten LIKE 'ds\\_%' ESCAPE '\\'")
        self.assertEqual(len(dong), 21)   # Y22a thêm ds_hang_ai
        self.assertEqual({d[0] for d in dong}, set(dsmorong.KHOITAO))
        self.assertTrue(all(d[1] == "danhsach" and d[3] == "hethong" for d in dong))
        self.assertEqual(json.loads(dict((d[0], d[2]) for d in dong)["ds_loai_nguoi"]), ["anh", "nhanvien", "khach"])
        self.assertEqual(thongso.doc_het(self.thumuc)["tong"], 13)  # ngăn Thông số không đổi (màn 09 "…/13")
        khoitao.tao_het(self.thumuc)  # chạy lại không thêm
        self.assertEqual(len(self.lay("Dulieu_Chinh", "SELECT 1 FROM thongso WHERE ten LIKE 'ds\\_%' ESCAPE '\\'")), 21)

    def test_trigger_chan_gia_tri_ngoai_danh_sach(self):
        DC = "Dulieu_Chinh"
        self.ghi(DC, "INSERT INTO shop (id, ma, thitruong, tien_ma) VALUES ('s1', 'SHOP01', 'VN', 'VND')")
        for sql in ("INSERT INTO shop (id, ma, thitruong) VALUES ('s2', 'SHOP02', 'TH')",
                    "INSERT INTO shop (id, ma, tien_ma) VALUES ('s3', 'SHOP03', 'USD')",
                    "UPDATE shop SET thitruong = 'XX' WHERE id = 's1'",
                    "INSERT INTO donhang (id, thitruong) VALUES ('d1', 'TH')",         # cột chung số liệu
                    "INSERT INTO donhang (id, tien_ma) VALUES ('d2', 'USD')",
                    "INSERT INTO ghep_mangoai (id, hieuluc_tu, nguon) VALUES ('g1', '2026-11-22', 'lazada')",
                    "INSERT INTO vandon (id, donvi_vanchuyen) VALUES ('v1', 'GHN')",   # danh sách đang trống
                    "INSERT INTO nguoi (id, ma, ten, loai, nguoi_khai, tao_luc) VALUES ('n1', '0000001', 'X', 'congtacvien', 'hethong', 'x')"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.ghi(DC, sql)
        self.ghi(DC, "INSERT INTO ghep_mangoai (id, hieuluc_tu, nguon) VALUES ('g2', '2026-11-22', 'file_donhang')")  # mẫu file_*
        self.ghi(DC, "INSERT INTO vandon (id) VALUES ('v2')")  # trống thì không chặn
        self.ghi(DC, "UPDATE shop SET ten = 'Shop 01' WHERE id = 's1'")  # sửa cột khác không kiểm lại
        self.assertEqual(self.lay(DC, "SELECT thitruong FROM shop WHERE id = 's1'"), [("VN",)])

    def test_them_phien_ban_thong_so_moi_mo_gia_tri_moi(self):
        DC = "Dulieu_Chinh"
        cn = self.mo(DC)
        try:
            cu = cn.execute("SELECT id, hieuluc_tu FROM thongso WHERE ten = 'ds_thitruong'").fetchone()
            # Thêm phiên bản mới bắt đầu từ ngày của dòng cũ: dòng cũ đóng, dòng mới có thêm TH
            cn.execute("UPDATE thongso SET hieuluc_den = ? WHERE id = ?", (cu[1], cu[0]))
            cn.execute("INSERT INTO thongso (id, ten, giatri, kieu, hieuluc_tu, nguoi_dat) VALUES (?, 'ds_thitruong', ?, 'danhsach', ?, 'hethong')",
                       (maso.tao(), json.dumps(["VN", "MY", "TH"]), cu[1]))
            cn.execute("INSERT INTO shop (id, ma, thitruong) VALUES ('s4', 'SHOP04', 'TH')")
            self.assertEqual(dsmorong.doc(cn, "ds_thitruong"), ["VN", "MY", "TH"])
        finally:
            cn.close()

    def test_lop_1_kiem_trong_ma(self):
        cn = self.mo("Dulieu_Chinh")
        try:
            dsmorong.kiem(cn, "ds_tien", "VND")
            dsmorong.kiem(cn, "ds_nguon_mangoai", "file_tygia")
            dsmorong.kiem(cn, "ds_tien", None)
            with self.assertRaises(ValueError):
                dsmorong.kiem(cn, "ds_tien", "USD")
            with self.assertRaises(ValueError):
                dsmorong.kiem(cn, "ds_kenh_nhan", "discord")  # danh sách của bảng khác file: chỉ kiểm lớp 1
        finally:
            cn.close()

    def test_so_trigger_khop_anh_xa(self):
        cn = self.mo("Dulieu_Chinh")
        try:
            so_cot = sum(len(v) for v in dsmorong.anh_xa_day_du(cn).values())
            self.assertEqual(dsmorong.tao_trigger(cn), 2 * so_cot)
        finally:
            cn.close()


class KiemNangBan2CoTrung(CoThuMuc):
    def test_ban_2_co_tin_trung_thi_khong_nang_tra_ca_07_file(self):
        dung_ban2(self.thumuc)
        self.ghi("Ketnoi", "INSERT INTO hoptin (id, nguon, ma_sukien) VALUES (?, 'pancake', 'S1'), (?, 'pancake', 'S1')",
                 (maso.tao(), maso.tao()))
        with self.assertRaises(sqlite3.IntegrityError):
            khoitao.tao_het(self.thumuc)
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA user_version")[0][0], 2, ten)

    def test_nang_ban_2_co_danh_sach_va_trigger(self):
        dung_ban2(self.thumuc)
        khoitao.tao_het(self.thumuc)
        self.assertEqual(len(self.lay("Dulieu_Chinh", "SELECT 1 FROM thongso WHERE ten LIKE 'ds\\_%' ESCAPE '\\'")), 21)
        with self.assertRaises(sqlite3.IntegrityError):  # trigger có cả trên bảng vừa dựng lại
            self.ghi("Dulieu_Chinh", "INSERT INTO donhang (id, tien_ma) VALUES ('d1', 'USD')")


if __name__ == "__main__":
    unittest.main()
