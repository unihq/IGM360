"""Kiểm trước khi nâng lược đồ bản 2 → bản 3 (QĐ108, QĐ109; kế hoạch GĐ 1 ngày 10). CHỈ ĐỌC.

Chạy được bằng Python có sẵn trong container bản cũ (chỉ dùng thư viện chuẩn), không cần mã bản mới:

    curl -fsSL https://raw.githubusercontent.com/unihq/IGM360/<commit>/maychu/dulieu/kiemtruoc_ban3.py \\
      | docker compose exec -T igm360 python - /dulieu

Cách kiểm: mở 07 file ở chế độ chỉ đọc, chép sang bộ nhớ, chạy thử đúng các bước nâng bản 3 trên bản trong bộ nhớ
(đổi tên bảng, tạo bảng mới, dựng lại bảng theo lược đồ bản 3, đổi giá trị "ai bấm" cũ, kiểm khoá ngoại).
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
  "Dulieu_Chinh": [
   "nguoi"
  ]
 },
 "DDL": {
  "Baomat.nguoidung": "CREATE TABLE IF NOT EXISTS nguoidung (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  vaitro TEXT CHECK (vaitro IS NULL OR vaitro IN ('chu', 'nhanvien')),\n  module_xem TEXT,\n  matkhau_bam TEXT,\n  totp_khoa_id TEXT REFERENCES kekhoa(id),\n  nguoi_id TEXT NOT NULL UNIQUE\n);",
  "Bot.kenh_nhan": "CREATE TABLE IF NOT EXISTS kenh_nhan (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  loai TEXT,\n  vai TEXT NOT NULL CHECK (vai IN ('anh_nhan_baocao', 'bot_giaoviec')),\n  co_nutbam INTEGER,\n  co_nhom INTEGER,\n  cuaso_gui_gio INTEGER,\n  ketnoi_id TEXT\n);",
  "Bot.lich_baocao": "CREATE TABLE IF NOT EXISTS lich_baocao (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  gio_gui TEXT,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  noidung_mau TEXT,\n  lap_lai TEXT NOT NULL DEFAULT 'hangngay' CHECK (lap_lai IN ('hangngay', 'hangthang')),\n  ngay_trongthang INTEGER CHECK (ngay_trongthang IS NULL OR ngay_trongthang BETWEEN 1 AND 31),\n  gui_tin INTEGER NOT NULL DEFAULT 1 CHECK (gui_tin IN (0, 1)),\n  CHECK (lap_lai <> 'hangthang' OR ngay_trongthang IS NOT NULL)\n);",
  "Bot.tin_nhom": "CREATE TABLE IF NOT EXISTS tin_nhom (\n  id TEXT PRIMARY KEY NOT NULL,\n  kenhnhan_id TEXT REFERENCES kenh_nhan(id),\n  chude_id TEXT REFERENCES chude_nhom(id),\n  nguoigui TEXT,\n  nguoi_id TEXT,\n  loai TEXT CHECK (loai IS NULL OR loai IN ('chu', 'file', 'anh', 'video', 'thoai')),\n  noidung TEXT,\n  giongnoi_id TEXT REFERENCES giongnoi_luot(id),\n  nhiemvu_id TEXT,\n  lonap_id TEXT,\n  trangthai TEXT\n);",
  "Dulieu_Chinh.dieuchinh": "CREATE TABLE IF NOT EXISTS dieuchinh (\n  id TEXT PRIMARY KEY NOT NULL,\n  bang TEXT,\n  dong_id TEXT,\n  truong TEXT,\n  giatri_cu TEXT,\n  giatri_moi TEXT,\n  lydo TEXT,\n  nguoi_sua_loai TEXT CHECK (nguoi_sua_loai IS NULL OR nguoi_sua_loai IN ('anh', 'ai', 'nhanvien')),\n  nguoi_sua_id TEXT REFERENCES nguoi(id),\n  muc TEXT CHECK (muc IS NULL OR muc IN ('ai_tuapdung', 'anh_duyet')),\n  cuacho_id TEXT REFERENCES cuacho(id),\n  the_duyet_id TEXT,\n  sua_luc TEXT,\n  con_hieuluc INTEGER,\n  hoantac_boi_id TEXT\n);",
  "Dulieu_Chinh.donhang": "CREATE TABLE IF NOT EXISTS donhang (\n  id TEXT PRIMARY KEY NOT NULL,\n  congty_id TEXT REFERENCES congty(id),\n  shop_id TEXT REFERENCES shop(id),\n  thitruong TEXT,\n  ky TEXT,\n  ky_goc TEXT,\n  tien_ma TEXT,\n  sotien_nguyente INTEGER,\n  sotien_quydoi INTEGER,\n  tygia_id TEXT REFERENCES tygia_ngay(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),\n  lonap_id TEXT REFERENCES lonap(id),\n  banghigoc_id TEXT,\n  nhan_du TEXT CHECK (nhan_du IS NULL OR nhan_du IN ('du', 'tamtinh')),\n  tao_luc TEXT,\n  kenh_id TEXT REFERENCES kenh(id),\n  ma_don_nguon TEXT,\n  ma_don_pancake TEXT,\n  nguon_don TEXT CHECK (nguon_don IS NULL OR nguon_don IN ('pancake', 'san', 'file')),\n  khuvuc_id TEXT REFERENCES khuvuc(id),\n  dat_luc TEXT,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdong', 'danggiao', 'giao_thanhcong', 'giao_thatbai', 'hoan', 'huy')),\n  trangthai_nguon TEXT,\n  giao_thanhcong_luc TEXT,\n  doanhthu INTEGER,\n  giamgia INTEGER,\n  phisan INTEGER,\n  UNIQUE (shop_id, ma_don_nguon)\n);",
  "Dulieu_Chinh.ghep_mangoai": "CREATE TABLE IF NOT EXISTS ghep_mangoai (\n  id TEXT PRIMARY KEY NOT NULL,\n  hieuluc_tu TEXT NOT NULL,\n  hieuluc_den TEXT,\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  nguon TEXT,\n  shop_id TEXT REFERENCES shop(id),\n  ma_ngoai TEXT,\n  doituong_loai TEXT CHECK (doituong_loai IS NULL OR doituong_loai IN ('sku', 'combo', 'taikhoan', 'kho', 'shop', 'nguoi')),\n  doituong_id TEXT\n);",
  "Dulieu_Chinh.lonap": "CREATE TABLE IF NOT EXISTS lonap (\n  id TEXT PRIMARY KEY NOT NULL,\n  loai_dulieu TEXT REFERENCES loai_module(id),\n  nguon TEXT CHECK (nguon IS NULL OR nguon IN ('ketnoi', 'file', 'bot', 'nhaptay')),\n  ketnoi_id TEXT,\n  thay_cho_lonap_id TEXT,\n  congty_id TEXT REFERENCES congty(id),\n  shop_id TEXT REFERENCES shop(id),\n  ky_tu TEXT,\n  ky_den TEXT,\n  khuon_id TEXT,\n  nguoi_nap TEXT CHECK (nguoi_nap IS NULL OR nguoi_nap IN ('anh', 'nhanvien', 'bot', 'viecnen')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  khoa_chongtrung TEXT,\n  so_dong_doc INTEGER,\n  so_dong_nhan INTEGER,\n  so_dong_loi INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangdoc', 'cho_xuly', 'xong', 'loaibo')),\n  batdau_luc TEXT,\n  xong_luc TEXT,\n  tao_luc TEXT\n);",
  "Dulieu_Chinh.nguoi": "CREATE TABLE IF NOT EXISTS nguoi (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT NOT NULL UNIQUE CHECK (length(ma) = 7 AND ma GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),\n  ten TEXT NOT NULL,\n  loai TEXT NOT NULL,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  trangthai_hoc TEXT NOT NULL DEFAULT 'chua_dongy' CHECK (trangthai_hoc IN ('chua_dongy', 'dang_hoc', 'dung_hoc')),\n  lydo_dung_hoc TEXT CHECK (lydo_dung_hoc IS NULL OR lydo_dung_hoc IN ('rutlai', 'nghiviec')),\n  trangthai_hoc_luc TEXT,\n  co_dlcn INTEGER NOT NULL DEFAULT 0 CHECK (co_dlcn IN (0, 1)),\n  gop_vao_id TEXT REFERENCES nguoi(id),\n  nguoi_khai TEXT NOT NULL,\n  tao_luc TEXT NOT NULL,\n  CHECK (trangthai_hoc <> 'dung_hoc' OR lydo_dung_hoc IS NOT NULL)\n);",
  "Dulieu_Chinh.nhanvien": "CREATE TABLE IF NOT EXISTS nhanvien (\n  id TEXT PRIMARY KEY NOT NULL,\n  ma TEXT,\n  ten TEXT,\n  hieuluc_tu TEXT,\n  hieuluc_den TEXT,\n  phienban INTEGER,\n  trangthai TEXT NOT NULL DEFAULT 'dung' CHECK (trangthai IN ('dung', 'ngung')),\n  nguoi_khai TEXT,\n  tao_luc TEXT,\n  phongban TEXT,\n  module_phutrach TEXT,\n  kenh_chinh TEXT,\n  kenh_duphong TEXT,\n  nguoi_id TEXT NOT NULL UNIQUE REFERENCES nguoi(id),\n  tinhtrang TEXT NOT NULL DEFAULT 'danglam' CHECK (tinhtrang IN ('danglam', 'danghi')),\n  ngay_nghiviec TEXT\n);",
  "Dulieu_Chinh.nhiemvu": "CREATE TABLE IF NOT EXISTS nhiemvu (\n  id TEXT PRIMARY KEY NOT NULL,\n  viec_id TEXT REFERENCES viec_muctieu(id),\n  tieude TEXT,\n  mota TEXT,\n  loai_nguoinhan TEXT NOT NULL CHECK (loai_nguoinhan IN ('anh', 'nhanvien', 'congsu')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  congsu_id TEXT,\n  phongban TEXT,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('cho', 'danglam', 'chodoichieu', 'xong', 'huy')),\n  uutien INTEGER,\n  han TEXT,\n  giatri_lucgiao INTEGER,\n  muctieu INTEGER,\n  ngay_dolai TEXT,\n  ketqua_dolai TEXT,\n  phuthuoc_json TEXT,\n  lich_id TEXT,\n  quytrinh_lanchay_id TEXT,\n  team_luot_id TEXT,\n  cuacho_id TEXT REFERENCES cuacho(id),\n  the_duyet_id TEXT,\n  tao_luc TEXT,\n  xong_luc TEXT,\n  CHECK ((loai_nguoinhan IN ('anh', 'nhanvien') AND nguoi_id IS NOT NULL AND congsu_id IS NULL)\n      OR (loai_nguoinhan = 'congsu' AND congsu_id IS NOT NULL AND nguoi_id IS NULL))\n);",
  "Dulieu_Chinh.nhiemvu_sukien": "CREATE TABLE IF NOT EXISTS nhiemvu_sukien (\n  id TEXT PRIMARY KEY NOT NULL,\n  nhiemvu_id TEXT REFERENCES nhiemvu(id),\n  loai TEXT CHECK (loai IS NULL OR loai IN ('phanhoi', 'doitrangthai', 'binhluan', 'file', 'dolai')),\n  noidung TEXT,\n  tin_id TEXT,\n  nguoi_loai TEXT CHECK (nguoi_loai IS NULL OR nguoi_loai IN ('anh', 'nhanvien', 'congsu', 'bot')),\n  nguoi_id TEXT REFERENCES nguoi(id),\n  congsu_id TEXT,\n  luc TEXT\n);",
  "Hotho.banghigoc": "CREATE TABLE IF NOT EXISTS banghigoc (\n  id TEXT PRIMARY KEY NOT NULL,\n  lonap_id TEXT,\n  filegoc_id TEXT REFERENCES filegoc(id),\n  nguon TEXT,\n  loai_dulieu TEXT,\n  ma_doituong TEXT,\n  dong_trongfile TEXT,\n  lay_luc TEXT,\n  noidung_json TEXT,\n  mabam TEXT,\n  vitri_luu TEXT CHECK (vitri_luu IS NULL OR vitri_luu IN ('vps', 'drive')),\n  drive_goi_id TEXT,\n  UNIQUE (nguon, loai_dulieu, ma_doituong, mabam)\n);",
  "Hotho.filegoc": "CREATE TABLE IF NOT EXISTS filegoc (\n  id TEXT PRIMARY KEY NOT NULL,\n  lonap_id TEXT,\n  ten_file TEXT,\n  mabam_sha256 TEXT,\n  dungluong_byte INTEGER,\n  dinhdang TEXT,\n  noi_luu TEXT CHECK (noi_luu IS NULL OR noi_luu IN ('vps_tam', 'drive')),\n  drive_file_id TEXT,\n  trangthai_day TEXT CHECK (trangthai_day IS NULL OR trangthai_day IN ('cho_day', 'da_day', 'loi')),\n  nhan_luc TEXT,\n  day_luc TEXT,\n  nguoi_gui TEXT,\n  UNIQUE (mabam_sha256)\n);",
  "Ketnoi.hoptin": "CREATE TABLE IF NOT EXISTS hoptin (\n  id TEXT PRIMARY KEY NOT NULL,\n  nguon TEXT,\n  ketnoi_id TEXT REFERENCES ketnoi(id),\n  ma_sukien TEXT,\n  loai_sukien TEXT,\n  ma_don TEXT,\n  nhan_luc TEXT,\n  cach_kiem TEXT CHECK (cach_kiem IS NULL OR cach_kiem IN ('dauxacthuc', 'mabimat_duongdan')),\n  ketqua_kiem TEXT CHECK (ketqua_kiem IS NULL OR ketqua_kiem IN ('dat', 'khongdat')),\n  noidung_json TEXT,\n  da_goilai INTEGER,\n  goilai_luc TEXT,\n  lonap_id TEXT,\n  trung INTEGER,\n  trangthai TEXT CHECK (trangthai IS NULL OR trangthai IN ('moi', 'dangxuly', 'xong', 'loi')),\n  so_lan_thu INTEGER,\n  UNIQUE (nguon, ma_sukien)\n);"
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
   "lich_baocao"
  ],
  "Dulieu_Chinh": [
   "ghep_mangoai",
   "nhanvien",
   "lonap",
   "dieuchinh",
   "nhiemvu",
   "nhiemvu_sukien",
   "donhang"
  ],
  "Hotho": [
   "filegoc",
   "banghigoc"
  ],
  "Ketnoi": [
   "hoptin"
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


def _dung_lai(cn, bang, ddl, dien):
    """Giống khoitao._dung_lai: trả số dòng còn dữ liệu ở cột sắp bỏ (0 = không vướng)."""
    moi = f"{bang}__moi"
    cn.execute(ddl.replace(f"CREATE TABLE IF NOT EXISTS {bang} (", f"CREATE TABLE {moi} (", 1))
    cot_moi = cn.execute(f"PRAGMA table_info({moi})").fetchall()
    cot_cu = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
    vuong = []
    for c in sorted(cot_cu - {r[1] for r in cot_moi}):
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
    if all(b == 3 for b in ban.values()):
        ghi(1, True, f"Phiên bản lược đồ: {chu_ban}. Đã ở bản 3, không cần nâng")
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
    tong_doi, la = 0, []
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
            for b in SINH["DUNG_LAI"].get(ten, []):
                try:
                    vuong += [f"{b}: {v}" for v in _dung_lai(cn, b, SINH["DDL"][f"{ten}.{b}"], DIEN.get(ten, {}).get(b, {}))]
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
