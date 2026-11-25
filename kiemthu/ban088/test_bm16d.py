"""Bài kiểm bản sửa lỗi bảo mật 16d (QĐ374, anh "Chọn A"; KIEM-BM-16d; CDA bản đồ mục 16d):
(a) Codex: exec và app-server (lượt có người nghe, kiểm bản CLI mới) mang `--disable shell_tool` → mô hình không có
    công cụ chạy lệnh;
(b) biến môi trường đưa cho CLI AI không có mật khẩu quản trị, mã cập nhật, biến dạng khóa / mã / bí mật;
(c) Claude ở lượt không phải trò chuyện: `--tools ""` + `--strict-mcp-config` (không công cụ, không MCP).
Không gọi CLI thật: thay `_chay`, `_chay_as` bằng hàm ghi lại đối số và môi trường. Giá trị giống bí mật ghép lúc chạy.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao
from maychu.hethong.mohinh import congai, dangnhap_goi

GIA = "gia" + "-" + "16d"
BI_MAT = {"IGM360_ADMIN_USER": "chu", "IGM360_ADMIN_PASSWORD": GIA, "WATCHTOWER_TOKEN": GIA, "OPENAI_API_KEY": GIA,
          "ANTHROPIC_API_KEY": GIA, "MOT_SECRET": GIA, "GH_TOKEN": GIA, "DB_PASSWORD": GIA, "KEY": GIA, "X_KEY_Y": GIA}
GIU = {"PATH", "IGM360_THUMUC_DULIEU", "HOME_GIA_16D"}


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        g = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {
            "IGM360_THUMUC_DULIEU": str(g / "dulieu"), "IGM360_LICH": "tat", "IGM360_THUMUC_CLAUDE": str(g / "claude"),
            "IGM360_THUMUC_CHATGPT": str(g / "codex"), "IGM360_CLAUDE_CLI": str(g / "khong_co_claude"),
            "IGM360_CODEX_CLI": str(g / "khong_co_codex"), "HOME_GIA_16D": "1", **BI_MAT}))
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

    def khong_bi_mat(self, env):
        # chỉ báo tên biến, KHÔNG in nội dung môi trường (máy GitHub công khai)
        for k in BI_MAT:
            self.assertFalse(k in env, k)
        self.assertFalse(GIA in env.values(), "còn giá trị giả")
        for k in GIU:
            self.assertTrue(k in env, k)


class KiemCodex(Nen):
    def test_a_exec_tat_cong_cu_chay_lenh(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            self.assertEqual(congai._goi_chatgpt(1, "x", "gpt-5")["chu"], "ok")
        l = self.lenh[-1]
        self.assertEqual(l[1:4], ["exec", "--disable", "shell_tool"])            # QĐ374 (a)
        self.assertEqual(l[l.index("--sandbox") + 1], "read-only")
        self.assertEqual(l[-1], "-")
        self.khong_bi_mat(self.env[-1])                                          # QĐ374 (b)

    def test_a_app_server_luot_co_nguoi_nghe(self):
        tok = congai._NGHE.set(congai.Nghe(lambda loai, **du: None))
        try:
            with mock.patch.object(congai, "_chay_as", side_effect=self.chay_as):
                self.assertEqual(congai._goi_chatgpt(1, "x", "gpt-5")["chu"], "ok")
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual(self.lenh[-1][1:], ["app-server", "--disable", "shell_tool"])
        self.khong_bi_mat(self.env[-1])

    def test_a_kiem_ban_cli_moi_app_server(self):
        with mock.patch.object(congai, "_chay_as", side_effect=self.chay_as):
            congai.kiem_app_server(1, "x", "ban-moi")
        self.assertEqual(self.lenh[-1], ["ban-moi", "app-server", "--disable", "shell_tool"])
        self.khong_bi_mat(self.env[-1])

    def test_a_kiem_ban_cli_moi_exec(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            congai._goi_chatgpt(1, "x", None, cli="ban-moi")
        self.assertEqual(self.lenh[-1][:4], ["ban-moi", "exec", "--disable", "shell_tool"])


class KiemClaude(Nen):
    def test_c_luot_khong_phai_tro_chuyen_khong_cong_cu(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            congai._goi_claude(1, "x", None)
        l = self.lenh[-1]
        self.assertEqual(l[l.index("--max-turns") + 1], "1")
        self.assertEqual(l[l.index("--tools") + 1], "")                          # QĐ374 (c): không công cụ nào
        self.assertIn("--strict-mcp-config", l)
        self.assertNotIn("--allowedTools", l)
        self.khong_bi_mat(self.env[-1])

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
        self.khong_bi_mat(self.env[-1])


class KiemBienMoiTruong(Nen):
    def test_b_loc_moi_goi_moi_tai_khoan(self):
        for goi in ("claude", "chatgpt"):
            for tk in (1, 2):
                self.khong_bi_mat(dangnhap_goi._env(goi, tk))

    def test_b_ten_bien(self):
        for ten in BI_MAT:
            self.assertTrue(dangnhap_goi.bien_cam(ten), ten)
        for ten in ("PATH", "HOME", "LANG", "TZ", "HTTPS_PROXY", "NODE_EXTRA_CA_CERTS", "CODEX_HOME", "CLAUDE_CONFIG_DIR",
                    "IGM360_THUMUC_DULIEU", "KEYBOARD", "MONKEY"):
            self.assertFalse(dangnhap_goi.bien_cam(ten), ten)

    def test_b_ma_dai_han_claude_dat_sau_buoc_loc(self):
        # mã dài hạn của đúng tài khoản được đặt lại SAU bước lọc (madaihan.moi_truong), không bị bộ lọc bỏ
        from maychu.hethong.mohinh import madaihan
        with mock.patch.object(madaihan, "moi_truong", side_effect=lambda env, tk, dung_ma=True: env.update({madaihan.BIEN: GIA})):
            env = dangnhap_goi._env("claude", 1)
        self.assertEqual(env[madaihan.BIEN], GIA)


if __name__ == "__main__":
    unittest.main()
