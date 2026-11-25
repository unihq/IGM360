"""Bài kiểm Y46 (bản 0.8.4; QĐ263, QĐ264, QĐ265, QĐ271; PTD-14 B + D; CDA KT-Y46-KH K1–K5).

Loại 1 – bài đơn vị: giả tiến trình (npm, CLI), giả npm bằng httpx.MockTransport. KHÔNG gọi npm, CLI, mạng thật.
"""
import asyncio
import json
import re
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import httpx

from maychu.dulieu import khoitao, ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import antoan, capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.mohinh import nangcli

BAY = datetime(2026, 11, 25, 3, 0, tzinfo=MUIGIO_VN)


def npm_gia(ban="2.1.340", ra=BAY - timedelta(hours=30), giai_nen=1000):
    def tra(req: httpx.Request):
        assert str(req.url).startswith("https://registry.npmjs.org/")          # K5: ghi cứng địa chỉ
        return httpx.Response(200, json={"dist-tags": {"latest": ban}, "time": {ban: ra.isoformat()},
                                         "versions": {ban: {"dist": {"unpackedSize": giai_nen}}}})
    return httpx.Client(transport=httpx.MockTransport(tra))


class ChayGia:
    """Giả `subprocess.run`: npm install tạo tệp chạy ở đúng chỗ; `--version` trả số bản theo tệp."""

    def __init__(self, ban_cai=None, loi_cai=False):
        self.lenh, self.env, self.ban_cai, self.loi_cai = [], [], ban_cai, loi_cai

    def __call__(self, lenh, **kw):
        self.lenh.append(lenh)
        self.env.append(kw.get("env"))
        if lenh[0] == "npm":
            dich = Path(lenh[lenh.index("--prefix") + 1])
            goi = next(g for g, c in nangcli.GOI_CLI.items() if lenh[-1].startswith(c["npm"] + "@"))
            ban = lenh[-1].rsplit("@", 1)[1]
            b = dich / "node_modules" / ".bin" / nangcli.GOI_CLI[goi]["lenh"]
            b.parent.mkdir(parents=True, exist_ok=True)
            b.write_text(self.ban_cai or ban, encoding="utf-8")
            Path(lenh[lenh.index("--cache") + 1]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(lenh, 1 if self.loi_cai else 0, "", "")
        if lenh[1:] in (["auth", "status", "--json"], ["login", "status"]):       # kiểm thử thêm khi đã đăng nhập
            ok = getattr(self, "da_noi_moi", True)
            out = json.dumps({"loggedIn": ok}) if lenh[1] == "auth" else ("Logged in using ChatGPT" if ok else "Not logged in")
            return subprocess.CompletedProcess(lenh, 0 if ok else 1, out, "")
        if lenh[-1] == "--version":
            p = Path(lenh[0])
            out = p.read_text(encoding="utf-8") if p.exists() else ""
            return subprocess.CompletedProcess(lenh, 0 if out else 1, f"{out} (Claude Code)\n", "")
        raise AssertionError(f"lệnh lạ: {lenh}")


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"}))
        khoitao.tao_het(self.dl)
        antoan.CHE_DO["an_toan"] = False
        self.addCleanup(antoan.CHE_DO.update, an_toan=False)
        capnhat._SAO.update(buoc=None, tu=0.0, loi=None, den=None)                # trạng thái bộ nhớ do bài trước để lại
        capnhat._CHO.update(tu=0.0, nguoi=None)
        from maychu.hethong import tiendo
        tiendo._NHO.update(td=None, ghi_luc=0.0)
        self.addCleanup(tiendo._NHO.update, td=None, ghi_luc=0.0)
        nangcli._GOC.clear()
        nangcli._GOC.update(claude="2.1.331", chatgpt="0.172.0")                   # bản trong gói, không chạy CLI thật
        self.addCleanup(nangcli._GOC.clear)
        self.enterContext(mock.patch.object(nangcli, "_uoc_giai_nen", return_value=1000))
        from maychu.hethong.mohinh import dangnhap_goi
        self.trang_thai = self.enterContext(mock.patch.object(dangnhap_goi, "trang_thai", return_value={"da_noi": False}))

    def nang(self, **kw):
        chay = kw.pop("chay", None) or ChayGia()
        return nangcli.nang(kw.pop("goi", "claude"), self.dl, client=kw.pop("client", None) or npm_gia(**kw.pop("npm", {})),
                            chay=chay, bay=kw.pop("bay", BAY), **kw), chay

    def f04(self, lenhcon):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return cn.execute("SELECT thamso_tomtat, ketqua FROM nhatky_thaotac WHERE congcu = 'cli' AND lenhcon = ?",
                              (lenhcon,)).fetchall()
        finally:
            cn.close()


class KiemCongTac(Nen):
    def test_mac_dinh_bat_va_an_o_ngan_thong_so(self):
        self.assertTrue(thongso.cong_tac_bat("tunang_congcu_ai", self.dl))       # QĐ263: mặc định bật
        thongso.khoi_tao(self.dl)
        self.assertTrue(thongso.cong_tac_bat("tunang_congcu_ai", self.dl))
        self.assertNotIn("tunang_congcu_ai", [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])   # Z20: ở khối Công cụ AI
        thongso.gat("tunang_congcu_ai", False, "hethong", self.dl)
        self.assertFalse(thongso.cong_tac_bat("tunang_congcu_ai", self.dl))


class KiemBoNang(Nen):
    def test_dat_doi_con_tro_ghi_f04_xoa_dem(self):
        kq, chay = self.nang()
        self.assertEqual(kq, {"kq": "dat", "ban": "2.1.340", "truoc": "2.1.331"})
        tt = nangcli.doc_trangthai(self.dl)["claude"]
        self.assertEqual((tt["dang"], tt["truoc"], tt["ket_qua"]), ("2.1.340", None, "dat"))
        self.assertEqual(len(self.f04("nang")), 1)
        self.assertFalse((nangcli.thumuc_cli(self.dl) / ".npm_dem").exists())      # K1c
        lenh = chay.lenh[0]
        self.assertEqual(lenh[lenh.index("--registry") + 1], "https://registry.npmjs.org/")   # K5
        self.assertNotIn("--ignore-scripts", lenh)                                # Claude chạy bước cài kèm gói chính
        self.assertEqual(chay.env[0]["npm_config_userconfig"], os.devnull)       # K5: không đọc .npmrc
        self.assertEqual(lenh[-1], "@anthropic-ai/claude-code@2.1.340")

    def test_codex_bo_buoc_cai_kem(self):
        kq, chay = self.nang(goi="chatgpt", npm={"ban": "0.180.0"})
        self.assertEqual(kq["kq"], "dat")
        self.assertIn("--ignore-scripts", chay.lenh[0])
        self.assertEqual(chay.lenh[0][-1], "@openai/codex@0.180.0")

    def test_chua_du_24_gio_va_nut_nang_ngay(self):
        kq, chay = self.nang(npm={"ra": BAY - timedelta(hours=5)})
        self.assertEqual(kq["kq"], "chua_du_24_gio")
        self.assertEqual([l for l in chay.lenh if l[0] == "npm"], [])
        kq, _ = self.nang(npm={"ra": BAY - timedelta(hours=5)}, ngay=True)       # K2: bấm Nâng công cụ AI bỏ qua 24 giờ
        self.assertEqual(kq["kq"], "dat")

    def test_kiem_thu_chua_dat_ve_ban_truoc_nho_ban_hong(self):
        kq, _ = self.nang(chay=ChayGia(ban_cai="2.1.339"))                        # --version không đúng số bản
        self.assertEqual(kq, {"kq": "hong", "ban": "2.1.340", "giu": "2.1.331"})
        tt = nangcli.doc_trangthai(self.dl)["claude"]
        self.assertEqual((tt["dang"], tt["hong"]), (None, ["2.1.340"]))
        self.assertFalse((nangcli.thumuc_cli(self.dl) / "claude" / "2.1.340").exists())
        self.assertEqual(self.f04("loi")[0][1], "loi")
        kq, chay = self.nang(ngay=True)
        self.assertEqual(kq["kq"], "da_hong")                                     # không thử lại bản hỏng
        self.assertEqual([l for l in chay.lenh if l[0] == "npm"], [])

    def test_cai_loi(self):
        kq, _ = self.nang(chay=ChayGia(loi_cai=True))
        self.assertEqual(kq["kq"], "hong")

    def test_giu_dung_ban_dang_va_01_ban_truoc(self):
        for ban in ("2.1.340", "2.1.341", "2.1.342"):
            self.assertEqual(self.nang(npm={"ban": ban}, ngay=True)[0]["kq"], "dat")
        con = sorted(p.name for p in (nangcli.thumuc_cli(self.dl) / "claude").iterdir())
        self.assertEqual(con, ["2.1.341", "2.1.342"])
        tt = nangcli.doc_trangthai(self.dl)["claude"]
        self.assertEqual((tt["dang"], tt["truoc"]), ("2.1.342", "2.1.341"))

    def test_moi_nhat(self):
        self.assertEqual(self.nang(npm={"ban": "2.1.331"})[0], {"kq": "moi_nhat", "ban": "2.1.331"})

    def test_cong_tac_tat_chi_nut_nang_ngay_chay(self):
        thongso.gat("tunang_congcu_ai", False, "hethong", self.dl)
        self.assertEqual(self.nang()[0], {"kq": "tat"})
        self.assertEqual(self.nang(ngay=True)[0]["kq"], "dat")

    def test_k1_khong_chay_khi_cap_nhat_an_toan_quay_ve_tam_dung(self):
        with mock.patch.object(capnhat, "dang_cho", return_value=True):
            self.assertEqual(self.nang(ngay=True)[0], {"kq": "khong_chay", "ly_do": "dang_cap_nhat"})
        antoan.CHE_DO["an_toan"] = True
        self.assertEqual(self.nang(ngay=True)[0]["ly_do"], "che_do_an_toan")
        antoan.CHE_DO["an_toan"] = False
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.8.4", "ban_truoc": "0.8.3"})
        self.assertEqual(self.nang(ngay=True)[0]["ly_do"], "co_quay_ve")
        antoan.ghi(self.dl, chay_ban_truoc=None)
        nangcli.tam_dung("0.8.3", self.dl)
        self.assertEqual(self.nang(ngay=True)[0]["ly_do"], "tam_dung")

    def test_k1b_thieu_cho_trong_khong_cai(self):
        with mock.patch.object(nangcli.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(10, 10, 5)):
            kq, chay = self.nang(ngay=True)
        self.assertEqual(kq["kq"], "thieu_o")
        self.assertEqual([l for l in chay.lenh if l[0] == "npm"], [])
        self.assertEqual(self.f04("thieu_o")[0][1], "bichan")


class KiemDangNhapSauNang(Nen):
    def setUp(self):
        super().setUp()
        from maychu.hethong.mohinh import congai
        self.congai = congai
        self.goi_claude = self.enterContext(mock.patch.object(congai, "_goi_claude", return_value={"chu": "OK"}))
        self.goi_chatgpt = self.enterContext(mock.patch.object(congai, "_goi_chatgpt", return_value={"chu": "OK"}))

    def test_da_dang_nhap_ban_moi_doc_duoc_tep_dang_nhap(self):
        self.trang_thai.return_value = {"da_noi": True}
        kq, chay = self.nang()
        self.assertEqual(kq["kq"], "dat")
        self.assertIn(["auth", "status", "--json"], [l[1:] for l in chay.lenh])
        a = self.goi_claude.call_args                                             # P3: 01 lượt gọi ngắn bằng bản mới
        self.assertEqual((a.args[0], a.args[1], a.args[2]), (1, nangcli.CAU_THU, None))
        self.assertTrue(a.kwargs["cli"].endswith(str(Path("2.1.340", "node_modules", ".bin", "claude"))))

    def test_p3_goi_ngan_loi_thi_hong(self):
        self.trang_thai.return_value = {"da_noi": True}
        self.goi_claude.side_effect = self.congai.LoiAI("Claude", "báo lỗi", "x")
        self.assertEqual(self.nang()[0]["kq"], "hong")

    def test_qd306_het_han_muc_thi_hoan_giu_ban_cu_luot_sau_thu_lai(self):
        self.trang_thai.return_value = {"da_noi": True}
        self.nang(npm={"ban": "2.1.340"})                                         # đang dùng 2.1.340
        self.goi_claude.side_effect = self.congai.HetHanMuc("hết hạn mức", {})
        kq, _ = self.nang(npm={"ban": "2.1.341"})
        self.assertEqual(kq, {"kq": "hoan", "ban": "2.1.341", "giu": "2.1.340"})
        tt = nangcli.doc_trangthai(self.dl)["claude"]
        self.assertEqual((tt["dang"], tt["hong"], tt["ket_qua"], tt["hoan_ban"]), ("2.1.340", [], "hoan", "2.1.341"))
        self.assertTrue(nangcli.duong_cli("claude", self.dl).endswith(str(Path("2.1.340", "node_modules", ".bin", "claude"))))
        self.assertFalse((nangcli.thumuc_cli(self.dl) / "claude" / "2.1.341").exists())
        self.assertEqual(self.f04("hoan"), [("claude 2.1.341: hoãn: hết hạn mức, giữ bản 2.1.340", "bichan")])
        self.assertEqual(self.f04("loi"), [])
        self.assertEqual(self.nang(npm={"ban": "2.1.341"})[0]["kq"], "hoan")      # vẫn hết hạn mức: hoãn tiếp
        self.goi_claude.side_effect = None                                        # có hạn mức lại
        kq, _ = self.nang(npm={"ban": "2.1.341"}, ngay=True)                       # nút Nâng công cụ AI vẫn dùng được
        self.assertEqual(kq["kq"], "dat")
        tt = nangcli.doc_trangthai(self.dl)["claude"]
        self.assertEqual((tt["dang"], tt["ket_qua"], tt.get("hoan_ban")), ("2.1.341", "dat", None))

    def test_chua_dang_nhap_khong_goi_ai(self):
        self.nang()
        self.goi_claude.assert_not_called()

    def test_da_dang_nhap_ban_moi_doc_loi_thi_hong(self):
        self.trang_thai.return_value = {"da_noi": True}
        chay = ChayGia()
        chay.da_noi_moi = False                                                   # CLI mới không đọc được tệp đăng nhập cũ
        kq, _ = self.nang(goi="chatgpt", npm={"ban": "0.180.0"}, chay=chay)
        self.assertEqual(kq["kq"], "hong")


class KiemConTro(Nen):
    def test_cli_thu_tu_bien_moi_truong_con_tro_ban_trong_goi(self):
        from maychu.hethong.mohinh import dangnhap_goi as dg
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGM360_CLAUDE_CLI", None)
            self.assertEqual(dg._cli("claude"), "claude")                         # chưa nâng: bản trong gói
            self.nang()
            self.assertTrue(dg._cli("claude").endswith(str(Path(".bin", "claude"))))   # con trỏ bản đã nâng
            os.environ["IGM360_CLAUDE_CLI"] = "/khong_co_cli"
            self.assertEqual(dg._cli("claude"), "/khong_co_cli")                  # biến môi trường đứng đầu (bài kiểm)

    def test_qd264_quay_ve_thi_tam_dung_len_ban_moi_thi_mo_lai(self):
        self.nang()
        with mock.patch.object(antoan, "thong_tin_quayve", return_value={"co": True, "ban": "0.8.3", "mat_tu": None,
                                                                         "chu": ""}), \
                mock.patch.object(antoan, "_thoat"), mock.patch.object(antoan.threading, "Timer"), \
                mock.patch.object(capnhat, "ban_dang_chay", return_value="0.8.4"):   # không hẹn giờ thoát tiến trình
            antoan.quay_ve("hethong", False, self.dl, tre_giay=0)
        d = nangcli.doc_trangthai(self.dl)
        self.assertEqual((d["tam_dung"], d["tam_dung_ban"]), (True, "0.8.3"))
        self.assertIsNone(nangcli.duong_cli("claude", self.dl))                   # dùng bản trong gói
        nangcli.mo_lai_neu_len_ban_moi("0.8.3", self.dl)
        self.assertTrue(nangcli.doc_trangthai(self.dl)["tam_dung"])               # cùng bản đã quay về: vẫn dừng
        nangcli.mo_lai_neu_len_ban_moi("0.8.5", self.dl)
        self.assertFalse(nangcli.doc_trangthai(self.dl)["tam_dung"])              # lên bản mới: tự nâng lại
        api = (Path(__file__).resolve().parents[2] / "maychu/web/api.py").read_text(encoding="utf-8")
        self.assertIn('if ten == "tunang_congcu_ai" and body.bat:', api)          # gạt bật lại cũng mở lại (Z20 dòng 13)
        kd = (Path(__file__).resolve().parents[2] / "maychu/khoidong.py").read_text(encoding="utf-8")
        self.assertIn("nangcli.mo_lai_neu_len_ban_moi(capnhat.ban_dang_chay())", kd)

    def test_diem_kiem_cli_doc_ban_dang_dung(self):
        from maychu.hethong.mohinh import dangnhap_goi as dg
        os.environ.pop("IGM360_CLAUDE_CLI", None)
        self.nang()
        chay = ChayGia()
        with mock.patch.object(antoan.subprocess, "run", side_effect=chay):
            self.assertTrue(antoan._kiem_cli("claude"))
        self.assertEqual(chay.lenh[0][0], dg._cli("claude"))                      # 06 điểm kiểm đúng bản đang dùng


class KiemSoatCDA(Nen):
    """CDA KT-Y46-1: P1 (tạm dừng giữa lúc nâng), K1 chiều ngược, P2, P4, P5."""

    def test_p1_quay_ve_giua_luc_nang_khong_mat_co_tam_dung(self):
        chay = ChayGia()
        goc = chay.__call__

        def npm_xong_thi_quay_ve(lenh, **kw):
            r = goc(lenh, **kw)
            if lenh[0] == "npm":
                nangcli.tam_dung("0.8.3", self.dl)                                # quay về đúng lúc npm đang chạy
            return r
        kq, _ = self.nang(chay=npm_xong_thi_quay_ve)
        self.assertEqual(kq["kq"], "dat")
        d = nangcli.doc_trangthai(self.dl)
        self.assertEqual((d["tam_dung"], d["claude"]["dang"]), (True, "2.1.340"))   # cờ tạm dừng còn
        self.assertIsNone(nangcli.duong_cli("claude", self.dl))

    def test_k1_cap_nhat_cho_khi_dang_nang(self):
        dem = {"n": 0}

        def dang():
            dem["n"] += 1
            return "claude" if dem["n"] <= 2 else None
        with mock.patch.object(nangcli, "dang_nang", side_effect=dang), \
                mock.patch.object(capnhat.time, "sleep") as ngu, \
                mock.patch("maychu.dulieu.saoluu.chay", side_effect=RuntimeError("dừng sau khi chờ")):
            capnhat._sao_roi_gui("hethong", "0.8.5", self.dl)
        self.assertEqual(ngu.call_count, 2)                                       # chờ đúng lúc bộ nâng còn chạy
        self.assertEqual(dem["n"], 3)

    def test_p2_khong_tai_ban_bang_hoac_thap_hon_ban_trong_goi(self):
        self.nang(npm={"ban": "2.1.340"}, ngay=True)
        nangcli._GOC["claude"] = "2.1.345"                                       # lên bản IGM360 có CLI cao hơn
        kq, chay = self.nang(npm={"ban": "2.1.344"}, ngay=True)
        self.assertEqual(kq, {"kq": "moi_nhat", "ban": "2.1.345"})
        self.assertEqual([l for l in chay.lenh if l[0] == "npm"], [])

    def test_p4_khong_nho_ket_qua_none(self):
        nangcli._GOC.clear()
        tra = iter([None, "2.1.331"])
        with mock.patch.object(nangcli, "ban_cua", side_effect=lambda *a: next(tra)):
            self.assertIsNone(nangcli.ban_trong_goi("claude"))
            self.assertEqual(nangcli.ban_trong_goi("claude"), "2.1.331")         # hỏi lại, không nhớ None

    def test_p5_dang_co_viec_ai_thi_chua_xoa_ban_cu(self):
        for ban in ("2.1.340", "2.1.341"):
            self.nang(npm={"ban": ban}, ngay=True)
        with mock.patch.object(capnhat, "so_viec_ai_dangchay", return_value=1):
            self.nang(npm={"ban": "2.1.342"}, ngay=True)
        con = sorted(p.name for p in (nangcli.thumuc_cli(self.dl) / "claude").iterdir())
        self.assertEqual(con, ["2.1.340", "2.1.341", "2.1.342"])                 # chưa xóa bản trước-trước
        self.nang(npm={"ban": "2.1.342"}, ngay=True)                              # lượt sau, không còn việc AI
        con = sorted(p.name for p in (nangcli.thumuc_cli(self.dl) / "claude").iterdir())
        self.assertEqual(con, ["2.1.341", "2.1.342"])


class KiemLichChuong(Nen):
    """Việc 7 (QĐ271): 03:00 mỗi ngày, kiểm khi bật lại; chuông Z20 dòng 14, 15."""

    def doc_chuong(self):
        from maychu.hethong.giamsat import thongbao
        for ten in ketnoi.CAC_FILE:
            cn = ketnoi.mo(ten, self.dl)
            try:
                co = cn.execute("SELECT 1 FROM sqlite_master WHERE name = 'canhbao'").fetchone()
                if co:
                    dong = cn.execute("SELECT khoa_chongtrung, giatri, nguong FROM canhbao WHERE khoa_chongtrung LIKE 'cli_%'"
                                      " AND trangthai IN ('moi', 'dabao', 'dagiao_task')").fetchall()
                    return [r[0] for r in dong], {k: thongbao._chu(k.split(":")[0], k, {"giatri": gt, "nguong": ng}, {}, {})
                                                  for k, gt, ng in dong}
            finally:
                cn.close()
        return [], {}

    def test_chuong_nang_xong_va_loi_dung_chu_z20(self):
        from maychu.hethong.giamsat import thongbao
        self.assertEqual(thongbao.LOAI["cli_loi"][:2], ("xem", "circle-alert"))   # QĐ271: vàng
        self.assertEqual(thongbao.LOAI["cli_nang"][:2], ("tin", "wrench"))
        self.nang(npm={"ban": "2.1.340"}, ngay=True)
        ds, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Đã nâng Claude · Code lên 2.1.340"])
        self.nang(npm={"ban": "2.1.341"}, ngay=True, chay=ChayGia(ban_cai="2.1.0"))
        ds, chu = self.doc_chuong()
        self.assertIn("Claude · Code 2.1.341 chưa đạt kiểm thử, đã về bản 2.1.340", chu.values())
        self.nang(npm={"ban": "2.1.342"}, ngay=True)
        ds, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Đã nâng Claude · Code lên 2.1.342"])  # lỗi cũ, nâng cũ tự đóng

    def test_luot_hang_ngay_01_lan_moi_ngay_loi_mang_khong_dung_goi_kia(self):
        self.assertFalse(nangcli.da_kiem_hom_nay(BAY, self.dl))

        def hoi(goi, client=None):
            if goi == "claude":
                raise httpx.ConnectError("mất mạng")
            return {"ban": "0.172.0", "ra_luc": (BAY - timedelta(days=3)).isoformat(), "co_giai_nen": 0}
        with mock.patch.object(nangcli, "hoi_npm", side_effect=hoi):
            ra = nangcli.luot_hang_ngay(self.dl, BAY)
        self.assertEqual((ra["claude"]["kq"], ra["chatgpt"]["kq"]), ("loi", "moi_nhat"))
        self.assertTrue(nangcli.da_kiem_hom_nay(BAY, self.dl))
        self.assertFalse(nangcli.da_kiem_hom_nay(BAY + timedelta(days=1), self.dl))
        self.assertEqual(len(self.f04("hoi_loi")), 1)

    def test_lich_goi_tu_03_gio_va_khi_bat_lai(self):
        lich = (Path(__file__).resolve().parents[2] / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("if bay_gio.hour >= nangcli.GIO_KIEM and not nangcli.da_kiem_hom_nay(bay_gio) and not dang_kiem_cli():",
                      lich)
        self.assertEqual(nangcli.GIO_KIEM, 3)
        # CDA L1: chuông sao lưu quét ngay sau dọn bản sao trước khi nâng (như trước Y46)
        self.assertIn("await asyncio.to_thread(saoluu.don_truoc_nangcap)   # D1 (QĐ281): mốc 30 ngày tự đến\n"
                      "                await asyncio.to_thread(thongbao.quet_saoluu)", lich)

    def test_l2_vong_lich_khong_cho_luot_kiem_cong_cu_ai(self):
        """CDA L2: lượt kiểm chạy thành việc nền; vòng lịch chạy tiếp 05 vòng trong khi lượt kiểm còn treo, không chạy chồng."""
        from maychu.hethong.giamsat import lich
        cho, goi, vong, ngu_that = threading.Event(), [], [0], asyncio.sleep

        def luot(*_a, **_k):
            goi.append(1)
            cho.wait(10)
            return {}

        async def ngu(_giay):
            vong[0] += 1
            await ngu_that(0.05)
            if vong[0] >= 5:
                self.assertFalse(cho.is_set())        # lượt kiểm vẫn đang treo
                cho.set()
                await ngu_that(0.05)
                raise asyncio.CancelledError

        with mock.patch.object(lich.asyncio, "sleep", ngu), mock.patch.object(lich.domay, "ghi_n02"), \
                mock.patch.object(lich.thongbao, "quet_maychu"), mock.patch.object(lich.capnhat, "xu_ly_cho"), \
                mock.patch.object(lich.saoluu, "da_co_hom_nay", return_value=True), \
                mock.patch.object(lich.thongbao, "quet", return_value={}), mock.patch.object(lich.thongbao, "quet_banmoi"), \
                mock.patch.object(lich.congai, "quet_codex"), mock.patch.object(lich.drive, "day_hang_cho", return_value={}), \
                mock.patch.object(nangcli, "GIO_KIEM", 0), mock.patch.object(nangcli, "da_kiem_hom_nay", return_value=False), \
                mock.patch.object(nangcli, "luot_hang_ngay", luot):
            try:
                asyncio.run(lich.chay_mai())
            except asyncio.CancelledError:
                pass
        self.assertEqual(vong[0], 5)
        self.assertEqual(goi, [1])                    # 01 lượt, không chạy chồng dù hôm nay "chưa kiểm"


class KiemConTroCu(Nen):
    def test_duong_cli_va_k3_ban_trong_goi_cao_hon(self):
        self.assertIsNone(nangcli.duong_cli("claude", self.dl))                   # chưa nâng: bản trong gói
        self.nang()
        p = nangcli.duong_cli("claude", self.dl)
        self.assertTrue(p and p.endswith(str(Path("claude", "2.1.340", "node_modules", ".bin", "claude"))))
        nangcli._GOC["claude"] = "2.1.350"                                       # lên bản IGM360 mới có CLI cao hơn
        self.assertIsNone(nangcli.duong_cli("claude", self.dl))                   # K3: dùng bản cao hơn (trong gói)

    def test_tam_dung_qd264_va_mo_lai(self):
        self.nang()
        nangcli.tam_dung("0.8.3", self.dl)
        self.assertIsNone(nangcli.duong_cli("claude", self.dl))                   # QĐ264: dùng bản trong gói
        nangcli.mo_lai(self.dl)
        self.assertIsNotNone(nangcli.duong_cli("claude", self.dl))
        self.assertEqual(len(self.f04("tam_dung")), 1)

    def test_ve_ban_truoc(self):
        self.nang(npm={"ban": "2.1.340"}, ngay=True)
        self.nang(npm={"ban": "2.1.341"}, ngay=True)
        kq = nangcli.ve_ban_truoc("claude", self.dl)
        self.assertEqual(kq, {"kq": "ve", "tu": "2.1.341", "ve": "2.1.340"})
        self.assertIn("2.1.341", nangcli.doc_trangthai(self.dl)["claude"]["hong"])   # Z20 dòng 11: không tự nâng lại
        self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl)["ve"], None)     # về tiếp: bản trong gói


