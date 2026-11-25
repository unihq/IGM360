"""Bài kiểm Y50 (bản 0.8.5; QĐ298, QĐ301, QĐ302): đổi dấu kiểu mới toàn phần mềm.

- 0 chỗ dấu kiểu cũ trong mọi tệp chữ của kho (vần mở oa, oe, uy có dấu ở nguyên âm sau, không phụ âm cuối, không sau
  "q"; không phân biệt hoa thường). Mẫu dò viết bằng lớp ký tự, không chứa chữ kiểu cũ.
- QĐ301: đổi 02 chữ đã lưu trên máy chủ theo 05 điều kiện CDA KT-Y50 (`maychu/dulieu/doidau.py`).
"""
import os
import re
import subprocess
import tempfile
import unicodedata
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import doidau, khoitao, ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN

GOC = Path(__file__).resolve().parents[2]
CU = re.compile(r"(?<![qQ])[oO][àáảãạèéẻẽẹÀÁẢÃẠÈÉẺẼẸ](?!\w)|(?<![qQ])[uU][ỳýỷỹỵỲÝỶỸỴ](?!\w)")
# Ngoại lệ chính thức (QĐ333, anh: "bản cũ thì bỏ qua, áp dụng từ bản mới."): 02 thư mục là bản chép máy của mã 0.7.9
# (d369e42), đúng từng byte, "KHÔNG sửa tay" (00. Noidung.txt); dùng cho bài Y40 (luocdo_ban3), Y41 (ma_079) và công cụ
# nâng ngày 10. Giữ nguyên 11 chỗ dấu kiểu cũ trong 02 thư mục này; mọi tệp khác 0 chỗ (QĐ302).
NGOAI_LE = ("kiemthu/ban080/luocdo_ban3/", "kiemthu/ban081/ma_079/")


def ve_kieu_cu(chu: str) -> str:
    """Đổi ngược kiểu mới → kiểu cũ (dời dấu về nguyên âm sau), để so chữ cũ viết bằng mã ký tự."""
    def doi(m):
        a, b = m.group(1), m.group(2)
        tach = unicodedata.normalize("NFD", a)
        return tach[0] + unicodedata.normalize("NFC", b + tach[1:])
    return re.sub(r"(?<![qQ])([òóỏõọÒÓỎÕỌùúủũụÙÚỦŨỤ])([aeyAEY])(?!\w)", doi, chu)


