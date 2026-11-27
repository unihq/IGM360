-- Lược đồ file Viecnen.sqlite3: 19 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- G01 Cộng sự: 01 dòng = 01 cộng sự AI × phiên bản
CREATE TABLE IF NOT EXISTS congsu (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  vaitro TEXT,
  module TEXT,
  cachlam TEXT,
  kynang_ids TEXT,
  congcu_ids TEXT,
  mohinh_id TEXT REFERENCES mohinh_ai(id),
  nguon_ai_id TEXT REFERENCES nguon_ai(id),
  ngansach_thang INTEGER,
  chude_ids TEXT,
  muc_quyen_toida INTEGER
);

-- G02 Việc nền: 01 dòng = 01 lần chạy việc nền
CREATE TABLE IF NOT EXISTS viecnen (
  id TEXT PRIMARY KEY NOT NULL,
  loai TEXT,
  congsu_id TEXT REFERENCES congsu(id),
  nhiemvu_id TEXT,
  team_luot_id TEXT REFERENCES team_luot(id),
  quytrinh_lanchay_id TEXT REFERENCES quytrinh_lanchay(id),
  buoc_so INTEGER,
  goi_ai INTEGER CHECK (goi_ai IS NULL OR goi_ai IN (0, 1)),
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('tao', 'chothulai', 'dangchay', 'xong', 'huy', 'hong')),
  hen_chay_luc TEXT,
  khoa_chongtrung TEXT,
  so_lan_thu INTEGER,
  thu_toida INTEGER,
  giu_boi TEXT,
  giu_den TEXT,
  phuthuoc_json TEXT,
  ketqua_json TEXT,
  loi TEXT,
  tao_luc TEXT,
  batdau_luc TEXT,
  xong_luc TEXT
);

-- G03 Cách lấy số: 01 dòng = 01 cách lấy số đã nhớ của 01 việc định kỳ
CREATE TABLE IF NOT EXISTS cach_layso (
  id TEXT PRIMARY KEY NOT NULL,
  lich_id TEXT REFERENCES lich_dinhky(id),
  tieuchi_xong TEXT,
  cach_layso TEXT,
  so_lan_giong INTEGER,
  trangthai TEXT,
  cap_nhat_luc TEXT
);

-- G05 Sự cố: 01 dòng = 01 sự cố
CREATE TABLE IF NOT EXISTS suco (
  id TEXT PRIMARY KEY NOT NULL,
  viecnen_id TEXT REFERENCES viecnen(id),
  loi TEXT,
  da_thulai INTEGER,
  da_bao_anh INTEGER,
  cach_sua TEXT,
  trangthai TEXT,
  tao_luc TEXT,
  dong_luc TEXT
);

-- G06 Nguồn AI: 01 dòng = 01 nguồn AI
CREATE TABLE IF NOT EXISTS nguon_ai (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  loai TEXT CHECK (loai IS NULL OR loai IN ('goi', 'khoa_api', 'tuchay')),
  hanmuc INTEGER,
  tran_tien_thang INTEGER,
  dungchung INTEGER CHECK (dungchung IS NULL OR dungchung IN (0, 1)),
  uutien INTEGER,
  tyle_5gio INTEGER,
  tyle_tuan INTEGER,
  datlai_5gio_luc TEXT,
  datlai_tuan_luc TEXT,
  do_luc TEXT,
  da_het_luc INTEGER,
  hang TEXT NOT NULL,
  cach_goi TEXT NOT NULL CHECK (cach_goi IN ('cli', 'anthropic', 'openai')),
  diachi_goc TEXT,
  goi_ten TEXT,
  giahan_ngay TEXT,
  giahan_trangthai TEXT CHECK (giahan_trangthai IS NULL OR giahan_trangthai IN ('tudong', 'dahuy')),
  chuky TEXT CHECK (chuky IS NULL OR chuky IN ('thang', 'nam')),
  phi_ky INTEGER,
  phi_tien_ma TEXT,
  khoanchi_ma TEXT
);

-- G07 Lịch định kỳ: 01 dòng = 01 việc lặp lại
CREATE TABLE IF NOT EXISTS lich_dinhky (
  id TEXT PRIMARY KEY NOT NULL,
  ten TEXT,
  lap_lai TEXT,
  mui_gio TEXT,
  viec_mau_json TEXT,
  congsu_id TEXT REFERENCES congsu(id),
  lan_chay_ke TEXT,
  lan_chay_cuoi TEXT,
  trangthai TEXT,
  nguoi_tao TEXT
);

-- G08 Mô hình AI: 01 dòng = 01 mô hình của 01 nguồn
CREATE TABLE IF NOT EXISTS mohinh_ai (
  id TEXT PRIMARY KEY NOT NULL,
  nguon_ai_id TEXT REFERENCES nguon_ai(id),
  ma_mohinh TEXT,
  khanang_json TEXT,
  gia_vao INTEGER,
  gia_ra INTEGER,
  tien_ma TEXT,
  macdinh_cho_json TEXT,
  trangthai TEXT
);

