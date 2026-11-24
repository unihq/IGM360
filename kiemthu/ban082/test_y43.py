"""Bài kiểm 0.8.2 (Y43; QĐ258 phương án B, PTD-13): cập nhật nhanh.

- Ảnh nền ghim theo sha256 (giữ nhãn trixie QĐ229), thứ tự lớp pip → Codex → Claude → mã, 02 CLI ghim số bản.
- Tệp luồng: không lấy CLI mới nhất lúc đóng gói; nhánh capnhat-nhanh chỉ đẩy nhãn thu-<sha>. Nâng CLI tự động, nút nâng ngay:
  tạm dừng (QĐ260, chờ KT-QĐ260).
- Bước 3: bản không nâng dữ liệu thì không chờ Drive (đẩy nền sau khi bản mới lên); bản có nâng hoặc không rõ: đẩy trước như cũ.
- Bước 8: trang tải lại ngay khi bản mới chạy; kiểm chạy nền, trang hỏi lại tới khi xong rồi vẽ lại lịch sử.
Không gọi Claude/Codex CLI thật.
"""
import json
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from kiemthu.ban081.test_y41 import GD, NenTD, _ma_the

GOC = Path(__file__).resolve().parents[2]
SO = r"\d+\.\d+\.\d+"


def _doc(ten: str) -> str:
    return (GOC / ten).read_text(encoding="utf-8").replace("\r\n", "\n")


class KiemDockerfile(unittest.TestCase):
    def test_nen_ghim_sha256_giu_trixie(self):
        df = _doc("Dockerfile")
        self.assertRegex(df, r"\nFROM python:3\.12-slim-trixie@sha256:[0-9a-f]{64}\n")          # QĐ229 + QĐ258
        self.assertRegex(df, r"\nFROM node:22\.\d+\.\d+-bookworm-slim@sha256:[0-9a-f]{64} AS nguon_node\n")
        self.assertIn("ARG ANH_TRUOC=ghcr.io/unihq/igm360:latest", df)                       # QĐ215: bản trước vẫn lấy từ latest

    def test_cli_ghim_so_ban(self):
        df = _doc("Dockerfile")
        for bien in ("CODEX_CLI_VERSION", "CLAUDE_CLI_VERSION"):
            self.assertRegex(df, rf"\nARG {bien}={SO}\n")
        self.assertNotIn("_CLI_VERSION=latest", df)

    def test_thu_tu_lop_pip_codex_claude_ma(self):
        df = _doc("Dockerfile")
        vi = [df.index(x) for x in ("RUN pip install -r requirements.txt", 'npm install -g "@openai/codex@',
                                    'npm install -g "@anthropic-ai/claude-code@', "COPY maychu ./maychu")]
        self.assertEqual(vi, sorted(vi))


class KiemTepLuong(unittest.TestCase):
    def test_dong_image_khong_lay_cli_moi_nhat(self):
        wf = _doc(".github/workflows/dongimage.yml")
        self.assertNotIn("npm view", wf)
        self.assertNotIn("CLAUDE_CLI_VERSION=${{", wf)
        self.assertNotIn("CODEX_CLI_VERSION=${{", wf)
        self.assertIn("cache-to: type=inline", wf)

    def test_nhanh_do_lop_khong_day_latest(self):
        wf = _doc(".github/workflows/dongimage.yml")
        self.assertIn("if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/capnhat-nhanh'", wf)
        buoc = wf.split("- name: Chọn nhãn đẩy", 1)[1].split("- uses:", 1)[0]
        nhanh = buoc.split("else", 1)[1].split("fi", 1)[0]
        self.assertIn(":thu-${GITHUB_SHA}", nhanh)
        self.assertNotIn(":latest", nhanh)
        self.assertNotIn("${PHIENBAN}", nhanh)
        self.assertIn("tags: ${{ env.NHAN }}", wf)


class KiemNangDuLieu(unittest.TestCase):
    def test_doc_dong_nang_du_lieu(self):
        from maychu.hethong import capnhat
        m = capnhat.phan_tich_thaydoi("## 0.9.2\nNâng dữ liệu: không\n- a\n\n## 0.9.1\nNâng dữ liệu: có\n\n## 0.9.0\n- b\n"
                                      "\n## 0.8.9\nNâng dữ liệu: chưa rõ\n")
        self.assertEqual([x["nang_dulieu"] for x in m], [False, True, None, None])
        self.assertEqual(m[0]["dong"], ["a"])                           # dòng "Nâng dữ liệu" không hiện ra trang

    def test_khoang_cap_nhat(self):
        from maychu.hethong import capnhat
        m = capnhat.phan_tich_thaydoi("## 0.9.3\nNâng dữ liệu: không\n## 0.9.2\nNâng dữ liệu: không\n## 0.9.1\nNâng dữ liệu: có\n"
                                      "## 0.9.0\n")
        co = capnhat.co_nang_dulieu
        self.assertFalse(co("0.9.1", "0.9.3", m))                       # mọi bản trong khoảng ghi "không"
        self.assertTrue(co("0.9.0", "0.9.3", m))                        # khoảng có bản nâng
        self.assertTrue(co("0.8.9", "0.9.0", m))                        # thiếu dòng: coi là có
        self.assertTrue(co("0.9.3", "0.9.4", m))                        # không có mục của bản đích: coi là có
        self.assertTrue(co("0.9.1", None, m))

    def test_thaydoi_ban_hien_tai_co_dong(self):
        from maychu.hethong import capnhat
        ban = _doc("VERSION").strip()
        muc = next(m for m in capnhat.phan_tich_thaydoi(_doc("THAYDOI.md")) if m["ban"] == ban)
        self.assertIn(muc["nang_dulieu"], (True, False))                # từ 0.8.2 mỗi bản phải ghi rõ


