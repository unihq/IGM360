"""Kiểm trước khi nâng lược đồ bản 2 → bản 3 (QĐ108, QĐ109; kế hoạch GĐ 1 ngày 10). CHỈ ĐỌC.

Chạy được bằng Python có sẵn trong container bản cũ (chỉ dùng thư viện chuẩn), không cần mã bản mới:

    curl -fsSL https://raw.githubusercontent.com/unihq/IGM360/<commit>/maychu/dulieu/kiemtruoc_ban3.py \\
      | docker compose exec -T igm360 python - /dulieu

Cách kiểm: mở 07 file ở chế độ chỉ đọc, chép sang bộ nhớ, chạy thử đúng các bước nâng bản 3 trên bản trong bộ nhớ
(đổi tên bảng, tạo bảng mới, đếm mã trống ở bảng có phiên bản, dựng lại bảng theo lược đồ bản 3, đổi giá trị
"ai bấm" cũ, kiểm khoá ngoại).
Không ghi gì vào file thật. Chỉ in số đếm, tên bảng, tên cột; không in dữ liệu.
Thoát 0 = ĐẠT (nâng được), 1 = DỪNG (lần nâng sẽ dừng và trả nguyên trạng), 2 = lỗi chạy.
"""
import re
import shutil
import sqlite3
import sys
from pathlib import Path

CAC_FILE = ("Dulieu_Chinh", "Hotho", "Ketnoi", "Viecnen", "Bot", "Nhatky", "Baomat")
# Mã giả cho tài khoản chủ khi dựng thử F01 (bản thật điền `id` dòng A18 của anh, xem khoitao._ban3_truoc).
CHU_GIA = "0" * 26
DIEN = {"Baomat": {"nguoidung": {"nguoi_id": f"(CASE WHEN vaitro = 'chu' THEN '{CHU_GIA}' END)"}}}

