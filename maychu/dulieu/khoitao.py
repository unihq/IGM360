"""Tạo 07 file dữ liệu và 118 bảng (+ cụm tìm chữ H08) theo lược đồ trong `luocdo/`, nâng cấp file đã có lên bản mới.

Chạy lại nhiều lần không sao. Số phiên bản lược đồ ghi ở PRAGMA user_version của từng file
(không thêm bảng phụ).
- File mới (user_version 0): chạy nguyên lược đồ bản hiện hành.
- File bản cũ: trước khi nâng, chụp bản sao CẢ 07 file vào `saoluu/truoc_nangcap_vNN/`. Mỗi file nâng thẳng
  lên bản hiện hành trong 01 giao dịch: tạo bảng mới, đổi tên bảng, dựng lại mỗi bảng đổi đúng 01 lần
  (tạo bảng theo lược đồ hiện hành, chép dữ liệu cột trùng tên, xóa bảng cũ, đổi tên), chạy bước điền dữ liệu.
  Cột bị bỏ mà còn dữ liệu thì dừng, không bỏ im lặng. Lỗi ở bất kỳ file nào: trả CẢ 07 file về bản sao
  (điều kiện CDA, QĐ108) rồi báo lỗi.
- Bản 4 (0.8.0; QĐ204 PTD-10, QĐ227, QĐ229; thiết kế mục 1.3): thêm cột thuần bằng `ALTER TABLE ADD COLUMN` (THEM_COT,
  F2: H08); câu `CREATE VIRTUAL TABLE`, `CREATE INDEX` của lược đồ chạy riêng sau bước dựng lại, thêm cột (V4: dựng lại
  bảng làm mất chỉ mục của bảng đó); H07 có `trangthai` lạ thì dừng nâng (K4b); N01 đổi dòng trước cập nhật của 0.7.9
  (QĐ227); dựng chỉ mục tìm chữ H08 từ tin cũ bằng đúng hàm đổi đ/Đ của phần mềm (`timchu`).
- Bản 5 (0.10.0; QĐ572, QĐ584, QĐ632; phiếu 16 mục 9.35–9.40; thiết kế mục 1.4): T01 `bn_suviec` mới (Viecnen); thêm
  09 cột cuối bảng (H07, H15 `bonao`; H16 04 cột bóc chữ, thay bản; C17 `ky_loai`; G04 `mohinh_thucchay`, `lydo`);
  D01 `chiso`, M02 `quytac_kiemdu` dựng lại để danh sách kỳ nhận thêm `quy`, `nam`. Trigger T01 tạo ở `_dong_khoitao`.
"""
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from maychu.dulieu import aibam, bonao, dsmorong, ketnoi, phienban, songuoi, suviec, timchu
from maychu.dulieu.saoluu import MUIGIO_VN

PHIENBAN_LUOCDO = 5
THUMUC_LUOCDO = Path(__file__).resolve().parent / "luocdo"

