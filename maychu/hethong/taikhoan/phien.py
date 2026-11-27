"""Phiên đăng nhập web (F05). Chỉ lưu mã băm của mã phiên, không lưu mã gốc.

Thời hạn (QĐ90): phiên hết sau 30 ngày không thao tác; dùng liên tục cũng phải đăng nhập lại sau 30 ngày
(`het_han` = lúc tạo + 30 ngày). Giao diện báo trước 05 phút, nút "Ở lại" gia hạn phần không thao tác.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso


NGAY_KHONG_THAOTAC = 30
NGAY_TOIDA = 30


def _bay_gio() -> str:
    return muigio.gio_luu()


def het_luc(lan_dung_cuoi: str, het_han: str) -> str:
    """Lúc phiên hết: sớm hơn giữa (lần dùng cuối + 30 ngày) và hạn tối đa."""
    nghi = datetime.fromisoformat(lan_dung_cuoi) + timedelta(days=NGAY_KHONG_THAOTAC)
    return min(nghi, datetime.fromisoformat(het_han)).isoformat(timespec="seconds")


def _bam(ma: str) -> str:
    return hashlib.sha256(ma.encode()).hexdigest()


def thietbi_tu(user_agent: str | None) -> str:
    """Rút gọn chuỗi trình duyệt thành dạng "Máy tính · Chrome trên Windows" (cột `thietbi`, bản vẽ màn 09)."""
    ua = user_agent or ""
    trinh = next((t for k, t in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"),
                                 ("Safari/", "Safari")) if k in ua), "Trình duyệt khác")
    may = next((t for k, t in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
                               ("Mac OS X", "macOS"), ("Linux", "Linux")) if k in ua), "máy khác")
    loai = "Điện thoại" if may in ("iPhone", "Android") and "Mobile" in ua or may == "iPhone" else (
        "Máy tính bảng" if may == "iPad" else "Máy tính")
    return f"{loai} · {trinh} trên {may}"


def tao(nguoidung_id: str, thietbi: str, thumuc: Path | None = None) -> str:
    """Tạo 01 phiên; trả về mã phiên gốc (chỉ đặt vào cookie, không lưu)."""
    ma = secrets.token_urlsafe(32)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        bay = muigio.bay()
        cn.execute("INSERT INTO phien_truycap (id, nguoidung_id, loai, mabam, tao_luc, het_han, lan_dung_cuoi, thietbi)"
                   " VALUES (?, ?, 'phien_web', ?, ?, ?, ?, ?)",
                   (maso.tao(), nguoidung_id, _bam(ma), bay.isoformat(timespec="seconds"),
                    (bay + timedelta(days=NGAY_TOIDA)).isoformat(timespec="seconds"), bay.isoformat(timespec="seconds"), thietbi))
    finally:
        cn.close()
    return ma


def tim(ma: str | None, thumuc: Path | None = None) -> dict | None:
    """Phiên còn dùng được (chưa thu hồi, người dùng đang dùng); cập nhật lần dùng cuối."""
    if not ma:
        return None
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        d = cn.execute(
            "SELECT p.id, p.nguoidung_id, u.ma, u.ten, u.vaitro, p.lan_dung_cuoi, p.het_han FROM phien_truycap p"
            " JOIN nguoidung u ON u.id = p.nguoidung_id"
            " WHERE p.mabam = ? AND p.loai = 'phien_web' AND p.thuhoi_luc IS NULL AND u.trangthai = 'dung'",
            (_bam(ma),)).fetchone()
        if not d or not d[6] or het_luc(d[5], d[6]) <= _bay_gio():
            return None
        bay = _bay_gio()
        cn.execute("UPDATE phien_truycap SET lan_dung_cuoi = ? WHERE id = ?", (bay, d[0]))
    finally:
        cn.close()
    return {"phien_id": d[0], "nguoidung_id": d[1], "ten_dangnhap": d[2], "ten": d[3], "vaitro": d[4],
            "het_luc": het_luc(bay, d[6])}   # Y20c: bỏ `module_xem`, quyền màn ở F08 (QĐ144)


def danh_sach(nguoidung_id: str, thumuc: Path | None = None) -> list[dict]:
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        dong = cn.execute("SELECT id, loai, thietbi, tao_luc, lan_dung_cuoi, het_han FROM phien_truycap"
                          " WHERE nguoidung_id = ? AND thuhoi_luc IS NULL ORDER BY lan_dung_cuoi DESC",
                          (nguoidung_id,)).fetchall()
    finally:
        cn.close()
    ra = [dict(zip(("id", "loai", "thietbi", "tao_luc", "lan_dung_cuoi", "het_han"), d)) for d in dong]
    for p in ra:
        p["het_luc"] = het_luc(p["lan_dung_cuoi"], p["het_han"]) if p["het_han"] and p["lan_dung_cuoi"] else None
    return [p for p in ra if p["het_luc"] and p["het_luc"] > _bay_gio()]


def thu_hoi(nguoidung_id: str, phien_id: str | None = None, tru_id: str | None = None,
            thumuc: Path | None = None) -> int:
    """Thu hồi 01 phiên (phien_id) hoặc mọi phiên trừ tru_id. Trả về số phiên đã thu hồi."""
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        if phien_id:
            cur = cn.execute("UPDATE phien_truycap SET thuhoi_luc = ? WHERE id = ? AND nguoidung_id = ? AND thuhoi_luc IS NULL",
                             (_bay_gio(), phien_id, nguoidung_id))
        else:
            cur = cn.execute("UPDATE phien_truycap SET thuhoi_luc = ? WHERE nguoidung_id = ? AND thuhoi_luc IS NULL"
                             " AND id IS NOT ?", (_bay_gio(), nguoidung_id, tru_id))
        return cur.rowcount
    finally:
        cn.close()
