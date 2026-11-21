"""Ngăn Cập nhật (màn 09): bản đang chạy, bản mới nhất trên kho ảnh GHCR (công khai), nội dung thay đổi,
lệnh "Cập nhật ngay" gửi watchtower (chỉ nghe trong mạng nội bộ Docker), lịch sử ghi ở F04."""
import os
import re
import time
from datetime import datetime
from pathlib import Path

import httpx

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN

ANH = os.environ.get("IGM360_IMAGE", "unihq/igm360")
KHO_MA = os.environ.get("IGM360_KHO_MA", "unihq/IGM360")
NHIP_KIEM_GIAY = 6 * 3600
_NHO = {"luc": 0.0, "ban_moi": None, "thaydoi": [], "loi": None}
_SO = re.compile(r"^\d+\.\d+\.\d+$")


def _khoa_so(b: str):
    return tuple(int(x) for x in b.split("."))


def ban_dang_chay() -> str:
    try:
        return (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def _hoi_ghcr() -> str | None:
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        ve = c.get("https://ghcr.io/token", params={"scope": f"repository:{ANH}:pull"}).json()["token"]
        nhan = c.get(f"https://ghcr.io/v2/{ANH}/tags/list", headers={"Authorization": f"Bearer {ve}"}).json().get("tags") or []
    so = sorted((t for t in nhan if _SO.match(t)), key=_khoa_so)
    return so[-1] if so else None


def _doc_thaydoi(tu_ban: str) -> list[dict]:
    """Đọc THAYDOI.md trên kho mã: mỗi bản 01 mục '## x.y.z', các dòng '- ...' là nội dung."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        r = c.get(f"https://raw.githubusercontent.com/{KHO_MA}/main/THAYDOI.md")
    if r.status_code != 200:
        return []
    return [m for m in phan_tich_thaydoi(r.text) if _khoa_so(m["ban"]) > _khoa_so(tu_ban)]


def phan_tich_thaydoi(chu: str) -> list[dict]:
    muc, ds = None, []
    for dong in chu.splitlines():
        m = re.match(r"^##\s+(\d+\.\d+\.\d+)", dong)
        if m:
            muc = {"ban": m.group(1), "dong": []}
            ds.append(muc)
        elif muc and dong.strip().startswith("- "):
            muc["dong"].append(dong.strip()[2:])
    return ds


def kiem_tra(bat_buoc: bool = False) -> dict:
    bay = time.time()
    if bat_buoc or bay - _NHO["luc"] > NHIP_KIEM_GIAY:
        try:
            _NHO["ban_moi"] = _hoi_ghcr()
            _NHO["thaydoi"] = _doc_thaydoi(ban_dang_chay()) if _NHO["ban_moi"] else []
            _NHO["loi"] = None
        except (httpx.HTTPError, KeyError, ValueError) as loi:
            _NHO["loi"] = "Chưa kiểm được bản mới vì không kết nối được kho ảnh, anh bấm Kiểm tra lại sau"
        _NHO["luc"] = bay
    dang = ban_dang_chay()
    moi = _NHO["ban_moi"]
    return {"ban_dang": dang, "ban_moi": moi, "co_ban_moi": bool(moi and _khoa_so(moi) > _khoa_so(dang)),
            "luc_kiem": datetime.fromtimestamp(_NHO["luc"], MUIGIO_VN).isoformat(timespec="seconds") if _NHO["luc"] else None,
            "thaydoi": _NHO["thaydoi"], "loi": _NHO["loi"]}


def _ghi_f04(lenhcon: str, tomtat: str, ketqua: str, lydo: str | None = None, nguoi_id=None, thumuc=None) -> None:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua, lydo_chan)"
                   " VALUES (?, ?, ?, ?, 'capnhat', ?, ?, ?, ?)",
                   (maso.tao(), datetime.now(MUIGIO_VN).isoformat(timespec="seconds"), "anh" if nguoi_id else None,
                    nguoi_id, lenhcon, tomtat, ketqua, lydo))
    finally:
        cn.close()


def ghi_khoi_dong(thumuc=None) -> None:
    """Mỗi lần chạy bản khác bản lần trước thì ghi 01 dòng lịch sử cài."""
    ban = ban_dang_chay()
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cu = cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'khoidong'"
                        " ORDER BY luc DESC LIMIT 1").fetchone()
    finally:
        cn.close()
    if not cu or cu[0] != ban:
        _ghi_f04("khoidong", ban, "dat", thumuc=thumuc)


def lich_su(thumuc=None) -> list[dict]:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        dong = cn.execute("SELECT luc, thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat' AND lenhcon = 'khoidong'"
                          " ORDER BY luc DESC LIMIT 20").fetchall()
    finally:
        cn.close()
    return [{"ban": d[1], "luc": d[0]} for d in dong]


def so_viec_ai_dangchay(thumuc=None) -> int:
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        return cn.execute("SELECT count(*) FROM viecnen WHERE trangthai = 'dangchay' AND goi_ai = 1").fetchone()[0]
    finally:
        cn.close()


def cap_nhat_ngay(nguoi_id: str, thumuc=None) -> dict:
    ma = os.environ.get("WATCHTOWER_TOKEN", "")
    if not ma:
        return {"loi": "Máy chủ chưa có mã cập nhật"}
    try:
        httpx.post("http://watchtower:8080/v1/update", headers={"Authorization": f"Bearer {ma}"}, timeout=5)
    except httpx.TimeoutException:
        pass  # watchtower đang kéo bản mới và khởi động lại phần mềm: bình thường
    except httpx.HTTPError as loi:
        _ghi_f04("capnhat_ngay", ban_dang_chay(), "loi", type(loi).__name__, nguoi_id, thumuc)
        return {"loi": "Chưa gửi được lệnh cập nhật"}
    _ghi_f04("capnhat_ngay", ban_dang_chay(), "dat", None, nguoi_id, thumuc)
    return {"ok": True}
