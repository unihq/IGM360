"""Bài kiểm 0.10.0 – múi giờ D-a (QĐ636; CDA PTD-20 mục 5, 5.5).

Cấm lấy giờ / ngày ngoài `maychu/dulieu/muigio.py` (dò mã) · danh sách chỗ được phép cắt ngày `[:10]` / strftime ngày ·
giờ lưu luôn +07:00 · đổi sang múi khác (vd. Tokyo) thì ngày số liệu, giờ hiện theo múi đó, 0 dòng dữ liệu viết lại ·
tên múi lạ từ chối · đường gọi đổi múi chỉ Chủ, hỏi mật khẩu + mã 02 lớp, ghi P01 + F04.
Phần đổi sang múi khác cần cơ sở múi giờ của máy: máy Windows không cài `tzdata` thì bỏ qua (máy GitHub Linux chạy đủ).
Mật khẩu, mã giả ghép lúc chạy.
"""

import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import available_timezones

from maychu.dulieu import khoitao, ketnoi, muigio
from maychu.hethong import antoan
from maychu.hethong.caidat import thongso

GOC = Path(__file__).resolve().parents[2]
CO_MUI = bool(available_timezones())
MK = "-".join(["matkhau", "kiem", "0100"])
# Chỗ được phép (QĐ636, CDA 5.5): (tệp, đoạn chữ của dòng) → lý do. Chỗ mới không có ở đây là đỏ.
DUOC_CAT_NGAY = {
    ("maychu/dulieu/muigio.py", "return luc[:10] if len(luc) <= 10"): "chuỗi chỉ có ngày, giữ nguyên",
    ("maychu/dulieu/doidau.py", '(dang[1] or "")[:10] >= hom_nay'): "ngày hiệu lực đã ghi (②), so với hôm nay (②)",
}
DUOC_STRFTIME_NGAY = {
    ("maychu/dulieu/saoluu.py", 'astimezone(muigio.MUIGIO_LUU).strftime("%Y-%m-%d")'): "① tên tệp sao lưu theo giờ lưu",
    ("maychu/dulieu/saoluu.py", 'luc.strftime("%Y-%m-%d")'): "① tên thư mục bản chụp (luc đã đổi về giờ lưu)",
    ("maychu/hethong/giamsat/lich.py", 'bay_gio.strftime("%Y-%m-%d %H")'): "③ mốc giờ lịch theo múi đã chọn",
}
DUOC_MUIGIO_VN = {
    ("maychu/chay.py", "MUIGIO_VN = timezone(timedelta(hours=7))"): "chạy độc lập trước khi nạp maychu (chọn bản chạy)",
    ("maychu/chay.py", 'return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")'): "① giờ lưu của chay.py",
    ("maychu/dulieu/saoluu.py", "MUIGIO_VN = muigio.MUIGIO_LUU"): "tên cũ giữ cho bài kiểm cũ",
}


def _dong_ma(mau: re.Pattern) -> list[tuple[str, str]]:
    """(tệp, dòng) có `mau` ở phần mã (bỏ chú thích sau #), toàn bộ maychu/ trừ muigio.py."""
    ra = []
    for p in sorted((GOC / "maychu").rglob("*.py")):
        ten = p.relative_to(GOC).as_posix()
        for d in p.read_text(encoding="utf-8").splitlines():
            ma = d.split("  #", 1)[0]
            if mau.search(ma):
                ra.append((ten, d.strip()))
    return ra


def _ngoai_danh_sach(ra, duoc) -> list:
    return [x for x in ra if not any(x[0] == t and doan in x[1] for t, doan in duoc)]


