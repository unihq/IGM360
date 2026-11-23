"""Bài kiểm ngày 06: Cổng AI 03 nguồn, chọn theo ưu tiên, chuyển nguồn khi hết hạn mức, trần tiền khoá API,
ghi G04 và % hạn mức gói, trò chuyện F35. CLI giả lập in đúng dạng dòng JSON của CLI thật; Google, OpenAI,
Anthropic giả lập bằng httpx.MockTransport."""
import json
import os
import stat
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

import httpx

from maychu.dulieu import khoitao, ketnoi, maso
from maychu.hethong.kekhoa import kho
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, trochuyen

MK06 = "mk-kiem-06"

CLAUDE_GIA = r'''
import json, os, sys, pathlib
noi = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or os.environ["GIA_MACDINH_CLAUDE"]); noi.mkdir(parents=True, exist_ok=True)
if sys.argv[1:3] == ["auth", "status"]:
    print(json.dumps({"loggedIn": True, "subscriptionType": "max"})); sys.exit(0)
cau = sys.stdin.read()
(noi / "cau_cuoi.txt").write_text(cau)
if os.environ.get("GIA_HET"):
    print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": "five_hour", "utilization": 1.0, "resetsAt": 4102444800}}))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "result": "Claude AI usage limit reached"})); sys.exit(1)
print(json.dumps({"type": "system", "subtype": "init", "model": "claude-x"}))
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "unifiedWindows": {
    "five_hour": {"utilization": 0.32, "resetsAt": 4102444800}, "seven_day": {"utilization": 0.59, "resetsAt": 4102444800}}}}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "Chào anh, Claude đây.",
                  "total_cost_usd": 0.0123, "usage": {"input_tokens": 100, "cache_read_input_tokens": 20, "output_tokens": 30}}))
'''
CODEX_GIA = r'''
import json, os, sys, pathlib, time
noi = pathlib.Path(os.environ.get("CODEX_HOME") or os.environ["GIA_MACDINH_CODEX"]); noi.mkdir(parents=True, exist_ok=True)
if sys.argv[1:3] == ["login", "status"]:
    print("Logged in using ChatGPT", file=sys.stderr); sys.exit(0)
assert sys.argv[1] == "exec" and sys.argv[-1] == "-"
cau = sys.stdin.read()
p = noi / "sessions" / "2026" / "11" / "21"; p.mkdir(parents=True, exist_ok=True)
(p / "rollout-1.jsonl").write_text(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
    "primary": {"used_percent": 12.0, "window_minutes": 300, "resets_at": 4102444800},
    "secondary": {"used_percent": 40.0, "window_minutes": 10080, "resets_at": 4102444800}}}}) + "\n")
for o in ({"type": "thread.started", "thread_id": "t1"}, {"type": "turn.started"},
          {"type": "item.completed", "item": {"id": "i1", "type": "agent_message", "text": "Chào anh, ChatGPT đây."}},
          {"type": "turn.completed", "usage": {"input_tokens": 50, "cached_input_tokens": 0, "output_tokens": 10, "reasoning_output_tokens": 5}}):
    print(json.dumps(o))
'''


def _cli(thumuc: Path, ten: str, ma: str) -> str:
    p = thumuc / ten
    p.write_text(f"#!{sys.executable}\n" + textwrap.dedent(ma))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


