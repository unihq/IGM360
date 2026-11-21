"""Đăng nhập gói Claude, gói ChatGPT ngay trên giao diện màn 13 (QĐ89; học cách làm của mã gốc ghi ở Sổ nguồn gốc,
mã viết mới).

- Gói Claude: chạy `claude auth login --claudeai` qua đường ống, lấy đường link CLI in ra cho anh mở;
  anh đăng nhập trên web, trang hiện mã, anh dán mã ở màn 13, máy ghi mã vào CLI (bước bắt đầu, dán mã, kiểm lại).
- Gói ChatGPT: chạy `codex login --device-auth`, lấy đường link và mã thiết bị cho anh xác nhận trên web;
  máy tự hỏi lại tới khi CLI báo xong (không phải dán mã).
- Mỗi gói tối đa 02 tài khoản. Tài khoản 01 dùng thư mục mặc định trong ổ riêng (`/home/igm/.claude`,
  `/home/igm/.codex`); tài khoản 02 dùng thư mục con `taikhoan_02` trong cùng ổ (CLAUDE_CONFIG_DIR, CODEX_HOME),
  nên không mất khi cập nhật.
- Đăng nhập xong thì ghi nguồn AI (G06) mã `goi_claude_01`, `goi_chatgpt_02`...; không ghi mã, đường link vào nhật ký.
"""
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN

GOI = {
    "claude": {"ten": "Gói Claude", "cli_bien": "IGM360_CLAUDE_CLI", "cli": "claude", "bien_thumuc": "CLAUDE_CONFIG_DIR",
               "thumuc": "/home/igm/.claude", "lenh": ["auth", "login", "--claudeai"]},
    "chatgpt": {"ten": "Gói ChatGPT", "cli_bien": "IGM360_CODEX_CLI", "cli": "codex", "bien_thumuc": "CODEX_HOME",
                "thumuc": "/home/igm/.codex", "lenh": ["login", "--device-auth"]},
}
SO_TAIKHOAN_TOIDA = 2
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
MA_THIETBI_RE = re.compile(r"\b[A-Z0-9]{4}-[A-Z0-9]{4,5}\b")
MAU_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")   # mã màu của cửa sổ lệnh (Codex tô màu đường link, mã)
MA_SAI = ("invalid code", "wasn't accepted", "login failed", "oauth error", "expired")
HAN_PHIEN_GIAY = 900
_PHIEN: dict[tuple, dict] = {}
_KHOA = threading.Lock()
_NHO_TRANGTHAI: dict[tuple, tuple] = {}
NHO_GIAY = 30


def _cli(goi: str) -> str:
    g = GOI[goi]
    return os.environ.get(g["cli_bien"], g["cli"])


def thu_muc(goi: str, taikhoan: int) -> Path | None:
    """None = tài khoản 01 dùng thư mục mặc định của CLI."""
    if taikhoan == 1:
        return None
    goc = Path(os.environ.get(f"IGM360_THUMUC_{goi.upper()}", GOI[goi]["thumuc"]))
    return goc / f"taikhoan_{taikhoan:02d}"


def _env(goi: str, taikhoan: int) -> dict:
    tm = thu_muc(goi, taikhoan)
    env = dict(os.environ)
    if tm is not None:
        tm.mkdir(parents=True, exist_ok=True)
        os.chmod(tm, 0o700)
        env[GOI[goi]["bien_thumuc"]] = str(tm)
    return env


def _kiem(goi: str, taikhoan: int) -> None:
    if goi not in GOI:
        raise ValueError("Gói không có")
    if not 1 <= taikhoan <= SO_TAIKHOAN_TOIDA:
        raise ValueError(f"Mỗi gói tối đa {SO_TAIKHOAN_TOIDA:02d} tài khoản")


def _dung(p: dict) -> None:
    pr = p.get("proc")
    if pr and pr.poll() is None:
        try:
            os.killpg(pr.pid, 15)
        except (ProcessLookupError, PermissionError, OSError):
            pr.terminate()
    if pr:
        try:
            pr.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pr.kill()
        for ong in (pr.stdin, pr.stdout):
            try:
                if ong:
                    ong.close()
            except OSError:
                pass


