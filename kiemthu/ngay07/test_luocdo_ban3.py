"""Bài kiểm ngày 07 GĐ 1 (lược đồ bản 3, phần 1/5): A18 Sổ người, A10, A15, B01, C20, E02 (L01), E03, F01, H03, H06;
tài khoản chủ nối A18; nâng file bản 2 lên bản 3; lỗi thì trả cả 07 file về bản sao (QĐ108, QĐ109, QĐ93)."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kiemthu.ngay07.luocdo_ban2 import V2
from maychu.dulieu import ketnoi, khoitao, maso, songuoi
from maychu.hethong.taikhoan import datlai, nguoidung


def dung_ban2(thumuc: Path) -> None:
    """Dựng 07 file như đang chạy trên VPS bản 2: bảng đổi ở bản 3 trở về lược đồ bản 2, chưa có A18."""
    khoitao.tao_het(thumuc)
    for ten in ketnoi.CAC_FILE:
        cn = ketnoi.mo(ten, thumuc)
        try:
            cn.execute("PRAGMA foreign_keys=OFF")
            for (t, bang), ddl in V2.items():
                if t == ten:
                    cn.execute(f"DROP TABLE {bang}")
                    cn.execute(ddl)
            if ten == "Dulieu_Chinh":
                cn.execute("DROP TABLE nguoi")
            cn.execute("PRAGMA user_version=2")
        finally:
            cn.close()


class CoThuMuc(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)

    def tearDown(self):
        self.tam.cleanup()

    def mo(self, ten):
        return ketnoi.mo(ten, self.thumuc)

    def lay(self, ten, sql, ts=()):
        cn = self.mo(ten)
        try:
            return cn.execute(sql, ts).fetchall()
        finally:
            cn.close()

    def ghi(self, ten, sql, ts=()):
        cn = self.mo(ten)
        try:
            cn.execute(sql, ts)
        finally:
            cn.close()


class KiemFileMoiBan3(CoThuMuc):
    def setUp(self):
        super().setUp()
        self.kq = khoitao.tao_het(self.thumuc)

    def test_105_bang_ban_3(self):
        self.assertEqual(sum(self.kq.values()), 105)
        self.assertEqual(self.kq["Dulieu_Chinh"], 54)
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA user_version")[0][0], 3)

    def test_h06_03_dong_khoi_tao_va_chay_lai_khong_them(self):
        khoitao.tao_het(self.thumuc)
        dong = self.lay("Bot", "SELECT ma, gio_gui, lap_lai, ngay_trongthang, gui_tin FROM lich_baocao ORDER BY ma")
        self.assertEqual(dong, [("bao_chua_lay_tygia", "09:30", "hangngay", None, 1),
                                ("lay_tygia_vcb", "09:00", "hangngay", None, 0),
                                ("nhac_khoa_tygia_thang", "09:00", "hangthang", 1, 1)])
        with self.assertRaises(sqlite3.IntegrityError):  # hằng tháng phải có ngày trong tháng
            self.ghi("Bot", "INSERT INTO lich_baocao (id, lap_lai) VALUES (?, 'hangthang')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi("Bot", "INSERT INTO lich_baocao (id, gui_tin) VALUES (?, 2)", (maso.tao(),))

    def test_a18_rang_buoc(self):
        a = songuoi.tao("Anh", "anh", "hethong", self.thumuc)
        b = songuoi.tao("Nhân viên 01", "nhanvien", "hethong", self.thumuc)
        self.assertEqual((a["ma"], b["ma"]), ("0000001", "0000002"))
        them = "INSERT INTO nguoi (id, ma, ten, loai, nguoi_khai, tao_luc{}) VALUES (?, ?, 'X', 'khach', 'hethong', '2026-11-22'{})"
        for ma in ("123", "00000AB", "0000001"):  # sai dạng 07 chữ số, trùng mã
            with self.subTest(ma=ma), self.assertRaises(sqlite3.IntegrityError):
                self.ghi("Dulieu_Chinh", them.format("", ""), (maso.tao(), ma))
        with self.assertRaises(sqlite3.IntegrityError):  # dừng học phải có lý do
            self.ghi("Dulieu_Chinh", them.format(", trangthai_hoc", ", 'dung_hoc'"), (maso.tao(), "0000009"))
        d = self.lay("Dulieu_Chinh", "SELECT trangthai, trangthai_hoc, co_dlcn FROM nguoi WHERE id = ?", (a["id"],))
        self.assertEqual(d, [("dung", "chua_dongy", 1)])
        cn = self.mo("Dulieu_Chinh")
        try:
            with self.assertRaises(RuntimeError):  # cấp mã ngoài giao dịch ghi
                songuoi.cap_ma(cn)
        finally:
            cn.close()

    def test_bang_noi_ve_a18(self):
        n = songuoi.tao("Nhân viên 01", "nhanvien", "hethong", self.thumuc)["id"]
        DC = "Dulieu_Chinh"
        with self.assertRaises(sqlite3.IntegrityError):  # A15 bắt buộc có người
            self.ghi(DC, "INSERT INTO nhanvien (id) VALUES (?)", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):  # khoá ngoại về A18
            self.ghi(DC, "INSERT INTO nhanvien (id, nguoi_id) VALUES (?, 'khongco')", (maso.tao(),))
        self.ghi(DC, "INSERT INTO nhanvien (id, nguoi_id) VALUES (?, ?)", (maso.tao(), n))
        with self.assertRaises(sqlite3.IntegrityError):  # 01 nhân viên = 01 người
            self.ghi(DC, "INSERT INTO nhanvien (id, nguoi_id) VALUES (?, ?)", (maso.tao(), n))
        self.assertEqual(self.lay(DC, "SELECT tinhtrang FROM nhanvien")[0][0], "danglam")
        self.assertNotIn("ma_trenkenh", {r[1] for r in self.lay(DC, "PRAGMA table_info(nhanvien)")})
        # E02 (L01): đúng 01 trong 02 cột người nhận theo loại
        nv = "INSERT INTO nhiemvu (id, loai_nguoinhan, nguoi_id, congsu_id) VALUES (?, ?, ?, ?)"
        self.ghi(DC, nv, (maso.tao(), "nhanvien", n, None))
        self.ghi(DC, nv, (maso.tao(), "congsu", None, "cs-01"))
        for loai, ng, cs in (("anh", None, None), ("congsu", None, None), ("nhanvien", n, "cs-01"), (None, n, None),
                             ("congsu", n, None), ("nhanvien", "khongco", None)):
            with self.subTest(loai=loai, ng=ng, cs=cs), self.assertRaises(sqlite3.IntegrityError):
                self.ghi(DC, nv, (maso.tao(), loai, ng, cs))
        self.assertNotIn("nguoinhan_id", {r[1] for r in self.lay(DC, "PRAGMA table_info(nhiemvu)")})
        # E03, B01, C20, A10
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(DC, "INSERT INTO nhiemvu_sukien (id, nguoi_loai) VALUES (?, 'khac')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(DC, "INSERT INTO nhiemvu_sukien (id, nguoi_loai, nguoi_id) VALUES (?, 'nhanvien', 'khongco')", (maso.tao(),))
        self.ghi(DC, "INSERT INTO nhiemvu_sukien (id, nguoi_loai, congsu_id) VALUES (?, 'congsu', 'cs-01')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(DC, "INSERT INTO lonap (id, nguoi_nap) VALUES (?, 'mã A15')", (maso.tao(),))
        self.ghi(DC, "INSERT INTO lonap (id, nguoi_nap, nguoi_id) VALUES (?, 'nhanvien', ?)", (maso.tao(), n))
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi(DC, "INSERT INTO dieuchinh (id, nguoi_sua_loai, nguoi_sua_id) VALUES (?, 'anh', 'khongco')", (maso.tao(),))
        self.ghi(DC, "INSERT INTO ghep_mangoai (id, hieuluc_tu, nguon, ma_ngoai, doituong_loai, doituong_id)"
                     " VALUES (?, '2026-11-22', 'telegram', '12345', 'nguoi', ?)", (maso.tao(), n))
        self.assertIn("nguoi_id", {r[1] for r in self.lay("Bot", "PRAGMA table_info(tin_nhom)")})

    def test_f01_bat_buoc_nguoi_id_khong_trung(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.ghi("Baomat", "INSERT INTO nguoidung (id, ma) VALUES (?, 'chu')", (maso.tao(),))
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, nguoi_id) VALUES (?, 'chu', 'n1')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):  # 01 người tối đa 01 tài khoản
            self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, nguoi_id) VALUES (?, 'chu2', 'n1')", (maso.tao(),))
        self.assertNotIn("nhanvien_id", {r[1] for r in self.lay("Baomat", "PRAGMA table_info(nguoidung)")})


class KiemTaiKhoanChuNoiA18(CoThuMuc):
    def test_tao_tu_env_tao_a18_truoc_va_chay_lai_khong_them(self):
        khoitao.tao_het(self.thumuc)
        with mock.patch.dict(os.environ, {"IGM360_ADMIN_USER": "chu", "IGM360_ADMIN_PASSWORD": "mk-thu-01"}):
            self.assertTrue(nguoidung.tao_quantri_tu_env(self.thumuc))
            self.assertFalse(nguoidung.tao_quantri_tu_env(self.thumuc))
        a18 = self.lay("Dulieu_Chinh", "SELECT id, ma, ten, loai, nguoi_khai FROM nguoi")
        self.assertEqual([r[1:] for r in a18], [("0000001", "chu", "anh", "hethong")])
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_id, vaitro FROM nguoidung"), [(a18[0][0], "chu")])

    def test_lenh_datlai_tao_chu_noi_a18(self):
        khoitao.tao_het(self.thumuc)
        kq = datlai.chay([], hoi=lambda _c: "mk-thu-02", hoi_chu=lambda _c: "chu", thumuc=self.thumuc)
        self.assertEqual(kq, 0)
        a18 = self.lay("Dulieu_Chinh", "SELECT id FROM nguoi WHERE loai = 'anh'")
        self.assertEqual(len(a18), 1)
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_id, nguoi_khai FROM nguoidung"), [(a18[0][0], "hethong")])


class KiemNangBan2LenBan3(CoThuMuc):
    def setUp(self):
        super().setUp()
        dung_ban2(self.thumuc)
        self.chu = maso.tao()
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, ten, vaitro, tao_luc) VALUES (?, 'chu', 'Chủ thử', 'chu', '2026-11-21')",
                 (self.chu,))
        self.ghi("Bot", "INSERT INTO lich_baocao (id, ma, gio_gui) VALUES (?, 'cu_01', '07:00')", (maso.tao(),))

    def test_nang_giu_du_lieu_tao_a18_cua_anh(self):
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 105)
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA user_version")[0][0], 3)
            self.assertTrue((self.thumuc / "saoluu" / "truoc_nangcap_v03" / f"{ten}.sqlite3").exists())
            self.assertEqual(self.lay(ten, "PRAGMA foreign_key_check"), [])
        a18 = self.lay("Dulieu_Chinh", "SELECT id, ma, ten, loai FROM nguoi")
        self.assertEqual([r[1:] for r in a18], [("0000001", "Chủ thử", "anh")])
        self.assertEqual(self.lay("Baomat", "SELECT id, nguoi_id FROM nguoidung"), [(self.chu, a18[0][0])])
        self.assertEqual(self.lay("Bot", "SELECT gio_gui, lap_lai, gui_tin FROM lich_baocao WHERE ma = 'cu_01'"),
                         [("07:00", "hangngay", 1)])
        self.assertEqual(len(self.lay("Bot", "SELECT 1 FROM lich_baocao")), 4)
        khoitao.tao_het(self.thumuc)  # chạy lại không tạo thêm A18
        self.assertEqual(len(self.lay("Dulieu_Chinh", "SELECT 1 FROM nguoi")), 1)

    def test_cot_bo_con_du_lieu_thi_dung(self):
        self.ghi("Dulieu_Chinh", "INSERT INTO nhanvien (id, ma_trenkenh) VALUES (?, '{\"telegram\": \"1\"}')", (maso.tao(),))
        with self.assertRaises(RuntimeError) as loi:
            khoitao.tao_het(self.thumuc)
        self.assertIn("ma_trenkenh", str(loi.exception))
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA user_version")[0][0], 2)

    def test_loi_o_file_cuoi_tra_ca_07_file(self):
        # 02 tài khoản chủ cùng trỏ 01 dòng A18 → Baomat (file nâng cuối) lỗi khi Dulieu_Chinh đã nâng xong
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, vaitro, tao_luc) VALUES (?, 'chu2', 'chu', '2026-11-22')", (maso.tao(),))
        with self.assertRaises(sqlite3.IntegrityError):
            khoitao.tao_het(self.thumuc)
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA user_version")[0][0], 2, ten)
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT count(*) FROM sqlite_master WHERE name = 'nguoi'"), [(0,)])
        self.assertIn("ma_trenkenh", {r[1] for r in self.lay("Dulieu_Chinh", "PRAGMA table_info(nhanvien)")})
        self.assertEqual(len(self.lay("Baomat", "SELECT 1 FROM nguoidung")), 2)


if __name__ == "__main__":
    unittest.main()
