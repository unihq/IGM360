"""Bài kiểm bản 0.7.4 (QĐ173, Y29): hồ sơ Claude tài khoản 01 nằm trong ổ lưu (CLAUDE_CONFIG_DIR), còn sau khi dựng
lại vùng chứa. Mô phỏng: ổ lưu = 01 thư mục giữ nguyên; vùng chứa = HOME, mỗi lần dựng lại là 01 HOME mới, trống.
Chỉ dùng tên giả (QĐ126), không gọi CLI thật, không đọc hồ sơ thật."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao
from maychu.hethong.mohinh import dangnhap_goi as dg

GOC = Path(__file__).resolve().parents[2]
TEN_GIA = "Nguoi Gia Demo"
HO_SO = {"oauthAccount": {"displayName": TEN_GIA, "emailAddress": "nguoigia@vidu.invalid", "planDisplayName": "Ultra"}}


class KiemHoSoTrongOLuu(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.t = Path(self.tam.name)
        self.oluu = self.t / "oluu_claude"            # ổ gắn igm360-claude:/home/igm/.claude
        self.oluu.mkdir()
        (self.oluu / ".credentials.json").write_text("{}", encoding="utf-8")   # mã đăng nhập giả có sẵn
        self.cu = {k: os.environ.get(k) for k in ("IGM360_THUMUC_CLAUDE", "CLAUDE_CONFIG_DIR", "HOME", "USERPROFILE",
                                                  "IGM360_THUMUC_DULIEU")}
        os.environ.update(IGM360_THUMUC_CLAUDE=str(self.oluu), IGM360_THUMUC_DULIEU=str(self.t / "dulieu"))
        dg._NHO_TRANGTHAI.clear()
        dg._PHIEN.clear()
        self.lan = 0

    def tearDown(self):
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    def _dung_vung_chua(self, co_bien: bool) -> Path:
        """01 lần dựng vùng chứa: HOME mới, trống; image 0.7.4 đặt CLAUDE_CONFIG_DIR, image 0.7.3 không đặt."""
        self.lan += 1
        home = self.t / f"vungchua_{self.lan:02d}"
        home.mkdir()
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
        if co_bien:
            os.environ["CLAUDE_CONFIG_DIR"] = str(self.oluu)
        else:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        dg._NHO_TRANGTHAI.clear()
        return home

    def _dang_nhap(self) -> None:
        """CLI đăng nhập ghi hồ sơ vào CLAUDE_CONFIG_DIR của tài khoản 01, không có biến thì vào HOME."""
        noi = Path(dg._env("claude", 1)["CLAUDE_CONFIG_DIR"]) if "CLAUDE_CONFIG_DIR" in dg._env("claude", 1) \
            else Path(os.environ["HOME"])
        (noi / ".claude.json").write_text(json.dumps(HO_SO), encoding="utf-8")

    def _the(self) -> tuple:
        khoitao.tao_het(self.t / "dulieu") if not (self.t / "dulieu").exists() else None
        with mock.patch.object(dg, "trang_thai", return_value={"da_noi": True, "goi_dang_dung": "max"}):
            o = dg.tinh_hinh_goi()["claude"][0]
        return o["ten_hien"], o["goi_ten"]

    def test_ban_cu_mat_ho_so_khi_dung_lai(self):
        # Đối chứng 0.7.3: hồ sơ ở HOME (ngoài ổ lưu) → dựng lại vùng chứa là mất, thẻ lùi "Max" (lỗi Y28 C1)
        self._dung_vung_chua(co_bien=False)
        self._dang_nhap()
        self.assertEqual(self._the(), (TEN_GIA, "Ultra"))
        self._dung_vung_chua(co_bien=False)
        self.assertEqual(self._the(), (None, "Max"))

    def test_ban_moi_giu_ho_so_khi_dung_lai(self):
        # Lần đầu sau cập nhật: ổ lưu có mã đăng nhập, chưa có hồ sơ → lùi "Tài khoản 1 · Max", không lỗi
        self._dung_vung_chua(co_bien=True)
        self.assertEqual(self._the(), (None, "Max"))
        # Anh gỡ, đăng nhập lại 01 lần → hồ sơ ghi vào ổ lưu → "Tên · Ultra"
        self._dang_nhap()
        self.assertTrue((self.oluu / ".claude.json").is_file())
        self.assertEqual(self._the(), (TEN_GIA, "Ultra"))
        # Dựng lại vùng chứa 02 lần (02 lần "Cập nhật ngay") → hồ sơ vẫn còn
        for _ in range(2):
            home = self._dung_vung_chua(co_bien=True)
            self.assertFalse((home / ".claude.json").exists())
            self.assertEqual(self._the(), (TEN_GIA, "Ultra"))
        self.assertTrue((self.oluu / ".credentials.json").is_file())   # mã đăng nhập cũ không bị đụng
        # Đ3 (CDA K-HS, QĐ164): 0 tệp dữ liệu nào (bảng, F04, nhật ký) chứa tên, email
        for tep in (self.t / "dulieu").rglob("*"):
            if tep.is_file():
                b = tep.read_bytes()
                self.assertNotIn(TEN_GIA.encode(), b, tep.name)
                self.assertNotIn(b"nguoigia@vidu.invalid", b, tep.name)

    def test_tai_khoan_02_van_dung_thu_muc_rieng(self):
        self._dung_vung_chua(co_bien=True)
        tk2 = self.oluu / "taikhoan_02"
        self.assertEqual(dg._env("claude", 1)["CLAUDE_CONFIG_DIR"], str(self.oluu))
        self.assertEqual(dg._env("claude", 2, tao=False)["CLAUDE_CONFIG_DIR"], str(tk2))   # ghi đè biến của image
        self.assertEqual(dg._tep_hoso_claude(1), self.oluu / ".claude.json")
        self.assertEqual(dg._tep_hoso_claude(2), tk2 / ".claude.json")
        self.assertNotEqual(dg._tep_hoso_claude(1), dg._tep_hoso_claude(2))

    def test_chan_trung_hoi_dung_cho_tai_khoan_01(self):
        # Y24: so email tài khoản 01 bằng `auth status` chạy với CLAUDE_CONFIG_DIR = ổ lưu (nơi có hồ sơ, có email)
        self._dung_vung_chua(co_bien=True)
        thay = {}

        def chay(lenh, **kw):
            thay["env"] = kw.get("env") or {}
            return mock.Mock(stdout=json.dumps({"loggedIn": True, "email": "NguoiGia@vidu.invalid", "orgId": "org_gia"}),
                             returncode=0)
        with mock.patch.object(dg.subprocess, "run", side_effect=chay):
            self.assertEqual(dg._dinh_danh("claude", 1), ("nguoigia@vidu.invalid", "org_gia"))
        self.assertEqual(thay["env"].get("CLAUDE_CONFIG_DIR"), str(self.oluu))

    def test_tieu_de_the_z9(self):
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        html = (GOC / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        self.assertIn("const GOI_TEN = {claude: 'Claude&nbsp;·&nbsp;Code', chatgpt: 'ChatGPT&nbsp;·&nbsp;Codex'}", js)
        self.assertIn('<b class="khoi">Claude&nbsp;·&nbsp;Code</b>', html)
        self.assertIn('<b class="khoi">ChatGPT&nbsp;·&nbsp;Codex</b>', html)
        self.assertNotIn("qua&nbsp;Codex", js + html)
        self.assertIn("GOI_NGAN = {claude: 'Gói Claude', chatgpt: 'Gói ChatGPT'}", js)   # chỗ khác giữ, chờ anh chốt

    def test_image_dat_bien_dung_o_luu(self):
        df = (GOC / "Dockerfile").read_text(encoding="utf-8")
        dc = (GOC / "docker-compose.yml").read_text(encoding="utf-8")
        m = re.search(r"CLAUDE_CONFIG_DIR=(\S+)", df)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "/home/igm/.claude")
        self.assertEqual(m.group(1), dg.GOI["claude"]["thumuc"])            # tài khoản N > 1 nằm trong cùng ổ
        self.assertIn("igm360-claude:" + m.group(1), dc)                     # đúng chỗ ổ gắn
        self.assertNotIn("CLAUDE_CONFIG_DIR", dc)                            # chỉ đặt ở image: cập nhật là có, không sửa tệp compose
        self.assertEqual((GOC / "VERSION").read_text(encoding="utf-8").strip(), "0.7.4")
        muc = (GOC / "THAYDOI.md").read_text(encoding="utf-8").split("## 0.7.4", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Tóm tắt:", muc)
        self.assertIn("đăng nhập lại tài khoản Claude 1", muc)


if __name__ == "__main__":
    unittest.main()
