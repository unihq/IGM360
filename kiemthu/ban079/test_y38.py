"""Bài kiểm bản 0.7.9 (QĐ213, QĐ215, QĐ216; Y38): 05 lớp an toàn khi cập nhật, N19 (B': tệp chụp tên, gói, dấu băm),
N28 (dán mã dài hạn). Chỉ dùng mã GIẢ, email GIẢ, CLI không có thật; không gọi watchtower, không gọi Drive thật."""
import json
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from maychu import chay
from maychu.dulieu import ketnoi, khoitao, maso, saoluu
from maychu.hethong import antoan, capnhat
from maychu.hethong.giamsat import thongbao
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, madaihan
from kiemthu.ban078.test_y37 import MA_GIA, NenMa

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"
EMAIL_A, EMAIL_B = "nguoigia.a@vidu.invalid", "nguoigia.b@vidu.invalid"


class NenAT(NenMa):
    def setUp(self):
        super().setUp()
        antoan.CHE_DO.update(an_toan=False, den=None, luc=None, lydo=None)
        capnhat._SAO.update(buoc=None, tu=0.0, loi=None, den=None)
        self.addCleanup(antoan.CHE_DO.update, an_toan=False)
        self.dl = self.g / "dulieu"
        self.enterContext(mock.patch("maychu.hethong.caidat.thongso.drive_bat", return_value=True))   # 0.8.3 (QĐ277): bài cũ giả Drive bật

    def f04(self, lenhcon):
        cn = ketnoi.mo("Nhatky")
        try:
            return cn.execute("SELECT thamso_tomtat, ketqua, lydo_chan FROM nhatky_thaotac WHERE lenhcon = ? ORDER BY luc", (lenhcon,)).fetchall()
        finally:
            cn.close()


# ---------------- Lớp 1: ổ trống ----------------
class KiemLop1(NenAT):
    def test_nguong_va_chan(self):
        o = antoan.o_trong()
        self.assertEqual(o["can"], 3 * o["dulieu"] + 2 * 1024 ** 3)
        with mock.patch("maychu.hethong.antoan.shutil.disk_usage", return_value=SimpleNamespace(free=1024 ** 3)), \
                mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.7.10"}), \
                mock.patch.object(capnhat, "bat_dau") as bd:
            kq = capnhat.yeu_cau(maso.tao(), "ngay")
        bd.assert_not_called()
        self.assertTrue(kq["loi"].startswith("Ổ trống còn 1 GB, cần "), kq["loi"])
        self.assertEqual(self.f04("chan_otrong")[0][1], "bichan")

    def test_du_cho_thi_qua(self):
        with mock.patch("maychu.hethong.antoan.shutil.disk_usage", return_value=SimpleNamespace(free=50 * 1024 ** 3)), \
                mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.7.10"}), \
                mock.patch.object(capnhat, "bat_dau", return_value={"ok": True, "sao": True}) as bd:
            kq = capnhat.yeu_cau("x", "ngay")                                       # QĐ218 dòng 30, 31: Drive chưa nối thì hỏi anh
            self.assertEqual(kq, {"loi": antoan.CHU["drive_chua_noi"], "can_chon": "drive_chua_noi"})
            bd.assert_not_called()
            self.assertEqual(capnhat.yeu_cau("x", "ngay", van_capnhat=True), {"ok": True, "sao": True})   # anh bấm "Vẫn cập nhật"
        bd.assert_called_once()

    def test_chu_o_trong(self):
        with mock.patch("maychu.hethong.antoan.shutil.disk_usage", return_value=SimpleNamespace(free=int(12.4 * 1024 ** 3))):
            self.assertEqual(antoan.o_trong()["chu"], "Ổ trống 12,4 GB · đủ để cập nhật")                      # dòng 24


# ---------------- Lớp 5: bản sao trước cập nhật ----------------
class KiemLop5(NenAT):
    def chay(self, drive_noi=False, sao=None):
        import contextlib
        goi = []
        with contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(capnhat, "_chay_nen", side_effect=lambda f: f()))
            st.enter_context(mock.patch.object(capnhat, "cap_nhat_ngay", side_effect=lambda n, t=None: goi.append(n) or {"ok": True}))
            st.enter_context(mock.patch("maychu.ketnoi.drive.dang_noi", return_value=drive_noi))
            st.enter_context(mock.patch("maychu.ketnoi.drive.day_hang_cho", side_effect=self.day_gia))
            st.enter_context(mock.patch.object(capnhat, "NGHI_DAY_GIAY", 0))
            if sao:
                st.enter_context(mock.patch.object(saoluu, "chay", side_effect=sao))
            kq = capnhat.bat_dau("nguoi", "0.7.10")
        return kq, goi

    def day_gia(self, thumuc=None):
        cn = ketnoi.mo("Hotho")
        try:
            cn.execute("UPDATE cho_day_drive SET trangthai = 'xong'")
        finally:
            cn.close()
        return {"day": 1, "loi": 0}

    def test_chup_thu_muc_rieng_roi_gui(self):
        kq, goi = self.chay()
        self.assertEqual((kq, goi), ({"ok": True, "sao": True}, ["nguoi"]))
        noi = [p for p in (self.dl / "saoluu").iterdir() if "_truoc_0.7.10" in p.name]
        self.assertEqual(len(noi), 1)
        self.assertFalse(saoluu.da_co_hom_nay())                      # không làm thay bản hằng ngày
        cn = ketnoi.mo("Nhatky")
        try:
            d = cn.execute("SELECT loai, ketqua_tungbuoc_json FROM saoluu").fetchall()
        finally:
            cn.close()
        self.assertEqual(len(d), 7)
        self.assertTrue(all(x[0] == "truoc_capnhat" and json.loads(x[1])["dip"] == "truoc_capnhat" for x in d))   # QĐ227 (bản 4); CDA C1 giữ "dip"
        self.assertEqual(antoan.doc()["yeu_cau"]["den"], "0.7.10")
        self.assertEqual(capnhat.trang_thai_sao()["dang_sao"], "tai")                # dòng 29: Bước 2/2 · Đang tải bản

    def test_drive_noi_thi_cho_day_xong(self):
        kq, goi = self.chay(drive_noi=True)
        self.assertEqual(goi, ["nguoi"])
        self.assertTrue(antoan.doc()["yeu_cau"]["drive"])
        noi = next(p for p in (self.dl / "saoluu").iterdir() if "_truoc_" in p.name)
        self.assertEqual(capnhat._con_cho_drive(noi), 0)

    def test_qua_10_phut_cho_anh_chon(self):                                         # QĐ218 dòng 28, 32, 34
        import contextlib
        goi = []
        with contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(capnhat, "_chay_nen", side_effect=lambda f: f()))
            st.enter_context(mock.patch.object(capnhat, "cap_nhat_ngay", side_effect=lambda n, t=None: goi.append(n) or {"ok": True}))
            st.enter_context(mock.patch("maychu.ketnoi.drive.dang_noi", return_value=True))
            st.enter_context(mock.patch("maychu.ketnoi.drive.day_hang_cho", return_value={"day": 0, "loi": 1}))
            st.enter_context(mock.patch.object(antoan, "CHO_DRIVE_GIAY", 0))
            capnhat.bat_dau("nguoi", "0.7.10")
            self.assertEqual((capnhat.trang_thai_sao()["dang_sao"], goi), ("qua_gio", []))
            self.assertEqual(capnhat.bat_dau("nguoi", "0.7.10"), {"ok": True, "sao": True})   # không chạy lượt thứ 02
            self.assertEqual(capnhat.tiep_tuc("nguoi", True), {"ok": True})
            self.assertEqual(goi, ["nguoi"])
            self.assertFalse(antoan.doc()["yeu_cau"]["drive"])
            capnhat._SAO.update(buoc="qua_gio")
            self.assertEqual(capnhat.tiep_tuc("nguoi", False), {"ok": True, "huy": True})
            self.assertIsNone(capnhat.trang_thai_sao()["dang_sao"])
            self.assertIn("bạn huỷ", self.f04("capnhat_ngay")[-1][2])
            self.assertIn("loi", capnhat.tiep_tuc("nguoi", True))

    def test_chup_loi_thi_khong_gui(self):
        kq, goi = self.chay(sao=lambda *a, **k: {"ketqua": "loi", "file": [{"ketqua": "loi", "ketqua_tungbuoc_json": json.dumps({"loi": "đĩa đầy"})}], "noi": self.dl})
        self.assertEqual(goi, [])
        self.assertIn("đĩa đầy", capnhat.trang_thai_sao()["sao_loi"])
        self.assertEqual(self.f04("capnhat_ngay")[-1][1], "bichan")

    def test_giu_02_lan_gan_nhat(self):
        for i in range(4):
            p = self.dl / "saoluu" / f"2026-11-2{i}_truoc_0.7.{i}"
            p.mkdir(parents=True)
            os.utime(p, (time.time() - 1000 + i, time.time() - 1000 + i))
        saoluu._don_truoc_capnhat(self.dl / "saoluu", self.dl)
        self.assertEqual(sorted(p.name for p in (self.dl / "saoluu").iterdir() if "_truoc_" in p.name),
                         ["2026-11-22_truoc_0.7.2", "2026-11-23_truoc_0.7.3"])


