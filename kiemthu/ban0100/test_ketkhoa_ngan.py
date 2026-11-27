"""Bài kiểm 0.10.0 – ngăn Két khóa (DM-03NGAN-0100, QĐ661; chữ bản GĐ 1 màn 09, dấu kiểu mới QĐ297;
CPO KETKHOA-A theo QĐ608: không nút "Thêm khóa" ở 0.10.0 – chỉ danh sách + Đổi + Xóa; QĐ661: hẹp thì hàng gọn + nút ⋯)."""

import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemKetKhoa(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.h = (GD / "index.html").read_text(encoding="utf-8")

    def test_ngan_dung_duong_goi_co_san(self):
        self.assertIn('<div data-s="tab:ketkhoa" class="cot-doc" id="ngan-ketkhoa"></div>', self.h)
        self.assertNotIn("Két khóa có ở bản sau", self.h)
        for x in ("D.kk = await api('/kekhoa');", "api('/kekhoa/' + encodeURIComponent(D.kkDoi) + '/doi', {giatri: gt, han:",
                  "api('/kekhoa/' + encodeURIComponent(x.id) + '/xoa', {})", "else if (S.tab === 'ketkhoa') await napKetKhoa();"):
            self.assertIn(x, self.js, x)

    def test_khong_them_khoa_o_0100(self):
        i = self.js.index("// ---- Màn 09 ngăn Két khóa")
        doan = self.js[i:self.js.index("\n// ---- Bấm", i)]
        self.assertNotIn("Thêm khóa", doan)          # CPO KETKHOA-A (QĐ608)
        self.assertNotIn("api('/kekhoa', {", doan)   # không gọi thêm khóa

    def test_chu_ban_gd1(self):
        for c in ("cot: ['Dịch vụ · dùng cho', 'Khóa', 'Hạn', 'Dùng lần cuối', 'Trạng thái']", "khongHan: 'Không đặt hạn'",
                  "doiT: t => 'Đổi khóa · ' + t", "han: 'Hạn (nếu có)'", "luuGhi: 'Lưu xong, khóa được mã hóa và chỉ hiện 04 ký tự cuối.'",
                  "luu: 'Lưu khóa'", "daLuu: 'Đã lưu khóa. Màn chỉ hiện 04 ký tự cuối.'", "xoaT: t => 'Xóa khóa ' + t + '?'",
                  "xoaC: 'Nguồn đang dùng khóa này sẽ ngừng lấy số cho tới khi có khóa mới. Xóa rồi không lấy lại được.'",
                  "them: 'Đổi, Xóa'", "' khóa · ' + hai(h) + ' hết hạn · ' + hai(s) + ' sắp hết hạn'"):
            self.assertIn(c, self.js, c)
        self.assertIn("rong: 'Chưa có khóa nào trong két.'};   // rong: TẠM", self.js)

    def test_hep_hang_gon_nut_ba(self):
        self.assertIn(".kk-tac{display:none}.kk-ba{display:flex}", self.h)   # QĐ661: 1024, 390 hàng gọn + nút ⋯ (nhãn đọc màn hình "Đổi, Xóa")


if __name__ == "__main__":
    unittest.main()
