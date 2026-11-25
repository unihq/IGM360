"""Người dùng (F01): tài khoản quản trị tạo sẵn, đăng nhập 02 bước, bật và đổi máy nhận mã 02 lớp.

Chặn đoán mật khẩu theo QĐ90 (chan.py): đang khóa thì không kiểm mật khẩu; sai mật khẩu hay mã 02 lớp đều đếm.
QĐ390 (thay "02 lớp bắt buộc, không có cách tắt trên web"): 02 lớp mặc định bật; Chủ tắt được ở Cài đặt › Tài khoản và
02 lớp, phải nhập mật khẩu + mã hiện tại; bật lại nhập 01 mã của khóa cũ (không quét lại QR), mọi máy khác tự đăng xuất
(QĐ393 (1)). Cờ ở P01 (`thongso.CO_2LOP`), giữ khóa khi tắt. Lần đầu chưa có khóa vẫn bắt bật. Lệnh `datlai` đặt cờ về bật
(QĐ393 (2)). Đổi máy nhận mã đếm sai như đăng nhập (QĐ393 (4)), bị từ chối khi đang tắt (QĐ398).
"""
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso, phienban, songuoi
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import nhatky
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import thongbao
from maychu.hethong.kekhoa import kho
from maychu.hethong.taikhoan import chan, matkhau, phien, totp

HAN_MA_TAM_GIAY = 300          # mã tạm giữa bước mật khẩu và bước mã 02 lớp
_MA_TAM: dict[str, dict] = {}  # mã tạm -> {nguoidung_id, khoa_moi, het}
_BUOC_DA_DUNG: dict[str, int] = {}
# QĐ397: chữ bản A khối "Công tắc đăng nhập 02 lớp" (bảng chữ màn 09), chép bằng chương trình; số đếm và danh từ
# không ngắt dòng (dấu cách không ngắt). Chữ giao diện công tắc ở app.js (CHU_2LOP).
CHU_2LOP = {
    "sai_tat": "M\u1eadt kh\u1ea9u ho\u1eb7c m\u00e3 06\u00a0s\u1ed1 ch\u01b0a \u0111\u00fang.",   # dòng 9: hộp tắt báo sai (đếm chung chặn đăng nhập)
    "an_toan": "\u0110ang \u1edf ch\u1ebf \u0111\u1ed9 an to\u00e0n: ch\u01b0a t\u1eaft \u0111\u01b0\u1ee3c \u0111\u0103ng nh\u1eadp 02\u00a0l\u1edbp.",   # dòng 11
    "chuong": "\u0110\u0103ng nh\u1eadp 02\u00a0l\u1edbp \u0111ang t\u1eaft. B\u1eadt l\u1ea1i \u1edf C\u00e0i \u0111\u1eb7t \u203a T\u00e0i kho\u1ea3n v\u00e0 02\u00a0l\u1edbp.",   # dòng 12; QĐ398: câu từ chối đổi máy nhận mã lúc đang tắt (CDO TL-HOI-CHU-400-DOIMAY)
}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def tao_quantri_tu_env(thumuc: Path | None = None) -> bool:
    """Chưa có người dùng nào thì tạo tài khoản chủ từ IGM360_ADMIN_USER, IGM360_ADMIN_PASSWORD (.env).

    Theo thứ tự có trạng thái (QĐ108): dòng A18 của anh trước (có rồi thì dùng lại), rồi F01 trỏ về dòng đó.
    """
    ten, mk = os.environ.get("IGM360_ADMIN_USER", "").strip(), os.environ.get("IGM360_ADMIN_PASSWORD", "")
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        if cn.execute("SELECT count(*) FROM nguoidung").fetchone()[0] or not ten or not mk:
            return False
    finally:
        cn.close()
    nguoi_id = songuoi.lay_hoac_tao_anh(ten, "hethong", thumuc)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        phienban.them(cn, "nguoidung", {"ma": ten, "ten": ten, "hieuluc_tu": _bay_gio()[:10], "phienban": 1,
                                        "nguoi_khai": "hethong", "vaitro": "chu",
                                        "matkhau_bam": matkhau.bam(mk), "nguoi_id": nguoi_id})
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