# Bảng phải dựng lại khi nâng lên từng bản (tên theo bản đó).
NANGCAP = {
    # Bản 2 (QĐ87, QĐ89): H01 `vai`, A08-A10 `hieuluc_tu` bắt buộc; `trangthai` của mọi bảng cột chung danh mục
    # bắt buộc, mặc định `dung`; N02 thêm `swap_dung`; F05 thêm `thietbi`. Danh sách sinh bằng máy khi so 02 bản lược đồ.
    2: {
        'Dulieu_Chinh': ['congty', 'kenh', 'shop', 'lydo_shopchet', 'kho', 'sku', 'barcode', 'combo_thanhphan', 'ghep_mangoai', 'taikhoan', 'nhacungcap', 'nhanvien', 'khoanchi', 'khuvuc', 'loai_module', 'hoso_phaply', 'chiso', 'quytac_kiemdu'],
        'Ketnoi': ['ketnoi', 'webhook', 'theodoi_trang'],
        'Viecnen': ['congsu', 'nguon_ai', 'team', 'kynang', 'quytrinh'],
        'Bot': ['kenh', 'chude_nhom', 'lich_baocao', 'chatbot'],
        'Nhatky': ['theodoi_maychu'],
        'Baomat': ['nguoidung', 'phien_truycap'],
    },
    # Bản 3 (QĐ108 A18, QĐ109 L01-L05, QĐ112, QĐ93 H06; thiết kế mục 1.2).
    3: {
        'Dulieu_Chinh': ['ghep_mangoai', 'nhanvien', 'lonap', 'dieuchinh', 'nhiemvu', 'nhiemvu_sukien',
                         'donhang',                  # ngày 08: L02 không trùng (shop_id, ma_don_nguon)
                         # Y18 (QĐ142, QĐ143): `ma` bắt buộc ở 29 bảng có phiên bản; A15 bỏ không trùng `nguoi_id`
                         'chiso', 'congty', 'hoso_phaply', 'kenh', 'kho', 'khoanchi', 'khuvuc', 'loai_module',
                         'lydo_shopchet', 'nhacungcap', 'quytac_kiemdu', 'shop', 'sku', 'taikhoan'],
        'Hotho': ['filegoc', 'banghigoc',             # ngày 08: L02 không trùng
                  'khuon'],                           # Y18
        'Ketnoi': ['hoptin',                          # ngày 08: L02 không trùng (nguon, ma_sukien); QĐ112
                   'ketnoi', 'theodoi_trang', 'webhook'],   # Y18
        'Viecnen': ['congsu', 'kynang', 'nguon_ai', 'quytrinh', 'team'],   # Y18
        'Bot': ['kenh_nhan',                          # ngày 09: L04 trangthai bắt buộc (sau khi đổi tên, L05)
                'tin_nhom', 'lich_baocao',
                'chatbot', 'chude_nhom'],             # Y18
        'Baomat': ['nguoidung'],
    },
    # Bản 4 (0.8.0, QĐ204 PTD-10; thiết kế mục 1.3): G06 +07 cột (PTD-07 A); H07 +09 cột + CHECK `trangthai`;
    # N01 CHECK `loai` thêm 'truoc_capnhat' (QĐ227). H08 không dựng lại: thêm cột ở THEM_COT (F2).
    4: {
        'Viecnen': ['nguon_ai'],
        'Bot': ['hoithoai'],
        'Nhatky': ['saoluu'],
    },
    # Bản 5 (0.10.0, QĐ572 II-2, II-3): D01 `ky_tinh`, M02 `ky_loai` thêm `quy`, `nam` – SQLite không sửa được CHECK
    # (CDA thử: danh sách cũ chặn `quy`) nên dựng lại; số dòng không được ít đi (SO_DONG_KIEM).
    5: {
        'Dulieu_Chinh': ['chiso', 'quytac_kiemdu'],
    },
}
# Bảng mới của từng bản (tạo theo lược đồ hiện hành trước khi dựng lại bảng khác).
BANG_MOI = {3: {'Dulieu_Chinh': ['nguoi'],
                'Baomat': ['vaitro', 'quyen_vaitro', 'gan_vaitro']},   # Y20c (QĐ144, QĐ155): F07-F09 rỗng
            # Bản 4: D05, H14, H13, H15–H21 rỗng; bảng nối cụm tìm chữ H08 (QĐ229). H15 trước H07, H16, H17 (khóa ngoại).
            4: {'Dulieu_Chinh': ['canhbao_doc'],
                'Viecnen': ['phien_cli'],
                'Bot': ['nhom_trochuyen', 'tinnhan_dau', 'tailieu_gan', 'nhom_dahoc', 'chiase_lienket', 'muctieu',
                        'tacdong_ai', 'tinnhan_camxuc', 'tinnhan_tim_noi']},
            # Bản 5: T01 sổ sự việc (QĐ96, QĐ632) rỗng.
            5: {'Viecnen': ['bn_suviec']}}