-- G09 Team: 01 dòng = 01 team × phiên bản
CREATE TABLE IF NOT EXISTS team (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  muctieu TEXT,
  truongnhom_id TEXT REFERENCES congsu(id),
  cach_duyet TEXT CHECK (cach_duyet IS NULL OR cach_duyet IN ('moibuoc', 'cuoi'))
);

-- G10 Thành viên team: 01 dòng = 01 cộng sự trong 01 team
CREATE TABLE IF NOT EXISTS team_thanhvien (
  id TEXT PRIMARY KEY NOT NULL,
  team_id TEXT REFERENCES team(id),
  congsu_id TEXT REFERENCES congsu(id),
  vai TEXT,
  thutu INTEGER,
  hieuluc_tu TEXT,
  hieuluc_den TEXT
);

-- G11 Lượt team: 01 dòng = 01 lần team nhận việc
CREATE TABLE IF NOT EXISTS team_luot (
  id TEXT PRIMARY KEY NOT NULL,
  team_id TEXT REFERENCES team(id),
  team_phienban TEXT,
  nhiemvu_id TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dangchay', 'choduyet', 'xong', 'huy')),
  buoc_hientai INTEGER,
  ketqua TEXT,
  batdau_luc TEXT,
  xong_luc TEXT
);

-- G12 Bài học: 01 dòng = 01 bài học
CREATE TABLE IF NOT EXISTS baihoc (
  id TEXT PRIMARY KEY NOT NULL,
  phamvi TEXT CHECK (phamvi IS NULL OR phamvi IN ('congsu', 'shopchet')),
  congsu_id TEXT REFERENCES congsu(id),
  kynang_id TEXT REFERENCES kynang(id),
  tinhhuong TEXT,
  rutra TEXT,
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('loi', 'anh_sua', 'doichieu', 'duyet')),
  lydo_shopchet_id TEXT,
  nhiemvu_id TEXT,
  so_lan_apdung INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('choduyet', 'dangdung', 'bo')),
  nguoi_duyet TEXT,
  duyet_luc TEXT,
  tao_luc TEXT
);

-- G13 Kỹ năng: 01 dòng = 01 kỹ năng × phiên bản
CREATE TABLE IF NOT EXISTS kynang (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  mota_khinao TEXT,
  noidung TEXT,
  congsu_ids TEXT,
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('vietmoi', 'chuyen', 'caitien')),
  so_lan_dung INTEGER
);

-- G14 Quy trình: 01 dòng = 01 quy trình × phiên bản
CREATE TABLE IF NOT EXISTS quytrinh (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  cacbuoc_json TEXT,
  kichhoat TEXT CHECK (kichhoat IS NULL OR kichhoat IN ('tay', 'lich', 'webhook', 'sukien'))
);

-- G15 Lần chạy quy trình: 01 dòng = 01 lần chạy quy trình
CREATE TABLE IF NOT EXISTS quytrinh_lanchay (
  id TEXT PRIMARY KEY NOT NULL,
  quytrinh_id TEXT REFERENCES quytrinh(id),
  phienban INTEGER,
  kichhoat_boi TEXT,
  trangthai TEXT,
  buoc_hientai INTEGER,
  dauvao_json TEXT,
  ketqua_json TEXT,
  batdau_luc TEXT,
  xong_luc TEXT
);

-- G16 Núm tự chỉnh: 01 dòng = 01 núm tự chỉnh (F49 lớp 1)
CREATE TABLE IF NOT EXISTS num_tuchinh (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  ten TEXT,
  gioihan_duoi INTEGER,
  gioihan_tren INTEGER,
  macdinh INTEGER,
  giatri INTEGER,
  quytac TEXT,
  anh_giu_den TEXT,
  khoa_den TEXT,
  lan_doi_cuoi TEXT
);

-- G17 Lần đổi núm: 01 dòng = 01 lần đổi núm
CREATE TABLE IF NOT EXISTS num_thaydoi (
  id TEXT PRIMARY KEY NOT NULL,
  num_id TEXT REFERENCES num_tuchinh(id),
  tu TEXT,
  den TEXT,
  nguoi TEXT CHECK (nguoi IS NULL OR nguoi IN ('quytac', 'ai', 'anh')),
  lydo TEXT,
  luc TEXT,
  hoantac_boi_id TEXT
);

