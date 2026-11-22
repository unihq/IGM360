"""Bài kiểm Y18 (QĐ142, QĐ143; PTD-03 mục 10; thiết kế mục 0.7 Q1-Q8): mã bền ở 29 bảng có phiên bản, A15 tách
phiên bản theo người, C16 không trùng theo (người, tháng), đổi phiên bản giữa kỳ không mất nối, nâng bản 2 → 3 dừng
khi còn mã trống. Dữ liệu thử chỉ dùng mã, tên giả (QĐ126)."""
import contextlib
import io
import json
import re
import sqlite3
from pathlib import Path

from kiemthu.ngay07.test_luocdo_ban3 import CoThuMuc, dung_ban2
from maychu.dulieu import ketnoi, khoitao, kiemtruoc_ban3 as kt, luong, maso, phienban, songuoi

BANG_29 = {
    "Dulieu_Chinh": ['chiso', 'congty', 'hoso_phaply', 'kenh', 'kho', 'khoanchi', 'khuvuc', 'loai_module', 'lydo_shopchet',
                     'nhacungcap', 'nhanvien', 'quytac_kiemdu', 'shop', 'sku', 'taikhoan'],
    "Hotho": ['khuon'],
    "Ketnoi": ['ketnoi', 'theodoi_trang', 'webhook'],
    "Viecnen": ['congsu', 'kynang', 'nguon_ai', 'quytrinh', 'team'],
    "Bot": ['chatbot', 'chude_nhom', 'kenh_nhan', 'lich_baocao'],
    "Baomat": ['nguoidung'],
}
GOC = Path(__file__).resolve().parents[2]


class NenMoi(CoThuMuc):
    def setUp(self):
        super().setUp()
        khoitao.tao_het(self.thumuc)
        self.cn = self.mo("Dulieu_Chinh")

    def tearDown(self):
        self.cn.close()
        super().tearDown()


