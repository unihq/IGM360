"""Mã dài hạn gói Claude (QĐ198, QĐ200, PTD-09; bản 0.7.8).

`claude setup-token` cấp 01 mã dùng 365 ngày cho đúng gói đã đăng nhập, dành cho việc chạy không người ngồi. CLI nhận
mã qua biến `CLAUDE_CODE_OAUTH_TOKEN`. Theo mã CLI 2.1.330 (đọc chữ trong tệp chạy, chưa chạy thật), CLI chọn nguồn đăng
nhập theo thứ tự: `ANTHROPIC_API_KEY` → apiKeyHelper → khoá /login → `ANTHROPIC_AUTH_TOKEN` → `CLAUDE_CODE_OAUTH_TOKEN` →
tệp mã → đăng nhập claude.ai đã lưu. Vì vậy lượt gọi gói luôn bỏ 02 biến khoá API ra khỏi môi trường, rồi mới đặt mã.

Bảo mật (PTD-09 Đ1–Đ8):
- Đ1: mã chỉ nằm ở Két khoá F03 (mã hoá bằng khoá chủ), mỗi tài khoản 01 dòng `dichvu` = `goi_claude_NN`,
  `han` = lúc lưu + 365 ngày (không đọc được ngày hết hạn từ mã nên tính từ lúc lưu). Không ghi ra tệp nào khác.
- Đ2: mã chỉ đi qua biến môi trường của từng lần chạy CLI, đúng tài khoản; tài khoản khác bỏ biến này.
- Đ3: không ra F04, G04, N01, D03, câu lỗi, câu trả lời API (`kekhoa.che`). Đầu ra của `setup-token` chỉ giữ trong
  bộ nhớ phiên lấy mã tới lúc lưu xong rồi xoá.
- Đ5: gỡ tài khoản thì xoá dòng F03 (`dangnhap_goi.go`). Đ6: mã hết hạn thì không gọi tài khoản đó.
- Đ7: lấy mã mới thì thay dòng cũ (`kho.doi`). Đ8: chỉ nhận chuỗi bắt đầu `sk-ant-oat01-`; lưu xong, gọi thử đạt rồi
  mới đăng xuất kiểu đăng nhập cũ của thư mục đó.

Cách chạy `setup-token` học từ mã có sẵn ghi ở Sổ nguồn gốc (viết mới, không chép mã):
lệnh vẽ màn hình đầy đủ nên phải chạy trong khung giả lập dòng lệnh (pty, chỉ có trên Linux, macOS), khung thật rộng để
mã không bị ngắt dòng; lấy đường link trong siêu liên kết của dòng lệnh trước, không có thì lấy chữ hiện.
"""
import os
import re
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import kho
from maychu.hethong.kekhoa.che import che  # noqa: F401 - nơi khác gọi `madaihan.che`

TIEN_TO = "sk-ant-oat01-"
MA_RE = re.compile(r"sk-ant-oat01-[A-Za-z0-9_\-]{20,}")
BIEN = "CLAUDE_CODE_OAUTH_TOKEN"
BIEN_BO = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", BIEN)   # lượt gọi gói không bao giờ mang khoá API
SO_NGAY = 365                # mã `setup-token` sống 01 năm
SO_NGAY_NHAC = 7             # QĐ200: chuông nhắc mỗi ngày 01 lần từ 07 ngày trước (khoá Drive giữ 05 ngày, QĐ165)
SO_NGAY_VANG = 14            # QĐ198: thẻ màn 13 đổi màu Cảnh báo trong 14 ngày cuối (tính lúc hiện, không lưu)
COT, DONG = 500, 60          # khung giả lập rộng: mã dài không bị ngắt dòng
CHO_LINK_GIAY, CHO_MA_GIAY, HAN_PHIEN_GIAY = 20, 45, 900
BAO_SAI = ("invalid code", "invalid authorization", "oauth error", "failed to", "error:", "expired")


def dichvu(tk: int) -> str:
    return f"goi_claude_{tk:02d}"


def hop_le(ma: str) -> bool:
    return isinstance(ma, str) and bool(MA_RE.fullmatch(ma.strip()))