# Hằng số dưới sinh bằng máy từ khoitao.py, aibam.py, luocdo/*.sql của cùng commit; không sửa tay
# (bài kiểm kiemthu/ngay10 so lại với mã).
# ---- BẮT ĐẦU PHẦN SINH BẰNG MÁY ----
SINH = {
 "AIBAM": {
  "Baomat": [
   [
    "nguoidung",
    "nguoi_khai"
   ],
   [
    "quyen",
    "nguoi_dat"
   ],
   [
    "kekhoa",
    "nguoi_nhap"
   ],
   [
    "link_chiase",
    "nguoi_tao"
   ],
   [
    "vaitro",
    "nguoi_khai"
   ],
   [
    "quyen_vaitro",
    "nguoi_dat"
   ],
   [
    "gan_vaitro",
    "nguoi_cap"
   ]
  ],
  "Bot": [
   [
    "kenh_nhan",
    "nguoi_khai"
   ],
   [
    "chude_nhom",
    "nguoi_khai"
   ],
   [
    "lich_baocao",
    "nguoi_khai"
   ],
   [
    "chatbot",
    "nguoi_khai"
   ]
  ],
  "Dulieu_Chinh": [
   [
    "congty",
    "nguoi_khai"
   ],
   [
    "kenh",
    "nguoi_khai"
   ],
   [
    "shop",
    "nguoi_khai"
   ],
   [
    "vongdoi_shop",
    "nguoi_ghi"
   ],
   [
    "lydo_shopchet",
    "nguoi_khai"
   ],
   [
    "kho",
    "nguoi_khai"
   ],
   [
    "sku",
    "nguoi_khai"
   ],
   [
    "barcode",
    "nguoi_khai"
   ],
   [
    "combo_thanhphan",
    "nguoi_khai"
   ],
   [
    "ghep_mangoai",
    "nguoi_khai"
   ],
   [
    "taikhoan",
    "nguoi_khai"
   ],
   [
    "tygia_ngay",
    "nguoi_nhap"
   ],
   [
    "tygia_quantri",
    "nguoi_nhap"
   ],
   [
    "nhacungcap",
    "nguoi_khai"
   ],
   [
    "nhanvien",
    "nguoi_khai"
   ],
   [
    "khoanchi",
    "nguoi_khai"
   ],
   [
    "khuvuc",
    "nguoi_khai"
   ],
   [
    "nguoi",
    "nguoi_khai"
   ],
   [
    "loai_module",
    "nguoi_khai"
   ],
   [
    "cuacho",
    "nguoi_xuly"
   ],
   [
    "chungtukho",
    "nguoi_duyet"
   ],
   [
    "kehoach_nguong",
    "nguoi_dat"
   ],
   [
    "thu_sku",
    "nguoi_ketluan"
   ],
   [
    "giavon_chiec",
    "nguoi_khai"
   ],
   [
    "ky_chotso",
    "nguoi_chot"
   ],
   [
    "hoso_phaply",
    "nguoi_khai"
   ],
   [
    "hoso_phaply",
    "nguoi_duyet"
   ],
   [
    "chiso",
    "nguoi_khai"
   ],
   [
    "banxuat",
    "nguoi_xuat"
   ],
   [
    "viec_muctieu",
    "nguoi_tao"
   ],
   [
    "quytac_kiemdu",
    "nguoi_khai"
   ],
   [
    "quytac_kiemdu",
    "nguoi_duyet"
   ],
   [
    "thongso",
    "nguoi_dat"
   ]
  ],
  "Hotho": [
   [
    "filegoc",
    "nguoi_gui"
   ],
   [
    "khuon",
    "nguoi_duyet"
   ],
   [
    "vanban",
    "nguoi_duyet"
   ]
  ],
  "Ketnoi": [
   [
    "ketnoi",
    "nguoi_khai"
   ],
   [
    "webhook",
    "nguoi_khai"
   ],
   [
    "theodoi_trang",
    "nguoi_khai"
   ]
  ],
  "Nhatky": [
   [
    "nhatky_thaotac",
    "nguoi_id"
   ]
  ],
  "Viecnen": [
   [
    "congsu",
    "nguoi_khai"
   ],
   [
    "nguon_ai",
    "nguoi_khai"
   ],
   [
    "lich_dinhky",
    "nguoi_tao"
   ],
   [
    "team",
    "nguoi_khai"
   ],
   [
    "baihoc",
    "nguoi_duyet"
   ],
   [
    "kynang",
    "nguoi_khai"
   ],
   [
    "quytrinh",
    "nguoi_khai"
   ]
  ]
 },
 "BANG_MOI": {
  "Baomat": [
   "vaitro",
   "quyen_vaitro",
   "gan_vaitro"
  ],
  "Dulieu_Chinh": [
   "nguoi"
  ]
 },
 "BANG_PHIENBAN": {
  "Baomat": [
   "nguoidung",
   "vaitro"
  ],
  "Bot": [
   "chatbot",
   "chude_nhom",
   "kenh_nhan",
   "lich_baocao"
  ],
  "Dulieu_Chinh": [
   "chiso",
   "congty",
   "hoso_phaply",
   "kenh",
   "kho",
   "khoanchi",
   "khuvuc",
   "loai_module",
   "lydo_shopchet",
   "nhacungcap",
   "nhanvien",
   "quytac_kiemdu",
   "shop",
   "sku",
   "taikhoan"
  ],
  "Hotho": [
   "khuon"
  ],
  "Ketnoi": [
   "ketnoi",
   "theodoi_trang",
   "webhook"
  ],
  "Viecnen": [
   "congsu",
   "kynang",
   "nguon_ai",
   "quytrinh",
   "team"
  ]
 },
 "BO_COT": {
  "Baomat": {
   "nguoidung": [
    "module_xem"
   ]
  }
 },
 "DDL": {
  "Baomat.gan_vaitro": "CREATE TABLE IF NOT EXISTS gan_vaitro (\n  id TEXT PRIMARY KEY NOT NULL,\n  nguoidung_id TEXT NOT NULL REFERENCES nguoidung(id),\n  vaitro_ma TEXT NOT NULL,\n  phamvi_loai TEXT NOT NULL CHECK (phamvi_loai IN ('congty', 'shop', 'chinhminh')),\n  phamvi_ma_json TEXT,\n  nguoi_cap TEXT,\n  cap_luc TEXT,\n  hieuluc_tu TEXT NOT NULL,\n  hieuluc_den TEXT,\n  lydo TEXT\n);",
  "Baomat.nguoidung": "CREATE TABLE IF NOT EXISTS nguoidung (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  vaitro TEXT CHECK (vaitro IS NULL OR vaitro IN ('chu', 'nhanvien')),\n  matkhau_bam TEXT,\n  totp_khoa_id TEXT REFERENCES kekhoa(id),\n  nguoi_id TEXT NOT NULL UNIQUE\n);",
  "Baomat.quyen_vaitro": "CREATE TABLE IF NOT EXISTS quyen_vaitro (\n  id TEXT PRIMARY KEY NOT NULL,\n  vaitro_ma TEXT NOT NULL,\n  doituong_loai TEXT NOT NULL CHECK (doituong_loai IN ('man', 'nhom_nhaycam')),\n  doituong_ma TEXT NOT NULL,\n  thaotac TEXT NOT NULL CHECK (thaotac IN ('xem', 'nhap', 'sua', 'duyet', 'xuat', 'chiase')),\n  phamvi_toida TEXT NOT NULL CHECK (phamvi_toida IN ('congty', 'shop', 'chinhminh')),\n  nguoi_dat TEXT,\n  tao_luc TEXT,\n  hieuluc_tu TEXT NOT NULL,\n  hieuluc_den TEXT,\n  CHECK (doituong_loai <> 'nhom_nhaycam' OR doituong_ma IN ('loinhuan', 'luong', 'dongtien')),\n  CHECK (NOT (doituong_loai = 'nhom_nhaycam' AND doituong_ma = 'luong' AND phamvi_toida = 'shop')),\n  CHECK (NOT (doituong_loai = 'nhom_nhaycam' AND doituong_ma = 'luong' AND thaotac IN ('chiase', 'duyet')))\n);",
  "Baomat.vaitro": "CREATE TABLE IF NOT EXISTS vaitro (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  mota TEXT,\n  la_macdinh INTEGER NOT NULL DEFAULT 0 CHECK (la_macdinh IN (0, 1))\n);",
  "Bot.chatbot": "CREATE TABLE IF NOT EXISTS chatbot (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  congsu_id TEXT,\n  nguon_trithuc_json TEXT,\n  chinhsach_traloi TEXT,\n  muc_tugui TEXT CHECK (muc_tugui IS NULL OR muc_tugui IN ('chi_dexuat', 'tugui_trongnguong'))\n);",
  "Bot.chude_nhom": "CREATE TABLE IF NOT EXISTS chude_nhom (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  ma_nhom TEXT,\n  module TEXT,\n  congsu_id TEXT\n);",
  "Bot.kenh_nhan": "CREATE TABLE IF NOT EXISTS kenh_nhan (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  vai TEXT NOT NULL CHECK (vai IN ('anh_nhan_baocao', 'bot_giaoviec')),\n  co_nutbam INTEGER,\n  co_nhom INTEGER,\n  cuaso_gui_gio INTEGER,\n  ketnoi_id TEXT,\n  nguoi_id TEXT\n);",
  "Bot.lich_baocao": "CREATE TABLE IF NOT EXISTS lich_baocao (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  gio_gui TEXT,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  noidung_mau TEXT,\n  lap_lai TEXT NOT NULL DEFAULT 'hangngay' CHECK (lap_lai IN ('hangngay', 'hangthang')),\n  ngay_trongthang INTEGER CHECK (ngay_trongthang IS NULL OR ngay_trongthang BETWEEN 1 AND 31),\n  gui_tin INTEGER NOT NULL DEFAULT 1 CHECK (gui_tin IN (0, 1)),\n  CHECK (lap_lai <> 'hangthang' OR ngay_trongthang IS NOT NULL)\n);",
  "Bot.tin_nhom": "CREATE TABLE IF NOT EXISTS tin_nhom (\n  id TEXT PRIMARY KEY NOT NULL,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  chude_id TEXT REFERENCES chude_nhom(id),\n  nguoigui TEXT,\n  nguoi_id TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('chu', 'file', 'anh', 'video', 'thoai')),\n  noidung TEXT,\n  giongnoi_id TEXT REFERENCES giongnoi_luot(id),\n  nhiemvu_id TEXT,\n  lonap_id TEXT,\n  trangthai TEXT\n);",
  "Dulieu_Chinh.chiso": "CREATE TABLE IF NOT EXISTS chiso (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT CHECK (nhom IS NULL OR nhom IN ('lai', 'tien', 'hang', 'ban', 'tmdt')),\n  donvi TEXT CHECK (donvi IS NULL OR donvi IN ('tien', 'tyle', 'so', 'ngay')),\n  ma_ham TEXT,\n  mota_congthuc TEXT,\n  cauhoi_quantri TEXT,\n  module_lamchu TEXT,\n  phamvi_chophep TEXT,\n  ky_tinh TEXT CHECK (ky_tinh IS NULL OR ky_tinh IN ('ngay', 'tuan', 'thang')),\n  chieu_tot TEXT CHECK (chieu_tot IS NULL OR chieu_tot IN ('tang', 'giam')),\n  bang_nguon TEXT,\n  quytac_du_ids TEXT,\n  nhom_nhaycam TEXT CHECK (nhom_nhaycam IS NULL OR nhom_nhaycam IN ('loinhuan', 'luong', 'dongtien'))\n);",
  "Dulieu_Chinh.congty": "CREATE TABLE IF NOT EXISTS congty (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  tien_goc INTEGER\n);",
  "Dulieu_Chinh.dieuchinh": "CREATE TABLE IF NOT EXISTS dieuchinh (\n  id TEXT PRIMARY KEY NOT NULL,\n  bang TEXT,\n  dong_id TEXT,\n  truong TEXT,\n  giatri_cu TEXT,\n  giatri_moi TEXT,\n  lydo TEXT,\n  nguoi_sua_loai TEXT CHECK (nguoi_sua_loai IS NULL OR nguoi_sua_loai IN ('anh', 'ai', 'nhanvien')),\n  nguoi_sua_id TEXT REFERENCES nguoi(id),\n  muc TEXT CHECK (muc IS NULL OR muc IN ('ai_tuapdung', 'anh_duyet')),\n  cuacho_id TEXT REFERENCES cuacho(id),\n  the_duyet_id TEXT,\n  sua_luc TEXT,\n  con_hieuluc INTEGER,\n  hoantac_boi_id TEXT\n);",
  "Dulieu_Chinh.donhang": "CREATE TABLE IF NOT EXISTS donhang (\n  id TEXT PRIMARY KEY NOT NULL,\n  congty_id TEXT REFERENCES congty(id),\n  shop_id TEXT REFERENCES shop(id),\n  thitruong TEXT,\n  ky TEXT,\n  ky_goc TEXT,\n  tien_ma TEXT,\n  sotien_nguyente INTEGER,\n  sotien_quydoi INTEGER,\n  tygia_id TEXT REFERENCES tygia_ngay(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),\n  lonap_id TEXT REFERENCES lonap(id),\n  banghigoc_id TEXT,\n  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),\n  tao_luc TEXT,\n  kenh_id TEXT REFERENCES kenh(id),\n  ma_don_nguon TEXT,\n  ma_don_pancake TEXT,\n  nguon_don TEXT CHECK (nguon_don IS NULL OR nguon_don IN ('pancake', 'san', 'file')),\n  khuvuc_id TEXT REFERENCES khuvuc(id),\n  dat_luc TEXT,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdong', 'danggiao', 'giao_thanhcong', 'giao_thatbai', 'hoan', 'huy')),\n  trangthai_nguon TEXT,\n  giao_thanhcong_luc TEXT,\n  doanhthu INTEGER,\n  giamgia INTEGER,\n  phisan INTEGER,\n  UNIQUE (shop_id, ma_don_nguon)\n);",
  "Dulieu_Chinh.ghep_mangoai": "CREATE TABLE IF NOT EXISTS ghep_mangoai (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT NOT NULL,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nguon TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  ma_ngoai TEXT,\n  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('sku', 'combo', 'taikhoan', 'kho', 'shop', 'nguoi')),\n  doituong_id TEXT\n);",
  "Dulieu_Chinh.hoso_phaply": "CREATE TABLE IF NOT EXISTS hoso_phaply (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  nhanhang TEXT,\n  so_vanban TEXT,\n  vanban_id TEXT,\n  nguoi_duyet TEXT,\n  duyet_luc TEXT\n);",
  "Dulieu_Chinh.kenh": "CREATE TABLE IF NOT EXISTS kenh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT\n);",
  "Dulieu_Chinh.kho": "CREATE TABLE IF NOT EXISTS kho (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  quocgia TEXT,\n  ma_kho_pancake TEXT\n);",
  "Dulieu_Chinh.khoanchi": "CREATE TABLE IF NOT EXISTS khoanchi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT\n);",
  "Dulieu_Chinh.khuvuc": "CREATE TABLE IF NOT EXISTS khuvuc (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  thitruong TEXT,\n  tinh_bang TEXT,\n  nhom_vung TEXT\n);",
  "Dulieu_Chinh.loai_module": "CREATE TABLE IF NOT EXISTS loai_module (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  module_soluong TEXT,\n  module_giatri TEXT,\n  duong_vao TEXT CHECK (duong_vao IS NULL OR duong_vao IN ('A', 'B', 'C', 'D'))\n);",
  "Dulieu_Chinh.lonap": "CREATE TABLE IF NOT EXISTS lonap (\n  id TEXT PRIMARY KEY NOT NULL,\n  loai_dulieu TEXT REFERENCES loai_module(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),\n  ketnoi_id TEXT,\n  thay_cho_lonap_id TEXT,\n  congty_id TEXT REFERENCES congty(id),\n  shop_id TEXT REFERENCES shop(id),\n  ky_tu TEXT,\n  ky_den TEXT,\n  khuon_id TEXT,\n  nguoi_nap TEXT CHECK (nguoi_nap IS NULL OR nguoi_nap IN ('anh', 'nhanvien', 'bot', 'viecnen')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  khoa_chongtrung TEXT,\n  so_dong_doc INTEGER,\n  so_dong_nhan INTEGER,\n  so_dong_loi INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdoc', 'cho_xuly', 'xong', 'loaibo')),\n  batdau_luc TEXT,\n  xong_luc TEXT,\n  tao_luc TEXT\n);",
  "Dulieu_Chinh.lydo_shopchet": "CREATE TABLE IF NOT EXISTS lydo_shopchet (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nhom TEXT\n);",
  "Dulieu_Chinh.nguoi": "CREATE TABLE IF NOT EXISTS nguoi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL UNIQUE CHECK (length(ma) = 7 AND ma GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),\n  ten TEXT NOT NULL,\n  loai TEXT NOT NULL,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  trangthai_hoc TEXT NOT NULL DEFAULT 'chua_dongy' CHECK (trangthai_hoc IN ('chua_dongy', 'dang_hoc', 'dung_hoc')),\n  lydo_dung_hoc TEXT CHECK (lydo_dung_hoc IS NULL OR lydo_dung_hoc IN ('rutlai', 'nghiviec')),\n  trangthai_hoc_luc TEXT,\n  co_dlcn INTEGER NOT NULL DEFAULT 0 CHECK (co_dlcn IN (0, 1)),\n  gop_vao_id TEXT REFERENCES nguoi(id),\n  nguoi_khai TEXT NOT NULL,\n  tao_luc TEXT NOT NULL,\n  CHECK (trangthai_hoc <> 'dung_hoc' OR lydo_dung_hoc IS NOT NULL)\n);",
  "Dulieu_Chinh.nhacungcap": "CREATE TABLE IF NOT EXISTS nhacungcap (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  dieukhoan_tra TEXT,\n  songay_no INTEGER,\n  tien_ma TEXT\n);",
  "Dulieu_Chinh.nhanvien": "CREATE TABLE IF NOT EXISTS nhanvien (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  phongban TEXT,\n  module_phutrach TEXT,\n  kenh_chinh TEXT,\n  kenh_duphong TEXT,\n  nguoi_id TEXT NOT NULL REFERENCES nguoi(id),\n  tinhtrang TEXT NOT NULL DEFAULT 'danglam' CHECK (tinhtrang IN ('danglam', 'danghi')),\n  ngay_nghiviec TEXT\n);",
  "Dulieu_Chinh.nhiemvu": "CREATE TABLE IF NOT EXISTS nhiemvu (\n  id TEXT PRIMARY KEY NOT NULL,\n  viec_id TEXT REFERENCES viec_muctieu(id),\n  tieude TEXT,\n  mota TEXT,\n  loai_nguoinhan TEXT NOT NULL CHECK (loai_nguoinhan IN ('anh', 'nhanvien', 'congsu')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  congsu_id TEXT,\n  phongban TEXT,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho', 'danglam', 'chodoichieu', 'xong', 'huy')),\n  uutien INTEGER,\n  han TEXT,\n  giatri_lucgiao INTEGER,\n  muctieu INTEGER,\n  ngay_dolai TEXT,\n  ketqua_dolai TEXT,\n  phuthuoc_json TEXT,\n  lich_id TEXT,\n  quytrinh_lanchay_id TEXT,\n  team_luot_id TEXT,\n  cuacho_id TEXT REFERENCES cuacho(id),\n  the_duyet_id TEXT,\n  tao_luc TEXT,\n  xong_luc TEXT,\n  CHECK ((loai_nguoinhan IN ('anh', 'nhanvien') AND nguoi_id IS NOT NULL AND congsu_id IS NULL)\n      OR (loai_nguoinhan = 'congsu' AND congsu_id IS NOT NULL AND nguoi_id IS NULL))\n);",
  "Dulieu_Chinh.nhiemvu_sukien": "CREATE TABLE IF NOT EXISTS nhiemvu_sukien (\n  id TEXT PRIMARY KEY NOT NULL,\n  nhiemvu_id TEXT REFERENCES nhiemvu(id),\n  loai TEXT CHECK (loai IS NULL OR loai IN ('phanhoi', 'doitrangthai', 'binhluan', 'file', 'dolai')),\n  noidung TEXT,\n  tin_id TEXT,\n  nguoi_loai TEXT CHECK (nguoi_loai IS NULL OR nguoi_loai IN ('anh', 'nhanvien', 'congsu', 'bot')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  congsu_id TEXT,\n  luc TEXT\n);",
  "Dulieu_Chinh.quytac_kiemdu": "CREATE TABLE IF NOT EXISTS quytac_kiemdu (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai_dulieu TEXT REFERENCES loai_module(id),\n  kieu_kiem TEXT CHECK (kieu_kiem IS NULL OR kieu_kiem IN ('co_du_lieu', 'thieu_giatri', 'sai_giatri', 'trung', 'do_moi', 'du_doi_tuong')),\n  bang TEXT,\n  cot TEXT,\n  boloc_json TEXT,\n  nguong INTEGER,\n  donvi_nguong TEXT CHECK (donvi_nguong IS NULL OR donvi_nguong IN ('dong', 'tyle', 'phut', 'gio', 'ngay')),\n  phamvi_loai TEXT CHECK (phamvi_loai IS NULL OR phamvi_loai IN ('congty', 'shop')),\n  ky_loai TEXT CHECK (ky_loai IS NULL OR ky_loai IN ('ngay', 'tuan', 'thang')),\n  chiso_anhhuong TEXT,\n  nguoi_duyet TEXT,\n  duyet_luc TEXT\n);",
  "Dulieu_Chinh.shop": "CREATE TABLE IF NOT EXISTS shop (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  congty_id TEXT REFERENCES congty(id),\n  kenh_id TEXT REFERENCES kenh(id),\n  thitruong TEXT,\n  tien_ma TEXT,\n  ky_tcong INTEGER,\n  taikhoan_ban_id TEXT REFERENCES taikhoan(id),\n  ma_trensan TEXT\n);",
  "Dulieu_Chinh.sku": "CREATE TABLE IF NOT EXISTS sku (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  ma_hienthi TEXT,\n  donvi TEXT,\n  nganhhang TEXT,\n  vongdoi TEXT CHECK (vongdoi IS NULL OR vongdoi IN ('thu', 'chuluc', 'ngung')),\n  loai TEXT CHECK (loai IS NULL OR loai IN ('hang', 'combo', 'qua_kemdieukien', 'qua_khongdieukien', 'baobi')),\n  dinhmuc_baobi INTEGER,\n  ngay_batdau_ban TEXT\n);",
  "Dulieu_Chinh.taikhoan": "CREATE TABLE IF NOT EXISTS taikhoan (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('banhang', 'quangcao', 'nganhang')),\n  shop_id TEXT REFERENCES shop(id),\n  tien_ma TEXT,\n  phapnhan_dungten_id TEXT REFERENCES congty(id),\n  sotk_4socuoi TEXT\n);",
  "Hotho.banghigoc": "CREATE TABLE IF NOT EXISTS banghigoc (\n  id TEXT PRIMARY KEY NOT NULL,\n  lonap_id TEXT,\n  filegoc_id TEXT REFERENCES filegoc(id),\n  nguon TEXT,\n  loai_dulieu TEXT,\n  ma_doituong TEXT,\n  dong_trongfile TEXT,\n  lay_luc TEXT,\n  noidung_json TEXT,\n  mabam TEXT,\n  vitri_luu TEXT CHECK (vitri_luu IS NULL OR vitri_luu IN ('vps', 'drive')),\n  drive_goi_id TEXT,\n  UNIQUE (nguon, loai_dulieu, ma_doituong, mabam)\n);",
  "Hotho.filegoc": "CREATE TABLE IF NOT EXISTS filegoc (\n  id TEXT PRIMARY KEY NOT NULL,\n  lonap_id TEXT,\n  ten_file TEXT,\n  mabam_sha256 TEXT,\n  dungluong_byte INTEGER,\n  dinhdang TEXT,\n  noi_luu TEXT CHECK (noi_luu IS NULL OR noi_luu IN ('vps_tam', 'drive')),\n  drive_file_id TEXT,\n  trangthai_day TEXT CHECK (trangthai_day IS NULL OR trangthai_day IN ('cho_day', 'da_day', 'loi')),\n  nhan_luc TEXT,\n  day_luc TEXT,\n  nguoi_gui TEXT,\n  UNIQUE (mabam_sha256)\n);",
  "Hotho.khuon": "CREATE TABLE IF NOT EXISTS khuon (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  phienban INTEGER,\n  loai_dulieu TEXT,\n  nguon TEXT,\n  bo_tieude_json TEXT,\n  mabam_tieude TEXT,\n  cach_tim_dong_tieude TEXT,\n  anhxa_json TEXT,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dexuat', 'daduyet', 'ngung')),\n  nguoi_duyet TEXT,\n  duyet_luc TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT\n);",
  "Ketnoi.hoptin": "CREATE TABLE IF NOT EXISTS hoptin (\n  id TEXT PRIMARY KEY NOT NULL,\n  nguon TEXT,\n  ketnoi_id TEXT REFERENCES ketnoi(id),\n  ma_sukien TEXT,\n  loai_sukien TEXT,\n  ma_don TEXT,\n  nhan_luc TEXT,\n  cach_kiem TEXT CHECK (cach_kiem IS NULL OR cach_kiem IN ('dauxacthuc', 'mabimat_duongdan')),\n  ketqua_kiem TEXT CHECK (ketqua_kiem IS NULL OR ketqua_kiem IN ('dat', 'khongdat')),\n  noidung_json TEXT,\n  da_goilai INTEGER,\n  goilai_luc TEXT,\n  lonap_id TEXT,\n  trung INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangxuly', 'xong', 'loi')),\n  so_lan_thu INTEGER,\n  UNIQUE (nguon, ma_sukien)\n);",
  "Ketnoi.ketnoi": "CREATE TABLE IF NOT EXISTS ketnoi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  mau_ketnoi TEXT,\n  cach_noi TEXT CHECK (cach_noi IS NULL OR cach_noi IN ('ketnoi_chinhthuc', 'file_xuatsan', 'trangweb', 'webhook_vao')),\n  shop_id TEXT,\n  khoa_id TEXT,\n  trangthai_phien TEXT,\n  lan_battay_cuoi TEXT,\n  so_congcu_thay INTEGER,\n  loi_cuoi TEXT\n);",
  "Ketnoi.theodoi_trang": "CREATE TABLE IF NOT EXISTS theodoi_trang (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  diachi TEXT,\n  vung_theodoi TEXT,\n  nhip TEXT,\n  lan_xem_cuoi TEXT,\n  mabam_cuoi TEXT,\n  bao_ve TEXT\n);",
  "Ketnoi.webhook": "CREATE TABLE IF NOT EXISTS webhook (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('vao', 'ra')),\n  duongdan TEXT,\n  khoa_id TEXT,\n  cach_kiem TEXT,\n  quytac_json TEXT,\n  viec_gan TEXT,\n  thu_lai TEXT\n);",
  "Viecnen.congsu": "CREATE TABLE IF NOT EXISTS congsu (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  vaitro TEXT,\n  module TEXT,\n  cachlam TEXT,\n  kynang_ids TEXT,\n  congcu_ids TEXT,\n  mohinh_id TEXT REFERENCES mohinh_ai(id),\n  nguon_ai_id TEXT REFERENCES nguon_ai(id),\n  ngansach_thang INTEGER,\n  chude_ids TEXT,\n  muc_quyen_toida INTEGER\n);",
  "Viecnen.kynang": "CREATE TABLE IF NOT EXISTS kynang (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  mota_khinao TEXT,\n  noidung TEXT,\n  congsu_ids TEXT,\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('vietmoi', 'chuyen', 'caitien')),\n  so_lan_dung INTEGER\n);",
  "Viecnen.nguon_ai": "CREATE TABLE IF NOT EXISTS nguon_ai (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('goi', 'khoa_api', 'tuchay')),\n  hanmuc INTEGER,\n  tran_tien_thang INTEGER,\n  dungchung INTEGER CHECK (dungchung IS NULL OR dungchung IN (0, 1)),\n  uutien INTEGER,\n  tyle_5gio INTEGER,\n  tyle_tuan INTEGER,\n  datlai_5gio_luc TEXT,\n  datlai_tuan_luc TEXT,\n  do_luc TEXT,\n  da_het_luc INTEGER,\n  hang TEXT NOT NULL,\n  cach_goi TEXT NOT NULL CHECK (cach_goi IN ('cli', 'anthropic', 'openai')),\n  diachi_goc TEXT\n);",
  "Viecnen.quytrinh": "CREATE TABLE IF NOT EXISTS quytrinh (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  cacbuoc_json TEXT,\n  kichhoat TEXT CHECK (kichhoat IS NULL OR kichhoat IN ('tay', 'lich', 'webhook', 'sukien'))\n);",
  "Viecnen.team": "CREATE TABLE IF NOT EXISTS team (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  muctieu TEXT,\n  truongnhom_id TEXT REFERENCES congsu(id),\n  cach_duyet TEXT CHECK (cach_duyet IS NULL OR cach_duyet IN ('moibuoc', 'cuoi'))\n);"
 },
 "DIEN_BAN3": {
  "Viecnen": {
   "nguon_ai": {
    "cach_goi": "(CASE WHEN ma GLOB 'goi_claude_*' OR ma GLOB 'goi_chatgpt_*' THEN 'cli' WHEN ma GLOB 'khoa_anthropic*' THEN 'anthropic' WHEN ma GLOB 'khoa_openai*' THEN 'openai' END)",
    "hang": "(CASE WHEN ma GLOB 'goi_claude_*' OR ma GLOB 'khoa_anthropic*' THEN 'anthropic' WHEN ma GLOB 'goi_chatgpt_*' OR ma GLOB 'khoa_openai*' THEN 'openai' END)"
   }
  }
 },
 "DOI_CU_MAY": {
  "lenh_vps": "hethong"
 },
 "DOI_TEN": {
  "Bot": [
   [
    "kenh",
    "kenh_nhan"
   ]
  ]
 },
 "DUNG_LAI": {
  "Baomat": [
   "nguoidung"
  ],
  "Bot": [
   "kenh_nhan",
   "tin_nhom",
   "lich_baocao",
   "chatbot",
   "chude_nhom"
  ],
  "Dulieu_Chinh": [
   "ghep_mangoai",
   "nhanvien",
   "lonap",
   "dieuchinh",
   "nhiemvu",
   "nhiemvu_sukien",
   "donhang",
   "chiso",
   "congty",
   "hoso_phaply",
   "kenh",
   "kho",
   "khoanchi",
   "khuvuc",
   "loai_module",
   "lydo_shopchet",
   "nhacungcap",
   "quytac_kiemdu",
   "shop",
   "sku",
   "taikhoan"
  ],
  "Hotho": [
   "filegoc",
   "banghigoc",
   "khuon"
  ],
  "Ketnoi": [
   "hoptin",
   "ketnoi",
   "theodoi_trang",
   "webhook"
  ],
  "Viecnen": [
   "congsu",
   "kynang",
   "nguon_ai",
   "quytrinh",
   "team"
  ]
 },
 "MA_MAY": [
  "hethong",
  "bot",
  "viecnen",
  "ai"
 ],
 "ULID": "^[0-9A-HJKMNP-TV-Z]{26}$"
}
# ---- HẾT PHẦN SINH BẰNG MÁY ----


