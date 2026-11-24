"""Sao lưu 07 file dữ liệu (thiết kế cơ sở dữ liệu mục 0.1), ghi kết quả vào N01.

Không bao giờ chép thẳng file đang chạy. Mỗi file 05 bước:
  (1) chụp bằng lệnh sao lưu trực tuyến của SQLite ra file tạm;
  (2) PRAGMA integrity_check trên bản chụp, khác "ok" thì dừng cả lượt;
  (3) đổi tên file tạm thành tên chính thức trong 01 lần;
  (4) mã hoá bản chụp ra tệp `.mahoa` (Fernet), khoá sao lưu suy ra từ khoá chủ (HKDF-SHA256), nên chỉ cần
      01 bản khoá chủ anh đã chép về máy là giải mã được bản trên Drive, kể cả khi mất cả VPS;
  (5) xếp tệp `.mahoa` vào hàng chờ đẩy Drive (M01); việc đẩy chạy theo lịch khi đã kết nối Drive
      (maychu/ketnoi/drive.py), đẩy xong mới xoá tệp `.mahoa` trên máy.
      0.8.3 (QĐ277): công tắc "Sao lưu Google Drive" tắt thì bỏ qua bước (5). QĐ279 (luật C): dòng M01 loại `saoluu` đang
      chờ chỉ tồn tại khi tệp còn trên máy; QĐ283: tắt hoặc bật mà chưa nối Drive thì dọn tệp theo luật 03 ngày / 02 lượt,
      không giữ tệp đang chờ.
Bản chụp chưa mã hoá giữ trên máy 03 ngày để khôi phục nhanh (thư mục quyền 700, tệp quyền 600).
"""
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from maychu.dulieu import ketnoi, maso

DUOI_MAHOA = ".mahoa"

MUIGIO_VN = timezone(timedelta(hours=7))
GIU_SO_NGAY = 3  # giữ bản trên máy của 03 ngày gần nhất; bản lâu dài nằm ở Drive