def bat_dau(goi: str, taikhoan: int = 1) -> dict:
    """Mở 01 lượt đăng nhập; trả {url, ma_thietbi (ChatGPT)} hoặc {loi}."""
    _kiem(goi, taikhoan)
    k = (goi, taikhoan)
    with _KHOA:
        if k in _PHIEN:
            _dung(_PHIEN.pop(k))
        try:
            pr = subprocess.Popen([_cli(goi), *GOI[goi]["lenh"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
                                  start_new_session=True, env=_env(goi, taikhoan))
        except FileNotFoundError:
            return {"loi": f"Máy chủ chưa có công cụ đăng nhập {GOI[goi]['ten']}"}
        p = {"proc": pr, "url": "", "ma_thietbi": "", "xong": False, "loi": "", "dong": [], "bat_luc": time.time()}
        _PHIEN[k] = p

    def doc():
        try:
            for dong in pr.stdout:
                dong = MAU_RE.sub("", dong).replace("Paste code here if prompted >", "").strip()
                if not dong:
                    continue
                p["dong"].append(dong[:300])
                if not p["url"] and (m := URL_RE.search(dong)):
                    p["url"] = m.group(0)
                if goi == "chatgpt" and not p["ma_thietbi"] and (m := MA_THIETBI_RE.search(dong)):
                    p["ma_thietbi"] = m.group(0)
                thap = dong.lower()
                if "login successful" in thap or "successfully logged in" in thap:
                    p["xong"] = True
                elif any(x in thap for x in MA_SAI) or thap.startswith("error"):
                    p["loi"] = dong[:300]
        finally:
            if pr.wait() == 0:
                p["xong"] = True

    threading.Thread(target=doc, daemon=True).start()
    for _ in range(75):   # chờ tối đa khoảng 15 giây để CLI in đường link
        if p["url"] and (goi == "claude" or p["ma_thietbi"]) or p["xong"] or p["loi"] or pr.poll() not in (None, 0):
            break
        time.sleep(0.2)
    if not p["url"] and not p["xong"]:
        _dung(p)
        _PHIEN.pop(k, None)
        return {"loi": "Không lấy được đường link đăng nhập" + (f" ({_duoi(p)})" if _duoi(p) else "")}
    return {"url": p["url"], "ma_thietbi": p["ma_thietbi"] or None, "xong": p["xong"]}


def _duoi(p: dict, n: int = 2) -> str:
    """Vài dòng cuối CLI in ra (bỏ đường link) để nêu lý do khi lỗi."""
    return " ".join(x for x in p["dong"][-n - 2:] if not URL_RE.search(x))[-300:]


def dan_ma(goi: str, taikhoan: int, ma: str) -> dict:
    """Gói Claude: ghi mã anh dán vào CLI, chờ tối đa khoảng 24 giây."""
    _kiem(goi, taikhoan)
    p = _PHIEN.get((goi, taikhoan))
    if not p:
        return {"loi": "Chưa bắt đầu đăng nhập: bấm Đăng nhập trước"}
    pr = p["proc"]
    if pr.poll() is not None and not p["xong"]:
        return {"loi": "Lượt đăng nhập đã kết thúc: bấm Mở trang lấy mã mới"}
    p["loi"] = ""
    if not p["xong"]:
        try:
            pr.stdin.write(ma.strip() + "\n")
            pr.stdin.flush()
        except (BrokenPipeError, OSError):
            return {"loi": "Lượt đăng nhập đã kết thúc: bấm Mở trang lấy mã mới"}
    for _ in range(120):
        if p["xong"]:
            return _ket_thuc(goi, taikhoan)
        if p["loi"]:
            return {"loi": "Mã chưa đúng hoặc đã hết hạn. Bấm Mở trang lấy mã mới rồi dán lại"}
        if pr.poll() is not None:
            time.sleep(0.3)
            return _ket_thuc(goi, taikhoan) if p["xong"] else {"loi": "Đăng nhập chưa xong" + (f" ({_duoi(p)})" if _duoi(p) else "")}
        time.sleep(0.2)
    return {"loi": "Claude chưa trả lời sau 24 giây: bấm Kiểm tra lại hoặc lấy mã mới"}


def hoi(goi: str, taikhoan: int) -> dict:
    """Gói ChatGPT: giao diện hỏi lại mỗi vài giây tới khi xong."""
    _kiem(goi, taikhoan)
    p = _PHIEN.get((goi, taikhoan))
    if not p:
        return {"loi": "Chưa bắt đầu đăng nhập"}
    if p["xong"]:
        return _ket_thuc(goi, taikhoan)
    if time.time() - p["bat_luc"] > HAN_PHIEN_GIAY:
        huy(goi, taikhoan)
        return {"loi": "Mã thiết bị đã hết hạn: bấm Đăng nhập để lấy mã mới"}
    if p["proc"].poll() not in (None, 0) or p["loi"]:
        loi = _duoi(p)
        _PHIEN.pop((goi, taikhoan), None)
        return {"loi": "Đăng nhập chưa xong" + (f" ({loi})" if loi else "")}
    return {"cho": True}


def huy(goi: str, taikhoan: int) -> None:
    _kiem(goi, taikhoan)
    p = _PHIEN.pop((goi, taikhoan), None)
    if p:
        _dung(p)


def _ket_thuc(goi: str, taikhoan: int) -> dict:
    p = _PHIEN.pop((goi, taikhoan), None)
    if p:
        _dung(p)
    _NHO_TRANGTHAI.pop((goi, taikhoan), None)
    tt = trang_thai(goi, taikhoan, bo_nho=True)
    if not tt["da_noi"]:
        return {"loi": "CLI báo xong nhưng kiểm lại vẫn chưa đăng nhập: bấm Đăng nhập lại"}
    ghi_nguon(goi, taikhoan)
    return {"xong": True, **tt}


def trang_thai(goi: str, taikhoan: int, bo_nho: bool = False) -> dict:
    """Hỏi CLI tài khoản này đã đăng nhập chưa (nhớ 30 giây)."""
    _kiem(goi, taikhoan)
    k = (goi, taikhoan)
    nho = _NHO_TRANGTHAI.get(k)
    if nho and not bo_nho and time.time() - nho[0] < NHO_GIAY:
        return nho[1]
    lenh = ["auth", "status", "--json"] if goi == "claude" else ["login", "status"]
    try:
        r = subprocess.run([_cli(goi), *lenh], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=15, env=_env(goi, taikhoan))
        if goi == "claude":
            d = json.loads((r.stdout or "").strip() or "{}")
            kq = {"da_noi": bool(d.get("loggedIn")), "goi_dang_dung": d.get("subscriptionType") or None}
        else:
            chu = MAU_RE.sub("", r.stdout + r.stderr).lower()   # Codex in "Logged in using ChatGPT" hoặc "Not logged in"
            kq = {"da_noi": r.returncode == 0 and "logged in using chatgpt" in chu, "goi_dang_dung": None}
    except FileNotFoundError:
        kq = {"da_noi": False, "goi_dang_dung": None, "loi": "Máy chủ chưa có công cụ đăng nhập"}
    except (subprocess.TimeoutExpired, ValueError) as e:
        kq = {"da_noi": False, "goi_dang_dung": None, "khong_ro": True, "loi": type(e).__name__}
    _NHO_TRANGTHAI[k] = (time.time(), kq)
    return kq


def ma_nguon(goi: str, taikhoan: int) -> str:
    return f"goi_{goi}_{taikhoan:02d}"


def ghi_nguon(goi: str, taikhoan: int, thumuc: Path | None = None) -> str:
    """Thêm hoặc bật lại dòng G06 của tài khoản gói; ưu tiên mới = sau nguồn cuối cùng."""
    ma = ma_nguon(goi, taikhoan)
    bay = datetime.now(MUIGIO_VN).isoformat(timespec="seconds")
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        d = cn.execute("SELECT id FROM nguon_ai WHERE ma = ?", (ma,)).fetchone()
        if d:
            cn.execute("UPDATE nguon_ai SET trangthai = 'dung', da_het_luc = NULL WHERE id = ?", (d[0],))
            return d[0]
        uu = (cn.execute("SELECT coalesce(max(uutien), 0) FROM nguon_ai").fetchone()[0] or 0) + 1
        moi = maso.tao()
        cn.execute("INSERT INTO nguon_ai (id, ma, ten, hieuluc_tu, phienban, nguoi_khai, tao_luc, loai, dungchung, uutien)"
                   " VALUES (?, ?, ?, ?, 1, 'anh', ?, 'goi', 1, ?)",
                   (moi, ma, f"{GOI[goi]['ten']} · tài khoản {taikhoan:02d}", bay[:10], bay, uu))
        return moi
    finally:
        cn.close()


def danh_sach(thumuc: Path | None = None) -> list[dict]:
    """Thẻ màn 13: nguồn AI (G06) theo ưu tiên, kèm trạng thái đăng nhập của tài khoản gói."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cot = ["id", "ma", "ten", "loai", "uutien", "trangthai", "tran_tien_thang", "tyle_5gio", "tyle_tuan",
               "datlai_5gio_luc", "datlai_tuan_luc", "do_luc", "da_het_luc"]
        dong = [dict(zip(cot, r)) for r in cn.execute(f"SELECT {', '.join(cot)} FROM nguon_ai ORDER BY uutien, ma")]
    finally:
        cn.close()
    for d in dong:
        m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", d["ma"] or "")
        if m:
            d["goi"], d["taikhoan"] = m.group(1), int(m.group(2))
            d.update(trang_thai(d["goi"], d["taikhoan"]))
    return dong
