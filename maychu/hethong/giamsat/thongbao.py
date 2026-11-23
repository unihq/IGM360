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

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.caidat import thongso

log = logging.getLogger("igm360.thongbao")
NB = " "   # dấu cách không ngắt (bản vẽ Z7b: "Tài khoản 1", "hết hạn", "05 ngày"… không tách khi xuống dòng)
CON_MO = ("moi", "dabao", "dagiao_task")
MAYCHU = ("03", "o-maychu", "Bảng điều hành › Máy chủ")
# tiền tố khoá: (mức, icon, màn đích, chỗ cuộn tới, nơi mở). Mức: do = Cần xử lý ngay, xem = Sắp tới hạn, tin = Tin mới
LOAI = {
    "goi_hetphien": ("do", "brain-circuit", "13", None, "Mô hình AI"),
    "hanmuc_tuan": ("xem", "hourglass", "13", None, "Mô hình AI"),
    "khoa_hethan": ("do", "key-round", "ketkhoa", None, "Cài đặt › Két khoá"),
    "khoa_saphethan": ("xem", "key-round", "ketkhoa", None, "Cài đặt › Két khoá"),
    "saoluu_loi": ("do", "database-backup", *MAYCHU),
    "ocung_vuot": ("do", "hard-drive", *MAYCHU),
    "swap_vuot_nguong": ("do", "memory-stick", *MAYCHU),
    "banmoi": ("tin", "cloud-download", "capnhat", None, "Cài đặt › Cập nhật"),
}
THU_TU_MUC = {"do": 0, "xem": 1, "tin": 2}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _so(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# ---------------- Ghi D03 ----------------
def _mo(cn, khoa: str, bang: str | None, dong_id: str | None = None, nguong=None, giatri=None) -> str:
    """Mở 01 dòng còn mở theo khoá; đã có thì chỉ cập nhật số (giữ giờ tạo, giữ dòng nguồn đầu tiên)."""
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
    bay = datetime.now(MUIGIO_VN)
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
    """Khoá kết nối đã hết hạn (đỏ); còn ≤ `songay_baotruoc_khoa_hethan` ngày (vàng)."""
    from maychu.hethong.kekhoa import kho
    n = _so(thongso.doc_mot("songay_baotruoc_khoa_hethan", "5", thumuc))
    ds = kho.danh_sach(thumuc, n)
    with _Ghi(thumuc) as w:
        con = set()
        for k in ds:
            con.add(k["id"])
            het, sap = f"khoa_hethan:{k['id']}", f"khoa_saphethan:{k['id']}"
            if k["tinhtrang"] == "hethan":
                _mo(w, het, "kekhoa", k["id"])
                _dong(w, sap, "Khoá đã hết hạn")
            elif k["tinhtrang"] == "saphet":
                _mo(w, sap, "kekhoa", k["id"], nguong=n, giatri=k["con_ngay"])
                _dong(w, het, "Đã gia hạn khoá")
            else:
                _dong(w, het, "Đã gia hạn khoá")
                _dong(w, sap, "Đã gia hạn khoá")
        for khoa in _khoa_mo(w, "khoa_hethan:") + _khoa_mo(w, "khoa_saphethan:"):
            if khoa.split(":", 1)[1] not in con:
                _dong(w, khoa, "Khoá đã xoá")


def quet_saoluu(thumuc: Path | None = None) -> None:
    """Lượt sao lưu gần nhất có file lỗi (đỏ). 01 dòng còn mở cho mọi lượt lỗi liên tiếp (lịch thử lại mỗi phút)."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        gan = cn.execute("SELECT chup_luc FROM saoluu ORDER BY chup_luc DESC, rowid DESC LIMIT 1").fetchone()
        loi = cn.execute("SELECT id FROM saoluu WHERE chup_luc = ? AND ketqua = 'loi' LIMIT 1", gan).fetchone() if gan else None
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


def quet_banmoi(thumuc: Path | None = None) -> None:
    """Có bản phần mềm mới (xanh); bản đó đã cài hoặc có bản mới hơn thì đóng."""
    from maychu.hethong import capnhat
    kq = capnhat.kiem_tra()   # nhớ 06 giờ; không kết nối được thì giữ nguyên
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


NGUON = (quet_goi, quet_khoa, quet_saoluu, quet_maychu, quet_banmoi)


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
        return {i: kho.TEN_DICHVU.get(dv, dv) for i, dv in cn.execute("SELECT id, dichvu FROM kekhoa")}
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
        return f"{_ten_goi(sau)} hết phiên đăng nhập"
    if loai == "hanmuc_tuan":
        return f"{_ten_goi(sau)} đã dùng {gt}% {_nb('hạn mức tuần')}"
    if loai in ("khoa_hethan", "khoa_saphethan"):
        ten = f"Khoá {ten_khoa.get(sau, 'kết nối')}"
        if loai == "khoa_hethan":
            return f"{ten} đã {_nb('hết hạn')}"
        return f"{ten} {_nb('hết hạn')} hôm nay" if not gt else f"{ten} còn {_nb(f'{gt:02d} ngày')} {_nb('hết hạn')}"
    if loai == "saoluu_loi":
        luc = gio_sl.get(d["dong_nguon_id"]) or d["tao_luc"] or ""
        return f"Sao lưu lúc {luc[11:16]} không xong"
    if loai == "ocung_vuot":
        return f"Ổ cứng máy chủ dùng {gt}%, quá {_nb(f'ngưỡng {ng}%')}"
    if loai == "swap_vuot_nguong":
        return f"Máy chủ dùng tệp hoán đổi {_nb(f'{gt} MB')}, quá {_nb(f'{ng} MB')}"
    if loai == "banmoi":
        return f"Có bản mới {sau}"
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
