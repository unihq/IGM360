"""Bài kiểm 0.10.0 bước 8c – giao diện ngăn Mức dùng (bản DM-CAIDAT-010; QĐ564 B, QĐ653 icon chart-no-axes-column; chữ QĐ666
dòng 01–13; ô "Cửa sổ 05 giờ" không icon (CPO ICON-ACTIVITY); không dòng "≈ … đ" (CPO MUCDUNG-TRALOI); khung "Chưa đủ lượt để so"
khi đỉnh = 0 (CPO NGUONG-AP))."""

import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemNganMucDung(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        i = self.js.index("// ---- Màn 09 ngăn Mức dùng")
        self.doan = self.js[i:self.js.index("\n// ---- Bấm", i)]

    def test_menu_07_ngan(self):
        self.assertIn("['thongbao', 'bell', 'Thông báo'], ['mucdung', 'chart-no-axes-column', 'Mức dùng']", self.js)
        self.assertIn('<div data-s="tab:mucdung" class="cot-doc" id="ngan-mucdung"></div>', self.h)
        self.assertIn("else if (S.tab === 'mucdung') await napMucDung();", self.js)

    def test_chu_qd666(self):
        for c in ("cs: 'Cửa sổ 05 giờ'", "dinhP: (p, d, k) => p + '% đỉnh 60 ngày (' + d + (k ? ', ' + k : '') + ')'",
                  "chuaTran: 'Chưa đặt mức trần 05 giờ'", "tranP: (p, t) => p + '% mức trần 05 giờ ' + t",
                  "hmThang: x => 'Hạn mức chi tháng: ' + (x == null ? 'Chưa đặt' : soVN(x) + ' USD')",
                  "bd1: 'Cửa sổ 05 giờ · 24 giờ qua', bd2: 'Token mỗi giờ', bd3: 'Giờ bận · 07 ngày'",
                  "nay: 'Giờ này', truoc: 'Giờ trước', ban3: '03 giờ bận nhất', dinh: 'Đỉnh 60 ngày', tran: 'Mức trần', nguon: 'Nguồn: ', tatCa: 'Tất cả'",
                  "chan: 'Token đếm từ lượt AI chạy qua IGM360; % hạn mức gói lấy từ hãng.'", "viDu: 'Ví dụ: 500.000'",
                  "deTrong: d => 'Để trống: so với đỉnh 60 ngày' + (d ? ' (' + d + ' token)' : '')", "datTs: 'Đặt ở Thông số'"):
            self.assertIn(c, self.doan, c)

    def test_khong_icon_cua_so_khong_quy_doi_dong(self):
        self.assertIn("'</div><div class=\"md-os\"><div class=\"md-tn\">' + C.cs + '</div>'", self.doan)   # ô Cửa sổ 05 giờ: 0 icon
        self.assertNotIn("activity", self.doan)
        self.assertNotIn(" đ tham", self.doan)                                                         # chưa có tỷ giá
        self.assertIn("du = k.du", self.doan)                                                         # khung khi đỉnh = 0 (máy chủ)
        self.assertIn("api('/mucdung/tran', {tran: $('#md-tran').value.trim()})", self.doan)
        self.assertIn("data-tab=\"thongso\" data-nhom=\"AI\"", self.doan)                              # hạn mức chi tháng sửa ở Thông số

    def test_bieu_do_b2_ro_cham_phim(self):
        for x in ("role=\"slider\" tabindex=\"0\"", "ArrowLeft: i - 1, ArrowRight: i + 1", "'pointermove'", "'pointerdown'"):
            self.assertIn(x, self.doan, x)
        self.assertIn(".md-cot .c{flex:1;border-radius:3px 3px 0 0;background:var(--h-truoc);min-height:1px}", self.h)   # màu kỳ trước Quychuan 5.13
        self.assertIn("@media (max-width:1199px){.md-o3,.md-bd2,.md-nsg{grid-template-columns:minmax(0,1fr)}}", self.h)


if __name__ == "__main__":
    unittest.main()
