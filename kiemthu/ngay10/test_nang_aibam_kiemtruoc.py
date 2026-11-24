"""Bài kiểm ngày 10 (lược đồ bản 3 phần 4/5; QĐ108, QĐ109): đổi giá trị "ai bấm" cũ khi nâng bản 2 → 3, giá trị lạ
thì dừng và trả nguyên trạng; bước kiểm trước chỉ đọc (`kiemtruoc_ban3.py`) báo đúng như lần nâng thật.
Dữ liệu thử chỉ dùng tên giả (QĐ126)."""
import ast
import contextlib
import inspect
import io
import json
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from kiemthu.ngay07.test_luocdo_ban3 import CoThuMuc, dung_ban2
from maychu.dulieu import aibam, ketnoi, khoitao, kiemtruoc_ban3 as kt, maso, phienban

TEN_GIA = "Chủ thử"
LA = "ai-do-la"


class NenBan2(CoThuMuc):
    def setUp(self):
        super().setUp()
        dung_ban2(self.thumuc)
        self.chu = maso.tao()
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, ten, vaitro, tao_luc, nguoi_khai) VALUES (?, 'chu', ?, 'chu',"
                 " '2026-11-21', 'lenh_vps')", (self.chu, TEN_GIA))

    def chay_kiem(self):
        ra = io.StringIO()
        with contextlib.redirect_stdout(ra):
            ma = kt.main([str(self.thumuc)])
        return ma, ra.getvalue()

    def ban(self):
        return {t: self.lay(t, "PRAGMA user_version")[0][0] for t in ketnoi.CAC_FILE}


class KiemDoiAiBam(NenBan2):
    def them_gia_tri_cu(self):
        self.ghi("Dulieu_Chinh", "INSERT INTO thongso (id, ten, nguoi_dat) VALUES (?, 'thu_01', 'chu')", (maso.tao(),))
        self.ghi("Dulieu_Chinh", "INSERT INTO thongso (id, ten, nguoi_dat) VALUES (?, 'thu_02', ?)", (maso.tao(), TEN_GIA))
        self.ghi("Baomat", "INSERT INTO kekhoa (id, dichvu, nguoi_nhap) VALUES (?, 'thu', 'anh')", (maso.tao(),))
        self.ghi("Viecnen", "INSERT INTO nguon_ai (id, ma, nguoi_khai) VALUES (?, 'goi_claude_01', 'anh')", (maso.tao(),))
        self.ghi("Ketnoi", "INSERT INTO ketnoi (id, ma, nguoi_khai) VALUES (?, 'drive', ?)", (maso.tao(), self.chu))
        self.ghi("Nhatky", "INSERT INTO nhatky_thaotac (id, luc, nguoi_id) VALUES (?, '2026-11-21', ?)", (maso.tao(), self.chu))

    def test_55_cot_ai_bam(self):
        ds = {t: aibam.cac_cot(t) for t in ketnoi.CAC_FILE}
        self.assertEqual(sum(map(len, ds.values())), 59)            # thiết kế mục 0.4: 58 cột + 0.8.0 H18 `nguoi_tao`
        self.assertIn(("chiase_lienket", "nguoi_tao"), ds["Bot"])
        self.assertIn(("nhatky_thaotac", "nguoi_id"), ds["Nhatky"])
        self.assertNotIn(("nguoidung", "nguoi_id"), ds["Baomat"])   # nguoi_id khác F04 trỏ A18, không phải "ai bấm"

    def test_nang_doi_gia_tri_cu_va_ca_55_cot_hop_le(self):
        self.them_gia_tri_cu()
        khoitao.tao_het(self.thumuc)
        self.assertEqual(set(self.ban().values()), {khoitao.PHIENBAN_LUOCDO})   # 0.8.0: nâng thẳng 2 → 4
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT nguoi_dat FROM thongso WHERE ten IN ('thu_01', 'thu_02')"),
                         [(self.chu,), (self.chu,)])
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_nhap FROM kekhoa"), [(self.chu,)])
        self.assertEqual(self.lay("Viecnen", "SELECT nguoi_khai FROM nguon_ai"), [(self.chu,)])
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_khai FROM nguoidung"), [("hethong",)])
        self.assertEqual(self.lay("Ketnoi", "SELECT nguoi_khai FROM ketnoi"), [(self.chu,)])
        for ten in ketnoi.CAC_FILE:                                   # quét đủ 55 cột: chỉ còn mã tài khoản, mã máy
            for bang, cot in aibam.cac_cot(ten):
                for (v,) in self.lay(ten, f"SELECT DISTINCT {cot} FROM {bang} WHERE {cot} IS NOT NULL"):
                    self.assertTrue(aibam.la_hop_le(v), f"{ten}.{bang}.{cot}")

    def test_gia_tri_la_thi_dung_tra_ca_07_file_khong_in_gia_tri(self):
        self.ghi("Viecnen", "INSERT INTO nguon_ai (id, ma, nguoi_khai) VALUES (?, 'goi_claude_09', ?)", (maso.tao(), LA))
        with self.assertRaises(RuntimeError) as loi:
            khoitao.tao_het(self.thumuc)
        self.assertIn("nguon_ai.nguoi_khai", str(loi.exception))
        self.assertNotIn(LA, str(loi.exception))
        self.assertEqual(set(self.ban().values()), {2})
        self.assertEqual(self.lay("Viecnen", "SELECT nguoi_khai FROM nguon_ai"), [(LA,)])
        self.assertEqual(self.lay("Baomat", "SELECT nguoi_khai FROM nguoidung"), [("lenh_vps",)])

    def test_chua_co_tai_khoan_chu_thi_chu_anh_la_gia_tri_la(self):
        self.ghi("Baomat", "DELETE FROM nguoidung")
        self.ghi("Baomat", "INSERT INTO kekhoa (id, dichvu, nguoi_nhap) VALUES (?, 'thu', 'anh')", (maso.tao(),))
        with self.assertRaises(RuntimeError):
            khoitao.tao_het(self.thumuc)
        self.assertEqual(set(self.ban().values()), {2})


