"""Bài kiểm ngày 11 (lược đồ bản 3 phần 5/5; QĐ108 điều kiện CDA): dữ liệu dựng như bản 0.5.0 đang chạy (tài khoản
chủ có mật khẩu, đã bật 02 lớp, két F03 ghi "ai bấm" là 'anh', F01 do lệnh đặt lại ghi 'lenh_vps', đang có 01 phiên),
nâng lên bản 3 rồi đăng nhập lại đủ 02 lớp; mã người cấp tiếp không trùng; khóa ngoại về A18 đúng.
Dữ liệu thử chỉ dùng tên giả (QĐ126)."""
from kiemthu.ngay07.test_luocdo_ban3 import CoThuMuc, dung_ban2
from maychu.dulieu import aibam, ketnoi, khoitao, maso, songuoi
from maychu.hethong.kekhoa import kho
from maychu.hethong.taikhoan import matkhau, nguoidung, phien, totp

MK = "mk-thu-ngay-11"


class KiemDangNhapSauNang(CoThuMuc):
    def setUp(self):
        super().setUp()
        dung_ban2(self.thumuc)
        self.chu = maso.tao()
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, ten, hieuluc_tu, phienban, nguoi_khai, tao_luc, vaitro, module_xem,"
                 " matkhau_bam, trangthai) VALUES (?, 'chu', 'Chủ thử', '2026-11-21', 1, 'lenh_vps', '2026-11-21T09:00:00+07:00',"
                 " 'chu', '[\"tatca\"]', ?, 'dung')", (self.chu, matkhau.bam(MK)))
        # Bật 02 lớp lần đầu trên dữ liệu bản 2 (như anh đã làm ở bản 0.3.0)
        kq = nguoidung.buoc_matkhau("chu", MK, thumuc=self.thumuc)
        self.assertEqual(kq["buoc"], "bat2lop")
        self.khoa = kq["khoa"]
        r = nguoidung.buoc_ma2lop(kq["ma_tam"], totp.ma_cua_buoc(self.khoa, totp.buoc()), "Máy thử", thumuc=self.thumuc)
        self.phien_cu = r["ma_phien"]
        self.ghi("Baomat", "UPDATE kekhoa SET nguoi_nhap = 'anh'")      # bản 0.5.0 ghi 'anh' ở két 02 lớp

    def tearDown(self):
        nguoidung._MA_TAM.clear()
        nguoidung._BUOC_DA_DUNG.clear()
        super().tearDown()

    def test_nang_roi_dang_nhap_du_02_lop(self):
        self.assertEqual(set(self.lay(t, "PRAGMA user_version")[0][0] for t in ketnoi.CAC_FILE), {2})
        khoitao.tao_het(self.thumuc)
        self.assertEqual(set(self.lay(t, "PRAGMA user_version")[0][0] for t in ketnoi.CAC_FILE), {khoitao.PHIENBAN_LUOCDO})   # 0.8.0: nâng thẳng 2 → 4
        # "ai bấm" đã đổi; két 02 lớp vẫn giải được bằng khóa chủ cũ
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_nhap FROM kekhoa"), [(self.chu,)])
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_khai FROM nguoidung"), [("hethong",)])
        khoa_id = self.lay("Baomat", "SELECT totp_khoa_id FROM nguoidung")[0][0]
        self.assertEqual(kho.doc(khoa_id, self.thumuc), self.khoa)
        # phiên đăng nhập cũ vẫn còn; đăng nhập mới đủ 02 lớp
        self.assertIsNotNone(phien.tim(self.phien_cu, self.thumuc))
        kq = nguoidung.buoc_matkhau("chu", MK, thumuc=self.thumuc)
        self.assertEqual(kq["buoc"], "ma2lop")
        sai = nguoidung.buoc_ma2lop(kq["ma_tam"], totp.ma_cua_buoc(self.khoa, totp.buoc() + 10), "Máy thử 2",
                                    thumuc=self.thumuc)                    # mã của 05 phút sau: ngoài cửa sổ nhận
        self.assertIn("loi", sai)
        r = nguoidung.buoc_ma2lop(kq["ma_tam"], totp.ma_cua_buoc(self.khoa, totp.buoc() + 1), "Máy thử 2", thumuc=self.thumuc)
        self.assertIn("ma_phien", r)
        # F01 nối A18 của anh; mã người cấp tiếp không trùng; khóa ngoại về A18 đúng ở cả 07 file
        a18 = self.lay("Dulieu_Chinh", "SELECT id, ma FROM nguoi WHERE loai = 'anh'")
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_id FROM nguoidung"), [(a18[0][0],)])
        self.assertEqual(a18[0][1], "0000001")
        nv = songuoi.tao("Nhân viên 01", "nhanvien", "hethong", self.thumuc)
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT ma FROM nguoi WHERE id = ?", (nv["id"],)), [("0000002",)])
        self.ghi("Dulieu_Chinh", "INSERT INTO nhanvien (id, ma, nguoi_id) VALUES (?, 'NV01', ?)", (maso.tao(), nv["id"]))
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self.lay(ten, "PRAGMA foreign_key_check"), [], ten)
            for bang, cot in aibam.cac_cot(ten):
                for (v,) in self.lay(ten, f"SELECT DISTINCT {cot} FROM {bang} WHERE {cot} IS NOT NULL"):
                    self.assertTrue(aibam.la_hop_le(v), f"{ten}.{bang}.{cot}")


if __name__ == "__main__":
    import unittest
    unittest.main()
