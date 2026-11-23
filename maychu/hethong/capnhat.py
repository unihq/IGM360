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
# QĐ174, QĐ175 (Y29): dò bản mới cố định 05 phút, không làm thông số (nguồn học cách làm: tailieu/Songuongoc.md).
# Nhịp chỉ viết ở 01 chỗ này; nơi khác đọc qua `nhip_kiem_giay()`.
NHIP_KIEM_GIAY = 5 * 60
_NHO = {"luc": 0.0, "luc_dat": 0.0, "ban_moi": None, "thaydoi": [], "tomtat": {}, "loi": None, "nhan_thaydoi": None}


def nhip_kiem_giay() -> int:
    return NHIP_KIEM_GIAY
_SO = re.compile(r"^\d+\.\d+\.\d+$")


def _khoa_so(b: str):
    return tuple(int(x) for x in b.split("."))


def ban_dang_chay() -> str:
    try:
        return (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


_KIEU_GOI = ", ".join(("application/vnd.oci.image.index.v1+json", "application/vnd.oci.image.manifest.v1+json",
                        "application/vnd.docker.distribution.manifest.list.v2+json",
                        "application/vnd.docker.distribution.manifest.v2+json"))


def _hoi_ghcr(dang: str | None = None) -> tuple[str | None, str | None]:
    """(bản mới nhất DÙNG ĐƯỢC, nhãn số lớn nhất trên kho). 02 lượt hỏi: khoá đọc ẩn danh + danh sách nhãn. Nhãn lớn
    hơn bản đang chạy thì hỏi thêm đúng nhãn đó (QĐ174 điểm 04): gói đóng xong (trả 200) mới tính là bản mới; đang đóng
    thì lùi về nhãn trước, lần sau hỏi lại."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        ve = c.get("https://ghcr.io/token", params={"scope": f"repository:{ANH}:pull"}).json()["token"]
        nhan = c.get(f"https://ghcr.io/v2/{ANH}/tags/list", headers={"Authorization": f"Bearer {ve}"}).json().get("tags") or []
        so = sorted((t for t in nhan if _SO.match(t)), key=_khoa_so)
        if not so:
            return None, None
        moi_hon = [t for t in so if dang is None or _khoa_so(t) > _khoa_so(dang)]
        for t in reversed(moi_hon[-2:]):   # tối đa 02 nhãn mới nhất
            r = c.head(f"https://ghcr.io/v2/{ANH}/manifests/{t}", headers={"Authorization": f"Bearer {ve}", "Accept": _KIEU_GOI})
            if r.status_code == 200:
                return t, so[-1]
        cu = [t for t in so if t not in moi_hon]
        return (cu[-1] if cu else None), so[-1]


def _tai_thaydoi_kq() -> tuple[list[dict], int]:
    """Đọc THAYDOI.md trên kho mã (tệp không nằm trong ảnh máy chủ). Trả (các mục, mã trả về)."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        r = c.get(f"https://raw.githubusercontent.com/{KHO_MA}/main/THAYDOI.md")
    return (phan_tich_thaydoi(r.text) if r.status_code == 200 else []), r.status_code


def _tai_thaydoi() -> list[dict]:
    return _tai_thaydoi_kq()[0]


def _doc_thaydoi(tu_ban: str, het: list[dict] | None = None) -> list[dict]:
    return [m for m in (_tai_thaydoi() if het is None else het) if _khoa_so(m["ban"]) > _khoa_so(tu_ban)]


def phan_tich_thaydoi(chu: str) -> list[dict]:
    """Mỗi bản 01 mục '## x.y.z'; dòng 'Tóm tắt: ...' là chữ ngắn cho lịch sử cập nhật (N07);
    các dòng '- ...' là nội dung có gì mới."""
    muc, ds = None, []
    for dong in chu.splitlines():
        m = re.match(r"^##\s+(\d+\.\d+\.\d+)", dong)
        if m:
            muc = {"ban": m.group(1), "tomtat": None, "dong": []}
            ds.append(muc)
        elif muc and dong.strip().startswith("Tóm tắt:"):
            muc["tomtat"] = dong.strip()[len("Tóm tắt:"):].strip() or None
        elif muc and dong.strip().startswith("- "):
            muc["dong"].append(dong.strip()[2:])
    return ds


def kiem_tra(bat_buoc: bool = False) -> dict:
    """Kết quả nhớ `nhip_kiem_giay()` (QĐ174: 05 phút); `bat_buoc` (nút Kiểm tra lại) thì hỏi ngay.
    Mỗi lần hỏi: 02 lượt ghcr.io; THAYDOI.md (raw.githubusercontent.com) chỉ tải khi kho có nhãn mới so với lần tải
    trước, hoặc lần trước tải chưa được. Kho từ chối, lỗi mạng: giữ kết quả cũ, không báo lỗi, lượt sau hỏi lại;
    chưa từng kiểm được lần nào thì mới báo."""
    bay = time.time()
    dang = ban_dang_chay()
    if bat_buoc or bay - _NHO["luc"] > nhip_kiem_giay():
        _NHO["luc"] = bay
        try:
            moi, nhan_lon = _hoi_ghcr(dang)
            _NHO["ban_moi"], _NHO["luc_dat"] = moi, bay
            _NHO["loi"] = None
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            nhan_lon = None
            if not _NHO["luc_dat"]:
                _NHO["loi"] = "Chưa kiểm được bản mới vì không kết nối được kho ảnh, anh bấm Kiểm tra lại sau"
        if nhan_lon and nhan_lon != _NHO["nhan_thaydoi"]:
            try:
                het, ma_tra = _tai_thaydoi_kq()
            except httpx.HTTPError:
                het, ma_tra = [], 0
            if ma_tra == 200:
                _NHO["thaydoi"] = _doc_thaydoi(dang, het)
                _NHO["tomtat"] = {m["ban"]: m["tomtat"] for m in het if m["tomtat"]}
                _NHO["nhan_thaydoi"] = nhan_lon
            elif not _NHO["tomtat"]:   # Y17 (e): chưa có nội dung cũ thì nói rõ; có rồi thì giữ, lượt sau tải lại
                _NHO["loi"] = f"Chưa tải được nội dung thay đổi (mã trả về {ma_tra}), số bản mới vẫn đúng"
    moi = _NHO["ban_moi"]
    return {"ban_dang": dang, "ban_moi": moi, "co_ban_moi": bool(moi and _khoa_so(moi) > _khoa_so(dang)),
            "luc_kiem": datetime.fromtimestamp(_NHO["luc_dat"], MUIGIO_VN).isoformat(timespec="seconds") if _NHO["luc_dat"] else None,
            "nhip_phut": nhip_kiem_giay() // 60,
            "thaydoi": _NHO["thaydoi"] if moi else [], "tomtat": _NHO["tomtat"], "loi": _NHO["loi"]}


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


_CHO = {"tu": 0.0, "nguoi": None}
CHO_TOIDA_GIAY = 30 * 60


def yeu_cau(nguoi_id: str, che_do: str, thumuc=None) -> dict:
    """che_do 'ngay': gửi lệnh luôn. 'cho': không có việc AI đang chạy thì gửi luôn; có thì chờ việc xong,
    tối đa 30 phút (lịch chạy nền gọi xu_ly_cho mỗi phút). Việc mới không nhận khi đang chờ: dang_cho()."""
    if not kiem_tra()["co_ban_moi"]:   # QĐ174 điểm 04: chỉ cập nhật khi gói bản mới đã đóng xong trên kho
        return {"loi": "Chưa có bản mới đóng gói xong, anh chờ vài phút rồi bấm Kiểm tra lại"}
    if che_do == "cho" and so_viec_ai_dangchay(thumuc):
        _CHO.update(tu=time.time(), nguoi=nguoi_id)
        return {"ok": True, "cho": True}
    return cap_nhat_ngay(nguoi_id, thumuc)


def dang_cho() -> bool:
    return bool(_CHO["tu"])


def xu_ly_cho(thumuc=None) -> None:
    if _CHO["tu"] and (not so_viec_ai_dangchay(thumuc) or time.time() - _CHO["tu"] > CHO_TOIDA_GIAY):
        nguoi = _CHO["nguoi"]
        _CHO.update(tu=0.0, nguoi=None)
        cap_nhat_ngay(nguoi, thumuc)


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