class KiemTruoc(NenBan2):
    def test_sach_thi_dat_va_khong_ghi_gi(self):
        ma, ra = self.chay_kiem()
        self.assertEqual(ma, 0, ra)
        self.assertIn("KẾT QUẢ: ĐẠT", ra)
        self.assertEqual(set(self.ban().values()), {2})
        self.assertFalse((self.thumuc / "saoluu").exists())
        self.assertNotIn(TEN_GIA, ra)
        self.assertNotIn("chu", ra.replace("chủ", ""))                  # không in tên đăng nhập

    def test_da_o_ban_3(self):
        khoitao.tao_het(self.thumuc)
        ma, ra = self.chay_kiem()
        self.assertEqual((ma, "không cần nâng" in ra), (0, True))

    def kiem_cung_ket_qua(self, chu_dung):
        """Bước kiểm DỪNG đúng chỗ, và lần nâng thật cũng dừng, trả nguyên trạng."""
        ma, ra = self.chay_kiem()
        self.assertEqual(ma, 1, ra)
        self.assertIn(chu_dung, ra)
        self.assertNotIn(LA, ra)
        with self.assertRaises((RuntimeError, sqlite3.IntegrityError)):
            khoitao.tao_het(self.thumuc)
        self.assertEqual(set(self.ban().values()), {2})

    def test_tin_trung_b08(self):
        for _ in range(2):
            self.ghi("Ketnoi", "INSERT INTO hoptin (id, nguon, ma_sukien) VALUES (?, 'tiktok', 'sk_01')", (maso.tao(),))
        self.kiem_cung_ket_qua("hoptin: UNIQUE constraint failed: hoptin.nguon, hoptin.ma_sukien")

    def test_trung_b02_c01(self):
        for _ in range(2):
            self.ghi("Hotho", "INSERT INTO filegoc (id, mabam_sha256) VALUES (?, 'bam_01')", (maso.tao(),))
        self.kiem_cung_ket_qua("filegoc: UNIQUE constraint failed")

    def test_cot_bo_con_du_lieu(self):
        self.ghi("Dulieu_Chinh", "INSERT INTO nhanvien (id, ma, ma_trenkenh) VALUES (?, 'NV01', 'x')", (maso.tao(),))
        self.kiem_cung_ket_qua("nhanvien: cột ma_trenkenh sắp bỏ còn 01 dòng")

    def test_cot_bat_buoc_moi(self):
        self.ghi("Dulieu_Chinh", "INSERT INTO nhanvien (id, ma) VALUES (?, 'NV01')", (maso.tao(),))   # A15 bản 3: nguoi_id bắt buộc
        self.kiem_cung_ket_qua("nhanvien: NOT NULL constraint failed: nhanvien.nguoi_id")

    def test_ai_bam_la(self):
        self.ghi("Viecnen", "INSERT INTO nguon_ai (id, ma, nguoi_khai) VALUES (?, 'goi_claude_09', ?)", (maso.tao(), LA))
        self.kiem_cung_ket_qua("Viecnen.nguon_ai.nguoi_khai 01 dòng")

    def test_02_tai_khoan_chu(self):
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, vaitro, tao_luc) VALUES (?, 'chu2', 'chu', '2026-11-22')", (maso.tao(),))
        self.kiem_cung_ket_qua("Tài khoản chủ: 02 (cần đúng 01)")


