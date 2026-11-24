"""Bài kiểm Y46 (bản 0.8.4; QĐ263, QĐ264, QĐ265, QĐ271; PTD-14 B + D; CDA KT-Y46-KH K1–K5).

Loại 1 – bài đơn vị: giả tiến trình (npm, CLI), giả npm bằng httpx.MockTransport. KHÔNG gọi npm, CLI, mạng thật.
"""
import json
import os
import shutil
import subprocess
import tempfile
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
        nangcli._GOC.clear()
        nangcli._GOC.update(claude="2.1.331", chatgpt="0.172.0")                   # bản trong gói, không chạy CLI thật
        self.addCleanup(nangcli._GOC.clear)
        self.enterContext(mock.patch.object(nangcli, "_uoc_giai_nen", return_value=1000))

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


class KiemConTro(Nen):
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
