"""Bài kiểm ngày 04: tài khoản, 02 lớp, phiên, thông số, cập nhật, khóa chủ, lệnh đặt lại mật khẩu, trang."""
import os
import stat
import tempfile
import unittest
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.hethong import capnhat
from maychu.hethong.kekhoa import khoachu, kho
from maychu.hethong.taikhoan import datlai, matkhau, nguoidung, totp

MK = "matkhau-kiem-thu-01"


class KiemMayChu(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH", "IGM360_ADMIN_USER",
                                                   "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(self.thumuc), IGM360_LICH="tat", IGM360_ADMIN_USER="chu",
                          IGM360_ADMIN_PASSWORD=MK, IGM360_COOKIE_SECURE="0")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}

    def tearDown(self):
        self.c.__exit__(None, None, None)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        nguoidung._MA_TAM.clear()
        nguoidung._BUOC_DA_DUNG.clear()
        self.tam.cleanup()

    def dang_nhap_lan_dau(self):
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h)
        self.assertEqual(r.status_code, 200)
        kq = r.json()
        self.assertEqual(kq["buoc"], "bat2lop")
        self.assertIn("<svg", kq["qr_svg"])
        ma = totp.ma_cua_buoc(kq["khoa"], totp.buoc())
        r = self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": ma}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        return kq["khoa"]

    def test_trang_va_lop_bao_ve(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("/tainguyen/app.js", r.text)
        self.assertNotIn("minhhoa", r.text)
        self.assertIn("frame-ancestors 'none'", r.headers["content-security-policy"])
        self.assertEqual(self.c.get("/tainguyen/app.js").status_code, 200)
        self.assertEqual(self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}).status_code, 403)
        self.assertEqual(self.c.get("/api/toi").status_code, 401)
        self.assertEqual(self.c.get("/docs").status_code, 404)

    def test_dang_nhap_02_lop(self):
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": "sai-mat-khau"}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        khoa = self.dang_nhap_lan_dau()
        toi = self.c.get("/api/toi").json()
        self.assertTrue(toi["da_bat_2lop"])
        cn = ketnoi.mo("Baomat", self.thumuc)
        try:
            khoa_id, = cn.execute("SELECT totp_khoa_id FROM nguoidung").fetchone()
            banma, cuoi = cn.execute("SELECT banma, kytu_cuoi FROM kekhoa WHERE id = ?", (khoa_id,)).fetchone()
            bam, = cn.execute("SELECT mabam FROM phien_truycap").fetchone()
        finally:
            cn.close()
        self.assertNotIn(khoa.encode(), banma)
        self.assertEqual(cuoi, khoa[-4:])
        self.assertNotEqual(bam, self.c.cookies.get("igm360_phien"))
        # lần sau: bước mã 02 lớp; mã của bước đã dùng không nhận lại
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        self.assertEqual(r["buoc"], "ma2lop")
        cu = totp.ma_cua_buoc(khoa, totp.buoc())
        self.assertEqual(self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": cu}, headers=self.h).status_code, 400)
        moi = totp.ma_cua_buoc(khoa, totp.buoc() + 1)
        self.assertEqual(self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": moi}, headers=self.h).status_code, 200)
        self.assertEqual(len(self.c.get("/api/taikhoan").json()["phien"]), 2)

    def test_thong_so(self):
        self.dang_nhap_lan_dau()
        d = self.c.get("/api/thongso").json()
        self.assertEqual((d["tong"], d["da_dat"]), (15, 11))   # ngưỡng tiền AI tự áp dụng: Từ GĐ 2, không tính; +saoluu_drive (QĐ278, mặc định "0")
        self.assertNotIn("gio_baocao_sang", [t["ten"] for t in d["thongso"]])
        self.assertEqual(self.c.post("/api/thongso/phuongphap_giaxuat", json={"giatri": "binhquan_giaquyen", "hieuluc_tu": "2099-01-01"},
                                     headers=self.h).status_code, 400)
        r = self.c.post("/api/thongso/nguong_ocung", json={"giatri": "80", "hieuluc_tu": "2099-01-01"}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        r = self.c.post("/api/thongso/nguong_ocung", json={"giatri": "85", "hieuluc_tu": "2099-01-01"}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"]["o"], "tu")
        self.assertEqual(self.c.post("/api/thongso/nguong_ocung", json={"giatri": "abc", "hieuluc_tu": "2099-02-01"},
                                     headers=self.h).status_code, 400)
        self.assertEqual(self.c.post("/api/thongso/loai_gia_tygia", json={"giatri": "khac", "hieuluc_tu": "2099-02-01"},
                                     headers=self.h).status_code, 400)
        ls = self.c.get("/api/thongso/nguong_ocung/lichsu").json()
        self.assertEqual([x["giatri"] for x in ls], ["80", "70"])
        self.assertEqual(ls[1]["hieuluc_den"], "2099-01-01")
        nay = {t["ten"]: t for t in self.c.get("/api/thongso").json()["thongso"]}
        self.assertEqual(nay["nguong_ocung"]["giatri"], "70")
        self.assertEqual(nay["nguong_ocung"]["sap_ap_dung"], {"giatri": "80", "tu": "2099-01-01"})

    def test_doi_mat_khau_thu_hoi_dang_xuat(self):
        khoa = self.dang_nhap_lan_dau()
        from fastapi.testclient import TestClient
        from maychu import khoidong
        may2 = TestClient(khoidong.app)
        r = may2.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        may2.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": totp.ma_cua_buoc(khoa, totp.buoc() + 1)}, headers=self.h)
        self.assertEqual(may2.get("/api/toi").status_code, 200)
        r = self.c.post("/api/matkhau", json={"cu": MK, "moi": "", "nhap_lai": ""}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/matkhau", json={"cu": MK, "moi": "ab", "nhap_lai": "ab"}, headers=self.h)   # QĐ90: không quy định độ dài
        self.assertEqual(r.json()["thu_hoi"], 1)
        self.assertEqual(may2.get("/api/toi").status_code, 401)
        ds = self.c.get("/api/taikhoan").json()
        self.assertEqual(self.c.post(f"/api/phien/{ds['phien_id']}/thuhoi", headers=self.h).status_code, 400)
        self.c.post("/api/dangxuat", headers=self.h)
        self.assertEqual(self.c.get("/api/toi").status_code, 401)

    def test_khoa_dang_nhap_qua_duong_goi(self):
        for i in range(4):
            r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": "sai"}, headers=self.h)
            self.assertEqual((r.status_code, r.json()["detail"]["con_lai"]), (400, 4 - i))
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": "sai"}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]["phut"]), (429, 15))
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h)   # đúng mật khẩu vẫn bị chặn
        self.assertEqual(r.status_code, 429)
        dap = iter(["mat-khau-moi", "mat-khau-moi"])
        datlai.chay([], hoi=lambda _: next(dap), thumuc=self.thumuc)       # lệnh VPS mở khóa ngay
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": "mat-khau-moi"}, headers=self.h)
        self.assertEqual(r.status_code, 200)

    def test_ma_2lop_sai_cung_dem(self):
        khoa = self.dang_nhap_lan_dau()
        self.c.post("/api/dangxuat", headers=self.h)
        for _ in range(4):
            r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
            self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": "000000"}, headers=self.h)
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        r = self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": "000000"}, headers=self.h)
        self.assertEqual(r.status_code, 429)

    def test_dang_xuat_moi_may_khac_va_cookie_30_ngay(self):
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        khoa = r["khoa"]
        r2 = self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": totp.ma_cua_buoc(khoa, totp.buoc())}, headers=self.h)
        self.assertIn("Max-Age=2592000", r2.headers["set-cookie"])
        from fastapi.testclient import TestClient
        from maychu import khoidong
        may2 = TestClient(khoidong.app)
        r = may2.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        may2.post("/api/dangnhap/ma2lop", json={"ma_tam": r["ma_tam"], "ma": totp.ma_cua_buoc(khoa, totp.buoc() + 1)}, headers=self.h)
        self.assertEqual(self.c.post("/api/phien/thuhoi_khac", headers=self.h).json()["so"], 1)
        self.assertEqual(may2.get("/api/toi").status_code, 401)
        self.assertEqual(self.c.get("/api/toi").status_code, 200)
        self.assertIn("het_luc", self.c.post("/api/phien/giahan", headers=self.h).json())

    def test_lenh_dat_lai_mat_khau(self):
        self.dang_nhap_lan_dau()
        dap = iter(["mat-khau-dat-lai-01", "mat-khau-dat-lai-01"])
        self.assertEqual(datlai.chay(["--tat-2lop"], hoi=lambda _: next(dap), thumuc=self.thumuc), 0)
        self.assertEqual(self.c.get("/api/toi").status_code, 401)
        r = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": "mat-khau-dat-lai-01"}, headers=self.h).json()
        self.assertEqual(r["buoc"], "bat2lop")
        sai = iter(["", ""])
        self.assertEqual(datlai.chay([], hoi=lambda _: next(sai), thumuc=self.thumuc), 1)

    def test_khoa_chu_va_ket_khoa(self):
        p = khoachu.duong(self.thumuc)
        k1 = khoachu.lay(self.thumuc)
        self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
        self.assertEqual(khoachu.lay(self.thumuc), k1)
        ma = kho.cat("thu", "khoa-bi-mat-1234", self.thumuc)
        self.assertEqual(kho.doc(ma, self.thumuc), "khoa-bi-mat-1234")

    def test_cap_nhat(self):
        ds = capnhat.phan_tich_thaydoi("# T\n\n## 0.3.0\n- Dòng a\n- Dòng b\n\n## 0.2.0\n- Dòng c\n")
        self.assertEqual([(m["ban"], len(m["dong"])) for m in ds], [("0.3.0", 2), ("0.2.0", 1)])
        capnhat.ghi_khoi_dong(self.thumuc)  # lần khởi động thứ 02 cùng bản: không ghi thêm
        self.assertEqual([x["ban"] for x in capnhat.lich_su(self.thumuc)], [capnhat.ban_dang_chay()])


class KiemMaHoa(unittest.TestCase):
    def test_totp_rfc6238(self):
        khoa = __import__("base64").b32encode(b"12345678901234567890").decode()
        self.assertEqual(totp.ma_cua_buoc(khoa, 59 // 30), "287082")
        self.assertEqual(totp.ma_cua_buoc(khoa, 1111111109 // 30), "081804")

    def test_bam_mat_khau(self):
        h = matkhau.bam("abc-123-xyz")
        self.assertTrue(h.startswith("scrypt$"))
        self.assertTrue(matkhau.kiem("abc-123-xyz", h))
        self.assertFalse(matkhau.kiem("abc-123-xyZ", h))
        self.assertFalse(matkhau.kiem("x", None))


if __name__ == "__main__":
    unittest.main()