class NenCongAI(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        g = self.g = Path(self.tam.name)
        self.cu = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_CLAUDE_CLI", "IGM360_CODEX_CLI",
                                                  "IGM360_THUMUC_CLAUDE", "IGM360_THUMUC_CHATGPT", "GIA_MACDINH_CLAUDE",
                                                  "GIA_MACDINH_CODEX", "GIA_HET", "CODEX_HOME")}
        os.environ.update(IGM360_THUMUC_DULIEU=str(g / "dulieu"), IGM360_CLAUDE_CLI=_cli(g, "claude_gia", CLAUDE_GIA),
                          IGM360_CODEX_CLI=_cli(g, "codex_gia", CODEX_GIA), IGM360_THUMUC_CLAUDE=str(g / "claude"),
                          IGM360_THUMUC_CHATGPT=str(g / "codex"), GIA_MACDINH_CLAUDE=str(g / "claude"),
                          GIA_MACDINH_CODEX=str(g / "codex"), CODEX_HOME=str(g / "codex"))
        os.environ.pop("GIA_HET", None)
        khoitao.tao_het(g / "dulieu")
        dg._NHO_TRANGTHAI.clear()

    def tearDown(self):
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def g04(self):
        cn = ketnoi.mo("Nhatky")
        try:
            return cn.execute("SELECT nguon_ai_id, luong_vao, luong_ra, sotien, sotien_thamkhao, ketqua FROM nhatky_ai ORDER BY rowid").fetchall()
        finally:
            cn.close()

    def g06(self, ma):
        cn = ketnoi.mo("Viecnen")
        try:
            return cn.execute("SELECT tyle_5gio, tyle_tuan, datlai_5gio_luc, do_luc, da_het_luc FROM nguon_ai WHERE ma = ?", (ma,)).fetchone()
        finally:
            cn.close()

    def them_khoa(self, ma, uu, tran, gia=(3_000_000, 15_000_000)):
        cn = ketnoi.mo("Viecnen")
        try:
            nid = maso.tao()
            hang = "anthropic" if "anthropic" in ma else "openai"   # Y22a: G06 bắt buộc hang, cach_goi (QĐ161)
            cn.execute("INSERT INTO nguon_ai (id, ma, ten, loai, uutien, tran_tien_thang, hang, cach_goi)"
                       " VALUES (?, ?, ?, 'khoa_api', ?, ?, ?, ?)", (nid, ma, "Khoá API AI", uu, tran, hang, hang))
            cn.execute("INSERT INTO mohinh_ai (id, nguon_ai_id, ma_mohinh, gia_vao, gia_ra, tien_ma, trangthai)"
                       " VALUES (?, ?, 'mo-hinh-x', ?, ?, 'USD', 'dung')", (maso.tao(), nid, *gia))
        finally:
            cn.close()
        kho.cat(ma, "sk-gia-bimat-1234")
        return nid


class KiemCongAI(NenCongAI):
    def test_goi_claude_ghi_g04_va_han_muc(self):
        dg.ghi_nguon("claude", 1)
        kq = congai.goi("Xin chào")
        self.assertEqual((kq["chu"], kq["nguon"]), ("Chào anh, Claude đây.", "Gói Claude · tài khoản 01"))
        self.assertEqual((self.g / "claude" / "cau_cuoi.txt").read_text(), "Xin chào")   # câu hỏi qua đầu vào chuẩn
        d = self.g04()[0]
        self.assertEqual(d[1:], (120, 30, None, 12300, "xong"))          # tiền thật trống, quy đổi tham khảo 0,0123 USD
        h = self.g06("goi_claude_01")
        self.assertEqual((h[0], h[1]), (32, 59))
        self.assertTrue(h[2].startswith("2100-01-01") and h[3])

    def test_goi_chatgpt_doc_han_muc_tep_phien(self):
        dg.ghi_nguon("chatgpt", 1)
        kq = congai.goi("Xin chào")
        self.assertEqual(kq["chu"], "Chào anh, ChatGPT đây.")
        self.assertEqual(self.g04()[0][1:], (50, 15, None, None, "xong"))
        self.assertEqual(self.g06("goi_chatgpt_01")[:2], (12, 40))

    def test_het_han_muc_chuyen_nguon_uu_tien_2(self):
        dg.ghi_nguon("claude", 1)
        dg.ghi_nguon("chatgpt", 1)
        os.environ["GIA_HET"] = "1"
        kq = congai.goi("Xin chào")
        self.assertEqual(kq["nguon"], "Gói ChatGPT · tài khoản 01")
        self.assertIn("hết hạn mức", kq["bo_qua"][0]["lydo"])
        self.assertEqual([r[5] for r in self.g04()], ["het_hanmuc", "xong"])
        self.assertEqual(self.g06("goi_claude_01")[4], 1)
        os.environ.pop("GIA_HET")
        kq = congai.goi("Lần 2")                                          # chưa tới giờ đặt lại: vẫn bỏ qua Claude
        self.assertEqual(kq["nguon"], "Gói ChatGPT · tài khoản 01")
        self.assertEqual(kq["bo_qua"][0]["lydo"], "hết hạn mức")

    def test_khoa_api_tran_tien_va_tien_that(self):
        nid = self.them_khoa("khoa_anthropic_01", 1, None)
        self.assertEqual(congai.goi("x")["bo_qua"][0]["lydo"], "chưa đặt trần tiền")
        cn = ketnoi.mo("Viecnen")
        cn.execute("UPDATE nguon_ai SET tran_tien_thang = 1 WHERE id = ?", (nid,))
        cn.close()
        goi_den = []

        def gia(req):
            goi_den.append(req)
            assert req.headers["x-api-key"] == "sk-gia-bimat-1234"
            return httpx.Response(200, json={"content": [{"type": "text", "text": "Khoá API đây."}],
                                             "usage": {"input_tokens": 1000, "output_tokens": 200}})
        kq = congai.goi("x", client=httpx.Client(transport=httpx.MockTransport(gia)))
        self.assertEqual(kq["chu"], "Khoá API đây.")
        self.assertEqual(self.g04()[0][3], 6000)                          # 1000×3 + 200×15 phần triệu USD = 0,006 USD
        self.assertEqual(congai.tom_tat_tuan()["tien_that_usd"], 0.006)
        cn = ketnoi.mo("Nhatky")
        cn.execute("UPDATE nhatky_ai SET sotien = 1000000")              # tháng này đã tiêu 01 USD = chạm trần 01 USD
        cn.close()
        self.assertEqual(congai.goi("x", client=httpx.Client(transport=httpx.MockTransport(gia)))["bo_qua"][0]["lydo"],
                         "chạm trần tiền tháng")
        self.assertEqual(len(goi_den), 1)

    def test_khong_co_nguon(self):
        self.assertEqual(congai.goi("x")["loi"], "Chưa có nguồn AI nào dùng được")

    def test_tro_chuyen_luu_hoi_thoai(self):
        dg.ghi_nguon("claude", 1)
        kq = trochuyen.gui(None, "nguoi-1", "Tóm tắt giúp em")
        self.assertEqual(kq["tra_loi"]["noidung"], "Chào anh, Claude đây.")
        kq2 = trochuyen.gui(kq["hoithoai_id"], "nguoi-1", "Thêm ý nữa")
        self.assertEqual(kq2["hoithoai_id"], kq["hoithoai_id"])
        cau = (self.g / "claude" / "cau_cuoi.txt").read_text()
        self.assertIn("Tóm tắt giúp em", cau)                            # gửi kèm các lượt trước
        self.assertIn("Thêm ý nữa", cau)
        ht = trochuyen.xem(kq["hoithoai_id"], "nguoi-1")
        self.assertEqual([t["vai"] for t in ht["tinnhan"]], ["nguoi", "ai", "nguoi", "ai"])
        self.assertTrue(ht["tinnhan"][1]["nhatky_ai_id"])
        self.assertEqual(trochuyen.danh_sach("nguoi-1")[0]["tieude"], "Tóm tắt giúp em")
        self.assertIsNone(trochuyen.xem(kq["hoithoai_id"], "nguoi-khac"))

    def test_tro_chuyen_khi_khong_co_nguon(self):
        kq = trochuyen.gui(None, "nguoi-1", "Xin chào")
        self.assertEqual(kq["tra_loi"]["vai"], "hethong")
        self.assertIn("Chưa có nguồn AI", kq["tra_loi"]["noidung"])


