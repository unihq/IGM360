"""Bài kiểm 0.9.0 – công tắc tắt/bật đăng nhập 02 lớp (QĐ390, QĐ391, QĐ392, QĐ393, QĐ397, QĐ398; CDA bản đồ 16b danh mục
KH-090 điều 1–16, 16g, 16h, 16j, 16k; KH-090 mục 2.6, 2.7).

Chạy đường gọi thật bằng TestClient trên thư mục dữ liệu tạm; mật khẩu, mã giả ghép lúc chạy. Bước mã 02 lớp đã dùng giữ
trong bộ nhớ (`_BUOC_DA_DUNG`, chống dùng lại ±01 bước): bài xóa trước mỗi lần nhập mã để mô phỏng thời gian trôi.
"""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.hethong import antoan
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import thongbao
from maychu.hethong.taikhoan import datlai, nguoidung, totp

MK = "-".join(["matkhau", "kiem", "090"])
NB = " "
CHUONG = "Đăng nhập 02" + NB + "lớp đang tắt. Bật lại ở Cài đặt › Tài khoản và 02" + NB + "lớp."   # bảng chữ màn 09 dòng 12
SAI_TAT = "Mật khẩu hoặc mã 06" + NB + "số chưa đúng."                                              # dòng 9
AN_TOAN = "Đang ở chế độ an toàn: chưa tắt được đăng nhập 02" + NB + "lớp."                         # dòng 11


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH", "IGM360_ADMIN_USER",
                                                   "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(self.thumuc), IGM360_LICH="tat", IGM360_ADMIN_USER="chu",
                          IGM360_ADMIN_PASSWORD=MK, IGM360_COOKIE_SECURE="0")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        self.TestClient, self.app = TestClient, khoidong.app
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}

    def tearDown(self):
        self.c.__exit__(None, None, None)
        antoan.CHE_DO.update(an_toan=False)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        nguoidung._MA_TAM.clear()
        nguoidung._BUOC_DA_DUNG.clear()
        self.tam.cleanup()

    def ma(self, khoa, lech=0):
        nguoidung._BUOC_DA_DUNG.clear()
        return totp.ma_cua_buoc(khoa, totp.buoc() + lech)

    def dang_nhap_lan_dau(self, c=None):
        c = c or self.c
        kq = c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        self.assertEqual(kq["buoc"], "bat2lop")
        r = c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": self.ma(kq["khoa"])}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        return kq["khoa"]

    def may_khac(self, khoa):
        m = self.TestClient(self.app)
        kq = m.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        if kq["buoc"] == "ma2lop":
            m.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual(m.get("/api/toi").status_code, 200)
        return m

    def tat(self, khoa, mk=MK):
        return self.c.post("/api/2lop/tat", json={"matkhau": mk, "ma": self.ma(khoa)}, headers=self.h)

    def bat(self, khoa):
        return self.c.post("/api/2lop/bat", json={"ma": self.ma(khoa)}, headers=self.h)

    def khoa_id(self):
        cn = ketnoi.mo("Baomat", self.thumuc)
        try:
            return cn.execute("SELECT totp_khoa_id FROM nguoidung").fetchone()[0]
        finally:
            cn.close()

    def f04(self, lenhcon):
        cn = ketnoi.mo("Nhatky", self.thumuc)
        try:
            return [r[0] for r in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'taikhoan' AND lenhcon = ?"
                                             " ORDER BY luc, rowid", (lenhcon,))]
        finally:
            cn.close()

    def chuong(self):
        return [x for x in thongbao.danh_sach(thumuc=self.thumuc)["ds"] if x["loai"] == "dangnhap_2lop_tat"]


class KiemDuongChung(Nen):
    def test_dieu1_duong_sua_va_gat_chung_tu_choi_co(self):          # SOAT-KH090 (a): phiên mượn không tắt được không cần mật khẩu
        self.dang_nhap_lan_dau()
        r = self.c.post("/api/thongso/dangnhap_2lop", json={"giatri": "0", "hieuluc_tu": date.today().isoformat()}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/thongso/dangnhap_2lop/gat", json={"bat": False}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))
        self.assertTrue(self.c.get("/api/toi").json()["da_bat_2lop"])
        self.assertNotIn("dangnhap_2lop", [t["ten"] for t in self.c.get("/api/thongso").json()["thongso"]])   # ẩn khỏi ngăn Thông số
        self.assertEqual(thongso.dat("dangnhap_2lop", "0", "2099-01-01", nguoi="hethong")["loi"], "Không có thông số này")
        self.assertIn("loi", thongso.gat("dangnhap_2lop", False, nguoi="hethong"))

    def test_dieu5_co_trong_hoac_doc_loi_la_bat(self):
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))                                  # chưa có dòng
        thongso._ghi_gat(thongso.CO_2LOP, "", "hethong", "thử", self.thumuc)
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))                                  # trống
        with mock.patch.object(thongso, "doc_mot", side_effect=OSError("hỏng")):
            self.assertTrue(thongso.co_2lop_bat(self.thumuc))                              # đọc lỗi


