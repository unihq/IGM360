-- Lược đồ file Dulieu_Chinh.sqlite3: 54 bảng (bản 3: thêm A18 Sổ người, QĐ108).
-- Sinh từ thiết kế cơ sở dữ liệu đã duyệt; sửa thiết kế thì sinh lại, không sửa tay.

-- A01 Công ty: 01 dòng = 01 pháp nhân
CREATE TABLE IF NOT EXISTS congty (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  tien_goc INTEGER
);

-- A02 Kênh bán: 01 dòng = 01 kênh bán
CREATE TABLE IF NOT EXISTS kenh (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  loai TEXT
);

-- A03 Shop: 01 dòng = 01 shop × 01 khoảng hiệu lực
CREATE TABLE IF NOT EXISTS shop (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  congty_id TEXT REFERENCES congty(id),
  kenh_id TEXT REFERENCES kenh(id),
  thitruong TEXT,
  tien_ma TEXT,
  ky_tcong INTEGER,
  taikhoan_ban_id TEXT REFERENCES taikhoan(id),
  ma_trensan TEXT
);

-- A04 Vòng đời shop: 01 dòng = 01 lần shop đổi trạng thái
CREATE TABLE IF NOT EXISTS vongdoi_shop (
  id TEXT PRIMARY KEY NOT NULL,
  shop_id TEXT REFERENCES shop(id),
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('chuanbi', 'dangban', 'bihanche', 'chet')),
  tu_luc TEXT,
  lydo_chinh_id TEXT REFERENCES lydo_shopchet(id),
  lydo_phu_id TEXT REFERENCES lydo_shopchet(id),
  shop_thaythe_id TEXT REFERENCES shop(id),
  nhiemvu_khangnghi_id TEXT REFERENCES nhiemvu(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('anh', 'bot_dexuat')),
  nguoi_ghi TEXT,
  anhchup_chiso_json TEXT
);

-- A05 Lý do shop chết: 01 dòng = 01 lý do
CREATE TABLE IF NOT EXISTS lydo_shopchet (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  nhom TEXT
);

-- A06 Kho: 01 dòng = 01 kho
CREATE TABLE IF NOT EXISTS kho (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  quocgia TEXT,
  ma_kho_pancake TEXT
);

-- A07 SKU: 01 dòng = 01 SKU hoặc combo × hiệu lực
CREATE TABLE IF NOT EXISTS sku (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  ma_hienthi TEXT,
  donvi TEXT,
  nganhhang TEXT,
  vongdoi TEXT CHECK (vongdoi IS NULL OR vongdoi IN ('thu', 'chuluc', 'ngung')),
  loai TEXT CHECK (loai IS NULL OR loai IN ('hang', 'combo', 'qua_kemdieukien', 'qua_khongdieukien', 'baobi')),
  dinhmuc_baobi INTEGER,
  ngay_batdau_ban TEXT
);

-- A08 Barcode: 01 dòng = 01 barcode gắn 01 SKU trong 01 khoảng hiệu lực
CREATE TABLE IF NOT EXISTS barcode (
  id TEXT PRIMARY KEY NOT NULL,
  hieuluc_tu TEXT NOT NULL,
  hieuluc_den TEXT,
  nguoi_khai TEXT,
  tao_luc TEXT,
  barcode TEXT,
  sku_id TEXT REFERENCES sku(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('nhacungcap', 'noibo'))
);

-- A09 Combo thành phần: 01 dòng = 01 SKU thành phần trong 01 combo × hiệu lực
CREATE TABLE IF NOT EXISTS combo_thanhphan (
  id TEXT PRIMARY KEY NOT NULL,
  hieuluc_tu TEXT NOT NULL,
  hieuluc_den TEXT,
  nguoi_khai TEXT,
  tao_luc TEXT,
  combo_id TEXT REFERENCES sku(id),
  sku_id TEXT REFERENCES sku(id),
  so_chiec INTEGER
);

-- A10 Ghép mã ngoài: 01 dòng = 01 mã ngoài của 01 nguồn
CREATE TABLE IF NOT EXISTS ghep_mangoai (
  id TEXT PRIMARY KEY NOT NULL,
  hieuluc_tu TEXT NOT NULL,
  hieuluc_den TEXT,
  nguoi_khai TEXT,
  tao_luc TEXT,
  nguon TEXT,
  shop_id TEXT REFERENCES shop(id),
  ma_ngoai TEXT,
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('sku', 'combo', 'taikhoan', 'kho', 'shop', 'nguoi')),
  doituong_id TEXT
);

