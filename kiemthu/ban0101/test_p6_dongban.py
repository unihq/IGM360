"""Bài kiểm 0.10.1 phần P6 – đóng bản (phiếu dựng PD22, PD24; CDA SOAT-PD0101-CDA, SOAT-PD0101b; QA S10, S11; QĐ673).

PD22: 0 đổi dữ liệu – lược đồ giữ bản 5 và mọi tệp đổi so với 0.10.0 (bd069da) chỉ nằm trong 05 chỗ cho phép: giao diện
`maychu/web/giaodien/`, bài kiểm `kiemthu/`, `VERSION`, `THAYDOI.md`, đúng 01 tệp luồng `.github/workflows/dongimage.yml` (P7).
Tệp khác trong `maychu/` (thông số P01, API, khởi động) hay `tugop.yml`, `.github/cua/` là ĐỎ. PD24: không có nút "‹ Thu nhỏ" (QĐ673).
"""
import shutil
import subprocess
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
MOC = "bd069dae0a94c8be92d0464373b82b865cc3eea1"   # main 0.10.0 (QĐ670)
CHO_PHEP = ("maychu/web/giaodien/", "kiemthu/")
CHO_PHEP_TEP = {"VERSION", "THAYDOI.md", ".github/workflows/dongimage.yml"}


class KiemDongBan(unittest.TestCase):
    def test_pd22_luoc_do_giu_ban_5(self):
        from maychu.dulieu import khoitao
        self.assertEqual(khoitao.PHIENBAN_LUOCDO, 5)

    @unittest.skipUnless(shutil.which("git"), "máy không có git")
    def test_pd22_chi_doi_tep_cho_phep(self):
        r = subprocess.run(["git", "diff", "--name-only", MOC], cwd=GOC, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            self.skipTest("máy chạy không có commit mốc bd069da")
        doi = [x for x in r.stdout.splitlines() if x.strip()]
        ngoai = [x for x in doi if not x.startswith(CHO_PHEP) and x not in CHO_PHEP_TEP]
        self.assertEqual(ngoai, [], "tệp đổi ngoài 05 chỗ cho phép")

    def test_pd23_thaydoi_khop_version(self):   # CPO chốt A: VERSION + mục THAYDOI anh duyệt lưu cùng 01 lần ("Bản 0.10.1")
        from maychu.hethong import capnhat
        ban = (GOC / "VERSION").read_text(encoding="utf-8").strip()
        muc = next((m for m in capnhat.phan_tich_thaydoi((GOC / "THAYDOI.md").read_text(encoding="utf-8")) if m["ban"] == ban), None)
        self.assertIsNotNone(muc, f"THAYDOI thiếu mục {ban}")
        self.assertIn(ban, ("0.10.0", "0.10.1"))
        if ban == "0.10.1":   # 0.10.1 không nâng lược đồ (PD22)
            self.assertIs(muc["nang_dulieu"], False)
            self.assertTrue(muc["tomtat"] and len(muc["tomtat"]) < 50)

    def test_pd24_khong_nut_thu_nho(self):
        for tep in ("index.html", "app.js"):
            self.assertNotIn("Thu nhỏ", (GOC / "maychu" / "web" / "giaodien" / tep).read_text(encoding="utf-8"), tep)


if __name__ == "__main__":
    unittest.main()
