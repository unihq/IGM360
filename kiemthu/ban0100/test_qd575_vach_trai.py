"""Bài kiểm 0.10.0 – QĐ575 (anh 26/11/2026: "trong thiết kế tuyệt đối k dùng kiểu thanh màu xa góc trái này"): 0 vạch màu
sát mép trái ở giao diện (mục đang chọn, dải cảnh báo, hộp báo). Chỉ cho viền trái trong suốt, bằng 0, hoặc vạch ngăn
xám --ke giữa 02 nút liền nhau (.nac) – không phải vạch báo nghĩa."""

import re
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2] / "maychu"
DUOC = ("transparent", "var(--ke)")


class KiemVachTrai(unittest.TestCase):
    def test_khong_vach_mau_mep_trai(self):
        sai = []
        for p in list(GOC.rglob("*.html")) + list(GOC.rglob("*.js")) + list(GOC.rglob("*.css")) + list(GOC.rglob("*.py")):
            s = p.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"(border-left|border-inline-start|borderLeft)(-color)?\s*:\s*([^;}\"']*)", s):
                gt = m.group(3).strip()
                if gt in ("0", "none") or any(x in gt for x in DUOC):
                    continue
                sai.append(f"{p.relative_to(GOC)}: {m.group(0)[:60]}")
            for m in re.finditer(r"box-shadow\s*:\s*inset\s+([1-9]\d*)px\s+0", s):   # vạch giả bằng bóng trong bên trái
                sai.append(f"{p.relative_to(GOC)}: {m.group(0)[:60]}")
        self.assertEqual(sai, [])

    def test_dai_va_hop_bao_giu_nghia_bang_icon(self):
        h = (GOC / "web" / "giaodien" / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertIn('<div class="vach do-v" data-s="k:matketnoi"><svg\n  style="flex:none;vertical-align:middle;color:var(--canh)"', h)
        self.assertIn(".thongbao{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:var(--khoi);border:1px solid var(--ke);border-radius:12px;", h)


if __name__ == "__main__":
    unittest.main()
