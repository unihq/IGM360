"""Bài kiểm 0.10.0 – lược đồ bản 5 (QĐ572, QĐ584, QĐ632; phiếu 16 mục 9.35–9.40; thiết kế mục 1.4).

Tạo mới đủ 125 bảng · nâng 4 → 5 ra đúng như tạo mới (so bằng PRAGMA) · nâng giữ dữ liệu, D01 / M02 nhận kỳ `quy`,
`nam` · T01 `bn_suviec` chặn sửa 02 tầng (QĐ632, QA L14, 03 sửa của CDA) · quay về 5 → 4 giữ 05 sổ, G04 mất đúng
02 cột mới, đếm dòng không hụt (QA Đ01, QĐ237). Dữ liệu bản 4 dựng từ `luocdo_ban4/` (đúng lược đồ 0.9.4 `fdae5bd`).
Tên giả, 0 gọi CLI thật.
"""
import ast
import os
import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso, saoluu, suviec
from maychu.hethong import antoan

BAN4 = Path(__file__).resolve().parent / "luocdo_ban4"
GOC = Path(__file__).resolve().parents[2]
COT_T01 = ["id", "luc", "loai", "nguon_loai", "bang_nguon", "dong_nguon_id", "khoa_chongtrung", "bonao", "doituong",
           "nguoi_id", "co_dlcn", "shop_id", "kenh_id", "nhatky_ai_id", "lydo_ma", "lydo_chu", "so_lan_sua",
           "trithuc_ma", "danhgia", "moc_json", "trangthai_xuly", "xuly_luc"]   # thiết kế mục 1.4, QĐ632: 22 cột
# phiếu 16 mục 9.39 (a): 09 cột thêm / 05 bảng
COT_THEM = {("Bot", "hoithoai"): ["bonao"], ("Bot", "nhom_trochuyen"): ["bonao"],
            ("Bot", "tailieu_gan"): ["boc_trangthai", "boc_ghichu", "boc_luc", "thay_cho_id"],
            ("Dulieu_Chinh", "kehoach_nguong"): ["ky_loai"], ("Nhatky", "nhatky_ai"): ["mohinh_thucchay", "lydo"]}


def dung_ban4(dl: Path) -> None:
    """07 tệp đúng lược đồ bản 4 (0.9.4)."""
    dl.mkdir(parents=True, exist_ok=True)
    for ten in ketnoi.CAC_FILE:
        cn = ketnoi.mo(ten, dl)
        try:
            cn.executescript((BAN4 / f"{ten}.sql").read_text(encoding="utf-8"))
            cn.execute("PRAGMA user_version=4")
            khoitao._dong_khoitao(cn, ten)
        finally:
            cn.close()


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)   # đăng ký trước → dọn sau cùng (Windows: đóng tệp trước khi xóa)
        self.g = Path(self.tam.name)
        self.dl = self.g / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            "IGM360_CLAUDE_CLI": str(self.g / "khong_co_cli_claude"),
                                            "IGM360_CODEX_CLI": str(self.g / "khong_co_cli_codex")})
        bien.start()
        self.addCleanup(bien.stop)
        antoan.CHE_DO.update(an_toan=False, den=None, luc=None, lydo=None)
        self.addCleanup(antoan.CHE_DO.update, an_toan=False, den=None, luc=None, lydo=None)

    def lay(self, ten, sql, ts=(), dl=None):
        cn = ketnoi.mo(ten, dl or self.dl)
        try:
            return cn.execute(sql, ts).fetchall()
        finally:
            cn.close()

    def cot(self, ten, bang, dl=None):
        return [r[1] for r in self.lay(ten, f"PRAGMA table_info({bang})", dl=dl)]

    def ban(self, dl=None):
        return {t: self.lay(t, "PRAGMA user_version", dl=dl)[0][0] for t in ketnoi.CAC_FILE}


