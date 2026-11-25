"""Cất, đọc, đổi, xóa khóa ở F03 `kekhoa`. Chỉ lưu bản mã và 04 ký tự cuối; không ghi khóa ra nhật ký.

Màn 09 ngăn Két khóa (ngày 05) chỉ đọc danh sách không có bản mã. Khóa không có hạn: `han` để trống, màn hiện
"Không có hạn". Khóa sắp hết hạn: còn ít ngày hơn hoặc bằng thông số `songay_baotruoc_khoa_hethan` (mặc định 05).
"""
from datetime import date, datetime
from pathlib import Path

from maychu.dulieu import aibam, ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import khoachu


def cat(dichvu: str, giatri: str, thumuc: Path | None = None, *, ketnoi_id=None, han=None,
        nguoi_nhap: str = "hethong", cn=None) -> str:
    """Cất 01 khóa; trả về id dòng F03. Truyền `cn` để ghi trong giao dịch của người gọi.
    `nguoi_nhap`: "ai bấm" (mã tài khoản F01 hoặc mã máy, QĐ108)."""
    aibam.kiem(nguoi_nhap)
    ma = maso.tao()
    dong = (ma, dichvu, ketnoi_id, khoachu.ma_hoa(giatri.encode(), thumuc), giatri[-4:], han, nguoi_nhap, "dung")
    sql = ("INSERT INTO kekhoa (id, dichvu, ketnoi_id, banma, kytu_cuoi, han, nguoi_nhap, trangthai)"
           " VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    if cn is not None:
        cn.execute(sql, dong)
        return ma
    c = ketnoi.mo("Baomat", thumuc)
    try:
        c.execute(sql, dong)
    finally:
        c.close()
    return ma


def doc(ma: str, thumuc: Path | None = None) -> str:
    """Giải mã 01 khóa (chỉ lớp kết nối, tài khoản gọi; không đưa ra giao diện, nhật ký)."""
    c = ketnoi.mo("Baomat", thumuc)
    try:
        dong = c.execute("SELECT banma FROM kekhoa WHERE id = ?", (ma,)).fetchone()
        if not dong:
            raise KeyError(ma)
        c.execute("UPDATE kekhoa SET lan_dung_cuoi = ? WHERE id = ?",
                  (datetime.now(MUIGIO_VN).isoformat(timespec="seconds"), ma))
    finally:
        c.close()
    return khoachu.giai_ma(dong[0], thumuc).decode()


def xoa(ma: str, thumuc: Path | None = None, cn=None) -> None:
    sql = "DELETE FROM kekhoa WHERE id = ?"
    if cn is not None:
        cn.execute(sql, (ma,))
        return
    c = ketnoi.mo("Baomat", thumuc)
    try:
        c.execute(sql, (ma,))
    finally:
        c.close()


# Khóa do phần mềm tự sinh, dùng nội bộ: không hiện ở ngăn Két khóa, không sửa trên web.
NOIBO = {"totp_2lop"}
TEN_DICHVU = {"google_oauth_ungdung": "Google Drive · mã ứng dụng", "google_drive_lammoi": "Google Drive · quyền đẩy file"}


def ten_dichvu(dv: str) -> str:
    """Tên hiện của 01 dịch vụ; mã dài hạn gói Claude sinh theo mã nguồn (0 cột)."""
    if dv in TEN_DICHVU:
        return TEN_DICHVU[dv]
    if dv and dv.startswith("goi_claude_") and dv[11:].isdigit():
        return f"Claude · Code · Tài khoản {int(dv[11:])} · mã dài hạn"
    return dv


def tinh_trang(han: str | None, songay_baotruoc: int, hom_nay: date | None = None) -> tuple[str, int | None]:
    """('khong_han' | 'dung' | 'saphet' | 'hethan', số ngày còn lại)."""
    if not han:
        return "khong_han", None
    con = (date.fromisoformat(han[:10]) - (hom_nay or datetime.now(MUIGIO_VN).date())).days
    if con < 0:
        return "hethan", con
    return ("saphet" if con <= songay_baotruoc else "dung"), con


def danh_sach(thumuc: Path | None = None, songay_baotruoc: int = 5, hom_nay: date | None = None) -> list[dict]:
    c = ketnoi.mo("Baomat", thumuc)
    try:
        dong = c.execute("SELECT id, dichvu, ketnoi_id, kytu_cuoi, han, lan_dung_cuoi, nguoi_nhap FROM kekhoa"
                         " WHERE trangthai = 'dung' ORDER BY dichvu, id").fetchall()
    finally:
        c.close()
    ds = []
    for ma, dv, kn, cuoi, han, dung, nguoi in dong:
        if dv in NOIBO:
            continue
        tt, con = tinh_trang(han, songay_baotruoc, hom_nay)
        ds.append({"id": ma, "dichvu": dv, "ten": ten_dichvu(dv), "ketnoi_id": kn, "kytu_cuoi": cuoi,
                   "han": han, "lan_dung_cuoi": dung, "nguoi_nhap": nguoi, "tinhtrang": tt, "con_ngay": con})
    return ds


def doi(ma: str, giatri: str, thumuc: Path | None = None, *, han=None, cn=None) -> None:
    """Thay giá trị 01 khóa (giữ id để nguồn đang dùng khóa không phải nối lại)."""
    sql = "UPDATE kekhoa SET banma = ?, kytu_cuoi = ?, han = ? WHERE id = ? AND trangthai = 'dung'"
    gt = (khoachu.ma_hoa(giatri.encode(), thumuc), giatri[-4:], han, ma)
    c = cn or ketnoi.mo("Baomat", thumuc)
    try:
        if c.execute(sql, gt).rowcount != 1:
            raise KeyError(ma)
    finally:
        if cn is None:
            c.close()


def tim(dichvu: str, thumuc: Path | None = None) -> str | None:
    c = ketnoi.mo("Baomat", thumuc)
    try:
        d = c.execute("SELECT id FROM kekhoa WHERE dichvu = ? AND trangthai = 'dung' ORDER BY rowid DESC LIMIT 1",
                      (dichvu,)).fetchone()
    finally:
        c.close()
    return d[0] if d else None
