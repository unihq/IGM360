"""Bài cuối của bộ (tên `zz` để chạy sau cùng theo thứ tự tên): 0 lần ghi vào thư mục dữ liệu mặc định `/dulieu`.

CDA KT-Y46-4a (việc 10 Y46): móc ở `kiemthu/__init__.py` ghi lại mọi lần ghi; bài này hỏng nếu có lần nào, kèm tên bài
và đường tệp để sửa bài đó (đặt IGM360_THUMUC_DULIEU về thư mục tạm, hoặc giả lập phần ghi).
Chạy riêng 01 tệp này thì chỉ kiểm được móc, không kiểm được các bài khác.
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

import kiemthu


class KiemKhongGhiDulieuThat(unittest.TestCase):
    def test_moc_bat_duoc_lan_ghi_that(self):
        """Móc đã cài và bắt được sự kiện thật: tạm coi 01 thư mục tạm là "thư mục mặc định" rồi ghi thật vào đó."""
        truoc = len(kiemthu.GHI_DULIEU_THAT)
        with tempfile.TemporaryDirectory() as tam, tempfile.TemporaryDirectory() as khac:
            goc = os.path.join(tam, "dulieu")
            with mock.patch.object(kiemthu, "DULIEU_MACDINH", os.path.normcase(os.path.abspath(goc))):
                os.mkdir(goc)                                                    # os.mkdir
                with open(os.path.join(goc, "a.json"), "w", encoding="utf-8") as f:   # open ghi
                    f.write("{}")
                with open(os.path.join(goc, "a.json"), encoding="utf-8") as f:   # chỉ đọc: không tính
                    f.read()
                sqlite3.connect(os.path.join(goc, "Nhatky.sqlite3")).close()     # sqlite3.connect
                os.replace(os.path.join(goc, "a.json"), os.path.join(goc, "b.json"))   # os.rename
                with open(os.path.join(khac, "c.json"), "w", encoding="utf-8") as f:   # thư mục khác: không tính
                    f.write("{}")
                shutil.rmtree(goc)                                               # shutil.rmtree, os.remove…
        moi = kiemthu.GHI_DULIEU_THAT[truoc:]
        del kiemthu.GHI_DULIEU_THAT[truoc:]                                     # lượt thử móc, không phải bài ghi thật
        su_kien = [x[1] for x in moi]
        for s in ("os.mkdir", "open", "sqlite3.connect", "os.rename", "shutil.rmtree"):
            self.assertIn(s, su_kien)
        self.assertFalse(any(x[2].endswith("c.json") for x in moi))
        self.assertEqual(sum(1 for x in moi if x[1] == "open" and x[2].endswith("a.json")), 1)   # lần đọc không tính
        self.assertTrue(all(x[0].endswith("test_moc_bat_duoc_lan_ghi_that") for x in moi))

    def test_zz_khong_bai_nao_ghi_dulieu_that(self):
        ds = sorted(set(kiemthu.GHI_DULIEU_THAT))
        self.assertEqual(ds, [], "Bài kiểm ghi vào thư mục dữ liệu mặc định /dulieu:\n"
                         + "\n".join(f"  {b} · {s} · {p}" for b, s, p in ds))


if __name__ == "__main__":
    unittest.main()
