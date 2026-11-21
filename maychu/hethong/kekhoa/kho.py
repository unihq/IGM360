"""Cất, đọc, xoá khoá ở F03 `kekhoa`. Chỉ lưu bản mã và 04 ký tự cuối; không ghi khoá ra nhật ký."""
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import khoachu


def cat(dichvu: str, giatri: str, thumuc: Path | None = None, *, ketnoi_id=None, han=None,
        nguoi_nhap: str = "anh", cn=None) -> str:
    """Cất 01 khoá; trả về id dòng F03. Truyền `cn` để ghi trong giao dịch của người gọi."""
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
    """Giải mã 01 khoá (chỉ lớp kết nối, tài khoản gọi; không đưa ra giao diện, nhật ký)."""
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
