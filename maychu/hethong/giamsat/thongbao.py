"""Chuông thông báo bước 1 (QĐ165; PTD-06 mục 1, mục 10; bản vẽ Z7b). 0 đổi cấu trúc dữ liệu.

- Mỗi thông báo là 01 dòng D03 `canhbao`, `loai` = `sukien`, `khoa_chongtrung` = "<loại>[:<dòng nguồn>]". 01 việc
  chỉ 01 dòng còn mở; việc đã xử lý (nguồn hết lỗi, bản mới đã cài) thì đóng dòng (`dadong`, `lydo_dong`).
- Lịch nền (`giamsat/lich.py`) gọi `quet()` mỗi 10 phút; đo máy, sao lưu xong thì quét ngay phần của mình.
- Mức, icon, màn đích của từng loại để ở bảng `LOAI` trong mã, không ghi vào từng dòng D03.
- Chữ sinh lúc đọc từ loại + `nguong`, `giatri` + dòng nguồn (không lưu sẵn chữ) để lọc quyền được ngay lúc đọc.
- Đọc hay chưa do 01 thông số mốc đọc (`moc_doc_chuong`, QĐ165): bấm "Đọc hết" không đổi trạng thái D03.
- Lọc quyền: 01 hàm duy nhất `loc_quyen`, dùng chung cho số trên chuông và danh sách; GĐ 1 trả hết cho Chủ (QĐ141).
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi, maso
from maychu.hethong.caidat import thongso

log = logging.getLogger("igm360.thongbao")
NB = " "   # dấu cách không ngắt (bản vẽ Z7b: "Tài khoản 1", "hết hạn", "05 ngày"… không tách khi xuống dòng)
CON_MO = ("moi", "dabao", "dagiao_task")
MAYCHU = ("03", "o-maychu", "Bảng điều hành › Máy chủ")
# tiền tố khóa: (mức, icon, màn đích, chỗ cuộn tới, nơi mở). Mức: do = Cần xử lý ngay, xem = Sắp tới hạn, tin = Tin mới
LOAI = {
    "goi_hetphien": ("do", "brain-circuit", "13", None, "Mô hình AI"),
    "hanmuc_tuan": ("xem", "hourglass", "13", None, "Mô hình AI"),
    "khoa_hethan": ("do", "key-round", "ketkhoa", None, "Cài đặt › Két khóa"),
    "khoa_saphethan": ("xem", "key-round", "ketkhoa", None, "Cài đặt › Két khóa"),
    "madaihan_hethan": ("do", "key-round", "13", None, "Mô hình AI"),
    "madaihan_saphethan": ("xem", "key-round", "13", None, "Mô hình AI"),
    "saoluu_loi": ("do", "database-backup", *MAYCHU),
    "ocung_vuot": ("do", "hard-drive", *MAYCHU),
    "swap_vuot_nguong": ("do", "memory-stick", *MAYCHU),
    "banmoi": ("tin", "cloud-download", "capnhat", None, "Cài đặt › Cập nhật"),
    "capnhat_kiem": ("do", "shield-alert", "capnhat", None, "Cài đặt › Cập nhật"),   # 0.7.9 lớp 4
    "quayve_loi": ("do", "rotate-ccw", "capnhat", None, "Cài đặt › Cập nhật"),   # Y38d: quay về hỏng
    "drive_nen": ("xem", "cloud-alert", "capnhat", None, "Cài đặt › Cập nhật"),   # QĐ261, QĐ262: Bản sao Drive lỗi
    "cli_nang": ("tin", "wrench", "capnhat", None, "Cài đặt › Cập nhật"),   # QĐ271 Z20 dòng 14: Nâng công cụ AI
    "cli_loi": ("xem", "circle-alert", "capnhat", None, "Cài đặt › Cập nhật"),   # QĐ271 Z20 dòng 15: Công cụ AI lỗi (vàng)
    "cli_o": ("xem", "hard-drive", "capnhat", None, "Cài đặt › Cập nhật"),   # QĐ307 Z20 dòng 18: thiếu ổ trống (vàng)
    "cli_mang": ("xem", "wifi-off", "capnhat", None, "Cài đặt › Cập nhật"),   # QĐ307 Z20 dòng 19: không kết nối được hãng
    # QĐ390, QĐ397 (bảng chữ màn 09 dòng 12, BV04): mức Xem, icon shield-alert, mở suốt lúc 02 lớp tắt
    "dangnhap_2lop_tat": ("xem", "shield-alert", "taikhoan", None, "Tài khoản"),
    # QĐ634, QĐ636 "F04 + chuông": tin sự kiện (đã xảy ra, không cần xử lý) – mức tin, mở Cài đặt › Chung; đóng khi "Đọc hết" (TẠM)
    "tenmien_doi": ("tin", "globe", "chung", None, "Cài đặt › Chung"),
    "muigio_doi": ("tin", "clock", "chung", None, "Cài đặt › Chung"),
}
SU_KIEN = ("tenmien_doi", "muigio_doi")
KHOA_2LOP_TAT = "dangnhap_2lop_tat"
THU_TU_MUC = {"do": 0, "xem": 1, "tin": 2}


def _bay_gio() -> str:
    return muigio.gio_luu()


def _so(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# ---------------- Ghi D03 ----------------
def _mo(cn, khoa: str, bang: str | None, dong_id: str | None = None, nguong=None, giatri=None) -> str:
    """Mở 01 dòng còn mở theo khóa; đã có thì chỉ cập nhật số (giữ giờ tạo, giữ dòng nguồn đầu tiên)."""
    d = cn.execute(f"SELECT id FROM canhbao WHERE khoa_chongtrung = ? AND trangthai IN {CON_MO} LIMIT 1", (khoa,)).fetchone()
    if d:
        if nguong is not None or giatri is not None:
            cn.execute("UPDATE canhbao SET nguong = coalesce(?, nguong), giatri = coalesce(?, giatri) WHERE id = ?",
                       (nguong, giatri, d[0]))
        return d[0]
    ma = maso.tao()
    cn.execute("INSERT INTO canhbao (id, loai, nguong, giatri, chieu, bang_nguon, dong_nguon_id, khoa_chongtrung, trangthai,"
               " tao_luc) VALUES (?, 'sukien', ?, ?, ?, ?, ?, ?, 'moi', ?)",
               (ma, nguong, giatri, "tren" if nguong is not None else None, bang, dong_id, khoa, _bay_gio()))
    return ma


def _dong(cn, khoa: str, lydo: str) -> int:
    return cn.execute(f"UPDATE canhbao SET trangthai = 'dadong', dong_luc = ?, lydo_dong = ? WHERE khoa_chongtrung = ?"
                      f" AND trangthai IN {CON_MO}", (_bay_gio(), lydo, khoa)).rowcount


def _khoa_mo(cn, tien_to: str) -> list[str]:
    return [r[0] for r in cn.execute(f"SELECT khoa_chongtrung FROM canhbao WHERE substr(khoa_chongtrung, 1, ?) = ?"
                                     f" AND trangthai IN {CON_MO}", (len(tien_to), tien_to))]


class _Ghi:
    """01 giao dịch ghi D03 (BEGIN IMMEDIATE) cho 01 nguồn."""
    def __init__(self, thumuc):
        self.thumuc = thumuc

    def __enter__(self):
        self.cn = ketnoi.mo("Dulieu_Chinh", self.thumuc)
        self.cn.execute("BEGIN IMMEDIATE")
        return self.cn

    def __exit__(self, loai, *_):
        try:
            self.cn.execute("ROLLBACK" if loai else "COMMIT")
        finally:
            self.cn.close()


# ---------------- 05 nguồn (+ đóng tệp hoán đổi) ----------------
def quet_goi(thumuc: Path | None = None) -> None:
    """Gói AI hết phiên đăng nhập (đỏ); gói AI dùng ≥ `tyle_bao_hanmuc_tuan` hạn mức tuần (vàng)."""
    from maychu.hethong.mohinh import dangnhap_goi
    nguong = _so(thongso.doc_mot("tyle_bao_hanmuc_tuan", "80", thumuc)) or 80
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        goi = cn.execute("SELECT ma, trangthai, tyle_tuan, datlai_tuan_luc FROM nguon_ai WHERE substr(ma, 1, 4) = 'goi_'").fetchall()
    finally:
        cn.close()
    bay = muigio.bay()
    tt = {}
    for ma, trangthai, _t, _d in goi:   # hỏi CLI trước, ngoài giao dịch ghi
        m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", ma or "")
        if m and trangthai == "dung":
            tt[ma] = dangnhap_goi.trang_thai(m.group(1), int(m.group(2)))
    with _Ghi(thumuc) as w:
        for ma, trangthai, tyle, datlai in goi:
            if trangthai != "dung":
                _dong(w, f"goi_hetphien:{ma}", "Đã gỡ tài khoản")
                _dong(w, f"hanmuc_tuan:{ma}", "Đã gỡ tài khoản")
                continue
            t = tt.get(ma) or {}
            if not t.get("khong_ro") and "da_noi" in t:   # chưa kiểm được thì giữ nguyên
                if t["da_noi"]:
                    _dong(w, f"goi_hetphien:{ma}", "Đã đăng nhập lại")
                else:
                    _mo(w, f"goi_hetphien:{ma}", "nguon_ai", ma)
            try:
                da_datlai = bool(datlai) and datetime.fromisoformat(datlai) <= bay
            except ValueError:
                da_datlai = False
            if tyle is not None and not da_datlai and tyle >= nguong:
                _mo(w, f"hanmuc_tuan:{ma}", "nguon_ai", ma, nguong=nguong, giatri=int(tyle))
            else:
                _dong(w, f"hanmuc_tuan:{ma}", "Hạn mức tuần đã đặt lại" if da_datlai else "Đã dưới ngưỡng báo")


def quet_khoa(thumuc: Path | None = None) -> None:
    """Khóa kết nối đã hết hạn (đỏ); còn ≤ `songay_baotruoc_khoa_hethan` ngày (vàng)."""
    from maychu.hethong.kekhoa import kho
    n = _so(thongso.doc_mot("songay_baotruoc_khoa_hethan", "5", thumuc))
    ds = [k for k in kho.danh_sach(thumuc, n) if not (k["dichvu"] or "").startswith("goi_claude_")]   # mã dài hạn: quet_madaihan
    with _Ghi(thumuc) as w:
        con = set()
        for k in ds:
            con.add(k["id"])
            het, sap = f"khoa_hethan:{k['id']}", f"khoa_saphethan:{k['id']}"
            if k["tinhtrang"] == "hethan":
                _mo(w, het, "kekhoa", k["id"])
                _dong(w, sap, "Khóa đã hết hạn")
            elif k["tinhtrang"] == "saphet":
                _mo(w, sap, "kekhoa", k["id"], nguong=n, giatri=k["con_ngay"])
                _dong(w, het, "Đã gia hạn khóa")
            else:
                _dong(w, het, "Đã gia hạn khóa")
                _dong(w, sap, "Đã gia hạn khóa")
        for khoa in _khoa_mo(w, "khoa_hethan:") + _khoa_mo(w, "khoa_saphethan:"):
            if khoa.split(":", 1)[1] not in con:
                _dong(w, khoa, "Khóa đã xóa")


def quet_madaihan(thumuc: Path | None = None) -> None:
    """0.7.8 (QĐ198, QĐ200, PTD-09 mục 3): mã dài hạn gói Claude hết hạn (đỏ, 01 dòng mở tới khi lấy mã mới hoặc gỡ);
    còn ≤ `madaihan.SO_NGAY_NHAC` ngày (vàng) thì MỖI NGÀY 01 dòng: khóa chống trùng gắn ngày, dòng ngày cũ đóng."""
    from maychu.hethong.mohinh import madaihan
    bay = muigio.bay()
    hom_nay = muigio.hom_nay(thumuc)   # ③ "mỗi ngày 01 dòng" theo múi đã chọn
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        dv = [r[0] for r in cn.execute("SELECT DISTINCT dichvu FROM kekhoa WHERE trangthai = 'dung'"
                                       " AND substr(dichvu, 1, 11) = 'goi_claude_'")]
    finally:
        cn.close()
    tt = {d: madaihan.thong_tin(int(d[11:]), thumuc, bay) for d in dv if d[11:].isdigit()}
    with _Ghi(thumuc) as w:
        for d, t in tt.items():
            het, sap = f"madaihan_hethan:{d}", f"madaihan_saphethan:{d}:{hom_nay}"
            for khoa in _khoa_mo(w, f"madaihan_saphethan:{d}:"):
                if khoa != sap:
                    _dong(w, khoa, "Đã sang ngày mới")
            if t and t["het"]:
                _mo(w, het, "kekhoa", d)
                _dong(w, sap, "Mã đã hết hạn")
            elif t and t["con_ngay"] is not None and t["con_ngay"] <= madaihan.SO_NGAY_NHAC:
                _mo(w, sap, "kekhoa", d, nguong=madaihan.SO_NGAY_NHAC, giatri=t["con_ngay"])
                _dong(w, het, "Đã lấy mã mới")
            else:
                _dong(w, het, "Đã lấy mã mới")
                _dong(w, sap, "Đã lấy mã mới")
        for khoa in _khoa_mo(w, "madaihan_hethan:") + _khoa_mo(w, "madaihan_saphethan:"):
            if khoa.split(":")[1] not in tt:
                _dong(w, khoa, "Đã ngắt mã dài hạn")


def quet_kiem_capnhat(ban: str, loi: list[str], thumuc: Path | None = None) -> None:
    """0.7.9 lớp 4: kiểm sau cập nhật có điểm chưa đạt thì mở 01 tin đỏ; bản sau kiểm đạt thì đóng tin của bản cũ."""
    khoa = f"capnhat_kiem:{ban}"
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, "capnhat_kiem:"):
            if k != khoa or not loi:
                _dong(w, k, f"Kiểm sau cập nhật bản {ban} đạt" if not loi else f"Đã lên bản {ban}")
        if loi:
            _mo(w, khoa, None, None, None, len(loi))


def quet_quayve_loi(thumuc: Path | None = None) -> None:
    """Y38d: lượt quay về hỏng gần nhất (07 ngày) mở 01 tin đỏ; quay về đạt sau đó thì đóng."""
    from maychu.hethong import antoan
    q = antoan.quay_ve_loi_gan(thumuc)
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, "quayve_loi:"):
            if not q or k != f"quayve_loi:{q['luc']}":
                _dong(w, k, "Đã có lượt quay về mới")
        if q:
            _mo(w, f"quayve_loi:{q['luc']}", None)


SO_LAN_BAO_DRIVE = 3   # QĐ261: đẩy nền lỗi 03 lần liên tiếp (thử lại 05, 10 phút → khoảng 15 phút) thì báo chuông


def quet_drive_nen(thumuc: Path | None = None) -> None:
    """QĐ261, QĐ262: bản chụp trước cập nhật đẩy Drive nền (bản không nâng dữ liệu) lỗi SO_LAN_BAO_DRIVE lần liên tiếp thì
    mở 01 tin vàng "Bản sao Drive lỗi"; đẩy đủ tệp thì tự đóng. Lần mở đầu ghi 01 dòng F04."""
    from maychu.hethong import capnhat, tiendo
    from maychu.hethong.caidat import thongso
    td = tiendo.doc(thumuc)
    dn = tiendo.drive_nen(td, thumuc) if thongso.drive_bat(thumuc) else None   # QĐ277: tắt thì chuông Drive không mở
    khoa = f"drive_nen:{td.get('den')}" if td else None
    moi = False
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, "drive_nen:"):
            if k != khoa or not dn or dn["da"] >= dn["tong"]:
                _dong(w, k, "Bản sao Drive đã lên đủ tệp" if dn and k == khoa else "Đã có lượt cập nhật mới")
        if dn and dn["da"] < dn["tong"] and dn["lan"] >= SO_LAN_BAO_DRIVE:
            moi = khoa not in _khoa_mo(w, "drive_nen:")
            _mo(w, khoa, None, None, dn["tong"], dn["da"])
    if moi:
        capnhat._ghi_f04("drive_nen_loi", f"{td.get('den')}: {dn['da']:02d}/{dn['tong']:02d} tệp, đã thử {dn['lan']:02d} lần",
                         "loi", "đẩy Drive nền lỗi", thumuc=thumuc)


def bao_cli(goi: str, loai: str, sau: str, thumuc: Path | None = None) -> None:
    """Y46: mở chuông công cụ AI. Khóa "<loại>:<gói>:<bản>[:<bản giữ>]"; 01 gói chỉ 01 chuông còn mở mỗi loại; nâng
    xong thì đóng chuông lỗi cũ của gói đó."""
    khoa = f"{loai}:{goi}:{sau}"
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, f"{loai}:{goi}:") + (_khoa_mo(w, f"cli_loi:{goi}:") if loai == "cli_nang" else []):
            if k != khoa:
                _dong(w, k, "Đã có lượt nâng công cụ AI mới")
        _mo(w, khoa, None, None)


def bao_cli_o(goi: str, ban: str, trong: int, can: int, thumuc: Path | None = None) -> None:
    """QĐ307 Z20 dòng 18: mở 01 chuông cho 01 gói (bản mới hơn thay chuông cũ); số đo cập nhật mỗi lượt."""
    khoa = f"cli_o:{goi}:{ban}"
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, f"cli_o:{goi}:"):
            if k != khoa:
                _dong(w, k, "Đã có lượt nâng công cụ AI mới")
        _mo(w, khoa, None, None, nguong=int(can), giatri=int(trong))


def bao_cli_mang(thumuc: Path | None = None) -> None:
    """QĐ307 Z20 dòng 19: 01 chuông chung cho cả 02 gói."""
    with _Ghi(thumuc) as w:
        _mo(w, "cli_mang", None, None)


def bao_2lop_tat(thumuc: Path | None = None) -> None:
    """QĐ390 (CDA 16g, 16h dòng 4): 01 dòng chuông "Đăng nhập 02 lớp đang tắt", mở suốt lúc tắt."""
    with _Ghi(thumuc) as w:
        _mo(w, KHOA_2LOP_TAT, None, None)


def dong_2lop_tat(lydo: str, thumuc: Path | None = None) -> None:
    """Đóng chuông "đang tắt" khi bật lại, bật lần đầu, lệnh datlai (QĐ393 (2))."""
    with _Ghi(thumuc) as w:
        _dong(w, KHOA_2LOP_TAT, lydo)


def bao_su_kien(loai: str, sau: str, thumuc: Path | None = None) -> None:
    """QĐ634, QĐ636: 01 tin chuông khi đổi tên miền / múi giờ (khóa `loai:giá trị mới`; trùng thì không mở thêm)."""
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, loai):   # tin cũ cùng loại (giá trị trước) đóng, chỉ giữ lần đổi gần nhất
            _dong(w, k, "đổi lại")
        _mo(w, f"{loai}:{sau}", None, None)


def dong_su_kien(lydo: str, thumuc: Path | None = None) -> int:
    """Đóng tin sự kiện khi bấm "Đọc hết" (TẠM – chờ CDA / CPO chốt vòng đời tin sự kiện)."""
    n = 0
    with _Ghi(thumuc) as w:
        for loai in SU_KIEN:
            for k in _khoa_mo(w, loai):
                n += _dong(w, k, lydo)
    return n


def quet_2lop(thumuc: Path | None = None) -> None:
    """Giữ chuông khớp cờ: cờ tắt mà chưa có chuông thì mở, cờ bật mà còn chuông thì đóng (mỗi lượt quét 10 phút)."""
    if thongso.co_2lop_bat(thumuc):
        dong_2lop_tat("Đăng nhập 02 lớp đang bật", thumuc)
    else:
        bao_2lop_tat(thumuc)


def dong_cli(tien_to: str, lydo: str, thumuc: Path | None = None) -> None:
    with _Ghi(thumuc) as w:
        for k in _khoa_mo(w, tien_to):
            _dong(w, k, lydo)


def quet_saoluu(thumuc: Path | None = None) -> None:
    """Lượt sao lưu hằng ngày gần nhất có file lỗi (đỏ). 01 dòng còn mở cho mọi lượt lỗi liên tiếp (lịch thử lại mỗi phút).
    0.8.0 (QĐ227): chỉ đọc `loai` = 'hangngay'; lượt trước cập nhật (`truoc_capnhat`) không che lần sao lưu hằng ngày hỏng."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        gan = cn.execute("SELECT chup_luc FROM saoluu WHERE loai = 'hangngay' ORDER BY chup_luc DESC, rowid DESC LIMIT 1").fetchone()
        loi = cn.execute("SELECT id FROM saoluu WHERE chup_luc = ? AND loai = 'hangngay' AND ketqua = 'loi' LIMIT 1",
                         gan).fetchone() if gan else None
    finally:
        cn.close()
    if not gan:
        return
    with _Ghi(thumuc) as w:
        if loi:
            _mo(w, "saoluu_loi", "saoluu", loi[0])
        else:
            _dong(w, "saoluu_loi", f"Sao lưu đã xong lúc {gan[0][11:16]}")


