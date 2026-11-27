"""Bài kiểm 0.10.0 bước 8a – máy chủ ngăn Thông báo + Mức dùng: QĐ553 (5) tắt theo loại, QĐ664 tin "Cập nhật xong",
QĐ665 dangnhap_2lop_tat tắt được (mặc định bật), QĐ666 dòng 16 "Đã lên bản {bản}"; P01 chuong_loai_tat, mucdung_tran_5gio
(CDA phiếu 06 mục 12.2, 13); bảng LOAI không có khóa lặp (CDA 13.3)."""

import ast
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import thongbao

GOC = Path(__file__).resolve().parents[2]


class KiemLoai(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"})
        bien.start()
        self.addCleanup(bien.stop)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)

    def test_loai_khong_lap_va_dem_21(self):
        cay = ast.parse((GOC / "maychu/hethong/giamsat/thongbao.py").read_text(encoding="utf-8"))
        gan = next(n for n in ast.walk(cay) if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "LOAI")
        khoa = [k.value for k in gan.value.keys]
        self.assertEqual(len(khoa), len(set(khoa)))
        muc = [v[0] for v in thongbao.LOAI.values()]
        self.assertEqual((len(khoa), muc.count("do"), muc.count("xem"), muc.count("tin")), (21, 8, 8, 5))   # QĐ664: 21 loại
        self.assertEqual(thongbao.LOAI["capnhat_xong"][:3], ("tin", "package-check", "capnhat"))

    def test_tat_theo_loai_tu_choi_loai_do(self):
        self.assertEqual(thongso.doc_loai_tat(self.dl), set())                           # mặc định bật hết (QĐ665: 02 lớp bật)
        self.assertEqual(thongso.dat_loai_tat("saoluu_loi", False, "hethong", self.dl), {"loi": thongso.CHU_LUON_BAO})
        self.assertIn("loi", thongso.dat_loai_tat("khong_co", False, "hethong", self.dl))
        kq = thongso.dat_loai_tat("dangnhap_2lop_tat", False, "hethong", self.dl)        # QĐ665 (B): tắt được
        self.assertEqual(kq["tat"], ["dangnhap_2lop_tat"])
        thongso.dat_loai_tat("banmoi", False, "hethong", self.dl)
        thongso.dat_loai_tat("dangnhap_2lop_tat", True, "hethong", self.dl)
        self.assertEqual(thongso.doc_loai_tat(self.dl), {"banmoi"})
        self.assertNotIn("chuong_loai_tat", [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])   # không ở ngăn Thông số
        self.assertIn("loi", thongso.dat("chuong_loai_tat", "x", "2026-11-27", nguoi="hethong", thumuc=self.dl))   # đường chung từ chối

    def test_loai_da_tat_van_trong_bang_khong_cong_so(self):
        thongbao.bao_su_kien("tenmien_doi", "igm.vidu.test", self.dl, truoc="")
        self.assertEqual(thongbao.danh_sach(None, self.dl)["so_moi"], 1)
        thongso.dat_loai_tat("tenmien_doi", False, "hethong", self.dl)
        kq = thongbao.danh_sach(None, self.dl)
        self.assertEqual(([x["tat"] for x in kq["ds"]], kq["so_moi"]), ([True], 0))

    def test_cap_nhat_xong_mo_khi_kiem_dat_dong_khi_co_ban_moi(self):
        thongbao.quet_kiem_capnhat("0.10.0", [], self.dl)
        ds = thongbao.danh_sach(None, self.dl)["ds"]
        self.assertEqual([(x["loai"], x["muc"], x["icon"], x["chu"]) for x in ds],
                         [("capnhat_xong", "tin", "package-check", "Đã lên bản 0.10.0")])   # QĐ666 dòng 16
        thongbao.quet_kiem_capnhat("0.10.1", ["Lịch chạy nền"], self.dl)                   # kiểm chưa đạt: không có tin xong
        self.assertEqual([x["loai"] for x in thongbao.danh_sach(None, self.dl)["ds"]], ["capnhat_kiem"])
        thongbao.quet_kiem_capnhat("0.10.1", [], self.dl)
        from maychu.hethong import capnhat
        with mock.patch.object(capnhat, "kiem_tra", return_value={"ban_dang": "0.10.1", "ban_moi": "0.10.2", "co_ban_moi": True}):
            thongbao.quet_banmoi(self.dl)
        self.assertEqual([x["loai"] for x in thongbao.danh_sach(None, self.dl)["ds"]], ["banmoi"])

    def test_tran_5gio(self):
        self.assertIsNone(thongso.doc_tran_5gio(self.dl))
        self.assertEqual(thongso.dat_tran_5gio("500.000", "hethong", self.dl)["tran"], 500000)
        self.assertEqual(thongso.doc_tran_5gio(self.dl), 500000)
        self.assertEqual(thongso.dat_tran_5gio("-3", "hethong", self.dl), {"loi": thongso.CHU_TRAN_SAI})
        self.assertIsNone(thongso.dat_tran_5gio("", "hethong", self.dl)["tran"])        # trống = so với đỉnh 60 ngày
        self.assertIsNone(thongso.doc_tran_5gio(self.dl))
        self.assertNotIn("mucdung_tran_5gio", [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])


if __name__ == "__main__":
    unittest.main()
