"""Tìm chữ không dấu, có chữ "đ" (thiết kế mục 0.8 Q1–Q8; PTD-02; QĐ120, QĐ229 cách C).

Cụm tìm chữ H08 ở tệp Bot (lược đồ bản 4): bảng ảo FTS5 `tinnhan_tim` không giữ chữ (`content=''`,
`contentless_delete=1`) + bảng nối `tinnhan_tim_noi` (`so` ↔ `tin_id`). Nối bằng `id` tin, không dựa `rowid` H08 (V5).
Ghi, xoá chỉ mục cùng giao dịch với dòng gốc, trong hàm ghi duy nhất (Q5); không trigger.
Chỉ dùng thư viện chuẩn.
"""
import sqlite3


def chuanhoa(chu) -> str:
    """Q1: đổi đ → d, Đ → D; các dấu khác để FTS5 (`remove_diacritics 2`) bỏ. Dùng ở cả 02 phía (Q2)."""
    return str(chu or "").replace("đ", "d").replace("Đ", "D")


def cau_tim(chu: str) -> str:
    """Q7: bọc chữ người dùng gõ trong ngoặc kép (ngoặc kép bên trong nhân đôi), để `"`, `*`, `-`, `OR` không thành lệnh."""
    return '"' + chuanhoa(chu).replace('"', '""') + '"'


def ghi_tin(cn: sqlite3.Connection, tin_id: str, noidung) -> None:
    """Ghi chỉ mục 01 tin (người gọi giữ giao dịch, cùng giao dịch với dòng H08)."""
    so = cn.execute("INSERT INTO tinnhan_tim_noi (tin_id) VALUES (?)", (tin_id,)).lastrowid
    cn.execute("INSERT INTO tinnhan_tim (rowid, noidung) VALUES (?, ?)", (so, chuanhoa(noidung)))


def xoa_tin(cn: sqlite3.Connection, tin_id: str) -> None:
    """Xoá chỉ mục 01 tin qua bảng nối (tra theo chỉ mục không trùng)."""
    d = cn.execute("SELECT so FROM tinnhan_tim_noi WHERE tin_id = ?", (tin_id,)).fetchone()
    if d:
        cn.execute("DELETE FROM tinnhan_tim WHERE rowid = ?", (d[0],))
        cn.execute("DELETE FROM tinnhan_tim_noi WHERE so = ?", (d[0],))


def dung_lai(cn: sqlite3.Connection) -> int:
    """Q8: dựng lại toàn bộ chỉ mục từ H08 (dùng khi nâng lược đồ 3 → 4, khi chỉ mục lệch). Trả số tin đã ghi."""
    cn.execute("INSERT INTO tinnhan_tim (tinnhan_tim) VALUES ('delete-all')")
    cn.execute("DELETE FROM tinnhan_tim_noi")
    so = 0
    for tin_id, noidung in cn.execute("SELECT id, noidung FROM tinnhan ORDER BY luc, id").fetchall():
        ghi_tin(cn, tin_id, noidung)
        so += 1
    return so


def tim(cn: sqlite3.Connection, chu: str, gioi_han: int = 50) -> list[str]:
    """`id` các tin khớp chữ gõ (không dấu, có "đ"). Chưa có màn dùng ở 0.8.0; để bài kiểm Q10 và tính năng sau."""
    if not str(chu or "").strip():
        return []
    return [r[0] for r in cn.execute(
        "SELECT n.tin_id FROM tinnhan_tim t JOIN tinnhan_tim_noi n ON n.so = t.rowid WHERE tinnhan_tim MATCH ?"
        " ORDER BY t.rank LIMIT ?", (cau_tim(chu), gioi_han))]
