"""Sao lưu 07 file dữ liệu (thiết kế cơ sở dữ liệu mục 0.1), ghi kết quả vào N01.

Không bao giờ chép thẳng file đang chạy. Mỗi file 05 bước:
  (1) chụp bằng lệnh sao lưu trực tuyến của SQLite ra file tạm;
  (2) PRAGMA integrity_check trên bản chụp, khác "ok" thì dừng cả lượt;
  (3) đổi tên file tạm thành tên chính thức trong 01 lần;
  (4) mã hoá bản chụp ra tệp `.mahoa` (Fernet), khoá sao lưu suy ra từ khoá chủ (HKDF-SHA256), nên chỉ cần
      01 bản khoá chủ anh đã chép về máy là giải mã được bản trên Drive, kể cả khi mất cả VPS;
  (5) xếp tệp `.mahoa` vào hàng chờ đẩy Drive (M01); việc đẩy chạy theo lịch khi đã kết nối Drive
      (maychu/ketnoi/drive.py), đẩy xong mới xoá tệp `.mahoa` trên máy.
Bản chụp chưa mã hoá giữ trên máy 03 ngày để khôi phục nhanh (thư mục quyền 700, tệp quyền 600).
"""
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from maychu.dulieu import ketnoi, maso

DUOI_MAHOA = ".mahoa"

MUIGIO_VN = timezone(timedelta(hours=7))
GIU_SO_NGAY = 3  # giữ bản trên máy của 03 ngày gần nhất; bản lâu dài nằm ở Drive