-- A11 Tài khoản: 01 dòng = 01 tài khoản
CREATE TABLE IF NOT EXISTS taikhoan (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  loai TEXT CHECK (loai IS NULL OR loai IN ('banhang', 'quangcao', 'nganhang')),
  shop_id TEXT REFERENCES shop(id),
  tien_ma TEXT,
  phapnhan_dungten_id TEXT REFERENCES congty(id),
  sotk_4socuoi TEXT
);

-- A12 Tỷ giá theo ngày: 01 dòng = 01 cặp tiền × 01 loại giá × 01 ngày
CREATE TABLE IF NOT EXISTS tygia_ngay (
  id TEXT PRIMARY KEY NOT NULL,
  cap_tien TEXT,
  loai_gia TEXT,
  ngay TEXT,
  tygia INTEGER,
  nguon TEXT,
  la_giacu INTEGER CHECK (la_giacu IS NULL OR la_giacu IN (0, 1)),
  ngay_giagoc TEXT,
  nguoi_nhap TEXT,
  tao_luc TEXT
);

-- A13 Tỷ giá quản trị tháng: 01 dòng = 01 cặp tiền × 01 tháng
CREATE TABLE IF NOT EXISTS tygia_quantri (
  id TEXT PRIMARY KEY NOT NULL,
  cap_tien TEXT,
  thang TEXT,
  tygia INTEGER,
  nguon TEXT,
  nguoi_nhap TEXT,
  da_khoa INTEGER
);

-- A14 Nhà cung cấp: 01 dòng = 01 nhà cung cấp
CREATE TABLE IF NOT EXISTS nhacungcap (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  dieukhoan_tra TEXT,
  songay_no INTEGER,
  tien_ma TEXT
);

-- A15 Nhân viên: 01 dòng = 01 nhân viên
CREATE TABLE IF NOT EXISTS nhanvien (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  phongban TEXT,
  module_phutrach TEXT,
  kenh_chinh TEXT,
  kenh_duphong TEXT,
  nguoi_id TEXT NOT NULL REFERENCES nguoi(id),
  tinhtrang TEXT NOT NULL DEFAULT 'danglam' CHECK (tinhtrang IN ('danglam', 'danghi')),
  ngay_nghiviec TEXT
);

-- A16 Khoản chi: 01 dòng = 01 loại chi phí
CREATE TABLE IF NOT EXISTS khoanchi (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  nhom TEXT
);

-- A17 Khu vực: 01 dòng = 01 khu vực giao hàng
CREATE TABLE IF NOT EXISTS khuvuc (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  thitruong TEXT,
  tinh_bang TEXT,
  nhom_vung TEXT
);

