-- Lược đồ file Baomat.sqlite3: 08 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- F01 Người dùng: 01 dòng = 01 người dùng
CREATE TABLE IF NOT EXISTS nguoidung (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  vaitro TEXT CHECK (vaitro IS NULL OR vaitro IN ('chu', 'nhanvien')),
  matkhau_bam TEXT,
  totp_khoa_id TEXT REFERENCES kekhoa(id),
  nguoi_id TEXT NOT NULL UNIQUE
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

-- F03 Két khóa: 01 dòng = 01 khóa
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
  thietbi TEXT,
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

-- F07 Vai trò: 01 dòng = 01 vai trò × 01 phiên bản (QĐ144; bảng có phiên bản thứ 30, mã bền QĐ142)
CREATE TABLE IF NOT EXISTS vaitro (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  mota TEXT,
  la_macdinh INTEGER NOT NULL DEFAULT 0 CHECK (la_macdinh IN (0, 1))
);

-- F08 Dòng quyền: 01 dòng = 01 vai trò × 01 đối tượng × 01 thao tác × 01 khoảng hiệu lực (chỉ dòng cho phép)
CREATE TABLE IF NOT EXISTS quyen_vaitro (
  id TEXT PRIMARY KEY NOT NULL,
  vaitro_ma TEXT NOT NULL,
  doituong_loai TEXT NOT NULL CHECK (doituong_loai IN ('man', 'nhom_nhaycam')),
  doituong_ma TEXT NOT NULL,
  thaotac TEXT NOT NULL CHECK (thaotac IN ('xem', 'nhap', 'sua', 'duyet', 'xuat', 'chiase')),
  phamvi_toida TEXT NOT NULL CHECK (phamvi_toida IN ('congty', 'shop', 'chinhminh')),
  nguoi_dat TEXT,
  tao_luc TEXT,
  hieuluc_tu TEXT NOT NULL,
  hieuluc_den TEXT,
  CHECK (doituong_loai <> 'nhom_nhaycam' OR doituong_ma IN ('loinhuan', 'luong', 'dongtien')),
  CHECK (NOT (doituong_loai = 'nhom_nhaycam' AND doituong_ma = 'luong' AND phamvi_toida = 'shop')),
  CHECK (NOT (doituong_loai = 'nhom_nhaycam' AND doituong_ma = 'luong' AND thaotac IN ('chiase', 'duyet')))
);

-- F09 Gán vai trò: 01 dòng = 01 tài khoản × 01 vai trò × 01 khoảng hiệu lực (không sửa đè)
CREATE TABLE IF NOT EXISTS gan_vaitro (
  id TEXT PRIMARY KEY NOT NULL,
  nguoidung_id TEXT NOT NULL REFERENCES nguoidung(id),
  vaitro_ma TEXT NOT NULL,
  phamvi_loai TEXT NOT NULL CHECK (phamvi_loai IN ('congty', 'shop', 'chinhminh')),
  phamvi_ma_json TEXT,
  nguoi_cap TEXT,
  cap_luc TEXT,
  hieuluc_tu TEXT NOT NULL,
  hieuluc_den TEXT,
  lydo TEXT
);
