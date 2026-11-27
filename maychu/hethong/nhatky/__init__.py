"""Nhật ký thao tác F04 (file Nhatky, chỉ ghi thêm). Không ghi khóa, mật khẩu vào cột nào."""
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso
from maychu.hethong.kekhoa.che import che


def ghi(congcu: str, lenhcon: str, tomtat: str, ketqua: str = "dat", nguoi_id: str | None = None,
        lydo: str | None = None, thumuc: Path | None = None) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua, lydo_chan)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (maso.tao(), muigio.gio_luu(), "anh" if nguoi_id else None,
                    nguoi_id, congcu, lenhcon, che(tomtat)[:300], ketqua, che(lydo)))   # 0.7.8 Đ3: không ghi mã dài hạn
    finally:
        cn.close()