def buoc_matkhau(ten: str, mk: str, ip: str = "khong_ro", thumuc: Path | None = None, thietbi: str = "") -> dict:
    """Bước 1. Đang khóa: {'loi': 'khoa', 'khoa': {...}}; sai: {'loi': ..., 'con_lai': n};
    đúng: {'buoc': 'ma2lop' | 'bat2lop', 'ma_tam': ..., (qr, khoa khi bật)};
    02 lớp đang tắt (QĐ390) và đã có khóa: {'buoc': 'vao', 'ma_phien': ...} – đường gọi đặt cookie, không trả mã phiên."""
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
    if u["totp_khoa_id"] and not thongso.co_2lop_bat(thumuc):   # QĐ390: đang tắt → đúng mật khẩu là vào
        chan.thanh_cong(ip, thumuc)
        return {"buoc": "vao", "ma_phien": phien.tao(u["id"], thietbi, thumuc)}
    if u["totp_khoa_id"]:
        return {"buoc": "ma2lop", "ma_tam": _ma_tam(u["id"])}
    khoa = totp.sinh_khoa()   # CDA 16b điều 6: chưa có khóa thì vẫn bắt bật, kể cả khi cờ đang tắt
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
        moi = kho.cat("totp_2lop", khoa, thumuc, nguoi_nhap=nguoidung_id, cn=cn)
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
        return {"loi": "Phiên đăng nhập đã hết hạn, bạn đăng nhập lại"}
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
        _bat_co(t["nguoidung_id"], "bat_lan_dau", thumuc)   # SOAT-KH090 (b), 16h dòng 4: bật lần đầu đặt cờ bật
    _MA_TAM.pop(ma_tam, None)
    chan.thanh_cong(ip, thumuc)
    return {"ma_phien": phien.tao(t["nguoidung_id"], thietbi, thumuc)}


def _bat_co(nguoidung_id: str, cach: str, thumuc: Path | None) -> bool:
    """Đặt cờ 02 lớp về bật (nếu đang tắt), đóng chuông "đang tắt", ghi F04 `bat_2lop` (16h dòng 4). Trả True nếu có đổi."""
    if thongso.co_2lop_bat(thumuc):
        thongbao.dong_2lop_tat("Đăng nhập 02 lớp đang bật", thumuc)   # chuông còn sót (nếu có) cũng đóng
        return False
    thongso.ghi_co_2lop(True, nguoidung_id, "Bật đăng nhập 02 lớp", thumuc)
    thongbao.dong_2lop_tat("Đã bật lại đăng nhập 02 lớp", thumuc)
    nhatky.ghi("taikhoan", "bat_2lop", cach, nguoi_id=nguoidung_id, thumuc=thumuc)
    return True


def tat_2lop(nguoidung_id: str, mk: str, ma: str, ip: str = "khong_ro", thumuc: Path | None = None) -> dict:
    """QĐ390: tắt 02 lớp. Hỏi mật khẩu đang dùng + mã 02 lớp hiện tại; sai 01 trong 02 thì không tắt, đếm vào `chan.py`.
    Không kiểm độ dài mật khẩu (QĐ391). Chế độ an toàn chặn ở đường gọi."""
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ma_id=nguoidung_id)
    finally:
        cn.close()
    if not u or not u["totp_khoa_id"]:
        return {"loi": CHU_2LOP["sai_tat"]}
    if not thongso.co_2lop_bat(thumuc):
        return {"ok": True, "doi": False}
    if not matkhau.kiem(mk or "", u["matkhau_bam"]) or not _kiem_ma(nguoidung_id, kho.doc(u["totp_khoa_id"], thumuc), ma or ""):
        return _sai(ip, CHU_2LOP["sai_tat"], thumuc)
    chan.thanh_cong(ip, thumuc)
    thongso.ghi_co_2lop(False, nguoidung_id, "Tắt đăng nhập 02 lớp", thumuc)
    thongbao.bao_2lop_tat(thumuc)
    nhatky.ghi("taikhoan", "tat_2lop", f"web · {ip}", nguoi_id=nguoidung_id, thumuc=thumuc)
    return {"ok": True, "doi": True}


