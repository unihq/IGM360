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

    def test_chi_main_dong_anh(self):
        """CDA KT-Y43 N5: đường đo lớp của nhánh capnhat-nhanh đã bỏ; chỉ main đóng và đẩy ảnh."""
        wf = _doc(".github/workflows/dongimage.yml")
        self.assertIn("    if: github.ref == 'refs/heads/main'\n", wf)
        self.assertNotIn("capnhat-nhanh'", wf)
        self.assertNotIn(":thu-", wf)
        buoc = wf.split("- name: Chọn nhãn đẩy", 1)[1].split("- uses:", 1)[0]
        for nhan in ("${IMAGE}:latest", "${IMAGE}:${GITHUB_SHA}", "${IMAGE}:${PHIENBAN}"):
            self.assertIn(nhan, buoc)
        self.assertIn("tags: ${{ env.NHAN }}", wf)
        self.assertIn("fetch-depth: 0", wf.split("dongimage:", 1)[0])      # kiemthu có origin/main (N1)

    def test_luoc_do_doi_thi_phai_ghi_nang_du_lieu_co(self):
        """CDA KT-Y43 N1: nhánh đổi PHIENBAN_LUOCDO so với main mà mục THAYDOI của bản ghi "Nâng dữ liệu: không" thì báo đỏ
        (máy chủ sẽ không đẩy Drive trước khi nâng dữ liệu)."""
        from maychu.dulieu import khoitao
        from maychu.hethong import capnhat
        r = subprocess.run(["git", "show", "origin/main:maychu/dulieu/khoitao.py"], cwd=GOC, capture_output=True,
                           text=True, encoding="utf-8")
        if r.returncode != 0:
            self.skipTest("không có origin/main để so (CI lấy đủ lịch sử bằng fetch-depth: 0)")
        m = re.search(r"^PHIENBAN_LUOCDO\s*=\s*(\d+)", r.stdout, re.M)
        self.assertIsNotNone(m, "không đọc được PHIENBAN_LUOCDO của main")
        ban = _doc("VERSION").strip()
        muc = next((x for x in capnhat.phan_tich_thaydoi(_doc("THAYDOI.md")) if x["ban"] == ban), None)
        self.assertIsNotNone(muc, f"THAYDOI thiếu mục {ban}")
        if khoitao.PHIENBAN_LUOCDO != int(m.group(1)):
            self.assertIs(muc["nang_dulieu"], True, f"PHIENBAN_LUOCDO {m.group(1)} → {khoitao.PHIENBAN_LUOCDO} mà mục {ban}"
                                                    " không ghi \"Nâng dữ liệu: có\"")


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