class KiemCam(unittest.TestCase):
    def test_khong_lay_gio_ngoai_muigio(self):
        self.assertEqual(_ngoai_danh_sach(_dong_ma(re.compile(r"\bMUIGIO_VN\b")), DUOC_MUIGIO_VN), [])
        ra = [x for x in _dong_ma(re.compile(r"datetime\.now\(|date\.today\(|datetime\.utcnow\(|fromtimestamp\(|MUIGIO_LUU"))
              if x[0] != "maychu/dulieu/muigio.py"]
        self.assertEqual(_ngoai_danh_sach(ra, DUOC_MUIGIO_VN | {("maychu/dulieu/saoluu.py", "muigio.MUIGIO_LUU"): ""}), [])

    def test_cat_ngay_chi_o_cho_duoc_phep(self):
        self.assertEqual(_ngoai_danh_sach(_dong_ma(re.compile(r"\[:10\]")), DUOC_CAT_NGAY), [])
        self.assertEqual(_ngoai_danh_sach(_dong_ma(re.compile(r'strftime\("%Y-%m-%d')), DUOC_STRFTIME_NGAY), [])

    def test_giao_dien_cat_gio_chi_sau_khi_doi_mui(self):
        # CDA 5.5: giao diện chỉ cắt ngày / giờ trên chuỗi đã đổi sang múi chọn (hien, theoMui, caVn) hoặc chuỗi ngày.
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8").splitlines()
        duoc = ("const ngay = iso =>", "const gio = iso =>", "const homNay = () =>", "const luc = iso =>", "const gioPhut = sec =>",
                "const lucTb = iso =>", "  return d === h ? gio(iso)", "    D.soLuc = theoMui(", "  const mai = theoMui(",
                "  const v = caVn(t), n = v.slice(0, 10);", "  const ngayChu = n === caVn(bay)", "  return (v.slice(11, 16)",
                "  const v = caVn(t), lech =", "const caKiemTiep =", "const caHomNay =", "      + '<span data-l=\"' + CA.cot[3]",
                "  else if (sk) { const {x, s} = sk", "        +caVn(s.luc).slice(11, 13)", "const denLuc = iso =>",
                "const gioKiem = iso =>", "function nhomNgay(iso)")
        la = [d.strip()[:90] for d in js if re.search(r"\.slice\((0, 10|11, 1[36]|8, 10|5, 7)\)", d.split("//", 1)[0])
              and not d.startswith(duoc)]
        self.assertEqual(la, [])
        ma = "\n".join(d.split("//", 1)[0] for d in js)
        self.assertNotIn("7 * 3600e3", ma)                                              # không cộng cứng giờ Việt Nam
        self.assertNotIn("+07:00", ma)

    def test_danh_sach_duoc_phep_con_dung(self):
        # chỗ được phép phải còn trong mã (sửa mã thì sửa danh sách, không để dòng thừa che lỗi)
        for (t, doan) in list(DUOC_CAT_NGAY) + list(DUOC_STRFTIME_NGAY) + list(DUOC_MUIGIO_VN):
            self.assertIn(doan, (GOC / t).read_text(encoding="utf-8"), t)


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"})
        bien.start()
        self.addCleanup(bien.stop)
        muigio.xoa_dem()
        self.addCleanup(muigio.xoa_dem)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)