def _dung_lai(cn, bang, ddl, dien, duoc_bo=()):
    """Giống khoitao._dung_lai: trả số dòng còn dữ liệu ở cột sắp bỏ (0 = không vướng); `duoc_bo` = BO_COT."""
    moi = f"{bang}__moi"
    cn.execute(ddl.replace(f"CREATE TABLE IF NOT EXISTS {bang} (", f"CREATE TABLE {moi} (", 1))
    cot_moi = cn.execute(f"PRAGMA table_info({moi})").fetchall()
    cot_cu = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
    vuong = []
    for c in sorted(cot_cu - {r[1] for r in cot_moi} - set(duoc_bo)):
        so = cn.execute(f"SELECT count(*) FROM {bang} WHERE {c} IS NOT NULL").fetchone()[0]
        if so:
            vuong.append(f"cột {c} sắp bỏ còn {so:02d} dòng có dữ liệu")
    if vuong:
        return vuong
    chung = [r for r in cot_moi if r[1] in cot_cu or r[1] in dien]
    lay = [f"COALESCE({dien.get(r[1], r[1])}, {r[4]})" if r[3] and r[4] is not None else dien.get(r[1], r[1]) for r in chung]
    cn.execute(f"INSERT INTO {moi} ({', '.join(r[1] for r in chung)}) SELECT {', '.join(lay)} FROM {bang}")
    cn.execute(f"DROP TABLE {bang}")
    cn.execute(f"ALTER TABLE {moi} RENAME TO {bang}")
    return []


