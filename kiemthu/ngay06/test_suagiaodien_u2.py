"""Bài kiểm lượt sửa giao diện U2 (QĐ121, QĐ122, QĐ125): tiền khóa API theo tháng kèm chỗ đồng Việt, lúc đăng nhập
gói, dòng tóm tắt mỗi bản trong THAYDOI.md, icon ô dán mã, giữ cụm chữ khi xuống dòng (chạy bằng node nếu máy có)."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from maychu.dulieu import khoitao, ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import capnhat, nhatky
from maychu.hethong.mohinh import congai, dangnhap_goi as dg

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"


class NenDuLieu(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.cu = os.environ.get("IGM360_THUMUC_DULIEU")
        os.environ["IGM360_THUMUC_DULIEU"] = self.tam.name
        khoitao.tao_het(Path(self.tam.name))

    def tearDown(self):
        os.environ.pop("IGM360_THUMUC_DULIEU", None) if self.cu is None else os.environ.__setitem__("IGM360_THUMUC_DULIEU", self.cu)
        self.tam.cleanup()


class KiemTienThang(NenDuLieu):
    def them(self, luc, sotien):
        cn = ketnoi.mo("Nhatky")
        cn.execute("INSERT INTO nhatky_ai (id, luc, sotien, ketqua) VALUES (?, ?, ?, 'xong')", (maso.tao(), luc, sotien))
        cn.close()

    def test_chi_tinh_tu_ngay_01_thang_nay(self):
        bay = datetime.now(MUIGIO_VN)
        dau = bay.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.them(dau.isoformat(timespec="seconds"), 12_280_000)                    # 12,28 USD, đúng 00:00 ngày 01
        self.them((dau - timedelta(seconds=1)).isoformat(timespec="seconds"), 5_000_000)   # tháng trước: không tính
        kq = congai.tom_tat_thang()
        self.assertEqual((kq["thang"], kq["luot"], kq["tien_that_usd"]), (bay.month, 1, 12.28))


class KiemLucDangNhapGoi(NenDuLieu):
    def test_lan_dangnhap_gan_nhat_theo_tai_khoan(self):
        self.assertEqual(dg._lan_dangnhap(), {})                                      # chưa có = đăng nhập lúc cài máy
        nhatky.ghi("mohinh", "dangnhap_goi", dg.nhan_dangnhap("chatgpt", 1), nguoi_id="01JDRVTEST0000000000000000")
        lan = dg._lan_dangnhap()
        self.assertEqual(list(lan), ["Gói ChatGPT tài khoản 01"])
        self.assertTrue(lan["Gói ChatGPT tài khoản 01"].startswith(datetime.now(MUIGIO_VN).date().isoformat()))
        self.assertNotIn(dg.nhan_dangnhap("claude", 1), lan)


class KiemThayDoi(unittest.TestCase):
    def test_doc_dong_tom_tat(self):
        ds = capnhat.phan_tich_thaydoi("# T\n\n## 0.3.0\nTóm tắt: Ngắn gọn\n- Dòng a\n- Dòng b\n\n## 0.2.0\n- Dòng c\n")
        self.assertEqual([(m["ban"], m["tomtat"], len(m["dong"])) for m in ds], [("0.3.0", "Ngắn gọn", 2), ("0.2.0", None, 1)])

    def test_moi_ban_trong_thaydoi_co_tom_tat_ngan(self):
        ds = capnhat.phan_tich_thaydoi((GOC / "THAYDOI.md").read_text(encoding="utf-8"))
        self.assertTrue(ds)
        for m in ds:
            with self.subTest(ban=m["ban"]):
                self.assertTrue(m["tomtat"] and len(m["tomtat"]) < 50, m["tomtat"])
        self.assertEqual(ds[0]["ban"], (GOC / "VERSION").read_text(encoding="utf-8").strip())


class KiemChuGiaoDien(unittest.TestCase):
    def setUp(self):
        self.html = (GD / "index.html").read_text(encoding="utf-8")
        self.js = (GD / "app.js").read_text(encoding="utf-8")

    def test_cac_cho_lech_u2(self):
        self.assertIn("ICON.hash + '<input id=\"ma-claude\"", self.js)                   # P01
        self.assertNotIn("quy đổi tham khảo 07 ngày", self.js)                          # N13
        self.assertIn("Chi phí AI tháng", self.js)
        self.assertIn("chưa có tỷ&nbsp;giá", self.js)                                   # P02 trước ngày 18
        self.assertIn("ICON.logo_chatgpt", self.js)   # N11: ô chờ "LOGO" nay là logo gốc OpenAI (QĐ92, QĐ169)
        self.assertIn("Chưa có tài khoản", self.js)                                     # N10
        self.assertNotIn("'Gói ' + esc(x.goi_dang_dung)", self.js)                      # N09
        self.assertIn('có gì&nbsp;mới</span></div><div id="cn-thaydoi">', self.html)    # N03
        for cum in ("ứng&nbsp;dụng", "24&nbsp;giờ", "30&nbsp;ngày", "06&nbsp;số", "thao&nbsp;tác", "Cài&nbsp;đặt&nbsp;›&nbsp;Thông&nbsp;số"):
            with self.subTest(cum=cum):
                self.assertIn(cum, self.html)                                           # N04, N05, N14
        self.assertNotIn("IGM360&nbsp;", self.html)                                     # đuôi số của tên không bị dính

    def test_cau_bao_may_chu(self):
        nguon = (GOC / "maychu/hethong/mohinh/dangnhap_goi.py").read_text(encoding="utf-8")
        self.assertIn('Bấm \\"Mở trang\\" lấy mã mới rồi dán lại', nguon)              # N12 (giao diện thêm dấu chấm)
        self.assertIn("mọi việc chờ bạn bấm.", (GOC / "maychu/hethong/caidat/thongso.py").read_text(encoding="utf-8"))  # N08

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_ham_giu_cum_va_tien(self):
        dau = self.js.index("const soVN")
        het = self.js.index("\n", self.js.index("const cau ="))
        vnd = re.search(r"^const vnd = .*$", self.js, re.M).group(0)
        mau = ["Đọc 1.240 dòng, có 04 dòng lỗi", "Gói Claude · tài khoản 01", "ưu tiên 2", "IGM360 theo 04 đường",
               "rồi 3. Số", "Mã chưa đúng"]
        ma = self.js[dau:het] + "\n" + vnd + "\nconsole.log(JSON.stringify([" + ",".join(f"cum({json.dumps(m)})" for m in mau) \
            + ", cau('Mã chưa đúng'), cau('Đã xong.'), vnd(12.28, null), vnd(12.28, 25400)]));"
        kq = json.loads(subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
        self.assertEqual(kq[:6], ["Đọc 1.240&nbsp;dòng, có 04&nbsp;dòng lỗi", "Gói Claude&nbsp;· tài&nbsp;khoản&nbsp;01",
                                  "ưu&nbsp;tiên&nbsp;2", "IGM360 theo 04&nbsp;đường", "rồi 3. Số", "Mã chưa đúng"])
        self.assertEqual(kq[6:], ["Mã chưa đúng.", "Đã xong.", "chưa có tỷ&nbsp;giá", "≈&nbsp;312.000&nbsp;đ tham&nbsp;khảo"])


if __name__ == "__main__":
    unittest.main()
