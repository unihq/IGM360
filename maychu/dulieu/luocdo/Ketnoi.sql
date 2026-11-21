-- Lược đồ file Ketnoi.sqlite3: 06 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- B08 Hộp tin nhận: 01 dòng = 01 tin báo nhận từ ngoài
CREATE TABLE IF NOT EXISTS hoptin (
  id TEXT PRIMARY KEY NOT NULL,
  nguon TEXT,
  ketnoi_id TEXT REFERENCES ketnoi(id),
  ma_sukien TEXT,
  loai_sukien TEXT,
  ma_don TEXT,
  nhan_luc TEXT,
  cach_kiem TEXT CHECK (cach_kiem IS NULL OR cach_kiem IN ('dauxacthuc', 'mabimat_duongdan')),
  ketqua_kiem TEXT CHECK (ketqua_kiem IS NULL OR ketqua_kiem IN ('dat', 'khongdat')),
  noidung_json TEXT,
  da_goilai INTEGER,
  goilai_luc TEXT,
  lonap_id TEXT,
  trung INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangxuly', 'xong', 'loi')),
  so_lan_thu INTEGER
);

-- K01 Kết nối: 01 dòng = 01 tài khoản kết nối
CREATE TABLE IF NOT EXISTS ketnoi (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  mau_ketnoi TEXT,
  cach_noi TEXT CHECK (cach_noi IS NULL OR cach_noi IN ('ketnoi_chinhthuc', 'file_xuatsan', 'trangweb', 'webhook_vao')),
  shop_id TEXT,
  khoa_id TEXT,
  trangthai_phien TEXT,
  lan_battay_cuoi TEXT,
  so_congcu_thay INTEGER,
  loi_cuoi TEXT
);

-- K02 Lịch lấy dữ liệu: 01 dòng = 01 loại dữ liệu × 01 kết nối
CREATE TABLE IF NOT EXISTS lich_lay (
  id TEXT PRIMARY KEY NOT NULL,
  ketnoi_id TEXT REFERENCES ketnoi(id),
  loai_dulieu TEXT,
  nhip TEXT,
  lan_lay_cuoi TEXT,
  lan_doichieu_cuoi TEXT,
  trangthai TEXT
);

-- K03 Lệnh đẩy ra sàn: 01 dòng = 01 lệnh đẩy ra sàn
CREATE TABLE IF NOT EXISTS lenh_day (
  id TEXT PRIMARY KEY NOT NULL,
  ketnoi_id TEXT REFERENCES ketnoi(id),
  loai TEXT,
  thamso_json TEXT,
  the_duyet_id TEXT,
  ketqua TEXT,
  nhiemvu_lamtay_id TEXT,
  tao_luc TEXT
);

-- K04 Webhook: 01 dòng = 01 webhook × phiên bản
CREATE TABLE IF NOT EXISTS webhook (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('vao', 'ra')),
  duongdan TEXT,
  khoa_id TEXT,
  cach_kiem TEXT,
  quytac_json TEXT,
  viec_gan TEXT,
  thu_lai TEXT
);

-- K05 Theo dõi trang: 01 dòng = 01 trang được theo dõi
CREATE TABLE IF NOT EXISTS theodoi_trang (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  diachi TEXT,
  vung_theodoi TEXT,
  nhip TEXT,
  lan_xem_cuoi TEXT,
  mabam_cuoi TEXT,
  bao_ve TEXT
);
