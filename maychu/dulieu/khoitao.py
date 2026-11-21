"""Tạo 07 file dữ liệu và 104 bảng theo lược đồ trong `luocdo/`, nâng cấp file đã có lên bản mới.

Chạy lại nhiều lần không sao. Số phiên bản lược đồ ghi ở PRAGMA user_version của từng file
(không thêm bảng phụ).
- File mới (user_version 0): chạy nguyên lược đồ bản hiện hành.
- File bản cũ: chụp 01 bản sao trước khi nâng cấp, rồi dựng lại đúng các bảng đổi ở từng bản
  (tạo bảng mới theo lược đồ hiện hành, chép dữ liệu cột trùng tên, xoá bảng cũ, đổi tên),
  tất cả trong 01 giao dịch; lỗi thì trả nguyên trạng và báo lỗi.
"""
import os
import re
import sqlite3
from pathlib import Path

from maychu.dulieu import ketnoi

PHIENBAN_LUOCDO = 2
THUMUC_LUOCDO = Path(__file__).resolve().parent / "luocdo"

# Bảng phải dựng lại khi nâng lên từng bản (QĐ87 điểm A2, A3).
NANGCAP = {
    2: {
        "Bot": ["kenh"],                       # H01 `vai` bắt buộc có giá trị
        "Dulieu_Chinh": ["taikhoan", "barcode", "combo_thanhphan", "ghep_mangoai"],  # trạng thái, hiệu lực bắt buộc
        "Nhatky": ["theodoi_maychu"],          # N02 thêm `swap_dung`
    },
}


def _lay_ddl(ten: str, bang: str) -> str:
    sql = (THUMUC_LUOCDO / f"{ten}.sql").read_text(encoding="utf-8")
    m = re.search(rf"CREATE TABLE IF NOT EXISTS {bang} \(.*?\n\);", sql, re.S)
    if not m:
        raise RuntimeError(f"lược đồ {ten} không có bảng {bang}")
    return m.group(0)


def _chup_truoc(cn: sqlite3.Connection, ten: str, thumuc: Path, ban: int) -> None:
    noi = thumuc / "saoluu" / f"truoc_nangcap_v{ban:02d}"
    noi.mkdir(parents=True, exist_ok=True)
    os.chmod(noi, 0o700)
    dich_duong = noi / f"{ten}.sqlite3"
    dich = sqlite3.connect(dich_duong)
    try:
        cn.backup(dich)
    finally:
        dich.close()
    os.chmod(dich_duong, 0o600)


def _dung_lai(cn: sqlite3.Connection, ten: str, bang: str) -> None:
    moi = f"{bang}__moi"
    cn.execute(_lay_ddl(ten, bang).replace(f"CREATE TABLE IF NOT EXISTS {bang} (", f"CREATE TABLE {moi} (", 1))
    cot_moi = cn.execute(f"PRAGMA table_info({moi})").fetchall()  # (stt, tên, kiểu, bắt buộc, mặc định, khoá chính)
    cot_cu = {r[1] for r in cn.execute(f"PRAGMA table_info({bang})")}
    chung = [r for r in cot_moi if r[1] in cot_cu]
    # Cột mới bắt buộc có mặc định: dòng cũ đang trống thì nhận mặc định; bắt buộc không mặc định mà trống thì báo lỗi.
    lay = [f"COALESCE({r[1]}, {r[4]})" if r[3] and r[4] is not None else r[1] for r in chung]
    cn.execute(f"INSERT INTO {moi} ({', '.join(r[1] for r in chung)}) SELECT {', '.join(lay)} FROM {bang}")
    cn.execute(f"DROP TABLE {bang}")
    cn.execute(f"ALTER TABLE {moi} RENAME TO {bang}")


def nang_cap(cn: sqlite3.Connection, ten: str, thumuc: Path, tu_ban: int) -> None:
    """Nâng 01 file từ `tu_ban` lên PHIENBAN_LUOCDO; mỗi bản 01 giao dịch."""
    for ban in range(tu_ban + 1, PHIENBAN_LUOCDO + 1):
        _chup_truoc(cn, ten, thumuc, ban)
        cn.execute("PRAGMA foreign_keys=OFF")
        try:
            cn.execute("BEGIN IMMEDIATE")
            try:
                for bang in NANGCAP.get(ban, {}).get(ten, []):
                    _dung_lai(cn, ten, bang)
                loi_noi = cn.execute("PRAGMA foreign_key_check").fetchall()
                if loi_noi:
                    raise RuntimeError(f"{ten}: {len(loi_noi)} dòng trỏ tới dòng không có")
                cn.execute(f"PRAGMA user_version={ban}")
                cn.execute("COMMIT")
            except Exception:
                cn.execute("ROLLBACK")
                raise
        finally:
            cn.execute("PRAGMA foreign_keys=ON")


def tao_mot(ten: str, thumuc: Path) -> int:
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
            nang_cap(cn, ten, thumuc, ban)
        so = cn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        cn.close()
    if moi:
        os.chmod(duong, 0o600)
    return so


def tao_het(thumuc: Path | None = None) -> dict:
    """Tạo đủ 07 file. Trả về {tên file: số bảng}; lệch thiết kế thì báo lỗi."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    thumuc.mkdir(parents=True, exist_ok=True)
    ketqua = {ten: tao_mot(ten, thumuc) for ten in ketnoi.CAC_FILE}
    lech = {t: (so, ketnoi.SO_BANG[t]) for t, so in ketqua.items() if so != ketnoi.SO_BANG[t]}
    if lech:
        raise RuntimeError(f"số bảng lệch thiết kế: {lech}")
    return ketqua
