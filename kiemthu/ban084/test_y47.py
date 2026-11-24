"""Bài kiểm Y47 (QĐ269, QĐ272, QĐ304): 14 tệp AGENTS.md hướng dẫn AI theo thư mục.

- Đúng 14 tệp ở đúng 14 thư mục, không tệp AGENTS.md nào khác, không CLAUDE.md trong kho mã.
- Mỗi tệp đủ 07 mục đúng thứ tự, tối đa 60 dòng.
- Kho công khai: không địa chỉ IP, tên miền, đường dẫn ổ đĩa, email, tên tài khoản, chữ cấm; chữ viết dấu kiểu mới.
"""
import re
import subprocess
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
THU_MUC = (".", ".github/workflows", "kiemthu", "maychu", "maychu/dulieu", "maychu/dulieu/luocdo", "maychu/hethong",
           "maychu/hethong/kekhoa", "maychu/hethong/taikhoan", "maychu/hethong/mohinh", "maychu/hethong/giamsat",
           "maychu/ketnoi", "maychu/web", "maychu/web/giaodien")
MUC = ("## 1. Vai thư mục", "## 2. Đọc gì trước", "## 3. Luật bắt buộc", "## 4. Được chứa / không được chứa",
       "## 5. Quyết định đã chốt – không tự đảo", "## 6. Kiểm trước bàn giao", "## 7. Người giữ")
CAM = {
    "địa chỉ IP": re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "đường dẫn ổ đĩa": re.compile(r"\b[A-Za-z]:[\\/]|/home/|/Users/|\\\\"),
    "tên miền, địa chỉ web": re.compile(r"://|\b[\w-]+\.(?:com|vn|net|io|org|dev|app)\b", re.I),
    "tên tài khoản": re.compile("Mr" + "-Jin|Mr" + r"\. ?Đạt|@" + "[A-Za-z]"),
    "chữ cấm": re.compile("|".join(["ja" + "vis", "uni" + "mate", "uni" + r"[ _\-]" + "mate"]), re.I),
    # QĐ304: chữ mới viết dấu kiểu mới (vần mở oa, oe, uy không phụ âm cuối, không sau "q")
    "dấu kiểu cũ": re.compile(r"(?<![qQ])[oO][àáảãạèéẻẽẹ](?![\wà-ỹ])|(?<![qQ])[uU][ỳýỷỹỵ](?![\wà-ỹ])"),
}


def doc(tm):
    return (GOC / tm / "AGENTS.md").read_text(encoding="utf-8")


class KiemTepHuongDanAI(unittest.TestCase):
    def test_dung_14_tep_khong_claude_md(self):
        for tm in THU_MUC:
            self.assertTrue((GOC / tm / "AGENTS.md").is_file(), tm)
        ra = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=GOC,
                            capture_output=True, text=True, encoding="utf-8")
        if ra.returncode == 0 and ra.stdout:
            tep = ra.stdout.split("\n")
            co = sorted(str(Path(t).parent).replace("\\", "/") for t in tep if Path(t).name == "AGENTS.md")
            self.assertEqual(co, sorted(THU_MUC))                               # không có AGENTS.md ngoài 14 thư mục
            self.assertEqual([t for t in tep if Path(t).name == "CLAUDE.md"], [])   # QĐ269

    def test_du_07_muc_dung_thu_tu_toi_da_60_dong(self):
        for tm in THU_MUC:
            with self.subTest(tm=tm):
                chu = doc(tm)
                self.assertLessEqual(len(chu.splitlines()), 60)
                vi = [chu.find("\n" + m + "\n") for m in MUC]
                self.assertNotIn(-1, vi, [m for m, v in zip(MUC, vi) if v < 0])
                self.assertEqual(vi, sorted(vi))
                self.assertTrue(chu.startswith("# AGENTS.md – " + ("gốc kho IGM360" if tm == "." else tm)))

    def test_khong_thong_tin_nhay_cam_va_dau_kieu_moi(self):
        for tm in THU_MUC:
            for ten, mau in CAM.items():
                with self.subTest(tm=tm, loai=ten):
                    self.assertEqual([m.group(0) for m in mau.finditer(doc(tm))], [])

    def test_thu_muc_khong_co_tep_rieng_ghi_o_tep_cha(self):
        """CDA (Y47 bổ sung): thư mục không có tệp riêng ghi tên ở tệp thư mục cha gần nhất có tệp."""
        for tm, con in ((".", (".github", ".github/cua", "tailieu")), ("maychu", ("mauketnoi",)),
                        ("maychu/hethong", ("caidat", "nhatky")), ("maychu/web/giaodien", ("logo",)),
                        ("kiemthu", ("banXXX", "ngayXX"))):
            for c in con:
                with self.subTest(tm=tm, con=c):
                    self.assertIn("`" + c + "`", doc(tm))


if __name__ == "__main__":
    unittest.main()
