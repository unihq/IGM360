"""Bài kiểm ngày 06: đăng nhập gói Claude (dán mã), gói ChatGPT (mã thiết bị), tài khoản thứ 02, ghi nguồn AI.
Dùng 02 công cụ giả lập CLI (không gọi mạng, không cần cài claude, codex)."""
import os
import stat
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from maychu.dulieu import khoitao, ketnoi
from maychu.hethong.mohinh import dangnhap_goi as dg

CLAUDE_GIA = r'''
import json, os, sys, pathlib
noi = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or os.environ["GIA_MACDINH_CLAUDE"])
noi.mkdir(parents=True, exist_ok=True)
if sys.argv[1:3] == ["auth", "status"]:
    print(json.dumps({"loggedIn": (noi / "da_noi").exists(), "subscriptionType": "max"})); sys.exit(0)
print("Opening browser to sign in...", flush=True)
print("If the browser didn't open, visit: https://claude.ai/oauth/authorize?code=true&state=gia", flush=True)
for dong in sys.stdin:
    if dong.strip() == "ma-dung":
        (noi / "da_noi").write_text("1"); print("Login successful.", flush=True); sys.exit(0)
    print("OAuth error: Invalid code", flush=True)
    print("Paste code here if prompted > ", end="", flush=True)
'''
CODEX_GIA = r'''
import os, sys, time, pathlib
noi = pathlib.Path(os.environ.get("CODEX_HOME") or os.environ["GIA_MACDINH_CODEX"])
noi.mkdir(parents=True, exist_ok=True)
if sys.argv[1:3] == ["login", "status"]:
    if (noi / "auth.json").exists():
        print("Logged in using ChatGPT", file=sys.stderr); sys.exit(0)
    print("Not logged in", file=sys.stderr); sys.exit(1)
# Đúng chữ Codex CLI in (codex-rs/login/src/device_code_auth.rs, commit 1145028), có mã màu quanh link và mã
X, H, R = "\x1b[34m", "\x1b[90m", "\x1b[0m"
print(f"\nWelcome to Codex [v{H}0.171.0{R}]\n\nFollow these steps to sign in with ChatGPT using device code authorization:\n"
      f"\n1. Open this link in your browser and sign in to your account\n   {X}https://auth.openai.com/codex/device{R}\n"
      f"\n2. Enter this one-time code {H}(expires in 15 minutes){R}\n   {X}KQ7M-4XRT{R}\n", flush=True)
time.sleep(float(os.environ.get("GIA_CHO", "0.6")))
(noi / "auth.json").write_text("{}"); print("Successfully logged in", file=sys.stderr, flush=True)
'''


def _tao_cli(thumuc: Path, ten: str, ma: str) -> str:
    p = thumuc / ten
    p.write_text(f"#!{sys.executable}\n" + textwrap.dedent(ma))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