# Cột thêm bằng `ALTER TABLE ADD COLUMN` (F2, PTD-10 mục 13.3): chỉ khi thêm cột cho phép trống ở cuối bảng, không đổi
# ràng buộc cột cũ; giữ `rowid`, không chép bảng. {bản: {(file, bảng): [cột theo đúng thứ tự cuối lược đồ]}}
THEM_COT = {4: {('Bot', 'tinnhan'): ['trangthai', 'phu_json', 'tra_loi_cho', 'kenh_nguon']},
            # Bản 5 (phiếu 16 mục 9.39 (a)): 09 cột / 05 bảng, đều cho phép trống, thêm cuối bảng.
            5: {('Bot', 'hoithoai'): ['bonao'], ('Bot', 'nhom_trochuyen'): ['bonao'],
                ('Bot', 'tailieu_gan'): ['boc_trangthai', 'boc_ghichu', 'boc_luc', 'thay_cho_id'],
                ('Dulieu_Chinh', 'kehoach_nguong'): ['ky_loai'],
                ('Nhatky', 'nhatky_ai'): ['mohinh_thucchay', 'lydo']}}
# K4b: giá trị H07 `trangthai` nhận ở bản 4; dòng cũ ngoài danh sách thì dừng nâng, không đổi im lặng (như QĐ143).
TRANGTHAI_H07 = ('dung', 'luutru', 'daxoa')
# Số dòng ghi lại lúc nâng để "Kiểm sau cập nhật" so (K4): {file: [bảng]}.
SO_DONG_KIEM = {'Bot': ['hoithoai', 'tinnhan'], 'Viecnen': ['nguon_ai'], 'Nhatky': ['saoluu'],
                'Dulieu_Chinh': ['chiso', 'quytac_kiemdu']}   # bản 5: D01, M02 dựng lại
# Điền cột mới bắt buộc cho dòng cũ khi nâng bản 3: {(file, bảng): {cột: biểu thức}}. Biểu thức ra NULL thì dòng đó
# không nhận ra được: dừng nâng, không đoán (QĐ143). Y22a (QĐ161, PTD-05 mục 4 câu 06): G06 theo tiền tố mã cũ.
DIEN_BAN3 = {("Viecnen", "nguon_ai"): {
    "hang": "(CASE WHEN ma GLOB 'goi_claude_*' OR ma GLOB 'khoa_anthropic*' THEN 'anthropic'"
            " WHEN ma GLOB 'goi_chatgpt_*' OR ma GLOB 'khoa_openai*' THEN 'openai' END)",
    "cach_goi": "(CASE WHEN ma GLOB 'goi_claude_*' OR ma GLOB 'goi_chatgpt_*' THEN 'cli'"
                " WHEN ma GLOB 'khoa_anthropic*' THEN 'anthropic' WHEN ma GLOB 'khoa_openai*' THEN 'openai' END)",
}}
# Cột được bỏ có chủ đích khi còn dữ liệu (ngoài danh sách này, cột sắp bỏ còn dữ liệu thì dừng nâng).
BO_COT = {3: {('Baomat', 'nguoidung'): ['module_xem']}}   # Y20c (QĐ144, QĐ155): quyền màn chuyển sang F08
# Bảng đổi tên ở từng bản: {(file, tên cũ): tên mới}.
DOI_TEN: dict[int, dict[tuple[str, str], str]] = {
    3: {('Bot', 'kenh'): 'kenh_nhan'},  # L05 (QĐ109): H01 không trùng tên A02 `kenh` khi gắn thêm file đọc chéo
}


def _lay_ddl(ten: str, bang: str) -> str:
    sql = (THUMUC_LUOCDO / f"{ten}.sql").read_text(encoding="utf-8")
    m = re.search(rf"CREATE TABLE IF NOT EXISTS {bang} \(.*?\n\);", sql, re.S)
    if not m:
        raise RuntimeError(f"lược đồ {ten} không có bảng {bang}")
    return m.group(0)


def _cot_ddl(ten: str, bang: str, cot: str) -> str:
    """Phần khai báo 01 cột (`<cột> <kiểu, ràng buộc>`) lấy ở câu tạo bảng của lược đồ hiện hành."""
    m = re.search(rf"^\s+({cot} [^\n]*?),?$", _lay_ddl(ten, bang), re.M)
    if not m:
        raise RuntimeError(f"lược đồ {ten}.{bang} không có cột {cot}")
    return m.group(1)


def _cau_phu(ten: str) -> list[str]:
    """V4: câu `CREATE VIRTUAL TABLE`, `CREATE INDEX` của lược đồ (`_lay_ddl` chỉ đọc `CREATE TABLE`)."""
    sql = (THUMUC_LUOCDO / f"{ten}.sql").read_text(encoding="utf-8")
    return re.findall(r"^CREATE (?:VIRTUAL TABLE|UNIQUE INDEX|INDEX) IF NOT EXISTS [^;]*;", sql, re.M)