-- G18 Đề xuất cải tiến: 01 dòng = 01 đề xuất cải tiến
CREATE TABLE IF NOT EXISTS caitien_dexuat (
  id TEXT PRIMARY KEY NOT NULL,
  lop TEXT CHECK (lop IS NULL OR lop IN ('1', '2')),
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('congsu', 'kynang', 'team', 'quytrinh')),
  doituong_id TEXT,
  phienban_goc TEXT,
  noidung_moi TEXT,
  cancu_json TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'choanh', 'daapdung', 'tuchoi', 'hoantac')),
  cau_xacnhan TEXT,
  xacnhan_luc TEXT,
  thunghiem_id TEXT REFERENCES caitien_thunghiem(id),
  tao_luc TEXT
);

-- G19 Thử nghiệm cải tiến: 01 dòng = 01 thử nghiệm (F49 lớp 2)
CREATE TABLE IF NOT EXISTS caitien_thunghiem (
  id TEXT PRIMARY KEY NOT NULL,
  dexuat_id TEXT REFERENCES caitien_dexuat(id),
  ban_goc TEXT,
  ban_moi TEXT,
  boca_json TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho', 'dangchay', 'xong', 'huy')),
  nguon_ai_id TEXT REFERENCES nguon_ai(id),
  chiphi INTEGER,
  tien_ma TEXT,
  kichhoat_boi TEXT CHECK (kichhoat_boi IS NULL OR kichhoat_boi IN ('tudong', 'anh')),
  batdau_luc TEXT,
  xong_luc TEXT
);

-- G20 Kết quả thử nghiệm: 01 dòng = 01 tình huống × 01 bản
CREATE TABLE IF NOT EXISTS caitien_ketqua (
  id TEXT PRIMARY KEY NOT NULL,
  thunghiem_id TEXT REFERENCES caitien_thunghiem(id),
  ca_so TEXT,
  ban TEXT CHECK (ban IS NULL OR ban IN ('goc', 'moi')),
  dat INTEGER,
  diem INTEGER,
  chiphi INTEGER,
  thoigian_ms INTEGER,
  bangchung TEXT
);

-- H14 Mã phiên CLI (bản 4, PTD-10): 01 dòng = 01 mã phiên CLI của 01 đối tượng trên 01 tài khoản. Chỉ ghi thêm.
-- 01 nơi giữ mã phiên cho nối phiên trò chuyện (TC76) và cứu việc AI kẹt (QĐ95): G02 0 cột.
CREATE TABLE IF NOT EXISTS phien_cli (
  id TEXT PRIMARY KEY NOT NULL,
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('hoithoai', 'viecnen')),
  doituong_id TEXT,
  nguon_ai_id TEXT REFERENCES nguon_ai(id),
  loai TEXT CHECK (loai IS NULL OR loai IN ('claude', 'codex')),
  ma_phien TEXT,
  gan_luc TEXT,
  dong_luc TEXT
);

-- T01 Sổ sự việc (bản 5, QĐ96, QĐ632; Thietke mục 1.4): 01 dòng = 01 sự việc cho bộ não học. Chỉ ghi thêm qua 01 hàm;
-- ngoại lệ duy nhất 02 cột trangthai_xuly, xuly_luc đổi 01 chiều (trigger sv__suthat, sv__xuly – dulieu/suviec.py).
-- Không chép câu chữ: ghi mã bảng, mã dòng nguồn (QĐ98).
CREATE TABLE IF NOT EXISTS bn_suviec (
  id TEXT PRIMARY KEY NOT NULL,
  luc TEXT NOT NULL,
  loai TEXT NOT NULL,
  nguon_loai TEXT,
  bang_nguon TEXT,
  dong_nguon_id TEXT,
  khoa_chongtrung TEXT UNIQUE,
  bonao TEXT,
  doituong TEXT CHECK (doituong IS NULL OR doituong IN ('anh', 'nhanvien', 'khach', 'khong')),
  nguoi_id TEXT,
  co_dlcn INTEGER CHECK (co_dlcn IS NULL OR co_dlcn IN (0, 1)),
  shop_id TEXT,
  kenh_id TEXT,
  nhatky_ai_id TEXT,
  lydo_ma TEXT,
  lydo_chu TEXT,
  so_lan_sua INTEGER CHECK (so_lan_sua IS NULL OR so_lan_sua >= 0),
  trithuc_ma TEXT,
  danhgia TEXT CHECK (danhgia IS NULL OR danhgia IN ('co_ich', 'co_hai', 'trung_tinh')),
  moc_json TEXT,
  trangthai_xuly TEXT NOT NULL DEFAULT 'moi' CHECK (trangthai_xuly IN ('moi', 'dahoc', 'boqua')),
  xuly_luc TEXT
);
CREATE INDEX IF NOT EXISTS bn_suviec_bonao_luc ON bn_suviec (bonao, luc);
CREATE INDEX IF NOT EXISTS bn_suviec_cho ON bn_suviec (trangthai_xuly, loai);
CREATE INDEX IF NOT EXISTS bn_suviec_trithuc ON bn_suviec (trithuc_ma, loai);
