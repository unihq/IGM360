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
  ketnoi_id TEXT,
  nguoi_id TEXT
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
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dung', 'luutru', 'daxoa')),
  tao_luc TEXT,
  cap_nhat_luc TEXT,
  ghim_luc TEXT,
  ghim_thutu INTEGER,
  doc_luc TEXT,
  xoa_luc TEXT,
  luutru_luc TEXT,
  mohinh_ghim TEXT,
  nhom_id TEXT REFERENCES nhom_trochuyen(id),
  tomtat_den_tin_id TEXT REFERENCES tinnhan(id),
  tuychon_ghim_json TEXT
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
  luc TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('xong', 'dung', 'loi')),
  phu_json TEXT,
  tra_loi_cho TEXT REFERENCES tinnhan(id),
  kenh_nguon TEXT
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

-- ---------- Lược đồ bản 4 (0.8.0; QĐ204 PTD-10, QĐ229) ----------

-- H15 Project trò chuyện (gói 2): 01 dòng = 01 Project
CREATE TABLE IF NOT EXISTS nhom_trochuyen (
  id TEXT PRIMARY KEY NOT NULL,
  ten TEXT,
  icon TEXT,
  huongdan TEXT,
  ghim_luc TEXT,
  thutu INTEGER,
  nguoidung_id TEXT,
  trangthai TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT
);

-- H13 Dấu trên tin (gói 1): 01 dòng = 01 dấu trên 01 tin. Chỉ ghi thêm, gỡ = điền `go_luc`
CREATE TABLE IF NOT EXISTS tinnhan_dau (
  id TEXT PRIMARY KEY NOT NULL,
  tinnhan_id TEXT REFERENCES tinnhan(id),
  loai TEXT CHECK (loai IS NULL OR loai IN ('ghim', 'an_tua')),
  dat_luc TEXT,
  go_luc TEXT,
  nguoi_id TEXT
);

-- H16 Tài liệu gắn (gói 2): 01 dòng = 01 tài liệu gắn vào 01 Project hoặc 01 cuộc
CREATE TABLE IF NOT EXISTS tailieu_gan (
  id TEXT PRIMARY KEY NOT NULL,
  nhom_id TEXT REFERENCES nhom_trochuyen(id),
  hoithoai_id TEXT REFERENCES hoithoai(id),
  loai TEXT,
  filegoc_id TEXT,
  duongdan TEXT,
  mota TEXT,
  vai TEXT,
  ghim_luc TEXT,
  them_luc TEXT,
  go_luc TEXT
);

-- H17 Project đã học (gói 2): 01 dòng = 01 ghi chú Project đã học
CREATE TABLE IF NOT EXISTS nhom_dahoc (
  id TEXT PRIMARY KEY NOT NULL,
  nhom_id TEXT REFERENCES nhom_trochuyen(id),
  loai TEXT,
  noidung TEXT,
  nguon TEXT,
  hoithoai_id TEXT REFERENCES hoithoai(id),
  trangthai TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT
);

-- H18 Link chia sẻ cuộc trò chuyện (gói 3): 01 dòng = 01 link công khai của 01 cuộc
CREATE TABLE IF NOT EXISTS chiase_lienket (
  id TEXT PRIMARY KEY NOT NULL,
  hoithoai_id TEXT REFERENCES hoithoai(id),
  ma_lienket TEXT UNIQUE,
  duongdan_tuchon TEXT,
  nhan TEXT,
  moc_tin_id TEXT REFERENCES tinnhan(id),
  luotxem_json TEXT,
  nguoi_tao TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT,
  thuhoi_luc TEXT
);

-- H19 Mục tiêu /goal (gói 3): 01 dòng = 01 mục tiêu; mỗi vòng là 01 việc nền G02
CREATE TABLE IF NOT EXISTS muctieu (
  id TEXT PRIMARY KEY NOT NULL,
  hoithoai_id TEXT REFERENCES hoithoai(id),
  noidung TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dangchay', 'tamdung', 'dat', 'dung_tran', 'xoa')),
  so_vong INTEGER,
  tran_vong INTEGER,
  lydo_dung TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT
);

-- H20 Việc AI tự làm, hoàn tác được (gói 3): 01 dòng = 01 việc AI làm trong 01 lượt
CREATE TABLE IF NOT EXISTS tacdong_ai (
  id TEXT PRIMARY KEY NOT NULL,
  tinnhan_id TEXT REFERENCES tinnhan(id),
  loai TEXT,
  doituong_bang TEXT,
  doituong_id TEXT,
  truoc_json TEXT,
  sau_json TEXT,
  luc TEXT,
  hoantac_luc TEXT,
  hoantac_boi TEXT
);

-- H21 Cảm xúc, phản hồi trên tin (gói 3): 01 dòng = 01 cảm xúc của 01 người trên 01 tin
CREATE TABLE IF NOT EXISTS tinnhan_camxuc (
  id TEXT PRIMARY KEY NOT NULL,
  tinnhan_id TEXT REFERENCES tinnhan(id),
  nguoidung_id TEXT,
  bieutuong TEXT,
  ghichu TEXT,
  trangthai_xuly TEXT CHECK (trangthai_xuly IS NULL OR trangthai_xuly IN ('moi', 'dadieuchinh', 'khongcandoi')),
  xuly_ghichu TEXT,
  caitien_id TEXT,
  tao_luc TEXT,
  cap_nhat_luc TEXT
);

-- Cụm tìm chữ H08 (QĐ229, PTD-02 cách C): bảng nối số ↔ `id` tin (nối bằng `id`, không dựa `rowid` H08)
CREATE TABLE IF NOT EXISTS tinnhan_tim_noi (
  so INTEGER PRIMARY KEY,
  tin_id TEXT NOT NULL UNIQUE REFERENCES tinnhan(id)
);

-- Bảng ảo không giữ chữ: chỉ giữ từ đã tách; `rowid` = `tinnhan_tim_noi.so`. Ghi trong hàm ghi duy nhất (thiết kế 0.8 Q5)
CREATE VIRTUAL TABLE IF NOT EXISTS tinnhan_tim USING fts5(noidung, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');

-- Chỉ mục H08: đếm tin, đọc theo cuộc (TC95)
CREATE INDEX IF NOT EXISTS tinnhan_cuoc ON tinnhan (hoithoai_id, luc);