# ---------------- Két khoá ----------------
def _dong(tk: int, thumuc=None):
    try:
        c = ketnoi.mo("Baomat", thumuc)
    except (sqlite3.Error, OSError):   # máy chưa có tệp dữ liệu (lúc cài, bài kiểm không dữ liệu): coi như chưa có mã
        return None
    try:
        return c.execute("SELECT id, kytu_cuoi, han FROM kekhoa WHERE dichvu = ? AND trangthai = 'dung'"
                         " ORDER BY rowid DESC LIMIT 1", (dichvu(tk),)).fetchone()
    finally:
        c.close()


def thong_tin(tk: int, thumuc=None, bay: datetime | None = None) -> dict | None:
    """Thẻ màn 13: {kytu_cuoi, han, luu_luc, con_ngay, het, vang}; không bao giờ có mã."""
    d = _dong(tk, thumuc)
    if not d:
        return None
    _, cuoi, han = d
    bay = bay or datetime.now(MUIGIO_VN)
    try:
        h = datetime.fromisoformat(han)
    except (TypeError, ValueError):
        return {"kytu_cuoi": cuoi, "han": None, "luu_luc": None, "con_ngay": None, "het": False, "vang": False}
    con = (h.date() - bay.date()).days
    return {"kytu_cuoi": cuoi, "han": han, "luu_luc": (h - timedelta(days=SO_NGAY)).isoformat(timespec="seconds"),
            "con_ngay": con, "het": h <= bay, "vang": con <= SO_NGAY_VANG}


def lay(tk: int, thumuc=None) -> str | None:
    """Mã còn hạn của tài khoản (chỉ lớp gọi CLI dùng); hết hạn hoặc chưa có thì None."""
    d = _dong(tk, thumuc)
    if not d:
        return None
    try:
        if datetime.fromisoformat(d[2]) <= datetime.now(MUIGIO_VN):
            return None
    except (TypeError, ValueError):
        return None
    try:
        return kho.doc(d[0], thumuc)
    except (KeyError, ValueError):
        return None


def luu(tk: int, ma: str, thumuc=None, nguoi: str = "hethong") -> dict:
    """Đ1, Đ7, Đ8: kiểm tiền tố rồi cất (thay dòng cũ nếu có). Trả thông tin thẻ."""
    ma = (ma or "").strip()
    if not hop_le(ma):
        raise ValueError("Mã không đúng dạng mã dài hạn của Claude")
    han = (datetime.now(MUIGIO_VN) + timedelta(days=SO_NGAY)).isoformat(timespec="seconds")
    cu = kho.tim(dichvu(tk), thumuc)
    if cu:
        kho.doi(cu, ma, thumuc, han=han)
    else:
        kho.cat(dichvu(tk), ma, thumuc, han=han, nguoi_nhap=nguoi)
    return thong_tin(tk, thumuc)


def xoa(tk: int, thumuc=None) -> bool:
    """Đ5: xoá hẳn dòng F03 (mã vẫn sống ở hãng tới khi thu hồi trên trang của hãng)."""
    c = ketnoi.mo("Baomat", thumuc)
    try:
        return c.execute("DELETE FROM kekhoa WHERE dichvu = ?", (dichvu(tk),)).rowcount > 0
    finally:
        c.close()


def moi_truong(env: dict, tk: int, dung_ma: bool = True, thumuc=None) -> dict:
    """Đ2: bỏ khoá API và mã của tài khoản khác; `dung_ma` thì đặt mã còn hạn của đúng tài khoản này."""
    for k in BIEN_BO:
        env.pop(k, None)
    if dung_ma:
        ma = lay(tk, thumuc)
        if ma:
            env[BIEN] = ma
    return env


# ---------------- Lấy mã bằng `claude setup-token` ----------------
_PHIEN: dict[int, dict] = {}
_KHOA = threading.Lock()
_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CSI = re.compile(r"\x1b\[[0-9;?<>=]*[ -/]*[@-~]")
_ESC = re.compile(r"\x1b[@-_]")
_LINK_RE = re.compile(r"https://[^\s\x07\x1b]*oauth/authorize[^\s\x07\x1b]*")
_KYTU_MA = re.compile(r"[A-Za-z0-9_\-]+")