def thumuc_saoluu(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / "saoluu"


def _mabam(duong: Path) -> str:
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def da_co_hom_nay(thumuc: Path | None = None, bay_gio: datetime | None = None) -> bool:
    ngay = (bay_gio or datetime.now(MUIGIO_VN)).strftime("%Y-%m-%d")
    noi = thumuc_saoluu(thumuc) / ngay
    return all((noi / f"{t}.sqlite3").exists() for t in ketnoi.CAC_FILE)


def _khoa_saoluu(thumuc: Path | None = None):
    """Khoá sao lưu = HKDF-SHA256 của khoá chủ (không cất riêng, không nằm trong bản sao lưu)."""
    import base64
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from maychu.hethong.kekhoa import khoachu
    goc = base64.urlsafe_b64decode(khoachu.lay(thumuc))
    return Fernet(base64.urlsafe_b64encode(HKDF(hashes.SHA256(), 32, None, b"igm360-saoluu-v1").derive(goc)))


def ma_hoa_tep(nguon: Path, thumuc: Path | None = None) -> Path:
    dich = nguon.with_name(nguon.name + DUOI_MAHOA)
    tam = dich.with_name(dich.name + ".tam")
    fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(_khoa_saoluu(thumuc).encrypt(nguon.read_bytes()))
    os.replace(tam, dich)
    return dich


def giai_ma_tep(tep_mahoa: Path, tep_khoachu: Path, dich: Path) -> Path:
    """Khôi phục bản tải từ Drive bằng tệp khoá chủ anh giữ (chạy được ở máy bất kỳ có thư viện cryptography)."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        Path(d, ".khoa_chu").write_bytes(Path(tep_khoachu).read_bytes())
        du_lieu = _khoa_saoluu(Path(d)).decrypt(Path(tep_mahoa).read_bytes())
    Path(dich).write_bytes(du_lieu)
    return Path(dich)


def _tep_dang_cho(thumuc: Path) -> set[str]:
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        return {r[0] for r in cn.execute("SELECT duongdan_tam FROM cho_day_drive WHERE trangthai IN ('cho', 'dangday', 'loi')")}
    finally:
        cn.close()


def _giu_tep_cho(thumuc: Path) -> bool:
    """QĐ279, QĐ283: chỉ giữ tệp đang chờ đẩy Drive khi công tắc BẬT và Drive ĐÃ NỐI. Không đọc được thì giữ (an toàn:
    không xoá tệp chưa lên Drive)."""
    from maychu.hethong.caidat import thongso
    from maychu.ketnoi import drive
    try:
        return thongso.drive_bat(thumuc) and drive.dang_noi(thumuc)
    except Exception:  # noqa: BLE001
        return True


CHO_DANG = ("cho", "dangday", "loi")   # PTD-15 6.2 điểm 1: chỉ dòng đang chờ; dòng 'xong' là lịch sử đẩy, giữ


def _don_dong_mat_tep(thumuc: Path) -> int:
    """QĐ279 (luật C): xoá dòng M01 loại `saoluu` đang chờ mà tệp không còn trên máy. Không đụng loại `filegoc`,
    `goi_banghigoc` (QĐ54), không đụng dòng `xong`. Trả số dòng đã xoá."""
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        mat = [r[0] for r in cn.execute("SELECT id, duongdan_tam FROM cho_day_drive WHERE loai = 'saoluu' AND trangthai IN"
                                        " (?, ?, ?)", CHO_DANG).fetchall() if not (r[1] and Path(r[1]).exists())]
        for i in mat:
            cn.execute("DELETE FROM cho_day_drive WHERE id = ? AND loai = 'saoluu'", (i,))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return len(mat)


def _don_ban_cu(goc: Path, thumuc: Path, giu: bool = True) -> None:
    ngay = sorted(p for p in goc.iterdir() if p.is_dir() and len(p.name) == 10)
    cho = _tep_dang_cho(thumuc) if giu else set()
    for p in ngay[:-GIU_SO_NGAY]:
        con = [x for x in p.iterdir() if str(x) in cho]
        if not con:
            shutil.rmtree(p, ignore_errors=True)
            continue
        for x in p.iterdir():  # còn tệp chưa đẩy Drive: giữ tệp đó, xoá phần còn lại
            if x not in con:
                x.unlink(missing_ok=True)


def ten_truoc_capnhat(luc: datetime, ban: str) -> str:
    """Thư mục bản sao trước cập nhật (0.7.9 lớp 5): tên trên Drive thành `<ngày>_truoc_<bản>_<giờ>_<tệp>.mahoa`.
    Y38c R2: thêm giờ phút giây để mỗi lần bấm cập nhật 01 thư mục riêng (không 02 dòng M01 chung 01 tệp)."""
    return f"{luc.strftime('%Y-%m-%d')}_truoc_{ban}_{luc.strftime('%H%M%S')}"


GIU_TRUOC_CAPNHAT = 2   # giữ bản sao trước cập nhật của 02 lần gần nhất trên máy (bản lâu dài ở Drive)


def _don_truoc_capnhat(goc: Path, thumuc: Path, giu: bool = True) -> None:
    cac = sorted((p for p in goc.iterdir() if p.is_dir() and "_truoc_" in p.name), key=lambda p: p.stat().st_mtime)
    cho = _tep_dang_cho(thumuc) if giu else set()
    for p in cac[:-GIU_TRUOC_CAPNHAT]:
        if not any(str(x) in cho for x in p.iterdir()):
            shutil.rmtree(p, ignore_errors=True)


def chay(thumuc: Path | None = None, bay_gio: datetime | None = None, truoc_ban: str | None = None, bao=None) -> dict:
    """Sao lưu lần lượt 07 file. Trả về {'ketqua': 'xong_tren_may' | 'loi', 'file': [...], 'noi': thư mục}.
    `truoc_ban` (0.7.9 lớp 5, QĐ213): lượt chụp ngay trước khi gửi lệnh cập nhật lên bản đó, vào thư mục riêng
    (không đè bản hằng ngày, không làm `da_co_hom_nay` đúng). `bao(i, n)`: 0.8.1 (QĐ251) báo đã chụp xong tệp i/n."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    luc = bay_gio or datetime.now(MUIGIO_VN)
    goc = thumuc_saoluu(thumuc)
    noi = goc / (ten_truoc_capnhat(luc, truoc_ban) if truoc_ban else luc.strftime("%Y-%m-%d"))
    noi.mkdir(parents=True, exist_ok=True)
    os.chmod(goc, 0o700)
    os.chmod(noi, 0o700)
    dong_n01, ketqua_chung = [], "xong_tren_may"
    loai = _loai_n01(thumuc, truoc_ban)
    from maychu.hethong.caidat import thongso
    drive_bat = thongso.drive_bat(thumuc)
    for ten in ketnoi.CAC_FILE:
        # Dịp ghi ở `ketqua_tungbuoc_json` khoá "dip" = "truoc_capnhat" (CDA C1, Y38). Từ lược đồ bản 4 (QĐ227) cột `loai`
        # = 'truoc_capnhat'; Nhatky còn lược đồ 3 (chế độ an toàn sau lần nâng hỏng) thì vẫn 'hangngay' + `dip` (V1b).
        buoc = {"dip": "truoc_capnhat", "ban": truoc_ban} if truoc_ban else {}
        tam = noi / f"{ten}.sqlite3.tam"
        chinh = noi / f"{ten}.sqlite3"
        kiemtra = None
        try:
            nguon = ketnoi.mo(ten, thumuc)
            dich = sqlite3.connect(tam)
            try:
                nguon.backup(dich)
            finally:
                dich.close()
                nguon.close()
            os.chmod(tam, 0o600)
            buoc["1_chup"] = "dat"
            cn = sqlite3.connect(tam)
            try:
                kiemtra = cn.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                cn.close()
            if kiemtra != "ok":
                buoc["2_kiemtra"] = "loi"
                raise RuntimeError(f"integrity_check: {kiemtra}")
            buoc["2_kiemtra"] = "dat"
            os.replace(tam, chinh)
            buoc["3_doiten"] = "dat"
            ma_hoa_tep(chinh, thumuc)
            buoc["4_mahoa"] = "dat"
            buoc["5_day_drive"] = "cho_day" if drive_bat else "bo_qua_drive_tat"   # QĐ277: tắt thì không xếp hàng chờ
            ketqua = "xong_tren_may"
        except Exception as loi:  # ghi lại rồi dừng cả lượt
            tam.unlink(missing_ok=True)
            buoc["loi"] = str(loi)[:300]
            ketqua = ketqua_chung = "loi"
        dong_n01.append({
            "id": maso.tao(), "loai": loai, "file_dulieu": ten,
            "chup_luc": luc.isoformat(timespec="seconds"), "cach_chup": "backup_api",
            "kiemtra": kiemtra, "mabam": _mabam(chinh) if ketqua != "loi" else None,
            "dungluong_byte": chinh.stat().st_size if ketqua != "loi" else None,
            "noi_luu": str(chinh) if ketqua != "loi" else None,
            "ketqua_tungbuoc_json": json.dumps(buoc, ensure_ascii=False), "ketqua": ketqua,
        })
        if bao and ketqua != "loi":
            try:
                bao(len(dong_n01), len(ketnoi.CAC_FILE))
            except Exception:  # noqa: BLE001 - báo tiến độ lỗi không chặn sao lưu
                pass
        if ketqua == "loi":
            break
    _ghi_n01(thumuc, dong_n01)
    if drive_bat:   # QĐ283: bật mà chưa nối vẫn xếp hàng chờ (nối Drive trong 03 ngày thì bản còn trên máy vẫn lên)
        _xep_cho_drive(thumuc, dong_n01, noi, luc)
    if ketqua_chung != "loi":
        giu = _giu_tep_cho(thumuc)
        _don_ban_cu(goc, thumuc, giu)
        _don_truoc_capnhat(goc, thumuc, giu)
        _don_dong_mat_tep(thumuc)   # QĐ279: xoá tệp nào thì xoá dòng chờ trỏ tệp đó trong cùng lượt
    return {"ketqua": ketqua_chung, "file": dong_n01, "noi": noi}


def _loai_n01(thumuc: Path, truoc_ban: str | None) -> str:
    """QĐ227, V1b: 'truoc_capnhat' chỉ khi tệp Nhatky đã ở lược đồ ≥ 4 (CHECK bản 3 không nhận giá trị này)."""
    if not truoc_ban:
        return "hangngay"
    try:
        cn = ketnoi.mo("Nhatky", thumuc)
        try:
            ban = cn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            cn.close()
    except sqlite3.Error:
        ban = 0
    return "truoc_capnhat" if ban >= 4 else "hangngay"


def _ghi_n01(thumuc: Path, dong: list) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        cot = list(dong[0].keys()) if dong else []
        for d in dong:
            cn.execute(f"INSERT INTO saoluu ({', '.join(cot)}) VALUES ({', '.join('?' * len(cot))})",
                       [d[c] for c in cot])
        cn.execute("COMMIT")
    finally:
        cn.close()


def _xep_cho_drive(thumuc: Path, dong_n01: list, noi: Path, luc: datetime) -> None:
    """Bước 5: mỗi tệp đã mã hoá 01 dòng M01 trạng thái 'cho'."""
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        for d in dong_n01:
            tep = noi / f"{d['file_dulieu']}.sqlite3{DUOI_MAHOA}"
            if d["ketqua"] == "loi" or not tep.exists():
                continue
            cn.execute("INSERT INTO cho_day_drive (id, loai, saoluu_id, duongdan_tam, dungluong_byte, trangthai, so_lan_thu, tao_luc)"
                       " VALUES (?, 'saoluu', ?, ?, ?, 'cho', 0, ?)",
                       (maso.tao(), d["id"], str(tep), tep.stat().st_size, luc.isoformat(timespec="seconds")))
        cn.execute("COMMIT")
    finally:
        cn.close()


def _dem_tep(goc: Path) -> tuple[int, int]:
    so = byte = 0
    if goc.is_dir():
        for duong, _t, ds in os.walk(goc):
            for ten in ds:
                try:
                    byte += (Path(duong) / ten).stat().st_size
                    so += 1
                except OSError:
                    pass
    return so, byte


def don_khi_khoidong(thumuc: Path | None = None) -> dict:
    """QĐ279 lượt dọn 01 lần khi bản mới chạy (PTD-15 6.2 điểm 3): dọn tệp đã dồn theo luật 03 ngày / 02 lượt (QĐ283) và
    các dòng chờ mất tệp. Chạy lại không đổi gì; chỉ ghi 01 dòng F04 khi có dọn. Không gọi ở chế độ an toàn (khoidong)."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    goc = thumuc_saoluu(thumuc)
    truoc = _dem_tep(goc)
    if goc.is_dir():
        giu = _giu_tep_cho(thumuc)
        _don_ban_cu(goc, thumuc, giu)
        _don_truoc_capnhat(goc, thumuc, giu)
    dong = _don_dong_mat_tep(thumuc)
    sau = _dem_tep(goc)
    kq = {"dong": dong, "tep": truoc[0] - sau[0], "byte": truoc[1] - sau[1]}
    if dong or kq["tep"]:
        from maychu.hethong import nhatky
        nhatky.ghi("saoluu", "don_tep_don", f"xoá {kq['dong']:02d} dòng chờ mất tệp · {kq['tep']:02d} tệp"
                   f" · giải phóng {kq['byte']} byte", thumuc=thumuc)
    return kq


# ---------------- 0.8.3 D1 (QĐ281, QĐ284; PTD-15 mục 6.3): bản sao trước khi nâng `truoc_nangcap_vNN` ----------------
GIU_TRUOC_NANG_NGAY = 30   # QĐ281: giữ bản của lần nâng gần nhất 30 ngày
DAU_TRUOC_NANG = "truoc_nangcap_v"


def _thumuc_truoc_nang(goc: Path) -> list[tuple[int, Path]]:
    ra = []
    for p in (goc.iterdir() if goc.is_dir() else []):
        so = p.name[len(DAU_TRUOC_NANG):] if p.name.startswith(DAU_TRUOC_NANG) else ""
        if p.is_dir() and so.isdigit():
            ra.append((int(so), p))
    return sorted(ra)


def _kiem_dat(ban: str | None, thumuc: Path) -> bool:
    """D1-2: lượt "Kiểm sau cập nhật" GẦN NHẤT của bản `ban` đã đạt (F04 capnhat / kiem_saunang, như capnhat.lich_su)."""
    if not ban:
        return False
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        d = cn.execute("SELECT ketqua FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'kiem_saunang'"
                       " AND thamso_tomtat LIKE ? ORDER BY luc DESC LIMIT 1", (ban + " · %",)).fetchone()
    finally:
        cn.close()
    return bool(d and d[0] == "dat")


def don_truoc_nangcap(thumuc: Path | None = None, bay_gio: datetime | None = None) -> list[dict]:
    """D1 (QĐ281): giữ bản sao trước khi nâng của lần nâng gần nhất 30 ngày, tính từ `nang_luocdo.luc` (D1-1); bản cũ hơn
    chỉ xoá khi lần nâng gần nhất đã "Kiểm sau cập nhật" đạt (D1-2); không chạy ở chế độ an toàn, không chạy khi còn cờ
    quay về hay đang nâng (D1-4); mỗi thư mục xoá ghi 01 dòng F04 (D1-5). Không đọc được giờ nâng thì không xoá bản mới
    nhất."""
    from maychu.hethong import antoan, nhatky
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    tt = antoan.doc(thumuc)
    if antoan.CHE_DO["an_toan"] or tt.get("chay_ban_truoc") or tt.get("dang_nang"):
        return []
    cac = _thumuc_truoc_nang(thumuc_saoluu(thumuc))
    if not cac:
        return []
    n = tt.get("nang_luocdo") or {}
    moi_nhat = cac[-1][0]
    xoa = []
    if n.get("den") == moi_nhat and _kiem_dat(n.get("ban"), thumuc):
        xoa += [(p, "cũ hơn bản v%02d" % moi_nhat) for _so, p in cac[:-1]]
    try:
        luc = datetime.fromisoformat(n["luc"]) if n.get("den") == moi_nhat and n.get("luc") else None
    except (TypeError, ValueError):
        luc = None
    if luc is not None:
        if luc.tzinfo is None:
            luc = luc.replace(tzinfo=MUIGIO_VN)
        if (bay_gio or datetime.now(MUIGIO_VN)) - luc > timedelta(days=GIU_TRUOC_NANG_NGAY):
            xoa.append((cac[-1][1], f"quá {GIU_TRUOC_NANG_NGAY} ngày sau lần nâng"))
    ra = []
    for p, lydo in xoa:
        so, byte = _dem_tep(p)
        shutil.rmtree(p, ignore_errors=True)
        if p.exists():
            continue
        nhatky.ghi("saoluu", "xoa_truoc_nangcap", f"{p.name} · {lydo} · {so:02d} tệp · {byte} byte", thumuc=thumuc)
        ra.append({"thumuc": p.name, "lydo": lydo, "byte": byte})
    return ra


def ngay_xoa_truoc_nangcap(ten: str, thumuc: Path | None = None) -> str | None:
    """QĐ287: giờ thật lúc xoá thư mục `ten` (dòng F04 do `don_truoc_nangcap` ghi), cho dòng báo `qv_het_han`."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        d = cn.execute("SELECT luc FROM nhatky_thaotac WHERE congcu = 'saoluu' AND lenhcon = 'xoa_truoc_nangcap'"
                       " AND thamso_tomtat LIKE ? ORDER BY luc DESC LIMIT 1", (ten + " · %",)).fetchone()
    finally:
        cn.close()
    return d[0] if d else None