def quet_maychu(thumuc: Path | None = None) -> None:
    """Ổ cứng dùng quá `nguong_ocung` (đỏ); đóng cảnh báo tệp hoán đổi khi đã xuống dưới ngưỡng (domay mở)."""
    from maychu.hethong.giamsat.domay import NGUONG_SWAP_MB
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        d = cn.execute("SELECT id, tyle_ocung, swap_dung FROM theodoi_maychu ORDER BY luc DESC, rowid DESC LIMIT 1").fetchone()
    finally:
        cn.close()
    if not d:
        return
    nguong = _so(thongso.doc_mot("nguong_ocung", "70", thumuc)) or 70
    pct = (d[1] or 0) / 100   # N02 lưu tỷ lệ × 100
    with _Ghi(thumuc) as w:
        if pct > nguong:
            _mo(w, "ocung_vuot", "theodoi_maychu", d[0], nguong=nguong, giatri=round(pct))
        else:
            _dong(w, "ocung_vuot", "Ổ cứng đã dưới ngưỡng")
        if (d[2] or 0) <= NGUONG_SWAP_MB:
            _dong(w, "swap_vuot_nguong", "Tệp hoán đổi đã dưới ngưỡng")


def quet_banmoi(thumuc: Path | None = None, hoi_kho: bool = False) -> None:
    """Có bản phần mềm mới (xanh); bản đó đã cài hoặc có bản mới hơn thì đóng.
    `hoi_kho` (lịch nền, mỗi 05 phút, QĐ174): hỏi kho ngay, tránh lệch mốc với bộ nhớ 05 phút (lệch thì thực tế
    thành 10 phút); mở chuông thì dùng kết quả nhớ, đã quá 05 phút mới hỏi."""
    from maychu.hethong import capnhat
    kq = capnhat.kiem_tra(bat_buoc=hoi_kho)   # không kết nối được thì giữ nguyên
    if kq.get("loi") and not kq.get("ban_moi"):
        return
    dang, moi = kq["ban_dang"], kq.get("ban_moi")
    with _Ghi(thumuc) as w:
        for khoa in _khoa_mo(w, "banmoi:"):
            ban = khoa.split(":", 1)[1]
            if capnhat._khoa_so(ban) <= capnhat._khoa_so(dang):
                _dong(w, khoa, f"Đã cài bản {dang}")
            elif kq["co_ban_moi"] and ban != moi:
                _dong(w, khoa, f"Có bản mới hơn {moi}")
        if kq["co_ban_moi"]:
            _mo(w, f"banmoi:{moi}", None)


