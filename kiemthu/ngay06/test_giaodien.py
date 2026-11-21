"""Bài kiểm giao diện dựng lại từ bản vẽ đã duyệt (QĐ91, QĐ94): đủ chỗ cho dữ liệu màn 13, 08; không còn viền hồng,
số minh hoạ; tên thiết bị phiên theo bản vẽ màn 09."""
import re
import unittest
from pathlib import Path

from maychu.hethong.taikhoan.phien import thietbi_tu

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemGiaoDien(unittest.TestCase):
    def setUp(self):
        self.html = (GD / "index.html").read_text(encoding="utf-8")
        self.js = (GD / "app.js").read_text(encoding="utf-8")

    def test_du_cho_du_lieu(self):
        for ma in ("ds-nguonai", "ds-mohinh", "md-songsong", "ds-ht", "ds-tin", "tc-o", "tc-tieude", "tc-nguon",
                   "sua-tu", "mk-gio", "h-nguonai", "h-them", "ds-thongso", "ds-phien"):
            with self.subTest(ma=ma):
                self.assertIn(f'id="{ma}"', self.html)
                self.assertTrue(ma.startswith("h-") or ma in self.js, ma)

    def test_khong_con_cho_cu(self):
        self.assertNotIn("#F1A7A4", self.html)                       # viền hồng (CDO mục 02, 19)
        self.assertNotIn('type="date"', self.html)                   # ô ngày cố định ngày/tháng/năm (mục 22)
        for cam in ("Shop A", "minhhoa", "Ghi chú bản vẽ", "Lô nạp Shop A", "KQ7M-4XRT"):
            self.assertNotIn(cam, self.html)
        self.assertNotIn("c2pa", (GD / "icon.js").read_text(encoding="utf-8"))

    def test_icon_theo_tu_dien(self):
        ico = (GD / "icon.js").read_text(encoding="utf-8")
        for ten in ("brain-circuit", "calendar-clock", "list-checks", "check", "key-round", "unplug", "clock-alert",
                    "rectangle-ellipsis", "vault", "cloud-download"):
            self.assertIn(f"lucide-{ten}", ico, ten)

    def test_ten_thiet_bi(self):
        self.assertEqual(thietbi_tu("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131 Safari/537.36"), "Máy tính · Chrome trên Windows")
        self.assertEqual(thietbi_tu("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18 Mobile/15E148 Safari/604.1"),
                         "Điện thoại · Safari trên iPhone")


if __name__ == "__main__":
    unittest.main()