class KiemTaoMoi(Nen):
    def test_tao_moi_125_bang_t01_22_cot(self):
        kq = khoitao.tao_het(self.dl)
        self.assertEqual(khoitao.PHIENBAN_LUOCDO, 5)
        self.assertEqual(sum(kq.values()), 125)                                        # QĐ572 I-1: 124 → 125
        self.assertEqual(kq, ketnoi.SO_BANG)
        self.assertEqual(self.cot("Viecnen", "bn_suviec"), COT_T01)
        chimuc = {r[0] for r in self.lay("Viecnen", "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'bn_suviec'")}
        self.assertTrue({"bn_suviec_bonao_luc", "bn_suviec_cho", "bn_suviec_trithuc"} <= chimuc)
        trig = {r[0] for r in self.lay("Viecnen", "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'bn_suviec'")}
        self.assertEqual(trig, {"sv__suthat", "sv__xuly"})
        for (ten, bang), ds in COT_THEM.items():
            self.assertEqual(self.cot(ten, bang)[-len(ds):], ds, f"{ten}.{bang}")     # thêm cuối bảng

    def test_chay_lai_khong_doi(self):
        khoitao.tao_het(self.dl)
        truoc = self.lay("Viecnen", "SELECT type, name, sql FROM sqlite_master ORDER BY name")
        khoitao.tao_het(self.dl)
        self.assertEqual(self.lay("Viecnen", "SELECT type, name, sql FROM sqlite_master ORDER BY name"), truoc)


class KiemNangBan5(Nen):
    def _master(self, ten, dl):
        q = "SELECT type, name, tbl_name FROM sqlite_master ORDER BY type, name"
        bang = [r[1] for r in self.lay(ten, q, dl=dl) if r[0] == "table"]
        return self.lay(ten, q, dl=dl), {b: self.lay(ten, f"PRAGMA table_xinfo('{b}')", dl=dl) for b in bang}

    def test_nang_ra_dung_nhu_tao_moi(self):
        dung_ban4(self.dl)
        self.assertEqual(set(self.ban().values()), {4})
        khoitao.tao_het(self.dl)
        moi = self.g / "moi"
        khoitao.tao_het(moi)
        for ten in ketnoi.CAC_FILE:
            self.assertEqual(self._master(ten, self.dl), self._master(ten, moi), ten)
        self.assertEqual(set(self.ban().values()), {5})

    def test_nang_giu_du_lieu_va_nhan_ky_quy_nam(self):
        dung_ban4(self.dl)
        cn = ketnoi.mo("Dulieu_Chinh", self.dl)
        try:
            d1, m2, c17 = maso.tao(), maso.tao(), maso.tao()
            cn.execute("INSERT INTO chiso (id, ma, ten, ky_tinh) VALUES (?, 'doanhthu', 'Doanh thu', 'thang')", (d1,))
            cn.execute("INSERT INTO quytac_kiemdu (id, ma, ten, ky_loai) VALUES (?, 'du_don', 'Đủ đơn', 'ngay')", (m2,))
            cn.execute("INSERT INTO kehoach_nguong (id, ma_chiso, ky, kehoach) VALUES (?, ?, '2026-11', 100)", (c17, d1))
            with self.assertRaises(sqlite3.IntegrityError):                            # bản 4: chưa nhận `quy`
                cn.execute("INSERT INTO chiso (id, ma, ky_tinh) VALUES (?, 'x', 'quy')", (maso.tao(),))
        finally:
            cn.close()
        g4 = maso.tao()
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            cn.execute("INSERT INTO nhatky_ai (id, luc, luong_vao, ketqua) VALUES (?, '2026-11-27T10:00:00+07:00', 123, 'xong')", (g4,))
        finally:
            cn.close()
        khoitao.tao_het(self.dl)
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT ten, ky_tinh FROM chiso WHERE id = ?", (d1,)), [("Doanh thu", "thang")])
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT ky_loai FROM quytac_kiemdu WHERE id = ?", (m2,)), [("ngay",)])
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT kehoach, ky_loai FROM kehoach_nguong WHERE id = ?", (c17,)), [(100, None)])
        self.assertEqual(self.lay("Nhatky", "SELECT luong_vao, mohinh_thucchay, lydo FROM nhatky_ai WHERE id = ?", (g4,)),
                         [(123, None, None)])
        cn = ketnoi.mo("Dulieu_Chinh", self.dl)
        try:
            for ky in ("quy", "nam"):                                                  # QĐ572 II-2, II-3
                cn.execute("INSERT INTO chiso (id, ma, ky_tinh) VALUES (?, ?, ?)", (maso.tao(), f"c_{ky}", ky))
                cn.execute("INSERT INTO quytac_kiemdu (id, ma, ky_loai) VALUES (?, ?, ?)", (maso.tao(), f"q_{ky}", ky))
                cn.execute("INSERT INTO kehoach_nguong (id, ky_loai) VALUES (?, ?)", (maso.tao(), ky))
            with self.assertRaises(sqlite3.IntegrityError):                            # C17 CHECK ở cột thêm (II-1)
                cn.execute("INSERT INTO kehoach_nguong (id, ky_loai) VALUES (?, 'mua')", (maso.tao(),))
        finally:
            cn.close()
        self.assertIn("Dulieu_Chinh.chiso", antoan.doc(self.dl)["nang_luocdo"]["so_dong"])   # K4: đếm D01, M02

    def test_nang_loi_tra_nguyen_trang(self):
        dung_ban4(self.dl)
        with mock.patch.object(khoitao, "_them_cot", side_effect=sqlite3.OperationalError("hỏng giả")):
            with self.assertRaises(sqlite3.OperationalError):
                khoitao.tao_het(self.dl)
        self.assertEqual(set(self.ban().values()), {4})
        self.assertNotIn("bn_suviec", {r[0] for r in self.lay("Viecnen", "SELECT name FROM sqlite_master WHERE type = 'table'")})