NGUON = (quet_goi, quet_khoa, quet_madaihan, quet_saoluu, quet_maychu, quet_banmoi, quet_drive_nen, quet_2lop)


def quet(thumuc: Path | None = None) -> dict:
    """Quét đủ nguồn; lỗi 01 nguồn không dừng nguồn khác. Trả {tên nguồn: 'dat' | lỗi}."""
    ra = {}
    for f in NGUON:
        try:
            f(thumuc)
            ra[f.__name__] = "dat"
        except Exception as e:   # noqa: BLE001 - lịch nền không được dừng vì 01 nguồn
            log.exception("quét thông báo %s lỗi", f.__name__)
            ra[f.__name__] = type(e).__name__
    return ra


# ---------------- Đọc ----------------
def loc_quyen(nguoi_id: str | None, ds: list[dict]) -> list[dict]:
    """01 hàm lọc quyền duy nhất của chuông (dùng cho cả số và danh sách). GĐ 1 chỉ có Chủ: trả hết (QĐ141).
    Khi làm phân quyền: áp PTD-04 lối 03 tại đây (`bang_nguon` → nhóm Dữ liệu mật, `congty_id`, `shop_id` → F08)."""
    return ds


def _nb(s: str) -> str:
    return s.replace(" ", NB)


def _ten_goi(ma: str) -> str:
    from maychu.hethong.mohinh import dangnhap_goi
    m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", ma or "")
    if not m:
        return "Gói AI"
    return f"{dangnhap_goi.GOI[m.group(1)]['ten']} · {_nb('Tài khoản ' + str(int(m.group(2))))}"


