"""Bài kiểm ngày 09 GĐ 1 (lược đồ bản 3, phần 3/5): L05 H01 đổi tên `kenh_nhan`, L04 `trangthai` bắt buộc;
cấp mã người 07 chữ số khi nhiều nơi tạo cùng lúc; hàm chung "ai bấm" (QĐ108, QĐ109)."""
import sqlite3
import threading
import unittest

from kiemthu.ngay07.test_luocdo_ban3 import CoThuMuc, dung_ban2
from maychu.dulieu import aibam, khoitao, maso, songuoi
from maychu.hethong.caidat import thongso
from maychu.hethong.kekhoa import kho


class KiemKenhNhan(CoThuMuc):
    def test_ten_moi_va_trangthai_bat_buoc(self):
        khoitao.tao_het(self.thumuc)
        bang = {r[0] for r in self.lay("Bot", "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("kenh_nhan", bang)
        self.assertNotIn("kenh", bang)
        k = maso.tao()
        self.ghi("Bot", "INSERT INTO kenh_nhan (id, vai) VALUES (?, 'anh_nhan_baocao')", (k,))
        self.assertEqual(self.lay("Bot", "SELECT trangthai FROM kenh_nhan WHERE id = ?", (k,)), [("dung",)])
        for sql in ("INSERT INTO kenh_nhan (id, vai, trangthai) VALUES (?, 'bot_giaoviec', NULL)",
                    "INSERT INTO kenh_nhan (id, vai, trangthai) VALUES (?, 'bot_giaoviec', 'tam')",
                    "INSERT INTO lich_baocao (id, kenhnhan_id) VALUES (?, 'khongco')"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.ghi("Bot", sql, (maso.tao(),))
        self.ghi("Bot", "INSERT INTO chude_nhom (id, kenhnhan_id) VALUES (?, ?)", (maso.tao(), k))

    def test_nang_ban_2_doi_ten_giu_du_lieu_va_khoa_ngoai(self):
        dung_ban2(self.thumuc)
        k = maso.tao()
        self.ghi("Bot", "INSERT INTO kenh (id, ten, vai) VALUES (?, 'Kênh báo anh', 'anh_nhan_baocao')", (k,))  # trangthai trống ở bản 2
        self.ghi("Bot", "INSERT INTO chude_nhom (id, kenhnhan_id) VALUES (?, ?)", (maso.tao(), k))
        khoitao.tao_het(self.thumuc)
        self.assertEqual(self.lay("Bot", "SELECT ten, vai, trangthai FROM kenh_nhan WHERE id = ?", (k,)),
                         [("Kênh báo anh", "anh_nhan_baocao", "dung")])
        self.assertEqual(self.lay("Bot", "PRAGMA foreign_key_check"), [])
        for bang in ("the_duyet", "tin_nhom", "chude_nhom", "lich_baocao", "hoithoai", "chatbot"):
            sql = self.lay("Bot", "SELECT sql FROM sqlite_master WHERE name = ?", (bang,))[0][0]
            with self.subTest(bang=bang):
                self.assertIn("kenh_nhan", sql)
        with self.assertRaises(sqlite3.IntegrityError):  # khoá ngoại tới bảng đổi tên vẫn chạy
            self.ghi("Bot", "INSERT INTO chude_nhom (id, kenhnhan_id) VALUES (?, 'khongco')", (maso.tao(),))


class KiemMaNguoi(CoThuMuc):
    def test_nhieu_noi_tao_cung_luc_khong_trung_ma(self):
        khoitao.tao_het(self.thumuc)
        loi, ma = [], []
        khoa = threading.Lock()

        def tao(n):
            try:
                for i in range(15):
                    kq = songuoi.tao(f"Người {n}-{i}", "khach", "hethong", self.thumuc)
                    with khoa:
                        ma.append(kq["ma"])
            except Exception as e:  # noqa: BLE001 - ghi lại để báo trong bài kiểm
                loi.append(e)

        luong = [threading.Thread(target=tao, args=(n,)) for n in range(3)]
        for t in luong:
            t.start()
        for t in luong:
            t.join()
        self.assertEqual(loi, [])
        self.assertEqual(sorted(ma), [f"{i:07d}" for i in range(1, 46)])


class KiemAiBam(CoThuMuc):
    def test_chi_nhan_ma_tai_khoan_hoac_ma_may(self):
        for gt in ("hethong", "bot", "viecnen", "ai", maso.tao()):
            with self.subTest(gt=gt):
                self.assertEqual(aibam.kiem(gt), gt)
        for gt in ("anh", "chu", "lenh_vps", "", None, "01JDRVTEST000000000000000I"):
            with self.subTest(gt=gt), self.assertRaises(ValueError):
                aibam.kiem(gt)

    def test_cho_ghi_dung_ham_chung(self):
        khoitao.tao_het(self.thumuc)
        tk = maso.tao()
        with self.assertRaises(ValueError):
            thongso.dat("nguong_ocung", "80", "2030-01-01", nguoi="anh", thumuc=self.thumuc)
        self.assertEqual(thongso.dat("nguong_ocung", "80", "2030-01-01", nguoi=tk, thumuc=self.thumuc), {"ok": True})
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT nguoi_dat FROM thongso WHERE ten = 'nguong_ocung' AND hieuluc_tu = '2030-01-01'"),
                         [(tk,)])
        with self.assertRaises(ValueError):
            kho.cat("dichvu_thu", "khoa-gia-0001", self.thumuc, nguoi_nhap="chu")
        ma = kho.cat("dichvu_thu", "khoa-gia-0002", self.thumuc)
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_nhap FROM kekhoa WHERE id = ?", (ma,)), [("hethong",)])


if __name__ == "__main__":
    unittest.main()