-- A18 Sổ người: 01 dòng = 01 người (anh, nhân viên, sau này khách), giữ nguyên mãi; không tách phiên bản (QĐ108)
CREATE TABLE IF NOT EXISTS nguoi (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL UNIQUE CHECK (length(ma) = 7 AND ma GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
  ten TEXT NOT NULL,
  loai TEXT NOT NULL,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  trangthai_hoc TEXT NOT NULL DEFAULT 'chua_dongy' CHECK (trangthai_hoc IN ('chua_dongy', 'dang_hoc', 'dung_hoc')),
  lydo_dung_hoc TEXT CHECK (lydo_dung_hoc IS NULL OR lydo_dung_hoc IN ('rutlai', 'nghiviec')),
  trangthai_hoc_luc TEXT,
  co_dlcn INTEGER NOT NULL DEFAULT 0 CHECK (co_dlcn IN (0, 1)),
  gop_vao_id TEXT REFERENCES nguoi(id),
  nguoi_khai TEXT NOT NULL,
  tao_luc TEXT NOT NULL,
  CHECK (trangthai_hoc <> 'dung_hoc' OR lydo_dung_hoc IS NOT NULL)
);

-- B01 Lô nạp: 01 dòng = 01 lần nạp file hoặc 01 lần lấy từ kết nối
CREATE TABLE IF NOT EXISTS lonap (
  id TEXT PRIMARY KEY NOT NULL,
  loai_dulieu TEXT REFERENCES loai_module(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  ketnoi_id TEXT,
  thay_cho_lonap_id TEXT,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  ky_tu TEXT,
  ky_den TEXT,
  khuon_id TEXT,
  nguoi_nap TEXT CHECK (nguoi_nap IS NULL OR nguoi_nap IN ('anh', 'nhanvien', 'bot', 'viecnen')),
  nguoi_id TEXT REFERENCES nguoi(id),
  khoa_chongtrung TEXT,
  so_dong_doc INTEGER,
  so_dong_nhan INTEGER,
  so_dong_loi INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdoc', 'cho_xuly', 'xong', 'loaibo')),
  batdau_luc TEXT,
  xong_luc TEXT,
  tao_luc TEXT
);

-- B05 Loại dữ liệu → module: 01 dòng = 01 loại dữ liệu
CREATE TABLE IF NOT EXISTS loai_module (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  module_soluong TEXT,
  module_giatri TEXT,
  duong_vao TEXT CHECK (duong_vao IS NULL OR duong_vao IN ('A', 'B', 'C', 'D'))
);

-- B07 Cửa chờ xử lý: 01 dòng = 01 việc chờ xử lý
CREATE TABLE IF NOT EXISTS cuacho (
  id TEXT PRIMARY KEY NOT NULL,
  bang_nguon TEXT,
  dong_nguon_id TEXT,
  lonap_id TEXT REFERENCES lonap(id),
  loai_loi TEXT,
  loi TEXT,
  muc_xuly TEXT CHECK (muc_xuly IS NULL OR muc_xuly IN ('ai_tuapdung', 'cho_anh')),
  dexuat_json TEXT,
  nhatky_ai_id TEXT,
  ketqua_dexuat TEXT CHECK (ketqua_dexuat IS NULL OR ketqua_dexuat IN ('duyet_nguyen', 'sua', 'tuchoi')),
  anhhuong_sotien INTEGER,
  tien_ma TEXT,
  tienle_id TEXT,
  han_xuly TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'choduyet', 'daxuly', 'hoantac')),
  the_duyet_id TEXT,
  nhiemvu_id TEXT REFERENCES nhiemvu(id),
  ketqua TEXT,
  nguoi_xuly TEXT,
  xuly_luc TEXT,
  tao_luc TEXT
);

-- C01 Đơn hàng: 01 dòng = 01 đơn
CREATE TABLE IF NOT EXISTS donhang (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  kenh_id TEXT REFERENCES kenh(id),
  ma_don_nguon TEXT,
  ma_don_pancake TEXT,
  nguon_don TEXT CHECK (nguon_don IS NULL OR nguon_don IN ('pancake', 'san', 'file')),
  khuvuc_id TEXT REFERENCES khuvuc(id),
  dat_luc TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdong', 'danggiao', 'giao_thanhcong', 'giao_thatbai', 'hoan', 'huy')),
  trangthai_nguon TEXT,
  giao_thanhcong_luc TEXT,
  doanhthu INTEGER,
  giamgia INTEGER,
  phisan INTEGER,
  UNIQUE (shop_id, ma_don_nguon)
);

-- C02 Dòng đơn: 01 dòng = 01 SKU hoặc combo trong 01 đơn
CREATE TABLE IF NOT EXISTS dongdon (
  id TEXT PRIMARY KEY NOT NULL,
  donhang_id TEXT REFERENCES donhang(id),
  dong_so INTEGER,
  ma_ngoai TEXT,
  sku_id TEXT REFERENCES sku(id),
  loai_dong TEXT CHECK (loai_dong IS NULL OR loai_dong IN ('hang', 'combo', 'qua_kemdieukien', 'qua_khongdieukien')),
  soluong_ban INTEGER,
  so_chiec_quydoi INTEGER,
  giaban INTEGER,
  giamgia INTEGER,
  doanhthu_dong INTEGER,
  giavon_dong INTEGER,
  nhan_giavon TEXT CHECK (nhan_giavon IS NULL OR nhan_giavon IN ('tam', 'that'))
);

-- C03 Vận đơn: 01 dòng = 01 lần đổi trạng thái giao của 01 kiện
CREATE TABLE IF NOT EXISTS vandon (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  donhang_id TEXT REFERENCES donhang(id),
  ma_vandon TEXT,
  donvi_vanchuyen TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho_lay', 'danggiao', 'giao_thanhcong', 'giao_thatbai', 'hoan_dangve', 'hoan_dave')),
  sukien_luc TEXT,
  phi_ship_di INTEGER,
  phi_ship_hoan INTEGER
);