def _them_cot(cn: sqlite3.Connection, ten: str, bang: str, cac_cot: list[str]) -> None:
    """F2: thêm cột cuối bảng, bỏ qua cột đã có (chạy lại không sao)."""
    co = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
    for cot in cac_cot:
        if cot not in co:
            cn.execute(f"ALTER TABLE {bang} ADD COLUMN {_cot_ddl(ten, bang, cot)}")


def _ban4_truoc(cn: sqlite3.Connection, ten: str) -> None:
    """Chạy trong giao dịch nâng bản 4, trước khi dựng lại bảng. K4b: H07 `trangthai` lạ thì dừng (không in giá trị)."""
    if ten == "Bot":
        ds = ", ".join(f"'{g}'" for g in TRANGTHAI_H07)
        so = cn.execute(f"SELECT count(*) FROM hoithoai WHERE trangthai IS NOT NULL AND trangthai NOT IN ({ds})").fetchone()[0]
        if so:
            raise RuntimeError(f"Bot.hoithoai: {so} dòng trangthai ngoài {', '.join(TRANGTHAI_H07)}; dừng nâng (K4b)")


def _ban4_sau(cn: sqlite3.Connection, ten: str) -> None:
    """Chạy trong giao dịch nâng bản 4, sau khi dựng lại, thêm cột, tạo bảng ảo, chỉ mục."""
    if ten == "Nhatky":   # QĐ227: dòng trước cập nhật của 0.7.9 (`hangngay` + `dip`) đổi sang `truoc_capnhat`
        cn.execute("UPDATE saoluu SET loai = 'truoc_capnhat' WHERE loai = 'hangngay'"
                   " AND json_valid(ketqua_tungbuoc_json) AND json_extract(ketqua_tungbuoc_json, '$.dip') = 'truoc_capnhat'")
    if ten == "Bot":      # QĐ229, V5: chỉ mục tìm chữ dựng từ H08 cũ bằng đúng hàm đổi đ/Đ (PTD-02 Q8)
        timchu.dung_lai(cn)


def _ten_moi(ten: str, bang: str, tu_ban: int) -> str:
    for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
        bang = DOI_TEN.get(ban, {}).get((ten, bang), bang)
    return bang


def _dung_lai(cn: sqlite3.Connection, ten: str, bang: str, dien: dict[str, str] | None = None,
              duoc_bo: tuple = ()) -> None:
    """Dựng lại 01 bảng theo lược đồ hiện hành. `dien`: {cột mới: biểu thức SQL} để điền cột mới cho dòng cũ.
    `duoc_bo`: cột bỏ có chủ đích (BO_COT), bỏ cả khi còn dữ liệu."""
    dien = dien or {}
    moi = f"{bang}__moi"
    cn.execute(_lay_ddl(ten, bang).replace(f"CREATE TABLE IF NOT EXISTS {bang} (", f"CREATE TABLE {moi} (", 1))
    cot_moi = cn.execute(f"PRAGMA table_info({moi})").fetchall()  # (stt, tên, kiểu, bắt buộc, mặc định, khóa chính)
    cot_cu = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
    bo = cot_cu - {r[1] for r in cot_moi}
    for c in sorted(bo - set(duoc_bo)):
        so = cn.execute(f"SELECT count(*) FROM {bang} WHERE {c} IS NOT NULL").fetchone()[0]
        if so:
            raise RuntimeError(f"{ten}.{bang}: cột {c} sắp bỏ còn {so} dòng có dữ liệu, không bỏ được")
    chung = [r for r in cot_moi if r[1] in cot_cu or r[1] in dien]
    # Cột bắt buộc có mặc định: dòng cũ đang trống thì nhận mặc định; bắt buộc không mặc định mà trống thì báo lỗi.
    lay = []
    for r in chung:
        bt = dien.get(r[1], r[1])
        lay.append(f"COALESCE({bt}, {r[4]})" if r[3] and r[4] is not None else bt)
    cn.execute(f"INSERT INTO {moi} ({', '.join(r[1] for r in chung)}) SELECT {', '.join(lay)} FROM {bang}")
    cn.execute(f"DROP TABLE {bang}")
    cn.execute(f"ALTER TABLE {moi} RENAME TO {bang}")


