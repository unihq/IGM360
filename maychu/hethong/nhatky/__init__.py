"""Nhật ký thao tác F04 (file Nhatky, chỉ ghi thêm). Không ghi khoá, mật khẩu vào cột nào."""
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN


def ghi(congcu: str, lenhcon: str, tomtat: str, ketqua: str = "dat", nguoi_id: str | None = None,
        lydo: str | None = None, thumuc: Path | None = None) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua, lydo_chan)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (maso.tao(), datetime.now(MUIGIO_VN).isoformat(timespec="seconds"), "anh" if nguoi_id else None,
                    nguoi_id, congcu, lenhcon, tomtat[:300], ketqua, lydo))
    finally:
        cn.close()