-- C04 Sổ kho: 01 dòng = 01 lần thay đổi số lượng ở 01 ngăn
CREATE TABLE IF NOT EXISTS sokho (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  sku_id TEXT REFERENCES sku(id),
  kho_id TEXT REFERENCES kho(id),
  ngan TEXT CHECK (ngan IS NULL OR ngan IN ('taikho', 'danggiao', 'hoandangve', 'chokiem')),
  cap_id TEXT,
  so_chiec_doi INTEGER,
  so_con_ngan_sau INTEGER,
  so_con_tong_sau INTEGER,
  gia_vao INTEGER,
  gia_ra INTEGER,
  giabq_sau INTEGER,
  giatri_ton_sau INTEGER,
  chenh_giatri INTEGER,
  chungtu_id TEXT REFERENCES chungtukho(id),
  dongdon_id TEXT,
  xayra_luc TEXT,
  tao_luc TEXT,
  da_huy INTEGER,
  dong_dao_id TEXT,
  tinhlai_luc TEXT,
  ky TEXT,
  ky_goc TEXT
);

-- C05 Chứng từ kho: 01 dòng = 01 chứng từ
CREATE TABLE IF NOT EXISTS chungtukho (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  loai TEXT CHECK (loai IS NULL OR loai IN ('xuat_giao', 'nhap_hoan', 'bienban_hongmat', 'nhap_mua', 'tra_ncc', 'kiemke', 'chuyenkho')),
  so_chungtu TEXT,
  ngay TEXT,
  xayra_luc TEXT,
  kho_id TEXT REFERENCES kho(id),
  donhang_goc_id TEXT,
  vandon_ma TEXT,
  donmua_so TEXT,
  nguon_sinh TEXT CHECK (nguon_sinh IS NULL OR nguon_sinh IN ('pancake', 'igm360')),
  da_day_pancake INTEGER,
  nguoi_duyet TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('soan', 'ghiso', 'huy')),
  tongtien INTEGER
);

-- C06 Đơn mua: 01 dòng = 01 dòng hàng của 01 đơn mua
CREATE TABLE IF NOT EXISTS donmua (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  so_donmua TEXT,
  nhacungcap_id TEXT REFERENCES nhacungcap(id),
  sku_id TEXT REFERENCES sku(id),
  soluong_dat INTEGER,
  gia_nhap INTEGER,
  soluong_danhan INTEGER,
  ngay_dat TEXT,
  ngay_dukien TEXT,
  tiencoc INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('soan', 'dadat', 'nhan_motphan', 'nhan_du', 'huy'))
);

-- C07 Chi phí mua: 01 dòng = 01 khoản chi phí mua
CREATE TABLE IF NOT EXISTS chiphimua (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  so_donmua TEXT,
  chungtu_nhapmua_id TEXT REFERENCES chungtukho(id),
  loai TEXT,
  cach_phanbo TEXT CHECK (cach_phanbo IS NULL OR cach_phanbo IN ('theo_sochiec', 'theo_giatri')),
  vanban_id TEXT
);

-- C08 Công nợ phải trả: 01 dòng = 01 khoản phải trả
CREATE TABLE IF NOT EXISTS congno_phaitra (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('nhacungcap', 'quangcao')),
  nhacungcap_id TEXT REFERENCES nhacungcap(id),
  taikhoan_id TEXT REFERENCES taikhoan(id),
  chungtu_loai TEXT CHECK (chungtu_loai IS NULL OR chungtu_loai IN ('nhap_mua', 'chiphimua', 'hoadon_quangcao')),
  chungtu_id TEXT,
  phaitra INTEGER,
  datra INTEGER,
  tru_coc INTEGER,
  conno INTEGER,
  ngay_phatsinh TEXT,
  han_tra TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('chuatra', 'tra_motphan', 'datra'))
);

-- C09 Giao dịch tiền: 01 dòng = 01 lần tiền vào hoặc ra
CREATE TABLE IF NOT EXISTS giaodich_tien (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  taikhoan_id TEXT REFERENCES taikhoan(id),
  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('vao', 'ra')),
  loai TEXT,
  doituong_loai TEXT,
  doituong_id TEXT,
  congno_id TEXT REFERENCES congno_phaitra(id),
  tiensan_id TEXT REFERENCES tien_trensan(id),
  xayra_luc TEXT,
  ma_giaodich_nguon TEXT
);