class KiemTatBat(Nen):
    def test_dieu2_10_tat_thieu_mot_trong_hai_thi_khong_tat_va_dem(self):
        khoa = self.dang_nhap_lan_dau()
        r = self.c.post("/api/2lop/tat", json={"matkhau": "sai", "ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]["loi"], r.json()["detail"]["con_lai"]), (400, SAI_TAT, 4))
        r = self.c.post("/api/2lop/tat", json={"matkhau": MK, "ma": "000000" if self.ma(khoa) != "000000" else "111111"}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]["con_lai"]), (400, 3))
        r = self.c.post("/api/2lop/tat", json={"matkhau": MK}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))
        self.assertEqual(self.f04("tat_2lop"), [])
        # QĐ391: mật khẩu ngắn vẫn tắt được (không kiểm độ dài)
        self.assertEqual(self.c.post("/api/matkhau", json={"cu": MK, "moi": "ab", "nhap_lai": "ab"}, headers=self.h).status_code, 200)
        r = self.tat(khoa, mk="ab")
        self.assertEqual((r.status_code, r.json()), (200, {"ok": True, "doi": True}))
        self.assertFalse(thongso.co_2lop_bat(self.thumuc))

    def test_dieu3_7_11_f04_chuong_hai_chieu_bat_lai_giu_khoa_thu_hoi_may_khac(self):
        khoa = self.dang_nhap_lan_dau()
        kid = self.khoa_id()
        self.assertEqual(self.tat(khoa).status_code, 200)
        self.assertEqual(len(self.f04("tat_2lop")), 1)
        self.assertEqual([x["chu"] for x in self.chuong()], [CHUONG])                     # 01 dòng, mức Xem
        self.assertEqual((self.chuong()[0]["muc"], self.chuong()[0]["icon"], self.chuong()[0]["di"]), ("xem", "shield-alert", "taikhoan"))
        thongbao.quet(self.thumuc)                                                         # quét 10 phút: không mở đôi
        self.assertEqual(len(self.chuong()), 1)
        toi = self.c.get("/api/toi").json()
        self.assertEqual((toi["da_bat_2lop"], toi["co_khoa_2lop"]), (False, True))
        # đang tắt: /dangnhap tạo phiên, đặt cookie; không trả mã phiên
        m2 = self.TestClient(self.app)
        r = m2.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h)
        self.assertEqual((r.status_code, r.json()), (200, {"buoc": "vao"}))
        self.assertEqual(m2.get("/api/toi").status_code, 200)
        self.assertEqual(self.khoa_id(), kid)                                              # tắt giữ khóa
        # bật lại: sai mã đếm, không bật
        r = self.c.post("/api/2lop/bat", json={"ma": "12345"}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]["con_lai"]), (400, 4))
        self.assertFalse(thongso.co_2lop_bat(self.thumuc))
        r = self.bat(khoa)                                                                  # 01 mã đúng của khóa cũ
        self.assertEqual((r.status_code, r.json()["doi"], r.json()["thu_hoi"]), (200, True, 1))
        self.assertEqual(self.khoa_id(), kid)                                              # không sinh khóa mới
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))
        self.assertEqual(m2.get("/api/toi").status_code, 401)                              # QĐ393 (1): máy khác đăng xuất
        self.assertEqual(self.c.get("/api/toi").status_code, 200)                         # phiên vừa bật còn dùng được
        self.assertEqual(self.chuong(), [])
        self.assertEqual(len(self.f04("bat_2lop")), 1)
        self.assertEqual(self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()["buoc"], "ma2lop")

    def test_dieu4_che_do_an_toan_chan_tat_cho_bat(self):
        khoa = self.dang_nhap_lan_dau()
        self.assertEqual(self.tat(khoa).status_code, 200)
        antoan.CHE_DO.update(an_toan=True)
        self.assertEqual(self.bat(khoa).status_code, 200)                                  # bật vẫn được
        r = self.tat(khoa)
        self.assertEqual((r.status_code, r.json()["detail"]), (403, AN_TOAN))
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))

    def test_dieu6_lan_dau_chua_co_khoa_van_bat_buoc_bat_va_dat_co_bat(self):          # SOAT-KH090 (b)
        thongso.ghi_co_2lop(False, "hethong", "thử", self.thumuc)
        thongbao.bao_2lop_tat(self.thumuc)
        self.dang_nhap_lan_dau()                                                           # vẫn bước bat2lop dù cờ tắt
        self.assertTrue(thongso.co_2lop_bat(self.thumuc))
        self.assertEqual(self.chuong(), [])
        self.assertEqual(self.f04("bat_2lop"), ["bat_lan_dau"])
        self.assertTrue(self.c.get("/api/toi").json()["da_bat_2lop"])