class KiemDriveNen(NenTD):
    def chay(self, day_truoc: bool, con_cho: int = 3):
        from maychu.dulieu import maso
        from maychu.hethong import antoan, capnhat, tiendo
        goi = []
        with mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.9.9", "nang_dulieu": day_truoc}), \
                mock.patch.object(capnhat, "cap_nhat_ngay", return_value={"ok": True}), \
                mock.patch.object(capnhat, "_con_cho_drive", return_value=con_cho), \
                mock.patch.object(capnhat, "NGHI_DAY_GIAY", 0.05), mock.patch.object(antoan, "CHO_DRIVE_GIAY", 0.3), \
                mock.patch("maychu.ketnoi.drive.dang_noi", return_value=True), \
                mock.patch("maychu.ketnoi.drive.day_hang_cho", side_effect=lambda *a, **k: goi.append(1) or {}):
            self.assertTrue(capnhat.yeu_cau(maso.tao(), "ngay", thumuc=self.dl)["ok"])
            het = time.time() + 30
            while capnhat._SAO["buoc"] not in ("tai", "qua_gio") and time.time() < het:
                time.sleep(0.05)
        return capnhat._SAO["buoc"], goi, tiendo.doc(self.dl), antoan.doc(self.dl).get("yeu_cau") or {}

    def test_khong_nang_du_lieu_khong_cho_drive(self):
        buoc, goi, td, yc = self.chay(day_truoc=False)
        self.assertEqual((buoc, goi), ("tai", []))                     # gửi lệnh ngay, không đẩy Drive trước
        self.assertEqual(td["chi_tiet"]["drive"], {"nen": True, "da": 0, "tong": 3})
        self.assertFalse(yc.get("drive"))                               # bản sao chưa lên Drive lúc gửi lệnh

    def test_co_nang_du_lieu_day_truoc_nhu_cu(self):
        buoc, goi, td, _ = self.chay(day_truoc=True)
        self.assertEqual(buoc, "qua_gio")                               # chờ Drive như QĐ213 lớp 5, QĐ218 dòng 28
        self.assertGreater(len(goi), 0)
        self.assertNotIn("nen", td["chi_tiet"]["drive"])

    def test_dong_f04_co_chay_moi(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.1", "0.9.9", tiendo._bay(), self.dl)
        for b in ("gui", "tai", "khoidong", "nang", "kiem"):
            tiendo.sang(b, self.dl)
        tiendo.xong("0.9.9", self.dl)
        dong = self.f04("tiendo")
        self.assertEqual(len(dong), 1)
        self.assertRegex(dong[0], r" · chay_moi=\d+ · bat_dau=")


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemTrang(unittest.TestCase):
    def node(self, ma: str) -> dict:
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "t.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_buoc_3_drive_nen_icon_xam_khong_chu(self):
        from kiemthu.ban081.test_y41 import T0, _td
        td = _td("tai", {"o_trong": 0, "chup": 2, "drive": 11, "gui": 12, "tai": 13}, drive={"nen": True, "da": 0, "tong": 5})
        ma = (_ma_the() + "const CHU_CN = {kiem: 'Kiểm sau cập nhật: '};\n"
              f"console.log(JSON.stringify({{h: htmlTienDo({json.dumps(td, ensure_ascii=False)}, {{bay: Date.parse('{T0}') + 60e3}})}}));\n")
        h = self.node(ma)["h"]
        dong = h.split('3. Bản sao Drive</span>', 1)
        self.assertIn("lucide-circle-minus", dong[0][-700:])
        self.assertTrue(dong[1].startswith('<span class="td8-m"></span>'))   # chữ chờ CDO U19
        self.assertNotIn("chưa lên hết", h)
        self.assertNotIn("chưa nối Drive", h)

    def test_theo_kiem_hoi_den_khi_xong_roi_ve_lai(self):
        js = GD.joinpath("app.js").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("function theoKiem("))
        b = next(i for i in range(a, len(js)) if js[i] == "}")
        ham = "\n".join(js[a:b + 1]).replace("Date.now()", "dongHo.now()")
        ma = r"""
let T = 0, hen = [], hoi = 0, ve = [];
const D = {}, dongHo = {now: () => T};
const setTimeout = (f, ms) => { hen.push({luc: T + ms, f}); };
const api = async () => { hoi++; return {tien_do: hoi < 4 ? {buoc: 'kiem', den: '0.9.9'} : {buoc: 'xong', den: '0.9.9'}, lan: hoi}; };
const veCapNhat = s => { ve.push(s.lan); };
""" + ham + r"""
(async () => {
  theoKiem(); theoKiem();   // gọi 02 lần: chỉ 01 vòng hỏi
  for (let i = 0; i < 500 && hen.length; i++) { hen.sort((a, b) => a.luc - b.luc); const h = hen.shift(); T = h.luc; await h.f(); }
  console.log(JSON.stringify({hoi, ve, dang: D.theoKiem, giay: T / 1000}));
})();
"""
        kq = self.node(ma)
        self.assertEqual((kq["hoi"], kq["ve"], kq["dang"]), (4, [4], False))   # vẽ lại 01 lần khi kiểm xong
        self.assertEqual(kq["giay"], 40)                                       # mỗi 10 giây

    def test_tai_lai_ngay_va_khong_con_cho_xong(self):
        js = GD.joinpath("app.js").read_text(encoding="utf-8")
        self.assertIn("if (k.phienban && k.phienban !== cu) { location.reload(); return; }", js)
        self.assertNotIn("moiChay", js)
        self.assertIn("else if (dangLuot && t.den === d.ban_dang) theoKiem();", js)


if __name__ == "__main__":
    unittest.main()