def thumuc_saoluu(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / "saoluu"


def _mabam(duong: Path) -> str:
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def da_co_hom_nay(thumuc: Path | None = None, bay_gio: datetime | None = None) -> bool:
    ngay = (bay_gio or datetime.now(MUIGIO_VN)).strftime("%Y-%m-%d")
    noi = thumuc_saoluu(thumuc) / ngay
    return all((noi / f"{t}.sqlite3").exists() for t in ketnoi.CAC_FILE)


def _khoa_saoluu(thumuc: Path | None = None):
    """Khoá sao lưu = HKDF-SHA256 của khoá chủ (không cất riêng, không nằm trong bản sao lưu)."""
    import base64
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from maychu.hethong.kekhoa import khoachu
    goc = base64.urlsafe_b64decode(khoachu.lay(thumuc))
    return Fernet(base64.urlsafe_b64encode(HKDF(hashes.SHA256(), 32, None, b"igm360-saoluu-v1").derive(goc)))


def ma_hoa_tep(nguon: Path, thumuc: Path | None = None) -> Path:
    dich = nguon.with_name(nguon.name + DUOI_MAHOA)
    tam = dich.with_name(dich.name + ".tam")
    fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(_khoa_saoluu(thumuc).encrypt(nguon.read_bytes()))
    os.replace(tam, dich)
    return dich


def giai_ma_tep(tep_mahoa: Path, tep_khoachu: Path, dich: Path) -> Path:
    """Khôi phục bản tải từ Drive bằng tệp khoá chủ anh giữ (chạy được ở máy bất kỳ có thư viện cryptography)."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        Path(d, ".khoa_chu").write_bytes(Path(tep_khoachu).read_bytes())
        du_lieu = _khoa_saoluu(Path(d)).decrypt(Path(tep_mahoa).read_bytes())
    Path(dich).write_bytes(du_lieu)
    return Path(dich)


def _tep_dang_cho(thumuc: Path) -> set[str]:
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        return {r[0] for r in cn.execute("SELECT duongdan_tam FROM cho_day_drive WHERE trangthai IN ('cho', 'dangday', 'loi')")}
    finally:
        cn.close()


def _don_ban_cu(goc: Path, thumuc: Path) -> None:
    ngay = sorted(p for p in goc.iterdir() if p.is_dir() and len(p.name) == 10)
    cho = _tep_dang_cho(thumuc)
    for p in ngay[:-GIU_SO_NGAY]:
        con = [x for x in p.iterdir() if str(x) in cho]
        if not con:
            shutil.rmtree(p, ignore_errors=True)
            continue
        for x in p.iterdir():  # còn tệp chưa đẩy Drive: giữ tệp đó, xoá phần còn lại
            if x not in con:
                x.unlink(missing_ok=True)


def ten_truoc_capnhat(luc: datetime, ban: str) -> str:
    """Thư mục bản sao trước cập nhật (0.7.9 lớp 5): tên trên Drive thành `<ngày>_truoc_<bản>_<tệp>.mahoa`."""
    return f"{luc.strftime('%Y-%m-%d')}_truoc_{ban}"


GIU_TRUOC_CAPNHAT = 2   # giữ bản sao trước cập nhật của 02 lần gần nhất trên máy (bản lâu dài ở Drive)


def _don_truoc_capnhat(goc: Path, thumuc: Path) -> None:
    cac = sorted((p for p in goc.iterdir() if p.is_dir() and "_truoc_" in p.name), key=lambda p: p.stat().st_mtime)
    cho = _tep_dang_cho(thumuc)
    for p in cac[:-GIU_TRUOC_CAPNHAT]:
        if not any(str(x) in cho for x in p.iterdir()):
            shutil.rmtree(p, ignore_errors=True)


def chay(thumuc: Path | None = None, bay_gio: datetime | None = None, truoc_ban: str | None = None) -> dict:
    """Sao lưu lần lượt 07 file. Trả về {'ketqua': 'xong_tren_may' | 'loi', 'file': [...], 'noi': thư mục}.
    `truoc_ban` (0.7.9 lớp 5, QĐ213): lượt chụp ngay trước khi gửi lệnh cập nhật lên bản đó, vào thư mục riêng
    (không đè bản hằng ngày, không làm `da_co_hom_nay` đúng)."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    luc = bay_gio or datetime.now(MUIGIO_VN)
    goc = thumuc_saoluu(thumuc)
    noi = goc / (ten_truoc_capnhat(luc, truoc_ban) if truoc_ban else luc.strftime("%Y-%m-%d"))
    noi.mkdir(parents=True, exist_ok=True)
    os.chmod(goc, 0o700)
    os.chmod(noi, 0o700)
    dong_n01, ketqua_chung = [], "xong_tren_may"
    for ten in ketnoi.CAC_FILE:
        # CDA C1 (Y38): lượt trước cập nhật vẫn ghi N01 `loai` = 'hangngay' (CHECK N01 chỉ nhận 'hangngay',
        # 'camay_hangtuan'; 0 đổi lược đồ), dịp ghi ở `ketqua_tungbuoc_json` khoá "dip" = "truoc_capnhat".
        # Chỗ nào sau này đọc N01 theo nghĩa "hằng ngày" (đếm lượt, tính giờ sao lưu gần nhất) phải lọc bỏ `dip`.
        buoc = {"dip": "truoc_capnhat", "ban": truoc_ban} if truoc_ban else {}
        tam = noi / f"{ten}.sqlite3.tam"
        chinh = noi / f"{ten}.sqlite3"
        kiemtra = None
        try:
            nguon = ketnoi.mo(ten, thumuc)
            dich = sqlite3.connect(tam)
            try:
                nguon.backup(dich)
            finally:
                dich.close()
                nguon.close()
            os.chmod(tam, 0o600)
            buoc["1_chup"] = "dat"
            cn = sqlite3.connect(tam)
            try:
                kiemtra = cn.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                cn.close()
            if kiemtra != "ok":
                buoc["2_kiemtra"] = "loi"
                raise RuntimeError(f"integrity_check: {kiemtra}")
            buoc["2_kiemtra"] = "dat"
            os.replace(tam, chinh)
            buoc["3_doiten"] = "dat"
            ma_hoa_tep(chinh, thumuc)
            buoc["4_mahoa"] = "dat"
            buoc["5_day_drive"] = "cho_day"
            ketqua = "xong_tren_may"
        except Exception as loi:  # ghi lại rồi dừng cả lượt
            tam.unlink(missing_ok=True)
            buoc["loi"] = str(loi)[:300]
            ketqua = ketqua_chung = "loi"
        dong_n01.append({
            "id": maso.tao(), "loai": "hangngay", "file_dulieu": ten,
            "chup_luc": luc.isoformat(timespec="seconds"), "cach_chup": "backup_api",
            "kiemtra": kiemtra, "mabam": _mabam(chinh) if ketqua != "loi" else None,
            "dungluong_byte": chinh.stat().st_size if ketqua != "loi" else None,
            "noi_luu": str(chinh) if ketqua != "loi" else None,
            "ketqua_tungbuoc_json": json.dumps(buoc, ensure_ascii=False), "ketqua": ketqua,
        })
        if ketqua == "loi":
            break
    _ghi_n01(thumuc, dong_n01)
    _xep_cho_drive(thumuc, dong_n01, noi, luc)
    if ketqua_chung != "loi":
        _don_ban_cu(goc, thumuc)
        _don_truoc_capnhat(goc, thumuc)
    return {"ketqua": ketqua_chung, "file": dong_n01, "noi": noi}


def _ghi_n01(thumuc: Path, dong: list) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cot = list(dong[0].keys()) if dong else []
        for d in dong:
            cn.execute(f"INSERT INTO saoluu ({', '.join(cot)}) VALUES ({', '.join('?' * len(cot))})",
                       [d[c] for c in cot])
        cn.execute("COMMIT")
    finally:
        cn.close()


def _xep_cho_drive(thumuc: Path, dong_n01: list, noi: Path, luc: datetime) -> None:
    """Bước 5: mỗi tệp đã mã hoá 01 dòng M01 trạng thái 'cho'."""
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        for d in dong_n01:
            tep = noi / f"{d['file_dulieu']}.sqlite3{DUOI_MAHOA}"
            if d["ketqua"] == "loi" or not tep.exists():
                continue
            cn.execute("INSERT INTO cho_day_drive (id, loai, saoluu_id, duongdan_tam, dungluong_byte, trangthai, so_lan_thu, tao_luc)"
                       " VALUES (?, 'saoluu', ?, ?, ?, 'cho', 0, ?)",
                       (maso.tao(), d["id"], str(tep), tep.stat().st_size, luc.isoformat(timespec="seconds")))
        cn.execute("COMMIT")
    finally:
        cn.close()
