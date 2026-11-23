"""Bài kiểm bản 0.7.1 (QĐ164, Y24): chặn nối trùng tài khoản gói, nút Gỡ tài khoản, không hiện sẵn ô tài khoản 02.
Dùng 02 công cụ giả lập CLI (không gọi mạng). Định danh trong bài chỉ là email giả, tên miền `.invalid` (QĐ126)."""
import base64
import json
import os
import stat
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from maychu.dulieu import khoitao, ketnoi, maso
from maychu.hethong.mohinh import dangnhap_goi as dg
from maychu.web import api

A, B = "nguoi-a@vidu.invalid", "nguoi-b@vidu.invalid"

CLAUDE_GIA = r'''
import json, os, sys, pathlib
noi = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or os.environ["GIA_MACDINH_CLAUDE"])
noi.mkdir(parents=True, exist_ok=True)
dd = noi / "dinhdanh.json"
if sys.argv[1:3] == ["auth", "status"]:
    d = {"loggedIn": dd.exists(), "subscriptionType": "max"}
    if dd.exists():
        d.update(json.loads(dd.read_text()))
    print(json.dumps(d)); sys.exit(0)
if sys.argv[1:3] == ["auth", "logout"]:
    if os.environ.get("GIA_DANGXUAT_HONG"):
        sys.exit(1)
    if dd.exists():
        dd.unlink()
    print("Successfully logged out"); sys.exit(0)
print("If the browser didn't open, visit: https://claude.ai/oauth/authorize?code=true&state=gia", flush=True)
for dong in sys.stdin:
    email, _, org = dong.strip().partition("|")
    dd.write_text(json.dumps({"email": email, "orgId": org or None}))
    print("Login successful.", flush=True); sys.exit(0)
'''
CODEX_GIA = r'''
import base64, json, os, sys, time, pathlib
noi = pathlib.Path(os.environ.get("CODEX_HOME") or os.environ["GIA_MACDINH_CODEX"])
noi.mkdir(parents=True, exist_ok=True)
au = noi / "auth.json"
if sys.argv[1:3] == ["login", "status"]:
    if au.exists():
        print("Logged in using ChatGPT", file=sys.stderr); sys.exit(0)
    print("Not logged in", file=sys.stderr); sys.exit(1)
if sys.argv[1:2] == ["logout"]:
    if au.exists():
        au.unlink()
    print("Successfully logged out"); sys.exit(0)
print("1. Open this link in your browser\n   https://auth.openai.com/codex/device\n"
      "2. Enter this one-time code\n   KQ7M-4XRT\n", flush=True)
time.sleep(0.3)
to_chuc = os.environ.get("GIA_TOCHUC") or None
than = base64.urlsafe_b64encode(json.dumps({"email": os.environ["GIA_EMAIL"],
       "https://api.openai.com/auth": {"chatgpt_account_id": to_chuc}}).encode()).decode().rstrip("=")
au.write_text(json.dumps({"OPENAI_API_KEY": None, "tokens": {"id_token": "e30." + than + ".gia", "account_id": to_chuc}}))
print("Successfully logged in", file=sys.stderr, flush=True)
'''