def ho_tro() -> bool:
    """Máy có khung giả lập dòng lệnh (Linux, macOS). Không có thì chỉ dùng được nút Dán mã."""
    if os.name != "posix":
        return False
    try:
        import pty  # noqa: F401
    except ImportError:
        return False
    return True


def _chu_tron(tho: str) -> str:
    return _ESC.sub("", _CSI.sub("", _OSC.sub("", tho or "")))


def tim_link(tho: str) -> str:
    """Đích của siêu liên kết dòng lệnh (không bị màn hình cắt) trước, rồi tới chữ hiện."""
    for dich in re.findall(r"\x1b\]8;[^;]*;([^\x07\x1b]*)(?:\x07|\x1b\\)", tho or ""):
        if m := _LINK_RE.search(dich):
            return m.group(0)
    m = _LINK_RE.search(_chu_tron(tho))
    return m.group(0) if m else ""


def tim_ma(tho: str, da_ket_thuc: bool = False) -> str:
    """Mã đã in trọn: chỉ nhận dòng đã có xuống dòng phía sau (hoặc lệnh đã kết thúc); mã chạm cuối dòng thì nối các
    dòng sau chỉ gồm ký tự của mã, tới khi gặp dòng khác."""
    chu = re.sub(r"\r*\n", "\n", _chu_tron(tho)).replace("\r", "\n")
    dong = chu.split("\n")
    if not da_ket_thuc:
        dong = dong[:-1]
    for i, d in enumerate(dong):
        m = MA_RE.search(d)
        if not m:
            continue
        ma = m.group(0)
        if m.end() == len(d.rstrip()):
            xong = da_ket_thuc
            for sau in dong[i + 1:]:
                s = sau.strip()
                if not s or not _KYTU_MA.fullmatch(s):
                    xong = True
                    break
                ma += s
            if not xong:
                return ""
        return ma
    return ""


def _duoi(tho: str) -> str:
    """Vài dòng cuối lệnh in ra để nêu lý do lỗi; bỏ đường link, đã che mã."""
    ds = []
    for d in _chu_tron(tho).replace("\r", "\n").split("\n"):
        d = " ".join(d.split()).lstrip("✘✗✔✓×·•*>- ")
        if len(d) >= 4 and any(c.isalpha() for c in d) and not _LINK_RE.search(d):
            ds.append(che(d))
    return " ".join(ds[-2:])[:300]


def _dung(p: dict | None) -> None:
    if not p:
        return
    pr, fd = p.get("proc"), p.get("fd")
    p["tho"], p["ma"] = "", ""   # Đ3: quên đầu ra, kể cả mã
    if pr is not None and pr.poll() is None:
        try:
            os.killpg(pr.pid, 15)
        except (ProcessLookupError, PermissionError, OSError, AttributeError):
            pr.terminate()
        try:
            pr.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pr.kill()
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def huy_lay(tk: int) -> None:
    with _KHOA:
        p = _PHIEN.pop(tk, None)
    _dung(p)


def _doc(tk: int, p: dict) -> None:
    while True:
        try:
            khuc = os.read(p["fd"], 4096)
        except OSError:
            break
        if not khuc:
            break
        with _KHOA:
            if _PHIEN.get(tk) is not p:
                return
            p["tho"] = (p["tho"] + khuc.decode("utf-8", "replace"))[-200_000:]
            if not p["url"]:
                p["url"] = tim_link(p["tho"])
            if not p["ma"]:
                p["ma"] = tim_ma(p["tho"])
            if p["da_gui"] and not p["ma"] and any(x in _chu_tron(khuc.decode("utf-8", "replace")).lower() for x in BAO_SAI):
                p["loi"] = _duoi(p["tho"]) or "Claude không nhận mã này"


