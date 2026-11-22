"""Bài kiểm ngày 04 (phần dữ liệu): lược đồ bản 2, nâng cấp file bản 1 (nay nâng thẳng lên bản hiện hành), cảnh báo tệp hoán đổi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso
from maychu.hethong.giamsat import domay

# Lược đồ bản 1 của 33 bảng đổi ở bản 2 (chép từ commit c63410f), để dựng lại file bản 1 khi kiểm.
V1 = {
    ('Dulieu_Chinh', 'congty'): "CREATE TABLE IF NOT EXISTS congty (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  tien_goc INTEGER\n);",
    ('Dulieu_Chinh', 'kenh'): "CREATE TABLE IF NOT EXISTS kenh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT\n);",
    ('Dulieu_Chinh', 'shop'): "CREATE TABLE IF NOT EXISTS shop (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  congty_id TEXT REFERENCES congty(id),\n  kenh_id TEXT REFERENCES kenh(id),\n  thitruong TEXT,\n  tien_ma TEXT,\n  ky_tcong INTEGER,\n  taikhoan_ban_id TEXT REFERENCES taikhoan(id),\n  ma_trensan TEXT\n);",
    ('Dulieu_Chinh', 'lydo_shopchet'): "CREATE TABLE IF NOT EXISTS lydo_shopchet (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT\n);",
    ('Dulieu_Chinh', 'kho'): "CREATE TABLE IF NOT EXISTS kho (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  quocgia TEXT,\n  ma_kho_pancake TEXT\n);",
    ('Dulieu_Chinh', 'sku'): "CREATE TABLE IF NOT EXISTS sku (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  ma_hienthi TEXT,\n  donvi TEXT,\n  nganhhang TEXT,\n  vongdoi TEXT CHECK (vongdoi IS NULL OR vongdoi IN ('thu', 'chuluc', 'ngung')),\n  loai TEXT CHECK (loai IS NULL OR loai IN ('hang', 'combo', 'qua_kemdieukien', 'qua_khongdieukien', 'baobi')),\n  dinhmuc_baobi INTEGER,\n  ngay_batdau_ban TEXT\n);",
    ('Dulieu_Chinh', 'barcode'): "CREATE TABLE IF NOT EXISTS barcode (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  barcode TEXT,\n  sku_id TEXT REFERENCES sku(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('nhacungcap', 'noibo'))\n);",
    ('Dulieu_Chinh', 'combo_thanhphan'): 'CREATE TABLE IF NOT EXISTS combo_thanhphan (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  combo_id TEXT REFERENCES sku(id),\n  sku_id TEXT REFERENCES sku(id),\n  so_chiec INTEGER\n);',
    ('Dulieu_Chinh', 'ghep_mangoai'): "CREATE TABLE IF NOT EXISTS ghep_mangoai (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nguon TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  ma_ngoai TEXT,\n  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('sku', 'combo', 'taikhoan', 'kho', 'shop')),\n  doituong_id TEXT\n);",
    ('Dulieu_Chinh', 'taikhoan'): "CREATE TABLE IF NOT EXISTS taikhoan (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('banhang', 'quangcao', 'nganhang')),\n  shop_id TEXT REFERENCES shop(id),\n  tien_ma TEXT,\n  phapnhan_dungten_id TEXT REFERENCES congty(id),\n  sotk_4socuoi TEXT\n);",
    ('Dulieu_Chinh', 'nhacungcap'): "CREATE TABLE IF NOT EXISTS nhacungcap (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  dieukhoan_tra TEXT,\n  songay_no INTEGER,\n  tien_ma TEXT\n);",
    ('Dulieu_Chinh', 'nhanvien'): "CREATE TABLE IF NOT EXISTS nhanvien (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  phongban TEXT,\n  module_phutrach TEXT,\n  kenh_chinh TEXT,\n  kenh_duphong TEXT,\n  ma_trenkenh TEXT\n);",
    ('Dulieu_Chinh', 'khoanchi'): "CREATE TABLE IF NOT EXISTS khoanchi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT\n);",
    ('Dulieu_Chinh', 'khuvuc'): "CREATE TABLE IF NOT EXISTS khuvuc (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  thitruong TEXT,\n  tinh_bang TEXT,\n  nhom_vung TEXT\n);",
    ('Dulieu_Chinh', 'loai_module'): "CREATE TABLE IF NOT EXISTS loai_module (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  module_soluong TEXT,\n  module_giatri TEXT,\n  duong_vao TEXT CHECK (duong_vao IS NULL OR duong_vao IN ('A', 'B', 'C', 'D'))\n);",
    ('Dulieu_Chinh', 'hoso_phaply'): "CREATE TABLE IF NOT EXISTS hoso_phaply (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  nhanhang TEXT,\n  so_vanban TEXT,\n  vanban_id TEXT,\n  nguoi_duyet TEXT,\n  duyet_luc TEXT\n);",
    ('Dulieu_Chinh', 'chiso'): "CREATE TABLE IF NOT EXISTS chiso (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT CHECK (nhom IS NULL OR nhom IN ('lai', 'tien', 'hang', 'ban', 'tmdt')),\n  donvi TEXT CHECK (donvi IS NULL OR donvi IN ('tien', 'tyle', 'so', 'ngay')),\n  ma_ham TEXT,\n  mota_congthuc TEXT,\n  cauhoi_quantri TEXT,\n  module_lamchu TEXT,\n  phamvi_chophep TEXT,\n  ky_tinh TEXT CHECK (ky_tinh IS NULL OR ky_tinh IN ('ngay', 'tuan', 'thang')),\n  chieu_tot TEXT CHECK (chieu_tot IS NULL OR chieu_tot IN ('tang', 'giam')),\n  bang_nguon TEXT,\n  quytac_du_ids TEXT\n);",
    ('Dulieu_Chinh', 'quytac_kiemdu'): "CREATE TABLE IF NOT EXISTS quytac_kiemdu (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai_dulieu TEXT REFERENCES loai_module(id),\n  kieu_kiem TEXT CHECK (kieu_kiem IS NULL OR kieu_kiem IN ('co_du_lieu', 'thieu_giatri', 'sai_giatri', 'trung', 'do_moi', 'du_doi_tuong')),\n  bang TEXT,\n  cot TEXT,\n  boloc_json TEXT,\n  nguong INTEGER,\n  donvi_nguong TEXT CHECK (donvi_nguong IS NULL OR donvi_nguong IN ('dong', 'tyle', 'phut', 'gio', 'ngay')),\n  phamvi_loai TEXT CHECK (phamvi_loai IS NULL OR phamvi_loai IN ('congty', 'shop')),\n  ky_loai TEXT CHECK (ky_loai IS NULL OR ky_loai IN ('ngay', 'tuan', 'thang')),\n  chiso_anhhuong TEXT,\n  nguoi_duyet TEXT,\n  duyet_luc TEXT\n);",
    ('Ketnoi', 'ketnoi'): "CREATE TABLE IF NOT EXISTS ketnoi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  mau_ketnoi TEXT,\n  cach_noi TEXT CHECK (cach_noi IS NULL OR cach_noi IN ('ketnoi_chinhthuc', 'file_xuatsan', 'trangweb', 'webhook_vao')),\n  shop_id TEXT,\n  khoa_id TEXT,\n  trangthai_phien TEXT,\n  lan_battay_cuoi TEXT,\n  so_congcu_thay INTEGER,\n  loi_cuoi TEXT\n);",
    ('Ketnoi', 'webhook'): "CREATE TABLE IF NOT EXISTS webhook (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('vao', 'ra')),\n  duongdan TEXT,\n  khoa_id TEXT,\n  cach_kiem TEXT,\n  quytac_json TEXT,\n  viec_gan TEXT,\n  thu_lai TEXT\n);",
    ('Ketnoi', 'theodoi_trang'): "CREATE TABLE IF NOT EXISTS theodoi_trang (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  diachi TEXT,\n  vung_theodoi TEXT,\n  nhip TEXT,\n  lan_xem_cuoi TEXT,\n  mabam_cuoi TEXT,\n  bao_ve TEXT\n);",
    ('Viecnen', 'congsu'): "CREATE TABLE IF NOT EXISTS congsu (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  vaitro TEXT,\n  module TEXT,\n  cachlam TEXT,\n  kynang_ids TEXT,\n  congcu_ids TEXT,\n  mohinh_id TEXT REFERENCES mohinh_ai(id),\n  nguon_ai_id TEXT REFERENCES nguon_ai(id),\n  ngansach_thang INTEGER,\n  chude_ids TEXT,\n  muc_quyen_toida INTEGER\n);",
    ('Viecnen', 'nguon_ai'): "CREATE TABLE IF NOT EXISTS nguon_ai (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('goi', 'khoa_api')),\n  hanmuc INTEGER,\n  tran_tien_thang INTEGER,\n  dungchung INTEGER CHECK (dungchung IS NULL OR dungchung IN (0, 1)),\n  uutien INTEGER,\n  tyle_5gio INTEGER,\n  tyle_tuan INTEGER,\n  datlai_5gio_luc TEXT,\n  datlai_tuan_luc TEXT,\n  do_luc TEXT,\n  da_het_luc INTEGER\n);",
    ('Viecnen', 'team'): "CREATE TABLE IF NOT EXISTS team (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  muctieu TEXT,\n  truongnhom_id TEXT REFERENCES congsu(id),\n  cach_duyet TEXT CHECK (cach_duyet IS NULL OR cach_duyet IN ('moibuoc', 'cuoi'))\n);",
    ('Viecnen', 'kynang'): "CREATE TABLE IF NOT EXISTS kynang (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  mota_khinao TEXT,\n  noidung TEXT,\n  congsu_ids TEXT,\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('vietmoi', 'chuyen', 'caitien')),\n  so_lan_dung INTEGER\n);",
    ('Viecnen', 'quytrinh'): "CREATE TABLE IF NOT EXISTS quytrinh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  cacbuoc_json TEXT,\n  kichhoat TEXT CHECK (kichhoat IS NULL OR kichhoat IN ('tay', 'lich', 'webhook', 'sukien'))\n);",
    ('Bot', 'kenh'): "CREATE TABLE IF NOT EXISTS kenh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  vai TEXT CHECK (vai IS NULL OR vai IN ('anh_nhan_baocao', 'bot_giaoviec')),\n  co_nutbam INTEGER,\n  co_nhom INTEGER,\n  cuaso_gui_gio INTEGER,\n  ketnoi_id TEXT\n);",
    ('Bot', 'chude_nhom'): "CREATE TABLE IF NOT EXISTS chude_nhom (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  kenhnhan_id TEXT REFERENCES kenh(id),\n  ma_nhom TEXT,\n  module TEXT,\n  congsu_id TEXT\n);",
    ('Bot', 'lich_baocao'): "CREATE TABLE IF NOT EXISTS lich_baocao (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  gio_gui TEXT,\n  kenhnhan_id TEXT REFERENCES kenh(id),\n  noidung_mau TEXT\n);",
    ('Bot', 'chatbot'): "CREATE TABLE IF NOT EXISTS chatbot (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  kenhnhan_id TEXT REFERENCES kenh(id),\n  congsu_id TEXT,\n  nguon_trithuc_json TEXT,\n  chinhsach_traloi TEXT,\n  muc_tugui TEXT CHECK (muc_tugui IS NULL OR muc_tugui IN ('chi_dexuat', 'tugui_trongnguong'))\n);",
    ('Nhatky', 'theodoi_maychu'): 'CREATE TABLE IF NOT EXISTS theodoi_maychu (\n  id TEXT PRIMARY KEY NOT NULL,\n  luc TEXT,\n  tyle_ocung INTEGER,\n  ram_dung INTEGER,\n  so_viec_dangchay INTEGER,\n  so_viec_ai_dangchay INTEGER,\n  thoigian_cho_ghi_ms INTEGER\n);',
    ('Baomat', 'nguoidung'): "CREATE TABLE IF NOT EXISTS nguoidung (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  vaitro TEXT CHECK (vaitro IS NULL OR vaitro IN ('chu', 'nhanvien')),\n  module_xem TEXT,\n  matkhau_bam TEXT,\n  totp_khoa_id TEXT REFERENCES kekhoa(id),\n  nhanvien_id TEXT\n);",
    ('Baomat', 'phien_truycap'): "CREATE TABLE IF NOT EXISTS phien_truycap (\n  id TEXT PRIMARY KEY NOT NULL,\n  nguoidung_id TEXT REFERENCES nguoidung(id),\n  loai TEXT CHECK (loai IS NULL OR loai IN ('phien_web', 'ma_truycap')),\n  mabam TEXT,\n  tao_luc TEXT,\n  het_han TEXT,\n  lan_dung_cuoi TEXT,\n  thuhoi_luc TEXT\n);",
}


def dung_ban1(thumuc: Path) -> None:
    khoitao.tao_het(thumuc)
    for (ten, bang), ddl in V1.items():
        cn = ketnoi.mo(ten, thumuc)
        try:
            cn.execute("PRAGMA foreign_keys=OFF")
            cn.execute(f"DROP TABLE {bang}")
            cn.execute(ddl)
            cn.execute("PRAGMA user_version=1")
        finally:
            cn.close()
    for ten in ketnoi.CAC_FILE:
        cn = ketnoi.mo(ten, thumuc)
        try:
            cn.execute("PRAGMA user_version=1")
        finally:
            cn.close()


class KiemBan2(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)

    def tearDown(self):
        self.tam.cleanup()

    def mo(self, ten):
        return ketnoi.mo(ten, self.thumuc)

    def test_file_moi_ban_2_va_cot_bat_buoc(self):
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 105)
        for ten in ketnoi.CAC_FILE:
            cn = self.mo(ten)
            try:
                self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], khoitao.PHIENBAN_LUOCDO)
            finally:
                cn.close()
        cn = self.mo("Bot")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO kenh (id) VALUES (?)", (maso.tao(),))
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO kenh (id, vai) VALUES (?, 'cahai')", (maso.tao(),))
            cn.execute("INSERT INTO kenh (id, vai) VALUES (?, 'bot_giaoviec')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            ma = maso.tao()
            cn.execute("INSERT INTO taikhoan (id, loai) VALUES (?, 'nganhang')", (ma,))
            self.assertEqual(cn.execute("SELECT trangthai FROM taikhoan WHERE id = ?", (ma,)).fetchone()[0], "dung")
            for bang in ("barcode", "combo_thanhphan", "ghep_mangoai"):
                with self.assertRaises(sqlite3.IntegrityError):
                    cn.execute(f"INSERT INTO {bang} (id) VALUES (?)", (maso.tao(),))
                cn.execute(f"INSERT INTO {bang} (id, hieuluc_tu) VALUES (?, '2026-11-21')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            self.assertIn("swap_dung", {r[1] for r in cn.execute("PRAGMA table_info(theodoi_maychu)")})
        finally:
            cn.close()
        cn = self.mo("Baomat")
        try:
            self.assertIn("thietbi", {r[1] for r in cn.execute("PRAGMA table_info(phien_truycap)")})
            ma = maso.tao()
            cn.execute("INSERT INTO nguoidung (id, ma, nguoi_id) VALUES (?, 'chu', 'n1')", (ma,))
            self.assertEqual(cn.execute("SELECT trangthai FROM nguoidung WHERE id = ?", (ma,)).fetchone()[0], "dung")
            with self.assertRaises(sqlite3.IntegrityError):
                cn.execute("INSERT INTO nguoidung (id, trangthai) VALUES (?, NULL)", (maso.tao(),))
        finally:
            cn.close()

    def test_nang_cap_tu_ban_1_giu_du_lieu(self):
        dung_ban1(self.thumuc)
        ma_kenh, ma_tk, ma_n02 = maso.tao(), maso.tao(), maso.tao()
        cn = self.mo("Bot")
        try:
            cn.execute("INSERT INTO kenh (id, ten, vai) VALUES (?, 'Kênh báo anh', 'anh_nhan_baocao')", (ma_kenh,))
            cn.execute("INSERT INTO lich_baocao (id, kenhnhan_id) VALUES (?, ?)", (maso.tao(), ma_kenh))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            cn.execute("INSERT INTO taikhoan (id, loai, sotk_4socuoi) VALUES (?, 'banhang', '1234')", (ma_tk,))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            cn.execute("INSERT INTO theodoi_maychu (id, ram_dung) VALUES (?, 639)", (ma_n02,))
        finally:
            cn.close()
        self.assertEqual(sum(khoitao.tao_het(self.thumuc).values()), 105)
        cn = self.mo("Bot")
        try:
            self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], khoitao.PHIENBAN_LUOCDO)
            self.assertEqual(cn.execute("SELECT ten, vai FROM kenh WHERE id = ?", (ma_kenh,)).fetchone(),
                             ("Kênh báo anh", "anh_nhan_baocao"))
            self.assertEqual(cn.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):  # khoá ngoại tới bảng dựng lại vẫn chạy
                cn.execute("INSERT INTO lich_baocao (id, kenhnhan_id) VALUES (?, 'khongco')", (maso.tao(),))
        finally:
            cn.close()
        cn = self.mo("Dulieu_Chinh")
        try:
            self.assertEqual(cn.execute("SELECT sotk_4socuoi, trangthai FROM taikhoan WHERE id = ?", (ma_tk,)).fetchone(),
                             ("1234", "dung"))
        finally:
            cn.close()
        cn = self.mo("Nhatky")
        try:
            self.assertEqual(cn.execute("SELECT ram_dung, swap_dung FROM theodoi_maychu WHERE id = ?", (ma_n02,)).fetchone(),
                             (639, None))
        finally:
            cn.close()
        for ten in ketnoi.CAC_FILE:
            self.assertTrue((self.thumuc / "saoluu" / "truoc_nangcap_v03" / f"{ten}.sqlite3").exists())

    def test_nang_cap_loi_thi_tra_nguyen_trang(self):
        dung_ban1(self.thumuc)
        ma = maso.tao()
        cn = self.mo("Bot")
        try:
            cn.execute("INSERT INTO kenh (id, ten) VALUES (?, 'Kênh chưa có vai')", (ma,))
        finally:
            cn.close()
        with self.assertRaises(sqlite3.IntegrityError):
            khoitao.tao_het(self.thumuc)
        cn = self.mo("Bot")
        try:
            self.assertEqual(cn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(cn.execute("SELECT ten FROM kenh WHERE id = ?", (ma,)).fetchone()[0], "Kênh chưa có vai")
            self.assertNotIn("vai TEXT NOT NULL", cn.execute("SELECT sql FROM sqlite_master WHERE name = 'kenh'").fetchone()[0])
        finally:
            cn.close()


class KiemCanhBaoSwap(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        khoitao.tao_het(self.thumuc)

    def tearDown(self):
        self.tam.cleanup()

    def dem(self):
        cn = ketnoi.mo("Dulieu_Chinh", self.thumuc)
        try:
            return cn.execute("SELECT count(*), max(giatri) FROM canhbao WHERE khoa_chongtrung = 'swap_vuot_nguong'").fetchone()
        finally:
            cn.close()

    def ghi(self, swap_mb):
        that = domay.do_may
        with mock.patch.object(domay, "do_may", lambda t=None: {**that(t), "may_hoandoi_dung_mb": swap_mb}):
            return domay.ghi_n02(self.thumuc)

    def test_duoi_nguong_khong_bao(self):
        self.assertEqual(self.ghi(100)["swap_dung"], 100)
        self.assertEqual(self.dem()[0], 0)

    def test_qua_nguong_bao_01_lan(self):
        self.ghi(150)
        self.ghi(180)
        self.assertEqual(self.dem(), (1, 150))


if __name__ == "__main__":
    unittest.main()
