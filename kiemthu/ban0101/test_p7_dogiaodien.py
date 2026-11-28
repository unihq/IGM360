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
        mau = [r"[A-Za-z]:\\\\", r"9\. AI", r"[A-Za-z]:\\\\Users\\\\[^\\\\]+", r"[A-Z0-9]{1,6}~1", r"\.edge_an", r"msedge\.exe", r"(?<![A-Za-z0-9])[A-Z2-7]{16,}(?![A-Za-z0-9])"]
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

    def test_pd28_cham_dat(self):
        c = self.m.cham
        self.assertEqual(c("M01", {"ten": "M01_p03", "kho": "1440x900", "chedo": "sang", "gt": {"so_de": 0, "de": [], "so_che": 0, "che": []}}), [])
        self.assertEqual(c("M07", {"ten": "M07_2_keo_lon", "kho": "1024x768", "chedo": "sang", "gt": {"cot": 280, "tc": 768}}), [])
        self.assertEqual(c("M07", {"ten": "M07_6_thu", "kho": "1440x900", "chedo": "sang", "gt": {"cot": 56, "tc": 1184, "dai_nut": ["a", "b", "c"]}}), [])


if __name__ == "__main__":
    unittest.main()