-- C10 Tiền trên sàn: 01 dòng = 01 khoản quyết toán theo đơn hoặc theo kỳ
CREATE TABLE IF NOT EXISTS tien_trensan (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  donhang_id TEXT REFERENCES donhang(id),
  ma_quyettoan_nguon TEXT,
  khoan TEXT,
  sotien INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho_quyettoan', 'dave', 'bigiu')),
  ngay_dukien TEXT,
  ngay_ve TEXT,
  ngay_giu TEXT,
  lydo_giu TEXT,
  dukien_nha INTEGER,
  giaodich_tien_id TEXT REFERENCES giaodich_tien(id)
);

-- C11 Đối soát COD: 01 dòng = 01 dòng đối soát
CREATE TABLE IF NOT EXISTS doisoat_cod (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  donhang_id TEXT REFERENCES donhang(id),
  vandon_ma TEXT,
  donvi_vanchuyen TEXT,
  tien_thuho INTEGER,
  phi_vanchuyen INTEGER,
  phi_khac INTEGER,
  tien_thucnhan INTEGER,
  chenh INTEGER,
  ky_doisoat TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('khop', 'lech'))
);

-- C12 Quảng cáo, tiền tiêu: 01 dòng = 01 tài khoản quảng cáo × ngày × chiến dịch
CREATE TABLE IF NOT EXISTS quangcao_tieu (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  taikhoan_id TEXT REFERENCES taikhoan(id),
  ngay TEXT,
  ma_chiendich TEXT,
  ten_chiendich TEXT,
  tien_tieu INTEGER,
  ketqua_json TEXT
);

-- C13 Quảng cáo, nạp và hóa đơn: 01 dòng = 01 hóa đơn nạp
CREATE TABLE IF NOT EXISTS quangcao_nap (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  taikhoan_id TEXT REFERENCES taikhoan(id),
  so_hoadon TEXT,
  ngay TEXT,
  tien_truocthue INTEGER,
  tyle_thue INTEGER,
  tien_thue INTEGER,
  tong_gomthue INTEGER,
  khautru_dadung INTEGER CHECK (khautru_dadung IS NULL OR khautru_dadung IN (0, 1)),
  trangthai_tra TEXT CHECK (trangthai_tra IS NULL OR trangthai_tra IN ('datra', 'chuatra')),
  han_tra TEXT,
  congno_id TEXT REFERENCES congno_phaitra(id)
);

-- C14 Chỉ số shop: 01 dòng = 01 shop × ngày × chỉ số
CREATE TABLE IF NOT EXISTS chiso_shop (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  ngay TEXT,
  ma_chiso TEXT,
  giatri INTEGER,
  so_vipham INTEGER,
  vanban_id TEXT
);

-- C15 Chi phí chung: 01 dòng = 01 khoản chi
CREATE TABLE IF NOT EXISTS chiphi_chung (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  khoanchi_id TEXT REFERENCES khoanchi(id),
  cach_phanbo TEXT,
  phanbo_json TEXT,
  vanban_id TEXT,
  giaodich_tien_id TEXT REFERENCES giaodich_tien(id)
);

-- C16 Lương, nhân sự: 01 dòng = 01 nhân viên × tháng
CREATE TABLE IF NOT EXISTS luong_nhansu (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  thitruong TEXT,
  ky TEXT,
  ky_goc TEXT,
  tien_ma TEXT,
  sotien_nguyente INTEGER,
  sotien_quydoi INTEGER,
  tygia_id TEXT REFERENCES tygia_ngay(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),
  lonap_id TEXT REFERENCES lonap(id),
  banghigoc_id TEXT,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  tao_luc TEXT,
  nhanvien_id TEXT REFERENCES nhanvien(id),
  thang TEXT,
  luong INTEGER,
  thuong INTEGER,
  khac INTEGER,
  tong INTEGER,
  phanbo_json TEXT
);

-- C17 Kế hoạch, ngưỡng: 01 dòng = 01 chỉ số × kỳ × phạm vi
CREATE TABLE IF NOT EXISTS kehoach_nguong (
  id TEXT PRIMARY KEY NOT NULL,
  ma_chiso TEXT REFERENCES chiso(id),
  ky TEXT,
  phamvi_loai TEXT CHECK (phamvi_loai IS NULL OR phamvi_loai IN ('congty', 'kenh', 'shop', 'sku')),
  phamvi_id TEXT,
  kehoach INTEGER,
  nguong_canhbao INTEGER,
  chieu_canhbao TEXT CHECK (chieu_canhbao IS NULL OR chieu_canhbao IN ('duoi', 'tren')),
  nguoi_dat TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  tao_luc TEXT
);

