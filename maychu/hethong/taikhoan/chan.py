"""Chặn đoán mật khẩu (QĐ90, anh duyệt 18:48).

- Sai liền 05 lần (mật khẩu hoặc mã 02 lớp) trong 15 phút từ 01 địa chỉ IP: khoá địa chỉ đó 15 phút.
  Bị khoá lại trong 24 giờ thì thời gian khoá gấp đôi (30, 60, 120 phút...), tối đa 24 giờ;
  24 giờ không sai thì đếm lại từ đầu (thời gian đang bị khoá không tính là "không sai").
- Cộng mọi địa chỉ IP, sai 20 lần trong 24 giờ: khoá tài khoản 01 giờ.
- Địa chỉ IP là địa chỉ thật do cổng HTTPS chuyển tới (uvicorn chỉ tin cổng HTTPS).
Bộ đếm ghi ra 01 tệp trong ổ dữ liệu (quyền 600) để lệnh đặt lại mật khẩu trên VPS xoá được ngay.
"""
import json
import os
import threading
import time
from pathlib import Path

from maychu.dulieu import ketnoi

SO_LAN_IP, CUA_SO_IP_GIAY, KHOA_DAU_PHUT, KHOA_TOIDA_PHUT = 5, 15 * 60, 15, 24 * 60
SO_LAN_TK, CUA_SO_TK_GIAY, KHOA_TK_GIAY = 20, 24 * 3600, 3600
NGAY_GIAY = 24 * 3600
TEN_TEP = ".chan_dangnhap.json"
_KHOA = threading.Lock()


def _tep(thumuc: Path | None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / TEN_TEP


def _doc(thumuc) -> dict:
    try:
        return json.loads(_tep(thumuc).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ip": {}, "tk": {"sai": [], "khoa_den": 0}}


def _ghi(d: dict, thumuc) -> None:
    p = _tep(thumuc)
    tam = p.with_suffix(".tam")
    fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tam, p)


def dang_khoa(ip: str, thumuc: Path | None = None, bay: float | None = None) -> dict | None:
    """Đang bị khoá thì trả {'loai': 'taikhoan' | 'ip', 'den': giây, 'phut': số phút của lần khoá}."""
    bay = time.time() if bay is None else bay
    with _KHOA:
        d = _doc(thumuc)
    if d["tk"].get("khoa_den", 0) > bay:
        return {"loai": "taikhoan", "den": d["tk"]["khoa_den"], "phut": KHOA_TK_GIAY // 60}
    r = d["ip"].get(ip)
    if r and r.get("khoa_den", 0) > bay:
        return {"loai": "ip", "den": r["khoa_den"], "phut": r.get("phut", KHOA_DAU_PHUT)}
    return None


def ghi_sai(ip: str, thumuc: Path | None = None, bay: float | None = None) -> dict:
    """Ghi 01 lần sai. Trả {'con_lai': n} hoặc thông tin khoá nếu lần sai này làm khoá."""
    bay = time.time() if bay is None else bay
    with _KHOA:
        d = _doc(thumuc)
        r = d["ip"].setdefault(ip, {"sai": [], "khoa_den": 0, "phut": 0, "sai_cuoi": 0})
        if bay - max(r.get("sai_cuoi", 0), r.get("khoa_den", 0)) > NGAY_GIAY:   # 24 giờ không sai (tính cả lúc đang khoá): đếm lại
            r.update(phut=0, khoa_den=0)
        r["sai_cuoi"] = bay
        r["sai"] = [t for t in r["sai"] if bay - t < CUA_SO_IP_GIAY] + [bay]
        kq = {"con_lai": SO_LAN_IP - len(r["sai"])}
        if len(r["sai"]) >= SO_LAN_IP:
            lai = r.get("khoa_den", 0) and bay - r["khoa_den"] < NGAY_GIAY   # bị khoá lại trong 24 giờ
            phut = min(r.get("phut", 0) * 2, KHOA_TOIDA_PHUT) if lai and r.get("phut") else KHOA_DAU_PHUT
            r.update(khoa_den=bay + phut * 60, phut=phut, sai=[])
            kq = {"loai": "ip", "den": r["khoa_den"], "phut": phut}
        tk = d["tk"]
        tk["sai"] = [t for t in tk.get("sai", []) if bay - t < CUA_SO_TK_GIAY] + [bay]
        if len(tk["sai"]) >= SO_LAN_TK:
            tk.update(khoa_den=bay + KHOA_TK_GIAY, sai=[])
            kq = {"loai": "taikhoan", "den": tk["khoa_den"], "phut": KHOA_TK_GIAY // 60}
        d["ip"] = {k: v for k, v in d["ip"].items() if bay - v.get("sai_cuoi", 0) < NGAY_GIAY or v.get("khoa_den", 0) > bay}
        _ghi(d, thumuc)
    return kq


def thanh_cong(ip: str, thumuc: Path | None = None) -> None:
    """Đăng nhập đúng: xoá chuỗi sai liền của địa chỉ đó (giữ số lần đã bị khoá trong 24 giờ)."""
    with _KHOA:
        d = _doc(thumuc)
        if ip in d["ip"] and d["ip"][ip]["sai"]:
            d["ip"][ip]["sai"] = []
            _ghi(d, thumuc)


def xoa_het(thumuc: Path | None = None) -> None:
    """Lệnh đặt lại mật khẩu trên VPS: mở mọi khoá ngay."""
    with _KHOA:
        _tep(thumuc).unlink(missing_ok=True)