class KiemKhongConDauKieuCu(unittest.TestCase):
    def test_mau_do(self):
        for tu in ("kho\u00e1", "KHO\u00c1", "xo\u00e1", "hu\u1ef7", "HU\u1ef6", "kho\u1ebb", "ho\u1ea1", "to\u00e0", "tu\u1ef3"):
            self.assertTrue(CU.search(tu), tu)
        for tu in ("khóa", "KHÓA", "xóa", "hủy", "khỏe", "họa", "hoán", "thoát", "toàn", "loại", "khoảng", "quý", "QUÝ",
                   "quả", "hoạt", "Hoàng"):
            self.assertFalse(CU.search(tu), tu)

    def test_0_cho_kieu_cu_trong_kho(self):
        ra = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=GOC,
                            capture_output=True, text=True, encoding="utf-8")
        if ra.returncode != 0 or not ra.stdout:
            self.skipTest("không đọc được danh sách tệp git")
        con = []
        for duong in ra.stdout.splitlines():
            if duong.startswith(NGOAI_LE) or not (GOC / duong).is_file():
                continue
            try:
                chu = (GOC / duong).read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                continue
            for i, dong in enumerate(chu.splitlines(), 1):
                for m in CU.finditer(dong):
                    con.append(f"{duong}:{i}: {m.group(0)}")
        self.assertEqual(con, [], "\n".join(con[:40]))

    def test_chu_moi_o_cho_nguoi_dung_thay(self):
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        html = (GOC / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        self.assertIn("Hủy", html + js)                                            # nút dùng chung (đổi trong Y50)
        self.assertIn(("Nhắc khóa tỷ giá tháng"), [x[1] for x in khoitao.LICH_KHOITAO])


class KiemDoiChuDaLuu(unittest.TestCase):
    """QĐ301 = A, 05 điều kiện CDA KT-Y50."""

    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"}))
        khoitao.tao_het(self.dl)
        self.hom_nay = datetime.now(MUIGIO_VN).date().isoformat()
        self.hom_qua = (datetime.now(MUIGIO_VN).date() - timedelta(days=1)).isoformat()

    def sql(self, ten, cau, thamso=()):
        cn = ketnoi.mo(ten, self.dl)
        try:
            cn.execute("BEGIN IMMEDIATE")
            r = cn.execute(cau, thamso).fetchall()
            cn.execute("COMMIT")
            return r
        finally:
            cn.close()

    def may_cu(self, ten=doidau.LICH_CU, tu=None):
        """Giả máy chủ cài từ bản cũ: dòng lịch mang chữ kiểu cũ, bắt đầu từ hôm qua; 01 kết nối mất khóa ghi câu cũ."""
        self.sql("Bot", "UPDATE lich_baocao SET ten = ?, hieuluc_tu = ? WHERE ma = ?", (ten, tu or self.hom_qua, doidau.LICH_MA))
        self.sql("Ketnoi", "INSERT INTO ketnoi (id, ma, loi_cuoi) VALUES (?, 'k_cu', ?)", (maso.tao(), doidau.LOI_CU))
        self.sql("Ketnoi", "INSERT INTO ketnoi (id, ma, loi_cuoi) VALUES (?, 'k_khac', 'Lỗi khác do bạn ghi')", (maso.tao(),))

    def lich(self):
        return self.sql("Bot", "SELECT ten, hieuluc_tu, hieuluc_den, phienban, nguoi_khai FROM lich_baocao WHERE ma = ?"
                               " ORDER BY phienban", (doidau.LICH_MA,))

    def f04(self):
        return self.sql("Nhatky", "SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'dulieu' AND lenhcon = 'doi_dau_kieu_moi'")

    def test_chu_cu_viet_bang_ma_ky_tu_dung_chu_cu(self):
        self.assertEqual(doidau.LICH_CU, ve_kieu_cu(doidau.LICH_MOI))
        self.assertEqual(doidau.LOI_CU, ve_kieu_cu(doidau.LOI_MOI))
        self.assertNotEqual(doidau.LICH_CU, doidau.LICH_MOI)

    def test_doi_ca_02_cho_them_phien_ban_ghi_01_dong_f04(self):
        self.may_cu()
        self.assertEqual(doidau.doi_khi_khoidong(self.dl), {"lich": 1, "ketnoi": 1})
        ls = self.lich()
        self.assertEqual([(x[0], x[3], x[4]) for x in ls], [(doidau.LICH_CU, 1, "hethong"), (doidau.LICH_MOI, 2, "hethong")])
        self.assertEqual((ls[0][2], ls[1][1], ls[1][2]), (self.hom_nay, self.hom_nay, None))   # đk 2: phiên bản cũ đóng, giữ
        loi = dict(self.sql("Ketnoi", "SELECT ma, loi_cuoi FROM ketnoi WHERE ma IN ('k_cu', 'k_khac')"))
        self.assertEqual(loi, {"k_cu": doidau.LOI_MOI, "k_khac": "Lỗi khác do bạn ghi"})       # đk 5
        self.assertEqual(self.f04(), [("lich_baocao 01 dòng · ketnoi 01 dòng",)])              # đk 4

    def test_chay_lai_khong_doi_gi(self):
        self.may_cu()
        doidau.doi_khi_khoidong(self.dl)
        self.assertEqual(doidau.doi_khi_khoidong(self.dl), {"lich": 0, "ketnoi": 0})
        self.assertEqual(len(self.lich()), 2)
        self.assertEqual(len(self.f04()), 1)                                                   # đk 4: không thêm dòng

    def test_anh_da_doi_ten_lich_thi_khong_dung(self):
        self.may_cu(ten="Nhắc chốt tỷ giá")
        self.assertEqual(doidau.doi_khi_khoidong(self.dl)["lich"], 0)                           # đk 1
        self.assertEqual([x[0] for x in self.lich()], ["Nhắc chốt tỷ giá"])

    def test_phien_ban_bat_dau_hom_nay_thi_bo_qua_khong_loi(self):
        self.may_cu(tu=self.hom_nay)
        self.assertEqual(doidau.doi_khi_khoidong(self.dl), {"lich": 0, "ketnoi": 1})           # đk 3
        self.assertEqual([x[0] for x in self.lich()], [doidau.LICH_CU])

    def test_may_moi_cai_da_la_chu_moi(self):
        self.assertEqual([x[0] for x in self.lich()], [doidau.LICH_MOI])
        self.assertEqual(doidau.doi_khi_khoidong(self.dl), {"lich": 0, "ketnoi": 0})
        self.assertEqual(self.f04(), [])

    def test_khoidong_goi_ngoai_che_do_an_toan_boc_loi(self):
        ma = (GOC / "maychu/khoidong.py").read_text(encoding="utf-8")
        i = ma.index("if not antoan.CHE_DO[\"an_toan\"]:")
        j = ma.index("doidau.doi_khi_khoidong()")
        self.assertLess(i, j)
        self.assertIn("except Exception:  # noqa: BLE001\n            import logging\n            logging.getLogger(__name__)"
                      ".exception(\"đổi chữ dấu kiểu mới lúc khởi động lỗi\")", ma.replace("\r\n", "\n"))


class KiemThaydoi085(unittest.TestCase):
    def test_version_va_muc_085_nguyen_van_qd324(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 8, 5))                                    # bản sau giữ mục 0.8.5 nguyên văn
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.5")
        self.assertEqual(dong[i:i + 6], [
            "## 0.8.5",
            "Tóm tắt: Đặt dấu kiểu mới: xóa, khóa",
            "Nâng dữ liệu: không",
            "- Chữ trên màn hình đặt dấu kiểu mới: xóa, khóa, hóa, hủy, gồm cả nút Hủy, Két khóa và các mục cũ của Có gì mới."
            " Chỉ đổi cách đặt dấu, không đổi nội dung.",
            "- Tên lịch \"Nhắc khóa tỷ giá tháng\" và câu báo \"Khóa đã bị xóa ở Két khóa\" đã lưu trên máy chủ cũng đổi theo;"
            " tên lịch bạn đã tự đổi thì giữ nguyên.",
            "",
        ])                                                                        # QĐ324 (A + A1), đúng từng ký tự
        self.assertEqual(dong[i + 6], "## 0.8.4")


if __name__ == "__main__":
    unittest.main()
