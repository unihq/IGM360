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
        # QĐ662 (anh "Chọn A"): tin 02 dòng, ghim nguyên văn
        thongso.doi_tenmien("igm.vidu.test", "hethong", self.dl)   # (3) lần đầu
        ds = thongbao.danh_sach(None, self.dl)["ds"]
        self.assertEqual([(x["loai"], x["muc"], x["di"], x["icon"], x["chu"], x["phu"]) for x in ds],
                         [("tenmien_doi", "tin", "chung", "globe", "Đã đặt tên miền riêng",
                           "igm.vidu.test · tên gốc goc.vidu.test vẫn dùng được")])
        thongso.doi_tenmien("moi.vidu.test", "hethong", self.dl)   # (2) đổi – chỉ giữ lần gần nhất
        self.assertEqual([(x["chu"], x["phu"]) for x in thongbao.danh_sach(None, self.dl)["ds"]],
                         [("Đã đổi tên miền riêng", "igm.vidu.test → moi.vidu.test")])
        thongso.doi_tenmien("", "hethong", self.dl)   # (4) bỏ
        self.assertEqual([(x["chu"], x["phu"]) for x in thongbao.danh_sach(None, self.dl)["ds"]],
                         [("Đã bỏ tên miền riêng", "moi.vidu.test → chỉ còn tên gốc goc.vidu.test")])
        self.assertFalse(hasattr(thongbao, "dong_su_kien"))   # CPO TIN-TM-MG-SUA (3): "Đọc hết" không đóng tin

    def test_doc_het_khong_dong_tin_su_kien(self):
        thongso.doi_tenmien("igm.vidu.test", "hethong", self.dl)
        src = (GOC / "maychu/web/api.py").read_text(encoding="utf-8")
        i = src.index('@router.post("/thongbao/dochet")')
        self.assertNotIn("thongbao.dong", src[i:src.index("@router", i + 10)])
        self.assertEqual([x["chu"] for x in thongbao.danh_sach(None, self.dl)["ds"]], ["Đã đặt tên miền riêng"])

    def test_tin_doi_mui_gio_goi_tu_doi_muigio(self):
        from datetime import timezone
        # Windows không có bộ múi giờ (tzdata): giả múi = UTC, chỉ kiểm khóa tin
        with mock.patch.object(muigio, "kiem_ten", return_value=True), mock.patch.object(muigio, "ZoneInfo", lambda k: timezone.utc):
            thongso.doi_muigio("muigio", "Asia/Tokyo", "hethong", self.dl)
            thongso.doi_muigio("muigio_doisoat", "Asia/Bangkok", "hethong", self.dl)
            thongso.doi_muigio("muigio", "Asia/Seoul", "hethong", self.dl)
            ds = thongbao.danh_sach(None, self.dl)["ds"]
        # CPO TIN-TM-MG-SUA (2): khóa muigio_doi:<tên thông số>:<mới>:<cũ>; đổi lại chỉ đóng tin cùng tên thông số
        from maychu.dulieu import ketnoi
        cn = ketnoi.mo("Dulieu_Chinh", self.dl)
        try:
            mo = sorted(r[0] for r in cn.execute("SELECT khoa_chongtrung FROM canhbao WHERE khoa_chongtrung LIKE 'muigio_doi:%'"
                                                 f" AND trangthai IN {thongbao.CON_MO}"))
        finally:
            cn.close()
        self.assertEqual(mo, ["muigio_doi:muigio:Asia/Seoul:Asia/Tokyo", "muigio_doi:muigio_doisoat:Asia/Bangkok:Asia/Ho_Chi_Minh"])
        self.assertEqual(sorted(x["chu"] for x in ds), ["Đã đổi múi giờ", "Đã đổi múi giờ đối soát sang Asia/Bangkok"])   # QĐ662 (1); đối soát TẠM tới 0.12.0
        mg = next(x for x in ds if x["chu"] == "Đã đổi múi giờ")
        self.assertEqual((mg["icon"], mg["mg"]), ("watch", ["Asia/Tokyo", "Asia/Seoul"]))   # QĐ663; dòng 2 giao diện ghi tên múi QĐ652
        self.assertTrue(set(mg["qg"]) <= {"Asia/Tokyo", "Asia/Seoul"})


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
        self.assertIn('return "Đã bỏ tên miền riêng" if not moi else "Đã đổi tên miền riêng" if cu else "Đã đặt tên miền riêng"', src)   # QĐ662
        self.assertIn("const dong2Tb = x => x.mg ? tenMuiTb(x.mg[0], x.qg) + ' → ' + tenMuiTb(x.mg[1], x.qg) : x.phu || '';", self.js)
        self.assertIn("ICON.watch = ICON.watch || svgLucide('watch',", self.js)                                  # QĐ663


if __name__ == "__main__":
    unittest.main()