-- C18 Kết quả thử SKU: 01 dòng = 01 SKU × 01 lần thử
CREATE TABLE IF NOT EXISTS thu_sku (
  id TEXT PRIMARY KEY NOT NULL,
  sku_id TEXT REFERENCES sku(id),
  lan_thu TEXT,
  shop_id TEXT REFERENCES shop(id),
  tu_ngay TEXT,
  den_ngay TEXT,
  ketqua_json TEXT,
  ketluan TEXT CHECK (ketluan IS NULL OR ketluan IN ('dat', 'khongdat', 'theodoi_them')),
  nguoi_ketluan TEXT,
  ghichu TEXT,
  tao_luc TEXT
);

-- C19 Giá vốn mỗi chiếc: 01 dòng = 01 SKU × 01 lần tính
CREATE TABLE IF NOT EXISTS giavon_chiec (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  sku_id TEXT REFERENCES sku(id),
  ky TEXT,
  loai_gia TEXT CHECK (loai_gia IS NULL OR loai_gia IN ('tam', 'that')),
  phuongphap TEXT,
  gia_chiec INTEGER,
  tien_ma TEXT,
  sokho_id TEXT,
  nguoi_khai TEXT,
  chenh_so_voi_tam INTEGER,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  tinh_luc TEXT
);

-- C20 Lớp điều chỉnh: 01 dòng = 01 trường đã sửa của 01 dòng
CREATE TABLE IF NOT EXISTS dieuchinh (
  id TEXT PRIMARY KEY NOT NULL,
  bang TEXT,
  dong_id TEXT,
  truong TEXT,
  giatri_cu TEXT,
  giatri_moi TEXT,
  lydo TEXT,
  nguoi_sua_loai TEXT CHECK (nguoi_sua_loai IS NULL OR nguoi_sua_loai IN ('anh', 'ai', 'nhanvien')),
  nguoi_sua_id TEXT REFERENCES nguoi(id),
  muc TEXT CHECK (muc IS NULL OR muc IN ('ai_tuapdung', 'anh_duyet')),
  cuacho_id TEXT REFERENCES cuacho(id),
  the_duyet_id TEXT,
  sua_luc TEXT,
  con_hieuluc INTEGER,
  hoantac_boi_id TEXT
);

-- C21 Kỳ chốt số: 01 dòng = 01 pháp nhân × 01 kỳ
CREATE TABLE IF NOT EXISTS ky_chotso (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  ky TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('mo', 'dachot')),
  tygia_quantri_id TEXT REFERENCES tygia_quantri(id),
  nguoi_chot TEXT,
  chot_luc TEXT,
  so_dong_chenh INTEGER,
  tao_luc TEXT
);

-- C22 Hồ sơ pháp lý: 01 dòng = 01 hồ sơ
CREATE TABLE IF NOT EXISTS hoso_phaply (
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
  shop_id TEXT REFERENCES shop(id),
  nhanhang TEXT,
  so_vanban TEXT,
  vanban_id TEXT,
  nguoi_duyet TEXT,
  duyet_luc TEXT
);

-- D01 Định nghĩa chỉ số: 01 dòng = 01 chỉ số × 01 phiên bản
CREATE TABLE IF NOT EXISTS chiso (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  nhom TEXT CHECK (nhom IS NULL OR nhom IN ('lai', 'tien', 'hang', 'ban', 'tmdt')),
  donvi TEXT CHECK (donvi IS NULL OR donvi IN ('tien', 'tyle', 'so', 'ngay')),
  ma_ham TEXT,
  mota_congthuc TEXT,
  cauhoi_quantri TEXT,
  module_lamchu TEXT,
  phamvi_chophep TEXT,
  ky_tinh TEXT CHECK (ky_tinh IS NULL OR ky_tinh IN ('ngay', 'tuan', 'thang')),
  chieu_tot TEXT CHECK (chieu_tot IS NULL OR chieu_tot IN ('tang', 'giam')),
  bang_nguon TEXT,
  quytac_du_ids TEXT,
  nhom_nhaycam TEXT CHECK (nhom_nhaycam IS NULL OR nhom_nhaycam IN ('loinhuan', 'luong', 'dongtien'))
);