class KiemChuongQd307(KiemLichChuong):
    """QĐ307 (anh "Duyệt A"): chữ nguyên văn bảng chữ Z20 dòng 15b, 18, 19; dòng 20 không mở chuông."""

    def test_15b_ve_ban_trong_goi_co_so_va_khong_so(self):
        kq, _ = self.nang(chay=ChayGia(ban_cai="2.1.0"), ngay=True)              # chưa nâng lần nào: giữ bản trong gói
        self.assertEqual(kq["kq"], "hong")
        _, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Claude · Code 2.1.340 chưa đạt kiểm thử, đã về bản 2.1.331 trong gói"])
        with mock.patch.object(nangcli, "ban_trong_goi", return_value=None):  # không đọc được số bản trong gói
            self.nang(npm={"ban": "2.1.341"}, chay=ChayGia(ban_cai="2.1.0"), ngay=True)
            _, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Claude · Code 2.1.341 chưa đạt kiểm thử, đã về bản trong gói"])

    def test_18_thieu_o_trong_so_do_that_mo_01_lan_o_du_tu_dong(self):
        gb = 1024 ** 3
        with mock.patch.object(antoan, "o_trong", return_value={"can": int(1.5 * gb) - 1000}), \
                mock.patch.object(nangcli.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(10 * gb, 9 * gb, int(1.1 * gb))):
            self.assertEqual(self.nang(ngay=True)[0]["kq"], "thieu_o")
            self.assertEqual(self.nang(ngay=True)[0]["kq"], "thieu_o")         # lần 02: không mở thêm chuông
            ds, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Chưa nâng Claude · Code lên 2.1.340: ổ trống còn 1,1 GB, cần 1,5 GB."
                                              " Dọn ổ máy chủ; phần mềm tự thử lại lúc 03:00."])
        from maychu.hethong.giamsat import thongbao
        self.assertEqual(thongbao.LOAI[ds[0].split(":")[0]][:2], ("xem", "hard-drive"))   # vàng, icon hard-drive
        self.assertEqual(self.nang(ngay=True)[0]["kq"], "dat")                  # ổ đủ: chuông tự đóng
        self.assertEqual([c for c in self.doc_chuong()[1].values() if c.startswith("Chưa nâng")], [])

    def test_19_khong_ket_noi_duoc_hang_mo_01_chuong_hoi_lai_duoc_thi_dong(self):
        def mat_mang(goi, client=None):
            raise httpx.ConnectError("mất mạng")
        with mock.patch.object(nangcli, "hoi_npm", side_effect=mat_mang):
            nangcli.luot_hang_ngay(self.dl, BAY)
        ds, chu = self.doc_chuong()
        self.assertEqual(list(chu.values()), ["Chưa kiểm được bản mới của công cụ AI: không kết nối được máy chủ của hãng."
                                              " Công cụ AI vẫn chạy bản đang dùng; phần mềm tự thử lại lúc 03:00."])   # 01 chuông cho 02 gói
        from maychu.hethong.giamsat import thongbao
        self.assertEqual(thongbao.LOAI["cli_mang"][:2], ("xem", "wifi-off"))
        self.nang(npm={"ban": "2.1.331"})                                         # hỏi lại được: tự đóng
        self.assertEqual(self.doc_chuong()[0], [])

    def test_20_hoan_khong_mo_chuong(self):
        from maychu.hethong.mohinh import congai
        self.trang_thai.return_value = {"da_noi": True}
        with mock.patch.object(congai, "_goi_claude", side_effect=congai.HetHanMuc("hết hạn mức", {})):
            self.assertEqual(self.nang(ngay=True)[0]["kq"], "hoan")
        self.assertEqual(self.doc_chuong()[0], [])
        sk = nangcli.doc_trangthai(self.dl)["claude"]["su_kien"]
        self.assertEqual((sk["loai"], sk["ban"], sk["giu"], sk["giu_goi"]), ("hoan", "2.1.340", "2.1.331", True))


