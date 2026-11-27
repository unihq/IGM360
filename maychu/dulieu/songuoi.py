"""A18 Sổ người (QĐ99, QĐ108; thiết kế mục 0.4, 0.7, 1.2).

- 01 dòng = 01 người, giữ nguyên mãi, không tách phiên bản; đổi tên đi qua lớp điều chỉnh C20.
- Mã hiển thị `ma`: 07 chữ số tăng dần, không mang nghĩa loại (`0000001`), cấp trong cùng giao dịch ghi
  (người gọi đã mở BEGIN IMMEDIATE trên Dulieu_Chinh) để 02 nguồn tạo người cùng lúc không ra 01 số.
- Dòng của anh (`loai` = `anh`) có đúng 01; tài khoản chủ F01 trỏ về dòng này.
"""
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso

MA_TOIDA = 9_999_999


def _bay_gio() -> str:
    return muigio.gio_luu()


def cap_ma(cn) -> str:
    """Mã kế tiếp. Chỉ gọi trong giao dịch ghi đang mở trên Dulieu_Chinh."""
    if not cn.in_transaction:
        raise RuntimeError("cấp mã người phải nằm trong giao dịch ghi")
    d = cn.execute("SELECT max(ma) FROM nguoi").fetchone()[0]
    so = int(d) + 1 if d else 1
    if so > MA_TOIDA:
        raise RuntimeError("đã hết mã người 07 chữ số")
    return f"{so:07d}"


def them(cn, ten: str, loai: str, nguoi_khai: str, co_dlcn: int = 1) -> dict:
    """Thêm 01 người trong giao dịch đang mở; trả {id, ma}."""
    ten = (ten or "").strip()
    if not ten:
        raise ValueError("tên người không được trống")
    ma_id, ma = maso.tao(), cap_ma(cn)
    cn.execute("INSERT INTO nguoi (id, ma, ten, loai, co_dlcn, nguoi_khai, tao_luc) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (ma_id, ma, ten, loai, co_dlcn, nguoi_khai, _bay_gio()))
    return {"id": ma_id, "ma": ma}


def tao(ten: str, loai: str, nguoi_khai: str, thumuc: Path | None = None, co_dlcn: int = 1) -> dict:
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        try:
            kq = them(cn, ten, loai, nguoi_khai, co_dlcn)
            cn.execute("COMMIT")
        except Exception:
            cn.execute("ROLLBACK")
            raise
    finally:
        cn.close()
    return kq


def id_cua_anh(cn) -> str | None:
    d = cn.execute("SELECT id FROM nguoi WHERE loai = 'anh' AND trangthai = 'dung' ORDER BY ma LIMIT 1").fetchone()
    return d[0] if d else None


def lay_hoac_tao_anh(ten: str, nguoi_khai: str, thumuc: Path | None = None) -> str:
    """Dòng A18 của anh: có rồi thì dùng lại (chạy lại không tạo thêm), chưa có thì tạo."""
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        try:
            ma_id = id_cua_anh(cn) or them(cn, ten, "anh", nguoi_khai)["id"]
            cn.execute("COMMIT")
        except Exception:
            cn.execute("ROLLBACK")
            raise
    finally:
        cn.close()
    return ma_id


def ton_tai(nguoi_id: str, thumuc: Path | None = None) -> bool:
    """Lớp ghi kiểm dòng A18 có thật trước khi ghi nối khác file (F01, H03; thiết kế mục 0.7)."""
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        return bool(cn.execute("SELECT 1 FROM nguoi WHERE id = ?", (nguoi_id,)).fetchone())
    finally:
        cn.close()
