"""Bài kiểm khung máy chủ tối thiểu: chỉ dùng thư viện chuẩn của Python và thư viện đã khai."""
import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

import uvicorn

from maychu import khoidong
from maychu.hethong.giamsat import domay


def _cong_trong() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class KiemMayChu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tam = tempfile.TemporaryDirectory()
        os.environ["IGM360_THUMUC_DULIEU"] = cls.tam.name
        os.environ["IGM360_LICH"] = "tat"
        cls.cong = _cong_trong()
        cls.maychu = uvicorn.Server(uvicorn.Config(khoidong.app, host="127.0.0.1", port=cls.cong, log_level="warning"))
        cls.luong = threading.Thread(target=cls.maychu.run, daemon=True)
        cls.luong.start()
        for _ in range(100):
            if cls.maychu.started:
                break
            time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.maychu.should_exit = True
        cls.luong.join(timeout=5)
        cls.tam.cleanup()

    def _lay(self, duong):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.cong}{duong}", timeout=5)

    def test_suckhoe(self):
        tl = self._lay("/suckhoe")
        self.assertEqual(tl.status, 200)
        noidung = json.loads(tl.read())
        self.assertEqual(noidung["trangthai"], "chay")
        self.assertEqual(noidung["phienban"], khoidong.PHIENBAN)

    def test_khong_co_trang_tudong(self):
        for duong in ("/docs", "/redoc", "/openapi.json"):  # "/" là màn hình từ ngày 04 (QĐ88)
            with self.subTest(duong=duong):
                with self.assertRaises(urllib.error.HTTPError) as loi:
                    self._lay(duong)
                self.assertEqual(loi.exception.code, 404)


class KiemDoMay(unittest.TestCase):
    def test_do_may_du_so(self):
        s = domay.do_may()
        for khoa in ("may_ram_tong_mb", "may_ram_con_mb", "may_hoandoi_tong_mb", "ocung_dung_tyle", "so_tientrinh_ai"):
            self.assertIn(khoa, s)
        self.assertGreater(s["may_ram_tong_mb"], 0)

    def test_in_chu_va_json(self):
        s = domay.do_may()
        self.assertIn("CẢ MÁY", domay.in_chu(s))
        self.assertIsInstance(json.loads(json.dumps(s, ensure_ascii=False)), dict)

    def test_so_kieu_viet(self):
        self.assertEqual(domay._so(3812), "3.812")
        self.assertEqual(domay._so(12.5), "12,5")
        self.assertEqual(domay._so(83.0), "83")
        self.assertEqual(domay._so(None), "không đo được")
        self.assertEqual(domay._mb_chu("max"), "không đặt")
        self.assertEqual(domay._mb_chu(None), "không đo được")
        self.assertEqual(domay._mb_chu(520), "520 MB")


if __name__ == "__main__":
    unittest.main()
