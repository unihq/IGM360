"""Sao lưu 07 file dữ liệu (thiết kế cơ sở dữ liệu mục 0.1), ghi kết quả vào N01.

Không bao giờ chép thẳng file đang chạy. Mỗi file 05 bước:
  (1) chụp bằng lệnh sao lưu trực tuyến của SQLite ra file tạm;
  (2) PRAGMA integrity_check trên bản chụp, khác "ok" thì dừng cả lượt;
  (3) đổi tên file tạm thành tên chính thức trong 01 lần;
  (4) mã hoá: CHỜ két khoá (F03) có khoá sao lưu;
  (5) đẩy lên Drive: CHỜ kết nối Drive.
Bước 4, 5 ghi trạng thái chờ trong N01 cho tới khi 02 phần đó có.
"""
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from maychu.dulieu import ketnoi, maso

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


def _don_ban_cu(goc: Path) -> None:
    ngay = sorted(p for p in goc.iterdir() if p.is_dir() and len(p.name) == 10)
    for p in ngay[:-GIU_SO_NGAY]:
        shutil.rmtree(p, ignore_errors=True)


def chay(thumuc: Path | None = None, bay_gio: datetime | None = None) -> dict:
    """Sao lưu lần lượt 07 file. Trả về {'ketqua': 'xong_tren_may' | 'loi', 'file': [...]}."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    luc = bay_gio or datetime.now(MUIGIO_VN)
    goc = thumuc_saoluu(thumuc)
    noi = goc / luc.strftime("%Y-%m-%d")
    noi.mkdir(parents=True, exist_ok=True)
    os.chmod(goc, 0o700)
    os.chmod(noi, 0o700)
    dong_n01, ketqua_chung = [], "xong_tren_may"
    for ten in ketnoi.CAC_FILE:
        buoc = {}
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
            buoc["4_mahoa"] = "cho_khoa_saoluu"
            buoc["5_day_drive"] = "cho_ket_noi_drive"
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
    if ketqua_chung != "loi":
        _don_ban_cu(goc)
    return {"ketqua": ketqua_chung, "file": dong_n01}


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