class KiemDangNhapGoi(unittest.TestCase):
    def setUp(self):
        # QĐ374 (b): CLI chỉ nhận biến trong danh sách trắng; khai tên biến mà CLI giả của bài này đọc
        self.addCleanup(setattr, dg, "BIEN_GIU_THU", dg.BIEN_GIU_THU)
        dg.BIEN_GIU_THU = frozenset({"GIA_MACDINH_CLAUDE", "GIA_MACDINH_CODEX", "GIA_CHO"})
        self.tam = tempfile.TemporaryDirectory()
        g = Path(self.tam.name)
        self.cu = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_CLAUDE_CLI", "IGM360_CODEX_CLI",
                                                  "IGM360_THUMUC_CLAUDE", "IGM360_THUMUC_CHATGPT", "GIA_MACDINH_CLAUDE",
                                                  "GIA_MACDINH_CODEX")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(g / "dulieu"), IGM360_CLAUDE_CLI=_tao_cli(g, "claude_gia", CLAUDE_GIA),
                          IGM360_CODEX_CLI=_tao_cli(g, "codex_gia", CODEX_GIA), IGM360_THUMUC_CLAUDE=str(g / "claude"),
                          IGM360_THUMUC_CHATGPT=str(g / "codex"), GIA_MACDINH_CLAUDE=str(g / "claude"),
                          GIA_MACDINH_CODEX=str(g / "codex"))
        khoitao.tao_het(g / "dulieu")
        dg._PHIEN.clear()
        dg._NHO_TRANGTHAI.clear()

    def tearDown(self):
        for k in list(dg._PHIEN):
            dg.huy(*k)
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def test_claude_dan_ma_sai_roi_dung(self):
        self.assertFalse(dg.trang_thai("claude", 1)["da_noi"])
        kq = dg.bat_dau("claude", 1)
        self.assertTrue(kq["url"].startswith("https://claude.ai/oauth/authorize"))
        self.assertIn("Mã chưa đúng", dg.dan_ma("claude", 1, "ma-sai")["loi"])
        kq = dg.dan_ma("claude", 1, "ma-dung")                        # CLI vẫn chờ: dán lại được
        self.assertTrue(kq["xong"], kq)
        self.assertTrue(kq["da_noi"])
        ds = dg.danh_sach()
        self.assertEqual([(d["ma"], d["loai"], d["uutien"], d["da_noi"]) for d in ds], [("goi_claude_01", "goi", 1, True)])
        self.assertEqual(ds[0]["ten"], "Gói Claude · tài khoản 01")

    def test_chatgpt_ma_thiet_bi_tu_hoi_lai(self):
        kq = dg.bat_dau("chatgpt", 1)
        self.assertEqual((kq["url"], kq["ma_thietbi"]), ("https://auth.openai.com/codex/device", "KQ7M-4XRT"))
        self.assertEqual(dg.hoi("chatgpt", 1), {"cho": True})
        for _ in range(50):
            kq = dg.hoi("chatgpt", 1)
            if not kq.get("cho"):
                break
            time.sleep(0.1)
        self.assertTrue(kq.get("xong"), kq)
        self.assertEqual(dg.danh_sach()[0]["ma"], "goi_chatgpt_01")

    def test_tai_khoan_02_thu_muc_rieng_va_gioi_han(self):
        dg.bat_dau("claude", 1)
        dg.dan_ma("claude", 1, "ma-dung")
        dg.bat_dau("claude", 2)
        dg.dan_ma("claude", 2, "ma-dung")
        tm = dg.thu_muc("claude", 2)
        self.assertTrue((tm / "da_noi").exists())
        self.assertEqual(stat.S_IMODE(tm.stat().st_mode), 0o700)
        self.assertEqual([(d["ma"], d["uutien"]) for d in dg.danh_sach()], [("goi_claude_01", 1), ("goi_claude_02", 2)])
        with self.assertRaises(ValueError):
            dg.bat_dau("claude", 3)
        with self.assertRaises(ValueError):
            dg.bat_dau("gemini", 1)

    def test_huy_va_chua_bat_dau(self):
        self.assertIn("Chưa bắt đầu", dg.dan_ma("claude", 1, "x")["loi"])
        dg.bat_dau("claude", 1)
        dg.huy("claude", 1)
        self.assertIn("Chưa bắt đầu", dg.dan_ma("claude", 1, "ma-dung")["loi"])
        self.assertEqual(dg.danh_sach(), [])

    def test_thieu_cong_cu(self):
        os.environ["IGM360_CLAUDE_CLI"] = "/khong/co/claude"
        self.assertIn("chưa có công cụ", dg.bat_dau("claude", 1)["loi"])
        self.assertFalse(dg.trang_thai("claude", 1, bo_nho=True)["da_noi"])

    def test_dang_nhap_lai_khong_them_dong(self):
        for _ in range(2):
            dg.bat_dau("claude", 1)
            dg.dan_ma("claude", 1, "ma-dung")
        cn = ketnoi.mo("Viecnen")
        try:
            self.assertEqual(cn.execute("SELECT count(*) FROM nguon_ai").fetchone()[0], 1)
        finally:
            cn.close()


if __name__ == "__main__":
    unittest.main()
