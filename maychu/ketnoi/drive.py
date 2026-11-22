"""Kết nối Google Drive nhánh A (QĐ59, QĐ66): dự án Google riêng của anh (trạng thái "In production"),
xin đúng 01 quyền `drive.file` (chỉ thấy, sửa file do IGM360 tạo ra), máy đẩy thẳng; không dùng service account.

Gọi API bằng httpx (thư viện đã duyệt, QĐ80); không thêm thư viện của Google.
- Mã ứng dụng (client id, client secret) anh dán ở màn 11, cất ở két khoá: dịch vụ `google_oauth_ungdung`.
- Quyền đẩy file (refresh token) cất ở két khoá: dịch vụ `google_drive_lammoi`. Mã truy cập ngắn hạn chỉ giữ trong bộ nhớ.
- Tệp đẩy lên thư mục `IGM360_Saoluu` do IGM360 tạo trên Drive của anh.
- Đẩy theo hàng chờ M01; lỗi thì thử lại sau 05, 10, 20... phút, tối đa 06 giờ; đẩy xong mới xoá tệp tạm trên VPS.
"""
import json
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx

from maychu.dulieu import ketnoi, phienban
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import kho

URL_XIN = "https://accounts.google.com/o/oauth2/v2/auth"
URL_MA = "https://oauth2.googleapis.com/token"
URL_API = "https://www.googleapis.com/drive/v3/files"
URL_TAI = "https://www.googleapis.com/upload/drive/v3/files"
PHAMVI = "https://www.googleapis.com/auth/drive.file"
THUMUC_DRIVE = "IGM360_Saoluu"
DV_UNGDUNG = "google_oauth_ungdung"
DV_LAMMOI = "google_drive_lammoi"
MA_KETNOI = "google_drive"
HAN_TRANGTHAI_GIAY = 600
THU_LAI_PHUT, THU_LAI_TOIDA_PHUT = 5, 360

_TRANGTHAI: dict[str, dict] = {}   # mã chống giả (state) → người bấm, hạn; dùng 01 lần
_MA_TRUYCAP: dict = {}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _client(client):
    return client or httpx.Client(timeout=60)


def luu_ungdung(client_id: str, client_secret: str, thumuc: Path | None = None) -> None:
    client_id, client_secret = client_id.strip(), client_secret.strip()
    if not client_id.endswith(".apps.googleusercontent.com") or not client_secret:
        raise ValueError("Mã ứng dụng chưa đúng: client ID phải kết thúc bằng .apps.googleusercontent.com")
    gt = json.dumps({"client_id": client_id, "client_secret": client_secret})
    cu = kho.tim(DV_UNGDUNG, thumuc)
    if cu:
        kho.doi(cu, gt, thumuc)
    else:
        kho.cat(DV_UNGDUNG, gt, thumuc)


def _ungdung(thumuc) -> dict:
    ma = kho.tim(DV_UNGDUNG, thumuc)
    if not ma:
        raise LookupError("Chưa có mã ứng dụng Google")
    return json.loads(kho.doc(ma, thumuc))


def bat_dau(duong_ve: str, nguoi_id: str, thumuc: Path | None = None) -> str:
    """Đường dẫn trang xin quyền của Google; mã chống giả gắn với người bấm, hạn 10 phút, dùng 01 lần."""
    ud = _ungdung(thumuc)
    bay = time.time()
    for k in [k for k, v in _TRANGTHAI.items() if v["het"] < bay]:
        _TRANGTHAI.pop(k, None)
    st = secrets.token_urlsafe(24)
    _TRANGTHAI[st] = {"nguoi_id": nguoi_id, "het": bay + HAN_TRANGTHAI_GIAY, "duong_ve": duong_ve}
    return URL_XIN + "?" + urlencode({"client_id": ud["client_id"], "redirect_uri": duong_ve, "response_type": "code",
                                      "scope": PHAMVI, "access_type": "offline", "prompt": "consent",
                                      "include_granted_scopes": "false", "state": st})


