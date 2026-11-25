"""Bài kiểm 0.9.1 việc 1.1 – nút con mắt ô mật khẩu (QĐ404, anh "A. Đổi theo anh"; KH-091): hình chỉ TRẠNG THÁI đang có
(đang ẩn → con mắt gạch `eye-off`, đang hiện → con mắt mở `eye`); nhãn máy đọc giữ QĐ369 (6) theo việc sẽ làm
(đang ẩn → "Hiện mật khẩu", đang hiện → "Ẩn mật khẩu"). Chạy đoạn bấm `data-mat` của app.js bằng node, DOM giả tối thiểu.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class KiemMat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        ic = (GD / "icon.js").read_text(encoding="utf-8")
        cls.ICON = json.loads(re.search(r"const ICON=(\{.*?\});", ic, re.S).group(1))

    def test_trang_thai_dau_an_la_con_mat_gach(self):
        dau = '<button type="button" class="mat" data-mat aria-label="Hiện mật khẩu">'
        self.assertEqual(self.html.count('data-mat'), 1)                                   # 01 ô mật khẩu có nút này (#mk)
        i = self.html.index(dau) + len(dau)
        svg = self.html[i:self.html.index("</svg>", i) + len("</svg>")]
        self.assertEqual(svg, self.ICON["eye-off"].replace("<svg", '<svg aria-hidden="true"', 1))
        self.assertIn('<input type="password" id="mk"', self.html)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_bam_doi_hinh_theo_trang_thai_nhan_theo_viec_se_lam(self):
        a = self.app
        i = a.index("  else if ('mat' in d) {")
        nhanh = a[i:a.index("  else if ('dangnhap' in d)", i)].replace("  else if ('mat' in d) {", "if ('mat' in d) {", 1)
        cdn = a[a.index("const CHU_DN = "):a.index("\n", a.index("const CHU_DN = ")) + 1]
        ma = ("const ICON = " + json.dumps({"eye": "<svg stroke=\"#000\" width=\"1\" height=\"1\">eye</svg>",
                                            "eye-off": "<svg stroke=\"#000\" width=\"1\" height=\"1\">eye-off</svg>"}) + ";\n"
              + "const icoMau = (svg, mau, co) => svg.replace(/stroke=\"[^\"]*\"/, 'stroke=\"' + mau + '\"');\n" + cdn
              + "const o = {type: 'password'}, $ = () => o, d = {mat: ''};\n"
              + "const t = {innerHTML: '', nhan: '', setAttribute(k, v) { this.nhan = v; }};\n"
              + "const bam = () => { " + nhanh + " return [o.type, /eye-off/.test(t.innerHTML) ? 'eye-off' : 'eye', t.nhan]; };\n"
              + "console.log(JSON.stringify([bam(), bam()]));")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [["text", "eye", "Ẩn mật khẩu"],               # đang hiện → con mắt mở; bấm sẽ ẩn
                                                ["password", "eye-off", "Hiện mật khẩu"]])   # đang ẩn → con mắt gạch; bấm sẽ hiện


if __name__ == "__main__":
    unittest.main()
