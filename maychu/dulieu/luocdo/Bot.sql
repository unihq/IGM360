-- Lược đồ file Bot.sqlite3: 11 bảng.
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- H01 Kênh nhắn: 01 dòng = 01 kênh nhắn (tên bảng kenh_nhan từ bản 3, QĐ109 L05)
CREATE TABLE IF NOT EXISTS kenh_nhan (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  loai TEXT,
  vai TEXT NOT NULL CHECK (vai IN ('anh_nhan_baocao', 'bot_giaoviec')),
  co_nutbam INTEGER,
  co_nhom INTEGER,
  cuaso_gui_gio INTEGER,
  ketnoi_id TEXT
);

-- H02 Thẻ duyệt: 01 dòng = 01 thẻ duyệt
CREATE TABLE IF NOT EXISTS the_duyet (
  id TEXT PRIMARY KEY NOT NULL,
  loai_viec TEXT CHECK (loai_viec IS NULL OR loai_viec IN ('cuacho', 'toanquyen', 'caitien')),
  doituong_id TEXT,
  ma_ngan TEXT,
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  han TEXT,
  ketqua TEXT CHECK (ketqua IS NULL OR ketqua IN ('duyet', 'tuchoi', 'hethan')),
  cau_traloi TEXT,
  traloi_luc TEXT
);

-- H03 Tin nhóm: 01 dòng = 01 tin hoặc file nhân viên gửi trong nhóm
CREATE TABLE IF NOT EXISTS tin_nhom (
  id TEXT PRIMARY KEY NOT NULL,
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  chude_id TEXT REFERENCES chude_nhom(id),
  nguoigui TEXT,
  nguoi_id TEXT,
  loai TEXT CHECK (loai IS NULL OR loai IN ('chu', 'file', 'anh', 'video', 'thoai')),
  noidung TEXT,
  giongnoi_id TEXT REFERENCES giongnoi_luot(id),
  nhiemvu_id TEXT,
  lonap_id TEXT,
  trangthai TEXT
);

-- H04 Chủ đề nhóm: 01 dòng = 01 chủ đề
CREATE TABLE IF NOT EXISTS chude_nhom (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  ma_nhom TEXT,
  module TEXT,
  congsu_id TEXT
);

-- H06 Lịch báo cáo: 01 dòng = 01 loại báo cáo
CREATE TABLE IF NOT EXISTS lich_baocao (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  gio_gui TEXT,
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  noidung_mau TEXT,
  lap_lai TEXT NOT NULL DEFAULT 'hangngay' CHECK (lap_lai IN ('hangngay', 'hangthang')),
  ngay_trongthang INTEGER CHECK (ngay_trongthang IS NULL OR ngay_trongthang BETWEEN 1 AND 31),
  gui_tin INTEGER NOT NULL DEFAULT 1 CHECK (gui_tin IN (0, 1)),
  CHECK (lap_lai <> 'hangthang' OR ngay_trongthang IS NOT NULL)
);

-- H07 Hội thoại: 01 dòng = 01 cuộc trò chuyện
CREATE TABLE IF NOT EXISTS hoithoai (
  id TEXT PRIMARY KEY NOT NULL,
  loai TEXT CHECK (loai IS NULL OR loai IN ('troly', 'chatbot')),
  nguoidung_id TEXT,
  congsu_id TEXT,
  chatbot_id TEXT REFERENCES chatbot(id),
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  tieude TEXT,
  tomtat TEXT,
  trangthai TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT
);

-- H08 Tin nhắn: 01 dòng = 01 tin trong 01 cuộc trò chuyện
CREATE TABLE IF NOT EXISTS tinnhan (
  id TEXT PRIMARY KEY NOT NULL,
  hoithoai_id TEXT REFERENCES hoithoai(id),
  vai TEXT CHECK (vai IS NULL OR vai IN ('nguoi', 'ai', 'hethong')),
  noidung TEXT,
  tep_json TEXT,
  giongnoi_id TEXT REFERENCES giongnoi_luot(id),
  nhatky_ai_id TEXT,
  luc TEXT
);

-- H09 Chatbot: 01 dòng = 01 chatbot × phiên bản
CREATE TABLE IF NOT EXISTS chatbot (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  kenhnhan_id TEXT REFERENCES kenh_nhan(id),
  congsu_id TEXT,
  nguon_trithuc_json TEXT,
  chinhsach_traloi TEXT,
  muc_tugui TEXT CHECK (muc_tugui IS NULL OR muc_tugui IN ('chi_dexuat', 'tugui_trongnguong'))
);

-- H10 Hộp kết quả: 01 dòng = 01 kết quả gửi về anh
CREATE TABLE IF NOT EXISTS hop_ketqua (
  id TEXT PRIMARY KEY NOT NULL,
  nguon_loai TEXT CHECK (nguon_loai IS NULL OR nguon_loai IN ('viecnen', 'quytrinh', 'theodoitrang', 'webhook', 'caitien')),
  nguon_id TEXT,
  tieude TEXT,
  tomtat TEXT,
  lienket TEXT,
  da_doc INTEGER,
  doc_luc TEXT,
  tao_luc TEXT
);

-- H11 Lượt giọng nói: 01 dòng = 01 lượt nghe hoặc đọc (F50 lớp 1)
CREATE TABLE IF NOT EXISTS giongnoi_luot (
  id TEXT PRIMARY KEY NOT NULL,
  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('nghe', 'doc')),
  tin_id TEXT,
  tep_id TEXT,
  nhacungcap TEXT,
  chu_nghe TEXT,
  chu_sau_sua TEXT,
  sua_json TEXT,
  thoiluong_giay INTEGER,
  chiphi INTEGER,
  tien_ma TEXT,
  ketqua TEXT CHECK (ketqua IS NULL OR ketqua IN ('dat', 'loi', 'chua_co_khoa')),
  luc TEXT
);

-- H12 Cuộc gọi: 01 dòng = 01 cuộc gọi thoại (F50 lớp 2)
CREATE TABLE IF NOT EXISTS cuoc_goi (
  id TEXT PRIMARY KEY NOT NULL,
  nguoidung_id TEXT,
  congsu_id TEXT,
  nhacungcap TEXT,
  hoithoai_id TEXT REFERENCES hoithoai(id),
  batdau_luc TEXT,
  ketthuc_luc TEXT,
  thoiluong_giay INTEGER,
  chiphi INTEGER,
  tien_ma TEXT,
  trangthai TEXT
);