def ve_trang(code: str, state: str, thumuc: Path | None = None, client=None) -> dict:
    """Google trả về sau khi anh đồng ý: đổi mã lấy quyền đẩy file, cất két khoá, ghi K01."""
    v = _TRANGTHAI.pop(state or "", None)
    if not v or v["het"] < time.time():
        raise PermissionError("Phiên kết nối đã hết hạn hoặc không phải do IGM360 tạo; bấm Kết nối lại")
    ud = _ungdung(thumuc)
    c = _client(client)
    r = c.post(URL_MA, data={"code": code, "client_id": ud["client_id"], "client_secret": ud["client_secret"],
                             "redirect_uri": v["duong_ve"], "grant_type": "authorization_code"})
    if r.status_code != 200:
        raise RuntimeError(f"Google không cấp quyền (mã {r.status_code})")
    kq = r.json()
    if PHAMVI not in kq.get("scope", "").split():
        raise RuntimeError("Google cấp sai quyền: cần đúng quyền chỉ trên file IGM360 tạo ra")
    if not kq.get("refresh_token"):
        raise RuntimeError("Google không trả quyền dài hạn; vào tài khoản Google gỡ IGM360 rồi Kết nối lại")
    _MA_TRUYCAP.update(ma=kq["access_token"], het=time.time() + int(kq.get("expires_in", 3600)) - 60)
    cu = kho.tim(DV_LAMMOI, thumuc)
    if cu:
        kho.doi(cu, kq["refresh_token"], thumuc)
        khoa_id = cu
    else:
        khoa_id = kho.cat(DV_LAMMOI, kq["refresh_token"], thumuc, nguoi_nhap=v["nguoi_id"])
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        bay = _bay_gio()
        d = cn.execute("SELECT id FROM ketnoi WHERE ma = ?", (MA_KETNOI,)).fetchone()
        if d:
            cn.execute("UPDATE ketnoi SET trangthai = 'dung', khoa_id = ?, trangthai_phien = 'dang_noi', lan_battay_cuoi = ?,"
                       " loi_cuoi = NULL WHERE id = ?", (khoa_id, bay, d[0]))
            ma = d[0]
        else:
            ma = phienban.them(cn, "ketnoi", {"ma": MA_KETNOI, "ten": "Google Drive", "hieuluc_tu": bay[:10], "phienban": 1,
                                              "nguoi_khai": v["nguoi_id"], "tao_luc": bay, "mau_ketnoi": "google_drive.json",
                                              "cach_noi": "ketnoi_chinhthuc", "khoa_id": khoa_id,
                                              "trangthai_phien": "dang_noi", "lan_battay_cuoi": bay})
    finally:
        cn.close()
    return {"ketnoi_id": ma}


def _ma(thumuc, c) -> str:
    if _MA_TRUYCAP.get("het", 0) > time.time():
        return _MA_TRUYCAP["ma"]
    ud, ma_lammoi = _ungdung(thumuc), kho.tim(DV_LAMMOI, thumuc)
    if not ma_lammoi:
        raise LookupError("Chưa kết nối Drive")
    r = c.post(URL_MA, data={"client_id": ud["client_id"], "client_secret": ud["client_secret"],
                             "refresh_token": kho.doc(ma_lammoi, thumuc), "grant_type": "refresh_token"})
    if r.status_code != 200:
        _ghi_loi(thumuc, "Google từ chối quyền đẩy file (có thể anh đã gỡ quyền); bấm Kết nối lại", "mat_quyen")
        raise PermissionError("mat_quyen")
    kq = r.json()
    _MA_TRUYCAP.update(ma=kq["access_token"], het=time.time() + int(kq.get("expires_in", 3600)) - 60)
    return _MA_TRUYCAP["ma"]


def _ghi_loi(thumuc, loi: str, phien: str | None = None) -> None:
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        cn.execute("UPDATE ketnoi SET loi_cuoi = ?, trangthai_phien = coalesce(?, trangthai_phien) WHERE ma = ?",
                   (loi[:300], phien, MA_KETNOI))
    finally:
        cn.close()


def _thu_muc(c, h) -> str:
    q = f"name = '{THUMUC_DRIVE}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    r = c.get(URL_API, params={"q": q, "fields": "files(id)", "spaces": "drive"}, headers=h)
    r.raise_for_status()
    ds = r.json().get("files", [])
    if ds:
        return ds[0]["id"]
    r = c.post(URL_API, json={"name": THUMUC_DRIVE, "mimeType": "application/vnd.google-apps.folder"},
               params={"fields": "id"}, headers=h)
    r.raise_for_status()
    return r.json()["id"]


def _ten_tren_drive(tep: Path) -> str:
    return f"{tep.parent.name}_{tep.name}"   # ví dụ 2026-11-22_Dulieu_Chinh.sqlite3.mahoa


def dang_noi(thumuc: Path | None = None) -> bool:
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        d = cn.execute("SELECT trangthai FROM ketnoi WHERE ma = ?", (MA_KETNOI,)).fetchone()
    finally:
        cn.close()
    return bool(d and d[0] == "dung" and kho.tim(DV_LAMMOI, thumuc))