def bat_lai_2lop(nguoidung_id: str, ma: str, phien_id: str | None, ip: str = "khong_ro", thumuc: Path | None = None) -> dict:
    """QĐ390, QĐ393 (1): bật lại bằng 01 mã của khóa cũ (không sinh khóa mới); đúng thì mọi phiên khác bị thu hồi,
    giữ phiên vừa bật. Sai mã đếm vào `chan.py`."""
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ma_id=nguoidung_id)
    finally:
        cn.close()
    if not u or not u["totp_khoa_id"]:
        return {"loi": "Mã 02 lớp chưa đúng."}
    if thongso.co_2lop_bat(thumuc):
        return {"ok": True, "doi": False, "thu_hoi": 0}
    if not _kiem_ma(nguoidung_id, kho.doc(u["totp_khoa_id"], thumuc), ma or ""):
        return _sai(ip, "Mã 02 lớp chưa đúng.", thumuc)
    chan.thanh_cong(ip, thumuc)
    _bat_co(nguoidung_id, f"web · {ip}", thumuc)
    return {"ok": True, "doi": True, "thu_hoi": phien.thu_hoi(nguoidung_id, tru_id=phien_id, thumuc=thumuc)}


def dat_lai_co_2lop(nguoidung_id: str, thumuc: Path | None = None) -> bool:
    """QĐ393 (2): lệnh `datlai` (có hay không `--tat-2lop`) đặt cờ về bật, đóng chuông, ghi F04."""
    return _bat_co(nguoidung_id, "lenh_vps", thumuc)


def kiem_ma_hien_tai(nguoidung_id: str, ma: str, thumuc: Path | None = None, ip: str = "khong_ro") -> dict:
    """Đổi máy nhận mã bước 1: anh nhập mã trên máy đang dùng để xác nhận. QĐ398: đang tắt thì từ chối (đọc cờ lúc gọi).
    QĐ393 (4): đang khóa thì từ chối, sai mã đếm vào `chan.py` như `buoc_ma2lop`."""
    if not thongso.co_2lop_bat(thumuc):
        return {"loi": CHU_2LOP["chuong"], "tat": True}
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        khoa_id = _lay(cn, ma_id=nguoidung_id)["totp_khoa_id"]
    finally:
        cn.close()
    if khoa_id and not _kiem_ma(nguoidung_id, kho.doc(khoa_id, thumuc), ma):
        return _sai(ip, "Mã 02 lớp chưa đúng", thumuc)
    chan.thanh_cong(ip, thumuc)
    return {"ok": True}


def bat_doi_may(nguoidung_id: str, thumuc: Path | None = None) -> dict:
    """Đổi máy nhận mã: sinh khóa mới, trả về QR; khóa cũ chỉ thay khi anh nhập đúng mã của khóa mới."""
    if not thongso.co_2lop_bat(thumuc):   # QĐ398
        return {"loi": CHU_2LOP["chuong"], "tat": True}
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        u = _lay(cn, ma_id=nguoidung_id)
    finally:
        cn.close()
    khoa = totp.sinh_khoa()
    return {"ma_tam": _ma_tam(nguoidung_id, khoa), "khoa": khoa, "qr_svg": totp.qr_svg(totp.duong_dan(khoa, u["ma"]))}


def xac_nhan_doi_may(nguoidung_id: str, ma_tam: str, ma: str, thumuc: Path | None = None, ip: str = "khong_ro") -> dict:
    """QĐ398, CDA điều 15: đọc cờ lúc xử lý → mã tạm cấp trước lúc tắt cũng bị từ chối, khóa không đổi.
    QĐ393 (4): đang khóa thì từ chối, sai mã đếm vào `chan.py`."""
    if not thongso.co_2lop_bat(thumuc):
        return {"loi": CHU_2LOP["chuong"], "tat": True}
    k = chan.dang_khoa(ip, thumuc)
    if k:
        return _bao_khoa(k)
    t = _doc_ma_tam(ma_tam)
    if not t or t["nguoidung_id"] != nguoidung_id or not t["khoa_moi"]:
        return {"loi": "Đã quá thời gian, bạn bấm Đổi máy nhận mã lại"}
    if not _kiem_ma(nguoidung_id, t["khoa_moi"], ma):
        return _sai(ip, "Mã 02 lớp chưa đúng", thumuc)
    _cat_khoa_2lop(nguoidung_id, t["khoa_moi"], thumuc)
    _MA_TAM.pop(ma_tam, None)
    chan.thanh_cong(ip, thumuc)
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
    # CDA 16b điều 7: da_bat_2lop = có khóa VÀ cờ bật; co_khoa_2lop để giao diện biết bật lại được (QĐ390)
    return {"ten_dangnhap": d[0], "ten": d[1], "vaitro": d[2], "da_bat_2lop": bool(d[3]) and thongso.co_2lop_bat(thumuc),
            "co_khoa_2lop": bool(d[3]), "lan_doi_matkhau": doi or d[4]}