def bat_dau_lay(tk: int, env: dict) -> dict:
    """Chạy `claude setup-token`, chờ đường link đăng nhập. {url} hoặc {loi, khong_ho_tro?}. `env`: môi trường của đúng
    tài khoản (thư mục cấu hình), đã bỏ khoá API và mã cũ: lệnh cấp mã cho gói nó đăng nhập, không dùng mã sẵn có."""
    if not ho_tro():
        return {"loi": "Máy chủ này không chạy được bước lấy mã tự động: dùng nút Dán mã", "khong_ho_tro": True}
    huy_lay(tk)
    import fcntl
    import pty
    import struct
    import termios
    chinh, phu = pty.openpty()
    try:
        fcntl.ioctl(phu, termios.TIOCSWINSZ, struct.pack("HHHH", DONG, COT, 0, 0))
    except OSError:
        pass
    e = moi_truong(dict(env), tk, dung_ma=False)
    e.update(TERM="xterm-256color", COLUMNS=str(COT), LINES=str(DONG))
    from maychu.hethong.mohinh import dangnhap_goi
    try:
        pr = subprocess.Popen([dangnhap_goi._cli("claude"), "setup-token"], stdin=phu, stdout=phu, stderr=phu, env=e,
                              start_new_session=True, close_fds=True)
    except (FileNotFoundError, OSError):
        os.close(chinh)
        os.close(phu)
        return {"loi": "Máy chủ chưa có công cụ đăng nhập Gói Claude"}
    os.close(phu)
    p = {"proc": pr, "fd": chinh, "tho": "", "url": "", "ma": "", "loi": "", "da_gui": False, "bat_luc": time.time()}
    with _KHOA:
        _PHIEN[tk] = p
    threading.Thread(target=_doc, args=(tk, p), daemon=True).start()
    het = time.time() + CHO_LINK_GIAY
    while time.time() < het:
        with _KHOA:
            if p["url"] or p["ma"]:
                return {"url": p["url"], "xong": bool(p["ma"])}
        if pr.poll() is not None:
            time.sleep(0.2)
            break
        time.sleep(0.2)
    with _KHOA:
        if p["url"] or p["ma"]:
            return {"url": p["url"], "xong": bool(p["ma"])}
        duoi = _duoi(p["tho"])
    huy_lay(tk)
    return {"loi": "Claude không đưa ra đường link đăng nhập" + (f" ({duoi})" if duoi else "")}


def gui_ma(tk: int, ma_web: str) -> dict:
    """Gõ mã trang đăng nhập hiện, chờ mã dài hạn. {ma} (chỉ cho lớp lưu, không trả ra API) hoặc {loi}."""
    ma_web = "".join(str(ma_web or "").split())
    with _KHOA:
        p = _PHIEN.get(tk)
    if not p:
        return {"loi": "Chưa bắt đầu lấy mã: bấm Lấy mã mới trước"}
    if time.time() - p["bat_luc"] > HAN_PHIEN_GIAY:
        huy_lay(tk)
        return {"loi": "Lượt lấy mã đã quá 15 phút: bấm Lấy mã mới"}
    if not ma_web and not p["ma"]:
        return {"loi": "Chưa có mã"}
    with _KHOA:
        if not p["ma"]:
            p["loi"], p["da_gui"] = "", True
    if not p["ma"]:
        try:
            os.write(p["fd"], ma_web.encode("utf-8"))
            time.sleep(0.15)
            os.write(p["fd"], b"\r")
        except OSError:
            huy_lay(tk)
            return {"loi": "Lượt lấy mã đã kết thúc: bấm Lấy mã mới"}
    het = time.time() + CHO_MA_GIAY
    while time.time() < het:
        with _KHOA:
            if p["ma"]:
                return {"ma": p["ma"]}
            if p["loi"]:
                loi = p["loi"]
                break
        if p["proc"].poll() is not None:
            time.sleep(0.3)
            with _KHOA:
                p["ma"] = p["ma"] or tim_ma(p["tho"], da_ket_thuc=True)
                if p["ma"]:
                    return {"ma": p["ma"]}
                loi = _duoi(p["tho"]) or "Lấy mã chưa được"
            huy_lay(tk)
            return {"loi": f"Lấy mã chưa được ({loi}): bấm Lấy mã mới"}
        time.sleep(0.2)
    else:
        return {"loi": "Claude chưa trả mã sau 45 giây: bấm Lấy mã mới"}
    return {"loi": f"Claude không nhận mã này ({loi}). Bấm \"Mở trang\" lấy mã mới rồi dán lại."}


def dang_lay(tk: int) -> bool:
    with _KHOA:
        return tk in _PHIEN


