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
            self.assertEqual(capnhat.yeu_cau("x", "ngay"), {"ok": True, "sao": True})
        bd.assert_called_once()


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
        self.assertTrue(all(x[0] == "hangngay" and json.loads(x[1])["dip"] == "truoc_capnhat" for x in d))   # CDA C1
        self.assertEqual(antoan.doc()["yeu_cau"]["den"], "0.7.10")
        self.assertIsNone(capnhat.trang_thai_sao()["dang_sao"])

    def test_drive_noi_thi_cho_day_xong(self):
        kq, goi = self.chay(drive_noi=True)
        self.assertEqual(goi, ["nguoi"])
        self.assertTrue(antoan.doc()["yeu_cau"]["drive"])
        noi = next(p for p in (self.dl / "saoluu").iterdir() if "_truoc_" in p.name)
        self.assertEqual(capnhat._con_cho_drive(noi), 0)

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
        self.assertEqual((kq["dat"], kq["tong"], kq["loi"]), (5, 6, ["Công cụ AI"]))
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
        self.assertEqual(kq["loi"], ["Đúng bản", "Lịch chạy nền"])
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
            self.assertIn("10:05 24/11", q["chu"])
            self.assertEqual(antoan.quay_ve("nguoi")["loi"], antoan.CHU["qv_can_dong_y"])
            self.assertEqual(antoan.quay_ve("nguoi", True, tre_giay=0.01), {"ok": True, "ban": "0.7.8"})
            time.sleep(0.3)
            th.assert_called_once()
        self.assertEqual(self.f04("thu"), [])                                       # dữ liệu trả về bản chụp
        self.assertEqual(antoan.doc(self.dl)["chay_ban_truoc"]["ban_truoc"], "0.7.8")
        self.assertIn("0.7.9 → 0.7.8", self.f04("quayve")[0][0])

    def test_khong_nang_luocdo_giu_du_lieu_khong_co_ban_truoc_thi_khong_co_nut(self):
        g = self.goc()
        with mock.patch.object(antoan, "GOC_MA", g), mock.patch.object(antoan, "_thoat"):
            q = antoan.thong_tin_quayve()
            self.assertEqual((q["mat_tu"], q["chu"]), (None, "Quay về bản 0.7.8. Dữ liệu giữ nguyên"))
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
        tt = [{"loggedIn": cu, "authMethod": ""}, {"loggedIn": True, "authMethod": "oauth_token"}]
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
        self.assertEqual(madaihan.chu_loi_dan("sk-ant-api03-xyz"), madaihan.CHU_DAN["chua_tron"].format(n=16))
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


# ---------------- Chữ ở 01 chỗ ----------------
class KiemChu(unittest.TestCase):
    def test_chu_moi_o_01_cho(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertEqual(js.count("const CHU_CN = {"), 1)
        self.assertEqual(js.count("const CHU_Z15 = {"), 1)
        for k in ("o_thieu", "an_toan", "an_toan_chan", "sao_loi", "sao_chi_may", "qv_khong_co", "qv_mat", "qv_giu", "qv_can_dong_y"):
            self.assertIn(k, antoan.CHU)

    def test_23_cau_da_duyet_dung_nguyen_van(self):   # QĐ217 (bảng Z15, Z15b; 03 câu CPO sửa ở dòng 19, 22, 23)
        js = (GD / "app.js").read_text(encoding="utf-8")
        for c in ("Mã dài hạn là gì?", "'Mã dài hạn'",
                  "Đăng nhập kiểu cũ có thể hết phiên giữa chừng: bot và việc nền dừng theo. Mã dài hạn giữ kết nối ổn định.",
                  "Mỗi mã dùng 365 ngày. Mã mới chỉ cấp khi anh đăng nhập trang claude.ai.",
                  'Trước hạn 07 ngày, chuông nhắc mỗi ngày; anh bấm "Lấy mã mới" là xong.',
                  'Cách 1 (nên dùng): bấm "Kết nối Claude", máy chủ tự chạy lệnh; anh chỉ đăng nhập claude.ai và dán mã xác nhận.',
                  'Cách 2: khi máy chủ không tự lấy được, chạy lệnh claude setup-token ở máy khác rồi bấm "Dán mã".',
                  "Mã vẫn tính vào gói Claude của anh: việc chạy nền tính như khi đăng nhập gói.",
                  'Mã dài hạn chỉ dán vào ô "Dán mã". Không chụp ảnh, không gửi qua tin nhắn.', "'Đã hiểu'",
                  "Tạo mã ở máy có Claude Code, chạy lệnh:", "'claude setup-token'", "'Đã chép.'", "'Thu hồi mã cũ ở trang '",
                  "claude.ai/settings/claude-code", "Trang hiện 01 mã xác nhận. Chép mã đó, dán vào ô dưới.",
                  "Máy chủ tự đổi thành mã dài hạn, cất ở Két khoá; anh không cần chép mã dài hạn.", "'Mã xác nhận'",
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

    def test_khong_nen_do(self):
        html = (GD / "index.html").read_text(encoding="utf-8")
        doan = html[html.index(".dai-antoan{"):html.index("#cn-antoan .dong")]
        self.assertIn("background:#fff", doan)
        self.assertNotIn("background:var(--canh)", doan)


if __name__ == "__main__":
    unittest.main()
