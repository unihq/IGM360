"""Bài kiểm 0.10.0 – hộp báo nhanh (QĐ413, QĐ417 A, QĐ419 – Quychuan dòng 208; QĐ575 0 vạch trái; tin CPO HOPBAO-TAM):
mọi lời gọi bao() ghi rõ loại 'loi' / 'xong' / 'thongtin'; lỗi có icon tròn đỏ + nút ✕ "Đóng", giữ tới khi bấm; xong icon xanh lá,
tự tắt 3,2 giây; thông tin TẠM (không icon, chờ anh duyệt icon)."""

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
        for x in ("ICON[loi ? 'circle-alert' : 'circle-check'], loi ? 'var(--canh)' : 'var(--dat)'",
                  "aria-label=\"Đóng\"", "e.setAttribute('role', loi ? 'alert' : 'status');",
                  "if (!loi) bao.h = setTimeout(() => { e.hidden = true; }, 3200);", "loai === 'thongtin' ? ''"):
            self.assertIn(x, ham, x)
        self.assertIn("'thongtin' TẠM (QĐ648", self.js)
        self.assertIn(".tb-dong{width:24px;height:24px;", self.h)
        self.assertIn(".mb .tb-dong{width:44px;height:44px;", self.h)


if __name__ == "__main__":
    unittest.main()
