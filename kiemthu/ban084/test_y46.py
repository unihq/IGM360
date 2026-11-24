"""Bài kiểm Y46 (bản 0.8.4; QĐ263, QĐ264, QĐ265, QĐ271; PTD-14 B + D; CDA KT-Y46-KH K1–K5).

Loại 1 – bài đơn vị: giả tiến trình (npm, CLI), giả npm bằng httpx.MockTransport. KHÔNG gọi npm, CLI, mạng thật.
"""
import asyncio
import json
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
                    ds = [r[0] for r in cn.execute("SELECT khoa_chongtrung FROM canhbao WHERE khoa_chongtrung LIKE 'cli_%'"
                                                   " AND trangthai IN ('moi', 'dabao', 'dagiao_task')")]
                    return ds, {k: thongbao._chu(k.split(":")[0], k, {"giatri": None, "nguong": None}, {}, {}) for k in ds}
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


if __name__ == "__main__":
    unittest.main()
