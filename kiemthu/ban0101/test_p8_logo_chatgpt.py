"""Bài kiểm 0.10.1 phần P8 – logo ChatGPT chế độ Tối (QĐ688; phiếu dựng PD29).

Anh: logo ChatGPT trên nền tối đưa về màu trắng; Sáng giữ đen (QĐ170). Vẫn hình gốc OpenAI (QĐ92): tệp logo không đổi, chỉ
01 luật CSS trong `html.toi` tô trắng – đúng bản `Blossom_Dark.svg` (fill="white") của trang thương hiệu OpenAI.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"
LUAT = 'html.toi [data-hang="ChatGPT"] svg path[fill="black"]{fill:white}'


class KiemChuoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.icon = (GD / "icon.js").read_text(encoding="utf-8")

    def test_pd29_luat_toi(self):
        self.assertEqual(self.html.count(LUAT), 1)
        css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", self.html, re.S))
        for dong in re.findall(r"[^{}]*ChatGPT[^{}]*\{[^}]*\}", css):   # 0 luật Sáng đổi màu logo
            if "fill" in dong.split("{")[1] or "color" in dong.split("{")[1]:
                self.assertIn("html.toi", dong, dong)

    def test_pd29_logo_goc_giu_nguyen(self):   # QĐ92: tệp gốc OpenAI giữ đen
        i = self.icon.index('"logo_chatgpt"')
        the = self.icon[i:self.icon.index("</svg>", i)]
        self.assertIn('fill=\\"black\\"', the)
        self.assertNotIn("white", the)
        self.assertIn('fill="black"', (GD / "logo" / "chatgpt.svg").read_text(encoding="utf-8"))

    def test_pd29_moi_cho_co_logo_trong_o_chatgpt(self):
        dong = [x for x in self.js.split("\n") if "ICON.logo_chatgpt" in x]
        self.assertEqual(len(dong), 2)
        self.assertIn('data-hang="ChatGPT"', dong[0])                    # logoGoi – thẻ nguồn AI
        self.assertIn("const logoNhom", self.js[self.js.index(dong[1]) - 400:self.js.index(dong[1])] + dong[1])
        i = self.html.index('viewBox="0 0 716 716"')                       # nút đăng nhập ChatGPT (bản in sẵn)
        self.assertIn('data-hang="ChatGPT"', self.html[i - 200:i])
        self.assertEqual(self.html.count('viewBox="0 0 716 716"'), 1)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemNode(unittest.TestCase):
    def test_pd29_logo_nhom_co_dau_hang(self):
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        i = a.index("const logoNhom = g =>")
        ham = a[i:a.index("; };", i) + 4]
        ma = ("const ICON = {logo_claude: '<svg width=\"25\" height=\"25\"></svg>', logo_chatgpt: '<svg width=\"40\" height=\"40\"><path fill=\"black\"/></svg>',"
              " 'key-round': '<svg width=\"16\" height=\"16\"></svg>'}; const icoMau = s => s;\n" + ham)
        r = subprocess.run(["node", "-e", ma + "\nconsole.log(JSON.stringify([logoNhom({goi: 'chatgpt'}), logoNhom({hang: 'openai'}), logoNhom({goi: 'claude'}), logoNhom({hang: 'khac'})]));"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        gpt, oai, cl, kh = json.loads(r.stdout)
        for x in (gpt, oai):
            self.assertTrue(x.startswith('<span class="logo-n" data-hang="ChatGPT">'), x)
        for x in (cl, kh):
            self.assertTrue(x.startswith('<span class="logo-n">'), x)


if __name__ == "__main__":
    unittest.main()