class KiemDatLai(Nen):
    def test_dieu12_datlai_ca_hai_kieu_dat_co_bat(self):                                 # QĐ393 (2)
        for them in ([], ["--tat-2lop"]):
            with self.subTest(them=them):
                khoa = self.dang_nhap_lan_dau() if not self.khoa_id() else None
                if khoa:
                    self.assertEqual(self.tat(khoa).status_code, 200)
                else:
                    thongso.ghi_co_2lop(False, "hethong", "thử", self.thumuc)
                    thongbao.bao_2lop_tat(self.thumuc)
                so = len(self.f04("bat_2lop"))
                dap = iter([MK, MK])
                self.assertEqual(datlai.chay(them, hoi=lambda _: next(dap), thumuc=self.thumuc), 0)
                self.assertTrue(thongso.co_2lop_bat(self.thumuc))
                self.assertEqual(self.chuong(), [])
                self.assertEqual(self.f04("bat_2lop")[so:], ["lenh_vps"])


class KiemDoiMay(Nen):
    def test_dieu14_doi_may_sai_05_lan_thi_khoa_nhu_dang_nhap(self):                    # QĐ393 (4); SOAT-KH090 (e)
        khoa = self.dang_nhap_lan_dau()
        dung = self.ma(khoa)
        sai = "000000" if dung != "000000" else "111111"
        for i in range(4):
            r = self.c.post("/api/2lop/doimay/batdau", json={"ma": sai}, headers=self.h)
            self.assertEqual(r.status_code, 400, i)
        r = self.c.post("/api/2lop/doimay/batdau", json={"ma": sai}, headers=self.h)
        self.assertEqual(r.status_code, 429)
        r = self.c.post("/api/2lop/doimay/batdau", json={"ma": self.ma(khoa)}, headers=self.h)   # đúng mã vẫn bị chặn
        self.assertEqual(r.status_code, 429)
        r = self.c.post("/api/2lop/doimay/xacnhan", json={"ma_tam": "x", "ma": sai}, headers=self.h)
        self.assertEqual(r.status_code, 429)

    def test_dieu15_i_dang_tat_batdau_tu_choi(self):                                    # QĐ398
        khoa = self.dang_nhap_lan_dau()
        kid = self.khoa_id()
        self.assertEqual(self.tat(khoa).status_code, 200)
        r = self.c.post("/api/2lop/doimay/batdau", json={"ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]), (400, CHUONG))
        self.assertEqual(self.khoa_id(), kid)

    def test_dieu15_ii_ma_tam_cap_truoc_luc_tat_cung_bi_tu_choi(self):
        khoa = self.dang_nhap_lan_dau()
        kid = self.khoa_id()
        r = self.c.post("/api/2lop/doimay/batdau", json={"ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        moi = r.json()
        self.assertEqual(self.tat(khoa).status_code, 200)
        r = self.c.post("/api/2lop/doimay/xacnhan", json={"ma_tam": moi["ma_tam"], "ma": self.ma(moi["khoa"])}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]), (400, CHUONG))
        self.assertEqual(self.khoa_id(), kid)                                              # khóa 02 lớp không đổi

    def test_dieu15_iii_bat_lai_thi_doi_may_chay_nhu_cu(self):
        khoa = self.dang_nhap_lan_dau()
        self.assertEqual(self.tat(khoa).status_code, 200)
        self.assertEqual(self.bat(khoa).status_code, 200)
        kid = self.khoa_id()
        r = self.c.post("/api/2lop/doimay/batdau", json={"ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        moi = r.json()
        r = self.c.post("/api/2lop/doimay/xacnhan", json={"ma_tam": moi["ma_tam"], "ma": self.ma(moi["khoa"])}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotEqual(self.khoa_id(), kid)


if __name__ == "__main__":
    unittest.main()