# ---------------- Lớp 2: chế độ an toàn ----------------
class KiemLop2(NenAT):
    def them_dong(self):
        cn = ketnoi.mo("Nhatky")
        try:
            cn.execute("INSERT INTO nhatky_thaotac (id, luc, congcu, lenhcon, thamso_tomtat, ketqua) VALUES (?, '2026-11-24T00:00:00+07:00', 'thu', 'thu', 'sau_chup', 'dat')", (maso.tao(),))
        finally:
            cn.close()

    def test_lan_nang_bi_ngat_tra_nguyen_trang(self):
        khoitao._chup_het(self.dl, ketnoi.CAC_FILE)
        self.them_dong()
        antoan.ghi(self.dl, dang_nang={"tu": khoitao.PHIENBAN_LUOCDO - 1, "den": khoitao.PHIENBAN_LUOCDO, "luc": "x", "tep": list(ketnoi.CAC_FILE)})
        khoitao.tao_het(self.dl)
        self.assertEqual(self.f04("thu"), [])                         # dòng ghi sau lúc chụp đã trả về như trước
        self.assertNotIn("dang_nang", antoan.doc(self.dl))            # CDA C2: bỏ cờ sau khi trả xong

    def test_nang_loi_tra_nguyen_trang_bo_co(self):
        cn = ketnoi.mo("Bot")
        try:
            cn.execute(f"PRAGMA user_version={khoitao.PHIENBAN_LUOCDO - 1}")
        finally:
            cn.close()
        with mock.patch.object(khoitao, "tao_mot", side_effect=RuntimeError("nâng hỏng")):
            with self.assertRaises(RuntimeError):
                khoitao.tao_het(self.dl)
        tt = antoan.doc(self.dl)
        self.assertNotIn("dang_nang", tt)
        self.assertIn("chup_luc", tt)
        self.assertEqual(khoitao._phienban("Bot", self.dl), khoitao.PHIENBAN_LUOCDO - 1)

    def test_che_do_an_toan_chi_mo_cap_nhat(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        with mock.patch.dict(os.environ, {"IGM360_LICH": "tat"}), \
                mock.patch.object(khoitao, "tao_het", side_effect=RuntimeError("nâng hỏng sk-ant-oat01-" + "Z" * 25)):
            with TestClient(khoidong.app) as c:
                self.assertTrue(c.get("/suckhoe").json()["an_toan"])
                r = c.get("/api/thongso")
                self.assertEqual((r.status_code, r.json()["detail"]), (503, antoan.CHU["an_toan_chan"]))
                self.assertNotEqual(c.get("/api/capnhat").status_code, 503)     # 401 vì chưa đăng nhập, không bị chặn
                self.assertNotEqual(c.post("/api/dangnhap", json={}).status_code, 503)
        self.assertTrue(antoan.chu_an_toan().startswith("Chế độ an toàn: bản "))
        self.assertNotIn("sk-ant-oat01-ZZ", antoan.CHE_DO["lydo"])          # lỗi đã che mã
        self.assertEqual(self.f04("an_toan")[0][1], "loi")


# ---------------- Lớp 4: kiểm sau cập nhật ----------------
class KiemLop4(NenAT):
    def test_06_diem_lich_su_va_chuong(self):
        capnhat.ghi_khoi_dong()
        ban = capnhat.ban_dang_chay()
        with mock.patch.object(antoan, "_kiem_cli", return_value=False):
            kq = antoan.kiem_sau_capnhat(True)
        self.assertEqual((kq["dat"], kq["tong"], kq["loi"]), (5, 6, ["gói AI chưa chạy được"]))   # QĐ219 A12
        self.assertIn("Kiểm sau cập nhật bản " + ban + ": gói AI chưa chạy được",
                      [d["chu"] for d in thongbao.danh_sach()["ds"] if d["loai"] == "capnhat_kiem"])   # QĐ218 dòng 47
        self.assertIn(f"capnhat_kiem:{ban}", [d["khoa"] for d in thongbao.danh_sach()["ds"]] if "khoa" in (thongbao.danh_sach()["ds"] or [{}])[0] else
                      ["capnhat_kiem:" + ban for d in thongbao.danh_sach()["ds"] if d["loai"] == "capnhat_kiem"])
        self.assertFalse(antoan.can_kiem())
        with mock.patch.object(antoan, "_kiem_cli", return_value=True):
            kq = antoan.kiem_sau_capnhat(True)
        self.assertEqual(kq["dat"], 6)
        self.assertNotIn("capnhat_kiem", [d["loai"] for d in thongbao.danh_sach()["ds"]])
        ls = capnhat.lich_su()[0]
        self.assertEqual((ls["ban"], ls["kiem"]), (ban, {"chu": "06/06 đạt", "dat": True}))

    def test_lich_tat_thi_khong_tu_kiem(self):   # bài kiểm tắt lịch: khởi động không chạm CLI của máy kiểm (sự cố Y38b-hỏi)
        from fastapi.testclient import TestClient
        from maychu import khoidong
        with mock.patch.dict(os.environ, {"IGM360_LICH": "tat"}), mock.patch.object(antoan, "kiem_sau_capnhat") as k:
            with TestClient(khoidong.app) as c:
                self.assertEqual(c.get("/suckhoe").status_code, 200)
        k.assert_not_called()

    def test_ban_dich_khac_la_chua_dat(self):
        antoan.ghi(yeu_cau={"tu": "0.7.8", "den": "9.9.9"})
        with mock.patch.object(antoan, "_kiem_cli", return_value=True):
            kq = antoan.kiem_sau_capnhat(False)
        self.assertEqual(kq["loi"], ["chưa lên đúng bản", "lịch chạy nền chưa bật"])   # QĐ219 A9
        cn = ketnoi.mo("Nhatky")
        try:
            tom = cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE lenhcon = 'kiem_saunang'").fetchone()[0]
        finally:
            cn.close()
        self.assertTrue(tom.endswith(" · 04/06 · chưa lên đúng bản, lịch chạy nền chưa bật"), tom)   # QĐ218 dòng 46
        self.assertNotIn("yeu_cau", antoan.doc())


# ---------------- Lớp 3: quay về bản trước ----------------
class KiemLop3(NenAT):
    def goc(self, ban_truoc="0.7.8"):
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.7.9\n", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text(ban_truoc + "\n", encoding="utf-8")
        return g

    def test_lenh_chay_chon_ban(self):
        g = self.goc()
        self.assertEqual(chay.chon(self.dl, g), g)                                 # bình thường
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8"})
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")
        (g / "VERSION").write_text("0.7.10", encoding="utf-8")                      # ảnh mới về: bỏ cờ
        self.assertEqual(chay.chon(self.dl, g), g)
        self.assertNotIn("chay_ban_truoc", antoan.doc(self.dl))

    def test_quay_ve_co_nang_luocdo_phai_dong_y_va_tra_ban_chup(self):
        g = self.goc()
        khoitao._chup_het(self.dl, ketnoi.CAC_FILE)
        KiemLop2.them_dong(self)
        antoan.ghi(self.dl, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": "0.7.9", "luc": "2026-11-24T10:05:00+07:00"})
        with mock.patch.object(antoan, "GOC_MA", g), mock.patch.object(capnhat, "ban_dang_chay", return_value="0.7.9"), \
                mock.patch.object(antoan, "_thoat") as th:
            q = antoan.thong_tin_quayve()
            self.assertEqual((q["co"], q["ban"], q["mat_tu"][:16]), (True, "0.7.8", "2026-11-24T10:05"))
            self.assertIn("dữ liệu trả về lúc 10:05", q["chu"])                     # QĐ218 dòng 40
            self.assertEqual(antoan.quay_ve("nguoi")["loi"], antoan.CHU["qv_can_dong_y"])
            self.assertEqual(antoan.quay_ve("nguoi", True, tre_giay=0.01), {"ok": True, "ban": "0.7.8"})
            time.sleep(0.3)
            th.assert_called_once()
        self.assertNotEqual(self.f04("thu"), [])                                    # Y38c R1: lúc còn chạy KHÔNG trả dữ liệu
        co = antoan.doc(self.dl)["chay_ban_truoc"]
        self.assertEqual((co["ban_truoc"], co["tra_du_lieu"]["thumuc"]), ("0.7.8", f"truoc_nangcap_v{khoitao.PHIENBAN_LUOCDO:02d}"))
        self.assertIn("0.7.9 → 0.7.8", self.f04("quayve")[0][0])
        (g / "VERSION").write_text("0.7.9", encoding="utf-8")
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")                    # lệnh chạy trả dữ liệu trước khi chạy bản trước
        self.assertEqual(self.f04("thu"), [("sau_chup", "dat", None)])   # QĐ237: nhật ký sau giờ chụp được giữ khi quay về
        self.assertNotIn("tra_du_lieu", antoan.doc(self.dl)["chay_ban_truoc"])
        self.assertNotIn("nang_luocdo", antoan.doc(self.dl))
        self.assertIn("đã trả dữ liệu về bản chụp", self.f04("quayve")[-1][0])   # nhật ký ghi lại sau khi trả

    def test_khong_nang_luocdo_giu_du_lieu_khong_co_ban_truoc_thi_khong_co_nut(self):
        g = self.goc()
        with mock.patch.object(antoan, "GOC_MA", g), mock.patch.object(antoan, "_thoat"):
            q = antoan.thong_tin_quayve()
            self.assertEqual((q["mat_tu"], q["chu"]), (None, "Lần cập nhật này không nâng dữ liệu: dữ liệu giữ nguyên."))   # 41
        with mock.patch.object(antoan, "GOC_MA", self.g / "khong_co"):
            self.assertEqual(antoan.quay_ve("nguoi")["loi"], antoan.CHU["qv_khong_co"])

    def test_anh_va_quy_trinh_dong_anh(self):
        df = (GOC / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("ARG ANH_TRUOC=ghcr.io/unihq/igm360:latest", df)
        self.assertIn("COPY --from=anh_truoc /app /tmp/anh_truoc", df)
        self.assertIn('CMD ["python", "-m", "maychu.chay"]', df)
        wf = (GOC / ".github/workflows/dongimage.yml").read_text(encoding="utf-8")
        self.assertIn("Thử bản trước khởi động được", wf)


# ---------------- N19 (QĐ216, B'): tệp chụp tên, gói, dấu băm ----------------
class KiemN19(NenAT):
    def hoso(self, tk, ten="Nguoi Gia", goi="Ultra"):
        p = dg._tep_hoso_claude(tk)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"oauthAccount": {"displayName": ten, "planDisplayName": goi, "emailAddress": "x@vidu.invalid"}}), encoding="utf-8")

    def ket_noi(self, tk, dinh_danh, cu=True):
        tt = [{"loggedIn": cu, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"},
              {"loggedIn": False, "authMethod": ""}]   # Y38h L6: kiểm lại kiểu cũ sau khi đăng xuất
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt), \
                mock.patch.object(dg, "_dinh_danh", side_effect=lambda goi, t: dinh_danh.get(t)), \
                mock.patch.object(dg, "_dang_xuat", return_value=True) as dx, \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {"5gio": {"pct": 7, "datlai": None}}}):
            return madaihan.ket_noi(tk, MA_GIA), dx

    def test_chup_truoc_dang_xuat_doc_tep_go_thi_xoa(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.hoso(1)
        kq, dx = self.ket_noi(1, {1: (EMAIL_A, "org1")})
        self.assertTrue(kq["goi_thu"])
        dx.assert_called_once()
        p = dg.tep_chup(1)
        chu = p.read_text(encoding="utf-8")
        self.assertEqual(set(json.loads(chu)), {"ten_hien", "goi_ten", "email_bam", "tochuc_bam", "chup_luc"})   # N2
        self.assertNotIn("@", chu)
        self.assertNotIn("sk-ant-oat01-", chu)
        if os.name != "nt":
            self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
        p.with_name(".claude.json").unlink()                                       # hồ sơ kiểu cũ đã mất sau đăng xuất
        self.assertEqual({k: v for k, v in dg.ho_so("claude", 1).items() if k in ("ten_hien", "goi_ten")},
                         {"ten_hien": "Nguoi Gia", "goi_ten": "Ultra"})          # N3: đọc tệp
        cn = ketnoi.mo("Viecnen")
        try:
            self.assertEqual(cn.execute("SELECT tyle_5gio FROM nguon_ai WHERE ma = 'goi_claude_01'").fetchone()[0], 7)   # hạn mức lần gọi thử
        finally:
            cn.close()
        k = madaihan.kiem_gan_nhat(1)
        self.assertTrue(k["dat"])
        self.assertIn("tên, gói theo đăng nhập kiểu cũ lúc", k["chu"])
        dg.go("claude", 1)
        self.assertFalse(p.exists())                                               # N5

    def test_trung_email_bi_chan_khac_email_cung_to_chuc_thi_khong(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.hoso(1)
        self.ket_noi(1, {1: (EMAIL_A, "org1")})
        self.hoso(2)
        kq, _ = self.ket_noi(2, {2: (EMAIL_A, "org1")})
        self.assertEqual(kq, {"loi": madaihan.CHU_DAN["trung"].format(tk=1), "trung_voi": 1})
        self.assertIn("Phần mềm không lưu mã", kq["loi"])   # N4: không lưu mã, không ghi tệp
        self.assertIsNone(madaihan.thong_tin(2))
        self.assertFalse(dg.tep_chup(2).exists())
        kq, _ = self.ket_noi(2, {2: (EMAIL_B, "org1")})                            # 02 chỗ ngồi cùng tổ chức
        self.assertTrue(kq["goi_thu"])

    def test_khong_chup_duoc_thi_ghi_chua_kiem(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        kq, dx = self.ket_noi(1, {}, cu=False)
        self.assertFalse(dg.tep_chup(1).exists())                                  # N6
        self.assertTrue(dg.ho_so("claude", 1)["chua_kiem_trung"])
        self.assertIn("chưa chụp được tên, gói", madaihan.kiem_gan_nhat(1)["chu"])

    def test_dang_nhap_kieu_cu_khi_co_ma_thi_chup_roi_dang_xuat(self):
        madaihan.luu(1, MA_GIA)
        c = {"ten_hien": "Nguoi Gia", "goi_ten": "Ultra", "email_bam": "a" * 64, "tochuc_bam": None, "chup_luc": "2026-11-24T09:12:00+07:00"}
        with mock.patch.object(dg, "chup_song", return_value=c), mock.patch.object(dg, "_dang_xuat", return_value=True) as dx:
            kq = dg._ket_thuc("claude", 1)
        self.assertTrue(kq["chup"])
        dx.assert_called_once()                                                    # Đ8 giữ: mã là nơi duy nhất giữ quyền vào
        self.assertEqual(dg.doc_chup(1)["ten_hien"], "Nguoi Gia")
        self.assertEqual(madaihan.lay(1), MA_GIA)                                  # mã cũ giữ nguyên

    def test_dau_bam_khong_do_nguoc_va_on_dinh(self):
        a, b = dg._bam(EMAIL_A), dg._bam(" " + EMAIL_A.upper())
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertNotIn("nguoigia", a)

    def test_khong_goi_cli_that(self):
        self.assertTrue(os.environ["IGM360_CLAUDE_CLI"].startswith(str(self.g)))
        self.assertIsNone(dg._dinh_danh("claude", 1))                              # CLI không có thật: không đọc được, không lỗi


# ---------------- N28: dán mã dài hạn ----------------
class KiemN28(NenAT):
    def test_lam_sach_nhan_va_tu_choi(self):
        cat = MA_GIA[:20] + "\r\n    " + MA_GIA[20:]
        for dung in (MA_GIA, " " + cat + " ", "\t" + MA_GIA + "\n", MA_GIA[:-1] + "​" + MA_GIA[-1],
                     "CLAUDE_CODE_OAUTH_TOKEN=" + MA_GIA, 'export CLAUDE_CODE_OAUTH_TOKEN="' + MA_GIA + '"', "'" + MA_GIA + "'"):
            self.assertTrue(madaihan.hop_le(dung), repr(dung))
            self.assertEqual(madaihan.lam_sach(dung), MA_GIA)
        for sai in ("sk-ant-api03-" + "Q" * 40, MA_GIA[:22] + "│" + MA_GIA[22:], MA_GIA[:20], "", "abc"):
            self.assertFalse(madaihan.hop_le(sai), repr(sai))

    def test_cau_loi_ghi_so_ky_tu_khong_hien_ma(self):
        c = madaihan.chu_loi_dan(MA_GIA[:25])
        self.assertEqual(c, madaihan.CHU_DAN["chua_tron"].format(n=25))
        self.assertNotIn(MA_GIA[13:25], c)
        self.assertEqual(madaihan.chu_loi_dan("sk-ant-api03-xyz"), madaihan.CHU_DAN["khoa_api"])   # Y38d N30
        self.assertEqual(c, "Mã vừa dán có 25 ký tự, chưa trọn. Chép lại cả mã rồi dán lại")

    def test_o_buoc_2_gap_ma_dai_han_thi_luu_nhu_dan(self):
        from maychu.web import api
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        madaihan._PHIEN[1] = {"bat_luc": time.time(), "ma": "", "loi": "", "fd": -1, "tho": "", "proc": mock.Mock()}
        with mock.patch.object(madaihan.os, "write") as gho:
            r = madaihan.gui_ma(1, MA_GIA[:30] + "\n " + MA_GIA[30:])
        gho.assert_not_called()                                                    # không gõ mã dài hạn vào setup-token
        self.assertEqual(r, {"ma": MA_GIA, "dan_nham": True})
        self.assertNotIn(1, madaihan._PHIEN)
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=[{"loggedIn": False, "authMethod": ""}] * 2), \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {}}):
            api.md_gui_ma(api.MaGoi(taikhoan=1, ma=" " + MA_GIA + " "), {"nguoidung_id": maso.tao()})
        self.assertEqual(madaihan.lay(1), MA_GIA)

    def test_api_dan_bo_khoang_trang_va_bao_loi_ro(self):
        from maychu.web import api
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        with self.assertRaises(HTTPException) as e:
            api.md_dan(api.MaGoi(taikhoan=1, ma=MA_GIA[:25]), {"nguoidung_id": "x"})
        self.assertIn("25 ký tự", str(e.exception.detail))
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=[{"loggedIn": False, "authMethod": ""}] * 2), \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {}}):
            api.md_dan(api.MaGoi(taikhoan=1, ma="CLAUDE_CODE_OAUTH_TOKEN=" + MA_GIA[:40] + "\n" + MA_GIA[40:]), {"nguoidung_id": maso.tao()})
        self.assertEqual(madaihan.lay(1), MA_GIA)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_giao_dien_lam_sach_va_chuyen_duong(self):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8")
        doan = js[js.index("function lamSachMa("):js.index("function theMd(")]
        ma = (doan + "\nconst M = " + json.dumps(MA_GIA) + ";\nconsole.log(JSON.stringify(["
              "lamSachMa(' ' + M.slice(0, 20) + '\\n   ' + M.slice(20)) === M, lamSachMa('CLAUDE_CODE_OAUTH_TOKEN=\"' + M + '\"') === M,"
              "lamSachMa(M.slice(0, 9) + '\\u200b' + M.slice(9)) === M, lamSachMa('abc') === 'abc']));")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "lamsach.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [True, True, True, True])
        nut = js[js.index("else if (d.mdGui)"):js.index("else if (d.mdLuu)")]
        self.assertIn("lamSachMa(ma).startsWith('sk-ant-oat01-')", nut)           # N28 (b) ở giao diện
        self.assertIn("'/mohinh/goi/claude/madaihan/dan'", nut)


