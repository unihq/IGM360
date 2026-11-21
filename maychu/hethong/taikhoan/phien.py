"""Phiên đăng nhập web (F05). Chỉ lưu mã băm của mã phiên, không lưu mã gốc.

Thời hạn phiên (hết sau bao lâu không thao tác, tối đa bao nhiêu ngày) và cách báo trước 05 phút
CHỜ ANH DUYỆT (nhật ký mục 5.57 D): `het_han` để trống tới khi có quyết định.
"""
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _bam(ma: str) -> str:
    return hashlib.sha256(ma.encode()).hexdigest()


def thietbi_tu(user_agent: str | None) -> str:
    """Rút gọn chuỗi trình duyệt thành dạng "Chrome · Windows" (cột `thietbi`)."""
    ua = user_agent or ""
    trinh = next((t for k, t in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"),
                                 ("Safari/", "Safari")) if k in ua), "Trình duyệt khác")
    may = next((t for k, t in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
                               ("Mac OS X", "macOS"), ("Linux", "Linux")) if k in ua), "máy khác")
    return f"{trinh} · {may}"


def tao(nguoidung_id: str, thietbi: str, thumuc: Path | None = None) -> str:
    """Tạo 01 phiên; trả về mã phiên gốc (chỉ đặt vào cookie, không lưu)."""
    ma = secrets.token_urlsafe(32)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        cn.execute("INSERT INTO phien_truycap (id, nguoidung_id, loai, mabam, tao_luc, lan_dung_cuoi, thietbi)"
                   " VALUES (?, ?, 'phien_web', ?, ?, ?, ?)",
                   (maso.tao(), nguoidung_id, _bam(ma), _bay_gio(), _bay_gio(), thietbi))
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
            "SELECT p.id, p.nguoidung_id, u.ma, u.ten, u.vaitro, u.module_xem FROM phien_truycap p"
            " JOIN nguoidung u ON u.id = p.nguoidung_id"
            " WHERE p.mabam = ? AND p.loai = 'phien_web' AND p.thuhoi_luc IS NULL AND u.trangthai = 'dung'",
            (_bam(ma),)).fetchone()
        if not d:
            return None
        cn.execute("UPDATE phien_truycap SET lan_dung_cuoi = ? WHERE id = ?", (_bay_gio(), d[0]))
    finally:
        cn.close()
    return {"phien_id": d[0], "nguoidung_id": d[1], "ten_dangnhap": d[2], "ten": d[3], "vaitro": d[4], "module_xem": d[5]}


def danh_sach(nguoidung_id: str, thumuc: Path | None = None) -> list[dict]:
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        dong = cn.execute("SELECT id, loai, thietbi, tao_luc, lan_dung_cuoi, het_han FROM phien_truycap"
                          " WHERE nguoidung_id = ? AND thuhoi_luc IS NULL ORDER BY lan_dung_cuoi DESC",
                          (nguoidung_id,)).fetchall()
    finally:
        cn.close()
    return [dict(zip(("id", "loai", "thietbi", "tao_luc", "lan_dung_cuoi", "het_han"), d)) for d in dong]


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
