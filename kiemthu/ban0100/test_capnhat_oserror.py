"""Bài kiểm 0.10.0 – QA lượt 03 ghi nhận (a): kiểm bản mới gặp lỗi đọc tệp (vd. SSL_CERT_FILE trỏ tệp CA không đọc được
→ PermissionError lúc dựng kết nối) không làm GET /api/capnhat trả 500: giữ kết quả cũ / báo "chưa kiểm được"."""

import unittest
from unittest import mock

from maychu.hethong import capnhat


class KiemOSError(unittest.TestCase):
    def setUp(self):
        cu = dict(capnhat._NHO)
        self.addCleanup(lambda: (capnhat._NHO.clear(), capnhat._NHO.update(cu)))
        capnhat._NHO.update(luc=0.0, luc_dat=0.0, ban_moi=None, loi=None, nhan_thaydoi=None, tomtat={}, thaydoi=[])

    def test_hoi_kho_anh_loi_quyen_doc(self):
        with mock.patch.object(capnhat, "_hoi_ghcr", side_effect=PermissionError(13, "Permission denied")):
            kq = capnhat.kiem_tra(bat_buoc=True)
        self.assertFalse(kq["co_ban_moi"])
        self.assertTrue(capnhat._NHO["loi"].startswith("Chưa kiểm được bản mới"))

    def test_tai_thaydoi_loi_quyen_doc(self):
        with mock.patch.object(capnhat, "_hoi_ghcr", return_value=("9.9.9", "9.9.9")), \
                mock.patch.object(capnhat, "_tai_thaydoi_kq", side_effect=OSError("không đọc được tệp CA")):
            kq = capnhat.kiem_tra(bat_buoc=True)
        self.assertEqual(kq["ban_moi"], "9.9.9")
        self.assertIn("mã trả về 0", capnhat._NHO["loi"])


if __name__ == "__main__":
    unittest.main()
