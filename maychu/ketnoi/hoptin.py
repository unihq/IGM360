"""B08 Hộp tin nhận (file Ketnoi): ghi tin báo từ ngoài, chống trùng (QĐ109 L02, QĐ112).

Ràng buộc không trùng (`nguon`, `ma_sukien`) nằm trong lược đồ (lưới an toàn). Lớp ghi dùng 01 câu
"thêm nếu chưa có": tin lặp lại cùng `nguon`, `ma_sukien` không thêm dòng, dòng cũ đặt `trung` = 1 để biết
nguồn đã gửi lặp; đơn chỉ nạp 01 lần. Phần nhận tin thật (cổng nhận, kiểm dấu, gọi lại Pancake) làm ở GĐ 3.
"""
import json
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso


def nhan(nguon: str, ma_sukien: str, *, loai_sukien: str | None = None, ma_don: str | None = None,
         ketnoi_id: str | None = None, noidung: dict | None = None, thumuc: Path | None = None) -> dict:
    """Ghi 01 tin. Trả {'id': mã dòng, 'moi': True nếu là tin mới, False nếu là tin lặp}."""
    if not nguon or not ma_sukien:
        raise ValueError("tin báo phải có nguồn và mã sự kiện")
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        try:
            ma = maso.tao()
            cn.execute("INSERT INTO hoptin (id, nguon, ketnoi_id, ma_sukien, loai_sukien, ma_don, nhan_luc, noidung_json,"
                       " trung, trangthai, so_lan_thu) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'moi', 0)"
                       " ON CONFLICT (nguon, ma_sukien) DO UPDATE SET trung = 1",
                       (ma, nguon, ketnoi_id, ma_sukien, loai_sukien, ma_don,
                        muigio.gio_luu(),
                        json.dumps(noidung, ensure_ascii=False) if noidung is not None else None))
            d = cn.execute("SELECT id FROM hoptin WHERE nguon = ? AND ma_sukien = ?", (nguon, ma_sukien)).fetchone()
            cn.execute("COMMIT")
        except Exception:
            cn.execute("ROLLBACK")
            raise
    finally:
        cn.close()
    return {"id": d[0], "moi": d[0] == ma}
