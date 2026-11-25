"""Bài kiểm Y52 (bản 0.8.6; QĐ321–QĐ332; bản vẽ Z27 · U40): thu gọn 05 nhóm thanh trái, chỉ khổ máy tính.

Chạy khối `// <NHOM>` của app.js bằng node (hàm thuần `tinhNhom`, `batNhom`), kiểm chuỗi CSS và chỗ gắn. Đã xem thử thật
trên trình duyệt (máy chủ xem thử): ghi ở nhật ký CTO.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parents[2]
GD = GOC_KHO / "maychu" / "web" / "giaodien"


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemThuGonNhom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (GD / "app.js").read_text(encoding="utf-8")
        cls.html = (GD / "index.html").read_text(encoding="utf-8")
        cls.ma = cls.app[cls.app.index("// <NHOM>"):cls.app.index("// </NHOM>")]

    def chay(self, cau):
        dau = "const esc = x => String(x), $ = () => null, ICON = {}, S = {trang: '03'};\nlet goiVe = 0;\n"
        ra = subprocess.run(["node", "-e", dau + self.ma + "\nfunction veNhom() { goiVe++; }\n" + "console.log(JSON.stringify(" + cau + "));"],
                            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        return json.loads(ra.stdout)

    DS = ("[{ten: 'QUẢN TRỊ TMĐT', so: 5, bao: [{ten: 'Chờ duyệt', so: '12', do: false}]},"
          " {ten: 'TRÒ CHUYỆN', so: 1, bao: []},"
          " {ten: 'NĂNG LỰC', so: 2, bao: [{ten: 'Giám sát AI', so: '01', do: true}]},"
          " {ten: 'KẾT NỐI', so: 3, bao: []}, {ten: 'HỆ THỐNG', so: 2, bao: []}]")

    def test_l1_mot_nhom_mo_bam_lai_thi_gap(self):
        ra = self.chay("(() => { const kq = []; NHOM.mo = new Set(['QUẢN TRỊ TMĐT']);"
                       " batNhom('NĂNG LỰC'); kq.push([...NHOM.mo]); batNhom('NĂNG LỰC'); kq.push([...NHOM.mo]);"
                       " batNhom('KẾT NỐI'); kq.push([...NHOM.mo]); kq.push(goiVe); return kq; })()")
        self.assertEqual(ra, [["NĂNG LỰC"], [], ["KẾT NỐI"], 3])                 # QĐ321 L1 A

    def test_l5_nhom_01_muc_dung_rieng(self):
        kq = self.chay("tinhNhom(" + self.DS + ", new Set(), null)")
        self.assertEqual([(x["ten"], x["rieng"], x["mo"]) for x in kq][1], ("TRÒ CHUYỆN", True, True))   # QĐ322 L5 B: luôn hiện
        self.assertEqual([x["rieng"] for x in kq], [False, True, False, False, False])

    def test_l3_nhom_gap_khong_che_so_giam_sat_ai(self):
        """Điểm an toàn vận hành (CDA KT-TG): nhóm NĂNG LỰC gập vẫn hiện số Giám sát AI ở tiêu đề, giữ màu đỏ."""
        kq = self.chay("tinhNhom(" + self.DS + ", new Set(['QUẢN TRỊ TMĐT']), 'QUẢN TRỊ TMĐT')")
        nl = kq[2]
        self.assertEqual((nl["mo"], nl["bao"]), (False, [{"ten": "Giám sát AI", "so": "01", "do": True}]))   # QĐ323 L3 A
        self.assertEqual(kq[0]["bao"], [])                                       # nhóm mở: số nằm ở mục, không lặp ở tiêu đề
        kq = self.chay("tinhNhom(" + self.DS + ", new Set(['NĂNG LỰC']), 'NĂNG LỰC')")
        self.assertEqual(kq[0]["bao"], [{"ten": "Chờ duyệt", "so": "12", "do": False}])
        self.assertIn("'<span class=\"bao' + (x.do ? ' do' : '') + '\" title=\"'\n      + esc(x.ten + ': ' + x.so)", self.app.replace("\r\n", "\n"))
        self.assertIn("map(x => ({ten: x.closest('.muc').title, so: x.textContent.trim(), do: x.classList.contains('do')}))", self.app)
        self.assertIn("    veNhom();   // Y52 L3: số báo ở tiêu đề nhóm gập theo số mới", self.app)   # cập nhật theo demSo

    def test_l2_tieu_de_xanh_khi_tu_gap_nhom_cua_trang(self):
        kq = self.chay("tinhNhom(" + self.DS + ", new Set(), 'NĂNG LỰC')")
        self.assertEqual([x["coTrang"] for x in kq], [False, False, True, False, False])   # QĐ325 L2 A
        kq = self.chay("tinhNhom(" + self.DS + ", new Set(['NĂNG LỰC']), 'NĂNG LỰC')")
        self.assertEqual([x["coTrang"] for x in kq], [False] * 5)                 # nhóm đang mở: không tô
        self.assertIn("if (S.trang !== NHOM.trangCu) { NHOM.trangCu = S.trang; if (cur) NHOM.mo = new Set([cur.ten]); }", self.app)

    def test_khong_luu_va_gan_dung_cho(self):
        self.assertNotIn("localStorage", self.ma)                                 # QĐ327: không lưu
        self.assertIn("  veNhom();   // Y52: thu gọn nhóm thanh trái\n}", self.app.replace("\r\n", "\n"))
        self.assertIn("  else if (d.nhomNut !== undefined) { batNhom(d.nhomNut); return; }", self.app)
        self.assertIn("ICON[mo ? 'chevron-down' : 'chevron-right']", self.ma)     # QĐ331
        self.assertNotIn("Mở nhóm", self.app + self.html)                         # QĐ330: không câu rê chuột
        self.assertNotIn("Thu gọn nhóm", self.app + self.html)

    def test_css_chi_may_tinh_thu_ca_thanh_giu_nhu_nay(self):
        for x in ("#app:not(.mb) .nhom-ds.gap>.muc{display:none}", "#app:not(.mb) .nhom-nut.co-trang{color:var(--xanh)}",
                  ".thu .nhom-nut{display:none!important}", ".thu .nhom-ds.gap>.muc{display:flex!important}",
                  "#app:not(.mb) .nhom-ds.rieng{margin-top:8px}"):
            self.assertIn(x, self.html)                                           # QĐ328 L4 A, QĐ329 điện thoại không áp dụng
        self.assertNotIn("menu-cuon", self.html + self.app)                       # QĐ326 L6 không làm ở bản này


class KiemThaydoi086(unittest.TestCase):
    def test_version_va_muc_086_nguyen_van_qd337(self):
        self.assertEqual((GOC_KHO / "VERSION").read_text(encoding="utf-8").strip(), "0.8.6")
        dong = (GOC_KHO / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.6")
        self.assertEqual(dong[i:i + 6], [
            '## 0.8.6',
            'Tóm tắt: Thu gọn nhóm menu',
            'Nâng dữ liệu: không',
            '- Menu bên trái thu gọn theo nhóm: mỗi lúc mở 01 nhóm, bấm tên nhóm để mở hoặc gập; mở trang nào thì nhóm của trang đó tự mở. "Trò chuyện AI" đứng riêng, luôn hiện.',
            '- Nhóm đang gập vẫn hiện số Chờ duyệt và số Giám sát AI ngay ở tên nhóm, giữ màu như cũ. Nút "Thu gọn menu" và màn hình điện thoại giữ như cũ.',
            ''])                                                                        # QĐ337 (A), đúng từng ký tự
        self.assertEqual(dong[i + 6], "## 0.8.5")


if __name__ == "__main__":
    unittest.main()