class KiemLuocDo(NenMoi):
    def test_29_bang_ma_bat_buoc_va_58_trigger(self):
        tong = 0
        for ten in ketnoi.CAC_FILE:
            cn = self.mo(ten)
            try:
                ds = phienban.cac_bang(cn)
                self.assertEqual(ds, BANG_29.get(ten, []), ten)
                for b in ds:
                    notnull = {r[1]: r[3] for r in cn.execute(f"PRAGMA table_info({b})")}["ma"]
                    self.assertEqual(notnull, 1, b)
                so = cn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'ma\\_\\_%' ESCAPE '\\'").fetchone()[0]
                self.assertEqual(so, 2 * len(ds), ten)
                tong += len(ds)
                if ten == "Viecnen":   # G15 là bảng sự kiện: có `phienban`, không có `ma`, không thuộc 29 bảng
                    self.assertNotIn("quytrinh_lanchay", ds)
            finally:
                cn.close()
        self.assertEqual(tong, 29)

    def test_a15_bo_khong_trung_nguoi_f01_giu(self):
        sql_nv = self.cn.execute("SELECT sql FROM sqlite_master WHERE name = 'nhanvien'").fetchone()[0]
        self.assertIn("nguoi_id TEXT NOT NULL REFERENCES nguoi(id)", sql_nv)
        self.assertNotIn("UNIQUE", sql_nv)
        bm = self.mo("Baomat")
        try:
            self.assertIn("nguoi_id TEXT NOT NULL UNIQUE", bm.execute("SELECT sql FROM sqlite_master WHERE name = 'nguoidung'").fetchone()[0])
        finally:
            bm.close()

    def test_luoi_an_toan_ma_trong_va_sua_ma(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.cn.execute("INSERT INTO shop (id) VALUES ('s1')")                      # NOT NULL
        for ma in ("", "   "):
            with self.subTest(ma=ma), self.assertRaises(sqlite3.IntegrityError):
                self.cn.execute("INSERT INTO shop (id, ma) VALUES ('s1', ?)", (ma,))   # trigger chặn mã trống
        self.cn.execute("INSERT INTO shop (id, ma, hieuluc_tu) VALUES ('s1', 'SHOP01', '2026-03-01')")
        with self.assertRaises(sqlite3.IntegrityError) as loi:
            self.cn.execute("UPDATE shop SET ma = 'SHOP09' WHERE id = 's1'")
        self.assertIn("không sửa mã", str(loi.exception))
        self.cn.execute("UPDATE shop SET ma = 'SHOP01', ten = 'Shop thử' WHERE id = 's1'")  # cùng mã: không chặn
        bm = self.mo("Baomat")
        try:
            bm.execute("INSERT INTO nguoidung (id, ma, nguoi_id) VALUES ('u1', 'chu_thu', 'n1')")
            with self.assertRaises(sqlite3.IntegrityError):
                bm.execute("UPDATE nguoidung SET ma = 'chu_khac' WHERE id = 'u1'")
        finally:
            bm.close()


class KiemLopGhi(NenMoi):
    def test_thieu_ma_sai_ngay_cot_la(self):
        for dong in ({"hieuluc_tu": "2026-03-01"}, {"ma": "  ", "hieuluc_tu": "2026-03-01"}, {"ma": None, "hieuluc_tu": "2026-03-01"}):
            with self.subTest(dong=dong), self.assertRaises(phienban.LoiPhienBan) as loi:
                phienban.them(self.cn, "shop", dong)
            self.assertIn("thiếu mã", str(loi.exception))
        for dong in ({"ma": "SHOP01"}, {"ma": "SHOP01", "hieuluc_tu": "01/03/2026"},
                     {"ma": "SHOP01", "hieuluc_tu": "2026-03-01", "hieuluc_den": "2026-03-01"},
                     {"ma": "SHOP01", "hieuluc_tu": "2026-03-01", "cot_la": 1}):
            with self.subTest(dong=dong), self.assertRaises(phienban.LoiPhienBan):
                phienban.them(self.cn, "shop", dong)
        with self.assertRaises(phienban.LoiPhienBan):
            phienban.them(self.cn, "donhang", {"ma": "x", "hieuluc_tu": "2026-03-01"})  # không phải danh mục có phiên bản
        self.assertEqual(self.cn.execute("SELECT count(*) FROM shop").fetchone()[0], 0)

    def test_chong_lan_cung_ma(self):
        a = phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": "2026-03-01", "hieuluc_den": "2026-04-01"})
        for tu, den in (("2026-03-15", None), ("2026-02-01", "2026-03-02"), ("2026-02-01", None), ("2026-03-01", "2026-04-01")):
            with self.subTest(tu=tu, den=den), self.assertRaises(phienban.LoiPhienBan) as loi:
                phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": tu, "hieuluc_den": den})
            self.assertIn("chồng lấn", str(loi.exception))
        b = phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": "2026-04-01"})   # liền kề: được
        phienban.them(self.cn, "shop", {"ma": "SHOP02", "hieuluc_tu": "2026-03-15"})       # mã khác: được
        self.assertEqual(self.cn.execute("SELECT id, phienban FROM shop WHERE ma = 'SHOP01' ORDER BY phienban").fetchall(),
                         [(a, 1), (b, 2)])

    def test_sua_ma_bi_chan_o_lop_ghi(self):
        a = phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": "2026-03-01"})
        for doi in ({"ma": "SHOP09"}, {"id": "khac"}, {"hieuluc_tu": "2026-01-01"}):
            with self.subTest(doi=doi), self.assertRaises(phienban.LoiPhienBan):
                phienban.sua(self.cn, "shop", a, doi)
        with self.assertRaises(phienban.LoiPhienBan):
            phienban.phienban_moi(self.cn, "shop", "SHOP01", "2026-04-01", {"ma": "SHOP09"}, "hethong")
        phienban.sua(self.cn, "shop", a, {"ten": "Shop thử", "trangthai": "ngung"})
        self.assertEqual(self.cn.execute("SELECT ma, ten, trangthai FROM shop").fetchall(), [("SHOP01", "Shop thử", "ngung")])

    def test_phien_ban_moi_va_tim_id(self):
        v1 = phienban.them(self.cn, "shop", {"ma": "SHOP01", "ten": "Shop thử", "hieuluc_tu": "2026-03-01", "ky_tcong": 7})
        v2 = phienban.phienban_moi(self.cn, "shop", "SHOP01", "2026-04-15", {"ky_tcong": 14}, "hethong")
        self.assertEqual(self.cn.execute("SELECT id, phienban, hieuluc_tu, hieuluc_den, ten, ky_tcong FROM shop"
                                         " ORDER BY phienban").fetchall(),
                         [(v1, 1, "2026-03-01", "2026-04-15", "Shop thử", 7), (v2, 2, "2026-04-15", None, "Shop thử", 14)])
        self.assertEqual([phienban.tim_id(self.cn, "shop", "SHOP01", n) for n in ("2026-02-28", "2026-04-14", "2026-04-15")],
                         [None, v1, v2])
        for tu in ("2026-04-15", "2026-03-20", "2026-02-01"):   # không mở phiên bản trùng ngày, chen giữa, trước ngày đầu
            with self.subTest(tu=tu), self.assertRaises(phienban.LoiPhienBan):
                phienban.phienban_moi(self.cn, "shop", "SHOP01", tu, {}, "hethong")

    def test_giao_dich_loi_thi_khong_ghi_do(self):
        self.cn.execute("BEGIN IMMEDIATE")
        phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": "2026-03-01"})
        self.cn.execute("ROLLBACK")      # chạy trong giao dịch người gọi: người gọi huỷ thì không còn dòng
        self.assertEqual(self.cn.execute("SELECT count(*) FROM shop").fetchone()[0], 0)


class KiemA15C16(NenMoi):
    def setUp(self):
        super().setUp()
        self.n1 = songuoi.tao("Nhân viên 01", "nhanvien", "hethong", self.thumuc)["id"]
        self.n2 = songuoi.tao("Nhân viên 02", "nhanvien", "hethong", self.thumuc)["id"]

    def test_a15_02_phien_ban_cung_nguoi(self):
        v1 = phienban.them(self.cn, "nhanvien", {"ma": "NV01", "nguoi_id": self.n1, "phongban": "kinhdoanh", "hieuluc_tu": "2026-03-01"})
        v2 = phienban.phienban_moi(self.cn, "nhanvien", "NV01", "2026-04-15", {"phongban": "kho"}, "hethong")
        self.assertEqual(self.cn.execute("SELECT count(*) FROM nhanvien WHERE nguoi_id = ?", (self.n1,)).fetchone()[0], 2)
        self.assertEqual(phienban.tim_id(self.cn, "nhanvien", self.n1, "2026-04-01", cot="nguoi_id"), v1)
        self.assertEqual(phienban.tim_id(self.cn, "nhanvien", self.n1, "2026-04-20", cot="nguoi_id"), v2)
        with self.assertRaises(phienban.LoiPhienBan) as loi:   # cùng người, mã khác, chồng lấn: chặn
            phienban.them(self.cn, "nhanvien", {"ma": "NV09", "nguoi_id": self.n1, "hieuluc_tu": "2026-05-01"})
        self.assertIn("nguoi_id", str(loi.exception))
        with self.assertRaises(phienban.LoiPhienBan):
            phienban.them(self.cn, "nhanvien", {"ma": "NV02", "hieuluc_tu": "2026-03-01"})   # thiếu người
        phienban.them(self.cn, "nhanvien", {"ma": "NV02", "nguoi_id": self.n2, "hieuluc_tu": "2026-03-01"})
        with self.assertRaises(phienban.LoiPhienBan):
            phienban.tim_id(self.cn, "shop", "x", cot="nguoi_id")   # nguoi_id chỉ là khoá bền của A15

    def test_c16_khong_trung_nguoi_thang_qua_02_phien_ban(self):
        v1 = phienban.them(self.cn, "nhanvien", {"ma": "NV01", "nguoi_id": self.n1, "hieuluc_tu": "2026-03-01"})
        v2 = phienban.phienban_moi(self.cn, "nhanvien", "NV01", "2026-04-15", {"phongban": "kho"}, "hethong")
        so = {"luong": 10_000_000, "thuong": 0, "khac": 0, "tong": 10_000_000}
        a = luong.ghi_thang(self.cn, {"nhanvien_id": v1, "thang": "2026-04", **so})
        self.assertEqual(luong.ghi_thang(self.cn, {"nhanvien_id": v1, "thang": "2026-04", **so}), a)   # nạp lại cùng số
        self.assertEqual(luong.ghi_thang(self.cn, {"nhanvien_id": v2, "thang": "2026-04", **so}), a)   # phiên bản khác, cùng số
        with self.assertRaises(luong.LoiTrung):   # Q7: 02 dòng lương cùng người cùng tháng, số khác
            luong.ghi_thang(self.cn, {"nhanvien_id": v2, "thang": "2026-04", **so, "thuong": 500_000, "tong": 10_500_000})
        luong.ghi_thang(self.cn, {"nhanvien_id": v2, "thang": "2026-05", **so})
        v3 = phienban.them(self.cn, "nhanvien", {"ma": "NV02", "nguoi_id": self.n2, "hieuluc_tu": "2026-03-01"})
        luong.ghi_thang(self.cn, {"nhanvien_id": v3, "thang": "2026-04", **so})   # người khác cùng tháng: được
        self.assertEqual(self.cn.execute("SELECT count(*) FROM luong_nhansu").fetchone()[0], 3)
        for dong in ({"nhanvien_id": v1, "thang": "2026-4"}, {"nhanvien_id": v1, "thang": "2026-13"},
                     {"nhanvien_id": "khongco", "thang": "2026-04"}, {"nhanvien_id": v1, "thang": "2026-06", "cot_la": 1}):
            with self.subTest(dong=dong), self.assertRaises(ValueError):
                luong.ghi_thang(self.cn, dong)


class KiemDoiPhienBanGiuaKy(NenMoi):
    """Q7: thêm phiên bản 2 cho 01 shop giữa kỳ thì phân bổ vẫn đủ 100%; cộng sự trỏ kỹ năng đã cải tiến dùng bản mới."""

    def test_phan_bo_theo_ma_du_100_phan_tram(self):
        s1 = phienban.them(self.cn, "shop", {"ma": "SHOP01", "hieuluc_tu": "2026-03-01", "ky_tcong": 7})
        phienban.them(self.cn, "shop", {"ma": "SHOP02", "hieuluc_tu": "2026-03-01"})
        phanbo = json.loads('{"SHOP01": 6000, "SHOP02": 4000}')   # tỷ lệ × 100, khoá bằng mã (Q1)
        theo_id_thang3 = {phienban.tim_id(self.cn, "shop", m, "2026-03-31"): t for m, t in phanbo.items()}
        phienban.phienban_moi(self.cn, "shop", "SHOP01", "2026-04-15", {"ky_tcong": 14}, "hethong")
        for ngay in ("2026-04-01", "2026-04-30"):
            noi = {m: phienban.tim_id(self.cn, "shop", m, ngay) for m in phanbo}
            with self.subTest(ngay=ngay):
                self.assertNotIn(None, noi.values())
                self.assertEqual(sum(phanbo[m] for m, i in noi.items() if i), 10000)
        # Trỏ bằng `id` phiên bản (cách cũ, loại S) sang tháng 04 chỉ còn nối 40%: lý do Q1 dùng mã cho loại K
        con = {phienban.tim_id(self.cn, "shop", m, "2026-04-30") for m in phanbo}
        self.assertEqual(sum(t for i, t in theo_id_thang3.items() if i in con), 4000)
        self.assertNotIn(s1, con)

    def test_cong_su_dung_ky_nang_ban_moi(self):
        vn = self.mo("Viecnen")
        try:
            k1 = phienban.them(vn, "kynang", {"ma": "KN_TOMTAT", "hieuluc_tu": "2026-03-01", "noidung": "bản 1"})
            phienban.them(vn, "congsu", {"ma": "CS01", "hieuluc_tu": "2026-03-01", "kynang_ids": json.dumps(["KN_TOMTAT"])})
            k2 = phienban.phienban_moi(vn, "kynang", "KN_TOMTAT", "2026-04-15", {"noidung": "bản 2", "nguon": "caitien"}, "hethong")
            ma_kn = json.loads(vn.execute("SELECT kynang_ids FROM congsu WHERE ma = 'CS01'").fetchone()[0])
            self.assertEqual([phienban.tim_id(vn, "kynang", m, "2026-04-20") for m in ma_kn], [k2])
            self.assertEqual([phienban.tim_id(vn, "kynang", m, "2026-04-01") for m in ma_kn], [k1])
        finally:
            vn.close()


class KiemNangBan2(CoThuMuc):
    def setUp(self):
        super().setUp()
        dung_ban2(self.thumuc)
        self.ghi("Baomat", "INSERT INTO nguoidung (id, ma, ten, vaitro, tao_luc, nguoi_khai) VALUES (?, 'chu', 'Chủ thử', 'chu',"
                 " '2026-11-21', 'lenh_vps')", (maso.tao(),))

    def chay_kiem(self):
        ra = io.StringIO()
        with contextlib.redirect_stdout(ra):
            ma = kt.main([str(self.thumuc)])
        return ma, ra.getvalue()

    def test_ma_trong_thi_kiem_truoc_va_lan_nang_cung_dung(self):
        self.ghi("Dulieu_Chinh", "INSERT INTO shop (id, ma) VALUES (?, NULL)", (maso.tao(),))
        self.ghi("Bot", "INSERT INTO kenh (id, ma, vai) VALUES (?, '', 'bot_giaoviec')", (maso.tao(),))
        ma, ra = self.chay_kiem()
        self.assertEqual(ma, 1, ra)
        self.assertIn("(6) Mã trống ở 29 bảng có phiên bản (cần 00; còn thì lần nâng dừng): Dulieu_Chinh.shop 01 dòng,"
                      " Bot.kenh_nhan 01 dòng → DỪNG", ra)
        with self.assertRaises(RuntimeError) as loi:
            khoitao.tao_het(self.thumuc)
        self.assertIn("mã trống", str(loi.exception))
        self.assertEqual({t: self.lay(t, "PRAGMA user_version")[0][0] for t in ketnoi.CAC_FILE}, dict.fromkeys(ketnoi.CAC_FILE, 2))

    def test_du_ma_thi_nang_duoc_co_trigger(self):
        s = maso.tao()
        self.ghi("Dulieu_Chinh", "INSERT INTO shop (id, ma, hieuluc_tu) VALUES (?, 'SHOP01', '2026-03-01')", (s,))
        ma, ra = self.chay_kiem()
        self.assertEqual(ma, 0, ra)
        self.assertIn("(6) Mã trống ở 29 bảng có phiên bản (cần 00; còn thì lần nâng dừng): 00 dòng → ĐẠT", ra)
        khoitao.tao_het(self.thumuc)
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT ma FROM shop WHERE id = ?", (s,)), [("SHOP01",)])
        with self.assertRaises(sqlite3.IntegrityError):   # bảng dựng lại có lại trigger chặn sửa mã
            self.ghi("Dulieu_Chinh", "UPDATE shop SET ma = 'SHOP09' WHERE id = ?", (s,))
        self.assertEqual(self.lay("Dulieu_Chinh", "SELECT count(*) FROM sqlite_master WHERE type = 'trigger'"
                                                  " AND name LIKE 'ma\\_\\_%' ESCAPE '\\'")[0][0], 30)


class KiemQuetMa(CoThuMuc):
    def test_khong_ghi_thang_vao_bang_phien_ban(self):
        """Mọi lần thêm dòng vào 29 bảng đi qua phienban.them; C16 đi qua luong.ghi_thang."""
        bang = "|".join(b for ds in BANG_29.values() for b in ds)
        mau = re.compile(rf"INSERT\s+(OR\s+\w+\s+)?INTO\s+({bang}|luong_nhansu)\b")
        cho_phep = {"maychu/dulieu/phienban.py", "maychu/dulieu/luong.py"}
        sai = []
        for p in sorted((GOC / "maychu").rglob("*.py")):
            ten = p.relative_to(GOC).as_posix()
            if ten in cho_phep or ten == "maychu/dulieu/kiemtruoc_ban3.py":   # bước kiểm trước chỉ chạy trên bản sao trong bộ nhớ
                continue
            for so, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if mau.search(dong):
                    sai.append(f"{ten}:{so}")
        self.assertEqual(sai, [])
