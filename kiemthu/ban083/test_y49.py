"""Bài kiểm Y49 (bản 0.8.3): công tắc "Sao lưu Google Drive" (QĐ277, QĐ278, QĐ280, QĐ282), luật C dòng chờ đi theo tệp
(QĐ279), bật mà chưa nối dọn như khi tắt (QĐ283), D1 bản sao trước khi nâng giữ 30 ngày + khoá Quay về (QĐ281, QĐ284,
QĐ287), bỏ chữ "chụp" trên giao diện (QĐ288, QĐ290). PTD-15 mục 6.2 (04 điểm) và 6.3 (D1-1 đến D1-6).
Không gọi mạng, không gọi CLI thật.
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, maso, saoluu
from maychu.hethong import antoan, capnhat, tiendo
from maychu.hethong.caidat import thongso

GOC = Path(__file__).resolve().parents[2]
GIAODIEN = GOC / "maychu" / "web" / "giaodien"
LUC = datetime(2026, 11, 22, 2, 5, tzinfo=saoluu.MUIGIO_VN)


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        self.env = os.environ.get("IGM360_THUMUC_DULIEU")
        os.environ["IGM360_THUMUC_DULIEU"] = str(self.thumuc)
        khoitao.tao_het(self.thumuc)
        self.goc = saoluu.thumuc_saoluu(self.thumuc)

    def tearDown(self):
        if self.env is None:
            os.environ.pop("IGM360_THUMUC_DULIEU", None)
        else:
            os.environ["IGM360_THUMUC_DULIEU"] = self.env
        antoan.CHE_DO["an_toan"] = False
        self.tam.cleanup()

    def bat(self, bat=True):
        thongso.gat("saoluu_drive", bat, "hethong", self.thumuc)

    def hang_cho(self, loai="saoluu"):
        cn = ketnoi.mo("Hotho", self.thumuc)
        try:
            return cn.execute("SELECT duongdan_tam, trangthai FROM cho_day_drive WHERE loai = ?", (loai,)).fetchall()
        finally:
            cn.close()

    def f04(self, congcu, lenhcon):
        cn = ketnoi.mo("Nhatky", self.thumuc)
        try:
            return cn.execute("SELECT luc, thamso_tomtat FROM nhatky_thaotac WHERE congcu = ? AND lenhcon = ? ORDER BY luc",
                              (congcu, lenhcon)).fetchall()
        finally:
            cn.close()

    def ngay(self, *ds):
        for d in ds:
            saoluu.chay(self.thumuc, LUC.replace(day=d))


# ---------------- Công tắc (QĐ277, QĐ278) ----------------
class KiemCongTac(Nen):
    def test_mac_dinh_tat_va_o_dem_tinh_them(self):
        self.assertFalse(thongso.drive_bat(self.thumuc))                       # chưa có dòng nào: coi là tắt
        thongso.khoi_tao(self.thumuc)
        self.assertFalse(thongso.drive_bat(self.thumuc))
        d = thongso.doc_het(self.thumuc)
        t = next(x for x in d["thongso"] if x["ten"] == "saoluu_drive")
        self.assertEqual((t["nhom"], t["nhan"], t["giatri"], t["giatri_chu"], t["cong_tac"], t["nguoi_dat"]),
                         ("Máy chủ và bảo mật", "Sao lưu Google Drive", "0", "Tắt", True, "hethong"))
        self.assertEqual(t["giai_thich"], "Tắt khi đang phát triển. Khi dùng thật, bật và nối Drive.")
        ten = [x["ten"] for x in d["thongso"]]
        self.assertEqual(ten.index("saoluu_drive") + 1, ten.index("nguong_cho_day_drive"))   # Z21: đứng trên ngưỡng chờ Drive
        self.assertEqual(d["tong"], len(thongso.DANHMUC) - len(thongso.GIAIDOAN_SAU)
                         - len(getattr(thongso, "AN_O_THONGSO", ())))      # ô đếm tính thêm thông số mới; 0.8.4: trừ thông số ẩn (Y46)

    def test_gat_nhieu_lan_trong_ngay_giu_lich_su(self):
        thongso.khoi_tao(self.thumuc)
        for bat in (True, False, True):
            self.assertEqual(thongso.gat("saoluu_drive", bat, "hethong", self.thumuc), {"ok": True, "doi": True})
            self.assertEqual(thongso.drive_bat(self.thumuc), bat)
        self.assertEqual(thongso.gat("saoluu_drive", True, "hethong", self.thumuc), {"ok": True, "doi": False})
        ls = thongso.lich_su("saoluu_drive", self.thumuc)
        self.assertEqual([x["giatri"] for x in ls], ["1", "0", "1", "0"])         # không xoá dòng cũ (luật P01)
        self.assertEqual(sum(1 for x in ls if x["hieuluc_den"] is None), 1)
        self.assertIn("loi", thongso.gat("nguong_ocung", True, "hethong", self.thumuc))   # không phải công tắc

    def test_y49b_n3_dat_khong_nhan_cong_tac(self):
        thongso.khoi_tao(self.thumuc)
        kq = thongso.dat("saoluu_drive", "1", "2099-01-01", nguoi="hethong", thumuc=self.thumuc)
        self.assertEqual(kq, {"loi": "Thông số này đổi bằng công tắc", "o": "giatri"})
        self.assertFalse(thongso.drive_bat(self.thumuc))
        self.assertEqual(len(thongso.lich_su("saoluu_drive", self.thumuc)), 1)   # chỉ dòng khởi tạo, không thêm dòng

    def test_tat_thi_khong_xep_hang_cho(self):
        kq = saoluu.chay(self.thumuc, LUC)
        self.assertEqual(kq["ketqua"], "xong_tren_may")
        self.assertEqual(self.hang_cho(), [])
        self.assertEqual({json.loads(d["ketqua_tungbuoc_json"])["5_day_drive"] for d in kq["file"]}, {"bo_qua_drive_tat"})
        self.assertEqual(len(list((self.goc / "2026-11-22").glob("*.mahoa"))), 7)   # bước 1–4 giữ nguyên

    def test_bat_ma_chua_noi_van_xep_hang_cho(self):
        self.bat()
        saoluu.chay(self.thumuc, LUC)
        self.assertEqual(len(self.hang_cho()), 7)                               # QĐ283: nối trong 03 ngày thì vẫn lên


# ---------------- Luật C (QĐ279), QĐ283, PTD-15 6.2 điểm 1–3 ----------------
class KiemLuatC(Nen):
    def test_tat_don_tep_va_dong_cung_luot(self):
        self.bat()
        self.ngay(18, 19)                                                      # 14 dòng chờ của 02 ngày đầu
        self.bat(False)
        self.ngay(20, 21, 22)
        con = sorted(p.name for p in self.goc.iterdir() if len(p.name) == 10)
        self.assertEqual(con, ["2026-11-20", "2026-11-21", "2026-11-22"])          # luật 03 ngày, không giữ tệp chờ
        self.assertEqual(self.hang_cho(), [])                                   # dòng đi theo tệp

    def test_bat_ma_chua_noi_don_nhu_khi_tat(self):
        self.bat()
        self.ngay(18, 19, 20, 21, 22)
        con = sorted(p.name for p in self.goc.iterdir() if len(p.name) == 10)
        self.assertEqual(con, ["2026-11-20", "2026-11-21", "2026-11-22"])
        dong = self.hang_cho()
        self.assertEqual(len(dong), 21)
        self.assertTrue(all(Path(d[0]).exists() for d in dong))               # mọi dòng còn lại đều trỏ tệp có thật

    def test_bat_va_da_noi_giu_tep_cho(self):
        self.bat()
        with mock.patch("maychu.ketnoi.drive.dang_noi", return_value=True):
            self.ngay(18, 19, 20, 21, 22)
        self.assertEqual(len([p for p in self.goc.iterdir() if len(p.name) == 10]), 5)   # như cũ: chưa đẩy thì giữ
        self.assertEqual(len(self.hang_cho()), 35)

    def test_chi_xoa_dong_saoluu_dang_cho(self):
        cn = ketnoi.mo("Hotho", self.thumuc)
        try:
            for loai, tt in (("saoluu", "cho"), ("saoluu", "loi"), ("saoluu", "xong"), ("filegoc", "cho")):
                cn.execute("INSERT INTO cho_day_drive (id, loai, duongdan_tam, trangthai, so_lan_thu, tao_luc)"
                           " VALUES (?, ?, ?, ?, 0, ?)", (maso.tao(), loai, str(self.thumuc / "khong_con.mahoa"), tt, LUC.isoformat()))
        finally:
            cn.close()
        self.assertEqual(saoluu._don_dong_mat_tep(self.thumuc), 2)
        self.assertEqual(self.hang_cho(), [(str(self.thumuc / "khong_con.mahoa"), "xong")])   # dòng 'xong' là lịch sử
        self.assertEqual(len(self.hang_cho("filegoc")), 1)                       # QĐ54: tệp gốc Hồ thô không đụng

    def test_luot_don_khi_khoidong_ghi_f04_01_lan(self):
        self.bat()
        with mock.patch("maychu.ketnoi.drive.dang_noi", return_value=True):     # dồn như bản 0.8.2 (giữ tệp chờ)
            self.ngay(17, 18, 19, 20, 21, 22)
        kq = saoluu.don_khi_khoidong(self.thumuc)
        self.assertEqual((kq["tep"] > 0, kq["dong"]), (True, 21))
        self.assertEqual(len([p for p in self.goc.iterdir() if len(p.name) == 10]), 3)
        self.assertEqual(len(self.f04("saoluu", "don_tep_don")), 1)
        self.assertEqual(saoluu.don_khi_khoidong(self.thumuc), {"dong": 0, "tep": 0, "byte": 0})   # chạy lại không đổi gì
        self.assertEqual(len(self.f04("saoluu", "don_tep_don")), 1)
        khoidong = (GOC / "maychu" / "khoidong.py").read_text(encoding="utf-8")
        self.assertLess(khoidong.index('if not antoan.CHE_DO["an_toan"]'), khoidong.index("saoluu.don_khi_khoidong()"))

    def test_bat_lai_day_tiep_ban_con_tren_may(self):
        self.bat(False)
        self.ngay(21)
        self.bat()
        self.ngay(22)
        dong = self.hang_cho()
        self.assertEqual(len(dong), 7)
        self.assertTrue(all(Path(d[0]).exists() for d in dong))               # 0 dòng trỏ tệp mất → 0 FileNotFoundError


# ---------------- Cập nhật, lịch, chuông, tiến độ (QĐ277) ----------------
class KiemCapNhat(Nen):
    def yeu_cau(self):
        with mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "9.9.9", "nang_dulieu": False}), \
                mock.patch.object(antoan, "o_trong", return_value={"du": True}), \
                mock.patch.object(capnhat, "bat_dau", return_value={"ok": True}) as bd, \
                mock.patch.object(capnhat, "dang_cho", return_value=True):
            return capnhat.yeu_cau("hethong", "ngay", self.thumuc), bd.called

    def test_tat_thi_khong_hoi_hop_drive(self):
        kq, goi = self.yeu_cau()
        self.assertEqual((kq, goi), ({"ok": True}, True))

    def test_bat_ma_chua_noi_van_hoi(self):
        self.bat()
        kq, goi = self.yeu_cau()
        self.assertEqual((kq.get("can_chon"), goi), ("drive_chua_noi", False))

    def test_sao_roi_gui_khi_tat_khong_day_va_buoc_3_tat(self):
        with mock.patch.object(saoluu, "chay", return_value={"ketqua": "xong_tren_may", "file": [], "noi": self.goc}), \
                mock.patch.object(capnhat, "_gui") as gui, mock.patch("maychu.ketnoi.drive.day_hang_cho") as day, \
                mock.patch("maychu.ketnoi.drive.dang_noi", return_value=True):
            tiendo.bat_dau("0.8.2", "0.8.3", tiendo._bay(), self.thumuc)
            capnhat._sao_roi_gui("hethong", "0.8.3", self.thumuc)
        self.assertFalse(day.called)
        self.assertFalse(gui.call_args.args[2])                                  # len_drive = False
        self.assertTrue(tiendo.hien(self.thumuc)["drive_tat"])

    def test_lich_va_chuong_xet_cong_tac(self):
        lich = (GOC / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("await asyncio.to_thread(drive.day_hang_cho) if thongso.drive_bat() else {}", lich)
        self.assertIn("await asyncio.to_thread(saoluu.don_truoc_nangcap)", lich)
        tb = (GOC / "maychu/hethong/giamsat/thongbao.py").read_text(encoding="utf-8")
        self.assertIn("tiendo.drive_nen(td, thumuc) if thongso.drive_bat(thumuc) else None", tb)


# ---------------- D1 (QĐ281, QĐ284, QĐ287; PTD-15 mục 6.3) ----------------
class KiemD1(Nen):
    def chuan_bi(self, luc_nang, kiem="dat"):
        for so in (3, 4):
            p = self.goc / f"truoc_nangcap_v{so:02d}"
            p.mkdir(parents=True, exist_ok=True)
            (p / "Dulieu_Chinh.sqlite3").write_bytes(b"x" * 10)
        antoan.ghi(self.thumuc, nang_luocdo={"den": 4, "ban": "0.8.0", "luc": luc_nang.isoformat(timespec="seconds")})
        capnhat._ghi_f04("kiem_saunang", "0.8.0 · 06/06 đạt" if kiem == "dat" else "0.8.0 · 05/06 · lịch", kiem,
                         thumuc=self.thumuc)

    def con(self):
        return sorted(p.name for p in self.goc.iterdir() if p.name.startswith("truoc_nangcap_v"))

    def test_d1_2_ban_cu_hon_xoa_khi_kiem_dat(self):
        bay = datetime(2026, 11, 25, 9, 0, tzinfo=saoluu.MUIGIO_VN)
        self.chuan_bi(datetime(2026, 11, 24, 14, 0, tzinfo=saoluu.MUIGIO_VN))
        ra = saoluu.don_truoc_nangcap(self.thumuc, bay)
        self.assertEqual((self.con(), [x["thumuc"] for x in ra]), (["truoc_nangcap_v04"], ["truoc_nangcap_v03"]))
        self.assertEqual(len(self.f04("saoluu", "xoa_truoc_nangcap")), 1)        # D1-5
        self.assertEqual(saoluu.don_truoc_nangcap(self.thumuc, bay), [])         # chạy lại 0 việc

    def test_d1_1_giu_30_ngay_theo_gio_nang(self):
        nang = datetime(2026, 11, 24, 14, 0, tzinfo=saoluu.MUIGIO_VN)
        self.chuan_bi(nang)
        saoluu.don_truoc_nangcap(self.thumuc, nang + timedelta(days=29, hours=23))
        self.assertEqual(self.con(), ["truoc_nangcap_v04"])
        os.utime(self.goc / "truoc_nangcap_v04", (0, 0))                        # giờ sửa thư mục không được dùng
        saoluu.don_truoc_nangcap(self.thumuc, nang + timedelta(days=30, minutes=1))
        self.assertEqual(self.con(), [])

    def test_d1_2_chua_kiem_dat_thi_giu(self):
        self.chuan_bi(datetime(2026, 11, 24, 14, 0, tzinfo=saoluu.MUIGIO_VN), kiem="loi")
        saoluu.don_truoc_nangcap(self.thumuc, datetime(2026, 11, 25, tzinfo=saoluu.MUIGIO_VN))
        self.assertEqual(self.con(), ["truoc_nangcap_v03", "truoc_nangcap_v04"])

    def test_d1_4_che_do_an_toan_hoac_co_quay_ve_thi_khong_xoa(self):
        self.chuan_bi(datetime(2026, 10, 1, tzinfo=saoluu.MUIGIO_VN))
        antoan.CHE_DO["an_toan"] = True
        self.assertEqual(saoluu.don_truoc_nangcap(self.thumuc), [])
        antoan.CHE_DO["an_toan"] = False
        antoan.ghi(self.thumuc, chay_ban_truoc={"ban_anh": "0.8.2", "ban_truoc": "0.8.1"})
        self.assertEqual(saoluu.don_truoc_nangcap(self.thumuc), [])
        self.assertEqual(self.con(), ["truoc_nangcap_v03", "truoc_nangcap_v04"])

    def test_luat_don_sao_luu_khong_xoa_truoc_nangcap(self):
        self.chuan_bi(datetime(2026, 11, 24, tzinfo=saoluu.MUIGIO_VN))
        self.ngay(18, 19, 20, 21, 22)
        saoluu.don_khi_khoidong(self.thumuc)
        self.assertEqual(self.con(), ["truoc_nangcap_v03", "truoc_nangcap_v04"])

    def test_d1_3_khoa_quay_ve_khi_ban_sao_da_xoa(self):
        ban = capnhat.ban_dang_chay()
        noi = khoitao._thumuc_chup(self.thumuc)
        noi.mkdir(parents=True)
        antoan.ghi(self.thumuc, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": ban, "luc": "2026-10-01T10:00:00+07:00"})
        capnhat._ghi_f04("kiem_saunang", ban + " · 06/06 đạt", "dat", thumuc=self.thumuc)
        with mock.patch.object(antoan, "ban_truoc", return_value="0.8.1"):
            q = antoan.thong_tin_quayve(self.thumuc)
            self.assertEqual((q["co"], q.get("khoa")), (True, None))             # còn bản sao: quay về như cũ (có mất dữ liệu)
            self.assertTrue(q["mat_tu"])
            saoluu.don_truoc_nangcap(self.thumuc, datetime(2026, 11, 2, tzinfo=saoluu.MUIGIO_VN))
            self.assertFalse(noi.exists())
            q = antoan.thong_tin_quayve(self.thumuc)
            ngay = datetime.fromisoformat(self.f04("saoluu", "xoa_truoc_nangcap")[-1][0]).strftime("%d/%m/%Y")
            self.assertEqual((q["co"], q["khoa"]), (True, True))
            self.assertEqual(q["chu"], "Không còn dữ liệu bản sao trước đó (đã xóa ngày " + ngay + ").")   # QĐ296
            self.assertEqual(antoan.quay_ve("hethong", True, self.thumuc), {"loi": q["chu"]})   # máy chủ cũng từ chối
            antoan.ghi(self.thumuc, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": "0.0.1", "luc": "2026-10-01T10:00:00+07:00"})
            q = antoan.thong_tin_quayve(self.thumuc)
            self.assertEqual((q["co"], q.get("khoa"), q["mat_tu"]), (True, None, None))   # bản không nâng lược đồ: như cũ

    def mo_nang_ban_dang_chay(self):
        noi = khoitao._thumuc_chup(self.thumuc)
        noi.mkdir(parents=True)
        for t in ("Dulieu_Chinh", "Nhatky"):
            (noi / f"{t}.sqlite3").write_bytes(b"x")
        antoan.ghi(self.thumuc, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": capnhat.ban_dang_chay(),
                                             "luc": "2026-10-01T10:00:00+07:00"})
        return noi

    def test_y49b_n2_xoa_do_giua_chung_van_khoa(self):
        noi = self.mo_nang_ban_dang_chay()
        that = shutil.rmtree

        def xoa_do(p, *a, **k):   # xoá được 01 tệp rồi hỏng giữa chừng
            next(Path(p).iterdir()).unlink()
            raise OSError("ổ lỗi giữa chừng")
        with mock.patch.object(antoan, "ban_truoc", return_value="0.8.1"):
            with mock.patch.object(saoluu.shutil, "rmtree", side_effect=xoa_do):
                with self.assertRaises(OSError):
                    saoluu.don_truoc_nangcap(self.thumuc, datetime(2026, 11, 2, tzinfo=saoluu.MUIGIO_VN))
            self.assertFalse(noi.exists())                                        # tên cũ đã mất trước khi xoá
            self.assertTrue(noi.with_name(noi.name + saoluu.DUOI_DANG_XOA).exists())
            self.assertEqual(len(self.f04("saoluu", "xoa_truoc_nangcap")), 1)
            q = antoan.thong_tin_quayve(self.thumuc)
            self.assertEqual((q["co"], q["khoa"]), (True, True))                  # khoá, không trả 01 phần tệp
            self.assertEqual(antoan.quay_ve("hethong", True, self.thumuc), {"loi": q["chu"]})
        self.assertIs(saoluu.shutil.rmtree, that)
        saoluu.don_truoc_nangcap(self.thumuc, datetime(2026, 11, 3, tzinfo=saoluu.MUIGIO_VN))   # lượt sau xoá tiếp phần sót
        self.assertEqual([p.name for p in self.goc.iterdir() if p.name.startswith("truoc_nangcap_v")], [])
        self.assertEqual(len(self.f04("saoluu", "xoa_truoc_nangcap")), 1)        # không ghi F04 lần 02

    def test_y49b_n1_thieu_dong_f04_bo_ve_ngay(self):
        noi = self.mo_nang_ban_dang_chay()
        shutil.rmtree(noi)                                                        # mất thư mục mà không có dòng F04
        with mock.patch.object(antoan, "ban_truoc", return_value="0.8.1"):
            q = antoan.thong_tin_quayve(self.thumuc)
        self.assertEqual((q["co"], q["khoa"]), (True, True))
        self.assertEqual(q["chu"], "Không tìm thấy ngày xóa dữ liệu bản sao.")   # QĐ296
        self.assertNotIn("?", q["chu"])


# ---------------- Chữ (QĐ278, QĐ282, QĐ287, QĐ288, QĐ290) ----------------
class KiemChu(unittest.TestCase):
    def chu_giao_dien(self):
        app = (GIAODIEN / "app.js").read_text(encoding="utf-8")
        html = (GIAODIEN / "index.html").read_text(encoding="utf-8")
        bo_chu_thich = "\n".join(re.sub(r"(^|\s)//.*$", "", d) for d in app.splitlines())
        return bo_chu_thich + "\n" + re.sub(r"<!--.*?-->|/\*.*?\*/", "", html, flags=re.S)

    def test_qd288_0_chu_chup_tren_giao_dien(self):
        chu = self.chu_giao_dien().replace("Không chụp ảnh", "")
        self.assertEqual(re.findall(r".{0,30}chụp.{0,30}", chu, flags=re.I), [])
        for v in antoan.CHU.values():
            self.assertNotIn("chụp", v.lower(), v)
        self.assertIn("Không chụp ảnh", self.chu_giao_dien())                    # câu mã dài hạn giữ nguyên

    def test_chu_da_duyet_dung_nguyen_van(self):
        chu = self.chu_giao_dien()
        for x in ("'Sao lưu dữ liệu'", "'Tắt khi đang phát triển. Khi dùng thật, bật và nối Drive.'" if False else "Tắt sao lưu Google Drive?",
                  "Bản sao chỉ nằm trên máy chủ. Máy chủ hỏng thì không lấy lại được.", "Drive chưa nối: bản sao chỉ nằm trên máy chủ.",
                  "Sao lưu Google Drive đang tắt: bản sao chỉ lưu trên máy chủ.", "Bản này có nâng dữ liệu.", "Bản sao Drive: tắt",
                  "tat: 'tắt'", " · Mặc định", " · Bạn đổi"):
            self.assertIn(x, chu)
        self.assertEqual(thongso.GIAI_THICH["saoluu_drive"], "Tắt khi đang phát triển. Khi dùng thật, bật và nối Drive.")
        self.assertEqual(antoan.CHU["sao_loi"], "Chưa tạo được bản sao trước khi cập nhật: {lydo}")
        self.assertEqual(antoan.CHU["qv_het_han"], "Không còn dữ liệu bản sao trước đó (đã xóa ngày {ngay}).")   # QĐ296
        self.assertEqual(antoan.CHU["qv_het_han_khong_ngay"], "Không tìm thấy ngày xóa dữ liệu bản sao.")
        self.assertIn('or "chưa rõ lỗi")', (GOC / "maychu/hethong/capnhat.py").read_text(encoding="utf-8"))

    def test_y49c_bat_chua_noi_co_icon_cloud_alert(self):
        """CPO Y49c (CDO U28 lệch L1): dòng "Drive chưa nối…" có icon cloud-alert cỡ 13, màu #8F5F00 đứng trước (Z21_02)."""
        import shutil as sh
        import subprocess
        if not sh.which("node"):
            self.skipTest("máy không có node")
        app = (GIAODIEN / "app.js").read_text(encoding="utf-8")
        ma = app[app.index("const CHU_Z21 = "):app.index("async function gatCongTac")]
        chay = ("const esc = x => String(x), cum = x => String(x), ngay = x => x;\n"
                "const icoMau = (s, mau, co) => '<i data-ico=\"' + s + '\" data-mau=\"' + mau + '\" data-co=\"' + co + '\"></i>';\n"
                "const ICON = {'cloud-alert': 'cloud-alert'};\n" + ma +
                "const t = g => ({ten: 'saoluu_drive', nhan: 'Sao lưu Google Drive', giatri: g, giai_thich: 'x', hieuluc_tu: '2026-11-24', nguoi_dat: 'a'});\n"
                "console.log(JSON.stringify([veCongTac(t('1'), {drive_noi: false}), veCongTac(t('1'), {drive_noi: true}), veCongTac(t('0'), {drive_noi: false})]));\n")
        ra = json.loads(subprocess.run(["node", "-e", chay], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
        icon = '<i data-ico="cloud-alert" data-mau="#8F5F00" data-co="13"></i><span>Drive chưa nối: bản sao chỉ nằm trên máy chủ.</span>'
        self.assertIn(icon, ra[0])                                                 # bật mà chưa nối: icon đứng trước chữ
        for h in ra[1:]:                                                           # đã nối, hoặc tắt: không có dòng nhắc
            self.assertNotIn("Drive chưa nối", h)
            self.assertNotIn("cloud-alert", h)

    def test_icon_lay_dung_net_ban_ve(self):
        app = (GIAODIEN / "app.js").read_text(encoding="utf-8")
        for net in ("M5.782 5.782A7 7 0 0 0 9 19h8.5a4.5 4.5 0 0 0 1.307-.193", '<rect width="20" height="5" x="2" y="3" rx="1" />',
                    "M7 11V7a5 5 0 0 1 10 0v4"):
            self.assertIn(net, app)
        self.assertNotIn("undefined", (GIAODIEN / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
