-- Lược đồ file Nhatky.sqlite3: 05 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- F04 Nhật ký thao tác: 01 dòng = 01 lần dùng công cụ, lệnh con hoặc lệnh terminal
CREATE TABLE IF NOT EXISTS nhatky_thaotac (
  id TEXT PRIMARY KEY NOT NULL,
  luc TEXT,
  nguoi_loai TEXT CHECK (nguoi_loai IS NULL OR nguoi_loai IN ('anh', 'congsu', 'viecnen', 'bot')),
  nguoi_id TEXT,
  congcu TEXT,
  lenhcon TEXT,
  thamso_tomtat TEXT,
  muc_quyen TEXT,
  ketqua TEXT CHECK (ketqua IS NULL OR ketqua IN ('dat', 'bichan', 'loi')),
  lydo_chan TEXT,
  thoigian_ms INTEGER,
  nhiemvu_id TEXT,
  viecnen_id TEXT
);

-- G04 Nhật ký dùng AI: 01 dòng = 01 lần gọi AI
CREATE TABLE IF NOT EXISTS nhatky_ai (
  id TEXT PRIMARY KEY NOT NULL,
  luc TEXT,
  nguon_ai_id TEXT,
  mohinh_id TEXT,
  viecnen_id TEXT,
  congsu_id TEXT,
  kynang_id TEXT,
  luong_vao INTEGER,
  luong_ra INTEGER,
  sotien INTEGER,
  sotien_thamkhao INTEGER,
  tien_ma TEXT,
  ketqua TEXT CHECK (ketqua IS NULL OR ketqua IN ('xong', 'loi', 'het_hanmuc', 'huy', 'quagio')),
  thoigian_ms INTEGER
);

-- H05 Nhật ký nói hoặc im: 01 dòng = 01 tin bot đã xét
CREATE TABLE IF NOT EXISTS nhatky_noihayim (
  id TEXT PRIMARY KEY NOT NULL,
  tin_id TEXT,
  quyetdinh TEXT CHECK (quyetdinh IS NULL OR quyetdinh IN ('noi', 'im')),
  lydo TEXT,
  luc TEXT
);

-- N01 Sao lưu: 01 dòng = 01 lần sao lưu 01 file
CREATE TABLE IF NOT EXISTS saoluu (
  id TEXT PRIMARY KEY NOT NULL,
  loai TEXT CHECK (loai IS NULL OR loai IN ('hangngay', 'camay_hangtuan')),
  file_dulieu TEXT,
  chup_luc TEXT,
  cach_chup TEXT CHECK (cach_chup IS NULL OR cach_chup IN ('backup_api', 'vacuum_into')),
  kiemtra TEXT,
  mabam TEXT,
  dungluong_byte INTEGER,
  noi_luu TEXT,
  ketqua_tungbuoc_json TEXT,
  ketqua TEXT
);

-- N02 Theo dõi máy chủ: 01 dòng = 01 lần đo (mỗi giờ)
CREATE TABLE IF NOT EXISTS theodoi_maychu (
  id TEXT PRIMARY KEY NOT NULL,
  luc TEXT,
  tyle_ocung INTEGER,
  ram_dung INTEGER,
  so_viec_dangchay INTEGER,
  so_viec_ai_dangchay INTEGER,
  thoigian_cho_ghi_ms INTEGER,
  swap_dung INTEGER
);