class KiemDuongGoiKhoi(Nen):
    """Việc 8: dữ liệu khối Công cụ AI, nút Nâng công cụ AI chạy nền, nút Về bản trước."""

    def test_xem_du_truong_va_ban_dang_dung(self):
        c = nangcli.xem(self.dl)
        self.assertEqual((c["bat"], c["tam_dung"], c["gio_kiem"], c["cho_gio"], c["dang_nang"], c["chan"]), (True, False, 3, 24, None, None))
        g = c["goi"][0]
        self.assertEqual((g["goi"], g["ten"], g["ban"], g["trong_goi"], g["ban_goi"]), ("claude", "Claude · Code", "2.1.331", True, "2.1.331"))
        self.nang(ngay=True)
        g = nangcli.xem(self.dl)["goi"][0]
        self.assertEqual((g["ban"], g["trong_goi"], g["hang"]["ban"], g["hang"]["uoc_chu"], g["su_kien"]["loai"]),
                         ("2.1.340", False, "2.1.340", antoan.chu_dungluong(1000), "dat"))
        self.assertEqual((g["truoc"], g["truoc_goi"], g["ban_goi"]), (None, True, "2.1.331"))   # CDO U36 chỗ 12

    def test_nut_nang_chay_nen_va_bi_chan(self):
        goc = nangcli.nang                                                         # luồng nền gọi nang(): trỏ npm, CLI giả

        def nang_gia(goi, thumuc=None, **kw):
            return goc(goi, thumuc, chay=ChayGia(), client=npm_gia(ra=BAY - timedelta(hours=2)), bay=BAY, **kw)
        with mock.patch.object(nangcli, "nang", nang_gia):
            kq = nangcli.nang_nen("claude", self.dl, nguoi=None)
            self.assertEqual(kq, {"bat_dau": True, "goi": "claude"})
            nangcli._LUONG["t"].join(10)
        self.assertEqual(nangcli.doc_trangthai(self.dl)["claude"]["dang"], "2.1.340")   # bỏ qua 24 giờ, bỏ qua công tắc
        with mock.patch.object(capnhat, "dang_cho", return_value=True):
            self.assertEqual(nangcli.nang_nen("claude", self.dl), {"loi": "dang_cap_nhat"})
        nangcli._KHOA.acquire()
        try:
            nangcli._DANG["goi"] = "claude"
            self.assertEqual(nangcli.nang_nen("claude", self.dl), {"loi": "dang_nang"})
            self.assertEqual(nangcli.xem(self.dl)["dang_nang"]["goi"], "claude")
            self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl), {"kq": "khong_chay", "ly_do": "dang_nang"})   # không chờ
        finally:
            nangcli._DANG["goi"] = None
            nangcli._KHOA.release()

    def test_a1_dang_nang_tinh_ca_luong_vua_bam(self):
        """CDA KT-Y46-4 A1: nút vừa bấm, luồng nâng chưa tới bước khóa → dang_nang() đã báo (cập nhật phần mềm chờ)."""
        cho = threading.Event()
        t = threading.Thread(target=cho.wait, args=(10,), daemon=True)
        cu = dict(nangcli._LUONG)
        nangcli._LUONG.update(t=t, goi="chatgpt")
        t.start()
        try:
            self.assertIsNone(nangcli._DANG["goi"])
            self.assertEqual(nangcli.dang_nang(), "chatgpt")
        finally:
            cho.set()
            t.join(5)
            nangcli._LUONG.clear()
            nangcli._LUONG.update(cu)
        self.assertIsNone(nangcli.dang_nang())

    def test_a2_ve_ban_truoc_bi_chan_o_che_do_an_toan_va_co_quay_ve(self):
        """CDA KT-Y46-4 A2 (QĐ218 dòng 37: chế độ an toàn chỉ mở Cập nhật, việc ghi khác bị chặn)."""
        self.nang(ngay=True)
        truoc = nangcli.doc_trangthai(self.dl)
        antoan.CHE_DO["an_toan"] = True
        self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl), {"kq": "khong_chay", "ly_do": "che_do_an_toan"})
        antoan.CHE_DO["an_toan"] = False
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.8.4", "ban_truoc": "0.8.3"})
        self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl), {"kq": "khong_chay", "ly_do": "co_quay_ve"})
        self.assertEqual(nangcli.doc_trangthai(self.dl), truoc)                   # không ghi gì
        self.assertEqual(self.f04("ve"), [])
        antoan.ghi(self.dl, chay_ban_truoc=None)
        self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl)["kq"], "ve")    # hết chặn: về được

    def test_ve_ban_truoc_ghi_su_kien_khong_tu_nang_lai(self):
        self.nang(ngay=True)
        kq = nangcli.ve_ban_truoc("claude", self.dl)
        self.assertEqual(kq, {"kq": "ve", "tu": "2.1.340", "ve": None})
        g = nangcli.xem(self.dl)["goi"][0]
        self.assertEqual((g["ban"], g["trong_goi"], g["ve_tay"], g["su_kien"]["giu"], g["su_kien"]["giu_goi"]),
                         ("2.1.331", True, ["2.1.340"], "2.1.331", True))
        self.assertEqual(self.nang(ngay=True)[0]["kq"], "da_hong")               # không tự nâng lại
        self.assertEqual(nangcli.ve_ban_truoc("claude", self.dl), {"kq": "khong_co"})

    def test_qd308_10_xem_tra_ban_dang_cap_nhat_len(self):
        from maychu.hethong import tiendo
        with mock.patch.object(nangcli, "chan_vi", return_value="dang_cap_nhat"), \
                mock.patch.object(tiendo, "doc", return_value={"den": "0.8.4"}):
            c = nangcli.xem(self.dl)
        self.assertEqual((c["chan"], c["cap_nhat_len"]), ("dang_cap_nhat", "0.8.4"))

    def test_duong_goi_api(self):
        api = (Path(__file__).resolve().parents[2] / "maychu/web/api.py").read_text(encoding="utf-8")
        for x in ('@router.get("/capnhat/congcu_ai")', '@router.post("/capnhat/congcu_ai/nang")', '@router.post("/capnhat/congcu_ai/ve")',
                  "nangcli.nang_nen(body.goi, nguoi=p[\"nguoidung_id\"])", "nangcli.ve_ban_truoc(body.goi, nguoi=p[\"nguoidung_id\"])"):
            self.assertIn(x, api)
        self.assertTrue(antoan.duoc_mo("/api/capnhat/congcu_ai"))                 # chế độ an toàn: xem được (nâng bị K1 chặn)