# ---------------- Y38c: sửa lỗi CDA và lượt rà độc lập của CPO ----------------
class KiemY38c(NenAT):
    def goc(self):
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.7.9\n", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text("0.7.8\n", encoding="utf-8")
        return g

    def test_r1_ban_chup_hong_thi_khong_thay_tep_nao(self):
        g = self.goc()
        khoitao._chup_het(self.dl, ketnoi.CAC_FILE)
        noi = khoitao._thumuc_chup(self.dl)
        (noi / "Viecnen.sqlite3").write_bytes(b"khong phai sqlite")              # 01 tệp chụp hỏng
        KiemLop2.them_dong(self)
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8",
                                            "tra_du_lieu": {"thumuc": noi.name, "tep": list(ketnoi.CAC_FILE)}})
        self.assertEqual(chay.chon(self.dl, g), g)                                 # không trả, chạy bản mới
        self.assertNotEqual(self.f04("thu"), [])                                   # Nhatky không bị thay (trả đủ hoặc không)
        tt = antoan.doc(self.dl)
        self.assertNotIn("chay_ban_truoc", tt)
        self.assertIn("không trả được dữ liệu", tt["quayve_loi"]["chu"])
        self.assertEqual([p.name for p in self.dl.iterdir() if p.name.endswith(".trave.tam")], [])
        antoan.bao_quay_ve_loi(self.dl)
        self.assertEqual(self.f04("quayve")[-1][1], "loi")
        self.assertNotIn("quayve_loi", antoan.doc(self.dl))

    def test_r1_nhat_ky_loi_thi_khong_ghi_co_khong_dung(self):
        g = self.goc()
        with mock.patch.object(antoan, "GOC_MA", g), mock.patch.object(capnhat, "ban_dang_chay", return_value="0.7.9"), \
                mock.patch.object(capnhat, "_ghi_f04", side_effect=sqlite3.OperationalError("khoá")), \
                mock.patch.object(antoan, "_thoat") as th:
            kq = antoan.quay_ve("nguoi", tre_giay=0.01)
            time.sleep(0.2)
        self.assertIn("loi", kq)
        th.assert_not_called()
        self.assertNotIn("chay_ban_truoc", antoan.doc(self.dl))

    def test_r3_ban_truoc_hong_03_lan_thi_ve_ban_moi(self):
        import signal
        g = self.goc()
        for s in (signal.SIGTERM, signal.SIGINT):
            self.addCleanup(signal.signal, s, signal.getsignal(s))
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8"})
        tep = self.dl / antoan.TEN_TEP
        with mock.patch.object(chay, "LENH", ["-c", "import sys; sys.exit(3)"]):
            for _ in range(3):
                self.assertEqual(chay.canh_ban_truoc(g / "ban_truoc", tep, cho_len=5, hoi=lambda: False), 3)
        self.assertEqual(antoan.doc(self.dl)["chay_ban_truoc"]["so_lan_hong"], 3)
        self.assertEqual(chay.chon(self.dl, g), g)
        self.assertIn("khởi động hỏng 03 lần", antoan.doc(self.dl)["quayve_loi"]["chu"])
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8", "so_lan_hong": 2})
        with mock.patch.object(chay, "LENH", ["-c", "import time; time.sleep(0.5)"]):
            chay.canh_ban_truoc(g / "ban_truoc", tep, cho_len=5, hoi=lambda: True)   # lên được → xoá số đếm
        self.assertEqual(antoan.doc(self.dl)["chay_ban_truoc"]["so_lan_hong"], 0)

    def test_g5_co_la_thi_vao_che_do_an_toan(self):
        antoan.ghi(self.dl, dang_nang={"tu": 2, "den": 99, "luc": "x", "tep": ["Bot"]})
        with self.assertRaises(RuntimeError):
            khoitao.tao_het(self.dl)
        self.assertIn("dang_nang", antoan.doc(self.dl))                            # giữ cờ để soát

    def test_r2_moi_lan_01_thu_muc_rieng(self):
        from datetime import datetime as dt
        a = saoluu.chay(bay_gio=dt(2026, 11, 24, 10, 0, 0, tzinfo=saoluu.MUIGIO_VN), truoc_ban="0.7.10")
        b = saoluu.chay(bay_gio=dt(2026, 11, 24, 10, 15, 0, tzinfo=saoluu.MUIGIO_VN), truoc_ban="0.7.10")
        self.assertNotEqual(a["noi"], b["noi"])
        self.assertEqual((capnhat._con_cho_drive(a["noi"]), capnhat._con_cho_drive(b["noi"])), (7, 7))   # không lẫn nhau
        cn = ketnoi.mo("Hotho")
        try:
            dup = cn.execute("SELECT count(*) FROM (SELECT duongdan_tam FROM cho_day_drive GROUP BY duongdan_tam HAVING count(*) > 1)").fetchone()[0]
        finally:
            cn.close()
        self.assertEqual(dup, 0)                                                   # 01 tệp đúng 01 dòng M01

    def test_r4_chup_truoc_roi_cho_viec_ai(self):
        goi, so = [], iter([1, 1, 0])
        with mock.patch.object(capnhat, "_chay_nen", side_effect=lambda f: f()), \
                mock.patch.object(capnhat, "cap_nhat_ngay", side_effect=lambda n, t=None: goi.append(capnhat.dang_cho()) or {"ok": True}), \
                mock.patch("maychu.ketnoi.drive.dang_noi", return_value=False), \
                mock.patch.object(capnhat, "so_viec_ai_dangchay", side_effect=lambda t=None: next(so)), \
                mock.patch.object(capnhat, "NGHI_DAY_GIAY", 0):
            capnhat.bat_dau("nguoi", "0.7.10", cho_viec=True)
        self.assertEqual(goi, [True])                                              # gửi lệnh sau khi việc AI xong; lúc đó vẫn chặn việc mới
        self.assertTrue(any(p.name.startswith(time.strftime("%Y-")) and "_truoc_" in p.name for p in (self.dl / "saoluu").iterdir()))

    def test_r6_lich_do_that(self):
        with mock.patch.object(antoan, "CHO_KIEM_LICH_GIAY", 0), mock.patch.object(antoan, "_kiem_cli", return_value=True):
            kq = antoan.kiem_sau_khi_chay(SimpleNamespace(done=lambda: True))
        self.assertFalse(kq["diem"]["lich"])
        self.assertIn("lịch chạy nền chưa bật", kq["loi"])

    def test_r7_ghi_dong_thoi_khong_mat_muc(self):
        import threading
        ts = [threading.Thread(target=antoan.ghi, kwargs={f"muc{i}": i}) for i in range(20)]
        [x.start() for x in ts]
        [x.join() for x in ts]
        d = antoan.doc(self.dl)
        self.assertEqual(sorted(k for k in d if k.startswith("muc")), sorted(f"muc{i}" for i in range(20)))
        self.assertEqual([p.name for p in self.dl.iterdir() if p.name.endswith(".tam")], [])

    def test_r8_gio_che_do_an_toan_lay_luc_chup(self):
        antoan.ghi(self.dl, chup_luc="2026-11-24T10:05:00+07:00")
        antoan.vao_an_toan(RuntimeError("x"), self.dl)
        self.assertEqual(antoan.CHE_DO["luc"], "2026-11-24T10:05:00+07:00")

    def test_r9_chu_dung_truoc_ma(self):
        for s in ("Token: " + MA_GIA, "Your OAuth token: " + MA_GIA[:30] + "\n" + MA_GIA[30:]):
            self.assertEqual(madaihan.lam_sach(s), MA_GIA)
        madaihan._PHIEN[1] = {"bat_luc": time.time(), "ma": "", "loi": "", "fd": -1, "tho": "", "proc": mock.Mock()}
        with mock.patch.object(madaihan.os, "write") as gho:
            self.assertEqual(madaihan.gui_ma(1, "Token: " + MA_GIA), {"ma": MA_GIA, "dan_nham": True})
        gho.assert_not_called()

    def test_r10_lay_ten_goi_thay_trung_thi_giu_ma(self):   # Y38e: QĐ219 A8 thay cách gỡ mã của R10
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        madaihan.luu(2, MA_GIA)
        dung = {"ten_hien": "Nguoi Dung", "goi_ten": "Pro", "email_bam": "a" * 64, "tochuc_bam": None, "chup_luc": "y"}
        dg.ghi_chup(2, dung)                                                       # tên, gói đúng đã chụp trước
        c = {"ten_hien": "B", "goi_ten": "Max", "email_bam": "b" * 64, "tochuc_bam": None, "chup_luc": "x"}
        with mock.patch.object(dg, "chup_song", return_value=c), mock.patch.object(dg, "tim_trung", return_value=1), \
                mock.patch.object(dg, "_dang_xuat", return_value=True) as dx:
            kq = dg._ket_thuc("claude", 2)
        self.assertFalse(dg.GO_MA_KHI_TRUNG)
        self.assertEqual(kq["loi"], "Bạn vừa đăng nhập tài khoản đã kết nối ở Tài khoản 1. Bấm Lấy tên, gói, đăng nhập đúng"
                                    " tài khoản của mã này.")                                                    # A8
        self.assertEqual(madaihan.lay(2), MA_GIA)                                   # mã dài hạn còn trong Két khoá
        self.assertEqual(dg.doc_chup(2)["ten_hien"], "Nguoi Dung")                  # không ghi tên, gói sai
        dx.assert_called_once()                                                     # đăng xuất kiểu cũ của tài khoản nhầm

    def ket_noi(self, tk, cu, goi_ok=True):
        tt = [{"loggedIn": cu, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"},
              {"loggedIn": False, "authMethod": ""}]   # Y38h L6: kiểm lại kiểu cũ sau khi đăng xuất
        goi = mock.Mock(return_value={"hanmuc": {}}) if goi_ok else mock.Mock(side_effect=congai.LoiAI("Claude", "lỗi", "x"))
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt), \
                mock.patch.object(dg, "_dinh_danh", side_effect=lambda goi, t, *a, **k: (EMAIL_A, "org1") if t == tk else None), \
                mock.patch.object(dg, "ho_so", return_value={"ten_hien": "Nguoi Gia", "goi_ten": "Ultra", "mota_goi": None}), \
                mock.patch.object(dg, "_dang_xuat", return_value=True), mock.patch.object(congai, "_goi_claude", goi):
            return madaihan.ket_noi(tk, MA_GIA)

    def test_g1_goi_thu_chua_duoc_van_ghi_tep_chup(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        kq = self.ket_noi(1, cu=True, goi_ok=False)
        self.assertFalse(kq["goi_thu"])
        self.assertTrue(dg.tep_chup(1).exists())

    def test_r11_khong_chup_duoc_thi_bo_tep_cu(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.ket_noi(1, cu=True)
        self.assertTrue(dg.tep_chup(1).exists())
        self.ket_noi(1, cu=False)                                                  # mã mới, không còn đăng nhập kiểu cũ
        self.assertFalse(dg.tep_chup(1).exists())


# ---------------- Y38d: lỗi CDO U13 (N29–N37) và chỗ hở V2 của CDA ----------------
MA_MOI = "sk-ant-oat01-" + "R" * 30 + "moiN29"


class KiemY38d(NenAT):
    def ket_noi(self, tk, ma, goi_ok=True, loi=None):
        tt = [{"loggedIn": False, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"},
              {"loggedIn": False, "authMethod": ""}]   # Y38h L6: kiểm lại kiểu cũ sau khi đăng xuất
        goi = mock.Mock(return_value={"hanmuc": {}}) if goi_ok else mock.Mock(side_effect=loi or congai.LoiAI("Claude", "lỗi", "x"))
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt), mock.patch.object(congai, "_goi_claude", goi):
            return madaihan.ket_noi(tk, ma)

    def test_n29_ma_moi_chua_goi_duoc_thi_giu_ma_cu(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        madaihan.luu(1, MA_GIA)
        self.han(days=200)
        han_cu = madaihan.thong_tin(1)["han"]
        kq = self.ket_noi(1, MA_MOI, goi_ok=False)
        self.assertEqual((kq["goi_thu"], kq.get("giu_ma_cu")), (False, True))
        self.assertEqual(madaihan.lay(1), MA_GIA)                                   # mã cũ còn nguyên
        self.assertEqual(madaihan.thong_tin(1)["han"], han_cu)                      # hạn cũ giữ
        self.assertTrue(madaihan.kiem_gan_nhat(1)["giu_ma_cu"])
        kq = self.ket_noi(1, MA_MOI)                                               # gọi thử đạt thì thay
        self.assertEqual((kq["goi_thu"], madaihan.lay(1)), (True, MA_MOI))

    def test_n29_chua_co_ma_hoac_ma_cu_het_han_thi_luu_ma_moi(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.ket_noi(1, MA_GIA, goi_ok=False)
        self.assertEqual(madaihan.lay(1), MA_GIA)                                   # chưa có mã cũ: giữ như trước
        self.han(minutes=-1)
        self.ket_noi(1, MA_MOI, goi_ok=False)
        self.assertEqual(madaihan.lay(1), MA_MOI)                                   # mã cũ hết hạn: không giữ

    def test_n37_het_han_muc_ghi_ro(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.ket_noi(1, MA_GIA, goi_ok=False, loi=congai.HetHanMuc("hết hạn mức"))
        k = madaihan.kiem_gan_nhat(1)
        self.assertEqual((k["dat"], k["het_hanmuc"]), (False, True))

    def test_n30_khoa_api_va_sai_tien_to(self):
        self.assertEqual(madaihan.chu_loi_dan("sk-ant-api03-" + "x" * 85), madaihan.CHU_DAN["khoa_api"])
        self.assertEqual(madaihan.chu_loi_dan("abc-xyz-123"), madaihan.CHU_DAN["sai_tien_to"])
        self.assertEqual(madaihan.chu_loi_dan(MA_GIA[:25]), madaihan.CHU_DAN["chua_tron"].format(n=25))
        js = (GD / "app.js").read_text(encoding="utf-8")
        nut = js[js.index("else if (d.mdLuu)"):js.index("else if (d.mdHuy)")]
        self.assertIn("ma.startsWith('sk-ant-api') ? CHU_Z15.khoaApi", nut)
        self.assertIn(": CHU_Z15.saiTienTo", nut)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_n31_n33_giao_dien(self):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8")
        doan = js[js.index("function veQuayVe(d) {"):js.index("function moQuayVe() {")]
        dong = next(x for x in js.splitlines() if "S.cn = d.an_toan ? 'antoan'" in x)
        ma = ("const S = {cn: 'moinhat'}; const nbsp = s => s; const ICON = new Proxy({}, {get: () => '<svg/>'});"
              "const CHU_CN = {quayve: 'Quay về bản trước', qvRe: b => 'Chạy lại bản ' + b};"
              "const nut = [{dataset: {}}, {dataset: {}}]; const $$ = q => nut;\n" + doan
              + "\nlet d = {an_toan: 'x', co_ban_moi: true};\n" + dong
              + "\nconst a = S.cn; S.cn = 'dangcn'; veQuayVe({quay_ve: {co: true, ban: '0.7.8'}}); const b = nut.every(x => x.disabled);"
              + "\nS.cn = 'moinhat'; veQuayVe({quay_ve: {co: true, ban: '0.7.8'}, dang_sao: 'day'}); const c = nut.every(x => x.disabled);"
              + "\nveQuayVe({quay_ve: {co: true, ban: '0.7.8'}}); const e = nut.every(x => !x.disabled);"
              + "\nconsole.log(JSON.stringify([a, b, c, e]));")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "n31.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["antoan", True, True, True])        # N31: an toàn ẩn thẻ mới nhất; N33 khoá
        self.assertNotIn('id="cn-quayve"', (GD / "index.html").read_text(encoding="utf-8"))   # N36 (a): không còn thẻ riêng

    def chuan_bi_tra(self):
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.7.9", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text("0.7.8", encoding="utf-8")
        khoitao._chup_het(self.dl, ketnoi.CAC_FILE)
        KiemLop2.them_dong(self)
        noi = khoitao._thumuc_chup(self.dl)
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8", "nguoi": "nguoi_thu",
                                            "tra_du_lieu": {"thumuc": noi.name, "tep": list(ketnoi.CAC_FILE)}})
        return g

    def bam(self):
        import hashlib
        return {t: hashlib.sha256(ketnoi.duongdan(t, self.dl).read_bytes()).hexdigest() for t in ketnoi.CAC_FILE}

    def test_v2_loi_o_tep_thu_04_thi_doi_ve_du_07_tep(self):
        g = self.chuan_bi_tra()
        truoc = self.bam()
        goc_replace, dem = os.replace, {"n": 0}

        def replace_hong(a, b):
            if str(a).endswith(".trave.tam"):
                dem["n"] += 1
                if dem["n"] == 4:
                    raise OSError("giả lập lỗi ở tệp thứ 04")
            return goc_replace(a, b)
        with mock.patch.object(chay.os, "replace", side_effect=replace_hong):
            self.assertEqual(chay.chon(self.dl, g), g)                             # không chạy bản trước
        self.assertEqual(self.bam(), truoc)                                         # 07 tệp như trước lúc trả
        self.assertNotEqual(self.f04("thu"), [])
        self.assertEqual([p.name for p in self.dl.iterdir() if p.name.endswith((".cu", ".tam"))], [])
        tt = antoan.doc(self.dl)
        self.assertNotIn("chay_ban_truoc", tt)
        self.assertIn("không trả được dữ liệu", tt["quayve_loi"]["chu"])

    def test_v2_mat_dien_giua_luc_thay_thi_doi_ve_roi_tra_lai(self):
        g = self.chuan_bi_tra()
        for t in ("Dulieu_Chinh", "Hotho", "Ketnoi"):                               # lần trước đã đổi 03 tệp sang .cu rồi dừng
            os.replace(ketnoi.duongdan(t, self.dl), str(ketnoi.duongdan(t, self.dl)) + ".cu")
            shutil.copy(khoitao._thumuc_chup(self.dl) / f"{t}.sqlite3", ketnoi.duongdan(t, self.dl))
        tt = antoan.doc(self.dl)
        tt["chay_ban_truoc"]["tra_du_lieu"]["buoc"] = "thay"
        antoan.ghi(self.dl, chay_ban_truoc=tt["chay_ban_truoc"])
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")                   # đổi .cu về, trả lại từ đầu, đạt
        self.assertEqual(self.f04("thu"), [("sau_chup", "dat", None)])   # QĐ237: nhật ký giữ, không ghi đôi khi trả lại từ đầu
        self.assertEqual([p.name for p in self.dl.iterdir() if p.name.endswith(".cu")], [])
        dong = self.f04("quayve")[-1]
        self.assertIn("đã trả dữ liệu về bản chụp", dong[0])
        cn = ketnoi.mo("Nhatky")
        try:
            self.assertEqual(cn.execute("SELECT nguoi_id FROM nhatky_thaotac WHERE lenhcon = 'quayve' ORDER BY luc DESC LIMIT 1").fetchone()[0],
                             "nguoi_thu")                                           # V2 nhỏ: có người bấm
        finally:
            cn.close()


class KiemY38dBoSung(NenAT):
    def test_n39_lich_su_moi_ban_01_dong(self):
        for ban in ("0.7.9", "0.7.8", "0.7.9"):                                     # lên 0.7.9, quay về 0.7.8, lên lại 0.7.9
            capnhat._ghi_f04("khoidong", ban, "dat")
            time.sleep(1.1)
        self.assertEqual([x["ban"] for x in capnhat.lich_su()], ["0.7.9", "0.7.8"])

    def lay_ten_trung(self, go_ma):
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        madaihan.luu(2, MA_GIA)
        c = {"ten_hien": "B", "goi_ten": "Max", "email_bam": "b" * 64, "tochuc_bam": None, "chup_luc": "x"}
        with mock.patch.object(dg, "GO_MA_KHI_TRUNG", go_ma), mock.patch.object(dg, "chup_song", return_value=c), \
                mock.patch.object(dg, "tim_trung", return_value=1), mock.patch.object(dg, "_dang_xuat", return_value=True):
            return dg._ket_thuc("claude", 2)

    def test_n40_02_cach(self):
        kq = self.lay_ten_trung(True)                                              # cách hiện tại: gỡ mã
        self.assertEqual((kq["loi"], kq["chu_rieng"]), (madaihan.CHU_DAN["trung"].format(tk=1), True))
        self.assertIsNone(madaihan.thong_tin(2))

    def test_n40_cach_cdo_giu_ma(self):
        kq = self.lay_ten_trung(False)                                             # cách CDO: giữ mã, báo đăng nhập lại
        self.assertEqual(kq["loi"], madaihan.CHU_DAN["trung_dang_nhap_lai"].format(tk=1))
        self.assertEqual(madaihan.lay(2), MA_GIA)
        self.assertFalse(dg.tep_chup(2).exists())

    def test_n41_api_chuyen_cau_rieng(self):
        from maychu.web import api
        e = api._loi_dn("claude", 2, {"loi": "Câu 22", "trung_voi": 1, "chu_rieng": True}, {"nguoidung_id": maso.tao()})
        self.assertEqual((e.status_code, e.detail["chu_rieng"], e.detail["loi"]), (409, True, "Câu 22"))
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("(D.trungChu || {})[g] ? giuTienTo(cum(cau(D.trungChu[g])))", js)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_n42_tien_to_khong_ngat(self):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8")
        dong = next(x for x in js.splitlines() if x.startswith("const giuTienTo"))
        ma = dong + "\nconsole.log(giuTienTo('Mã dài hạn bắt đầu bằng sk-ant-oat01-. Chép lại'));"
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "n42.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertIn('<span class="nw">sk-ant-oat01-</span>', r.stdout)

    def test_quay_ve_hong_chuong_va_lich_su(self):
        antoan.ghi(self.dl, quayve_loi={"chu": "không trả được dữ liệu: OSError", "luc": "x", "kieu": "tra",
                                        "ban_truoc": "0.7.8", "ban_anh": "0.7.9"})
        antoan.bao_quay_ve_loi(self.dl)
        q = antoan.quay_ve_loi_gan()
        self.assertEqual(q["chu_hien"], "Quay về bản 0.7.8 chưa được: chưa trả được dữ liệu. Vẫn chạy bản 0.7.9, dữ liệu giữ nguyên.")
        thongbao.quet_quayve_loi()
        tin = [d for d in thongbao.danh_sach()["ds"] if d["loai"] == "quayve_loi"]
        self.assertEqual((len(tin), tin[0]["icon"], tin[0]["muc"], tin[0]["chu"]),
                         (1, "rotate-ccw", "do", "Quay về bản 0.7.8 chưa được: chưa trả được dữ liệu"))   # A4
        from maychu.web import api
        with mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": False, "ban_moi": None}):
            self.assertEqual(api._them_antoan()["quayve_loi"]["chu_hien"], q["chu_hien"])


# ---------------- Y38e: 15 câu QĐ219, giữ mã khi đăng nhập nhầm, xưng "bạn" QĐ220 ----------------
class KiemY38e(NenAT):
    A = {1: "Đây là khoá API, không phải mã dài hạn. Khoá API thêm ở thẻ Khoá API.",
         2: "Đây không phải mã dài hạn (mã bắt đầu bằng sk-ant-oat01-).",
         3: "Đang quay về bản 0.7.8",
         4: "Quay về bản 0.7.8 chưa được: chưa trả được dữ liệu",
         5: "Quay về bản 0.7.8 chưa được: bản này lỗi khởi động 03 lần",
         6: "Quay về bản 0.7.8 chưa được: chưa trả được dữ liệu. Vẫn chạy bản 0.7.9, dữ liệu giữ nguyên.",
         7: "Quay về bản 0.7.8 chưa được: bản này lỗi khởi động 03 lần. Đã chạy lại bản 0.7.9.",
         8: "Bạn vừa đăng nhập tài khoản đã kết nối ở Tài khoản 1. Bấm Lấy tên, gói, đăng nhập đúng tài khoản của mã này.",
         14: "Trình duyệt chặn chép. Bạn bôi đen lệnh rồi chép tay.",
         15: "Mã đã lưu; lần gọi thử gặp hết hạn mức của gói nên chưa kiểm được mã."}

    def test_15_cau_dung_nguyen_van(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        A = self.A
        self.assertEqual((madaihan.CHU_DAN["khoa_api"], madaihan.CHU_DAN["sai_tien_to"]), (A[1], A[2]))
        self.assertEqual(madaihan.chu_loi_dan("sk-ant-api03-" + "x" * 85), A[1])
        self.assertEqual(madaihan.chu_loi_dan("abc-xyz-123"), A[2])
        for k, c in (("khoaApi", A[1]), ("saiTienTo", A[2]), ("chepLoi", A[14]), ("kiemHanMucRe", A[15])):
            self.assertIn(f"  {k}: '{c}'", js)
        self.assertIn("qvDang: 'Đang quay về bản ',", js)
        self.assertIn("tieuDangCn(CHU_CN.qvDang + q.ban)", js)                     # A3 = "Đang quay về bản " + bản trước
        d = {"luc": "x", "ban_truoc": "0.7.8", "ban_anh": "0.7.9"}
        self.assertEqual(antoan.chu_quay_ve_loi({**d, "kieu": "tra"}, "0.7.9"), A[6])
        self.assertEqual(antoan.chu_quay_ve_loi({**d, "kieu": "khoidong", "so_lan": 3}, "0.7.9"), A[7])
        self.assertEqual(antoan.cau_chuong(A[6]), A[4])
        self.assertEqual(antoan.cau_chuong(A[7]), A[5])
        self.assertEqual(madaihan.CHU_DAN["trung_dang_nhap_lai"].format(tk=1), A[8])
        self.assertEqual([antoan.TEN_DIEM[k] for k in ("ban", "dulieu", "luocdo", "cli", "o_trong")],
                         ["chưa lên đúng bản", "tệp dữ liệu hỏng", "cấu trúc dữ liệu lệch", "gói AI chưa chạy được",
                          "chưa đủ ổ trống"])                                       # A9–A13
        self.assertEqual(antoan.TEN_DIEM["lich"], "lịch chạy nền chưa bật")         # QĐ218 dòng 47 giữ

    def test_a4_a6_tra_du_lieu_hong(self):
        g = KiemY38d.chuan_bi_tra(self)
        noi = khoitao._thumuc_chup(self.dl)
        (noi / "Viecnen.sqlite3").write_bytes(b"khong phai sqlite")
        self.assertEqual(chay.chon(self.dl, g), g)
        antoan.bao_quay_ve_loi(self.dl)
        self.assertEqual(self.f04("quayve")[-1][:2], (self.A[6], "loi"))           # màn Cập nhật: A6
        self.assertEqual(antoan.quay_ve_loi_gan()["chu_chuong"], self.A[4])
        thongbao.quet_quayve_loi()
        tin = [d for d in thongbao.danh_sach()["ds"] if d["loai"] == "quayve_loi"]
        self.assertEqual(tin[0]["chu"], self.A[4])                                  # chuông: A4

    def test_a5_a7_hong_03_lan_sau_khi_da_tra(self):
        from datetime import datetime
        luc = datetime.now(saoluu.MUIGIO_VN).replace(hour=10, minute=5, second=0).isoformat(timespec="seconds")
        g = KiemY38d.chuan_bi_tra(self)
        antoan.ghi(self.dl, nang_luocdo={"ban": "0.7.9", "luc": luc})
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")                   # trả dữ liệu đạt, chạy bản trước
        tt = antoan.doc(self.dl)
        self.assertEqual(tt["chay_ban_truoc"]["da_tra"], luc)
        tt["chay_ban_truoc"]["so_lan_hong"] = 3                                     # bản trước hỏng 03 lần
        antoan.ghi(self.dl, chay_ban_truoc=tt["chay_ban_truoc"])
        self.assertEqual(chay.chon(self.dl, g), g)
        antoan.bao_quay_ve_loi(self.dl)
        self.assertEqual(self.f04("quayve")[-1][:2], (self.A[7] + " Dữ liệu đã trả về lúc 10:05.", "loi"))   # A7 có thêm
        self.assertEqual(antoan.quay_ve_loi_gan()["chu_chuong"], self.A[5])         # chuông: A5

    def test_a7_chua_tra_du_lieu(self):
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.7.9", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text("0.7.8", encoding="utf-8")
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.7.9", "ban_truoc": "0.7.8", "so_lan_hong": 3})
        self.assertEqual(chay.chon(self.dl, g), g)
        antoan.bao_quay_ve_loi(self.dl)
        self.assertEqual(self.f04("quayve")[-1][0], self.A[7])

    def test_n40_mac_dinh_giu_ma_va_giao_dien(self):
        self.assertFalse(dg.GO_MA_KHI_TRUNG)
        kq = KiemY38dBoSung.lay_ten_trung(self, dg.GO_MA_KHI_TRUNG)
        self.assertEqual((kq["loi"], kq["chu_rieng"]), (self.A[8], True))
        self.assertEqual(madaihan.lay(2), MA_GIA)
        self.assertFalse(dg.tep_chup(2).exists())


class KiemY38f(NenAT):
    """CDO U14: L1, L2 giữ liền cụm; L3 ô A8 kiểu báo lỗi kèm nút "Lấy tên, gói" (bản vẽ Z17_01, Z17_04)."""
    A = KiemY38e.A

    def chay_js(self, them):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        dau = next(i for i, x in enumerate(js) if x.startswith("const esc ="))
        cuoi = next(i for i, x in enumerate(js) if x.startswith("const cau ="))
        z = next(i for i, x in enumerate(js) if x.startswith("const CHU_Z15 = {"))
        z2 = next(i for i in range(z, len(js)) if js[i].rstrip().endswith("};"))
        b = next(i for i, x in enumerate(js) if x.startswith("const baoLayLai ="))
        ma = ("const NB = '&nbsp;'; const nbsp = s => String(s).replace(/ /g, NB);"
              "const ICON = new Proxy({}, {get: (o, k) => '<svg data-i=\"' + String(k) + '\"/>'});"
              "const icoMau = (svg, mau, co) => svg.replace('/>', ' stroke=\"' + mau + '\"/>');\n"
              + "\n".join(js[dau:cuoi + 1] + js[z:z2 + 1] + js[b:b + 3]) + "\n" + them)
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "y38f.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_l1_l2_giu_lien_cum(self):
        A = self.A
        a7 = A[7] + " Dữ liệu đã trả về lúc 10:05."
        ra = self.chay_js("console.log(JSON.stringify([" + ", ".join(json.dumps(s) for s in (A[1], A[6], a7)) + "].map(cum)));")
        for s in ra:
            for c in ("Khoá API", "khởi động", "chưa được", "dữ liệu", "Dữ liệu", "bản 0.7.8", "bản 0.7.9"):
                self.assertNotIn(c, s)                                              # cụm nào có trong câu đều đã nối &nbsp;
        self.assertEqual(ra[0].count("Khoá&nbsp;API"), 2)                            # L1: cả 02 chỗ
        for c in ("khởi&nbsp;động", "chưa&nbsp;được", "bản&nbsp;0.7.8", "bản&nbsp;0.7.9", "Dữ&nbsp;liệu"):
            self.assertIn(c, ra[2])
        self.assertIn("dữ&nbsp;liệu", ra[1])

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_l3_o_bao_loi_a8_kem_nut(self):
        h = self.chay_js("console.log(JSON.stringify(baoLayLai(" + json.dumps(self.A[8][:-1]) + ", 2)));")
        self.assertTrue(h.startswith('<div class="bao-lai t13"><div class="loi-o"><svg data-i="circle-alert"/>'), h)
        self.assertIn("<b>Lấy&nbsp;tên,&nbsp;gói</b>", h)
        self.assertIn('<button class="btn btn-phu nho" data-dn-goi="claude" data-dn-tk="2"><svg data-i="log-in" stroke="#1F2329"/>Lấy&nbsp;tên,&nbsp;gói</button>', h)   # icon tối trên nút trắng
        self.assertNotIn("user-round", h)
        css = (GD / "index.html").read_text(encoding="utf-8")
        o = css[css.index(".bao-lai{"):css.index("}", css.index(".bao-lai{"))]
        self.assertIn("background:#fff", o)                                         # không nền đỏ
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("D.trungTk = {...(D.trungTk || {}), claude: (e.ct || {}).lay_lai ? dn.tk : 0}", js)

    def test_qd221_tro_chuyen_gui_ai_xung_ban(self):
        from maychu.hethong.mohinh import trochuyen
        cau = []
        goi = mock.Mock(side_effect=lambda c, **k: cau.append(c) or {"chu": "Chào bạn", "nhatky_ai_id": None, "nguon": "thu"})
        ng = maso.tao()
        with mock.patch.object(trochuyen.congai, "goi", goi):
            kq = trochuyen.gui(None, ng, "Câu 01")
            trochuyen.gui(kq["hoithoai_id"], ng, "Câu 02")
        self.assertEqual(trochuyen.VAI_CHU["nguoi"], "Bạn")
        self.assertIn("Bạn: Câu 01", cau[1])
        self.assertIn("\n\nBạn hỏi tiếp:\nCâu 02", cau[1])
        self.assertIsNone(TU_ANH.search(cau[1]))

    def test_l3_may_chu_bao_lay_lai(self):
        kq = KiemY38dBoSung.lay_ten_trung(self, False)
        self.assertTrue(kq["lay_lai"])
        from maychu.web import api
        e = api._loi_dn("claude", 2, kq, {"nguoidung_id": maso.tao()})
        self.assertEqual((e.status_code, e.detail["lay_lai"], e.detail["loi"]), (409, True, kq["loi"]))


class KiemY38g(NenAT):
    """QĐ222 (N43, cách B): gọi thử hỏng vì hết hạn mức thì vẫn lưu mã mới; chỉ giữ mã cũ khi lỗi khác (N29)."""
    HHM = congai.HetHanMuc("hết hạn mức")

    def chuan_bi(self, co_ma_cu):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        if co_ma_cu:
            madaihan.luu(1, MA_GIA)
            self.han(days=200)
        return madaihan.thong_tin(1)

    def test_a_co_ma_cu_het_han_muc_thi_luu_ma_moi(self):
        cu = self.chuan_bi(True)
        kq = KiemY38d.ket_noi(self, 1, MA_MOI, goi_ok=False, loi=self.HHM)
        self.assertEqual((kq["goi_thu"], kq.get("het_hanmuc"), kq.get("giu_ma_cu")), (False, True, None))
        self.assertEqual(madaihan.lay(1), MA_MOI)                                   # lưu mã mới
        self.assertNotEqual(madaihan.thong_tin(1)["han"], cu["han"])                # hạn mới
        tom = self.f04("kiem_madaihan")[-1][0]
        self.assertIn("hết hạn mức", tom)
        self.assertNotIn("giữ mã cũ", tom)
        k = madaihan.kiem_gan_nhat(1)
        self.assertEqual((k["het_hanmuc"], k["giu_ma_cu"]), (True, False))          # rê chuột: câu A15

    def test_b_co_ma_cu_ma_sai_thi_giu_ma_cu(self):
        cu = self.chuan_bi(True)
        kq = KiemY38d.ket_noi(self, 1, MA_MOI, goi_ok=False)
        self.assertEqual((kq["goi_thu"], kq.get("giu_ma_cu"), kq.get("het_hanmuc")), (False, True, None))
        self.assertEqual((madaihan.lay(1), madaihan.thong_tin(1)["han"]), (MA_GIA, cu["han"]))
        self.assertIn("giữ mã cũ", self.f04("kiem_madaihan")[-1][0])

    def test_c_chua_co_ma_cu_het_han_muc_nhu_cu(self):
        self.chuan_bi(False)
        kq = KiemY38d.ket_noi(self, 1, MA_MOI, goi_ok=False, loi=self.HHM)
        self.assertEqual((kq["goi_thu"], kq.get("het_hanmuc"), kq.get("giu_ma_cu")), (False, True, None))
        self.assertEqual(madaihan.lay(1), MA_MOI)
        self.assertNotIn("giữ mã cũ", self.f04("kiem_madaihan")[-1][0])

    def test_d_goi_thu_dat_nhu_cu(self):
        self.chuan_bi(True)
        kq = KiemY38d.ket_noi(self, 1, MA_MOI)
        self.assertEqual((kq["goi_thu"], kq.get("het_hanmuc"), kq.get("giu_ma_cu")), (True, None, None))
        self.assertEqual(madaihan.lay(1), MA_MOI)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_bao_nhanh_dung_cau_a15(self):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("async function mdXong("))
        b = next(i for i in range(a, len(js)) if js[i].rstrip().endswith("await napMoHinh(); }"))
        z = next(i for i, x in enumerate(js) if x.startswith("const CHU_Z15 = {"))
        z2 = next(i for i in range(z, len(js)) if js[i].rstrip().endswith("};"))
        ma = ("const NB = '&nbsp;'; const nbsp = s => String(s).replace(/ /g, NB); const D = {mdh: {}}; const ra = [];"
              "const bao = s => ra.push(s); const napMoHinh = async () => {}; const ngay = s => s; const CHU_MDH = 'Mã dài hạn';\n"
              + "\n".join(js[z:z2 + 1] + js[a:b + 1])
              + "\n(async () => { await mdXong(1, {goi_thu: false, het_hanmuc: true, loi_goi_thu: 'API Error: 429 rate limit'});"
              "await mdXong(1, {goi_thu: false, loi_goi_thu: 'lỗi khác'}); await mdXong(1, {goi_thu: false, giu_ma_cu: true});"
              "console.log(JSON.stringify(ra)); })();")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "y38g.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        ra = json.loads(r.stdout)
        self.assertEqual(ra[0], KiemY38e.A[15])                                     # A15, không hiện lời gốc tiếng Anh
        self.assertEqual(ra[1], "Đã lưu mã dài hạn nhưng gọi thử chưa được: lỗi khác.")   # ca khác giữ nguyên
        self.assertNotIn("429", "".join(ra))


class KiemY38h(NenAT):
    """CDO U15: L4 ẩn hộp "Làm 01 lần" khi có ô A8; L5 chữ chuông giữ cụm; L6 F04 ghi đúng trạng thái kiểu cũ."""

    def ket_noi_dang_xuat(self, sau):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        tt = [{"loggedIn": True, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"}, {"loggedIn": sau, "authMethod": ""}]
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt) as ttc, \
                mock.patch.object(dg, "ho_so", return_value={"ten_hien": "Nguoi Gia", "goi_ten": "Ultra", "mota_goi": None}), \
                mock.patch.object(dg, "_dang_xuat", return_value=False) as dx, \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {}}):
            madaihan.ket_noi(1, MA_GIA)                                         # `_dang_xuat` báo False như trên máy thật (mã còn hạn)
        dx.assert_called_once()
        self.assertEqual(ttc.call_args_list[-1], mock.call(1, dung_ma=False))   # kiểm lại kiểu cũ KHÔNG kèm mã
        return self.f04("kiem_madaihan")[-1][0]

    def test_l6_da_thoat_thi_ghi_da_dang_xuat(self):
        tom = self.ket_noi_dang_xuat(False)
        self.assertIn("kiểu cũ đã đăng xuất", tom)
        self.assertNotIn("kiểu cũ giữ", tom)

    def test_l6_con_dang_nhap_thi_ghi_giu(self):
        self.assertIn("kiểu cũ giữ", self.ket_noi_dang_xuat(True))

    def test_l6_khong_hoi_duoc_thi_ghi_chua_ro(self):
        self.assertIn("kiểu cũ chưa rõ", self.ket_noi_dang_xuat(None))

    def js(self, them):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        f = lambda p: next(i for i, x in enumerate(js) if x.startswith(p))   # noqa: E731
        ma = ("const ICON = new Proxy({}, {get: () => '<svg/>'}); const gio = s => s; const homNay = () => '2026-11-24';\n"
              + "\n".join(js[f("const esc ="):f("const cau =") + 1] + js[f("const MAU_TB ="):f("function veChuong(")]
                          + [js[f("const coBaoLayLai =")]]) + "\n" + them)
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "y38h.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_l5_chuong_giu_cum(self):
        A = KiemY38e.A
        h = self.js("console.log(JSON.stringify([" + ", ".join(
            "dongTb({chu: " + json.dumps(A[k]) + ", muc: 'do', icon: 'rotate-ccw', di: '09', noi: 'Cập nhật', luc: '2026-11-24T10:05:00'})"
            for k in (4, 5)) + "]));")
        self.assertIn("khởi&nbsp;động", h[1])                                       # ảnh U15_13
        for s in h:
            self.assertIn("bản&nbsp;0.7.8", s)
            self.assertIn("chưa&nbsp;được", s)
        self.assertIn("dữ&nbsp;liệu", h[0])
        self.assertIn("03&nbsp;lần", h[1])

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_l4_an_hop_lam_01_lan_khi_co_o_a8(self):
        ra = self.js("const D = {trung: {claude: 1}, trungTk: {claude: 2}, trungChu: {claude: 'A8'}};"
                     "const a = [coBaoLayLai('claude', 2), coBaoLayLai('claude', 3)];"
                     "D.trung.claude = 0; a.push(coBaoLayLai('claude', 2)); console.log(JSON.stringify(a));")
        self.assertEqual(ra, [True, False, False])                                  # chỉ ô đang lấy tên; ô A8 tắt thì hộp hiện lại
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("if (chuaKiem && !coBaoLayLai('claude', tk)) h += '<div class=\"md-hd\">", js)
        self.assertIn("(cl && coBaoLayLai(g, x.taikhoan) ? baoLayLai(", js)


class KiemY38i(NenAT):
    """CDO U15b G1 (QĐ164 ý 1): "Lấy tên, gói" ở ô 1 cũng chặn trùng với ô khác (trước đây chỉ ô 2 trở đi)."""
    EMAIL_O2 = "nguoi.o2@vidu.invalid"

    def lay_ten_o1(self, o2_co_ma, o1_co_ma=True):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        if o1_co_ma:
            madaihan.luu(1, MA_GIA)
        c = {"ten_hien": "Nguoi O2", "goi_ten": "Max", "email_bam": dg._bam(self.EMAIL_O2), "tochuc_bam": None, "chup_luc": "x"}
        if o2_co_ma:   # ô 2 dùng mã dài hạn, đã có tệp chụp
            madaihan.luu(2, MA_MOI)
            dg.ghi_chup(2, dict(c))
        da_noi = lambda goi, tk, bo_nho=False: {"da_noi": tk in (1, 2), "goi_dang_dung": None}   # noqa: E731
        with mock.patch.object(dg, "trang_thai", side_effect=da_noi), mock.patch.object(dg, "chup_song", return_value=dict(c)), \
                mock.patch.object(dg, "_dinh_danh", side_effect=lambda goi, tk, *a, **k: (self.EMAIL_O2, None) if tk == 2 else None), \
                mock.patch.object(dg, "_dang_xuat", return_value=True) as dx, \
                mock.patch.object(dg, "ghi_nguon") as gn:
            kq = dg._ket_thuc("claude", 1)
        return kq, dx, gn

    def test_g1_o1_trung_o2_co_ma(self):
        kq, dx, gn = self.lay_ten_o1(o2_co_ma=True)
        self.assertEqual((kq["trung_voi"], kq.get("lay_lai"), kq.get("chu_rieng")), (2, True, True))
        self.assertEqual(kq["loi"], madaihan.CHU_DAN["trung_dang_nhap_lai"].format(tk=2))   # A8, số ô đang giữ tài khoản
        self.assertEqual(madaihan.lay(1), MA_GIA)                                    # giữ mã ô 1
        self.assertIsNone(dg.doc_chup(1))                                            # không ghi tên, gói của ô 2 vào ô 1
        dx.assert_called_once()
        gn.assert_not_called()

    def test_g1_o1_trung_o2_chi_dang_nhap_kieu_cu(self):
        kq, dx, gn = self.lay_ten_o1(o2_co_ma=False)                                  # ô 2 chưa có tệp chụp: so định danh sống
        self.assertEqual((kq["trung_voi"], kq.get("lay_lai")), (2, True))
        self.assertEqual(madaihan.lay(1), MA_GIA)
        self.assertIsNone(dg.doc_chup(1))
        gn.assert_not_called()

    def test_g1_o1_chua_co_ma_trung_thi_khong_ghi_g06(self):
        kq, dx, gn = self.lay_ten_o1(o2_co_ma=False, o1_co_ma=False)
        self.assertEqual(kq["trung_voi"], 2)
        self.assertNotIn("lay_lai", kq)
        gn.assert_not_called()                                                       # QĐ164 ý 1: không ghi G06

    def test_g1_o1_khong_trung_thi_ghi_ten_goi_nhu_cu(self):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        madaihan.luu(1, MA_GIA)
        c = {"ten_hien": "Nguoi O1", "goi_ten": "Pro", "email_bam": dg._bam("nguoi.o1@vidu.invalid"), "tochuc_bam": None, "chup_luc": "x"}
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": True, "goi_dang_dung": None}), \
                mock.patch.object(dg, "chup_song", return_value=c), \
                mock.patch.object(dg, "_dinh_danh", return_value=(self.EMAIL_O2, None)), \
                mock.patch.object(dg, "_dang_xuat", return_value=True):
            kq = dg._ket_thuc("claude", 1)
        self.assertTrue(kq.get("chup"))
        self.assertEqual(dg.doc_chup(1)["ten_hien"], "Nguoi O1")


class KiemY38j(NenAT):
    """QĐ223 (G1b, cách B): dán mã ở ô 1 khi đăng nhập kiểu cũ nhầm tài khoản ô khác → vẫn lưu mã, không ghi tệp chụp,
    đăng xuất lượt nhầm, trả trung_voi + lay_lai (câu A8). Ô 2 trở đi giữ câu 22."""
    EMAIL_O2 = "nguoi.o2@vidu.invalid"

    def dan_ma(self, tk, o2_co_ma, trung=True):
        self.nguon("goi_claude_01", "goi", 1, "anthropic")
        c2 = {"ten_hien": "Nguoi O2", "goi_ten": "Max", "email_bam": dg._bam(self.EMAIL_O2), "tochuc_bam": None, "chup_luc": "x"}
        c = c2 if trung else {**c2, "ten_hien": "Nguoi O1", "email_bam": dg._bam("nguoi.o1@vidu.invalid")}
        giu = 1 if tk == 2 else 2   # ô đang giữ tài khoản
        if o2_co_ma:
            madaihan.luu(giu, MA_MOI)
            dg.ghi_chup(giu, dict(c2))
        tt = [{"loggedIn": True, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"}, {"loggedIn": False, "authMethod": ""}]
        da_noi = lambda goi, t, bo_nho=False: {"da_noi": t in (1, 2), "goi_dang_dung": None}   # noqa: E731
        with mock.patch.object(madaihan, "_trang_thai_cli", side_effect=tt), \
                mock.patch.object(dg, "trang_thai", side_effect=da_noi), mock.patch.object(dg, "chup_song", return_value=dict(c)), \
                mock.patch.object(dg, "_dinh_danh", side_effect=lambda goi, t, *a, **k: (self.EMAIL_O2, None) if t == giu else None), \
                mock.patch.object(dg, "ho_so", return_value={"ten_hien": None, "goi_ten": None, "mota_goi": None}), \
                mock.patch.object(dg, "_dang_xuat", return_value=False) as dx, \
                mock.patch.object(dg, "ghi_nguon", return_value="nguon_thu"), \
                mock.patch.object(congai, "_goi_claude", return_value={"hanmuc": {}}) as goi:
            kq = madaihan.ket_noi(tk, MA_GIA)
        return kq, dx, goi

    def kiem_o1_trung(self, kq, dx):
        self.assertEqual((kq["xong"], kq["trung_voi"], kq["lay_lai"]), (True, 2, True))
        self.assertEqual(kq["trung_chu"], "Bạn vừa đăng nhập tài khoản đã kết nối ở Tài khoản 2. Bấm Lấy tên, gói, đăng nhập đúng"
                                          " tài khoản của mã này.")                                           # A8
        self.assertEqual(madaihan.lay(1), MA_GIA)                                    # vẫn lưu mã
        self.assertIsNone(dg.doc_chup(1))                                            # không ghi tên, gói của ô 2
        dx.assert_called_once()                                                      # đăng xuất lượt nhầm
        tom = self.f04("kiem_madaihan")[-1][0]
        self.assertIn("đăng nhập kiểu cũ trùng tài khoản 02, đã đăng xuất lượt nhầm, không ghi tên, gói", tom)
        self.assertNotIn(self.EMAIL_O2, tom)
        self.assertNotIn("Nguoi O2", tom)

    def test_o1_trung_o2_co_ma(self):
        self.kiem_o1_trung(*self.dan_ma(1, o2_co_ma=True)[:2])

    def test_o1_trung_o2_chi_dang_nhap_kieu_cu(self):
        self.kiem_o1_trung(*self.dan_ma(1, o2_co_ma=False)[:2])

    def test_o1_khong_trung_nhu_cu(self):
        kq, dx, _ = self.dan_ma(1, o2_co_ma=True, trung=False)
        self.assertNotIn("trung_voi", kq)
        self.assertEqual(dg.doc_chup(1)["ten_hien"], "Nguoi O1")                    # ghi tên, gói như cũ
        dx.assert_called_once()                                                      # gọi thử đạt → đăng xuất kiểu cũ (Đ8)

    def test_o2_trung_cau_22_nhu_cu(self):
        kq, dx, goi = self.dan_ma(2, o2_co_ma=True)
        self.assertEqual(kq, {"loi": madaihan.CHU_DAN["trung"].format(tk=1), "trung_voi": 1})
        self.assertIsNone(madaihan.thong_tin(2))                                     # không lưu mã
        goi.assert_not_called()
        dx.assert_not_called()

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_giao_dien_hien_o_a8_sau_dan_ma(self):
        import subprocess as sp
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("async function mdXong("))
        b = next(i for i in range(a, len(js)) if js[i].rstrip().endswith("await napMoHinh(); }"))
        ma = ("const D = {mdh: {}, trung: {}}; const bao = s => 0; const napMoHinh = async () => {}; const ngay = s => s;"
              "const CHU_MDH = 'Mã dài hạn'; const CHU_Z15 = {};\n" + "\n".join(js[a:b + 1])
              + "\n(async () => { await mdXong(1, {xong: true, goi_thu: true, han: 'x', trung_voi: 2, lay_lai: true, trung_chu: 'A8'});"
              "console.log(JSON.stringify([D.trung.claude, D.trungTk.claude, D.trungChu.claude])); })();")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "y38j.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [2, 1, "A8"])                        # coBaoLayLai('claude', 1) → ô A8 ở ô 1


TU_ANH = __import__("re").compile(r"(?<![\w-])[Aa]nh(?![\w-])")
# QĐ221: lời gửi AI ở Trò chuyện AI cũng xưng "bạn" — không còn ngoại lệ nào
CHO_PHEP_PY = set()


def _chuoi_py(p):
    """Chuỗi chữ trong mã Python, bỏ chuỗi mô tả hàm; bỏ mã dữ liệu 'anh' (loại người, không phải chữ hiện)."""
    import ast
    cay = ast.parse(p.read_text(encoding="utf-8"))
    mota = {id(n.body[0].value) for n in ast.walk(cay)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in mota and n.value != "anh":
            yield n.lineno, n.value


class KiemXungHo(unittest.TestCase):
    """QĐ220, từ điển quy tắc 7: chữ người dùng nhìn thấy xưng "bạn", không xưng "anh" (không bắt "ảnh", "nhanh", "xanh")."""

    def test_regex_khong_bat_nham(self):
        for s in ("ảnh", "nhanh", "xanh", "thanh", "Thanh toán", "danh sách", "anh-dd", "v-anh", "cạnh", "tranh"):
            self.assertIsNone(TU_ANH.search(s), s)
        for s in ("anh bấm", "Anh dán", "của&nbsp;anh.", "của anh", "chờ anh"):
            self.assertIsNotNone(TU_ANH.search(s), s)

    def test_giao_dien_khong_con_anh(self):
        import re
        js = (GD / "app.js").read_text(encoding="utf-8")
        js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
        sai = []
        for i, d in enumerate(js.splitlines(), 1):
            c = next((m.start() for m in re.finditer("//", d) if d[max(0, m.start() - 1)] != ":"), len(d))   # bỏ chú thích
            if TU_ANH.search(d[:c]):
                sai.append(f"app.js:{i}: {d.strip()[:100]}")
        html = (GD / "index.html").read_text(encoding="utf-8")
        html = re.sub(r"<!--.*?-->|<style.*?</style>|<script.*?</script>", "", html, flags=re.S)
        sai += [f"index.html: …{html[max(0, m.start() - 50):m.end() + 20]}…" for m in TU_ANH.finditer(html)]
        self.assertEqual(sai, [])

    def test_cau_bao_may_chu_khong_con_anh(self):
        sai = []
        for p in sorted((GOC / "maychu").rglob("*.py")):
            ten = p.relative_to(GOC).as_posix()
            for dong, s in _chuoi_py(p):
                if (ten, s) not in CHO_PHEP_PY and TU_ANH.search(s.replace("'anh'", "")):
                    sai.append(f"{ten}:{dong}: {s[:100]}")
        self.assertEqual(sai, [])


# ---------------- Chữ ở 01 chỗ ----------------
class KiemChu(unittest.TestCase):
    def test_chu_moi_o_01_cho(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertEqual(js.count("const CHU_CN = {"), 1)
        self.assertEqual(js.count("const CHU_Z15 = {"), 1)
        for k in ("o_thieu", "an_toan", "an_toan_chan", "sao_loi", "drive_chua_noi", "drive_qua_gio", "o_du", "o_thieu_lam", "qv_an_toan", "qv_khong_co", "qv_mat", "qv_giu", "qv_can_dong_y"):
            self.assertIn(k, antoan.CHU)

    def test_23_cau_da_duyet_dung_nguyen_van(self):   # QĐ217 (bảng Z15, Z15b; 03 câu CPO sửa ở dòng 19, 22, 23); xưng "bạn" QĐ220
        js = (GD / "app.js").read_text(encoding="utf-8")
        for c in ("Mã dài hạn là gì?", "'Mã dài hạn'",
                  "Đăng nhập kiểu cũ có thể hết phiên giữa chừng: bot và việc nền dừng theo. Mã dài hạn giữ kết nối ổn định.",
                  "Mỗi mã dùng 365 ngày. Mã mới chỉ cấp khi bạn đăng nhập trang claude.ai.",
                  'Trước hạn 07 ngày, chuông nhắc mỗi ngày; bạn bấm "Lấy mã mới" là xong.',
                  'Cách 1 (nên dùng): bấm "Kết nối Claude", máy chủ tự chạy lệnh; bạn chỉ đăng nhập claude.ai và dán mã xác nhận.',
                  'Cách 2: khi máy chủ không tự lấy được, chạy lệnh claude setup-token ở máy khác rồi bấm "Dán mã".',
                  "Mã vẫn tính vào gói Claude của bạn: việc chạy nền tính như khi đăng nhập gói.",
                  'Mã dài hạn chỉ dán vào ô "Dán mã". Không chụp ảnh, không gửi qua tin nhắn.', "'Đã hiểu'",
                  "Tạo mã ở máy có Claude Code, chạy lệnh:", "'claude setup-token'", "'Đã chép.'", "'Thu hồi mã cũ ở trang '",
                  "claude.ai/settings/claude-code", "Trang hiện 01 mã xác nhận. Chép mã đó, dán vào ô dưới.",
                  "Máy chủ tự đổi thành mã dài hạn, cất ở Két khoá; bạn không cần chép mã dài hạn.", "'Mã xác nhận'",
                  "'Kiểm mã · đạt '", "'Kiểm mã · chưa được '", "Claude chưa nhận mã này. Bấm Lấy mã mới hoặc Dán mã lại.",
                  "'Chưa kiểm được trùng tài khoản'",
                  "Phần mềm chưa có tên, gói của tài khoản này nên chưa so được với tài khoản khác. Mã vẫn dùng bình thường.",
                  "'Làm 01 lần để hiện tên, gói'", "'Lấy tên, gói'",
                  'Bấm "Lấy tên, gói", đăng nhập đúng tài khoản Claude này; phần mềm tự ghi tên, gói và giữ nguyên mã dài hạn.',
                  "'Lấy mã mới · tài khoản '", "'Đăng nhập đúng tài khoản '",
                  "'Mã vừa dán có ' + n + ' ký tự, chưa trọn. Chép lại cả mã rồi dán lại.'"):
            self.assertIn(c, js)
        self.assertEqual(madaihan.CHU_DAN["trung"].format(tk=1) + ".", "Tài khoản Claude này đã kết nối ở Tài khoản 1. Phần mềm không lưu mã."
                         " Thu hồi mã vừa tạo ở claude.ai/settings/claude-code.")                                     # dòng 22
        self.assertEqual(madaihan.CHU_DAN["chua_tron"].format(n=54) + ".", "Mã vừa dán có 54 ký tự, chưa trọn. Chép lại cả mã rồi dán lại.")   # 23

    def test_24_cau_05_lop_dung_nguyen_van(self):   # QĐ218 (bảng Z16 dòng 24–47)
        js = (GD / "app.js").read_text(encoding="utf-8")
        for c in ("Bước 1/2 · Đang tạo bản sao Drive (tối đa 10 phút)", "Bước 1/2 · Bản sao Drive quá 10 phút, chờ bạn chọn",
                  "'Bước 2/2 · Đang tải bản '", "'Chưa đủ ổ trống'", "Cập nhật khi chưa có bản sao Drive?",
                  "Máy chủ hỏng thì không lấy lại được bản sao này.", "'Kết nối Drive'", "'Huỷ'", "'Vẫn cập nhật'",
                  "'Chế độ an toàn'", "'Việc nền, AI tạm dừng.'", "Chỉ mở Cập nhật và nhật ký; việc ghi khác bị chặn.",
                  "Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.", "'Quay về bản trước'",
                  "'Chạy lại bản ' + b + ' đi kèm gói cài, không cần mạng'", "'Quay về bản ' + b + '?'",
                  "Phần mềm tạm ngừng rồi tự mở lại. Thao tác ghi vào nhật ký.", "Đang quay về bản trước. Trang tự tải lại khi xong.",
                  "'Kiểm sau cập nhật: '"):
            self.assertIn(c, js, c)
        self.assertEqual(antoan.CHU["o_thieu"].format(trong="1,2 GB", can="2,6 GB") + " " + antoan.CHU["o_thieu_lam"],
                         "Ổ trống còn 1,2 GB, cần 2,6 GB để cập nhật an toàn. Dọn ổ máy chủ rồi bấm Kiểm tra lại.")      # 25
        self.assertEqual(antoan.CHU["an_toan"].format(den="0.3.0", luc="10:05"),
                         "Chế độ an toàn: bản 0.3.0 nâng dữ liệu chưa được, dữ liệu đã trả về như trước lúc 10:05.")   # 35
        self.assertEqual(antoan.CHU["drive_chua_noi"], "Drive chưa kết nối. Bản sao chỉ nằm trên máy chủ.")             # 31
        self.assertEqual(antoan.CHU["drive_qua_gio"], "Đẩy bản sao lên Drive đã quá 10 phút. Bản sao chỉ nằm trên máy chủ.")   # 32
        self.assertEqual(antoan.CHU["qv_mat"].format(luc="10:05"), "Bản đang dùng đã nâng dữ liệu khi cập nhật. Quay về thì dữ liệu"
                         " trả về lúc 10:05 (trước khi cập nhật); việc nhập sau lúc đó không giữ được.")                   # 40
        self.assertEqual(antoan.CHU["qv_an_toan"].format(luc="10:05"), "Dữ liệu đã trả về lúc 10:05, quay về không mất thêm.")   # 42

    def test_khong_nen_do(self):
        html = (GD / "index.html").read_text(encoding="utf-8")
        doan = html[html.index(".dai-antoan{"):html.index("#cn-antoan .dong")]
        self.assertIn("background:#fff", doan)
        self.assertNotIn("background:var(--canh)", doan)


if __name__ == "__main__":
    unittest.main()
