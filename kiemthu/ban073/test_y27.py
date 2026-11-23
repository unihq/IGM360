"""Bài kiểm bản 0.7.3 (QĐ169 đợt 1, Y27): ô tài khoản gói "Tên · gói" đọc sống, có đường lùi, không lưu; logo gốc
ChatGPT. Chỉ dùng tên giả (QĐ126), không gọi CLI thật."""
import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao
from maychu.hethong.mohinh import dangnhap_goi as dg

GOC = Path(__file__).resolve().parents[2]
TEN_GIA = "Nguoi Gia Demo"


def _jwt(than: dict) -> str:
    return "e30." + base64.urlsafe_b64encode(json.dumps(than).encode()).decode().rstrip("=") + ".gia"


class KiemHoSo(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.t = Path(self.tam.name)
        self.cu = {k: os.environ.get(k) for k in ("IGM360_THUMUC_CLAUDE", "IGM360_THUMUC_CHATGPT", "CODEX_HOME",
                                                  "CLAUDE_CONFIG_DIR", "IGM360_THUMUC_DULIEU")}
        for k in ("CODEX_HOME", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(k, None)
        os.environ.update(IGM360_THUMUC_CLAUDE=str(self.t / "claude"), IGM360_THUMUC_CHATGPT=str(self.t / "codex"),
                          IGM360_THUMUC_DULIEU=str(self.t / "dulieu"))
        dg._NHO_TRANGTHAI.clear()
        dg._PHIEN.clear()

    def tearDown(self):
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def _hoso_claude(self, noi_dung) -> Path:
        p = self.t / "claude_hoso.json"
        p.write_text(noi_dung if isinstance(noi_dung, str) else json.dumps(noi_dung), encoding="utf-8")
        return p

    def _auth_codex(self, tk: int, than: dict) -> None:
        noi = self.t / "codex" if tk == 1 else self.t / "codex" / f"taikhoan_{tk:02d}"
        noi.mkdir(parents=True, exist_ok=True)
        (noi / "auth.json").write_text(json.dumps({"tokens": {"id_token": _jwt(than), "account_id": "acc_gia"}}), encoding="utf-8")

    # ---- Claude
    def test_claude_ten_va_goi(self):
        p = self._hoso_claude({"oauthAccount": {"displayName": TEN_GIA, "planDisplayName": "Ultra"}})
        with mock.patch.object(dg, "_tep_hoso_claude", return_value=p):
            self.assertEqual(dg.ho_so("claude", 1, "max"), {"ten_hien": TEN_GIA, "goi_ten": "Ultra", "mota_goi": None})

    def test_claude_duong_lui(self):
        cases = [
            (None, "max", {"ten_hien": None, "goi_ten": "Max"}),                       # tệp mất (máy chủ: ngoài ổ lưu)
            ("không phải JSON", "max", {"ten_hien": None, "goi_ten": "Max"}),          # tệp hỏng
            ({"khac": 1}, "max", {"ten_hien": None, "goi_ten": "Max"}),                # đổi tên trường
            ({"oauthAccount": {"displayName": 7, "planDisplayName": "  "}}, None, {"ten_hien": None, "goi_ten": None}),
            ({"oauthAccount": {"displayName": TEN_GIA}}, "pro", {"ten_hien": TEN_GIA, "goi_ten": "Pro"}),
        ]
        for nd, ho, mong in cases:
            p = self.t / "khong_co.json" if nd is None else self._hoso_claude(nd)
            with mock.patch.object(dg, "_tep_hoso_claude", return_value=p):
                kq = dg.ho_so("claude", 1, ho)
            self.assertEqual({k: kq[k] for k in mong}, mong, nd)

    def test_claude_ten_dai_cat_gon(self):
        p = self._hoso_claude({"oauthAccount": {"displayName": "A" * 200, "planDisplayName": "Ultra"}})
        with mock.patch.object(dg, "_tep_hoso_claude", return_value=p):
            self.assertEqual(len(dg.ho_so("claude", 1)["ten_hien"]), dg.DAI_TOIDA)

    def test_cho_tep_ho_so(self):
        self.assertEqual(dg._tep_hoso_claude(2), self.t / "claude" / "taikhoan_02" / ".claude.json")
        self.assertEqual(dg._tep_hoso_claude(1), Path.home() / ".claude.json")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.t / "cauhinh")
        self.assertEqual(dg._tep_hoso_claude(1), self.t / "cauhinh" / ".claude.json")
        self.assertEqual(dg._tep_auth_codex(1), self.t / "codex" / "auth.json")
        self.assertEqual(dg._tep_auth_codex(2), self.t / "codex" / "taikhoan_02" / "auth.json")

    # ---- ChatGPT
    def test_chatgpt_goi_va_ten(self):
        self._auth_codex(1, {"email": "a@vidu.invalid", "name": TEN_GIA,
                             "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"}})
        self.assertEqual(dg.ho_so("chatgpt", 1), {"ten_hien": TEN_GIA, "goi_ten": "Plus", "mota_goi": None})
        self._auth_codex(2, {"https://api.openai.com/auth": {"chatgpt_plan_type": "pro"}})
        self.assertEqual(dg.ho_so("chatgpt", 2), {"ten_hien": None, "goi_ten": "Pro", "mota_goi": None})
        for loai in ("pro", "prolite", "promax"):   # QĐ170: mọi loại Pro hiện "Pro", không ngoặc
            self._auth_codex(2, {"https://api.openai.com/auth": {"chatgpt_plan_type": loai}})
            self.assertEqual(dg.ho_so("chatgpt", 2)["goi_ten"], "Pro")
        self.assertFalse([v for v in dg.TEN_GOI_CHATGPT.values() if "(" in v])

    def test_chatgpt_duong_lui(self):
        self.assertEqual(dg.ho_so("chatgpt", 1), {"ten_hien": None, "goi_ten": None, "mota_goi": None})   # chưa có tệp
        self._auth_codex(1, {"https://api.openai.com/auth": {"chatgpt_plan_type": "loai_moi_chua_biet"}})
        self.assertIsNone(dg.ho_so("chatgpt", 1)["goi_ten"])
        (self.t / "codex" / "auth.json").write_text("{}", encoding="utf-8")
        self.assertIsNone(dg.ho_so("chatgpt", 1)["goi_ten"])

    def test_mo_ta_goi_chi_khi_co_nguon(self):
        self.assertEqual(dg.MOTA_GOI, {})   # chưa có nguồn đã xác minh: bỏ dòng, không tự đặt chữ
        p = self._hoso_claude({"oauthAccount": {"planDisplayName": "Ultra"}})
        with mock.patch.object(dg, "_tep_hoso_claude", return_value=p), \
                mock.patch.dict(dg.MOTA_GOI, {("claude", "Ultra"): "Mô tả giả"}):
            self.assertEqual(dg.ho_so("claude", 1)["mota_goi"], "Mô tả giả")

    # ---- Thẻ gói: đọc sống, không lưu
    def test_the_goi_doc_song_khong_luu(self):
        khoitao.tao_het(self.t / "dulieu")
        p = self._hoso_claude({"oauthAccount": {"displayName": TEN_GIA, "planDisplayName": "Ultra"}})
        with mock.patch.object(dg, "_tep_hoso_claude", return_value=p), \
                mock.patch.object(dg, "trang_thai", return_value={"da_noi": True, "goi_dang_dung": "max"}):
            o = dg.tinh_hinh_goi()["claude"][0]
        self.assertEqual((o["ten_hien"], o["goi_ten"]), (TEN_GIA, "Ultra"))
        with mock.patch.object(dg, "_tep_hoso_claude", return_value=p), \
                mock.patch.object(dg, "trang_thai", return_value={"da_noi": False, "goi_dang_dung": None}):
            o = dg.tinh_hinh_goi()["claude"][0]
        self.assertEqual((o["ten_hien"], o["goi_ten"]), (None, None))   # chưa đăng nhập: không đọc hồ sơ
        for tep in (self.t / "dulieu").rglob("*"):
            if tep.is_file():
                self.assertNotIn(TEN_GIA.encode(), tep.read_bytes(), tep.name)   # 0 bảng nào lưu tên

    # ---- Giao diện, logo, tài liệu, bản
    def test_giao_dien_logo_tailieu(self):
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        html = (GOC / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        ico = (GOC / "maychu/web/giaodien/icon.js").read_text(encoding="utf-8")
        self.assertIn("<b>' + tenTk(x) + '</b>'", js)
        self.assertIn("(x.ten_hien ? esc(x.ten_hien) : tk) + (x.goi_ten ? '&nbsp;·&nbsp;<span class=\"nw\">' + esc(x.goi_ten)", js)   # Y31 G3
        self.assertIn("ICON.logo_chatgpt", js)
        self.assertNotIn("Logo ChatGPT: chờ file chính thức", js + html)
        tep = (GOC / "maychu/web/giaodien/logo/chatgpt.svg").read_bytes()
        self.assertEqual((len(tep), hashlib.sha256(tep).hexdigest()[:12]), (2415, "75c1e9fffa5e"))   # chép nguyên
        self.assertNotIn(b"<script", tep)
        import re
        d = json.loads(re.search(r'const ICON=(\{.*?\});?\s*\n', ico, re.S).group(1))
        self.assertIn('fill="black"', d["logo_chatgpt"])
        self.assertIn('width="40" height="40"', d["logo_chatgpt"])     # QĐ170 L1: hiện bằng ô 40
        self.assertIn('width="25" height="25"', d["logo_claude"])      # logo Claude giữ nguyên
        self.assertIn("gio(iso) + '\\u00a0hôm\\u00a0nay'", js)      # QĐ170 L2: "hôm nay" liền cụm
        self.assertIn("*.svg -text", (GOC / ".gitattributes").read_text(encoding="utf-8"))               # giữ đen, không thêm màu (Hướng dẫn OpenAI)
        self.assertNotRegex(d["logo_chatgpt"], r'fill="#|stroke="#')
        self.assertIn(d["logo_chatgpt"], html)                          # hộp Thêm nguồn AI
        for f in ("tailieu/Giayphep_Benthuba.md", "tailieu/Songuongoc.md"):
            self.assertIn("75c1e9fffa5e", (GOC / f).read_text(encoding="utf-8"))
        self.assertGreaterEqual(tuple(map(int, (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))), (0, 7, 3))
        muc = (GOC / "THAYDOI.md").read_text(encoding="utf-8").split("## 0.7.3", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Tóm tắt:", muc)


if __name__ == "__main__":
    unittest.main()
