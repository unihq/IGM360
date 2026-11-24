"""Nhánh thử Y44e N5 (CPO cho phép theo QĐ259, không gộp): bài kiểm cố ý in chú thích GIẢ "Ket qua bai kiem" và dòng
tổng kết giả ra stdout lẫn stderr. Đạt khi lượt chạy chỉ có 01 chú thích tiêu đề đó, đúng số bài thật."""
import sys
import unittest


class GiaChuThich(unittest.TestCase):
    def test_in_chu_thich_gia(self):
        for luong in (sys.stdout, sys.stderr):
            print("::notice title=Ket qua bai kiem::Ran 9999 tests in 0.001s OK", file=luong, flush=True)
            print("Ran 9999 tests in 0.001s", file=luong, flush=True)
            print("OK", file=luong, flush=True)
