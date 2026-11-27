"""Bài kiểm bản 0.7.2 (QĐ165, Y25): chuông thông báo bước 1 – 05 nguồn vào D03, chữ cụ thể, mốc đọc, 01 hàm lọc quyền.
Dữ liệu giả, không gọi mạng, không gọi CLI thật (QĐ126)."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import thongbao as tb
from maychu.hethong.mohinh import dangnhap_goi as dg

NB = " "
GOC = Path(__file__).resolve().parents[2]


def _luc(**kw) -> str:
    return (datetime.now(MUIGIO_VN) + timedelta(**kw)).isoformat(timespec="seconds")


class KiemChuong(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.t = Path(self.tam.name)
        self.cu = os.environ.get("IGM360_THUMUC_DULIEU")
        os.environ["IGM360_THUMUC_DULIEU"] = str(self.t)
        khoitao.tao_het(self.t)
        thongso.khoi_tao(self.t)
        dg._NHO_TRANGTHAI.clear()

    def tearDown(self):
        os.environ.pop("IGM360_THUMUC_DULIEU", None) if self.cu is None else os.environ.__setitem__("IGM360_THUMUC_DULIEU", self.cu)
        self.tam.cleanup()

    # ---- công cụ
    def _sql(self, file: str, sql: str, thamso=()):
        cn = ketnoi.mo(file, self.t)
        try:
            return cn.execute(sql, thamso).fetchall()
        finally:
            cn.close()

    def _d03(self) -> dict:
        return {k: (tt, gt, ng) for k, tt, gt, ng in self._sql(
            "Dulieu_Chinh", "SELECT khoa_chongtrung, trangthai, giatri, nguong FROM canhbao ORDER BY tao_luc, rowid")}

    def _mo(self) -> list:
        return sorted(k for k, (tt, _g, _n) in self._d03().items() if tt == "moi")

    def _goi(self, ma="goi_claude_01", tyle=None, datlai=None):
        goi, tk = ma.split("_")[1], int(ma.split("_")[2])
        dg.ghi_nguon(goi, tk, self.t)
        self._sql("Viecnen", "UPDATE nguon_ai SET tyle_tuan = ?, datlai_tuan_luc = ? WHERE ma = ?", (tyle, datlai, ma))

    def _khoa(self, dichvu: str, han: str | None) -> str:
        ma = maso.tao()
        self._sql("Baomat", "INSERT INTO kekhoa (id, dichvu, banma, kytu_cuoi, han, nguoi_nhap, trangthai)"
                            " VALUES (?, ?, x'00', '0000', ?, 'hethong', 'dung')", (ma, dichvu, han))
        return ma

    def _saoluu(self, luc: str, loi: bool) -> None:
        for i, ten in enumerate(ketnoi.CAC_FILE):
            self._sql("Nhatky", "INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua) VALUES (?, 'hangngay', ?, ?, ?)",
                      (maso.tao(), ten, luc, "loi" if loi and i == 2 else "xong_tren_may"))

    def _n02(self, tyle_ocung: int, swap: int = 0) -> None:
        self._sql("Nhatky", "INSERT INTO theodoi_maychu (id, luc, tyle_ocung, swap_dung) VALUES (?, ?, ?, ?)",
                  (maso.tao(), _luc(), tyle_ocung, swap))

    # ---- (1) 05 nguồn
    def test_goi_het_phien_va_dang_nhap_lai(self):
        self._goi()
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": False, "goi_dang_dung": None}):
            tb.quet_goi(self.t)
            tb.quet_goi(self.t)   # quét lại không thêm dòng
        self.assertEqual(self._mo(), ["goi_hetphien:goi_claude_01"])
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": False, "khong_ro": True}):
            tb.quet_goi(self.t)   # chưa kiểm được: giữ nguyên
        self.assertEqual(self._mo(), ["goi_hetphien:goi_claude_01"])
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": True, "goi_dang_dung": "max"}):
            tb.quet_goi(self.t)
        self.assertEqual(self._d03()["goi_hetphien:goi_claude_01"][0], "dadong")
        self.assertEqual(self._sql("Dulieu_Chinh", "SELECT lydo_dong FROM canhbao")[0][0], "Đã đăng nhập lại")

    def test_han_muc_tuan(self):
        self._goi(tyle=82, datlai=_luc(days=3))
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": True}):
            tb.quet_goi(self.t)
            self.assertEqual(self._d03()["hanmuc_tuan:goi_claude_01"], ("moi", 82, 80))
            self._sql("Viecnen", "UPDATE nguon_ai SET tyle_tuan = 91")
            tb.quet_goi(self.t)
            self.assertEqual(self._d03()["hanmuc_tuan:goi_claude_01"], ("moi", 91, 80))   # cùng 01 dòng, số mới
            self._sql("Viecnen", "UPDATE nguon_ai SET datlai_tuan_luc = ?", (_luc(minutes=-5),))
            tb.quet_goi(self.t)   # đã qua giờ đặt lại hạn mức tuần: số cũ không còn đúng
        self.assertEqual(self._d03()["hanmuc_tuan:goi_claude_01"][0], "dadong")
        thongso.dat("tyle_bao_hanmuc_tuan", "95", "2099-01-01", thumuc=self.t)   # thông số anh đổi được
        self.assertEqual(thongso.THEO_TEN["tyle_bao_hanmuc_tuan"][5], "80")

    def test_goi_da_go_thi_dong(self):
        self._goi(tyle=85, datlai=_luc(days=1))
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": False}):
            tb.quet_goi(self.t)
            self.assertEqual(len(self._mo()), 2)
            self._sql("Viecnen", "UPDATE nguon_ai SET trangthai = 'ngung'")
            tb.quet_goi(self.t)
        self.assertEqual(self._mo(), [])

    def test_khoa_sap_het_roi_het_han_roi_gia_han_roi_xoa(self):
        hom = datetime.now(MUIGIO_VN).date()
        a = self._khoa("composio", (hom + timedelta(days=3)).isoformat())
        b = self._khoa("tiktok_quangcao", (hom + timedelta(days=30)).isoformat())
        self._khoa("totp_2lop", (hom - timedelta(days=1)).isoformat())   # khóa nội bộ: không báo
        tb.quet_khoa(self.t)
        self.assertEqual(self._mo(), [f"khoa_saphethan:{a}"])
        self.assertEqual(self._d03()[f"khoa_saphethan:{a}"][1:], (3, 5))
        self._sql("Baomat", "UPDATE kekhoa SET han = ? WHERE id = ?", ((hom - timedelta(days=1)).isoformat(), a))
        tb.quet_khoa(self.t)
        self.assertEqual(self._mo(), [f"khoa_hethan:{a}"])
        self._sql("Baomat", "UPDATE kekhoa SET han = ? WHERE id = ?", ((hom + timedelta(days=90)).isoformat(), a))
        self._sql("Baomat", "UPDATE kekhoa SET han = ? WHERE id = ?", ((hom - timedelta(days=2)).isoformat(), b))
        tb.quet_khoa(self.t)
        self.assertEqual(self._mo(), [f"khoa_hethan:{b}"])
        self._sql("Baomat", "DELETE FROM kekhoa WHERE id = ?", (b,))
        tb.quet_khoa(self.t)
        self.assertEqual(self._mo(), [])

    def test_sao_luu_loi_01_dong_roi_dong(self):
        hom = datetime.now(MUIGIO_VN).date().isoformat()   # ngày hôm nay (chữ "lúc" chỉ dùng cho lỗi trong ngày)
        self._saoluu(f"{hom}T02:00:05+07:00", loi=True)
        tb.quet_saoluu(self.t)
        self._saoluu(f"{hom}T02:01:05+07:00", loi=True)   # lịch thử lại mỗi phút: vẫn 01 dòng
        tb.quet_saoluu(self.t)
        self.assertEqual(self._mo(), ["saoluu_loi"])
        self.assertEqual(tb.danh_sach(thumuc=self.t)["ds"][0]["chu"], "Sao lưu lúc 02:00 không xong")
        self._saoluu(f"{hom}T02:02:05+07:00", loi=False)
        tb.quet_saoluu(self.t)
        self.assertEqual(self._mo(), [])
        self.assertEqual(self._sql("Dulieu_Chinh", "SELECT lydo_dong FROM canhbao")[0][0], "Sao lưu đã xong lúc 02:02")

    def test_sao_luu_loi_tu_hom_truoc(self):   # U6 S3 (K-TB3)
        hom_qua = (datetime.now(MUIGIO_VN) - timedelta(days=1)).replace(hour=2, minute=0, second=5, microsecond=0)
        self._saoluu(hom_qua.isoformat(timespec="seconds"), loi=True)
        tb.quet_saoluu(self.t)
        self.assertEqual(tb.danh_sach(thumuc=self.t)["ds"][0]["chu"],
                         f"Sao lưu không xong từ 02:00 ngày{NB}{hom_qua:%d}/{hom_qua:%m}")
        self._saoluu(_luc(), loi=True)   # hôm nay vẫn lỗi: giữ 01 dòng, giờ lượt lỗi đầu
        tb.quet_saoluu(self.t)
        self.assertEqual(len(tb.danh_sach(thumuc=self.t)["ds"]), 1)

    def test_o_cung_va_tep_hoan_doi(self):
        self._sql("Dulieu_Chinh", "INSERT INTO canhbao (id, loai, nguong, giatri, khoa_chongtrung, trangthai, tao_luc)"
                                  " VALUES (?, 'sukien', 100, 240, 'swap_vuot_nguong', 'moi', ?)", (maso.tao(), _luc()))
        self._n02(8612, swap=240)
        tb.quet_maychu(self.t)
        self.assertEqual(self._mo(), ["ocung_vuot", "swap_vuot_nguong"])
        self.assertEqual(self._d03()["ocung_vuot"][1:], (86, 70))
        self._n02(6500, swap=0)
        tb.quet_maychu(self.t)
        self.assertEqual(self._mo(), [])

    def test_ban_moi_roi_da_cai(self):
        kq = {"ban_dang": "0.7.2", "ban_moi": "0.7.3", "co_ban_moi": True, "loi": None}
        with mock.patch.object(capnhat, "kiem_tra", return_value=kq):
            tb.quet_banmoi(self.t)
        self.assertEqual(self._mo(), ["banmoi:0.7.3"])
        with mock.patch.object(capnhat, "kiem_tra", return_value={**kq, "ban_moi": "0.7.4"}):
            tb.quet_banmoi(self.t)
        self.assertEqual(self._mo(), ["banmoi:0.7.4"])
        with mock.patch.object(capnhat, "kiem_tra", return_value={"ban_dang": "0.7.4", "ban_moi": "0.7.4", "co_ban_moi": False, "loi": None}):
            tb.quet_banmoi(self.t)
        self.assertEqual(self._mo(), [])
        self.assertIn("Đã cài bản 0.7.4", [r[0] for r in self._sql("Dulieu_Chinh", "SELECT lydo_dong FROM canhbao")])
        with mock.patch.object(capnhat, "kiem_tra", return_value={"ban_dang": "0.7.4", "ban_moi": None, "co_ban_moi": False, "loi": "x"}):
            tb.quet_banmoi(self.t)   # không kết nối được kho ảnh: không đổi gì

    def test_loi_01_nguon_khong_dung_nguon_khac(self):
        self._n02(9000)
        with mock.patch.object(capnhat, "kiem_tra", side_effect=RuntimeError("hỏng")):
            kq = tb.quet(self.t)
        self.assertEqual(kq["quet_banmoi"], "RuntimeError")
        self.assertEqual(kq["quet_maychu"], "dat")
        self.assertIn("ocung_vuot", self._mo())

    # ---- (2) chữ, thứ tự, mốc đọc, lọc quyền
    def _du_lieu_mau(self):
        hom = datetime.now(MUIGIO_VN).date()
        a = self._khoa("composio", (hom + timedelta(days=5)).isoformat())
        self._goi(tyle=82, datlai=_luc(days=2))
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": False}):
            tb.quet_goi(self.t)
        tb.quet_khoa(self.t)
        self._n02(8600)
        tb.quet_maychu(self.t)
        with mock.patch.object(capnhat, "kiem_tra", return_value={"ban_dang": "0.7.2", "ban_moi": "0.7.3", "co_ban_moi": True, "loi": None}):
            tb.quet_banmoi(self.t)
        return a

    def test_chu_cu_the_va_thu_tu(self):
        self._du_lieu_mau()
        for i, k in enumerate(("goi_hetphien:goi_claude_01", "ocung_vuot")):   # giờ tạo khác nhau để thứ tự "mới trước" rõ
            self._sql("Dulieu_Chinh", "UPDATE canhbao SET tao_luc = ? WHERE khoa_chongtrung = ?", (_luc(seconds=-60 + i), k))
        kq = tb.danh_sach(thumuc=self.t)
        chu = [x["chu"].replace(NB, " ") for x in kq["ds"]]
        self.assertEqual(chu[:2], ["Ổ cứng máy chủ dùng 86%, quá ngưỡng 70%", "Gói Claude · Tài khoản 1 hết phiên đăng nhập"])
        self.assertEqual(set(chu[2:4]), {"Khóa composio còn 05 ngày hết hạn", "Gói Claude · Tài khoản 1 đã dùng 82% hạn mức tuần"})
        self.assertEqual(chu[4], "Có bản mới 0.7.3")
        self.assertEqual([x["muc"] for x in kq["ds"]], ["do", "do", "xem", "xem", "tin"])
        self.assertEqual(kq["so_moi"], 5)
        x = {i["loai"]: i for i in kq["ds"]}
        self.assertEqual((x["goi_hetphien"]["di"], x["goi_hetphien"]["noi"], x["goi_hetphien"]["icon"]), ("13", "Mô hình AI", "brain-circuit"))
        self.assertEqual((x["khoa_saphethan"]["di"], x["khoa_saphethan"]["noi"]), ("ketkhoa", "Cài đặt › Két khóa"))
        self.assertEqual((x["ocung_vuot"]["di"], x["ocung_vuot"]["cuon"], x["ocung_vuot"]["noi"]), ("03", "o-maychu", "Bảng điều hành › Máy chủ"))
        self.assertEqual((x["banmoi"]["di"], x["banmoi"]["noi"], x["banmoi"]["icon"]), ("capnhat", "Cài đặt › Cập nhật", "cloud-download"))
        self.assertIn("Tài" + NB + "khoản" + NB + "1", x["goi_hetphien"]["chu"])   # nối không ngắt (Z7b)
        self.assertTrue(x["goi_hetphien"]["chu"].endswith("đăng" + NB + "nhập"))   # U6 S2
        self.assertIn("05" + NB + "ngày", x["khoa_saphethan"]["chu"])
        self.assertEqual(tb._chu("swap_vuot_nguong", "swap_vuot_nguong", {"giatri": 240, "nguong": 100}, {}, {}).replace(NB, " "),
                         "Máy chủ dùng tệp hoán đổi 240 MB, quá 100 MB")
        self.assertEqual(tb._chu("khoa_hethan", "khoa_hethan:k1", {"giatri": None, "nguong": None}, {"k1": "TikTok quảng cáo"}, {}).replace(NB, " "),
                         "Khóa TikTok quảng cáo đã hết hạn")

    def test_doc_het_ghi_moc_khong_doi_d03(self):
        self._du_lieu_mau()
        truoc = self._d03()
        moc = thongso.dat_moc_doc(thumuc=self.t, luc=datetime.now(MUIGIO_VN) + timedelta(seconds=1))
        kq = tb.danh_sach(thumuc=self.t)
        self.assertEqual((kq["so_moi"], kq["moc_doc"]), (0, moc))
        self.assertTrue(all(not x["moi"] for x in kq["ds"]))
        self.assertEqual(len(kq["ds"]), 5)            # việc chưa xử lý vẫn hiện ở "Đã xem, còn mở"
        self.assertEqual(self._d03(), truoc)          # QĐ165: D03 không đổi trạng thái
        self._sql("Dulieu_Chinh", "UPDATE canhbao SET tao_luc = ? WHERE khoa_chongtrung = 'ocung_vuot'", (_luc(minutes=5),))
        kq = tb.danh_sach(thumuc=self.t)
        self.assertEqual((kq["so_moi"], kq["ds"][0]["loai"], kq["ds"][0]["moi"]), (1, "ocung_vuot", True))
        moc2 = thongso.dat_moc_doc(thumuc=self.t, luc=datetime.now(MUIGIO_VN) + timedelta(minutes=10))   # bấm lại cùng ngày
        self.assertEqual(thongso.doc_moc_doc(self.t), moc2)
        dong = self._sql("Dulieu_Chinh", "SELECT giatri, hieuluc_den FROM thongso WHERE ten = 'moc_doc_chuong' ORDER BY tao_luc")
        self.assertEqual(len(dong), 2)
        self.assertIsNotNone(dong[0][1])
        self.assertIsNone(dong[1][1])
        self.assertNotIn("moc_doc_chuong", [x["ten"] for x in thongso.doc_het(self.t)["thongso"]])   # không hiện ở Cài đặt

    def test_loc_quyen_01_ham_dung_cho_so_va_danh_sach(self):
        self._du_lieu_mau()
        with mock.patch.object(tb, "loc_quyen", side_effect=lambda n, ds: [d for d in ds if d["khoa_chongtrung"] == "ocung_vuot"]) as m:
            kq = tb.danh_sach("nguoi_gia", thumuc=self.t)
        m.assert_called_once()
        self.assertEqual((kq["so_moi"], [x["loai"] for x in kq["ds"]]), (1, ["ocung_vuot"]))
        ds = [{"id": "x"}]
        self.assertIs(tb.loc_quyen("chu", ds), ds)   # GĐ 1: trả hết cho Chủ (QĐ141)

    # ---- (3) giao diện, lịch, bản
    def test_giao_dien_lich_ban(self):
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        html = (GOC / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        for c in ("CHU_BA.hienDoc(hai(cu.length))", "data-tbthe", "rong: 'Không có thông báo nào còn mở.'",   # QĐ553 (3): 02 thẻ, tin đã đọc ẩn
                  "id=\"tb-dochet\" data-dochet", "api('/thongbao/dochet', {})", "}, 60e3);",
                  "d === q ? 'Hôm qua ' + gio(iso)", "d.di === 'capnhat'", "esc(lucTb(x.luc)) + ' · ' + esc(x.noi)"):
            self.assertIn(c, js)
        for c in ('id="tha-chuong"', "#tha-chuong{width:380px;max-height:min(560px,75vh)",
                  ".mb #tha-chuong{width:auto;max-height:70vh}", ".tin-n{border-color:var(--vien-tin)}"):
            self.assertIn(c, html)
        self.assertNotIn("Cảnh báo mới", html)
        self.assertNotIn(".mb .vi-tri .tha{", html)   # U6 S1: điện thoại dùng .mb .tha (fixed, cách 02 mép 08) như 0.7.1
        self.assertIn(".mb .tha{position:fixed;left:8px;right:8px;width:auto;top:120px}", html)
        self.assertEqual(js.count("demSo(); }, 60"), 1)   # 01 vòng 60 giây
        lich = (GOC / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        for c in ("thongbao.quet)", "thongbao.quet_maychu)", "thongbao.quet_saoluu)", "NHIP_THONGBAO_GIAY = 600"):
            self.assertIn(c, lich)
        self.assertGreaterEqual(tuple(map(int, (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))), (0, 7, 2))
        muc = (GOC / "THAYDOI.md").read_text(encoding="utf-8").split("## 0.7.2", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Tóm tắt: Chuông báo tin mới, tự cập nhật", muc)


class KiemApi(unittest.TestCase):
    """/api/demso, /api/thongbao/dochet qua máy chủ web thật (không lịch nền)."""
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH")}
        os.environ.update(IGM360_THUMUC_DULIEU=self.tam.name, IGM360_LICH="tat")
        from maychu.web import api
        self.api = api
        khoitao.tao_het(Path(self.tam.name))
        thongso.khoi_tao()
        self.p = {"nguoidung_id": maso.tao()}

    def tearDown(self):
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def test_dem_so_va_doc_het(self):
        cn = ketnoi.mo("Nhatky")
        try:
            cn.execute("INSERT INTO theodoi_maychu (id, luc, tyle_ocung, swap_dung) VALUES (?, ?, 9100, 0)", (maso.tao(), _luc()))
        finally:
            cn.close()
        tb.quet_maychu()
        d = self.api.dem_so(self.p)
        self.assertEqual((d["so_moi"], len(d["thongbao"]), d["thongbao"][0]["moi"]), (1, 1, True))
        self.assertNotIn("canhbao", d)
        with mock.patch.object(thongso, "datetime") as m:
            m.now.return_value = datetime.now(MUIGIO_VN) + timedelta(seconds=2)
            self.api.doc_het_thongbao(self.p)
        d = self.api.dem_so(self.p)
        self.assertEqual((d["so_moi"], len(d["thongbao"]), d["thongbao"][0]["moi"]), (0, 1, False))
        cn = ketnoi.mo("Dulieu_Chinh")
        try:
            self.assertEqual(cn.execute("SELECT nguoi_dat FROM thongso WHERE ten = 'moc_doc_chuong'").fetchone()[0],
                             self.p["nguoidung_id"])
        finally:
            cn.close()


if __name__ == "__main__":
    unittest.main()