def _tao_cli(thumuc: Path, ten: str, ma: str) -> str:
    """Linux: tệp chạy thẳng; Windows: thêm tệp .cmd gọi Python (để chạy được bài trên máy anh)."""
    p = thumuc / (ten + ".py")
    p.write_text(f"#!{sys.executable}\n" + textwrap.dedent(ma), encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    if os.name != "nt":
        return str(p)
    c = thumuc / (ten + ".cmd")
    c.write_text(f'@"{sys.executable}" "{p}" %*\r\n', encoding="utf-8")
    return str(c)


class KiemY24(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        g = self.g = Path(self.tam.name)
        bien = ("IGM360_THUMUC_DULIEU", "IGM360_CLAUDE_CLI", "IGM360_CODEX_CLI", "IGM360_THUMUC_CLAUDE",
                "IGM360_THUMUC_CHATGPT", "GIA_MACDINH_CLAUDE", "GIA_MACDINH_CODEX", "GIA_EMAIL", "GIA_TOCHUC",
                "GIA_DANGXUAT_HONG", "CODEX_HOME", "CLAUDE_CONFIG_DIR")
        self.cu = {k: os.environ.get(k) for k in bien}
        for k in ("GIA_EMAIL", "GIA_TOCHUC", "GIA_DANGXUAT_HONG", "CODEX_HOME", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(k, None)
        os.environ.update(IGM360_THUMUC_DULIEU=str(g / "dulieu"), IGM360_CLAUDE_CLI=_tao_cli(g, "claude_gia", CLAUDE_GIA),
                          IGM360_CODEX_CLI=_tao_cli(g, "codex_gia", CODEX_GIA), IGM360_THUMUC_CLAUDE=str(g / "claude"),
                          IGM360_THUMUC_CHATGPT=str(g / "codex"), GIA_MACDINH_CLAUDE=str(g / "claude"),
                          GIA_MACDINH_CODEX=str(g / "codex"))
        khoitao.tao_het(g / "dulieu")
        dg._PHIEN.clear()
        dg._NHO_TRANGTHAI.clear()
        if not hasattr(os, "killpg"):   # Windows: không có killpg, _dung tự chuyển sang terminate
            self.vakp = mock.patch.object(dg.os, "killpg", side_effect=OSError, create=True)
            self.vakp.start()
        self.p = {"nguoidung_id": maso.tao()}

    def tearDown(self):
        for k in list(dg._PHIEN):
            dg.huy(*k)
        if hasattr(self, "vakp"):
            self.vakp.stop()
        for k, v in self.cu.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tam.cleanup()

    # ---- công cụ
    def _claude(self, tk: int, email: str, org: str = "") -> dict:
        self.assertIn("url", dg.bat_dau("claude", tk))
        return dg.dan_ma("claude", tk, f"{email}|{org}")

    def _chatgpt(self, tk: int, email: str, org: str = "") -> dict:
        os.environ["GIA_EMAIL"], os.environ["GIA_TOCHUC"] = email, org
        self.assertIn("url", dg.bat_dau("chatgpt", tk))
        for _ in range(80):
            kq = dg.hoi("chatgpt", tk)
            if not kq.get("cho"):
                return kq
            time.sleep(0.1)
        self.fail("ChatGPT giả chưa xong")

    def _g06(self) -> dict:
        cn = ketnoi.mo("Viecnen")
        try:
            return dict(cn.execute("SELECT ma, trangthai FROM nguon_ai").fetchall())
        finally:
            cn.close()

    def _f04(self) -> list:
        cn = ketnoi.mo("Nhatky")
        try:
            return cn.execute("SELECT lenhcon, thamso_tomtat, ketqua, lydo_chan FROM nhatky_thaotac"
                              " WHERE congcu = 'mohinh' ORDER BY luc, rowid").fetchall()
        finally:
            cn.close()

    def _o(self, goi: str = "claude") -> list:
        return [x["taikhoan"] for x in dg.tinh_hinh_goi()[goi]]

    # ---- (1) chặn trùng
    def test_so_dinh_danh(self):
        self.assertTrue(dg.trung((A, "org1"), (A, "org1")))
        self.assertTrue(dg.trung((A, None), (A, "org1")))
        self.assertFalse(dg.trung((A, "org1"), (A, "org2")))   # cùng email, 02 tổ chức (02 gói riêng)
        self.assertFalse(dg.trung((A, "org1"), (B, "org1")))   # 02 chỗ ngồi cùng gói Team
        self.assertFalse(dg.trung(None, (A, None)))
        than = base64.urlsafe_b64encode(json.dumps({"email": A}).encode()).decode().rstrip("=")
        self.assertEqual(dg._jwt_than("x." + than + ".y")["email"], A)
        self.assertEqual(dg._jwt_than("hong"), {})

    def test_claude_trung_tai_khoan_01_bi_chan(self):
        self.assertTrue(self._claude(1, A, "org1").get("xong"))
        kq = self._claude(2, A.upper(), "org1")   # email viết hoa vẫn là cùng tài khoản
        self.assertEqual(kq["loi"], "Tài khoản này đã kết nối ở tài khoản 01")
        self.assertFalse(dg.trang_thai("claude", 2, bo_nho=True)["da_noi"])
        self.assertNotIn("goi_claude_02", self._g06())
        self.assertFalse(dg.thu_muc("claude", 2).exists())
        self.assertEqual(self._o(), [1])

    def test_claude_tai_khoan_khac_duoc_noi(self):
        self._claude(1, A, "org1")
        self.assertTrue(self._claude(2, B, "org2").get("xong"))
        self.assertEqual(self._g06(), {"goi_claude_01": "dung", "goi_claude_02": "dung"})
        self.assertEqual(self._o(), [1, 2])
        self.assertTrue(self._claude(2, B, "org2").get("xong"))   # đăng nhập lại chính ô 02: không tự chặn mình

    def test_chatgpt_trung_bi_chan(self):
        self.assertTrue(self._chatgpt(1, A, "acc1").get("xong"))
        kq = self._chatgpt(2, A, "acc1")
        self.assertEqual(kq["loi"], "Tài khoản này đã kết nối ở tài khoản 01")
        self.assertNotIn("goi_chatgpt_02", self._g06())
        self.assertEqual(self._o("chatgpt"), [1])
        self.assertTrue(self._chatgpt(2, B, "acc2").get("xong"))
        self.assertEqual(self._o("chatgpt"), [1, 2])

    def test_khong_doc_duoc_dinh_danh_thi_khong_chan(self):
        self._claude(1, "", "")   # CLI không trả email
        self.assertTrue(self._claude(2, "", "").get("xong"))

    def test_dinh_danh_khong_ra_giao_dien_khong_vao_f04(self):
        self.assertTrue(api.goi_bat_dau("claude", api.TaiKhoanGoi(taikhoan=1), self.p)["url"])
        api.goi_dan_ma(api.MaGoi(taikhoan=1, ma=f"{A}|org1"), self.p)
        api.goi_bat_dau("claude", api.TaiKhoanGoi(taikhoan=2), self.p)
        with self.assertRaises(HTTPException) as e:
            api.goi_dan_ma(api.MaGoi(taikhoan=2, ma=f"{A}|org1"), self.p)
        self.assertEqual((e.exception.status_code, e.exception.detail),
                         (409, {"loi": "Tài khoản này đã kết nối ở tài khoản 01", "trung_voi": 1}))
        f04 = self._f04()
        self.assertEqual([r[0] for r in f04], ["batdau_goi", "dangnhap_goi", "batdau_goi", "dangnhap_goi"])
        self.assertEqual(f04[-1][1:], ("Gói Claude tài khoản 02", "bichan", "trùng tài khoản 01"))
        ra = json.dumps([dg.tinh_hinh_goi(), dg.danh_sach(), f04], ensure_ascii=False, default=str)
        self.assertNotIn("vidu.invalid", ra)
        self.assertNotIn("org1", ra)

    # ---- (2) gỡ tài khoản
    def test_go_tai_khoan_02(self):
        self._claude(1, A)
        self._claude(2, B)
        kq = api.goi_go("claude", api.TaiKhoanGoi(taikhoan=2), self.p)
        self.assertEqual(kq, {"ok": True, "co_dong_g06": True})
        self.assertEqual(self._g06(), {"goi_claude_01": "dung", "goi_claude_02": "ngung"})   # giữ dòng
        self.assertFalse(dg.trang_thai("claude", 2, bo_nho=True)["da_noi"])
        self.assertEqual(self._o(), [1])
        self.assertEqual(self._f04()[-1][:3], ("go_goi", "Gói Claude tài khoản 02", "dat"))
        self.assertEqual(self._o(), [1])   # hỏi lại lần nữa vẫn không tự bật
        self.assertTrue(self._claude(2, B).get("xong"))   # thêm lại: bật lại đúng dòng cũ
        self.assertEqual(self._g06()["goi_claude_02"], "dung")

    def test_go_tai_khoan_01_o_2_giu_ten(self):
        self._claude(1, A)
        self._claude(2, B)
        self.assertTrue(dg.go("claude", 1)["ok"])
        self.assertEqual(self._g06(), {"goi_claude_01": "ngung", "goi_claude_02": "dung"})
        self.assertEqual(self._o(), [2])   # Z6-TK: gỡ Tài khoản 1 thì ô Tài khoản 2 giữ tên
        self.assertTrue(dg.go("claude", 2)["ok"])
        self.assertEqual(self._o(), [])    # gỡ hết: giao diện hiện dòng "Chưa có tài khoản"
        self.assertTrue(self._claude(1, A).get("xong"))   # đăng nhập lại ô 01: bật lại dòng cũ
        self.assertEqual(self._o(), [1])

    def test_go_khi_dang_xuat_hong(self):
        self._claude(1, A)
        self._claude(2, B)
        os.environ["GIA_DANGXUAT_HONG"] = "1"
        with self.assertRaises(HTTPException) as e:
            api.goi_go("claude", api.TaiKhoanGoi(taikhoan=2), self.p)
        self.assertIn("Chưa đăng xuất được tài khoản 02", e.exception.detail)
        self.assertEqual(self._g06()["goi_claude_02"], "dung")
        self.assertEqual(self._f04()[-1][:3], ("go_goi", "Gói Claude tài khoản 02", "loi"))

    def test_go_chatgpt(self):
        self._chatgpt(1, A)
        self._chatgpt(2, B)
        self.assertTrue(dg.go("chatgpt", 2)["ok"])
        self.assertEqual(self._g06()["goi_chatgpt_02"], "ngung")
        self.assertEqual(self._o("chatgpt"), [1])

    # ---- (3) không hiện sẵn ô tài khoản 02
    def test_thu_muc_cu_khong_hien_o(self):
        self._claude(1, A)
        tm = dg.thu_muc("claude", 2)
        tm.mkdir(parents=True)   # thư mục còn lại từ 01 lượt bỏ dở trước đây
        self.assertEqual(self._o(), [1])
        dg.huy("claude", 2)
        self.assertFalse(tm.exists())

    def test_hoi_trang_thai_khong_tao_thu_muc(self):
        self.assertFalse(dg.trang_thai("claude", 2, bo_nho=True)["da_noi"])
        self.assertFalse(dg.thu_muc("claude", 2).exists())
        self.assertEqual(self._o(), [1])
        self.assertFalse(dg.thu_muc("claude", 2).exists())

    def test_dang_dang_nhap_khong_hien_huy_thi_don(self):
        self._claude(1, A)
        api.goi_bat_dau("claude", api.TaiKhoanGoi(taikhoan=2), self.p)
        self.assertEqual(self._o(), [1])   # Z6-TK: ô chỉ hiện sau khi đăng nhập xong
        api.goi_huy("claude", api.TaiKhoanGoi(taikhoan=2), self.p)
        self.assertEqual(self._o(), [1])
        self.assertFalse(dg.thu_muc("claude", 2).exists())
        self.assertEqual(self._f04()[-1][:3], ("batdau_goi", "Gói Claude tài khoản 02", "dat"))

    def test_bo_do_qua_15_phut_thi_don(self):
        self._claude(1, A)
        dg.bat_dau("claude", 2)
        dg._PHIEN[("claude", 2)]["bat_luc"] -= dg.HAN_PHIEN_GIAY + 1
        self.assertEqual(self._o(), [1])
        self.assertNotIn(("claude", 2), dg._PHIEN)
        self.assertFalse(dg.thu_muc("claude", 2).exists())

    def test_o_da_co_g06_khong_bi_xoa_thu_muc(self):
        self._claude(1, A)
        self._claude(2, B)
        (dg.thu_muc("claude", 2) / "dinhdanh.json").unlink()   # phiên hết hạn: có dòng G06, chưa đăng nhập
        dg._NHO_TRANGTHAI.clear()
        dg.huy("claude", 2)
        self.assertTrue(dg.thu_muc("claude", 2).exists())
        self.assertEqual([(x["taikhoan"], x["da_noi"]) for x in dg.tinh_hinh_goi()["claude"]], [(1, True), (2, False)])

    def test_giao_dien(self):
        js = (Path(api.__file__).parent / "giaodien" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("Thêm tài khoản thứ 02", js)
        self.assertIn("'Thêm tài khoản ' + ten + ' khác</button>'", js)
        self.assertIn("xacnhan('Thêm tài khoản ' + ten + ' khác?', 'Dùng khi anh có 02 gói riêng, mỗi gói 01 tài khoản ' + ten", js)
        self.assertIn("'Tiếp tục', () => batDauDn(g, o)", js)
        self.assertIn("ICON['user-minus'] + 'Gỡ tài&nbsp;khoản</button>'", js)
        self.assertIn("xacnhan('Gỡ ' + ten + '?', 'Phần mềm ngừng dùng tài khoản này, ô ẩn khỏi màn.", js)
        self.assertIn("bao('Đã gỡ ' + ten + '. Nhật ký đã ghi.')", js)
        self.assertIn("' này đã kết&nbsp;nối ở Tài&nbsp;khoản&nbsp;' + D.trung[g] + '. Phần mềm không tạo ô&nbsp;mới.", js)
        self.assertIn("Đăng nhập tài khoản ' + dn.tk + '</div>", js)                      # QĐ177 (Z9c): bỏ đuôi tên nguồn
        self.assertIn("bao('Đã kết nối ' + tenNguon({goi: 'claude'}) + ', tài khoản ' + dn.tk + '.')", js)
        self.assertIn("D.trung.claude = (e.ct || {}).trung_voi", js)
        self.assertIn("'Đăng nhập để dùng làm nguồn ưu&nbsp;tiên&nbsp;' + uu", js)
        self.assertIn("if (rong && !dn.url) h += ", js)   # U5-2: đang đăng nhập lần đầu thì ẩn dòng "Chưa có tài khoản"
        thay = Path(api.__file__).parents[2] / "THAYDOI.md"
        muc = thay.read_text(encoding="utf-8").split("## 0.7.1", 1)[1].split("\n## ", 1)[0]   # U5-1
        self.assertIn("ở Tài khoản 1", muc)
        self.assertIn("chỉ hiện sau khi đăng nhập xong", muc)
        self.assertNotIn("đang đăng nhập hoặc", muc)
        ico = (Path(api.__file__).parent / "giaodien" / "icon.js").read_text(encoding="utf-8")
        self.assertIn("lucide lucide-user-minus", ico)
        self.assertIn("n.trangthai === 'dung').forEach", js)


if __name__ == "__main__":
    unittest.main()