class KiemChuongDrive(NenTD):
    """QĐ261, QĐ262: số đẩy Drive nền sau khi lên bản; chuông "Bản sao Drive lỗi" sau 03 lần lỗi; tự đóng khi lên đủ."""
    def chuan_bi(self, lan: int, xong: int = 0):
        from maychu.dulieu import ketnoi, maso
        from maychu.hethong import tiendo
        noi = self.dl / "saoluu" / "truoc_0.9.9"
        tiendo.bat_dau("0.8.1", "0.9.9", tiendo._bay(), self.dl)
        tiendo.sang("drive", self.dl, nen=True, da=0, tong=7)
        tiendo.dat(self.dl, drive_noi=str(noi))
        cn = ketnoi.mo("Hotho", self.dl)
        try:
            cn.execute("BEGIN IMMEDIATE")
            for i in range(7):
                cn.execute("INSERT INTO cho_day_drive (id, loai, duongdan_tam, dungluong_byte, trangthai, so_lan_thu, tao_luc)"
                           " VALUES (?, 'saoluu', ?, 1, ?, ?, ?)", (maso.tao(), str(noi / f"tep{i}.mahoa"),
                                                                     "xong" if i < xong else "loi", 0 if i < xong else lan, tiendo._bay()))
            cn.execute("COMMIT")
        finally:
            cn.close()

    def dat_het_xong(self):
        from maychu.dulieu import ketnoi
        cn = ketnoi.mo("Hotho", self.dl)
        try:
            cn.execute("UPDATE cho_day_drive SET trangthai = 'xong'")
        finally:
            cn.close()

    def chuong(self):
        from maychu.hethong.giamsat import thongbao
        return [x for x in thongbao.danh_sach(None, self.dl)["ds"] if x["loai"] == "drive_nen"]

    def test_hien_tra_so_drive_nen_khong_tra_duong_dan(self):
        from maychu.hethong import tiendo
        self.chuan_bi(lan=1, xong=3)
        h = tiendo.hien(self.dl)
        self.assertEqual(h["drive_nen"], {"da": 3, "tong": 7, "loi": True, "lan": 1, "hen": None})
        self.assertNotIn("drive_noi", h)
        self.assertNotIn(str(self.dl), json.dumps(h, ensure_ascii=False))

    def test_gio_hen_day_lai_som_nhat_qd273(self):
        """QĐ273: drive_nen có giờ hẹn đẩy lại sớm nhất (lan_thu_ke, giờ Việt Nam) của các tệp đang lỗi."""
        from maychu.dulieu import ketnoi
        from maychu.hethong import tiendo
        self.chuan_bi(lan=1, xong=3)
        cn = ketnoi.mo("Hotho", self.dl)
        try:
            ids = [r[0] for r in cn.execute("SELECT id FROM cho_day_drive WHERE trangthai = 'loi' ORDER BY rowid")]
            for i, gio in zip(ids, ("2026-11-24T14:45:00+07:00", "2026-11-24T14:35:00+07:00", "2026-11-24T14:50:00+07:00")):
                cn.execute("UPDATE cho_day_drive SET lan_thu_ke = ? WHERE id = ?", (gio, i))
        finally:
            cn.close()
        self.assertEqual(tiendo.hien(self.dl)["drive_nen"]["hen"], "2026-11-24T14:35:00+07:00")

    def test_chuong_sau_03_lan_va_tu_dong(self):
        from maychu.hethong.giamsat import thongbao
        self.chuan_bi(lan=2, xong=1)
        thongbao.quet_drive_nen(self.dl)
        self.assertEqual(self.chuong(), [])                              # 02 lần: chưa báo
        self.dat_het_xong()
        from maychu.dulieu import ketnoi
        cn = ketnoi.mo("Hotho", self.dl)
        try:
            cn.execute("UPDATE cho_day_drive SET trangthai = 'loi', so_lan_thu = 3 WHERE rowid > 1")
        finally:
            cn.close()
        thongbao.quet_drive_nen(self.dl)
        thongbao.quet_drive_nen(self.dl)                                 # quét lại: không mở đôi, không ghi F04 đôi
        ds = self.chuong()
        self.assertEqual(len(ds), 1)
        x = ds[0]
        self.assertEqual((x["muc"], x["icon"], x["di"], x["noi"]), ("xem", "cloud-alert", "capnhat", "Cài đặt › Cập nhật"))
        self.assertEqual(x["chu"].replace(" ", " "), "Bản sao Drive sau cập nhật 0.9.9 chưa lên: 01/07 tệp, đã thử 03 lần")
        self.assertEqual(len(self.f04("drive_nen_loi")), 1)
        self.dat_het_xong()
        thongbao.quet_drive_nen(self.dl)
        self.assertEqual(self.chuong(), [])                              # đẩy đủ tệp thì tự đóng


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemTrang(unittest.TestCase):
    def node(self, ma: str) -> dict:
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "t.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_buoc_3_drive_nen_va_buoc_8_sau_khi_tai_lai(self):
        """QĐ261 dòng 2, 3: bước 3 icon cloud-upload xám "sau khi lên bản"; bước 8 chưa tới "sau khi tải lại"."""
        from kiemthu.ban081.test_y41 import T0, _td
        td = _td("tai", {"o_trong": 0, "chup": 2, "drive": 11, "gui": 12, "tai": 13}, drive={"nen": True, "da": 0, "tong": 5})
        ma = (_ma_the() + "const CHU_CN = {kiem: 'Kiểm sau cập nhật: '};\n"
              f"console.log(JSON.stringify({{h: htmlTienDo({json.dumps(td, ensure_ascii=False)}, {{bay: Date.parse('{T0}') + 60e3}})}}));\n")
        h = self.node(ma)["h"]
        d3 = h.split('3. Bản sao Drive</span>', 1)
        self.assertIn('<div class="td8-dong cho">', d3[0][-900:])
        self.assertIn("lucide-cloud-upload", d3[0][-700:])
        self.assertIn('stroke="#646A73"', d3[0][-700:])
        self.assertTrue(d3[1].startswith('<span class="td8-m">sau khi lên bản</span>'))
        self.assertIn('8. Kiểm sau cập nhật</span><span class="td8-m">sau khi tải lại</span>', h)
        self.assertNotIn("undefined", h)

    def sau_len(self, d: dict) -> dict:
        """Chạy veSauLen với phần tử giả; trả html khung #cn-saulen, lớp viền, kết quả hàm."""
        js = GD.joinpath("app.js").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("const SL = {"))
        b = next(i for i in range(a, len(js)) if js[i].endswith("};"))
        c = next(i for i, x in enumerate(js) if x.startswith("function veSauLen("))
        e = next(i for i in range(c, len(js)) if js[i] == "}")
        ma = (_ma_the() + "const CHU_CN = {kiem: 'Kiểm sau cập nhật: '};\n" + "\n".join(js[a:b + 1]) + "\n" + "\n".join(js[c:e + 1]) + r"""
const lop = new Set(), khung = {innerHTML: ''}, the = {classList: {remove: x => lop.delete(x), toggle: (x, v) => v ? lop.add(x) : lop.delete(x)}};
const $ = s => s === '#cn-saulen' ? khung : the;
""" + f"const r = veSauLen({json.dumps(d, ensure_ascii=False)});\n"
              "console.log(JSON.stringify({h: khung.innerHTML, lop: [...lop], r}));\n")
        return self.node(ma)

    def tien_do(self, buoc, **them):
        moc = {"o_trong": "2026-11-24T14:19:00+07:00", "nang": "2026-11-24T14:19:50+07:00", "kiem": "2026-11-24T14:20:05+07:00"}
        return {"tu": "0.2.0", "den": "0.3.0", "buoc": buoc, "bat_dau": "2026-11-24T14:19:00+07:00", "moc": moc, **them}

    def test_sau_tai_lai_dang_kiem_va_dang_day_drive(self):
        kq = self.sau_len({"ban_dang": "0.3.0", "tien_do": self.tien_do("kiem", chi_tiet={"da": 3, "tong": 6},
                                                                         drive_nen={"da": 3, "tong": 7, "loi": False})})
        h = kq["h"]
        for chu in ("Vừa lên bản 0.3.0 lúc 14:20 · tổng thời gian 01:05", "Kiểm sau cập nhật: đang kiểm 03/06",
                    "Bản sao Drive: đang đẩy 03/07 tệp", "lucide-loader", "lucide-cloud-upload"):
            self.assertIn(chu, h)
        self.assertEqual((kq["lop"], kq["r"]["loiKiem"], kq["r"]["keoDrive"]), ([], False, True))

    def test_sau_tai_lai_kiem_dat_drive_da_len(self):
        kq = self.sau_len({"ban_dang": "0.3.0", "kiem_hien": {"dat": True, "chu": "06/06 đạt"},
                           "tien_do": self.tien_do("xong", xong="2026-11-24T14:20:45+07:00", drive_nen={"da": 7, "tong": 7, "loi": False})})
        for chu in ("Kiểm sau cập nhật: 06/06 đạt", "Bản sao Drive: đã lên 07/07 tệp", "lucide-cloud-check"):
            self.assertIn(chu, kq["h"])
        self.assertEqual((kq["lop"], kq["r"]["keoDrive"]), ([], False))

    def test_sau_tai_lai_kiem_chua_dat_va_drive_loi(self):
        kq = self.sau_len({"ban_dang": "0.3.0", "kiem_hien": {"dat": False, "chu": "05/06 · lịch chạy nền chưa bật"},
                           "tien_do": self.tien_do("xong", xong="2026-11-24T14:20:45+07:00",
                                                   drive_nen={"da": 3, "tong": 7, "loi": True, "hen": "2026-11-24T14:35:00+07:00"})})
        h = kq["h"]
        for chu in ('class="ks canh"', "Kiểm sau cập nhật: 05/06 · lịch chạy nền chưa bật",
                    "Bản 0.3.0 vẫn chạy. Lỗi đã ghi nhật ký và báo chuông.",
                    "Bản sao Drive: chưa lên hết 03/07 tệp · tự đẩy lại từ 14:35", "lucide-cloud-alert", 'class="ks xem"'):
            self.assertIn(chu, h)
        self.assertNotIn("sau 05 phút", h)                                  # QĐ273 thay câu cũ
        self.assertEqual((kq["lop"], kq["r"]["loiKiem"], kq["r"]["keoDrive"]), (["vien-loi"], True, True))   # G2: vẫn theo dõi

    def test_khong_hien_khi_khong_phai_luot_vua_len(self):
        for td in (None, self.tien_do("tai"), {**self.tien_do("xong"), "den": "0.2.9"}, {**self.tien_do("kiem"), "treo": True}):
            kq = self.sau_len({"ban_dang": "0.3.0", "tien_do": td})
            self.assertEqual((kq["h"], kq["lop"]), ("", []))

    def test_chu_the_co_ban_moi_va_quay_ve(self):
        js = GD.joinpath("app.js").read_text(encoding="utf-8")
        for chu in ("ndKhong: 'Không nâng dữ liệu: bản sao Drive đẩy sau khi lên bản mới.'",
                    "ndCo: 'Có nâng dữ liệu: đẩy bản sao Drive xong mới cập nhật.'", "typeof d.nang_dulieu === 'boolean'",
                    "b.className = sl.loiKiem ? 'btn btn-phu' : 'btn-chu';"):
            self.assertTrue(chu in js, chu)
        self.assertIn('<div id="cn-saulen"></div>', GD.joinpath("index.html").read_text(encoding="utf-8"))

    def test_theo_kiem_hoi_den_khi_xong_roi_thoi(self):
        js = GD.joinpath("app.js").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("function theoKiem("))
        b = next(i for i in range(a, len(js)) if js[i] == "}")
        ham = "\n".join(js[a:b + 1]).replace("Date.now()", "dongHo.now()")
        ma = r"""
let T = 1, hen = [], hoi = 0, ve = [];
const D = {}, dongHo = {now: () => T};
const setTimeout = (f, ms) => { hen.push({luc: T + ms, f}); };
const api = async () => { hoi++; const dn = {da: Math.min(7, hoi), tong: 7, loi: hoi >= 5 && hoi < 7};   // G2: lượt 5–6 Drive lỗi
  return {tien_do: {buoc: hoi < 4 ? 'kiem' : 'xong', den: '0.9.9', drive_nen: dn}, lan: hoi}; };
const veCapNhat = s => { ve.push(s.lan); theoKiem(); };
""" + ham + r"""
(async () => {
  theoKiem(); theoKiem();   // gọi 02 lần: chỉ 01 vòng hỏi
  for (let i = 0; i < 500 && hen.length; i++) { hen.sort((a, b) => a.luc - b.luc); const h = hen.shift(); T = h.luc; await h.f(); }
  console.log(JSON.stringify({hoi, ve, dang: D.theoKiem, giay: Math.round(T / 1000)}));
})();
"""
        kq = self.node(ma)
        self.assertEqual(kq["hoi"], 7)                                   # kiểm xong lượt 4; Drive lỗi lượt 5–6 vẫn hỏi; đủ 07/07 lượt 7
        self.assertEqual(kq["ve"], [1, 2, 3, 4, 5, 6, 7])                # vẽ lại mỗi lượt
        self.assertEqual((kq["dang"], kq["giay"]), (False, 70))         # mỗi 10 giây, rồi thôi hỏi

    def test_tai_lai_ngay_va_khong_con_cho_xong(self):
        js = GD.joinpath("app.js").read_text(encoding="utf-8")
        for chu in ("if (k.phienban && k.phienban !== cu) { location.hash = DAU_SAU_CN; location.reload(); return; }",
                    "else if ((dangLuot && t.den === d.ban_dang) || sl.keoDrive) theoKiem();"):
            self.assertTrue(chu in js, chu)
        self.assertFalse("moiChay" in js)


    def test_sau_cap_nhat_tai_lai_ve_cai_dat_cap_nhat(self):
        """CDO U21 G1: tải lại sau cập nhật mở đúng Cài đặt › Cập nhật (dấu #sau-capnhat), rồi xóa dấu khỏi địa chỉ."""
        js = GD.joinpath("app.js").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        dau = next(x for x in js if x.startswith("const DAU_SAU_CN = "))
        a = next(i for i, x in enumerate(js) if x.startswith("async function vaoPhanMem("))
        b = next(i for i in range(a, len(js)) if js[i] == "}")
        ma = r"""
const S = {trang: '03', tab: 'thongso'}, D = {}, goi = [];
const $ = () => ({textContent: ''});
const api = async () => ({ten: 'Chu'});
const fetch = async () => ({json: async () => ({an_toan: false})});
const location = {hash: '#sau-capnhat', pathname: '/', search: ''};
const history = {replaceState: (a, b, u) => { goi.push('xoa:' + u); location.hash = ''; }};
const ve = () => goi.push('ve'), demSo = () => {}, napTab = () => goi.push('napTab:' + S.trang + '/' + S.tab);
""" + dau + "\n" + "\n".join(js[a:b + 1]) + r"""
(async () => { await vaoPhanMem(); const mot = [S.trang, S.tab, location.hash];
  S.trang = '03'; S.tab = 'thongso'; await vaoPhanMem();   // lần mở sau (không còn dấu): màn như thường
  console.log(JSON.stringify({mot, hai: [S.trang, S.tab], goi})); })();
"""
        kq = self.node(ma)
        self.assertEqual(kq["mot"], ["09", "capnhat", ""])
        self.assertIn("napTab:09/capnhat", kq["goi"])
        self.assertIn("xoa:/", kq["goi"])
        self.assertEqual(kq["hai"], ["03", "thongso"])


if __name__ == "__main__":
    unittest.main()
