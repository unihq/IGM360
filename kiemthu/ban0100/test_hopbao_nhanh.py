"""Bài kiểm 0.10.0 – hộp báo nhanh (QĐ413, QĐ417 A, QĐ419 – Quychuan dòng 208; QĐ575 0 vạch trái; tin CPO HOPBAO-TAM):
mọi lời gọi bao() ghi rõ loại 'loi' / 'xong' / 'thongtin'; lỗi có icon tròn đỏ + nút ✕ "Đóng", giữ tới khi bấm; xong icon xanh lá,
tự tắt 3,2 giây; thông tin (QĐ667) icon badge-info màu Thông tin, giữ tới ✕."""

import re
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


def _loi_goi(js: str):
    """Mỗi lời gọi bao(...) (trừ dòng khai báo hàm) → đối số đầy đủ, dò ngoặc có tính chuỗi."""
    for m in re.finditer(r"(?<![\w.])bao\(", js):
        if js[max(0, m.start() - 9):m.start()] == "function ":
            continue
        sau, j, q = 0, m.end() - 1, None
        while True:
            c = js[j]
            if q:
                if c == "\\":
                    j += 2
                    continue
                if c == q:
                    q = None
            elif c in "'\"`":
                q = c
            elif c in "([{":
                sau += 1
            elif c in ")]}":
                sau -= 1
                if sau == 0:
                    break
            j += 1
        yield js[m.end():j]


class KiemHopBao(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_moi_cho_goi_co_nhan_loai(self):
        ds = list(_loi_goi(self.js))
        self.assertGreater(len(ds), 70)
        thieu = [a.strip()[:70] for a in ds if not re.search(r",\s*'(loi|xong|thongtin)'\s*$", a.strip())]
        self.assertEqual(thieu, [])
        dem = {k: sum(1 for a in ds if a.strip().endswith(f"'{k}'")) for k in ("loi", "xong", "thongtin")}
        self.assertEqual(dem["thongtin"], 10)   # danh sách gửi DM vẽ icon (HOPBAO-TAM)

    def test_hinh_theo_quychuan(self):
        i = self.js.index("function bao(t, loai) {")
        ham = self.js[i:self.js.index("\n}\n", i)]
        for x in ("giu = loai !== 'xong'", "aria-label=\"Đóng\"", "e.setAttribute('role', loi ? 'alert' : 'status');",
                  "if (!giu) bao.h = setTimeout(() => { e.hidden = true; }, 3200);"):
            self.assertIn(x, ham, x)
        # QĐ667 (anh "Chọn B"): thông tin = badge-info màu --tin, giữ tới ✕; lỗi đỏ, xong xanh lá (Quychuan dòng 208)
        self.assertIn("const MAU_BAO = {loi: ['circle-alert', 'var(--canh)'], xong: ['circle-check', 'var(--dat)'], thongtin: ['badge-info', 'var(--tin)']};", self.js)
        self.assertIn("ICON['badge-info'] = ICON['badge-info'] || svgLucide('badge-info',", self.js)
        self.assertLess(self.js.index("const svgLucide = "), self.js.index("ICON['badge-info'] = "))   # khai báo trước khi dùng
        self.assertNotIn("TẠM (QĐ648 – icon chờ anh duyệt)", self.js)
        self.assertIn(".hb-dong{width:24px;height:24px;", self.h)
        self.assertIn(".mb .hb-dong{width:44px;height:44px;", self.h)

    def test_ten_lop_khong_trung_dong_tin_chuong(self):   # CDO 5.372 P1: .tb-dong là dòng tin chuông – nút ✕ hộp báo phải khác tên
        i = self.js.index("function bao(t, loai) {")
        ham = self.js[i:self.js.index("\n}\n", i)]
        self.assertNotIn("tb-dong", ham)
        self.assertIn("class=\"nut-ico hb-dong\"", ham)
        self.assertNotIn(".tb-dong{width", self.h)

    def test_vi_tri_quychuan_208(self):   # CDO 5.372 P2: cách đáy khối đang mở / thanh nút đáy 08 px
        i = self.js.index("function viTriBao() {")
        ham = self.js[i:self.js.index("\n}\n", i)]
        for x in ("$('nav.tab-duoi')", "innerHeight - r['top'] + 8", "innerHeight - cd.getBoundingClientRect().bottom + 8"):
            self.assertIn(x, ham, x)
        self.assertIn("e.style['bottom'] = viTriBao();", self.js)


if __name__ == "__main__":
    unittest.main()
