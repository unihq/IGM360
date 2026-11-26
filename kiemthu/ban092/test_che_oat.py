"""Bài kiểm LOI-NANGCLI-3 (c): che.py che cả mã dài hạn tiền tố oat0<số>- (CHANGELOG Claude Code 2.1.332 dòng 110,
self-hosted runner: "its prefix can now end in oat02- as well as oat01-"). Chỗ nhận mã (madaihan.py) giữ oat01-.
Khóa giả ghép lúc chạy.
"""
import unittest

from maychu.hethong.kekhoa import che as chemod
from maychu.hethong.mohinh import madaihan

DUOI = "B" * 30


class KiemCheOat(unittest.TestCase):
    def test_che_oat01_nhu_cu(self):
        self.assertEqual(chemod.che("x " + "sk-ant-oat01-" + DUOI + " y"), "x sk-ant-oat01-•••• y")

    def test_che_oat02_va_oat09(self):
        for so in ("02", "09"):
            with self.subTest(so=so):
                kq = chemod.che("loi " + "sk-ant-oat" + so + "-" + DUOI)
                self.assertNotIn(DUOI, kq)
                self.assertEqual(kq, "loi sk-ant-oat01-••••")

    def test_khong_doi_chu_thuong_va_kieu_khac(self):
        khac = "sk-" + "ant-" + "api03-" + "khong-phai-ma-daihan"   # khóa giả ghép lúc chạy (không phải mã dài hạn)
        self.assertEqual(chemod.che(khac), khac)
        self.assertIsNone(chemod.che(None))
        self.assertEqual(chemod.che(5), 5)

    def test_cho_nhan_ma_van_chi_oat01(self):
        self.assertEqual(madaihan.TIEN_TO, "sk-ant-oat01-")
        self.assertIsNone(madaihan.MA_RE.search("sk-ant-oat02-" + DUOI))
        self.assertIsNotNone(madaihan.MA_RE.search("sk-ant-oat01-" + DUOI))


if __name__ == "__main__":
    unittest.main()
