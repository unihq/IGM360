"""Máy kiểm chữ cấm: mã IGM360 không được chứa tên của mã gốc (Khung phần mềm, mục chữ cấm).
Chữ cấm ghép từ từng mảnh để chính tệp này không chứa chữ cấm."""
import re
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THUMUC_KIEM = ("maychu", "giaodien", "kiemthu", "mauketnoi")
CHU_CAM = re.compile("|".join(["ja" + "vis", "uni" + "mate", "uni" + r"[ _\-]" + "mate"]), re.IGNORECASE)


class KiemChuCam(unittest.TestCase):
    def test_khong_co_chu_cam(self):
        pham = []
        for tm in THUMUC_KIEM:
            for tep in (GOC / tm).rglob("*") if (GOC / tm).is_dir() else []:
                if tep.is_file() and "__pycache__" not in tep.parts:
                    try:
                        noi = tep.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    if CHU_CAM.search(noi) or CHU_CAM.search(tep.name):
                        pham.append(str(tep.relative_to(GOC)))
        self.assertEqual(pham, [])


if __name__ == "__main__":
    unittest.main()