class KiemDuongGoi06(NenCongAI):
    def setUp(self):
        super().setUp()
        from maychu.hethong.taikhoan import totp
        self.cu2 = {k: os.environ.get(k) for k in ("IGM360_LICH", "IGM360_ADMIN_USER", "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE")}
        os.environ.update(IGM360_LICH="tat", IGM360_ADMIN_USER="chu", IGM360_ADMIN_PASSWORD=MK06, IGM360_COOKIE_SECURE="0")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}
        kq = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK06}, headers=self.h).json()
        self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": totp.ma_cua_buoc(kq["khoa"], totp.buoc())},
                    headers=self.h).raise_for_status()

    def tearDown(self):
        from maychu.hethong.taikhoan import nguoidung
        self.c.__exit__(None, None, None)
        for k, v in self.cu2.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        nguoidung._MA_TAM.clear()
        nguoidung._BUOC_DA_DUNG.clear()
        super().tearDown()

    def test_mohinh_goithu_trochuyen(self):
        nid = dg.ghi_nguon("claude", 1)
        kq = self.c.get("/api/mohinh").json()
        self.assertEqual((kq["nguon"][0]["ma"], kq["nguon"][0]["da_noi"], kq["tuan"]["luot"]), ("goi_claude_01", True, 0))
        self.assertEqual(self.c.post(f"/api/mohinh/{nid}/goithu", headers=self.h).json()["nguon"], "Gói Claude · tài khoản 01")
        r = self.c.post("/api/trochuyen", json={"noidung": "Xin chào"}, headers=self.h).json()
        self.assertEqual(r["tra_loi"]["noidung"], "Chào anh, Claude đây.")
        self.assertEqual(len(self.c.get(f"/api/trochuyen/{r['hoithoai_id']}").json()["tinnhan"]), 2)
        self.assertEqual(self.c.get("/api/trochuyen").json()["hoithoai"][0]["id"], r["hoithoai_id"])
        self.assertEqual(self.c.post("/api/trochuyen", json={"noidung": "  "}, headers=self.h).status_code, 400)
        self.assertEqual(self.c.get("/api/trochuyen/khong-co").status_code, 404)
        self.assertEqual(self.c.get("/api/mohinh").json()["tuan"]["luot"], 2)


if __name__ == "__main__":
    unittest.main()