-- D02 Kết quả chỉ số: 01 dòng = 01 chỉ số × kỳ × phạm vi × 01 lần tính
CREATE TABLE IF NOT EXISTS ketqua_chiso (
  id TEXT PRIMARY KEY NOT NULL,
  chiso_id TEXT REFERENCES chiso(id),
  chiso_phienban TEXT,
  congty_id TEXT REFERENCES congty(id),
  ky TEXT,
  phamvi_loai TEXT,
  phamvi_id TEXT,
  giatri INTEGER,
  tien_ma TEXT,
  ma_ham TEXT,
  phienban_phanmem TEXT,
  tyle_du INTEGER,
  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),
  nhan_giavon TEXT CHECK (nhan_giavon IS NULL OR nhan_giavon IN ('tam', 'that')),
  so_dong_cho INTEGER,
  tinh_luc TEXT,
  la_moinhat INTEGER
);

-- D03 Cảnh báo: 01 dòng = 01 lần vượt ngưỡng hoặc 01 sự kiện cần báo
CREATE TABLE IF NOT EXISTS canhbao (
  id TEXT PRIMARY KEY NOT NULL,
  loai TEXT CHECK (loai IS NULL OR loai IN ('chiso', 'sukien')),
  chiso_id TEXT REFERENCES chiso(id),
  ketqua_id TEXT REFERENCES ketqua_chiso(id),
  kehoach_id TEXT REFERENCES kehoach_nguong(id),
  nguong INTEGER,
  giatri INTEGER,
  chieu TEXT CHECK (chieu IS NULL OR chieu IN ('duoi', 'tren')),
  bang_nguon TEXT,
  dong_nguon_id TEXT,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  ky TEXT,
  khoa_chongtrung TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dabao', 'dagiao_task', 'dadong', 'boqua')),
  kenhnhan_id TEXT,
  dabao_luc TEXT,
  nhiemvu_id TEXT REFERENCES nhiemvu(id),
  dong_luc TEXT,
  lydo_dong TEXT,
  tao_luc TEXT
);

-- D04 Bản xuất: 01 dòng = 01 lần xuất dữ liệu
CREATE TABLE IF NOT EXISTS banxuat (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  loai_noidung TEXT CHECK (loai_noidung IS NULL OR loai_noidung IN ('baocao', 'chiso', 'bangdieuhanh')),
  ten_baocao TEXT,
  ky TEXT,
  boloc_json TEXT,
  dang TEXT CHECK (dang IS NULL OR dang IN ('excel', 'pdf', 'tinnhan')),
  nguoi_xuat TEXT,
  drive_file_id TEXT,
  mabam TEXT,
  xuat_luc TEXT
);

-- E01 Việc, mục tiêu: 01 dòng = 01 việc hoặc mục tiêu
CREATE TABLE IF NOT EXISTS viec_muctieu (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('canhbao', 'anh', 'cuacho', 'bot')),
  canhbao_id TEXT REFERENCES canhbao(id),
  chiso_id TEXT REFERENCES chiso(id),
  giatri_goc INTEGER,
  muctieu INTEGER,
  han TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('mo', 'dat', 'khongdat', 'huy')),
  nguoi_tao TEXT,
  tao_luc TEXT
);

-- E02 Nhiệm vụ: 01 dòng = 01 nhiệm vụ (thẻ Kanban)
CREATE TABLE IF NOT EXISTS nhiemvu (
  id TEXT PRIMARY KEY NOT NULL,
  viec_id TEXT REFERENCES viec_muctieu(id),
  tieude TEXT,
  mota TEXT,
  loai_nguoinhan TEXT NOT NULL CHECK (loai_nguoinhan IN ('anh', 'nhanvien', 'congsu')),
  nguoi_id TEXT REFERENCES nguoi(id),
  congsu_id TEXT,
  phongban TEXT,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho', 'danglam', 'chodoichieu', 'xong', 'huy')),
  uutien INTEGER,
  han TEXT,
  giatri_lucgiao INTEGER,
  muctieu INTEGER,
  ngay_dolai TEXT,
  ketqua_dolai TEXT,
  phuthuoc_json TEXT,
  lich_id TEXT,
  quytrinh_lanchay_id TEXT,
  team_luot_id TEXT,
  cuacho_id TEXT REFERENCES cuacho(id),
  the_duyet_id TEXT,
  tao_luc TEXT,
  xong_luc TEXT,
  CHECK ((loai_nguoinhan IN ('anh', 'nhanvien') AND nguoi_id IS NOT NULL AND congsu_id IS NULL)
      OR (loai_nguoinhan = 'congsu' AND congsu_id IS NOT NULL AND nguoi_id IS NULL))
);