class KiemHam(Nen):
    def test_gio_luu_luon_07(self):
        self.assertTrue(muigio.gio_luu().endswith("+07:00"))
        utc = datetime(2026, 11, 27, 16, 0, tzinfo=timezone.utc)
        self.assertEqual(muigio.gio_luu(utc), "2026-11-27T23:00:00+07:00")
        self.assertEqual(muigio.tu_so_giay(utc.timestamp()), "2026-11-27T23:00:00+07:00")

    def test_mac_dinh_viet_nam(self):
        self.assertEqual(thongso.doc_mot("muigio", None, self.dl), "Asia/Ho_Chi_Minh")
        self.assertEqual(muigio.ngay_cua("2026-11-27T23:30:00+07:00"), "2026-11-27")
        self.assertEqual(muigio.ngay_cua("2026-11-27"), "2026-11-27")
        self.assertEqual(muigio.gio_hien("2026-11-27T23:30:00+07:00").strftime("%H:%M"), "23:30")

    def test_ten_la_tu_choi(self):
        for ten in ("", "Abc/Xyz", "../etc", "Asia/Ho_Chi_Minh; x"):
            self.assertFalse(muigio.kiem_ten(ten), ten)
            self.assertEqual(thongso.doi_muigio("muigio", ten, "hethong", self.dl), {"loi": thongso.CHU_MUIGIO["ten_la"]})
        self.assertEqual(thongso.dat("muigio", "Asia/Tokyo", "2026-12-01", nguoi="hethong", thumuc=self.dl)["loi"],
                         "Không có thông số này")                                    # chỉ đổi qua đường riêng
        self.assertNotIn("muigio", {x["ten"] for x in thongso.doc_het(self.dl)["thongso"]})   # không hiện ở ngăn Thông số

    @unittest.skipUnless(CO_MUI, "máy không có cơ sở múi giờ (Windows chưa cài tzdata) – máy GitHub chạy")
    def test_doi_tokyo_ngay_va_gio_hien_theo_mui_moi_khong_viet_lai(self):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            truoc = cn.execute("SELECT id, luc FROM nhatky_thaotac ORDER BY id").fetchall()
        finally:
            cn.close()
        kq = thongso.doi_muigio("muigio", "Asia/Tokyo", "hethong", self.dl)
        self.assertEqual(kq, {"ok": True, "doi": True})
        self.assertEqual(muigio.ngay_cua("2026-11-27T22:30:00+07:00"), "2026-11-28")   # 00:30 giờ Tokyo
        self.assertEqual(muigio.gio_hien("2026-11-27T22:30:00+07:00").strftime("%H:%M"), "00:30")
        self.assertTrue(muigio.gio_luu().endswith("+07:00"))                          # ① giờ lưu không đổi
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            sau = cn.execute("SELECT id, luc FROM nhatky_thaotac ORDER BY id").fetchall()
            f04 = cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE lenhcon = 'doi_muigio'").fetchall()
        finally:
            cn.close()
        self.assertEqual([d for d in sau if d not in truoc and d[0] not in {x[0] for x in truoc}].__len__(), 1)  # chỉ thêm 01 dòng F04
        self.assertTrue(set(truoc) <= set(sau))                                        # dòng cũ giữ nguyên
        self.assertEqual(f04, [("muigio: Asia/Ho_Chi_Minh → Asia/Tokyo",)])
        self.assertEqual(len(thongso.lich_su("muigio", self.dl)), 2)                     # lịch sử P01 tra được múi cũ
        self.assertEqual(thongso.doi_muigio("muigio", "Asia/Tokyo", "hethong", self.dl), {"ok": True, "doi": False})


class KiemDuongGoi(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.dl = Path(self.tam.name)
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH", "IGM360_ADMIN_USER",
                                                   "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(self.dl), IGM360_LICH="tat", IGM360_ADMIN_USER="chu",
                          IGM360_ADMIN_PASSWORD=MK, IGM360_COOKIE_SECURE="0")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.hethong.taikhoan import nguoidung, totp
        self.nd, self.totp = nguoidung, totp
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}
        muigio.xoa_dem()

    def tearDown(self):
        self.c.__exit__(None, None, None)
        antoan.CHE_DO.update(an_toan=False)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.nd._MA_TAM.clear()
        self.nd._BUOC_DA_DUNG.clear()
        muigio.xoa_dem()
        self.tam.cleanup()

    def ma(self, khoa):
        self.nd._BUOC_DA_DUNG.clear()
        return self.totp.ma_cua_buoc(khoa, self.totp.buoc())

    def test_xem_va_doi_chi_khi_dung_mat_khau_ma(self):
        kq = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        khoa = kq["khoa"]
        self.assertEqual(self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": self.ma(khoa)},
                                     headers=self.h).status_code, 200)
        r = self.c.get("/api/muigio", headers=self.h)
        self.assertEqual((r.status_code, r.json()["muigio"], r.json()["ban"]), (200, "Asia/Ho_Chi_Minh", None))
        dich = "Asia/Tokyo" if CO_MUI else "Asia/Ho_Chi_Minh"
        r = self.c.post("/api/muigio", json={"giatri": dich, "matkhau": MK + "x", "ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual(r.status_code, 400)                                              # sai mật khẩu: không đổi
        self.assertEqual(thongso.doc_mot("muigio", None, self.dl), "Asia/Ho_Chi_Minh")
        r = self.c.post("/api/muigio", json={"giatri": "Abc/Xyz", "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual((r.status_code, r.json()["detail"]), (400, thongso.CHU_MUIGIO["ten_la"]))
        r = self.c.post("/api/muigio", json={"giatri": dich, "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(thongso.doc_mot("muigio", None, self.dl), dich)
        with mock.patch.object(muigio, "ly_do_ban", return_value="Đang nạp số liệu"):
            r = self.c.post("/api/muigio", json={"giatri": dich, "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual(r.status_code, 409)                                          # đang nạp / chốt kỳ: từ chối


if __name__ == "__main__":
    unittest.main()
