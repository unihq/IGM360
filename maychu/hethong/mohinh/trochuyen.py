"""F35 Trò chuyện (ngày 06): anh hỏi, Cổng AI trả lời; lưu H07 cuộc trò chuyện, H08 từng tin (chỉ ghi thêm).

Mỗi lượt gửi kèm các tin trước của cùng cuộc trò chuyện (tối đa khoảng 24.000 chữ gần nhất). Tin AI ghi
`nhatky_ai_id` (G04) để truy được nguồn AI, tiền. Không có nguồn AI dùng được thì ghi 01 tin hệ thống nêu lý do.
"""
from datetime import datetime

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.mohinh import congai

GIU_CHU = 24_000
VAI_CHU = {"nguoi": "Anh", "ai": "Trợ lý"}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _ghi_tin(cn, hoithoai_id: str, vai: str, noidung: str, nhatky_ai_id=None) -> dict:
    t = {"id": maso.tao(), "hoithoai_id": hoithoai_id, "vai": vai, "noidung": noidung, "nhatky_ai_id": nhatky_ai_id,
         "luc": _bay_gio()}
    cn.execute("INSERT INTO tinnhan (id, hoithoai_id, vai, noidung, nhatky_ai_id, luc) VALUES (?, ?, ?, ?, ?, ?)",
               (t["id"], hoithoai_id, vai, noidung, nhatky_ai_id, t["luc"]))
    cn.execute("UPDATE hoithoai SET cap_nhat_luc = ? WHERE id = ?", (t["luc"], hoithoai_id))
    return t


def _cua(cn, hoithoai_id: str, nguoidung_id: str) -> bool:
    return bool(cn.execute("SELECT 1 FROM hoithoai WHERE id = ? AND nguoidung_id = ?", (hoithoai_id, nguoidung_id)).fetchone())


def gui(hoithoai_id: str | None, nguoidung_id: str, noidung: str, thumuc=None) -> dict:
    noidung = (noidung or "").strip()
    if not noidung:
        raise ValueError("Chưa có nội dung")
    cn = ketnoi.mo("Bot", thumuc)
    try:
        if hoithoai_id is None:
            hoithoai_id = maso.tao()
            bay = _bay_gio()
            cn.execute("INSERT INTO hoithoai (id, loai, nguoidung_id, tieude, trangthai, tao_luc, cap_nhat_luc)"
                       " VALUES (?, 'troly', ?, ?, 'dung', ?, ?)", (hoithoai_id, nguoidung_id, noidung[:80], bay, bay))
        elif not _cua(cn, hoithoai_id, nguoidung_id):
            raise PermissionError("Không có cuộc trò chuyện này")
        truoc = cn.execute("SELECT vai, noidung FROM tinnhan WHERE hoithoai_id = ? AND vai IN ('nguoi', 'ai') ORDER BY luc, rowid",
                           (hoithoai_id,)).fetchall()
        hoi = _ghi_tin(cn, hoithoai_id, "nguoi", noidung)
    finally:
        cn.close()
    lich_su = "\n\n".join(f"{VAI_CHU[v]}: {n}" for v, n in truoc)[-GIU_CHU:]
    cau = (f"Các lượt trước của cuộc trò chuyện:\n{lich_su}\n\nAnh hỏi tiếp:\n{noidung}" if lich_su else noidung)
    kq = congai.goi(cau, thumuc=thumuc)
    cn = ketnoi.mo("Bot", thumuc)
    try:
        if "loi" in kq:
            ly = "; ".join(f"{b['nguon']}: {b['lydo']}" for b in kq["bo_qua"])
            tl = _ghi_tin(cn, hoithoai_id, "hethong", kq["loi"] + (f" ({ly})" if ly else "") + ". Mở mục Mô hình AI để kiểm nguồn AI.")
        else:
            tl = _ghi_tin(cn, hoithoai_id, "ai", kq["chu"], kq["nhatky_ai_id"])
            tl["nguon"], tl["nguon_id"] = kq["nguon"], kq.get("nguon_id")   # Z10a: giao diện đặt chữ theo mã nguồn
    finally:
        cn.close()
    return {"hoithoai_id": hoithoai_id, "hoi": hoi, "tra_loi": tl}


def danh_sach(nguoidung_id: str, thumuc=None) -> list[dict]:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        return [dict(zip(("id", "tieude", "cap_nhat_luc"), r)) for r in cn.execute(
            "SELECT id, tieude, cap_nhat_luc FROM hoithoai WHERE nguoidung_id = ? AND loai = 'troly'"
            " ORDER BY cap_nhat_luc DESC LIMIT 100", (nguoidung_id,))]
    finally:
        cn.close()


def xem(hoithoai_id: str, nguoidung_id: str, thumuc=None) -> dict | None:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        if not _cua(cn, hoithoai_id, nguoidung_id):
            return None
        tin = [dict(zip(("id", "vai", "noidung", "nhatky_ai_id", "luc"), r)) for r in cn.execute(
            "SELECT id, vai, noidung, nhatky_ai_id, luc FROM tinnhan WHERE hoithoai_id = ? ORDER BY luc, rowid", (hoithoai_id,))]
        td = cn.execute("SELECT tieude FROM hoithoai WHERE id = ?", (hoithoai_id,)).fetchone()[0]
    finally:
        cn.close()
    return {"id": hoithoai_id, "tieude": td, "tinnhan": tin}