class KiemGiaoDienKhoi(unittest.TestCase):
    """Việc 8 (Z20 dòng 1–13, 20; QĐ307 dòng 10, 11): chạy hàm vẽ khối bằng node, so nguyên văn chữ đã duyệt."""
    BAY = "2026-11-24T14:30:00+07:00"

    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise unittest.SkipTest("máy không có node")
        app = (Path(__file__).resolve().parents[2] / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        cls.ma = app[app.index("// <CA>"):app.index("// </CA>")]
        cls.app = app

    def ve(self, *ca, bay=None):
        dau = ("const esc = x => String(x ?? ''), cum = x => String(x);\n"
               "const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);\n"
               "const ngay = iso => { if (!iso) return ''; const [y, m, d] = iso.slice(0, 10).split('-'); return d + '/' + m + '/' + y; };\n"
               "const icoMau = (s, mau, co) => '<i ' + s + ' m=' + mau + '></i>';\n"
               "const svgLucide = t => t;\n"
               "const ICON = {wrench: 'wrench', loader: 'loader', 'rotate-ccw': 'rotate-ccw', clock: 'clock', 'circle-check': 'circle-check', 'circle-alert': 'circle-alert'};\n")
        chay = dau + self.ma + f"const bay = Date.parse('{bay or self.BAY}');\nconsole.log(JSON.stringify({json.dumps(list(ca))}.map(c => htmlCongCu(c, bay))));\n"
        ra = subprocess.run(["node", "-e", chay], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        self.tho = json.loads(ra.stdout)                                          # bản gốc (có dấu cách không ngắt)
        h = [x.replace("\u00a0", " ").replace("&nbsp;", " ") for x in self.tho]   # so chữ như dấu cách thường
        for x in h:
            self.assertNotIn("undefined", x)
            self.assertNotIn("null", x)
        return h

    def chu(self, cau):
        ra = subprocess.run(["node", "-e", "const hai = n => String(n), ngay = iso => { const [y, m, d] = iso.slice(0, 10).split('-'); return d + '/' + m + '/' + y; };\nconst svgLucide = t => t, ICON = {};\n" + self.ma
                             + f"console.log(JSON.stringify({cau}));"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        return json.loads(ra.stdout.replace("\u00a0", " "))

    @staticmethod
    def goi(**kw):
        g = {"goi": "claude", "ten": "Claude · Code", "ban": "2.1.331", "trong_goi": False, "ban_goi": "2.1.300", "truoc": "2.1.329",
             "hang": {"ban": "2.1.331", "ra_luc": "2026-11-20T03:00:00Z", "uoc": 193986560, "uoc_chu": "185 MB"}, "hong": [], "ve_tay": [],
             "nang_luc": "2026-11-23T06:00:00+07:00", "lan_cuoi": "2026-11-24T03:00:00+07:00", "su_kien": None}
        g.update(kw)
        return g

    def khoi(self, *goi, **kw):
        c = {"bat": True, "tam_dung": False, "tam_dung_ban": None, "kiem_ngay": "2026-11-24", "gio_kiem": 3, "cho_gio": 24, "chan": None,
             "dang_nang": None, "goi": list(goi) or [self.goi(), self.goi(goi="chatgpt", ten="ChatGPT · Codex", ban="0.172.0", truoc="0.171.0",
                                                                  hang={"ban": "0.172.0", "ra_luc": "2026-11-20T00:00:00Z"})]}
        c.update(kw)
        return c

    def test_dong_1_den_5_moi_nhat(self):
        h, = self.ve(self.khoi())
        for x in ("Công cụ AI", "Tự nâng mỗi ngày", "Công cụ chạy gói Claude, gói ChatGPT trên máy chủ. Chỉ nhận bản hãng đã ra từ 24 giờ,"
                  " kiểm thử đạt mới dùng; chưa đạt thì tự về bản trước.", "<span>Công cụ</span><span>Bản đang dùng</span><span>Bản mới của hãng</span>"
                  "<span>Nâng gần nhất</span>", "bản trước 2.1.329", ">Đã mới nhất<", "23/11/2026 06:00", "Về bản trước",
                  "Đang dùng bản mới nhất. Lần kiểm tới: 03:00 ngày mai.", 'title="Đang dùng bản mới nhất"', 'aria-checked="true"'):
            self.assertIn(x, h)
        self.assertNotIn("data-canang", h)                                        # mới nhất: nút khoá

    def test_dong_6_7_hang_co_ban_moi(self):
        moi = self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"})
        h, = self.ve(self.khoi(moi))
        self.assertIn("Claude · Code có bản 2.1.332 (ra lúc 10:00 hôm nay). Tự nâng khi bản ra đủ 24 giờ, sau 10:00 ngày mai.", h)
        self.assertIn("Muốn có ngay thì bấm Nâng công cụ AI.", h)
        self.assertIn("ra lúc 10:00 hôm nay", h)
        self.assertIn('data-canang="claude"', h)
        hop = self.chu("[CA.hopTieu('Claude · Code', '2.1.332'), CA.hopChu(true, '185 MB', '2.1.331')]")
        self.assertEqual(hop, ["Nâng Claude · Code lên 2.1.332?", "Bản này ra chưa đủ 24 giờ. Phần mềm tải khoảng 185 MB, kiểm thử rồi mới dùng;"
                               " chưa đạt thì tự về bản 2.1.331. AI vẫn chạy trong lúc nâng."])
        self.assertIn("xacnhan(CA.hopTieu(x.ten, h.ban), cum(CA.hopChu(chua24, h.uoc_chu, caBan(x.ban, x.trong_goi))), CA.nut,", self.app)

    def test_dong_8_dang_nang(self):
        moi = self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"})
        h, = self.ve(self.khoi(moi, dang_nang={"goi": "claude", "ban": "2.1.332", "cu": "2.1.331", "cu_goi": False}))
        self.assertIn("Đang nâng Claude · Code lên 2.1.332: tải và kiểm thử.", h)
        self.assertIn("Trong lúc nâng, AI vẫn chạy bằng bản 2.1.331.", h)        # QĐ309 đổi câu dòng 8 (A)
        self.assertIn('<div class="tdf chay"></div>', h)
        self.assertIn("disabled>loaderĐang nâng…</button>", h)
        self.assertNotIn("data-cave", h)

    def test_dong_9_10_11_su_kien_hom_nay(self):
        sk = lambda **k: {"luc": "2026-11-24T14:20:00+07:00", "ban": "2.1.332", **k}
        dat, lui, lui_goi, lui_khong_so, ve, ve_goi = self.ve(
            self.khoi(self.goi(ban="2.1.332", truoc="2.1.331", su_kien=sk(loai="dat"))),
            self.khoi(self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z"}, hong=["2.1.332"], su_kien=sk(loai="hong", giu="2.1.331", giu_goi=False))),
            self.khoi(self.goi(ban="2.1.300", trong_goi=True, truoc=None, su_kien=sk(loai="hong", giu="2.1.300", giu_goi=True))),
            self.khoi(self.goi(ban="2.1.300", trong_goi=True, truoc=None, su_kien=sk(loai="hong", giu=None, giu_goi=True))),
            self.khoi(self.goi(truoc=None, hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z"}, hong=["2.1.332"], ve_tay=["2.1.332"],
                               su_kien=sk(loai="ve", luc="2026-11-24T14:25:00+07:00", giu="2.1.331", giu_goi=False))),
            self.khoi(self.goi(ban="2.1.300", trong_goi=True, truoc=None, su_kien=sk(loai="ve", luc="2026-11-24T14:25:00+07:00", giu="2.1.300", giu_goi=True))))
        self.assertIn("Đã nâng Claude · Code lên 2.1.332 lúc 14:20 · kiểm thử đạt.", dat)
        self.assertIn("Claude · Code 2.1.332 kiểm thử chưa đạt, đã tự về bản 2.1.331.", lui)
        self.assertIn("AI vẫn chạy bình thường. Bản 2.1.332 không thử lại. Lỗi đã ghi nhật ký và báo chuông.", lui)
        self.assertIn("chưa đạt, không dùng", lui)
        self.assertIn("Claude · Code 2.1.332 kiểm thử chưa đạt, đã tự về bản 2.1.300 trong gói.", lui_goi)     # QĐ307 dòng 10
        self.assertIn("Claude · Code 2.1.332 kiểm thử chưa đạt, đã tự về bản trong gói.", lui_khong_so)
        self.assertIn("Đã về Claude · Code bản 2.1.331 lúc 14:25. Bản 2.1.332 không tự nâng lại.", ve)
        self.assertIn("không tự nâng lại", ve)
        self.assertIn("Đã về Claude · Code bản 2.1.300 trong gói lúc 14:25. Bản 2.1.332 không tự nâng lại.", ve_goi)   # QĐ307 dòng 11
        self.assertIn("2.1.300 · trong gói", ve_goi)
        self.assertNotIn("data-cave", ve_goi)                                     # đang dùng bản trong gói: không còn bản để về
        hop = self.chu("[CA.veTieu('Claude · Code', '2.1.331'), CA.veChu('2.1.332', '2.1.331'), CA.veTieu('Claude · Code', caBan('2.1.300', true)),"
                       " CA.veChu('2.1.332', caBan('2.1.300', true)), caBan(null, true)]")
        self.assertEqual(hop, ["Về Claude · Code bản 2.1.331?", "Bản 2.1.332 không tự nâng lại. Lượt AI mới dùng bản 2.1.331 ngay.",
                               "Về Claude · Code bản 2.1.300 trong gói?", "Bản 2.1.332 không tự nâng lại. Lượt AI mới dùng bản 2.1.300 trong gói ngay.",
                               "trong gói"])

    def test_dong_12_13_20(self):
        moi = self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"})
        tat, tam, hoan = self.ve(
            self.khoi(moi, bat=False),
            self.khoi(self.goi(ban="2.1.300", trong_goi=True, truoc=None, hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"}),
                      tam_dung=True, tam_dung_ban="0.2.0"),
            self.khoi(self.goi(su_kien={"loai": "hoan", "luc": "2026-11-24T03:01:00+07:00", "ban": "2.1.332", "giu": "2.1.331", "giu_goi": False})))
        self.assertIn("Tự nâng đang tắt. Hãng có bản mới thì hiện ở đây; bạn bấm Nâng công cụ AI để nâng.", tat)
        self.assertIn('aria-checked="false"', tat)
        self.assertIn('data-canang="claude"', tat)                                # tắt: vẫn bấm nâng được
        self.assertIn("Tự nâng tạm dừng: bạn đã quay về bản 0.2.0, công cụ AI dùng bản trong gói của bản này.", tam)
        self.assertIn("Bật lại: gạt công tắc Tự nâng mỗi ngày, hoặc cập nhật lên bản mới.", tam)
        self.assertIn("2.1.300 · trong gói", tam)
        self.assertIn('aria-checked="false"', tam)
        self.assertNotIn("data-canang", tam)                                      # nút nâng khoá
        self.assertIn("Hoãn nâng Claude · Code 2.1.332: gói Claude đang hết hạn mức nên chưa kiểm thử được. Vẫn dùng bản 2.1.331;"
                      " lượt kiểm 03:00 ngày mai thử lại.", hoan)
        self.assertIn("<i clock m=#646A73>", hoan)                                # dòng xám, icon clock

    def test_cdo_u36_cho_1_ngay_khac_va_khac_nam(self):
        h = self.chu("[caLuc(Date.parse('2026-11-23T03:00:00Z'), Date.parse('2026-11-24T14:30:00+07:00')),"
                     " caLuc(Date.parse('2025-12-30T03:00:00Z'), Date.parse('2026-01-02T14:30:00+07:00')),"
                     " caLuc(Date.parse('2026-11-25T03:00:00Z'), Date.parse('2026-11-24T14:30:00+07:00'))]")
        self.assertEqual(h, ["10:00 ngày 23/11", "10:00 ngày 30/12/2025", "10:00 ngày mai"])

    def test_cdo_u36_cho_12_ban_truoc_trong_goi(self):
        h, = self.ve(self.khoi(self.goi(ban="2.1.340", truoc=None, truoc_goi=True)))
        self.assertIn("bản trước 2.1.300 trong gói", h)

    def test_cdo_u36_l1_l3_khong_ngat_cum(self):
        sk = {"loai": "hoan", "luc": "2026-11-24T03:01:00+07:00", "ban": "2.1.332", "giu": "2.1.331", "giu_goi": False}
        self.ve(self.khoi(self.goi(su_kien=sk)), self.khoi(self.goi(ban="2.1.332", su_kien={"loai": "dat", "luc": "2026-11-24T14:20:00+07:00", "ban": "2.1.332"})),
                self.khoi(self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"})))
        hoan, dat, cho = self.tho
        self.assertIn("lượt kiểm 03:00 ngày&nbsp;mai thử lại.", hoan)                 # L1
        self.assertIn("lúc 14:20 · kiểm&nbsp;thử&nbsp;đạt.", dat)                        # L3
        self.assertIn("10:00 hôm nay", cho)
        self.assertIn("10:00 ngày mai", cho)

    def test_cdo_u36_l2_nut_chinh_44_diem_anh_tren_dien_thoai(self):
        html = (Path(__file__).resolve().parents[2] / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        self.assertIn("body.dien-thoai #khoi-cl .btn-chu,body.dien-thoai #khoi-cl .nut-gat,body.dien-thoai #khoi-cl .btn{min-height:44px", html)
        self.assertIn("#khoi-cl .btn-chu,#khoi-cl .nut-gat,#khoi-cl .btn{min-height:44px;min-width:44px;align-items:center}}", html)

    def test_so_ngan_nghin(self):   # QĐ311 G3 + QĐ312 (bỏ số 0 thừa)
        g, m = 1024 ** 3, 1024 ** 2
        self.assertEqual([antoan.chu_dungluong(x) for x in (1.0 * g, 1.2 * g, 819 * m, 9315.2 * g, 1250 * g, 999 * m, 1000 * m, 1023 * m, 0)],
                         ["1 GB", "1,2 GB", "819 MB", "9.315,2 GB", "1.250 GB", "999 MB", "1 GB", "1 GB", "0 MB"])

    def test_qd308_4_chua_nang(self):
        h, = self.ve(self.khoi(self.goi(nang_luc=None, su_kien=None)))
        self.assertIn('<span data-l="Nâng gần nhất">Chưa nâng</span>', h)

    def test_qd308_6_dong_ket_qua_hien_toi_luot_kiem_03_gio_ke_tiep(self):
        sk = {"loai": "dat", "luc": "2026-11-23T14:20:00+07:00", "ban": "2.1.332"}
        k = self.khoi(self.goi(ban="2.1.332", su_kien=sk), kiem_ngay="2026-11-23")
        truoc, sau = self.ve(k, bay="2026-11-24T02:59:00+07:00")[0], self.ve(k, bay="2026-11-24T03:01:00+07:00")[0]
        self.assertIn("Đã nâng Claude · Code lên 2.1.332 lúc 14:20 · kiểm thử đạt.", truoc)   # qua ngày, chưa tới 03:00: còn
        self.assertNotIn("Đã nâng", sau)                                               # qua lượt 03:00: về dòng 5
        self.assertIn("Đang dùng bản mới nhất.", sau)

    def test_qd308_10_nut_khoa_re_chuot_cau_san_co(self):
        moi = self.goi(hang={"ban": "2.1.332", "ra_luc": "2026-11-24T03:00:00Z", "uoc_chu": "185 MB"})
        at, cn = self.ve(self.khoi(moi, chan="che_do_an_toan", chan_chu="Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn."),
                         self.khoi(moi, chan="dang_cap_nhat", chan_chu="Đang cập nhật lên 0.8.4"))
        self.assertIn('<button class="btn khoa" disabled title="Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.">', at)
        self.assertIn('<button class="btn khoa" disabled title="Đang cập nhật lên 0.8.4">', cn)
        for h in (at, cn):
            self.assertNotIn("data-canang", h)
            self.assertNotIn("data-cave", h)                                        # CDA A2: không bấm được Về bản trước lúc bị chặn
        self.assertIn('<button class="btn-chu nho qv-khoa" disabled title="Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.">', at)   # QĐ308: khoá, không ẩn
        self.assertIn('<button class="btn-chu nho qv-khoa" disabled title="Đang cập nhật lên 0.8.4">', cn)
        self.assertEqual(at.count("qv-khoa"), 1)                                   # 01 dòng công cụ (khối thử chỉ có Claude)
        self.assertIn("D.ca.chan_chu = D.ca.chan === 'che_do_an_toan' ? CHU_CN.chan", self.app)
        self.assertIn(": D.ca.chan === 'dang_cap_nhat' ? TD8.dang(D.ca.cap_nhat_len || (D.capnhat || {}).ban_moi || '') : '';", self.app)
        self.assertIn("chan: 'Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.',", self.app)   # câu sẵn có QĐ218 dòng 37
        self.assertIn("dang: b => 'Đang cập nhật lên ' + b,", self.app)                                       # câu sẵn có QĐ249

    def test_qd308_11_hoan_truoc_03_gio_hom_nay(self):
        sk = lambda luc: {"loai": "hoan", "luc": luc, "ban": "2.1.332", "giu": "2.1.331", "giu_goi": False}
        som, muon = self.ve(self.khoi(self.goi(su_kien=sk("2026-11-24T02:10:00+07:00"))),
                            self.khoi(self.goi(su_kien=sk("2026-11-24T03:01:00+07:00"))), bay="2026-11-24T02:30:00+07:00")
        self.assertIn("Vẫn dùng bản 2.1.331; lượt kiểm 03:00 hôm nay thử lại.", som)
        self.assertIn("Vẫn dùng bản 2.1.331; lượt kiểm 03:00 ngày mai thử lại.", muon)

    def test_qd308_13_gat_tat_cau_dong_12_hien_ngay(self):
        h, = self.ve(self.khoi(self.goi(ban="2.1.332", su_kien={"loai": "dat", "luc": "2026-11-24T14:20:00+07:00", "ban": "2.1.332"}), bat=False))
        self.assertIn("Tự nâng đang tắt. Hãng có bản mới thì hiện ở đây; bạn bấm Nâng công cụ AI để nâng.", h)
        self.assertNotIn("Đã nâng Claude · Code", h)

    def test_cdo_u37a_l5_khong_ngat_trong_goi(self):
        sk = {"loai": "hong", "luc": "2026-11-24T14:20:00+07:00", "ban": "2.1.332", "giu": "2.1.300", "giu_goi": True}
        self.ve(self.khoi(self.goi(ban="2.1.300", trong_goi=True, truoc=None, su_kien=sk)),
                self.khoi(self.goi(ban="2.1.340", truoc=None, truoc_goi=True)))
        lui, nang = self.tho
        self.assertIn("2.1.300 · trong&nbsp;gói</span>", lui)                       # ô bản đang dùng
        self.assertIn("đã tự về bản 2.1.300 trong&nbsp;gói.", lui)                    # dòng 10
        self.assertIn("bản trước 2.1.300 trong&nbsp;gói", nang)                        # dòng phụ chỗ 12

    def test_qd311_l4_ban_du_24_gio_tu_nang_luot_ke_tiep(self):
        moi = {"ban": "2.1.341", "ra_luc": "2026-11-22T13:38:00Z", "uoc_chu": "185 MB"}   # 20:38 ngày 22/11 giờ Việt Nam
        da_kiem, chua_kiem = self.ve(self.khoi(self.goi(hang=moi)), self.khoi(self.goi(hang=moi), kiem_ngay="2026-11-23"))
        self.assertIn("Claude · Code có bản 2.1.341 (ra lúc 20:38 ngày 22/11). Tự nâng lúc 03:00 ngày mai.", da_kiem)
        self.assertIn("Claude · Code có bản 2.1.341 (ra lúc 20:38 ngày 22/11). Tự nâng lúc 03:00 hôm nay.", chua_kiem)
        self.assertIn("Muốn có ngay thì bấm Nâng công cụ AI.", da_kiem)
        self.assertNotIn("Tự nâng khi bản ra đủ 24 giờ", da_kiem)

    def test_qd311_g2_gom_ban_cu(self):
        ma = self.app[self.app.index("// <G2>"):self.app.index("// </G2>")]
        ds = ["haiku", "sonnet", "opus", "fable", "claude-opus-5-5", "claude-fable-5-2", "claude-sonnet-5-5", "claude-haiku-5-5",
              "claude-fable-5-1", "claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-opus-4-8",
              "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"]                 # danh mục thật 13 mô hình + 04 bí danh
        chay = ma + "const ds = " + json.dumps([{"ma": x, "khoa": "goi_claude|" + x} for x in ds]) + ";\n" \
            "const a = tachBanCu(ds, null), b = tachBanCu(ds, 'goi_claude|claude-opus-4-8');\n" \
            "console.log(JSON.stringify([a.chinh.map(m => m.ma), a.cu.length, b.chinh.map(m => m.ma), b.cu.length]));"
        ra = subprocess.run(["node", "-e", chay], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        chinh, n, chinh_ghim, n_ghim = json.loads(ra.stdout)
        self.assertEqual(chinh, ["haiku", "sonnet", "opus", "fable", "claude-opus-5-5", "claude-fable-5-2", "claude-sonnet-5-5", "claude-haiku-5-5"])
        self.assertEqual(n, 9)                                                    # "Bản cũ (09)" như CDO U37-G2
        self.assertIn("claude-opus-4-8", chinh_ghim)                              # mô hình đang ghim luôn hiện
        self.assertEqual(n_ghim, 8)
        self.assertIn("banCu: n => 'Bản cũ (' + hai(n) + ')'", self.app)
        self.assertIn("const {chinh, cu} = !q && g.nhom === 'goi_claude' ? tachBanCu(hien, dang.m && dang.m.khoa) : {chinh: hien, cu: []};", self.app)
        self.assertIn("if ('mhcu' in d) { MH.cu = !MH.cu; veLaiMh(); return; }", self.app)
        self.assertIn("[data-ivn],[data-mhcu]');", self.app)

    def test_icon_dung_net_ban_ve_va_khung(self):
        for net in ('<line x1="10" x2="10" y1="15" y2="9" />', "'m16 12-4-4-4 4', 'M12 16V8'"):
            self.assertIn(net, self.app)
        html = (Path(__file__).resolve().parents[2] / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="the o" data-s="cn:moinhat coban" id="khoi-cl"></div>', html)
        self.assertIn("else if (S.tab === 'capnhat') { veCapNhat(await api('/capnhat')); await napCongCu(); }", self.app)


class KiemPhanD(Nen):
    """Việc 9, phần D (QĐ265; Z20 dòng 16, 17): danh mục mô hình Claude Code theo tài khoản + bản tối thiểu."""

    def setUp(self):
        super().setUp()
        from maychu.dulieu import maso
        from maychu.hethong.mohinh import danhmuc_mohinh, dangnhap_goi
        self.dm = danhmuc_mohinh
        self.cfg = self.dl / "claude01"
        self.enterContext(mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.cfg)}))
        self.nid = maso.tao()
        cn = ketnoi.mo("Viecnen", self.dl)
        cn.execute("INSERT INTO nguon_ai (id, ma, ten, loai, uutien, hang, cach_goi, trangthai) VALUES (?, 'goi_claude_01',"
                   " 'Gói Claude · tài khoản 01', 'goi', 1, 'anthropic', 'cli', 'dung')", (self.nid,))
        cn.commit()
        cn.close()
        self.enterContext(mock.patch.object(dangnhap_goi, "danh_sach", return_value=[
            {"id": self.nid, "ma": "goi_claude_01", "ten": "Gói Claude · tài khoản 01", "loai": "goi", "hang": "anthropic",
             "goi": "claude", "da_noi": True, "trangthai": "dung"}]))
        danhmuc_mohinh._NHO.clear()
        self.addCleanup(danhmuc_mohinh._NHO.clear)

    def tep(self, ten, surface, models):
        p = self.cfg / "cache" / "model-catalog" / ten
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"version": 2, "catalog": {"surface": surface, "config": {"id": surface, "models": [
            {"id": i, "name": i, "section": "main", "min_claude_code_version": v} for i, v in models]}}}), encoding="utf-8")

    def mohinh(self):
        g = next(x for x in self.dm.danh_sach(self.dl)["nhom"] if x["nhom"] == "goi_claude")
        return {m["ma"]: {k: m.get(k) for k in ("can_nang", "ban_dang", "moi")} for m in g["mohinh"]}

    def test_doc_danh_muc_cc_them_vao_g08_va_xam_khi_can_ban_cao_hon(self):
        self.tep("a-cc.json", "cc", [("claude-opus-5-5", "2.1.280"), ("claude-opus-5-6", "2.1.340"), ("claude-sonnet-5-5", None)])
        self.tep("a-ccd.json", "ccd", [("claude-opus-5-6", "9.9.9"), ("claude-chi-o-ccd", None)])   # có tệp cc: bỏ tệp khác
        self.assertEqual(self.dm._danhmuc_claude(1), {"claude-opus-5-5": "2.1.280", "claude-opus-5-6": "2.1.340", "claude-sonnet-5-5": None})
        mh = self.mohinh()
        self.assertEqual(list(mh), ["haiku", "sonnet", "opus", "fable", "claude-opus-5-5", "claude-opus-5-6", "claude-sonnet-5-5"])
        self.assertEqual(mh["claude-opus-5-6"], {"can_nang": "2.1.340", "ban_dang": "2.1.331", "moi": None})   # Z20 dòng 16
        self.assertEqual(mh["claude-opus-5-5"], {"can_nang": None, "ban_dang": None, "moi": None})
        self.assertEqual(mh["claude-sonnet-5-5"], {"can_nang": None, "ban_dang": None, "moi": None})   # tài liệu 2.1.284 ≤ 2.1.331
        self.assertEqual(mh["opus"], {"can_nang": None, "ban_dang": None, "moi": None})
        self.nang(npm={"ban": "2.1.340"}, ngay=True)                              # công cụ AI nâng xong: tự sáng, nhãn "mới"
        mh = self.mohinh()
        self.assertEqual(mh["claude-opus-5-6"], {"can_nang": None, "ban_dang": None, "moi": True})   # Z20 dòng 17
        self.assertIsNone(mh["claude-opus-5-5"]["moi"])                           # đã dùng được từ trước
        cn = ketnoi.mo("Viecnen", self.dl)
        try:
            self.assertEqual(cn.execute("SELECT count(*) FROM mohinh_ai WHERE nguon_ai_id = ?", (self.nid,)).fetchone()[0], 7)
        finally:
            cn.close()

    def test_truong_trong_dung_bang_tai_lieu_du_phong(self):
        nangcli._GOC["claude"] = "2.1.300"
        self.tep("a-cc.json", "cc", [("claude-fable-5-2", None), ("claude-moi-chua-ro", None)])
        mh = self.mohinh()
        self.assertEqual(mh["claude-fable-5-2"]["can_nang"], "2.1.321")          # tài liệu Anthropic (PTD-14 mục 8.1)
        self.assertIsNone(mh["claude-moi-chua-ro"]["can_nang"])                   # trống cả 02 nơi: dùng được

    def test_chua_co_tep_chi_04_bi_danh_khong_hoi_so_ban(self):
        with mock.patch.object(nangcli, "ban_cli", side_effect=AssertionError("không được hỏi số bản")):
            self.assertEqual(list(self.mohinh()), ["haiku", "sonnet", "opus", "fable"])

    def test_giao_dien_dong_xam_va_nhan_moi(self):
        app = (Path(__file__).resolve().parents[2] / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        for x in ("can: 'Cần nâng công cụ AI', moi: 'mới'",
                  "re: (can, dang) => 'Mô hình mới theo tài khoản. Cần Claude · Code từ ' + can + ', bản đang dùng ' + dang"
                  " + '. Tự dùng được khi công cụ AI nâng xong.'",
                  "if (m.can_nang) return '<div class=\"mh-dong mh-xam\" title=\"' + esc(CHU_D.re(m.can_nang, m.ban_dang))",
                  "(m.moi ? ' <span class=\"mh-moi\">' + CHU_D.moi + '</span>' : '')"):
            self.assertIn(x, app)
        html = (Path(__file__).resolve().parents[2] / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        self.assertIn(".mh-moi{font-size:11px;color:#258832;border:1px solid #258832;border-radius:8px;padding:0 6px;margin-left:4px}", html)


class KiemK4VungChua(Nen):
    """K4 (QĐ263): tệp `kiemthu/vungchua/kiem_nang_cli.py` (bước trong ảnh của dongimage.yml) chạy với thư mục npm giả.
    Chạy thật trên máy GitHub (Linux); Windows không chạy được tệp chạy kiểu shell nên bỏ qua phần chạy."""

    def nap(self):
        import importlib.util
        p = Path(__file__).resolve().parents[1] / "vungchua" / "kiem_nang_cli.py"
        spec = importlib.util.spec_from_file_location("kiem_nang_cli", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def npm_gia(self):
        goc = self.dl / "npm_goc"
        for ten, lenh, ban, chu in (("@anthropic-ai/claude-code", "claude", "2.1.331", "2.1.331 (Claude Code)"),
                                    ("@openai/codex", "codex", "0.172.0", "codex-cli 0.172.0")):
            g = goc / ten
            g.mkdir(parents=True)
            (g / "package.json").write_text(json.dumps({"name": ten, "version": ban, "bin": {lenh: "cli.sh"}}), encoding="utf-8")
            (g / "cli.sh").write_text(f"#!/bin/sh\necho '{chu}'\n", encoding="utf-8")
            (g / "cli.sh").chmod(0o755)
        (goc / "@anthropic-ai" / "claude-code-linux-x64").mkdir()                # gói nhị phân theo máy: chép cả phạm vi
        return goc

    @unittest.skipIf(os.name == "nt", "tệp chạy kiểu shell chỉ chạy trên Linux (máy GitHub)")
    def test_k4_chep_cli_trong_anh_lam_ban_nang_gia(self):
        m = self.nap()
        ra = []
        self.assertEqual(m.chay(self.npm_gia(), self.dl, in_ra=ra.append), 0, ra)
        self.assertEqual(ra, ["Đạt · claude 2.1.331: nâng dat, chạy qua bản nâng được, về bản trước ve",
                              "Đạt · chatgpt 0.172.0: nâng dat, chạy qua bản nâng được, về bản trước ve"])
        self.assertTrue((nangcli.thumuc_cli(self.dl) / "claude" / "2.1.331" / "node_modules" / "@anthropic-ai" / "claude-code-linux-x64").is_dir())
        self.assertEqual(nangcli._GOC, {"claude": "2.1.331", "chatgpt": "0.172.0"})   # trả lại bản trong gói như trước

    def test_k4_thieu_goi_thi_chua_dat_va_chan_npm(self):
        m = self.nap()
        ra = []
        self.assertEqual(m.chay(self.dl / "khong_co", self.dl, in_ra=ra.append), 1)
        self.assertIn("Lỗi: claude: ảnh không có @anthropic-ai/claude-code", ra)
        with self.assertRaises(RuntimeError):
            m._chan_npm("subprocess.Popen", ("npm", ["npm", "install"], None, None))
        with self.assertRaises(RuntimeError):
            m._chan_npm("subprocess.Popen", (None, '"/usr/local/bin/npm" install', None, None))
        m._chan_npm("subprocess.Popen", ("claude", ["claude", "--version"], None, None))   # lệnh khác: cho chạy

    def test_k4_buoc_trong_dongimage(self):
        yml = (Path(__file__).resolve().parents[2] / ".github/workflows/dongimage.yml").read_text(encoding="utf-8")
        self.assertIn("- name: Kiểm bộ nâng công cụ AI trong ảnh", yml)
        self.assertIn('docker exec -i -w /app thu_cli python - < kiemthu/vungchua/kiem_nang_cli.py | tee -a "$GITHUB_STEP_SUMMARY" || kq=$?', yml)
        self.assertLess(yml.index("- name: Kiểm bộ nâng công cụ AI trong ảnh"), yml.index("- name: Đẩy image"))   # chưa đạt thì không đẩy

    def test_version_va_thaydoi_084_nguyen_van_qd309(self):
        goc = Path(__file__).resolve().parents[2]
        self.assertEqual((goc / "VERSION").read_text(encoding="utf-8").strip(), "0.8.4")
        td = (goc / "THAYDOI.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        muc = td[td.index("## 0.8.4\n"):td.index("## 0.8.3\n")]
        self.assertTrue(muc.startswith("## 0.8.4\nTóm tắt: Công cụ AI tự nâng mỗi ngày\nNâng dữ liệu: không\n"))
        self.assertEqual(muc.count("\n- "), 7)
        self.assertIn("- Kiểm thử chưa đạt thì tự về bản trước và không thử lại bản đó; gói AI đang hết hạn mức thì hoãn, lượt kiểm"
                      " sau thử lại.\n", muc)


class KiemLogoChatgptQd319(unittest.TestCase):
    """Y46-7 (QĐ319, thay cách làm QĐ318): logo ChatGPT ở ô chọn mô hình hiện ≈ 16 px trong ô 18 px; tệp logo và mọi bản
    chép giữ nguyên từng byte (QĐ169, QĐ170, Hướng dẫn thương hiệu OpenAI "Use the logo exactly as provided")."""
    GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"

    def test_tep_logo_giu_nguyen(self):
        import hashlib
        tep = (self.GD / "logo" / "chatgpt.svg").read_bytes()
        self.assertEqual((len(tep), hashlib.sha256(tep).hexdigest()[:12]), (2415, "75c1e9fffa5e"))
        ico = (self.GD / "icon.js").read_text(encoding="utf-8")
        d = json.loads(re.search(r'const ICON=(\{.*?\});?\s*\n', ico, re.S).group(1))
        self.assertIn('<svg width="40" height="40" viewBox="0 0 716 716"', d["logo_chatgpt"])   # bản chép 40 px không đổi
        self.assertIn(d["logo_chatgpt"], (self.GD / "index.html").read_text(encoding="utf-8"))  # hộp Thêm nguồn AI

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_o_chon_mo_hinh_hinh_16_px(self):
        js = (self.GD / "app.js").read_text(encoding="utf-8")
        i = js.index("const logoNhom = ")
        ham = js[i:js.index("\nfunction ", i)]
        ico = (self.GD / "icon.js").read_text(encoding="utf-8")
        d = json.loads(re.search(r'const ICON=(\{.*?\});?\s*\n', ico, re.S).group(1))
        chay = ("const ICON = " + json.dumps({k: d[k] for k in ("logo_claude", "logo_chatgpt")}) + "; ICON['key-round'] = '<svg width=\"16\" height=\"16\"></svg>';\n"
                "const icoMau = s => s;\n" + ham + "\nconsole.log(JSON.stringify([logoNhom({goi: 'chatgpt'}), logoNhom({goi: 'claude'}), logoNhom({hang: 'openai'})]));")
        ra = subprocess.run(["node", "-e", chay], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        gpt, cl, khoa = json.loads(ra.stdout)
        self.assertTrue(gpt.startswith('<span class="logo-n"><svg style="flex:none;margin:-7px" width="32" height="32" viewBox="0 0 716 716"'), gpt[:120])
        self.assertTrue(cl.startswith('<span class="logo-n"><svg width="18" height="18" viewBox="0 0 24 24"'), cl[:120])   # Claude không đổi
        self.assertEqual(gpt, khoa)                                               # nhận theo hãng cũng như theo gói
        self.assertIn('fill="black"', gpt)                                        # không đổi màu
        self.assertNotRegex(gpt, r'fill="#|stroke="#')
        co, le = 32, -7
        self.assertEqual(co + 2 * le, 18)                                         # chiếm đúng ô 18 px, không đẩy chữ bên cạnh
        hinh = co * (535.173 - 180.500) / 716                                     # hình thật 180,500–535,173 trong khung 716 (đo cực trị)
        self.assertTrue(15.5 <= hinh <= 17, hinh)                                 # ≈ 15,9 px, khoảng 88% ô (trước: 8,9 px)
        self.assertLessEqual(hinh, 18)                                            # hình không tràn ra ngoài ô


if __name__ == "__main__":
    unittest.main()
