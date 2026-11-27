"""Bài kiểm 0.10.0 – chuông, tài khoản (QĐ548 B, QĐ551, QĐ553, QĐ559, chữ QĐ566; CDA phiếu 06 mục 12; tin đổi tên miền /
múi giờ QĐ634, QĐ636 – chữ TẠM). Máy chủ: cờ P01 chuong_tamtat, tin sự kiện; giao diện: vị trí, thứ tự, chữ, số tối đa."""

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, muigio
from maychu.hethong.caidat import tenmien, thongso
from maychu.hethong.giamsat import thongbao

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"


class KiemMayChu(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            tenmien.BIEN_GOC: "goc.vidu.test"})
        bien.start()
        self.addCleanup(bien.stop)
        muigio.xoa_dem()
        self.addCleanup(muigio.xoa_dem)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)

    def test_tam_tat_mac_dinh_tat_gat_duoc_an_o_thong_so(self):
        self.assertFalse(thongso.cong_tac_bat("chuong_tamtat", self.dl))
        self.assertIn("chuong_tamtat", thongso.CONG_TAC)
        self.assertNotIn("chuong_tamtat", [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])
        thongso.gat("chuong_tamtat", True, "hethong", self.dl)
        self.assertTrue(thongso.cong_tac_bat("chuong_tamtat", self.dl))   # tới khi tự mở lại (QĐ551) – không có hạn giờ

    def test_tin_doi_ten_mien_mui_gio(self):
        thongso.doi_tenmien("igm.vidu.test", "hethong", self.dl)
        ds = thongbao.danh_sach(None, self.dl)["ds"]
        self.assertEqual([(x["loai"], x["muc"], x["di"], x["chu"]) for x in ds],
                         [("tenmien_doi", "tin", "chung", "Đã đổi tên miền riêng: igm.vidu.test")])
        thongso.doi_tenmien("", "hethong", self.dl)   # đổi lại: chỉ giữ lần gần nhất
        self.assertEqual([x["chu"] for x in thongbao.danh_sach(None, self.dl)["ds"]], ["Đã bỏ tên miền riêng"])
        self.assertEqual(thongbao.dong_su_kien("đã đọc", self.dl), 1)   # "Đọc hết" đóng tin sự kiện (TẠM)
        self.assertEqual(thongbao.danh_sach(None, self.dl)["ds"], [])

    def test_tin_doi_mui_gio_goi_tu_doi_muigio(self):
        with mock.patch.object(muigio, "kiem_ten", return_value=True):
            thongso.doi_muigio("muigio", "Asia/Tokyo", "hethong", self.dl)
        self.assertEqual([x["chu"] for x in thongbao.danh_sach(None, self.dl)["ds"]], ["Đã đổi múi giờ sang Asia/Tokyo"])


class KiemGiaoDien(unittest.TestCase):
    def setUp(self):
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_thu_tu_nhom_he_thong_qd559(self):
        i = self.h.index('<div class="nhom">HỆ THỐNG</div>')
        doan = self.h[i:self.h.index('<div class="gd-sau">', i)]
        self.assertEqual(re.findall(r'title="([^"]+)"', doan), ["Mô hình AI", "Cài đặt", "Tài khoản"])   # QĐ559
        self.assertIn('data-tk title="Tài khoản"', doan)                                              # QĐ553: chữ "Tài khoản"

    def test_ba_nut_goc_phai_va_dien_thoai(self):
        for x in ("data-chuong", 'class="nut36 an-dt" data-amthanh', 'class="nut36 an-dt" data-chedonut', 'class="nut36 chi-dt" data-tk'):
            self.assertIn(x, self.h, x)
        self.assertIn("#app:not(.mb) .vung>.vi-tri{position:absolute;top:22px;right:28px;z-index:20;gap:4px}", self.h)   # QĐ548 B
        self.assertIn(".nut36{width:36px;height:36px;", self.h)                                        # QĐ553 (2): 36 × 36, cách 4
        self.assertIn(".mb .an-dt,#app:not(.mb) .chi-dt{display:none!important}", self.h)            # QĐ553 (6)
        self.assertIn("(so > 99 ? '99+' : soVN(so))", self.js)                                         # QĐ553 (2)
        self.assertIn("if (S.xem !== 'mb' && vg && vt.parentElement !== vg) vg.prepend(vt);", self.js)

    def test_chu_qd566(self):
        for c in ("amBat: 'Đang bật âm thanh – bấm để tắt', amTat: 'Đang tắt âm thanh – bấm để bật', cheDo: 'Chế độ màu'",
                  "tamTat: 'Tạm tắt', moLai: 'Mở lại', canXl: 'Cần xử lý'", "hienDoc: n => 'Hiện ' + n + ' tin đã đọc'",
                  "daiTat: 'Đang tạm tắt thông báo. Tin nghiêm trọng (sao lưu lỗi, ổ đầy) vẫn báo.'",
                  "const TEN_CHEDO = {sang: 'Sáng', toi: 'Tối', hethong: 'Theo hệ thống'};"):
            self.assertIn(c, self.js, c)
        for c in (">Âm thanh<", ">Chế độ màu<", ">Có gì mới<", ">Trợ giúp<", ">Đăng xuất<", "Vai trò: Chủ"):
            self.assertIn(c, self.h, c)
        self.assertIn("api('/thongso/chuong_tamtat/gat', {bat: !D.tbTamTat})", self.js)               # QĐ551
        self.assertIn("(!tat || ds.some(x => x.moi && x.muc === 'do'))", self.js)                     # tạm tắt vẫn báo tin nghiêm trọng
        self.assertIn("const KHOA_AM = 'igm360_amthanh';", self.js)                                   # QĐ547: theo máy
        src = (GOC / "maychu/hethong/giamsat/thongbao.py").read_text(encoding="utf-8")
        self.assertIn("# TẠM (QĐ648): chữ tin chuông", src)


if __name__ == "__main__":
    unittest.main()
