"""Bài kiểm 0.10.0 – bản sửa lỗi QA lượt 04 (CPO LUOT04-SUA): (a) 01 dòng D03 sai định dạng khóa không làm hỏng cả
chuông; (b) tin tạo cùng giây với lúc bấm "Đọc hết" vẫn phân được trước / sau (so mili giây trong mã ULID, 0 lược đồ)."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, muigio
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import thongbao


class KiemChuongLuot04(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"})
        bien.start()
        self.addCleanup(bien.stop)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)

    def mo_tin(self, khoa):
        with thongbao._Ghi(self.dl) as w:
            thongbao._mo(w, khoa, None, None)

    def test_a_dong_sai_khoa_khong_hong_ca_chuong(self):
        self.mo_tin("cli_loi:qa")                       # thiếu phần bản – trước đây làm /api/demso trả 500
        self.mo_tin("tenmien_doi:igm.vidu.test:")       # dòng đúng
        with self.assertLogs("igm360.thongbao", level="WARNING") as nk:
            ds = thongbao.danh_sach(None, self.dl)["ds"]
        self.assertEqual([x["loai"] for x in ds], ["tenmien_doi"])
        self.assertIn("cli_loi:qa", "\n".join(nk.output))

    def test_b_cung_giay_phan_theo_mili_giay(self):
        co_dinh = "2026-11-27T22:10:05+07:00"
        with mock.patch.object(muigio, "gio_luu", lambda luc=None: co_dinh):
            self.mo_tin("tenmien_doi:truoc.vidu.test:")   # tạo trước lúc bấm, cùng giây
            time.sleep(0.01)
            thongso.dat_moc_doc("hethong", self.dl)
            time.sleep(0.01)
            thongbao.bao_su_kien("muigio_doi", "Asia/Tokyo", self.dl, nhom="muigio", truoc="Asia/Ho_Chi_Minh")   # sau lúc bấm
            kq = thongbao.danh_sach(None, self.dl)
        moi = {x["loai"]: x["moi"] for x in kq["ds"]}
        self.assertEqual(moi, {"tenmien_doi": False, "muigio_doi": True})
        self.assertEqual(kq["so_moi"], 1)

    def test_b_khac_giay_giu_cach_cu(self):
        thongso.dat_moc_doc("hethong", self.dl)
        self.assertEqual(thongbao._moi({"tao_luc": "2026-11-27T22:10:06+07:00", "id": "X" * 26}, "2026-11-27T22:10:05+07:00",
                                       "Z" * 26), True)
        self.assertEqual(thongbao._moi({"tao_luc": "2026-11-27T22:10:04+07:00", "id": "Z" * 26}, "2026-11-27T22:10:05+07:00",
                                       "0" * 26), False)


if __name__ == "__main__":
    unittest.main()