class KiemT01ChanSua(Nen):
    """QĐ632, QA L14: 02 tầng; 03 sửa của CDA (NOT NULL, `IS NOT 'moi'`, cấm OR REPLACE)."""

    def setUp(self):
        super().setUp()
        khoitao.tao_het(self.dl)
        self.cn = ketnoi.mo("Viecnen", self.dl)
        self.addCleanup(self.cn.close)
        self.cn.execute("INSERT INTO bn_suviec (id, luc, loai, khoa_chongtrung) VALUES ('a', '2026-11-27T10:00:00+07:00', 'anh_sua', 'k1')")

    def chan(self, sql, ts=()):
        with self.assertRaises(sqlite3.DatabaseError, msg=sql):
            self.cn.execute(sql, ts)

    def tt(self, i="a"):
        return self.cn.execute("SELECT trangthai_xuly, xuly_luc FROM bn_suviec WHERE id = ?", (i,)).fetchone()

    def test_mac_dinh_moi_va_khong_nhan_trong(self):
        self.assertEqual(self.tt(), ("moi", None))
        self.chan("INSERT INTO bn_suviec (id, luc, loai, trangthai_xuly) VALUES ('n', 't', 'x', NULL)")
        self.chan("UPDATE bn_suviec SET trangthai_xuly = NULL, xuly_luc = 't2' WHERE id = 'a'")

    def test_mot_chieu_trang_thai_cuoi(self):
        self.chan("UPDATE bn_suviec SET trangthai_xuly = 'dahoc' WHERE id = 'a'")       # thiếu xuly_luc
        self.cn.execute("UPDATE bn_suviec SET trangthai_xuly = 'dahoc', xuly_luc = 't2' WHERE id = 'a'")
        self.assertEqual(self.tt(), ("dahoc", "t2"))
        self.chan("UPDATE bn_suviec SET trangthai_xuly = 'boqua', xuly_luc = 't3' WHERE id = 'a'")   # dahoc ↔ boqua
        self.chan("UPDATE bn_suviec SET trangthai_xuly = 'moi', xuly_luc = 't3' WHERE id = 'a'")
        self.chan("UPDATE bn_suviec SET xuly_luc = 't9' WHERE id = 'a'")
        self.cn.execute("INSERT INTO bn_suviec (id, luc, loai) VALUES ('b', 't', 'anh_duyet')")
        self.cn.execute("UPDATE bn_suviec SET trangthai_xuly = 'boqua', xuly_luc = 't4' WHERE id = 'b'")
        self.assertEqual(self.tt("b"), ("boqua", "t4"))

    def test_cot_su_that_khong_sua(self):
        for c in suviec.COT_SUTHAT:
            self.chan(f"UPDATE bn_suviec SET {c} = {c} WHERE id = 'a'")
        self.assertEqual(len(suviec.COT_SUTHAT) + 2, len(COT_T01))

    def test_on_conflict_giu_dong_cu_va_xoa_khong_chan(self):
        self.cn.execute("UPDATE bn_suviec SET trangthai_xuly = 'dahoc', xuly_luc = 't2' WHERE id = 'a'")
        self.cn.execute("INSERT INTO bn_suviec (id, luc, loai, khoa_chongtrung) VALUES ('a2', 't9', 'anh_sua', 'k1')"
                        " ON CONFLICT(khoa_chongtrung) DO NOTHING")
        self.assertEqual(self.cn.execute("SELECT id, trangthai_xuly FROM bn_suviec WHERE khoa_chongtrung = 'k1'").fetchall(),
                         [("a", "dahoc")])
        self.cn.execute("DELETE FROM bn_suviec WHERE id = 'a'")                        # chưa có QĐ xóa dòng: không chặn
        self.assertEqual(self.cn.execute("SELECT count(*) FROM bn_suviec").fetchone()[0], 0)

    def test_tao_trigger_chay_lai_va_bo_qua_tep_chua_co_bang(self):
        suviec.tao_trigger(self.cn)
        cn = sqlite3.connect(":memory:")
        try:
            suviec.tao_trigger(cn)                                                     # chưa có T01: không lỗi
            self.assertEqual(cn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'trigger'").fetchone()[0], 0)
        finally:
            cn.close()

    def test_ma_khong_co_or_replace(self):
        # CDA L14 sửa 3: `INSERT OR REPLACE` / `REPLACE INTO` thay dòng = xóa + thêm, đi vòng trigger sửa → cấm ở maychu/
        # Dò chuỗi trong mã (câu SQL), bỏ chuỗi chú thích đầu tệp / hàm / lớp.
        mau = re.compile(r"\bOR\s+REPLACE\b|\bREPLACE\s+INTO\b", re.I)
        gap = []
        for p in (GOC / "maychu").rglob("*.py"):
            cay = ast.parse(p.read_text(encoding="utf-8"))
            chu_thich = {id(n.body[0].value) for n in ast.walk(cay)
                         if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body
                         and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            for n in ast.walk(cay):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in chu_thich and mau.search(n.value):
                    gap.append(f"{p.relative_to(GOC)}:{n.lineno}")
        self.assertEqual(gap, [])


class KiemBonao(Nen):
    """Đ-a (CDA 9.38), L03 (CPO áp A): 0.10.0 tạo `bonao/chung/` + 01 kho git; kho thư mục cha để 0.11.0."""

    def test_tao_het_tao_kho_git_chung(self):
        from maychu.dulieu import bonao
        khoitao.tao_het(self.dl)
        chung = self.dl / "bonao" / "chung"
        self.assertTrue(bonao.la_kho_git(chung))
        self.assertFalse((self.dl / "bonao" / ".git").exists())                        # L03: chưa có kho thư mục cha
        self.assertEqual(bonao.khoi_tao(self.dl), {"chung": "co_san"})                 # chạy lại không sao
        self.assertTrue(bonao.hop_le(self.dl))

    def test_thieu_git_bao_khong_chan(self):
        from maychu.dulieu import bonao
        with mock.patch.object(bonao.shutil, "which", return_value=None):
            self.assertEqual(sum(khoitao.tao_het(self.dl).values()), 125)            # dữ liệu vẫn tạo đủ
            self.assertEqual(bonao.khoi_tao(self.dl), {"chung": "thieu_git"})
            self.assertFalse(bonao.hop_le(self.dl))


class KiemQuayVe5ve4(Nen):
    """QA Đ01, QĐ237: quay về sau nâng 4 → 5 trả bản chụp, giữ 05 sổ + M01 ghi sau giờ chụp; G04 ghi nối theo cột chung
    (`chay.py` 196–197) – mất đúng 02 cột mới, giữ cột chung; đếm dòng không hụt (`INSERT OR IGNORE` bỏ im lặng dòng
    vi phạm CHECK); T01 và cột mới H16 mất đúng như phiếu 16 mục 9.35."""

    def dung(self):
        from maychu import chay
        dung_ban4(self.dl)
        khoitao.tao_het(self.dl)                    # chụp truoc_nangcap_v05 (dữ liệu bản 4) rồi nâng lên bản 5
        self.LUC = (datetime.now(saoluu.MUIGIO_VN) - timedelta(seconds=2)).isoformat(timespec="seconds")
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.10.0", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text("0.9.4", encoding="utf-8")
        self.id = {k: maso.tao() for k in ("f04", "g04", "h05", "n02", "n01", "t01", "h16")}
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            cn.execute("INSERT INTO nhatky_thaotac (id, luc, congcu, lenhcon, thamso_tomtat, ketqua) VALUES (?, ?, 'capnhat',"
                       " 'khoidong', '0.10.0', 'dat')", (self.id["f04"], self.LUC))
            cn.execute("INSERT INTO nhatky_ai (id, luc, luong_vao, ketqua, mohinh_thucchay, lydo) VALUES (?, ?, 321, 'xong',"
                       " 'mohinh-gia', 'chuyen nguon gia')", (self.id["g04"], self.LUC))
            for bang, k in (("nhatky_noihayim", "h05"), ("theodoi_maychu", "n02")):
                cn.execute(f"INSERT INTO {bang} (id, luc) VALUES (?, ?)", (self.id[k], self.LUC))
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua) VALUES (?, 'hangngay', 'Bot', ?,"
                       " 'xong_tren_may')", (self.id["n01"], self.LUC))
        finally:
            cn.close()
        cn = ketnoi.mo("Viecnen", self.dl)
        try:
            cn.execute("INSERT INTO bn_suviec (id, luc, loai) VALUES (?, ?, 'anh_sua')", (self.id["t01"], self.LUC))
        finally:
            cn.close()
        cn = ketnoi.mo("Bot", self.dl)
        try:
            cn.execute("INSERT INTO tailieu_gan (id, loai, boc_trangthai) VALUES (?, 'tep', 'xong')", (self.id["h16"],))
        finally:
            cn.close()
        self.dem_truoc = {b: self.lay("Nhatky", f"SELECT count(*) FROM {b}")[0][0] for b in chay.BANG_GIU}
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.10.0", "ban_truoc": "0.9.4", "nguoi": None,
                                            "tra_du_lieu": {"thumuc": "truoc_nangcap_v05", "tep": list(ketnoi.CAC_FILE)}})
        return chay, g

    def co(self, ten, bang, k):
        return bool(self.lay(ten, f"SELECT 1 FROM {bang} WHERE id = ?", (self.id[k],)))

    def test_quay_ve_giu_05_so_g04_mat_dung_02_cot(self):
        chay, g = self.dung()
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")
        self.assertEqual(set(self.ban().values()), {4})                                # dữ liệu đã trả về bản 4
        for bang, k in (("nhatky_thaotac", "f04"), ("nhatky_ai", "g04"), ("nhatky_noihayim", "h05"),
                        ("theodoi_maychu", "n02"), ("saoluu", "n01")):
            self.assertTrue(self.co("Nhatky", bang, k), bang)
        cot_g04 = self.cot("Nhatky", "nhatky_ai")
        self.assertNotIn("mohinh_thucchay", cot_g04)
        self.assertNotIn("lydo", cot_g04)
        self.assertEqual(self.lay("Nhatky", "SELECT luong_vao, ketqua FROM nhatky_ai WHERE id = ?", (self.id["g04"],)),
                         [(321, "xong")])                                              # cột chung giữ nguyên giá trị
        for bang, so in self.dem_truoc.items():                                        # không bỏ im lặng dòng nào
            self.assertGreaterEqual(self.lay("Nhatky", f"SELECT count(*) FROM {bang}")[0][0], so, bang)
        self.assertNotIn("bn_suviec", {r[0] for r in self.lay("Viecnen", "SELECT name FROM sqlite_master WHERE type = 'table'")})
        self.assertFalse(self.co("Bot", "tailieu_gan", "h16"))                         # H16 thêm sau giờ chụp: mất (9.35)
        self.assertFalse((self.dl / chay.TEP_GIU).exists())

    def test_ghi_noi_02_lan_khong_ghi_doi(self):
        import shutil
        chay, g = self.dung()
        chay._chep_giu(self.dl, self.dl / "saoluu" / "truoc_nangcap_v05")
        luu = self.g / "giu_luu.sqlite3"
        shutil.copy(self.dl / chay.TEP_GIU, luu)
        chay.chon(self.dl, g)
        dem = lambda: [self.lay("Nhatky", f"SELECT count(*) FROM {b}")[0][0] for b in chay.BANG_GIU]   # noqa: E731
        truoc = dem()
        shutil.copy(luu, self.dl / chay.TEP_GIU)
        chay._ghi_noi_giu(self.dl)
        self.assertEqual(dem(), truoc)


if __name__ == "__main__":
    unittest.main()