def don_phien() -> None:
    """Lượt lấy mã bỏ dở quá 15 phút."""
    with _KHOA:
        cu = [tk for tk, p in _PHIEN.items() if time.time() - p["bat_luc"] > HAN_PHIEN_GIAY]
    for tk in cu:
        huy_lay(tk)


def _trang_thai_cli(tk: int, dung_ma: bool) -> dict:
    """`claude auth status --json` của tài khoản (có hay không có mã dài hạn trong môi trường). Không ghi email."""
    from maychu.hethong.mohinh import dangnhap_goi as dg
    try:
        r = subprocess.run([dg._cli("claude"), "auth", "status", "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15, env=dg._env("claude", tk, tao=False, ma_daihan=dung_ma))
        import json
        d = json.loads((r.stdout or "").strip() or "{}")
        return {"loggedIn": bool(d.get("loggedIn")), "authMethod": che(str(d.get("authMethod") or ""))[:40]}
    except (OSError, ValueError, subprocess.TimeoutExpired, AttributeError):
        return {"loggedIn": None, "authMethod": ""}


def ket_noi(tk: int, ma: str, nguoi: str = "hethong", thumuc=None) -> dict:
    """Lưu mã (Đ1, Đ7, Đ8), gọi thử 01 câu ngắn, ghi 03 kết quả kiểm thật vào F04 (QĐ198 mục 04; không ghi mã, email),
    gọi thử đạt thì đăng xuất kiểu đăng nhập cũ của thư mục này (Đ8). Không bao giờ trả mã."""
    from maychu.hethong import nhatky
    from maychu.hethong.mohinh import congai, dangnhap_goi as dg
    tt = luu(tk, ma, thumuc, nguoi)
    dg._NHO_TRANGTHAI.pop(("claude", tk), None)
    cu = _trang_thai_cli(tk, dung_ma=False)            # đăng nhập kiểu cũ còn không
    moi = _trang_thai_cli(tk, dung_ma=True)            # (c) `auth status` khi có mã dài hạn
    hs = dg.ho_so("claude", tk)                        # (a) trước khi đăng xuất kiểu cũ
    kiem = {"ten_truoc": bool(hs.get("ten_hien")), "goi_truoc": bool(hs.get("goi_ten"))}
    loi = ""
    try:
        kq = congai._goi_claude(tk, "Trả lời đúng 01 chữ: được", None)
        kiem["rate_limit_event"] = bool(kq.get("hanmuc"))   # (b)
        dat = True
    except Exception as e:  # noqa: BLE001 - mọi lỗi gọi thử đều báo lại, mã đã lưu vẫn giữ
        dat, loi = False, che(str(e))[:200]
    if dat:
        if cu["loggedIn"]:
            kiem["dang_xuat_cu"] = dg._dang_xuat("claude", tk)
        hs2 = dg.ho_so("claude", tk)
        kiem.update(ten_sau=bool(hs2.get("ten_hien")), goi_sau=bool(hs2.get("goi_ten")))
        dg.ghi_nguon("claude", tk, thumuc, nguoi=nguoi)
    dg._NHO_TRANGTHAI.pop(("claude", tk), None)
    co = lambda v: "chưa rõ" if v is None else ("có" if v else "không")   # noqa: E731
    tom = (f"Gói Claude tài khoản {tk:02d} · mã dài hạn · gọi thử {'đạt' if dat else 'chưa được'}"
           f" · auth status loggedIn {co(moi['loggedIn'])}, authMethod {moi['authMethod'] or 'trống'}"
           f" · rate_limit_event {co(kiem.get('rate_limit_event'))}"
           f" · tên {co(kiem['ten_truoc'])}/{co(kiem.get('ten_sau'))}, gói {co(kiem['goi_truoc'])}/{co(kiem.get('goi_sau'))}"
           f" (trước/sau đăng xuất kiểu cũ) · kiểu cũ {'đã đăng xuất' if kiem.get('dang_xuat_cu') else 'không có' if not cu['loggedIn'] else 'giữ'}")
    nhatky.ghi("mohinh", "kiem_madaihan", tom, ketqua="dat" if dat else "loi", nguoi_id=None if nguoi == "hethong" else nguoi,
               lydo=loi or None, thumuc=thumuc)
    return {"xong": True, "goi_thu": dat, **({"loi_goi_thu": loi} if loi else {}), **(tt or {})}
