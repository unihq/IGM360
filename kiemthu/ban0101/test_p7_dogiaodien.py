"""Bài kiểm 0.10.1 phần P7 – việc "dogiaodien" đo giao diện trên máy GitHub (QĐ683; CDA 05 điều kiện, bảng soát K1–K8; CPO chốt K2,
K8 cách B; phiếu dựng PD28).

Việc riêng trong luồng "Kiểm và đóng image (GHCR)": quyền mức việc chỉ đọc mã, 0 khóa bí mật, 0 gói, 0 đăng nhập kho ảnh, 0 tải ảnh lên;
tên ≠ "kiemthu", 0 chú thích "Ket qua bai kiem"; việc dongimage vẫn chỉ cần kiemthu; tugop.yml không đổi. Kịch bản trong
kiemthu/giaodien: 0 đường dẫn máy cá nhân, 0 hồ sơ trình duyệt riêng của máy, 0 khóa 02 lớp viết sẵn (dò bằng mẫu chung).
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
LUONG = GOC / ".github" / "workflows" / "dongimage.yml"
GDO = GOC / "kiemthu" / "giaodien"


def khoi_viec(yml, ten):
    i = yml.index("\n  " + ten + ":\n")
    m = re.search(r"\n  [A-Za-z_][\w-]*:\n", yml[i + 3:])
    return yml[i:i + 3 + m.start()] if m else yml[i:]


class KiemLuong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yml = LUONG.read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.viec = khoi_viec(cls.yml, "dogiaodien")

    def test_pd28_luong_an_toan(self):   # K1, K2, K8
        v = self.viec
        self.assertIn("    permissions:\n      contents: read\n", v)
        self.assertNotRegex(v, r"(?m)^\s+(packages|id-token|actions|pull-requests):")
        for x in ("secrets.", "docker login", "docker/login-action", "upload-artifact", "Ket qua bai kiem", "::notice"):
            self.assertNotIn(x, v, x)
        self.assertIn("python kiemthu/giaodien/maythu_ci.py", v)
        self.assertIn("continue-on-error: true", v)   # QĐ683: chỉ báo tới khi 05 lần chạy ổn định
        self.assertIn("permissions: {}", self.yml)     # mức luồng giữ 0 quyền

    def test_pd28_viec_dong_anh_khong_doi(self):   # CPO: dongimage chỉ needs: kiemthu (chặn đóng ảnh chưa có QĐ)
        self.assertIn("  dongimage:\n    needs: kiemthu\n", self.yml)
        self.assertNotIn("needs: [kiemthu, dogiaodien]", self.yml)

    @unittest.skipUnless(shutil.which("git"), "máy không có git")
    def test_pd28_tugop_khong_doi(self):   # QĐ259: đổi cửa tự gộp phải anh duyệt riêng
        r = subprocess.run(["git", "diff", "--quiet", "bd069dae0a94c8be92d0464373b82b865cc3eea1", "--", ".github/workflows/tugop.yml"], cwd=GOC,
                           capture_output=True)
        if r.returncode not in (0, 1):
            self.skipTest("máy chạy không có commit mốc bd069da")
        self.assertEqual(r.returncode, 0, "tugop.yml đã đổi so với 0.10.0")

    def test_pd28_kich_ban_khong_lo_may(self):   # K3, K4: dò bằng mẫu chung, không ghi tên người dùng thật
        mau = [r"[A-Za-z]:\\", r"[A-Za-z]:/Users/", r"[A-Za-z]:\\Users\\[^\\]+", r"9\. AI", r"[A-Z0-9]{1,6}~1",
               r"\.edge_an", r"msedge\.exe", r"(?<![A-Za-z0-9])[A-Z2-7]{16,}(?![A-Za-z0-9])"]   # CDA P7-SOAT-K1K8: bắt cả 01 gạch ngược, gạch xuôi
        bat = lambda t: any(re.search(m, t) for m in mau)   # bài tự chứng minh bắt đủ 04 dạng đường dẫn máy
        for t in ("C:" + chr(92) + "Users" + chr(92) + "abc", "D:" + chr(92) + "Tam", "C:/Users/abc", "C:" + chr(92) * 2 + "Users"):
            self.assertTrue(bat(t), t)
        tep = sorted(p for p in GDO.iterdir() if p.is_file())
        self.assertEqual({p.name for p in tep}, {"chay_do.mjs", "ca_giaodien.mjs", "maythu_ci.py"})
        for p in tep + [LUONG]:
            s = p.read_text(encoding="utf-8")
            for m in mau:
                self.assertIsNone(re.search(m, s), f"{p.name}: {m}")
        self.assertIn("secrets.token_urlsafe", (GDO / "maythu_ci.py").read_text(encoding="utf-8"))   # mật khẩu thử tạo lúc chạy
        self.assertIn('b1.get("khoa")', (GDO / "maythu_ci.py").read_text(encoding="utf-8"))          # khóa 02 lớp do máy chủ tạo


class KiemCham(unittest.TestCase):   # ngưỡng chấm của kịch bản – chứng minh bắt được lỗi đã gặp
    @classmethod
    def setUpClass(cls):
        import importlib.util
        sp = importlib.util.spec_from_file_location("maythu_ci", GDO / "maythu_ci.py")
        cls.m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(cls.m)

    def test_pd28_cham_bat_loi_cu(self):
        c = self.m.cham
        self.assertTrue(c("M01", {"ten": "M01_p13", "kho": "1440x900", "chedo": "sang", "gt": {"so_de": 3, "de": [["cụm", "Thêm nguồn AI"]], "so_che": 0}}))   # L14 a
        self.assertTrue(c("M02", {"ten": "M02_p03", "kho": "1440x900", "chedo": "sang", "gt": {"lech": [1441, 0], "cum_trong_khung": True}}))   # L14 b
        self.assertTrue(c("M03", {"ten": "M03_p08", "kho": "1440x900", "chedo": "sang", "gt": {"kq": [{"vt": 0, "ngoai_px": 2289}]}}))   # L14 c
        self.assertTrue(c("M05", {"ten": "M05_p08", "kho": "1440x900", "chedo": "sang", "gt": {"so_vuot": 1, "vuot": [["#tc-tim", ".tc-trai", 11]], "so_cat_khong_cham": 0, "nhom": []}}))
        self.assertTrue(c("M08", {"ten": "M08_p13", "kho": "1280x800", "chedo": "sang", "gt": {"top": [123] * 3, "cao": [308] * 3, "rong": [307] * 3,
                                                                                              "nut_chinh": [[325, 365], [357, 397], None], "hang_nut": [], "chi_phi": [], "ten": [], "mo_ta": []}}))
        mo = {"logo": {"tam": 37}, "ghim": {"hop": [0, 74, 0, 40]}, "chan": {"hop": [0, 797, 0, 52]}, "chu_thu_gon_hien": False, "chu_cat": []}
        thu = {"nav_rong": 68, "ghim": {"hop": [0, 74, 0, 40]}, "gd": {"hop": [12, 640, 44, 30]}, "chu_cat": ["button.gd-nut:Hiện"]}
        self.assertTrue(c("M11", {"ten": "M11_thanh", "kho": "1440x900", "chedo": "sang", "gt": {"mo": mo, "thu": thu}}))   # LOI-THU-GDSAU 4c73aa0
        self.assertEqual(c("M11", {"ten": "M11_thanh", "kho": "1440x900", "chedo": "sang", "gt": {"mo": mo, "thu": dict(thu, gd=None, chu_cat=[])}}), [])
        o = lambda vt, k: {"vt": vt, "ngoai_px": 0, "day_khoi": k, "mep_tab": 784.5}
        self.assertTrue(c("M03", {"ten": "M03_p08", "kho": "390x844", "chedo": "toi", "gt": {"kq": [o(0, 784.5), o(0.5, 784.5), o(1, 780)]}}))   # SOAT-GD-0101 (02)
        self.assertTrue(c("M03", {"ten": "M03_p08", "kho": "390x844", "chedo": "toi", "gt": {"kq": [o(0, 784.5), o(0.5, 784.5), o(1, 784)]}}))   # L02-05PX: 167af8b lệch 0,5 → không đạt
        k = lambda vt: {"vt": vt, "ngoai_px": 0, "day_khoi": 784, "mep_tab": 784}
        self.assertEqual(c("M03", {"ten": "M03_p08", "kho": "390x844", "chedo": "toi", "gt": {"kq": [k(0), k(0.5), k(1)]}}), [])   # khít 0 px: đạt
        self.assertIn(("M03", {"BAI": "M03", "KHO": "390", "CHEDO": "toi"}), self.m.LUOT)   # đo cả chế độ Tối (vạch nền chỉ thấy ở Tối)
        nhan = [self.m.nhan_luot(b, v) for b, v in self.m.LUOT]   # CPO NHAN-M03: mỗi lượt 01 nhãn riêng ở bảng + chú thích
        self.assertEqual(len(nhan), len(set(nhan)), nhan)
        self.assertIn("M03 Tối", nhan)
        ds = self.m.chu_thich([("M03", 3, 3, []), ("M03 Tối", 1, 0, ["M03_p08 390x844 toi: lệch"])], [("M03 Tối", {"gt": {"kq": "toi"}})])
        self.assertTrue(ds[0].startswith("::error title=Do giao dien M03 Tối::") and '"toi"' in ds[0], ds[0])
        self.assertTrue(c("M03", {"ten": "M03_p08", "kho": "390x844", "chedo": "toi", "gt": {"kq": []}}))   # 390 không thấy thanh tab: không đạt

    def test_pd28_chu_thich_cong_khai(self):   # CPO DOC-KQ-CONGKHAI: số đo ca đỏ đọc được qua API, không cần đăng nhập
        bang = [("M01", 26, 24, ["M01_p13 1440x900 sang: đè 3: [['cụm', 'Thêm nguồn AI']]", "M01_p03 1024x768 sang: che 1: []"]),
                ("M03", 3, 3, [])] + [(f"X{i}", 1, 0, ["lỗi 100%\nxuống dòng"]) for i in range(12)]
        do = [("M01", {"ten": "M01_p13", "gt": {"so_de": 3, "de": [["cụm", "Thêm nguồn AI"]]}})]
        ds = self.m.chu_thich(bang, do)
        self.assertEqual(len(ds), 10)                                            # 09 lỗi + 01 tổng kết (máy GitHub nhận ≤ 10 lỗi mỗi bước)
        self.assertTrue(all(x.startswith(("::error title=Do giao dien", "::notice title=Do giao dien::")) for x in ds))
        self.assertTrue(ds[-1].startswith("::notice"))
        self.assertNotIn("Ket qua bai kiem", "\n".join(ds))                     # K2: tugop.yml đếm theo tiêu đề đó
        self.assertTrue(all("\n" not in x and "\r" not in x for x in ds))        # mỗi chú thích 01 dòng lệnh
        self.assertIn("%0ASố đo ca đỏ đầu: {\"so_de\": 3", ds[0])
        self.assertIn("100%25", ds[1])
        self.assertNotIn("M03", "".join(ds[:-1]))                              # bài đạt không thành lỗi
        self.assertEqual(self.m.chu_thich([("M01", 26, 26, [])], []), ["::notice title=Do giao dien::26/26 ca đạt; M01 26/26"])

    def test_pd28_che_gia_tri_bi_mat(self):   # CDA DOC-CHUTHICH-KQ: mật khẩu thử, khóa 02 lớp, cookie phiên đăng ký che trước khi in
        import contextlib
        import io
        import os
        from unittest import mock
        for bien, ra in (({"GITHUB_ACTIONS": "true"}, "::add-mask::abc123\n"), ({"GITHUB_ACTIONS": ""}, "")):
            with mock.patch.dict(os.environ, bien), contextlib.redirect_stdout(io.StringIO()) as o:
                self.m.che("abc123")
                self.m.che("")
            self.assertEqual(o.getvalue(), ra)
        nd = (GDO / "maythu_ci.py").read_text(encoding="utf-8")
        i = nd.index("def main():")
        for x in ("che(mk)", "che(khoa)", "che(phien)"):
            self.assertIn(x, nd[i:])
        self.assertLess(nd.index("che(mk)"), nd.index("IGM360_ADMIN_PASSWORD=mk"))   # che trước khi dùng

    def test_pd28_cham_dat(self):
        c = self.m.cham
        self.assertEqual(c("M01", {"ten": "M01_p03", "kho": "1440x900", "chedo": "sang", "gt": {"so_de": 0, "de": [], "so_che": 0, "che": []}}), [])
        self.assertEqual(c("M07", {"ten": "M07_2_keo_lon", "kho": "1024x768", "chedo": "sang", "gt": {"cot": 280, "tc": 768}}), [])
        self.assertEqual(c("M07", {"ten": "M07_6_thu", "kho": "1440x900", "chedo": "sang", "gt": {"cot": 56, "tc": 1184, "dai_nut": ["a", "b", "c"]}}), [])


if __name__ == "__main__":
    unittest.main()
