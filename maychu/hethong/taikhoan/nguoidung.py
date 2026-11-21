"""Người dùng (F01): tài khoản quản trị tạo sẵn, đăng nhập 02 bước, bật và đổi máy nhận mã 02 lớp.

Chặn đoán mật khẩu theo QĐ90 (chan.py): đang khoá thì không kiểm mật khẩu; sai mật khẩu hay mã 02 lớp đều đếm.
Mã 02 lớp bắt buộc, không có cách tắt trên web (chỉ lệnh đặt lại trên VPS).
"""
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import kho
from maychu.hethong.taikhoan import chan, matkhau, phien, totp

HAN_MA_TAM_GIAY = 300          # mã tạm giữa bước mật khẩu và bước mã 02 lớp
_MA_TAM: dict[str, dict] = {}  # mã tạm -> {nguoidung_id, khoa_moi, het}
_BUOC_DA_DUNG: dict[str, int] = {}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def tao_quantri_tu_env(thumuc: Path | None = None) -> bool:
    """Chưa có người dùng nào thì tạo tài khoản chủ từ IGM360_ADMIN_USER, IGM360_ADMIN_PASSWORD (.env)."""
    ten, mk = os.environ.get("IGM360_ADMIN_USER", "").strip(), os.environ.get("IGM360_ADMIN_PASSWORD", "")
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        if cn.execute("SELECT count(*) FROM nguoidung").fetchone()[0] or not ten or not mk:
            return False
        cn.execute("INSERT INTO nguoidung (id, ma, ten, hieuluc_tu, phienban, nguoi_khai, tao_luc, vaitro, module_xem, matkhau_bam)"
                   " VALUES (?, ?, ?, ?, 1, 'hethong', ?, 'chu', ?, ?)",
                   (maso.tao(), ten, ten, _bay_gio()[:10], _bay_gio(), json.dumps(["tatca"]), matkhau.bam(mk)))
        return True
    finally:
        cn.close()


def _lay(cn, *, ten=None, ma_id=None):
    sql = "SELECT id, ma, matkhau_bam, totp_khoa_id FROM nguoidung WHERE trangthai = 'dung' AND "
    d = cn.execute(sql + ("ma = ?" if ten is not None else "id = ?"), (ten if ten is not None else ma_id,)).fetchone()
    return dict(zip(("id", "ma", "matkhau_bam", "totp_khoa_id"), d)) if d else None


def _ma_tam(nguoidung_id: str, khoa_moi: str | None = None) -> str:
    bay = time.time()
    for k in [k for k, v in _MA_TAM.items() if v["het"] < bay]:
        _MA_TAM.pop(k, None)
    ma = secrets.token_urlsafe(24)
    _MA_TAM[ma] = {"nguoidung_id": nguoidung_id, "khoa_moi": khoa_moi, "het": bay + HAN_MA_TAM_GIAY}
    return ma


def _doc_ma_tam(ma: str | None) -> dict | None:
    v = _MA_TAM.get(ma or "")
    return v if v and v["het"] >= time.time() else None


def _bao_khoa(k: dict) -> dict:
    return {"loi": "khoa", "khoa": k}


def _sai(ip: str, chu: str, thumuc) -> dict:
    kq = chan.ghi_sai(ip, thumuc)
    return _bao_khoa(kq) if "den" in kq else {"loi": chu, "con_lai": kq["con_lai"]}


def buoc_matkhau(ten: str, mk: str, ip: str = "khong_ro", thumuc: Path | None = None) -> dict:
    """Bước 1. Đang khoá: {'loi': 'khoa', 'khoa': {...}}; sai: {'loi': ..., 'con_lai': n};
    đúng: {'buoc': 'ma2lop' | 'bat2lop', 'ma_tam': ..., (qr, khoa khi bật)}."""
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ten=ten)
    finally:
        cn.close()
    if not u or not matkhau.kiem(mk, u["matkhau_bam"]):
        return _sai(ip, "Tên đăng nhập hoặc mật khẩu chưa đúng.", thumuc)
    if u["totp_khoa_id"]:
        return {"buoc": "ma2lop", "ma_tam": _ma_tam(u["id"])}
    khoa = totp.sinh_khoa()
    return {"buoc": "bat2lop", "ma_tam": _ma_tam(u["id"], khoa), "khoa": khoa,
            "qr_svg": totp.qr_svg(totp.duong_dan(khoa, u["ma"]))}


def _kiem_ma(nguoidung_id: str, khoa: str, ma: str) -> bool:
    b = totp.kiem(khoa, ma, buoc_da_dung=_BUOC_DA_DUNG.get(nguoidung_id, -1))
    if b is None:
        return False
    _BUOC_DA_DUNG[nguoidung_id] = b
    return True


def _cat_khoa_2lop(nguoidung_id: str, khoa: str, thumuc: Path | None) -> None:
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cu = cn.execute("SELECT totp_khoa_id FROM nguoidung WHERE id = ?", (nguoidung_id,)).fetchone()[0]
        moi = kho.cat("totp_2lop", khoa, thumuc, nguoi_nhap="anh", cn=cn)
        cn.execute("UPDATE nguoidung SET totp_khoa_id = ? WHERE id = ?", (moi, nguoidung_id))
        if cu:
            kho.xoa(cu, cn=cn)
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()