def _hople(v, ulid=re.compile(SINH.get("ULID", "^$"))):
    return isinstance(v, str) and (v in SINH["MA_MAY"] or bool(ulid.match(v)))


def _doi_cu(chu):
    doi = dict(SINH["DOI_CU_MAY"])
    if chu:
        for k in ("anh", chu[1], chu[2]):
            if k and not _hople(k):
                doi[k] = chu[0]
    return doi


def _so(v, le=0) -> str:
    """Số kiểu Việt Nam: 1–9 ghi 02 chữ số (số đếm), nghìn ngăn bằng dấu chấm, thập phân bằng dấu phẩy."""
    if le == 0 and 0 <= v < 10:
        return f"{int(v):02d}"
    nguyen, _, phan = f"{v:,.{le}f}".partition(".")
    return nguyen.replace(",", ".") + ("," + phan if phan else "")


def _mo_bo_nho(duong: Path) -> sqlite3.Connection:
    nguon = sqlite3.connect(duong.resolve().as_uri() + "?mode=ro", uri=True)
    bo = sqlite3.connect(":memory:", isolation_level=None)
    try:
        nguon.backup(bo)
    finally:
        nguon.close()
    return bo


def kiem(thumuc: Path) -> tuple[bool, list[str]]:
    dong, dat = [], True

    def ghi(muc, ok, chu):
        nonlocal dat
        dat = dat and ok
        dong.append(f"({muc}) {chu} → {'ĐẠT' if ok else 'DỪNG'}")

    # (1) phiên bản từng file
    ban = {}
    for ten in CAC_FILE:
        p = thumuc / f"{ten}.sqlite3"
        if not p.exists():
            ban[ten] = None
            continue
        cn = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            ban[ten] = cn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            cn.close()
    chu_ban = " · ".join(f"{t} {'không có' if b is None else b}" for t, b in ban.items())
    if all(b is not None and b >= 3 for b in ban.values()):   # 0.8.0: bản 4 cũng không cần nâng 2 → 3
        ghi(1, True, f"Phiên bản lược đồ: {chu_ban}. Đã ở bản 3 trở lên, không cần nâng")
        return dat, dong
    ghi(1, all(b in (2, 3) for b in ban.values()), f"Phiên bản lược đồ (cần 2 hoặc 3, đủ 07 file): {chu_ban}")
    if not dat:
        return dat, dong

    # (2) tài khoản chủ, tài khoản khác (F01 bản 3: nguoi_id bắt buộc, không trùng; GĐ 1 chỉ 01 tài khoản chủ)
    bm = _mo_bo_nho(thumuc / "Baomat.sqlite3")
    so_chu, so_khac = bm.execute("SELECT sum(vaitro = 'chu'), sum(vaitro IS NOT 'chu') FROM nguoidung").fetchone()
    chu = bm.execute("SELECT id, ma, ten FROM nguoidung WHERE vaitro = 'chu' ORDER BY tao_luc LIMIT 1").fetchone()
    bm.close()
    so_chu, so_khac = so_chu or 0, so_khac or 0
    ghi(2, so_chu == 1 and so_khac == 0, f"Tài khoản chủ: {so_chu:02d} (cần đúng 01); tài khoản khác: {so_khac:02d} (cần 00)")

    # (3) dựng thử bản 3 trên bản trong bộ nhớ; (4) "ai bấm"
    doi = _doi_cu(chu)
    tong_doi, la, ma_trong = 0, [], []
    for ten in CAC_FILE:
        if ban[ten] == 3:
            continue
        cn = _mo_bo_nho(thumuc / f"{ten}.sqlite3")
        cn.create_function("aibam_hople", 1, lambda v: int(_hople(v)), deterministic=True)
        cn.execute("PRAGMA foreign_keys=OFF")
        vuong = []
        try:
            for cu, moi in SINH["DOI_TEN"].get(ten, []):
                cn.execute(f"ALTER TABLE {cu} RENAME TO {moi}")
            for b in SINH["BANG_MOI"].get(ten, []):
                cn.execute(SINH["DDL"][f"{ten}.{b}"])
            for b in SINH["BANG_PHIENBAN"].get(ten, []):   # (6) QĐ142: mã bắt buộc; lần nâng dừng nếu còn mã trống
                n = cn.execute(f"SELECT count(*) FROM {b} WHERE ma IS NULL OR trim(ma) = ''").fetchone()[0]
                if n:
                    ma_trong.append(f"{ten}.{b} {_so(n)} dòng")
            dien_them = SINH["DIEN_BAN3"].get(ten, {})   # Y22a: cột mới bắt buộc điền theo mã cũ (QĐ161)
            for b, dien in dien_them.items():
                for c, bt in dien.items():
                    n = cn.execute(f"SELECT count(*) FROM {b} WHERE {bt} IS NULL").fetchone()[0]
                    if n:
                        vuong.append(f"{b}: {_so(n)} dòng không nhận ra {c} theo mã cũ")
            for b in SINH["DUNG_LAI"].get(ten, []):
                try:
                    vuong += [f"{b}: {v}" for v in _dung_lai(cn, b, SINH["DDL"][f"{ten}.{b}"],
                                                          {**DIEN.get(ten, {}).get(b, {}), **dien_them.get(b, {})},
                                                          SINH["BO_COT"].get(ten, {}).get(b, []))]
                except sqlite3.IntegrityError as e:   # thông báo SQLite chỉ có loại ràng buộc và tên cột
                    vuong.append(f"{b}: {str(e).replace('__moi', '')}")
            so_fk = len(cn.execute("PRAGMA foreign_key_check").fetchall())
            if so_fk:
                vuong.append(f"{so_fk:02d} dòng trỏ tới dòng không có")
            for b, c in SINH["AIBAM"].get(ten, []):
                if c not in {r[1] for r in cn.execute(f"PRAGMA table_info({b})")}:
                    continue
                for cu, moi in doi.items():
                    tong_doi += cn.execute(f"UPDATE {b} SET {c} = ? WHERE {c} = ?", (moi, cu)).rowcount
                n = cn.execute(f"SELECT count(*) FROM {b} WHERE {c} IS NOT NULL AND NOT aibam_hople({c})").fetchone()[0]
                if n:
                    la.append(f"{ten}.{b}.{c} {n:02d} dòng")
        finally:
            cn.close()
        ghi(3, not vuong, f"Dựng thử bản 3 file {ten}: " + ("không vướng" if not vuong else "; ".join(vuong)))
    ghi(4, not la, f"Giá trị \"ai bấm\": {_so(tong_doi)} dòng giá trị cũ sẽ đổi ('anh', tên đăng nhập chủ → mã tài khoản;"
                   f" 'lenh_vps' → 'hethong'); giá trị lạ: " + ("00" if not la else ", ".join(la)))

    # (5) chỗ trống ổ: bản chụp tự động của lần nâng + bản chụp tay trước khi cập nhật
    co = sum(f.stat().st_size for ten in CAC_FILE for f in thumuc.glob(f"{ten}.sqlite3*"))
    trong = shutil.disk_usage(thumuc).free
    ghi(5, trong >= 3 * co, f"Ổ dữ liệu: 07 file {_so(co / 1e6, 1)} MB, còn trống {_so(trong / 1e6)} MB (cần ≥ 03 lần)")

    # (6) mã trống ở bảng có phiên bản (QĐ142, QĐ143), đếm ở bước dựng thử (3)
    so_bang = sum(len(ds) for ds in SINH["BANG_PHIENBAN"].values())
    ghi(6, not ma_trong, f"Mã trống ở {_so(so_bang)} bảng có phiên bản (cần 00; còn thì lần nâng dừng): "
                         + ("00 dòng" if not ma_trong else ", ".join(ma_trong)))
    return dat, dong


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # in tiếng Việt đúng cả khi đưa qua đường ống, cửa sổ không UTF-8
    thumuc = Path(argv[0] if argv else "/dulieu")
    try:
        dat, dong = kiem(thumuc)
    except Exception as e:  # noqa: BLE001 - lỗi chạy: in loại lỗi, không in dữ liệu
        print(f"LỖI CHẠY BƯỚC KIỂM: {type(e).__name__}: {e}")
        return 2
    print("===== KIỂM TRƯỚC KHI NÂNG LƯỢC ĐỒ BẢN 3 (chỉ đọc) =====")
    print("\n".join(dong))
    print("KẾT QUẢ:", "ĐẠT, nâng được" if dat else "DỪNG, chưa cập nhật; gửi nguyên kết quả này cho CPO")
    return 0 if dat else 1


if __name__ == "__main__":
    sys.exit(main())