# ---------- Bước điền dữ liệu riêng của bản 3 (QĐ108) ----------

def _gan_file(cn: sqlite3.Connection, ten: str, bidanh: str, thumuc: Path) -> bool:
    duong = ketnoi.duongdan(ten, thumuc)
    if not duong.exists():
        return False
    cn.execute(f"ATTACH DATABASE ? AS {bidanh}", (str(duong),))
    return True


def _ban3_truoc(cn: sqlite3.Connection, ten: str, co_bm: bool) -> dict[str, dict[str, str]]:
    """Chạy trong giao dịch nâng bản 3, trước khi dựng lại bảng. Trả {bảng: {cột: biểu thức điền}}."""
    if ten == "Dulieu_Chinh" and co_bm:
        # Tạo dòng A18 của anh trước, nối với tài khoản chủ F01 đang có (điều kiện CDA).
        chu = cn.execute("SELECT ten, ma FROM bm.nguoidung WHERE vaitro = 'chu' ORDER BY tao_luc LIMIT 1").fetchone()
        if chu and not songuoi.id_cua_anh(cn):
            songuoi.them(cn, chu[0] or chu[1], "anh", "hethong")
    them = {b: dict(d) for (t, b), d in DIEN_BAN3.items() if t == ten}
    for bang, dien in them.items():
        for cot, bt in dien.items():
            so = cn.execute(f"SELECT count(*) FROM {bang} WHERE {bt} IS NULL").fetchone()[0]
            if so:
                raise RuntimeError(f"{ten}.{bang}: {so} dòng không nhận ra {cot} theo mã cũ; dừng nâng (QĐ161)")
    if them:
        return them
    if ten == "Baomat":
        return {"nguoidung": {"nguoi_id": "(CASE WHEN vaitro = 'chu' THEN (SELECT id FROM dc.nguoi WHERE loai = 'anh'"
                                          " AND trangthai = 'dung' ORDER BY ma LIMIT 1) END)"}}
    return {}


