-- Lược đồ file Hotho.sqlite3: 05 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- B02 File gốc: 01 dòng = 01 file
CREATE TABLE IF NOT EXISTS filegoc (
  id TEXT PRIMARY KEY NOT NULL,
  lonap_id TEXT,
  ten_file TEXT,
  mabam_sha256 TEXT,
  dungluong_byte INTEGER,
  dinhdang TEXT,
  noi_luu TEXT CHECK (noi_luu IS NULL OR noi_luu IN ('vps_tam', 'drive')),
  drive_file_id TEXT,
  trangthai_day TEXT CHECK (trangthai_day IS NULL OR trangthai_day IN ('cho_day', 'da_day', 'loi')),
  nhan_luc TEXT,
  day_luc TEXT,
  nguoi_gui TEXT,
  UNIQUE (mabam_sha256)
);

-- B03 Bản ghi gốc: 01 dòng = 01 bản ghi mỗi lần lấy về
CREATE TABLE IF NOT EXISTS banghigoc (
  id TEXT PRIMARY KEY NOT NULL,
  lonap_id TEXT,
  filegoc_id TEXT REFERENCES filegoc(id),
  nguon TEXT,
  loai_dulieu TEXT,
  ma_doituong TEXT,
  dong_trongfile TEXT,
  lay_luc TEXT,
  noidung_json TEXT,
  mabam TEXT,
  vitri_luu TEXT CHECK (vitri_luu IS NULL OR vitri_luu IN ('vps', 'drive')),
  drive_goi_id TEXT,
  UNIQUE (nguon, loai_dulieu, ma_doituong, mabam)
);

-- B04 Khuôn nhận diện: 01 dòng = 01 khuôn × 01 phiên bản
CREATE TABLE IF NOT EXISTS khuon (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  phienban INTEGER,
  loai_dulieu TEXT,
  nguon TEXT,
  bo_tieude_json TEXT,
  mabam_tieude TEXT,
  cach_tim_dong_tieude TEXT,
  anhxa_json TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dexuat', 'daduyet', 'ngung')),
  nguoi_duyet TEXT,
  duyet_luc TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT
);

-- B06 Văn bản: 01 dòng = 01 văn bản (đường D)
CREATE TABLE IF NOT EXISTS vanban (
  id TEXT PRIMARY KEY NOT NULL,
  filegoc_id TEXT REFERENCES filegoc(id),
  loai_vanban TEXT,
  ai_trich_json TEXT,
  nguon_ai_id TEXT,
  nhatky_ai_id TEXT,
  trangthai_duyet TEXT CHECK (trangthai_duyet IS NULL OR trangthai_duyet IN ('choduyet', 'daduyet', 'tuchoi')),
  cuacho_id TEXT,
  nguoi_duyet TEXT,
  duyet_luc TEXT
);

-- M01 Chờ đẩy Drive: 01 dòng = 01 file chờ đẩy lên Drive
CREATE TABLE IF NOT EXISTS cho_day_drive (
  id TEXT PRIMARY KEY NOT NULL,
  loai TEXT CHECK (loai IS NULL OR loai IN ('filegoc', 'goi_banghigoc', 'saoluu')),
  filegoc_id TEXT REFERENCES filegoc(id),
  saoluu_id TEXT,
  duongdan_tam TEXT,
  dungluong_byte INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho', 'dangday', 'xong', 'loi')),
  so_lan_thu INTEGER,
  lan_thu_ke TEXT,
  loi_ganhat TEXT,
  tao_luc TEXT,
  xong_luc TEXT
);