def buoc_ma2lop(ma_tam: str, ma: str, thietbi: str, ip: str = "khong_ro", thumuc: Path | None = None) -> dict:
    """Bước 2 (đã bật 02 lớp) hoặc bước bật 02 lớp lần đầu. Đúng thì trả về mã phiên."""
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    t = _doc_ma_tam(ma_tam)
    if not t:
        return {"loi": "Phiên đăng nhập đã hết hạn, anh đăng nhập lại"}
    if t["khoa_moi"]:
        khoa = t["khoa_moi"]
    else:
        cn = ketnoi.mo("Baomat", thumuc)
        try:
            khoa_id = _lay(cn, ma_id=t["nguoidung_id"])["totp_khoa_id"]
        finally:
            cn.close()
        khoa = kho.doc(khoa_id, thumuc)
    if not _kiem_ma(t["nguoidung_id"], khoa, ma):
        return _sai(ip, "Mã 02 lớp chưa đúng.", thumuc)
    if t["khoa_moi"]:
        _cat_khoa_2lop(t["nguoidung_id"], khoa, thumuc)
    _MA_TAM.pop(ma_tam, None)
    chan.thanh_cong(ip, thumuc)
    return {"ma_phien": phien.tao(t["nguoidung_id"], thietbi, thumuc)}


def kiem_ma_hien_tai(nguoidung_id: str, ma: str, thumuc: Path | None = None) -> dict:
    """Đổi máy nhận mã bước 1: anh nhập mã trên máy đang dùng để xác nhận."""
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        khoa_id = _lay(cn, ma_id=nguoidung_id)["totp_khoa_id"]
    finally:
        cn.close()
    if khoa_id and not _kiem_ma(nguoidung_id, kho.doc(khoa_id, thumuc), ma):
        return {"loi": "Mã 02 lớp chưa đúng"}
    return {"ok": True}


def bat_doi_may(nguoidung_id: str, thumuc: Path | None = None) -> dict:
    """Đổi máy nhận mã: sinh khoá mới, trả về QR; khoá cũ chỉ thay khi anh nhập đúng mã của khoá mới."""
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ma_id=nguoidung_id)
    finally:
        cn.close()
    khoa = totp.sinh_khoa()
    return {"ma_tam": _ma_tam(nguoidung_id, khoa), "khoa": khoa, "qr_svg": totp.qr_svg(totp.duong_dan(khoa, u["ma"]))}


def xac_nhan_doi_may(nguoidung_id: str, ma_tam: str, ma: str, thumuc: Path | None = None) -> dict:
    t = _doc_ma_tam(ma_tam)
    if not t or t["nguoidung_id"] != nguoidung_id or not t["khoa_moi"]:
        return {"loi": "Đã quá thời gian, anh bấm Đổi máy nhận mã lại"}
    if not _kiem_ma(nguoidung_id, t["khoa_moi"], ma):
        return {"loi": "Mã 02 lớp chưa đúng"}
    _cat_khoa_2lop(nguoidung_id, t["khoa_moi"], thumuc)
    _MA_TAM.pop(ma_tam, None)
    return {"ok": True}


def doi_matkhau(nguoidung_id: str, cu: str, moi: str, nhap_lai: str, phien_id: str, thumuc: Path | None = None) -> dict:
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ma_id=nguoidung_id)
        if not matkhau.kiem(cu, u["matkhau_bam"]):
            return {"loi": "Mật khẩu đang dùng chưa đúng", "o": "cu"}
        loi = matkhau.loi_matkhau_moi(moi, nhap_lai)
        if loi:
            return {"loi": loi, "o": "moi"}
        cn.execute("UPDATE nguoidung SET matkhau_bam = ? WHERE id = ?", (matkhau.bam(moi), nguoidung_id))
    finally:
        cn.close()
    ghi_doi_matkhau(nguoidung_id, "web", thumuc)
    return {"ok": True, "thu_hoi": phien.thu_hoi(nguoidung_id, tru_id=phien_id, thumuc=thumuc)}


def ghi_doi_matkhau(nguoidung_id: str, cach: str, thumuc: Path | None = None) -> None:
    """Ghi lần đổi mật khẩu vào F04 (để màn Tài khoản hiện "Đổi lần cuối"); không ghi mật khẩu."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua)"
                   " VALUES (?, ?, 'anh', ?, 'taikhoan', 'doi_matkhau', ?, 'dat')", (maso.tao(), _bay_gio(), nguoidung_id, cach))
    finally:
        cn.close()


def thong_tin(nguoidung_id: str, thumuc: Path | None = None) -> dict:
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        d = cn.execute("SELECT ma, ten, vaitro, totp_khoa_id, tao_luc FROM nguoidung WHERE id = ?", (nguoidung_id,)).fetchone()
    finally:
        cn.close()
    nk = ketnoi.mo("Nhatky", thumuc)
    try:
        doi = nk.execute("SELECT max(luc) FROM nhatky_thaotac WHERE congcu = 'taikhoan' AND lenhcon = 'doi_matkhau'"
                         " AND nguoi_id = ?", (nguoidung_id,)).fetchone()[0]
    finally:
        nk.close()
    return {"ten_dangnhap": d[0], "ten": d[1], "vaitro": d[2], "da_bat_2lop": bool(d[3]), "lan_doi_matkhau": doi or d[4]}