def _doc_chu(thumuc: Path) -> tuple | None:
    """(id, ma, ten) tài khoản chủ cũ nhất ở F01 (đọc trước khi nâng); chưa có file hoặc chưa có tài khoản: None."""
    if not ketnoi.duongdan("Baomat", thumuc).exists():
        return None
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        return cn.execute("SELECT id, ma, ten FROM nguoidung WHERE vaitro = 'chu' ORDER BY tao_luc LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        cn.close()


def _doi_aibam(cn: sqlite3.Connection, ten: str, chu: tuple | None) -> int:
    """Bản 3 (QĐ108): đổi giá trị "ai bấm" cũ ở mọi cột "ai bấm" của file; còn giá trị lạ thì dừng nâng.
    Báo lỗi không in giá trị (có thể là tên đăng nhập), chỉ in bảng, cột, số dòng. Trả số dòng đã đổi."""
    doi = aibam.bang_doi_cu(chu)
    cn.create_function("aibam_hople", 1, lambda v: int(aibam.la_hop_le(v)), deterministic=True)
    so_doi = 0
    for bang, cot in aibam.cac_cot(ten):
        if cot not in {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}:
            continue
        for cu, moi in doi.items():
            so_doi += cn.execute(f"UPDATE {bang} SET {cot} = ? WHERE {cot} = ?", (moi, cu)).rowcount
        la = cn.execute(f"SELECT count(*) FROM {bang} WHERE {cot} IS NOT NULL AND NOT aibam_hople({cot})").fetchone()[0]
        if la:
            raise RuntimeError(f"{ten}.{bang}.{cot}: {la} dòng giá trị 'ai bấm' lạ (không phải mã tài khoản, mã máy,"
                               " 'anh', tên đăng nhập chủ, 'lenh_vps'); dừng nâng")
    return so_doi


def nang_cap(cn: sqlite3.Connection, ten: str, thumuc: Path, tu_ban: int, chu: tuple | None = None) -> None:
    """Nâng 01 file từ `tu_ban` thẳng lên PHIENBAN_LUOCDO trong 01 giao dịch. `chu`: tài khoản chủ (đọc trước)."""
    co_bm = ten == "Dulieu_Chinh" and _gan_file(cn, "Baomat", "bm", thumuc)
    co_dc = ten == "Baomat" and _gan_file(cn, "Dulieu_Chinh", "dc", thumuc)
    cn.execute("PRAGMA foreign_keys=OFF")
    try:
        cn.execute("BEGIN IMMEDIATE")
        try:
            for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
                for (t, cu), moi in DOI_TEN.get(ban, {}).items():
                    if t == ten:
                        cn.execute(f"ALTER TABLE {cu} RENAME TO {moi}")
                for bang in BANG_MOI.get(ban, {}).get(ten, []):
                    cn.execute(_lay_ddl(ten, bang))
            if tu_ban < 3:
                # QĐ142, QĐ143: `ma` bắt buộc ở bảng có phiên bản; dòng cũ mã trống thì dừng, không điền im lặng.
                trong = phienban.dem_ma_trong(cn)
                if trong:
                    raise RuntimeError(f"{ten}: {sum(trong.values())} dòng mã trống ở bảng "
                                       + ", ".join(f"{b} ({so})" for b, so in trong.items()) + "; dừng nâng (QĐ142)")
            dien = _ban3_truoc(cn, ten, co_bm) if tu_ban < 3 else {}
            if tu_ban < 4:
                _ban4_truoc(cn, ten)
            can = []
            for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
                for bang in NANGCAP.get(ban, {}).get(ten, []):
                    moi = _ten_moi(ten, bang, ban - 1)
                    if moi not in can:
                        can.append(moi)
            duoc_bo = {}
            for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
                for (t, b), ds in BO_COT.get(ban, {}).items():
                    if t == ten:
                        duoc_bo.setdefault(b, []).extend(ds)
            for bang in can:
                _dung_lai(cn, ten, bang, dien.get(bang), tuple(duoc_bo.get(bang, ())))
            for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
                for (t, b), cot in THEM_COT.get(ban, {}).items():
                    if t == ten:
                        _them_cot(cn, ten, b, cot)
            for cau in _cau_phu(ten):   # V4: bảng ảo, chỉ mục (kể cả chỉ mục của bảng vừa dựng lại)
                cn.execute(cau)
            if tu_ban < 3:
                _doi_aibam(cn, ten, chu)
            if tu_ban < 4:
                _ban4_sau(cn, ten)
            loi_noi = cn.execute("PRAGMA foreign_key_check").fetchall()
            if loi_noi:
                raise RuntimeError(f"{ten}: {len(loi_noi)} dòng trỏ tới dòng không có")
            cn.execute(f"PRAGMA user_version={PHIENBAN_LUOCDO}")
            cn.execute("COMMIT")
        except Exception:
            cn.execute("ROLLBACK")
            raise
    finally:
        cn.execute("PRAGMA foreign_keys=ON")
        for bd, co in (("bm", co_bm), ("dc", co_dc)):
            if co:
                cn.execute(f"DETACH DATABASE {bd}")


# ---------- Bản sao cả 07 file trước khi nâng, trả nguyên trạng khi lỗi ----------

def _thumuc_chup(thumuc: Path) -> Path:
    return thumuc / "saoluu" / f"truoc_nangcap_v{PHIENBAN_LUOCDO:02d}"


def _chup_het(thumuc: Path, cac_file) -> Path:
    noi = _thumuc_chup(thumuc)
    noi.mkdir(parents=True, exist_ok=True)
    os.chmod(noi, 0o700)
    for ten in cac_file:
        nguon = ketnoi.mo(ten, thumuc)
        dich_duong = noi / f"{ten}.sqlite3"
        dich = sqlite3.connect(dich_duong)
        try:
            nguon.backup(dich)
        finally:
            dich.close()
            nguon.close()
        os.chmod(dich_duong, 0o600)
    return noi


def _tra_nguyen_trang(thumuc: Path, cac_file) -> None:
    noi = _thumuc_chup(thumuc)
    for ten in cac_file:
        ban_chup = sqlite3.connect(noi / f"{ten}.sqlite3")
        dich = ketnoi.mo(ten, thumuc)
        try:
            ban_chup.backup(dich)
        finally:
            ban_chup.close()
            dich.close()


def _phienban(ten: str, thumuc: Path) -> int:
    if not ketnoi.duongdan(ten, thumuc).exists():
        return 0
    cn = ketnoi.mo(ten, thumuc)
    try:
        return cn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        cn.close()


# ---------- Dòng khởi tạo ----------

# H06: 03 dòng lịch theo QĐ93 (anh đổi giờ ở lịch màn 12).
LICH_KHOITAO = [
    ("lay_tygia_vcb", "Lấy tỷ giá Vietcombank", "09:00", "hangngay", None, 0),
    ("bao_chua_lay_tygia", "Báo chưa lấy được tỷ giá", "09:30", "hangngay", None, 1),
    ("nhac_khoa_tygia_thang", "Nhắc khóa tỷ giá tháng", "09:00", "hangthang", 1, 1),
]


def _dong_khoitao(cn: sqlite3.Connection, ten: str) -> None:
    cn.execute("BEGIN IMMEDIATE")
    try:
        if ten == "Dulieu_Chinh":
            # 20 thông số danh sách trước, rồi trigger kiểm danh sách mở rộng (thiết kế mục 0.6; QĐ109 L03).
            dsmorong.khoi_tao(cn)
            dsmorong.tao_trigger(cn)
        # Trigger chặn mã trống, chặn sửa `ma` ở mọi bảng có phiên bản (QĐ142, QĐ143). Bảng dựng lại khi nâng mất
        # trigger cũ, nên tạo lại ở đây sau cả 02 đường: file mới và file nâng.
        phienban.tao_trigger(cn)
        if ten == "Viecnen":   # QĐ632, L14: T01 chặn sửa 02 tầng; tạo lại sau mỗi lần nâng (như phienban.tao_trigger)
            suviec.tao_trigger(cn)
        if ten == "Bot":
            bay = datetime.now(MUIGIO_VN).isoformat(timespec="seconds")
            for ma, ten_lich, gio, lap, ngay, gui in LICH_KHOITAO:
                if not cn.execute("SELECT 1 FROM lich_baocao WHERE ma = ?", (ma,)).fetchone():
                    phienban.them(cn, "lich_baocao", {"ma": ma, "ten": ten_lich, "hieuluc_tu": bay[:10], "phienban": 1,
                                                      "nguoi_khai": "hethong", "tao_luc": bay, "gio_gui": gio,
                                                      "lap_lai": lap, "ngay_trongthang": ngay, "gui_tin": gui})
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise


def tao_mot(ten: str, thumuc: Path, chu: tuple | None = None) -> int:
    """Tạo hoặc nâng cấp 01 file; trả về số bảng đang có trong file."""
    duong = ketnoi.duongdan(ten, thumuc)
    moi = not duong.exists()
    cn = ketnoi.mo(ten, thumuc)
    try:
        ban = cn.execute("PRAGMA user_version").fetchone()[0]
        if ban == 0:
            cn.executescript((THUMUC_LUOCDO / f"{ten}.sql").read_text(encoding="utf-8"))
            cn.execute(f"PRAGMA user_version={PHIENBAN_LUOCDO}")
        elif ban < PHIENBAN_LUOCDO:
            nang_cap(cn, ten, thumuc, ban, chu)
        _dong_khoitao(cn, ten)
        so = cn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        cn.close()
    if moi:
        os.chmod(duong, 0o600)
    return so


def _noi_tiep_lan_bi_ngat(thumuc: Path) -> None:
    """0.7.9 lớp 2 (QĐ213): còn cờ "đang nâng" = lần nâng trước bị ngắt giữa chừng (mất điện, bị dừng). Trả nguyên
    trạng từ bản chụp của đúng lần đó rồi để `tao_het` nâng lại từ đầu; cờ của lược đồ khác thì chỉ bỏ cờ."""
    from maychu.hethong import antoan
    d = antoan.doc(thumuc).get("dang_nang")
    if not d:
        return
    noi = _thumuc_chup(thumuc)
    if d.get("den") != PHIENBAN_LUOCDO or not noi.is_dir():   # Y38c G5: không biết dữ liệu đang ở đâu → không tự nâng tiếp
        raise RuntimeError(f"lần nâng trước bị ngắt (lược đồ {d.get('den')}) mà không có bản chụp của lần đó")
    _tra_nguyen_trang(thumuc, [t for t in d.get("tep", []) if (noi / f"{t}.sqlite3").exists()])
    antoan.ghi(thumuc, dang_nang=None)


def _dem_dong(thumuc: Path, ban: dict) -> dict:
    """K4: số dòng các bảng ở SO_DONG_KIEM trước khi nâng (file chưa có hoặc bảng chưa có: bỏ qua)."""
    ra = {}
    for ten, cac_bang in SO_DONG_KIEM.items():
        if not ban.get(ten):
            continue
        cn = ketnoi.mo(ten, thumuc)
        try:
            co = {r[0] for r in cn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            for bang in cac_bang:
                if bang in co:
                    ra[f"{ten}.{bang}"] = cn.execute(f"SELECT count(*) FROM {bang}").fetchone()[0]
        finally:
            cn.close()
    return ra


def tao_het(thumuc: Path | None = None, bao=None) -> dict:
    """Tạo đủ 07 file. Trả về {tên file: số bảng}; lệch thiết kế thì trả nguyên trạng rồi báo lỗi.
    0.7.9 lớp 2: trước khi nâng ghi cờ "đang nâng" (tệp trạng thái, không phải bảng); nâng xong bỏ cờ."""
    from maychu.hethong import antoan
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    thumuc.mkdir(parents=True, exist_ok=True)
    _noi_tiep_lan_bi_ngat(thumuc)   # G5: cờ lạ → báo lỗi → khoidong vào chế độ an toàn (cờ giữ nguyên để soát)
    ban = {ten: _phienban(ten, thumuc) for ten in ketnoi.CAC_FILE}
    can_nang = any(0 < b < PHIENBAN_LUOCDO for b in ban.values())
    co_san = [t for t, b in ban.items() if b > 0]
    chu = _doc_chu(thumuc) if can_nang else None
    so_dong = _dem_dong(thumuc, ban) if can_nang else {}
    if can_nang:
        _chup_het(thumuc, co_san)
        luc = datetime.now(MUIGIO_VN).isoformat(timespec="seconds")
        antoan.ghi(thumuc, dang_nang={"tu": min(b for b in ban.values() if b > 0), "den": PHIENBAN_LUOCDO, "luc": luc,
                                      "tep": co_san}, chup_luc=luc)
    try:
        ketqua = {}
        for ten in ketnoi.CAC_FILE:
            ketqua[ten] = tao_mot(ten, thumuc, chu)
            if bao and can_nang:   # 0.8.1 (QĐ251) bước 7: đã nâng tệp i/07
                try:
                    bao(len(ketqua), len(ketnoi.CAC_FILE))
                except Exception:  # noqa: BLE001 - báo tiến độ lỗi không chặn nâng
                    pass
        lech = {t: (so, ketnoi.SO_BANG[t]) for t, so in ketqua.items() if so != ketnoi.SO_BANG[t]}
        if lech:   # 0.7.9: lệch số bảng cũng trả nguyên trạng (trước đây báo lỗi mà dữ liệu đã nâng dở)
            raise RuntimeError(f"số bảng lệch thiết kế: {lech}")
    except Exception:
        if can_nang:
            _tra_nguyen_trang(thumuc, co_san)
            antoan.ghi(thumuc, dang_nang=None)
        raise
    if can_nang:   # lớp 3: ghi lại bản nào đã nâng lược đồ, để nút quay về biết phải trả bản chụp (mất dữ liệu mới)
        from maychu.hethong import capnhat
        antoan.ghi(thumuc, dang_nang=None, nang_luocdo={"den": PHIENBAN_LUOCDO, "ban": capnhat.ban_dang_chay(), "luc": luc,
                                                        "so_dong": so_dong})   # K4: kiểm sau cập nhật so số dòng
    bonao.khoi_tao(thumuc)   # bản 5 (Đ-a, L03): thư mục bộ não + kho git `chung/` ngoài 07 tệp; chạy lại không sao
    return ketqua