def day_hang_cho(thumuc: Path | None = None, client=None, gioi_han: int = 20) -> dict:
    """Đẩy các dòng M01 đến lượt. Trả về số tệp đã đẩy, lỗi."""
    if not dang_noi(thumuc):
        return {"day": 0, "loi": 0, "lydo": "chua_ket_noi"}
    bay = _bay_gio()
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        dong = cn.execute("SELECT id, duongdan_tam, so_lan_thu FROM cho_day_drive WHERE trangthai IN ('cho', 'loi')"
                          " AND (lan_thu_ke IS NULL OR lan_thu_ke <= ?) ORDER BY tao_luc LIMIT ?", (bay, gioi_han)).fetchall()
    finally:
        cn.close()
    if not dong:
        return {"day": 0, "loi": 0}
    c = _client(client)
    day = loi = 0
    try:
        h = {"Authorization": f"Bearer {_ma(thumuc, c)}"}
        cha = _thu_muc(c, h)
    except Exception as e:  # noqa: BLE001 - mất quyền, mất mạng: để lượt sau
        if not isinstance(e, PermissionError):
            _ghi_loi(thumuc, f"Không tới được Google Drive: {type(e).__name__}")
        return {"day": 0, "loi": len(dong), "lydo": "khong_toi_duoc"}
    for ma, duong, lan in dong:
        tep = Path(duong)
        _dat(thumuc, ma, trangthai="dangday")
        try:
            if not tep.exists():
                raise FileNotFoundError("tệp chờ đẩy không còn trên máy")
            r = c.post(URL_TAI, params={"uploadType": "resumable"}, headers={**h, "X-Upload-Content-Type": "application/octet-stream"},
                       json={"name": _ten_tren_drive(tep), "parents": [cha]})
            r.raise_for_status()
            r = c.put(r.headers["Location"], content=tep.read_bytes(), headers={"Content-Type": "application/octet-stream"})
            r.raise_for_status()
            _dat(thumuc, ma, trangthai="xong", xong_luc=_bay_gio(), loi_ganhat=None)
            tep.unlink(missing_ok=True)
            day += 1
        except Exception as e:  # noqa: BLE001
            so = (lan or 0) + 1
            cho = min(THU_LAI_PHUT * 2 ** (so - 1), THU_LAI_TOIDA_PHUT)
            ke = (datetime.now(MUIGIO_VN) + timedelta(minutes=cho)).isoformat(timespec="seconds")
            _dat(thumuc, ma, trangthai="loi", so_lan_thu=so, lan_thu_ke=ke, loi_ganhat=f"{type(e).__name__}: {str(e)[:200]}")
            loi += 1
    if day and not loi:
        _ghi_loi_xoa(thumuc)
    return {"day": day, "loi": loi}


def _ghi_loi_xoa(thumuc) -> None:
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        cn.execute("UPDATE ketnoi SET loi_cuoi = NULL, trangthai_phien = 'dang_noi' WHERE ma = ?", (MA_KETNOI,))
    finally:
        cn.close()


def _dat(thumuc, ma: str, **cot) -> None:
    cn = ketnoi.mo("Hotho", thumuc)
    try:
        cn.execute(f"UPDATE cho_day_drive SET {', '.join(f'{k} = ?' for k in cot)} WHERE id = ?", [*cot.values(), ma])
    finally:
        cn.close()


def ngung(thumuc: Path | None = None) -> None:
    """Ngừng: lịch đẩy dừng, khoá giữ ở két, tệp chờ giữ trên máy; bật lại bằng Kết nối lại."""
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        cn.execute("UPDATE ketnoi SET trangthai = 'ngung', trangthai_phien = 'ngung' WHERE ma = ?", (MA_KETNOI,))
    finally:
        cn.close()
    _MA_TRUYCAP.clear()


def tinh_hinh(thumuc: Path | None = None) -> dict:
    """Số cho màn 11: trạng thái kết nối, hàng chờ, lần đẩy gần nhất."""
    cn = ketnoi.mo("Ketnoi", thumuc)
    try:
        k = cn.execute("SELECT id, trangthai, trangthai_phien, lan_battay_cuoi, loi_cuoi FROM ketnoi WHERE ma = ?",
                       (MA_KETNOI,)).fetchone()
    finally:
        cn.close()
    h = ketnoi.mo("Hotho", thumuc)
    try:
        dem = dict(h.execute("SELECT trangthai, count(*) FROM cho_day_drive GROUP BY trangthai").fetchall())
        cho_byte = h.execute("SELECT coalesce(sum(dungluong_byte), 0) FROM cho_day_drive WHERE trangthai IN ('cho', 'loi')").fetchone()[0]
        cuoi = h.execute("SELECT max(xong_luc) FROM cho_day_drive WHERE trangthai = 'xong'").fetchone()[0]
    finally:
        h.close()
    return {"co_ungdung": bool(kho.tim(DV_UNGDUNG, thumuc)), "ketnoi_id": k[0] if k else None,
            "trangthai": k[1] if k else None, "phien": k[2] if k else None, "noi_luc": k[3] if k else None,
            "loi": k[4] if k else None, "hang_cho": {"cho": dem.get("cho", 0), "loi": dem.get("loi", 0),
                                                       "xong": dem.get("xong", 0)},
            "cho_byte": cho_byte, "day_cuoi": cuoi}