class KiemHangSo(unittest.TestCase):
    def test_hang_so_sinh_bang_may_khop_ma(self):
        # 0.8.0: công cụ này là của lần nâng 2 → 3; so với lược đồ bản 3 lưu ở kiemthu/ban080/luocdo_ban3 (đúng d369e42)
        ban3 = Path(__file__).resolve().parents[1] / "ban080" / "luocdo_ban3"
        with mock.patch.object(khoitao, "THUMUC_LUOCDO", ban3), mock.patch.object(aibam, "_LUOCDO", ban3):
            self.so_hang_so()

    def so_hang_so(self):
        doi_ten = {}
        for (f, cu), moi in khoitao.DOI_TEN[3].items():
            doi_ten.setdefault(f, []).append([cu, moi])
        dung_lai = {}
        for f, ds in khoitao.NANGCAP[3].items():
            dung_lai[f] = list(dict.fromkeys(khoitao._ten_moi(f, b, 2) for b in ds))
        bang_moi = {f: list(ds) for f, ds in khoitao.BANG_MOI[3].items()}
        ddl = {f"{f}.{b}": khoitao._lay_ddl(f, b) for f in set(dung_lai) | set(bang_moi)
               for b in bang_moi.get(f, []) + dung_lai.get(f, [])}
        bpb = {}   # Y18: bảng có phiên bản theo file, đọc từ lược đồ bản 3 nạp vào bộ nhớ
        for f in ketnoi.CAC_FILE:
            cn = sqlite3.connect(":memory:")
            cn.executescript((khoitao.THUMUC_LUOCDO / f"{f}.sql").read_text(encoding="utf-8"))
            if phienban.cac_bang(cn):
                bpb[f] = phienban.cac_bang(cn)
            cn.close()
        self.assertEqual(sum(map(len, bpb.values())), 30)   # Y20c: F07 là bảng có phiên bản thứ 30
        dien3 = {}   # Y22a: điền cột mới bắt buộc theo mã cũ
        for (f, b), d in khoitao.DIEN_BAN3.items():
            dien3.setdefault(f, {})[b] = dict(d)
        bo_cot = {}
        for (f, b), ds in khoitao.BO_COT[3].items():
            bo_cot.setdefault(f, {})[b] = list(ds)
        mong = {"DOI_TEN": doi_ten, "BANG_MOI": bang_moi, "DUNG_LAI": dung_lai, "DDL": ddl, "BANG_PHIENBAN": bpb, "BO_COT": bo_cot, "DIEN_BAN3": dien3,
                "AIBAM": {f: [list(x) for x in aibam.cac_cot(f)] for f in ketnoi.CAC_FILE},
                "DOI_CU_MAY": aibam.DOI_CU_MAY, "MA_MAY": list(aibam.MA_MAY), "ULID": aibam._ULID.pattern}
        self.assertEqual(json.loads(json.dumps(kt.SINH)), json.loads(json.dumps(mong)),
                         "hằng số kiemtruoc_ban3.py lệch mã: chạy lại bước sinh")
        self.assertEqual(set(kt.DIEN["Baomat"]["nguoidung"]), {"nguoi_id"})   # cùng cột điền với khoitao._ban3_truoc
        self.assertIn('{"nguoidung": {"nguoi_id":', inspect.getsource(khoitao._ban3_truoc))

    def test_chi_dung_thu_vien_chuan(self):
        cay = ast.parse(Path(kt.__file__).read_text(encoding="utf-8"))
        dung = {a.name.split(".")[0] for n in ast.walk(cay) if isinstance(n, ast.Import) for a in n.names}
        dung |= {n.module.split(".")[0] for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)}
        self.assertLessEqual(dung, {"re", "shutil", "sqlite3", "sys", "pathlib"})


if __name__ == "__main__":
    unittest.main()
