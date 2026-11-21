-- Lược đồ file Baomat.sqlite3: 05 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- F01 Người dùng: 01 dòng = 01 người dùng
CREATE TABLE IF NOT EXISTS nguoidung (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  vaitro TEXT CHECK (vaitro IS NULL OR vaitro IN ('chu', 'nhanvien')),
  module_xem TEXT,
  matkhau_bam TEXT,
  totp_khoa_id TEXT REFERENCES kekhoa(id),
  nhanvien_id TEXT
);

-- F02 Quyền: 01 dòng = 01 đối tượng được cấp quyền
CREATE TABLE IF NOT EXISTS quyen (
  id TEXT PRIMARY KEY NOT NULL,
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('ketnoi', 'congcu', 'lenhcon', 'terminal')),
  doituong_ma TEXT,
  ketnoi_id TEXT,
  muc TEXT CHECK (muc IS NULL OR muc IN ('chidoc', 'ghiantoan', 'toanquyen')),
  can_anh_duyet INTEGER,
  luat_lenhcon_json TEXT,
  nguoi_dat TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT
);

-- F03 Két khoá: 01 dòng = 01 khoá
CREATE TABLE IF NOT EXISTS kekhoa (
  id TEXT PRIMARY KEY NOT NULL,
  dichvu TEXT,
  ketnoi_id TEXT,
  banma BLOB,
  kytu_cuoi TEXT,
  han TEXT,
  lan_dung_cuoi TEXT,
  nguoi_nhap TEXT,
  trangthai TEXT
);

-- F05 Phiên truy cập: 01 dòng = 01 phiên đăng nhập hoặc 01 mã truy cập
CREATE TABLE IF NOT EXISTS phien_truycap (
  id TEXT PRIMARY KEY NOT NULL,
  nguoidung_id TEXT REFERENCES nguoidung(id),
  loai TEXT CHECK (loai IS NULL OR loai IN ('phien_web', 'ma_truycap')),
  mabam TEXT,
  tao_luc TEXT,
  het_han TEXT,
  lan_dung_cuoi TEXT,
  thuhoi_luc TEXT
);

-- F06 Link chia sẻ: 01 dòng = 01 link chia sẻ
CREATE TABLE IF NOT EXISTS link_chiase (
  id TEXT PRIMARY KEY NOT NULL,
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('baocao', 'chiso', 'bangdieuhanh')),
  doituong_id TEXT,
  mabam TEXT,
  het_han TEXT,
  matkhau_bam TEXT,
  so_luot_xem INTEGER,
  luot_xem_cuoi TEXT,
  nguoi_tao TEXT,
  tao_luc TEXT,
  thuhoi_luc TEXT
);
