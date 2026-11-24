"""Bài kiểm Y44 (QĐ259, QĐ266, CDA KT-Y44): cửa chặn tự gộp bản sửa lỗi và quét chung.

Mỗi bài dựng 01 kho git tạm (nhánh main + nhánh sualoi/*), chạy đúng công cụ .github/cua/*.py như tệp luồng tugop.yml.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CUA = GOC / ".github" / "cua"

THAYDOI = """# Thay đổi

## 0.9.1
Tóm tắt: Bản trước
Nâng dữ liệu: không
- Việc cũ.

## 0.9.0
Tóm tắt: Bản cũ hơn
Nâng dữ liệu: có
- Việc cũ hơn.
"""
MUC_MOI = "## 0.9.2\nTóm tắt: Sửa lỗi nhỏ\nNâng dữ liệu: không\n- Sửa lỗi tính tổng.\n\n"
MA_GOC = {
    "VERSION": "0.9.1\n",
    "THAYDOI.md": THAYDOI,
    "requirements.txt": "httpx==0.27.2\n",
    "Dockerfile": "FROM python\n",
    "maychu/__init__.py": "",
    "maychu/hethong/mohinh/tinh.py": 'import json\nimport httpx\n\n\ndef tong(a, b):\n    """Cộng 02 số."""\n    return a + b\n\n\nCHU = "Đã lưu"\n',
    "maychu/dulieu/ketnoi.py": "SO = 1\n",
    "kiemthu/test_cu.py": "import unittest\n\n\nclass K(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(1, 1)\n",
}


@unittest.skipUnless(shutil.which("git"), "máy không có git")
class NenKho(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.k = Path(self.tam.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "kiem@vidu.invalid")
        self.git("config", "user.name", "Kiem")
        for ten, chu in MA_GOC.items():
            self.ghi(ten, chu)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "goc")
        self.git("switch", "-q", "-c", "sualoi/tong")

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.k, capture_output=True, text=True, encoding="utf-8", check=True).stdout

    def ghi(self, ten, chu):
        p = self.k / ten
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(chu, encoding="utf-8", newline="\n")

    def ban_hop_le(self):
        self.ghi("VERSION", "0.9.2\n")
        self.ghi("THAYDOI.md", THAYDOI.replace("## 0.9.1", MUC_MOI + "## 0.9.1", 1))

    def chay(self, cong_cu="kiem_sualoi.py", nhanh="sualoi/tong", *them):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "doi", "--allow-empty")
        lenh = [sys.executable, str(CUA / cong_cu), "--goc", "main", "--dau", "HEAD"]
        if cong_cu == "kiem_sualoi.py":
            lenh += ["--nhanh", nhanh, *them]
        r = subprocess.run(lenh, cwd=self.k, capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONUTF8": "1"})
        return r.returncode, r.stdout


class KiemCuaChan(NenKho):
    def test_ban_sua_loi_hop_le_dat(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/tinh.py", MA_GOC["maychu/hethong/mohinh/tinh.py"].replace("return a + b", "return int(a) + int(b)"))
        self.ghi("kiemthu/test_moi.py", "import unittest\n\n\nclass M(unittest.TestCase):\n    def test_b(self):\n        pass\n")
        ma, ra = self.chay("kiem_sualoi.py", "sualoi/tong", "--kiem-goc", "Ran 10 tests in 1s OK (skipped=1)",
                           "--kiem-dau", "Ran 11 tests in 1s OK (skipped=1)")
        self.assertEqual((ma, ra.strip().splitlines()[-1]), (0, "KẾT QUẢ: ĐẠT 0"), ra)

    def kiem_chan(self, mau: str, nhanh="sualoi/tong", *them):
        ma, ra = self.chay("kiem_sualoi.py", nhanh, *them)
        self.assertEqual(ma, 1, ra)
        self.assertIn(mau, ra)

    def test_chan_theo_duong_dan(self):
        for ten, luat in (("Dockerfile", "Luật 12"), ("maychu/dulieu/ketnoi.py", "Luật 01"), ("requirements.txt", "Luật 11")):
            with self.subTest(ten=ten):
                self.ban_hop_le()
                self.ghi(ten, (self.k / ten).read_text(encoding="utf-8") + "# doi\n")
                self.kiem_chan(f"{luat}: chạm {ten}")
                self.git("reset", "-q", "--hard", "main")

    def test_luat_15_cau_truc_du_lieu(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/tinh.py", MA_GOC["maychu/hethong/mohinh/tinh.py"] + 'Q = "create unique index i on t(a)"\n')
        self.kiem_chan("Luật 15: maychu/hethong/mohinh/tinh.py:11")

    def test_luat_16_thu_vien_moi_va_nap_dong(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/tinh.py", "import numpy\nimport importlib\nM = importlib.import_module('x')\n"
                 + MA_GOC["maychu/hethong/mohinh/tinh.py"])
        ma, ra = self.chay()
        self.assertEqual(ma, 1)
        self.assertIn("Luật 16: maychu/hethong/mohinh/tinh.py:1 thư viện ngoài mới numpy", ra)
        self.assertIn("nạp module động", ra)
        self.assertNotIn("thư viện ngoài mới importlib", ra)                      # thư viện chuẩn
        self.assertNotIn("thư viện ngoài mới httpx", ra)                          # đã có trong requirements, đã dùng trên main

    def test_luat_17_nang_du_lieu(self):
        self.ban_hop_le()
        self.ghi("THAYDOI.md", (self.k / "THAYDOI.md").read_text(encoding="utf-8").replace("Nâng dữ liệu: có", "Nâng dữ liệu: không"))
        self.kiem_chan('Luật 17: đổi dòng "Nâng dữ liệu" của bản 0.9.0')
        self.git("reset", "-q", "--hard", "main")
        self.ghi("VERSION", "0.9.2\n")
        self.ghi("THAYDOI.md", THAYDOI.replace("## 0.9.1", MUC_MOI.replace("Nâng dữ liệu: không", "Nâng dữ liệu: có") + "## 0.9.1", 1))
        self.kiem_chan('Luật 17: mục 0.9.2 phải ghi "Nâng dữ liệu: không"')

    def test_luat_18_bai_kiem_cu(self):
        cu = MA_GOC["kiemthu/test_cu.py"]
        for moi, mau in ((cu.replace("assertEqual(1, 1)", "assertTrue(True)"), "Luật 18: kiemthu/test_cu.py xoá hoặc sửa 01 dòng"),
                         (cu + "\n    @unittest.skip('tạm')\n    def test_c(self):\n        pass\n", "thêm lệnh bỏ qua bài kiểm"),
                         (cu + "\n    def test_a(self):\n        pass\n", "trùng tên hàm K.test_a")):
            with self.subTest(mau=mau):
                self.ban_hop_le()
                self.ghi("kiemthu/test_cu.py", moi)
                self.kiem_chan(mau)
                self.git("reset", "-q", "--hard", "main")
        self.ban_hop_le()
        self.kiem_chan("Luật 18: số bài chạy 9 ít hơn main 10", "sualoi/tong", "--kiem-goc", "Ran 10 tests in 1s OK",
                       "--kiem-dau", "Ran 9 tests in 1s OK")
        self.kiem_chan("Luật 18: số bài bỏ qua 2 nhiều hơn main 1", "sualoi/tong", "--kiem-goc", "Ran 10 tests OK (skipped=1)",
                       "--kiem-dau", "Ran 10 tests OK (skipped=2)")

    def test_luat_20_them_xoa_doi_ten(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/moi.py", "X = 1\n")
        self.kiem_chan("Luật 20: thêm tệp ngoài kiemthu/: maychu/hethong/mohinh/moi.py")
        self.git("reset", "-q", "--hard", "main")
        self.ban_hop_le()
        self.git("mv", "maychu/hethong/mohinh/tinh.py", "maychu/hethong/mohinh/tinh2.py")
        self.kiem_chan("Luật 20: đổi tên tệp ngoài kiemthu/")

    def test_luat_21_chu_nguoi_dung_thay(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/tinh.py", MA_GOC["maychu/hethong/mohinh/tinh.py"].replace('"Đã lưu"', '"Đã lưu xong"'))
        self.kiem_chan("Luật 21: maychu/hethong/mohinh/tinh.py thêm chữ tiếng Việt người dùng thấy")
        self.git("reset", "-q", "--hard", "main")
        self.ban_hop_le()   # chuỗi mô tả hàm, chú thích có dấu: không chặn
        self.ghi("maychu/hethong/mohinh/tinh.py", MA_GOC["maychu/hethong/mohinh/tinh.py"].replace('"""Cộng 02 số."""', '"""Cộng 02 số nguyên."""')
                 + "# Ghi chú có dấu\n")
        ma, ra = self.chay()
        self.assertEqual(ma, 0, ra)

    def test_khuon_co_gi_moi_qd270(self):
        self.ghi("VERSION", "0.9.2\n")
        self.ghi("THAYDOI.md", THAYDOI.replace("## 0.9.1", MUC_MOI.replace("- Sửa lỗi tính tổng.", "- Tính tổng đúng hơn.") + "## 0.9.1", 1))
        self.kiem_chan('chưa theo khuôn "Sửa lỗi <mô tả ngắn>" (QĐ270)')

    def test_nhanh_va_so_ban(self):
        self.ban_hop_le()
        self.kiem_chan("Nhánh: chỉ nhánh sualoi/* được tự gộp", "tinhnang/x")
        self.git("reset", "-q", "--hard", "main")
        self.ghi("VERSION", "0.10.0\n")
        self.kiem_chan("Số bản: bản sửa lỗi phải là 0.9.2")


class KiemQuetChung(NenKho):
    def test_bat_mau_chung_khong_in_gia_tri(self):
        khoa = "-----BEGIN " + "RSA PRIVATE KEY-----"
        ma_gh = "gh" + "p_" + "A1b2C3d4" * 5
        ip = ".".join(["8", "8", "4", "4"])
        thu = "nguoi" + "@" + "congty-thu" + "." + "com"
        self.ghi("maychu/hethong/mohinh/lo.py", f'K = "{khoa}"\nT = "{ma_gh}"\nI = "{ip}"\nE = "{thu}"\n')
        ma, ra = self.chay("quet_chung.py")
        self.assertEqual(ma, 1)
        for x in ("khoá riêng: maychu/hethong/mohinh/lo.py:1", "mã GitHub: maychu/hethong/mohinh/lo.py:2",
                  "địa chỉ IP công cộng: maychu/hethong/mohinh/lo.py:3", "email: maychu/hethong/mohinh/lo.py:4"):
            self.assertIn(x, ra)
        for x in (ma_gh, ip, thu):
            self.assertNotIn(x, ra)                                              # chỉ in loại và vị trí

    def test_khong_bat_dia_chi_noi_bo_va_email_mau(self):
        noi_bo, tai_lieu = ".".join(["10", "0", "0", "5"]), ".".join(["203", "0", "113", "9"])   # ghép lúc chạy: máy quét kho
        self.ghi("maychu/hethong/mohinh/lo.py", f'A = "localhost"\nB = "{noi_bo}"\nC = "{tai_lieu}"\nD = "x@vidu.invalid"\nV = "0.8.2"\n')
        ma, ra = self.chay("quet_chung.py")
        self.assertEqual((ma, ra.strip()), (0, "KẾT QUẢ: ĐẠT 0"))


class KiemSuaY44c(NenKho):
    """CDA KT-Y44c: N1 so từ điểm rẽ nhánh (main đi trước không chặn nhầm), N2 số bài lấy từ dòng tổng kết cuối."""

    def main_di_truoc(self):   # sau khi rẽ nhánh, main có thêm 01 commit chạm tệp bị chặn và 01 địa chỉ IP công cộng
        self.git("switch", "-q", "main")
        ip = ".".join(["8", "8", "4", "4"])
        self.ghi("Dockerfile", MA_GOC["Dockerfile"] + "# main doi\n")
        self.ghi("maychu/dulieu/ketnoi.py", MA_GOC["maychu/dulieu/ketnoi.py"] + f'MAY = "{ip}"\n')
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "main di truoc")
        self.git("switch", "-q", "sualoi/tong")

    def test_n1_main_di_truoc_khong_chan_nham(self):
        self.ban_hop_le()
        self.ghi("maychu/hethong/mohinh/tinh.py", MA_GOC["maychu/hethong/mohinh/tinh.py"].replace("return a + b", "return int(a) + int(b)"))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "sua")
        self.main_di_truoc()
        ma, ra = self.chay("kiem_sualoi.py", "sualoi/tong")
        self.assertEqual((ma, ra.strip().splitlines()[-1]), (0, "KẾT QUẢ: ĐẠT 0"), ra)
        ma, ra = self.chay("quet_chung.py")
        self.assertEqual((ma, ra.strip()), (0, "KẾT QUẢ: ĐẠT 0"), ra)

    def test_n1_van_chan_phan_doi_cua_nhanh(self):
        self.ban_hop_le()
        self.ghi("requirements.txt", MA_GOC["requirements.txt"] + "# doi\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "sua")
        self.main_di_truoc()
        ma, ra = self.chay("kiem_sualoi.py", "sualoi/tong")
        self.assertEqual(ma, 1, ra)
        self.assertIn("Luật 11: chạm requirements.txt", ra)
        self.assertNotIn("Dockerfile", ra)                                       # phần đổi của main không tính vào nhánh

    def test_n2_lay_dong_tong_ket_cuoi(self):
        sys.path.insert(0, str(CUA))
        self.addCleanup(sys.path.remove, str(CUA))
        import kiem_sualoi
        gia = "Ran 9999 tests in 0s OK (skipped=0) Ran 11 tests in 1.2s OK (skipped=2)"
        self.assertEqual(kiem_sualoi.doc_so_bai(gia), (11, 2))
        self.assertEqual(kiem_sualoi.doc_so_bai("Ran 11 tests in 1s OK OK (skipped=7)"), (11, 7))
        self.assertEqual(kiem_sualoi.doc_so_bai("Ran 5 tests in 1s OK (skipped=3) Ran 11 tests in 1s OK"), (11, 0))
        self.assertEqual(kiem_sualoi.doc_so_bai(""), (None, 0))
        self.ban_hop_le()
        ma, ra = self.chay("kiem_sualoi.py", "sualoi/tong", "--kiem-goc", "Ran 10 tests in 1s OK",
                           "--kiem-dau", "Ran 99 tests in 0s OK Ran 9 tests in 1s OK")
        self.assertEqual(ma, 1, ra)
        self.assertIn("Luật 18: số bài chạy 9 ít hơn main 10", ra)

    def test_n2_tugop_loc_tieu_de_lay_cuoi(self):
        lenh = (GOC / ".github/workflows/tugop.yml").read_text(encoding="utf-8")
        self.assertIn('select(.title == "Ket qua bai kiem")', lenh)
        self.assertIn("| last // empty", lenh)
        self.assertNotIn("grep -m1", lenh)
        dg = (GOC / ".github/workflows/dongimage.yml").read_text(encoding="utf-8")
        self.assertIn("::notice title=Ket qua bai kiem::", dg)                    # đúng tiêu đề bước "Chạy bài kiểm" ghi


class KiemTepLuongTuGop(unittest.TestCase):
    def test_tugop_chay_ban_main_va_khong_chay_ma_nhanh(self):
        import yaml
        wf = yaml.safe_load((GOC / ".github/workflows/tugop.yml").read_text(encoding="utf-8"))
        on = wf.get(True, wf.get("on"))
        self.assertEqual(on["workflow_run"]["branches"], ["sualoi/**"])
        self.assertEqual(on["workflow_run"]["workflows"], ["Kiểm và đóng image (GHCR)"])
        job = wf["jobs"]["tugop"]
        self.assertIn("conclusion == 'success'", job["if"])
        buoc = job["steps"]
        self.assertEqual(buoc[0]["with"]["ref"], "main")                          # công cụ cửa chặn lấy từ main
        lenh = "\n".join(b.get("run", "") for b in buoc)
        self.assertIn(".github/cua/kiem_sualoi.py", lenh)
        self.assertIn(".github/cua/quet_chung.py", lenh)
        self.assertIn("--match-head-commit", lenh)
        self.assertIn("gh workflow run dongimage.yml", lenh)
        self.assertNotIn("pip install", lenh)                                     # không chạy mã của nhánh
        self.assertLess(lenh.index("kiem_sualoi.py"), lenh.index("gh pr merge"))
        self.assertLess(lenh.index("quet_chung.py"), lenh.index("gh pr merge"))
        dg = (GOC / ".github/workflows/dongimage.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", dg)


if __name__ == "__main__":
    unittest.main()
