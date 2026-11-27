"""Bài kiểm 0.10.0 – khung Cài đặt B (QĐ573, QĐ574, QĐ580, QĐ583, QĐ586) + ngăn Chung (QĐ627, QĐ647, QĐ649–QĐ653; tên miền
QĐ634, múi giờ QĐ636). Cấu trúc màn 09 · chữ ghim đúng bảng anh duyệt · nhóm giao diện = nhóm máy chủ · công tắc "Giữ dấu
ảnh AI" (P01, mặc định bật, ẩn ở ngăn Thông số, gạt qua đường chung + F04) · bảng mã nước của múi giờ."""

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, muigio
from maychu.hethong.caidat import thongso

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"


def _doc(ten):
    return (GD / ten).read_text(encoding="utf-8").replace("\r\n", "\n")


class KiemKhung(unittest.TestCase):
    def setUp(self):
        self.h, self.js = _doc("index.html"), _doc("app.js")
        i = self.h.index('<div class="trang" id="p09"')
        self.p09 = self.h[i:self.h.index('<div class="trang" id="p11"', i)]

    def test_bo_cuc_b(self):
        for x in ('<div class="cd-cum">', '<div class="the cd-td">', 'id="ts-chua"', 'id="ts-thanh"', 'id="ts-dem"', 'data-loc-chua',
                  '<nav class="the cd-menu" id="cd-menu"', '<section class="the cd-ct">', 'id="cd-ten"', 'id="ngan-chung"'):
            self.assertIn(x, self.p09, x)
        self.assertNotIn('<div class="tabs">', self.p09)   # QĐ573: bỏ thẻ ngang
        self.assertLess(self.p09.index("cd-td"), self.p09.index("cd-menu"))   # QĐ574: tiến độ trên cùng
        for tab in ("chung", "thongso", "taikhoan", "capnhat", "ketkhoa"):
            self.assertIn(f'data-s="tab:{tab}"', self.p09, tab)
        self.assertIn("grid-template-columns:232px minmax(0,1fr)", self.h)   # menu 232 | khối chi tiết

    def test_menu_va_nhom(self):
        self.assertIn("const NGAN_CD = [['chung', 'monitor-cog', 'Chung'], ['thongso', 'sliders-horizontal', 'Thông số'],", self.js)
        nhom = re.search(r"const NHOM_CD = \[([^\]]*)\]", self.js).group(1)
        self.assertEqual(tuple(re.findall(r"'([^']*)'", nhom)), thongso.NHOM)   # QĐ586: tên nhóm giao diện = máy chủ
        self.assertIn("S.tab = 'thongso'; S.nhom = 'gom'; S.cdMan = 2; napTab();", self.js)   # QĐ583: 01 bấm sang trang gom
        self.assertIn("if (t.closest('#cd-menu')) S.cdMan = 2;", self.js)   # điện thoại: chạm ngăn → màn 2 (CaidatB_07, 08)
        self.assertIn("else if ('cdLui' in d) S.cdMan = 1;", self.js)
        self.assertIn(".mb #p09:not(.man2) .cd-ct{display:none}", self.h)
        self.assertIn(".mb #p09 .cd-mm{min-height:48px}", self.h)   # Quychuan Phần 8: dòng chạm 48
        self.assertIn("'Thông số chưa đặt'", self.js)
        self.assertIn("await napThongSo();   // QĐ574, QĐ583", self.js)          # tiến độ hiện ở mọi ngăn
        for ic in ("monitor-cog", "stamp", "sun", "moon", "monitor", "circle-chevron-right"):   # QĐ653 + chế độ màu, QĐ585
            self.assertRegex(self.js, r"ICON(\.|\[')" + re.escape(ic).replace("\\-", "-") + r"('\])? = svgLucide\('" + re.escape(ic), ic)

    def test_chu_da_duyet(self):
        js = self.js
        for chu in ("Giữ dấu ảnh AI", "Chưa có tác dụng: GĐ 1 chưa tạo ảnh. Dùng khi có module Marketing.", "Gỡ dấu ảnh AI?",   # QĐ649
                    "Dấu cho biết ảnh do AI tạo; Facebook đọc dấu này để gắn nhãn nội dung AI. Chỉ áp dụng cho ảnh tạo từ lúc này, ảnh đã tạo không đổi.",
                    "c2paHn: 'Gỡ dấu'", "hok: 'Đang chạy · đến {n}'", "hcho: 'Chờ DNS'", "hchua: 'Chưa đọc được'",   # QĐ650
                    "dok: 'Đã trỏ đúng'", "dsai: 'Chưa trỏ về máy chủ'", "luu: 'Lưu và kiểm tra'", "kt: 'Kiểm tra lại'",   # QĐ651
                    "Chưa bật đổi tên miền: máy chủ cần chạy 01 lệnh nâng cấu hình. Tên gốc vẫn chạy.", "ht: 'Đổi tên miền?'", "hn: 'Lưu tên miền'",
                    "Đổi tên miền thì đăng nhập lại ở địa chỉ mới. Nối lại Google Drive: thêm địa chỉ mới ở Google Cloud. Tên gốc luôn dùng được.",
                    "khoa: 'Chỉ tài khoản Chủ đổi tên miền'", "khoa: 'Chỉ tài khoản Chủ đổi múi giờ'", "hn: 'Đổi múi giờ'"):
            self.assertIn(chu, js, chu)
        for chu in ("boHt: 'Bỏ tên riêng?', boHn: 'Bỏ tên riêng'", "dkr: 'Chưa kiểm được, bấm Kiểm tra lại'",   # QĐ657 (1), (4)
                    "boHc: 'IGM360 chỉ còn mở ở tên gốc {goc}. Nhập mật khẩu và mã 06 số đang hiện trên điện thoại để xác nhận.'"):   # (5) cột B
            self.assertIn(chu, js, chu)
        self.assertNotIn("TẠM (QĐ648): hộp", js)
        self.assertIn("if (bat) await lam(); else xacnhan(CHU_CG.c2paHt", js)   # QĐ647: chỉ hỏi khi gạt sang gỡ dấu
        self.assertIn("CHEDO.dat(d.chedo)", js)                                 # QĐ411: dải chọn dùng chedo.js


class KiemMayChu(unittest.TestCase):
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

    def test_c2pa_mac_dinh_bat_an_o_thong_so_gat_duoc(self):
        self.assertTrue(thongso.cong_tac_bat("anh_ai_giu_dau_c2pa", self.dl))
        self.assertNotIn("anh_ai_giu_dau_c2pa", [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])
        self.assertEqual(thongso.gat("anh_ai_giu_dau_c2pa", False, "hethong", self.dl), {"ok": True, "doi": True})
        self.assertFalse(thongso.cong_tac_bat("anh_ai_giu_dau_c2pa", self.dl))

    def test_nhom_qd586(self):
        self.assertEqual(thongso.NHOM[1], "Máy chủ, sao lưu")
        self.assertEqual(thongso.NHOM[thongso.THEO_TEN["songay_baotruoc_khoa_hethan"][1]], "Báo cáo, dữ liệu")

    def test_quoc_gia_mui_gio(self):
        qg = muigio.quoc_gia()
        self.assertIsInstance(qg, dict)
        if Path("/usr/share/zoneinfo/zone.tab").exists():   # ảnh Linux
            self.assertEqual((qg["Asia/Tokyo"], qg["Asia/Ho_Chi_Minh"]), ("JP", "VN"))


if __name__ == "__main__":
    unittest.main()
