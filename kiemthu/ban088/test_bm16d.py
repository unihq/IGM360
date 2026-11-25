"""Bài kiểm bản sửa lỗi bảo mật 16d (QĐ374, anh "Chọn A"; KIEM-BM-16d; CDA KT-QĐ374, bản đồ mục 16d):
(a) Codex: exec và app-server (lượt có người nghe, kiểm bản CLI mới) mang `--disable shell_tool --disable view_image`
    → mô hình không có công cụ chạy lệnh, không có công cụ đọc tệp ảnh;
(b) biến môi trường đưa cho CLI AI và npm theo DANH SÁCH TRẮNG: không có IGM360_*, WATCHTOWER_TOKEN,
    FORWARDED_ALLOW_IPS, khóa API;
(c) Claude ở lượt không phải trò chuyện: `--tools ""` + `--strict-mcp-config` (không công cụ, không MCP).
Không gọi CLI thật, không gọi npm thật: thay `_chay`, `_chay_as`, `chay` bằng hàm ghi lại đối số và môi trường.
Giá trị giống bí mật ghép lúc chạy; câu kiểm không in nội dung biến môi trường (máy GitHub công khai).
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kiemthu.ban084 import test_y46 as y46
from maychu.dulieu import khoitao
from maychu.hethong.mohinh import congai, dangnhap_goi, madaihan

GIA = "gia" + "-" + "16d"
CAM = {"IGM360_ADMIN_USER": "chu", "IGM360_ADMIN_PASSWORD": GIA, "WATCHTOWER_TOKEN": GIA, "FORWARDED_ALLOW_IPS": ".".join(["10", "9", "8", "7"]),
       "OPENAI_API_KEY": GIA, "ANTHROPIC_API_KEY": GIA, "ANTHROPIC_AUTH_TOKEN": GIA, "CODEX_API_KEY": GIA, "GH_TOKEN": GIA,
       "IGM360_CONG": "8360", "PYTHONUNBUFFERED": "1"}
CHUNG = {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "TERM", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
         "ALL_PROXY", "http_proxy", "https_proxy", "no_proxy", "all_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR",
         "NODE_EXTRA_CA_CERTS"}
THEO_GOI = {"claude": {"CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN"}, "chatgpt": {"CODEX_HOME"}}
WIN = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"}
CO_LA = {"LANG": "C.UTF-8", "TZ": "Asia/Ho_Chi_Minh", "HTTPS_PROXY": "http://proxy.local:3128", "SSL_CERT_FILE": "/etc/ssl/a.pem"}


def duoc(goi=None):
    return CHUNG | THEO_GOI.get(goi, set()) | (WIN if os.name == "nt" else set())


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        g = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {
            "IGM360_THUMUC_DULIEU": str(g / "dulieu"), "IGM360_LICH": "tat", "IGM360_THUMUC_CLAUDE": str(g / "claude"),
            "IGM360_THUMUC_CHATGPT": str(g / "codex"), "IGM360_CLAUDE_CLI": str(g / "khong_co_claude"),
            "IGM360_CODEX_CLI": str(g / "khong_co_codex"), **CAM, **CO_LA}))
        khoitao.tao_het(g / "dulieu")
        self.enterContext(mock.patch.object(congai, "_doc_han_muc_codex", return_value={}))
        self.enterContext(mock.patch.object(congai, "_mohinh_codex", return_value=None))
        self.lenh, self.env = [], []

    def chay(self, lenh, env, vao=None, giay=None):
        self.lenh.append(list(lenh)), self.env.append(dict(env))
        if "exec" in lenh:
            dong = [{"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
                    {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}]
        else:
            dong = [{"type": "result", "subtype": "success", "result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}}]
        return subprocess.CompletedProcess(lenh, 0, "\n".join(json.dumps(x) for x in dong), "")

    def chay_as(self, lenh, env, cau, mohinh, nghe, giay=congai.GIAY_TOIDA, giay_khoi_dau=congai.GIAY_KHOI_DAU_AS):
        self.lenh.append(list(lenh)), self.env.append(dict(env))
        return {"chu": ["ok"], "vao": 1, "ra": 1, "loi": "", "hanmuc": {}, "mohinh_bao": None}

    def sach(self, env, goi):
        # chỉ báo TÊN biến lạ, không in giá trị (máy GitHub công khai)
        la = sorted(set(env) - duoc(goi))
        self.assertEqual(la, [], "biến ngoài danh sách trắng")
        for k in CAM:
            self.assertFalse(k in env, k)
        self.assertFalse(GIA in env.values(), "còn giá trị giả")
        for k in CO_LA:
            self.assertTrue(k in env, k)                                         # biến cần dùng vẫn đi qua


class KiemCodex(Nen):
    CO = ["--disable", "shell_tool", "--disable", "view_image"]

    def test_a_exec(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            self.assertEqual(congai._goi_chatgpt(1, "x", "gpt-5")["chu"], "ok")
        l = self.lenh[-1]
        self.assertEqual(l[1:6], ["exec", *self.CO])                             # QĐ374 (a); không dùng -c
        self.assertNotIn("-c", l)
        self.assertEqual(l[l.index("--sandbox") + 1], "read-only")
        self.assertEqual(l[-1], "-")
        self.sach(self.env[-1], "chatgpt")                                       # QĐ374 (b)

    def test_a_app_server_luot_co_nguoi_nghe(self):
        tok = congai._NGHE.set(congai.Nghe(lambda loai, **du: None))
        try:
            with mock.patch.object(congai, "_chay_as", side_effect=self.chay_as):
                self.assertEqual(congai._goi_chatgpt(1, "x", "gpt-5")["chu"], "ok")
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual(self.lenh[-1][1:], ["app-server", *self.CO])
        self.sach(self.env[-1], "chatgpt")

    def test_a_kiem_ban_cli_moi(self):
        with mock.patch.object(congai, "_chay_as", side_effect=self.chay_as):
            congai.kiem_app_server(1, "x", "ban-moi")
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            congai._goi_chatgpt(1, "x", None, cli="ban-moi")
        self.assertEqual(self.lenh[0], ["ban-moi", "app-server", *self.CO])
        self.assertEqual(self.lenh[1][:6], ["ban-moi", "exec", *self.CO])
        for e in self.env:
            self.sach(e, "chatgpt")


class KiemClaude(Nen):
    def test_c_luot_khong_phai_tro_chuyen_khong_cong_cu(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            congai._goi_claude(1, "x", None)
        l = self.lenh[-1]
        self.assertEqual(l[l.index("--max-turns") + 1], "1")
        self.assertEqual(l[l.index("--tools") + 1], "")                          # QĐ374 (c): không công cụ nào
        self.assertIn("--strict-mcp-config", l)
        self.assertNotIn("--allowedTools", l)
        self.sach(self.env[-1], "claude")

    def test_c_tro_chuyen_giu_nhu_qd195(self):
        tok = congai._TRA_WEB.set(True)
        try:
            with mock.patch.object(congai, "_chay", side_effect=self.chay):
                congai._goi_claude(1, "x", None)
        finally:
            congai._TRA_WEB.reset(tok)
        l = self.lenh[-1]
        self.assertEqual(l[l.index("--tools") + 1], "WebSearch,WebFetch")
        self.assertNotIn("--max-turns", l)
        self.sach(self.env[-1], "claude")


class KiemBienMoiTruong(Nen):
    def test_b_danh_sach_trang_ghim(self):
        self.assertEqual(dangnhap_goi.BIEN_GIU, frozenset(CHUNG))
        self.assertEqual({k: set(v) for k, v in dangnhap_goi.BIEN_GIU_GOI.items()}, THEO_GOI)
        self.assertEqual(dangnhap_goi.BIEN_GIU_WINDOWS, frozenset(WIN))
        self.assertEqual(dangnhap_goi.BIEN_GIU_THU, frozenset())                # chạy thật: không thêm biến nào

    def test_b_moi_goi_moi_tai_khoan(self):
        for goi in ("claude", "chatgpt"):
            for tk in (1, 2):
                for ma in (True, False):
                    self.sach(dangnhap_goi._env(goi, tk, ma_daihan=ma), goi)

    def test_b_thu_muc_tai_khoan_va_ma_dai_han_dat_sau_buoc_loc(self):
        self.assertTrue("CODEX_HOME" in dangnhap_goi._env("chatgpt", 2))
        self.assertTrue("CLAUDE_CONFIG_DIR" in dangnhap_goi._env("claude", 2))
        with mock.patch.object(madaihan, "moi_truong", side_effect=lambda env, tk, dung_ma=True: env.update({madaihan.BIEN: GIA})):
            env = dangnhap_goi._env("claude", 1)
        self.assertEqual(env[madaihan.BIEN], GIA)
        self.assertFalse("CLAUDE_CODE_OAUTH_TOKEN" in dangnhap_goi._env("chatgpt", 1))   # mã Claude không sang Codex

    def test_b_claude_oauth_cua_vung_chua_chi_sang_claude(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_OAUTH_TOKEN": GIA}):
            self.assertFalse(GIA in dangnhap_goi._env("chatgpt", 1).values())


class KiemNpm(y46.Nen):
    def test_b_npm_install_danh_sach_trang(self):
        with mock.patch.dict(os.environ, {**CAM, **CO_LA, "npm_config_cache_min": "10", "NPM_CONFIG_LOGLEVEL": "warn"}):
            kq, chay = self.nang()
        self.assertEqual(kq["kq"], "dat")
        e = next(x for x, l in zip(chay.env, chay.lenh) if l[0] == "npm")
        la = sorted(k for k in e if k not in duoc() and not k.lower().startswith("npm_config_"))
        self.assertEqual(la, [], "biến ngoài danh sách trắng")
        for k in CAM:
            self.assertFalse(k in e, k)
        thuong = {k.lower(): v for k, v in e.items()}                             # Windows đổi tên biến thành chữ hoa
        self.assertEqual((thuong["npm_config_cache_min"], thuong["npm_config_loglevel"]), ("10", "warn"))   # cộng npm_config_*
        self.assertEqual(e["npm_config_userconfig"], os.devnull)                  # K5 giữ


if __name__ == "__main__":
    unittest.main()