def _ten_khoa(thumuc) -> dict:
    from maychu.hethong.kekhoa import kho
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        return {i: kho.ten_dichvu(dv) for i, dv in cn.execute("SELECT id, dichvu FROM kekhoa")}
    finally:
        cn.close()


def _gio_saoluu(ids: list[str], thumuc) -> dict:
    if not ids:
        return {}
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        return dict(cn.execute(f"SELECT id, chup_luc FROM saoluu WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall())
    finally:
        cn.close()


def _chu(loai: str, khoa: str, d: dict, ten_khoa: dict, gio_sl: dict) -> str:
    sau = khoa.split(":", 1)[1] if ":" in khoa else ""
    gt, ng = d["giatri"], d["nguong"]
    if loai == "goi_hetphien":
        return f"{_ten_goi(sau)} hết phiên {_nb('đăng nhập')}"
    if loai == "hanmuc_tuan":
        return f"{_ten_goi(sau)} đã dùng {gt}% {_nb('hạn mức tuần')}"
    if loai in ("khoa_hethan", "khoa_saphethan"):
        ten = f"Khóa {ten_khoa.get(sau, 'kết nối')}"
        if loai == "khoa_hethan":
            return f"{ten} đã {_nb('hết hạn')}"
        return f"{ten} {_nb('hết hạn')} hôm nay" if not gt else f"{ten} còn {_nb(f'{gt:02d} ngày')} {_nb('hết hạn')}"
    if loai in ("madaihan_hethan", "madaihan_saphethan"):
        ten = f"Mã dài hạn {_ten_goi(sau.split(':')[0])}"
        if loai == "madaihan_hethan":
            return f"{ten} đã {_nb('hết hạn')}: lấy mã mới ở {_nb('Mô hình AI')}"
        return f"{ten} {_nb('hết hạn')} hôm nay" if not gt else f"{ten} còn {_nb(f'{gt:02d} ngày')} {_nb('hết hạn')}"
    if loai == "saoluu_loi":
        luc = gio_sl.get(d["dong_nguon_id"]) or d["tao_luc"] or ""
        if muigio.ngay_cua(luc) == muigio.hom_nay():   # ③ QĐ636
            return f"Sao lưu lúc {luc[11:16]} không xong"
        return f"Sao lưu không xong từ {luc[11:16]} {_nb(f'ngày {luc[8:10]}/{luc[5:7]}')}"   # S3 (K-TB3): lỗi từ hôm trước
    if loai == "ocung_vuot":
        return f"Ổ cứng máy chủ dùng {gt}%, quá {_nb(f'ngưỡng {ng}%')}"
    if loai == "swap_vuot_nguong":
        return f"Máy chủ dùng tệp hoán đổi {_nb(f'{gt} MB')}, quá {_nb(f'{ng} MB')}"
    if loai == "banmoi":
        return f"Có bản mới {sau}"
    if loai == "quayve_loi":   # QĐ219 A4, A5
        from maychu.hethong import antoan
        q = antoan.quay_ve_loi_gan(luc=sau)
        return q["chu_chuong"] if q else "Quay về bản trước chưa được"
    if loai in ("cli_nang", "cli_loi"):   # QĐ271 Z20 dòng 14, 15 (chữ đã duyệt)
        from maychu.hethong.mohinh import nangcli
        goi, ban, *giu = sau.split(":")
        ten = nangcli.TEN_GOI.get(goi, goi)
        if loai == "cli_nang":
            return f"Đã nâng {ten} lên {ban}"
        if giu and giu[0] == "goi":   # QĐ307 dòng 15b: về bản trong gói; không đọc được số thì câu không số
            ve = f"{giu[1]} trong gói" if len(giu) > 1 and giu[1] else "trong gói"
        else:
            ve = giu[0] if giu and giu[0] not in ("", "None") else "trong gói"
        return f"{ten} {ban} chưa đạt kiểm thử, đã về bản {ve}"
    if loai == "cli_o":   # QĐ307 dòng 18 (số đo lúc kiểm, cách ghi như lớp 1 ổ trống)
        from maychu.hethong import antoan
        from maychu.hethong.mohinh import nangcli
        goi, ban = (sau.split(":") + [""])[:2]
        return (f"Chưa nâng {nangcli.TEN_GOI.get(goi, goi)} lên {ban}: ổ trống còn {antoan.chu_dungluong(_so(gt))},"
                f" cần {antoan.chu_dungluong(_so(ng))}. Dọn ổ máy chủ; phần mềm tự thử lại lúc {nangcli.GIO_KIEM:02d}:00.")
    if loai == "cli_mang":   # QĐ307 dòng 19
        from maychu.hethong.mohinh import nangcli
        return ("Chưa kiểm được bản mới của công cụ AI: không kết nối được máy chủ của hãng. Công cụ AI vẫn chạy bản"
                f" đang dùng; phần mềm tự thử lại lúc {nangcli.GIO_KIEM:02d}:00.")
    if loai == "drive_nen":   # QĐ262 nguyên văn: "Bản sao Drive sau cập nhật {bản} chưa lên: {k}/07 tệp, đã thử 03 lần"
        return (f"Bản sao Drive sau cập nhật {sau} chưa lên: {_so(gt):02d}/{_so(ng):02d} tệp,"
                f" đã thử {_nb(f'{SO_LAN_BAO_DRIVE:02d} lần')}")
    if loai == "dangnhap_2lop_tat":   # QĐ397 bảng chữ màn 09 dòng 12
        from maychu.hethong.taikhoan import nguoidung
        return nguoidung.CHU_2LOP["chuong"]
    if loai == "capnhat_kiem":   # QĐ218 dòng 47: "Kiểm sau cập nhật bản 0.3.0: lịch chạy nền chưa bật"
        from maychu.hethong import capnhat
        ly = next((x["kiem"]["chu"].split(" · ", 1)[-1] for x in capnhat.lich_su() if x["ban"] == sau and x.get("kiem")), "")
        return f"Kiểm sau cập nhật bản {sau}: {ly}" if ly else f"Kiểm sau cập nhật bản {sau} chưa đạt"
    if loai == "tenmien_doi":   # TẠM (QĐ648): chữ tin chuông – CPO hỏi anh
        return f"Đã đổi tên miền riêng: {sau}" if sau else "Đã bỏ tên miền riêng"
    if loai == "muigio_doi":   # TẠM (QĐ648)
        return f"Đã đổi múi giờ sang {sau}"
    return "Có cảnh báo mới"


def danh_sach(nguoi_id: str | None = None, thumuc: Path | None = None) -> dict:
    """Ngăn Thông báo (Z7b): dòng D03 còn mở qua `loc_quyen`; nhóm Mới (sau mốc đọc) rồi Đã xem, còn mở; trong nhóm
    đỏ → vàng → xanh rồi mới trước. Số trên chuông = số dòng Mới."""
    moc = thongso.doc_moc_doc(thumuc)
    cot = ("id", "khoa_chongtrung", "nguong", "giatri", "bang_nguon", "dong_nguon_id", "tao_luc")
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        dong = [dict(zip(cot, r)) for r in cn.execute(
            f"SELECT {', '.join(cot)} FROM canhbao WHERE loai = 'sukien' AND trangthai IN {CON_MO}")]
    finally:
        cn.close()
    dong = loc_quyen(nguoi_id, dong)
    ten_khoa = _ten_khoa(thumuc) if any((d["khoa_chongtrung"] or "").startswith("khoa_") for d in dong) else {}
    gio_sl = _gio_saoluu([d["dong_nguon_id"] for d in dong if d["khoa_chongtrung"] == "saoluu_loi" and d["dong_nguon_id"]], thumuc)
    ds = []
    for d in dong:
        khoa = d["khoa_chongtrung"] or ""
        loai = khoa.split(":", 1)[0]
        muc, icon, di, cuon, noi = LOAI.get(loai, ("do", "circle-alert", "03", None, "Bảng điều hành"))
        ds.append({"id": d["id"], "loai": loai, "muc": muc, "icon": icon, "di": di, "cuon": cuon, "noi": noi,
                   "chu": _chu(loai, khoa, d, ten_khoa, gio_sl), "luc": d["tao_luc"],
                   "moi": not moc or (d["tao_luc"] or "") > moc})
    ds.sort(key=lambda x: x["luc"] or "", reverse=True)
    ds.sort(key=lambda x: (not x["moi"], THU_TU_MUC[x["muc"]]))
    return {"ds": ds, "so_moi": sum(1 for x in ds if x["moi"]), "moc_doc": moc}
