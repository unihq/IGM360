"""Bài kiểm 0.10.0 bước 8c – số ngăn Mức dùng (QĐ564 B; CDA phiếu 06 mục 13.4): cửa sổ 05 giờ và đỉnh 60 ngày theo thời
điểm tuyệt đối; ô giờ theo múi đã chọn (③); tiền tháng theo ngày số liệu (②), phần triệu USD; 0 bảng, 0 cột."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso, muigio
from maychu.hethong.caidat import thongso
from maychu.hethong.mohinh import mucdung

VN = timezone(timedelta(hours=7))
BAY = datetime(2026, 11, 27, 10, 30, tzinfo=VN)


class KiemMucDung(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"})
        bien.start()
        self.addCleanup(bien.stop)
        muigio.xoa_dem()
        self.addCleanup(muigio.xoa_dem)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)

    def ghi(self, luc, vao, ra=0, nguon="ng1", tien=None):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            cn.execute("INSERT INTO nhatky_ai (id, luc, nguon_ai_id, luong_vao, luong_ra, sotien, tien_ma, ketqua)"
                       " VALUES (?, ?, ?, ?, ?, ?, 'USD', 'xong')", (maso.tao(), muigio.gio_luu(luc), nguon, vao, ra, tien))
            cn.commit()
        finally:
            cn.close()

    def test_cua_so_dinh_gio_ban_tien(self):
        self.ghi(BAY - timedelta(hours=1), 1000, 500)                       # trong cửa sổ 05 giờ hiện tại
        self.ghi(BAY - timedelta(hours=4, minutes=59), 2000)                # còn trong cửa sổ
        self.ghi(BAY - timedelta(hours=5, minutes=1), 9000)                 # ngoài cửa sổ hiện tại
        self.ghi(BAY - timedelta(days=20), 40000, nguon="ng2", tien=3 * mucdung.TRIEU)   # đỉnh cũ, tháng 11
        self.ghi(BAY - timedelta(days=20, hours=3), 30000, nguon="ng2")     # cùng cửa sổ 05 giờ với lượt trên
        self.ghi(BAY - timedelta(days=61), 999999)                           # ngoài 60 ngày
        kq = mucdung.tong_hop(self.dl, bay=BAY)
        self.assertEqual(kq["cua_so"], 3500)
        self.assertEqual(kq["dinh"], 70000)
        self.assertEqual(kq["gio"][-1], 10)                                  # ô cuối = giờ hiện tại theo múi chọn
        self.assertEqual(sum(kq["tok_gio"]), 1500 + 2000 + 9000)
        self.assertEqual(kq["cs_gio"][-1], 3500)
        self.assertEqual(kq["luot_24h"], 3)
        self.assertEqual(kq["ban"][9], round(1500 / 7))                      # 09:30 → ô 09h
        self.assertEqual((kq["thang"], kq["tien_api"], kq["tien_thang"]), (11, 3 * mucdung.TRIEU, 3 * mucdung.TRIEU))
        self.assertTrue(kq["du"])
        self.assertEqual((kq["dinh_tu"], kq["dinh_den"]), ("2026-11-07T07:00:00+07:00", "2026-11-07T11:00:00+07:00"))   # 07:30 và 10:30

    def test_chua_du_luot_khi_dinh_bang_0(self):   # CPO NGUONG-AP: đỉnh 0 → khung; 01 lượt có token → so được
        self.ghi(BAY - timedelta(hours=1), 0)
        self.assertFalse(mucdung.tong_hop(self.dl, bay=BAY)["du"])
        self.ghi(BAY - timedelta(hours=2), 1)
        kq = mucdung.tong_hop(self.dl, bay=BAY)
        self.assertEqual((kq["du"], kq["dinh"]), (True, 1))

    def test_o_gio_theo_mui_da_chon(self):
        self.ghi(BAY - timedelta(minutes=20), 100)                           # 10:10 giờ VN = 03:10 UTC
        with mock.patch.object(muigio, "chon", return_value=timezone.utc):
            kq = mucdung.tong_hop(self.dl, bay=BAY)
        self.assertEqual(kq["gio"][-1], 3)
        self.assertEqual(kq["tok_gio"][-1], 100)
        self.assertEqual(kq["cua_so"], 100)                                  # cửa sổ không đổi theo múi

    def test_loc_nguon(self):
        self.ghi(BAY - timedelta(hours=1), 100, nguon="ng1")
        self.ghi(BAY - timedelta(hours=1), 50, nguon="ng2")
        kq = mucdung.tong_hop(self.dl, bay=BAY, nguon="ng2")
        self.assertEqual((sum(kq["tok_gio"]), kq["cua_so"]), (50, 150))      # lọc chỉ áp cho "Token mỗi giờ"
        self.assertEqual([x["id"] for x in kq["nguon_co"]], ["ng1", "ng2"])


if __name__ == "__main__":
    unittest.main()