-- E03 Sự kiện nhiệm vụ: 01 dòng = 01 sự kiện của 01 nhiệm vụ
CREATE TABLE IF NOT EXISTS nhiemvu_sukien (
  id TEXT PRIMARY KEY NOT NULL,
  nhiemvu_id TEXT REFERENCES nhiemvu(id),
  loai TEXT CHECK (loai IS NULL OR loai IN ('phanhoi', 'doitrangthai', 'binhluan', 'file', 'dolai')),
  noidung TEXT,
  tin_id TEXT,
  nguoi_loai TEXT CHECK (nguoi_loai IS NULL OR nguoi_loai IN ('anh', 'nhanvien', 'congsu', 'bot')),
  nguoi_id TEXT REFERENCES nguoi(id),
  congsu_id TEXT,
  luc TEXT
);

-- M02 Quy tắc kiểm đủ: 01 dòng = 01 quy tắc × 01 phiên bản
CREATE TABLE IF NOT EXISTS quytac_kiemdu (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT NOT NULL,
  ten TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  phienban INTEGER,
  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),
  nguoi_khai TEXT,
  tao_luc TEXT,
  loai_dulieu TEXT REFERENCES loai_module(id),
  kieu_kiem TEXT CHECK (kieu_kiem IS NULL OR kieu_kiem IN ('co_du_lieu', 'thieu_giatri', 'sai_giatri', 'trung', 'do_moi', 'du_doi_tuong')),
  bang TEXT,
  cot TEXT,
  boloc_json TEXT,
  nguong INTEGER,
  donvi_nguong TEXT CHECK (donvi_nguong IS NULL OR donvi_nguong IN ('dong', 'tyle', 'phut', 'gio', 'ngay')),
  phamvi_loai TEXT CHECK (phamvi_loai IS NULL OR phamvi_loai IN ('congty', 'shop')),
  ky_loai TEXT CHECK (ky_loai IS NULL OR ky_loai IN ('ngay', 'tuan', 'thang')),
  chiso_anhhuong TEXT,
  nguoi_duyet TEXT,
  duyet_luc TEXT
);

-- M03 Thiếu dữ liệu: 01 dòng = 01 lần phát hiện thiếu × phạm vi × kỳ
CREATE TABLE IF NOT EXISTS thieu_dulieu (
  id TEXT PRIMARY KEY NOT NULL,
  quytac_id TEXT,
  quytac_phienban TEXT,
  congty_id TEXT REFERENCES congty(id),
  shop_id TEXT REFERENCES shop(id),
  ky TEXT,
  thieu_gi TEXT,
  doituong_json TEXT,
  so_thieu INTEGER,
  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('dangthieu', 'dadu')),
  phathien_luc TEXT,
  da_nhac_anh INTEGER,
  nhac_luc TEXT,
  du_luc TEXT
);

-- P01 Thông số: 01 dòng = 01 thông số × 01 khoảng hiệu lực × 01 pháp nhân
CREATE TABLE IF NOT EXISTS thongso (
  id TEXT PRIMARY KEY NOT NULL,
  congty_id TEXT REFERENCES congty(id),
  ten TEXT,
  giatri TEXT,
  kieu TEXT CHECK (kieu IS NULL OR kieu IN ('so', 'chu', 'codong', 'danhsach')),
  donvi TEXT,
  hieuluc_tu TEXT,
  hieuluc_den TEXT,
  nguoi_dat TEXT,
  ghichu TEXT,
  tao_luc TEXT
);

-- P02 Điều kiện 02 nhánh: 01 dòng = 01 điều kiện của bảng rà 5.29
CREATE TABLE IF NOT EXISTS dieukien_2nhanh (
  id TEXT PRIMARY KEY NOT NULL,
  ma TEXT,
  dieukien TEXT,
  nhanh_a TEXT,
  nhanh_b TEXT,
  nhanh_dangchay TEXT CHECK (nhanh_dangchay IS NULL OR nhanh_dangchay IN ('A', 'B', 'chuakiem')),
  gd_kiem TEXT,
  ngay_kiem TEXT,
  ketqua TEXT,
  thongso_lienquan TEXT,
  cap_nhat_luc TEXT
);

-- D05 Đã đọc cảnh báo theo người (bản 4, PTD-06 B'): 01 dòng = 01 người đã đọc 01 cảnh báo
CREATE TABLE IF NOT EXISTS canhbao_doc (
  id TEXT PRIMARY KEY NOT NULL,
  canhbao_id TEXT REFERENCES canhbao(id),
  nguoi_id TEXT REFERENCES nguoi(id),
  doc_luc TEXT,
  UNIQUE (canhbao_id, nguoi_id)
);
