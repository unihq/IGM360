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
- Bản 0.7.1 (QĐ164, Y24):
  (1) chặn trùng: đăng nhập xong tài khoản N > 1 thì so định danh với các tài khoản đã kết nối cùng gói; trùng thì
      đăng xuất ô N, không ghi G06. Định danh chỉ so trong bộ nhớ, không ghi nhật ký, không trả ra giao diện.
      Claude: `email`, `orgId` của `claude auth status --json` (đã thấy trên CLI 2.1.330). ChatGPT: `email` trong
      `tokens.id_token` của `$CODEX_HOME/auth.json`, mã tổ chức `tokens.account_id` (theo mã nguồn công khai của Codex,
      codex-rs/login/src/auth/storage.rs, token_data.rs; chưa thấy trên máy thật). Không đọc được định danh thì không chặn.
  (2) gỡ tài khoản: đăng xuất CLI ở thư mục đó, G06 `trangthai` = `ngung` (không xoá dòng).
  (3) ô tài khoản N > 1 chỉ hiện sau khi đăng nhập xong (có dòng G06 đang dùng; bản vẽ Z6-TK); ô đã gỡ ẩn, kể cả
      đăng nhập (chưa từng có dòng G06).
- Bản 0.7.3 (QĐ169 đợt 1, Y26, bản vẽ Z8): ô tài khoản hiện "Tên · gói" đọc sống mỗi lần hỏi, **không lưu** vào bảng
  nào (dữ liệu cá nhân, PTD-07). Claude: `oauthAccount.displayName`, `planDisplayName` trong tệp hồ sơ của CLI
  (`.claude.json`; trường nội bộ, không có trong tài liệu chính thức). ChatGPT: loại gói `chatgpt_plan_type` trong
  `tokens.id_token` của `auth.json`, đổi ra chữ theo Codex (`codex-rs/protocol/src/auth.rs`); tên `name` nếu có (chưa
  xác minh). Đọc không được (tệp mất, đổi tên trường) thì lùi về "Tài khoản N" và họ gói như cũ, không báo lỗi.
- Bản 0.7.4 (QĐ173, Y29): bản 0.7.3 trên máy chủ ra "Tài khoản 1 · Max" vì `~/.claude.json` nằm ngoài ổ lưu, mất mỗi lần
  dựng lại vùng chứa (Y28). Image đặt CLAUDE_CONFIG_DIR = ổ lưu; sau cập nhật đăng nhập lại tài khoản 01 một lần để CLI
  ghi hồ sơ (tên, tên gói, email) vào ổ lưu. Email có lại thì chặn trùng tài khoản (Y24) so được với tài khoản 01.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from maychu.dulieu import aibam, ketnoi, phienban
from maychu.dulieu.saoluu import MUIGIO_VN

GOI = {
    "claude": {"ten": "Gói Claude", "hang": "anthropic", "cli_bien": "IGM360_CLAUDE_CLI", "cli": "claude", "bien_thumuc": "CLAUDE_CONFIG_DIR",
               "thumuc": "/home/igm/.claude", "lenh": ["auth", "login", "--claudeai"]},
    "chatgpt": {"ten": "Gói ChatGPT", "hang": "openai", "cli_bien": "IGM360_CODEX_CLI", "cli": "codex", "bien_thumuc": "CODEX_HOME",
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


def _env(goi: str, taikhoan: int, tao: bool = True) -> dict:
    tm = thu_muc(goi, taikhoan)
    env = dict(os.environ)
    if tm is not None:
        if not tao:
            env[GOI[goi]["bien_thumuc"]] = str(tm)
            return env
        tm.mkdir(parents=True, exist_ok=True)
        os.chmod(tm, 0o700)
        env[GOI[goi]["bien_thumuc"]] = str(tm)
    return env


def _kiem(goi: str, taikhoan: int) -> None:
    if goi not in GOI:
        raise ValueError("Gói không có")
    if not isinstance(taikhoan, int) or not 1 <= taikhoan <= SO_TAIKHOAN_TOIDA:
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
        _don(goi, taikhoan)
        return {"loi": "Không lấy được đường link đăng nhập" + (f" ({_duoi(p)})" if _duoi(p) else "")}
    return {"url": p["url"], "ma_thietbi": p["ma_thietbi"] or None, "xong": p["xong"]}


def _duoi(p: dict, n: int = 2) -> str:
    """Vài dòng cuối CLI in ra (bỏ đường link) để nêu lý do khi lỗi."""
    return " ".join(x for x in p["dong"][-n - 2:] if not URL_RE.search(x))[-300:]


def dan_ma(goi: str, taikhoan: int, ma: str, nguoi: str = "hethong") -> dict:
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
            return _ket_thuc(goi, taikhoan, nguoi)
        if p["loi"]:
            return {"loi": "Mã chưa đúng hoặc đã hết hạn. Bấm \"Mở trang\" lấy mã mới rồi dán lại."}   # N12
        if pr.poll() is not None:
            time.sleep(0.3)
            return _ket_thuc(goi, taikhoan, nguoi) if p["xong"] else {"loi": "Đăng nhập chưa xong" + (f" ({_duoi(p)})" if _duoi(p) else "")}
        time.sleep(0.2)
    return {"loi": "Claude chưa trả lời sau 24 giây: bấm Kiểm tra lại hoặc lấy mã mới"}


def hoi(goi: str, taikhoan: int, nguoi: str = "hethong") -> dict:
    """Gói ChatGPT: giao diện hỏi lại mỗi vài giây tới khi xong."""
    _kiem(goi, taikhoan)
    p = _PHIEN.get((goi, taikhoan))
    if not p:
        return {"loi": "Chưa bắt đầu đăng nhập"}
    if p["xong"]:
        return _ket_thuc(goi, taikhoan, nguoi)
    if time.time() - p["bat_luc"] > HAN_PHIEN_GIAY:
        huy(goi, taikhoan)
        return {"loi": "Mã thiết bị đã hết hạn: bấm Đăng nhập để lấy mã mới"}
    if p["proc"].poll() not in (None, 0) or p["loi"]:
        loi = _duoi(p)
        _PHIEN.pop((goi, taikhoan), None)
        _don(goi, taikhoan)
        return {"loi": "Đăng nhập chưa xong" + (f" ({loi})" if loi else "")}
    return {"cho": True}


def huy(goi: str, taikhoan: int) -> None:
    _kiem(goi, taikhoan)
    p = _PHIEN.pop((goi, taikhoan), None)
    if p:
        _dung(p)
    _don(goi, taikhoan)


def _g06(thumuc: Path | None = None) -> dict:
    """{mã G06 gói: trangthai}."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        return dict(cn.execute("SELECT ma, trangthai FROM nguon_ai WHERE substr(ma, 1, 4) = 'goi_'").fetchall())
    finally:
        cn.close()


def _don(goi: str, taikhoan: int, thumuc: Path | None = None) -> bool:
    """QĐ164 ý 3: xoá thư mục tài khoản N > 1 chưa đăng nhập, chưa từng có dòng G06, không đang đăng nhập."""
    tm = thu_muc(goi, taikhoan)
    if tm is None or not tm.is_dir() or (goi, taikhoan) in _PHIEN or ma_nguon(goi, taikhoan) in _g06(thumuc):
        return False
    if not re.fullmatch(r"taikhoan_\d\d", tm.name) or trang_thai(goi, taikhoan, bo_nho=True)["da_noi"]:
        return False
    shutil.rmtree(tm, ignore_errors=True)
    _NHO_TRANGTHAI.pop((goi, taikhoan), None)
    return not tm.exists()


def _jwt_than(jwt: str) -> dict:
    """Phần giữa của id_token (chỉ đọc thông tin, không kiểm chữ ký: tệp do CLI trên chính máy này ghi)."""
    try:
        than = jwt.split(".")[1]
        d = json.loads(base64.urlsafe_b64decode(than + "=" * (-len(than) % 4)))
        return d if isinstance(d, dict) else {}
    except (IndexError, ValueError, TypeError):
        return {}


def _dinh_danh(goi: str, taikhoan: int) -> tuple | None:
    """(email viết thường, mã tổ chức) của tài khoản; None khi không đọc được. Chỉ dùng để so, không ghi đi đâu."""
    tm = thu_muc(goi, taikhoan)
    if tm is not None and not tm.is_dir():
        return None
    try:
        if goi == "claude":
            r = subprocess.run([_cli(goi), "auth", "status", "--json"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=15, env=_env(goi, taikhoan, tao=False))
            d = json.loads((r.stdout or "").strip() or "{}")
            email, to_chuc = d.get("email"), d.get("orgId")
        else:
            goc = tm or Path(os.environ.get("CODEX_HOME") or os.environ.get("IGM360_THUMUC_CHATGPT", GOI[goi]["thumuc"]))
            tokens = (json.loads((goc / "auth.json").read_text(encoding="utf-8")) or {}).get("tokens") or {}
            than = _jwt_than(tokens.get("id_token") or "")
            email = than.get("email") or (than.get("https://api.openai.com/profile") or {}).get("email")
            to_chuc = tokens.get("account_id") or (than.get("https://api.openai.com/auth") or {}).get("chatgpt_account_id")
    except (OSError, ValueError, subprocess.TimeoutExpired, AttributeError):
        return None
    if not isinstance(email, str) or not email.strip():
        return None
    return email.strip().lower(), to_chuc if isinstance(to_chuc, str) and to_chuc else None


def trung(a: tuple | None, b: tuple | None) -> bool:
    """Cùng email và cùng tổ chức (thiếu mã tổ chức ở 01 bên thì chỉ so email). 02 email khác nhau cùng 01 tổ chức
    (ví dụ 02 chỗ ngồi của gói Team) là 02 tài khoản khác nhau."""
    if not a or not b or a[0] != b[0]:
        return False
    return a[1] is None or b[1] is None or a[1] == b[1]


def _dang_xuat(goi: str, taikhoan: int) -> bool:
    """Đăng xuất CLI ở thư mục của tài khoản; True khi kiểm lại đã ra."""
    lenh = ["auth", "logout"] if goi == "claude" else ["logout"]
    try:
        subprocess.run([_cli(goi), *lenh], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=20, env=_env(goi, taikhoan, tao=False))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    _NHO_TRANGTHAI.pop((goi, taikhoan), None)
    return not trang_thai(goi, taikhoan, bo_nho=True)["da_noi"]


def _ket_thuc(goi: str, taikhoan: int, nguoi: str = "hethong") -> dict:
    p = _PHIEN.pop((goi, taikhoan), None)
    if p:
        _dung(p)
    _NHO_TRANGTHAI.pop((goi, taikhoan), None)
    tt = trang_thai(goi, taikhoan, bo_nho=True)
    if not tt["da_noi"]:
        return {"loi": "CLI báo xong nhưng kiểm lại vẫn chưa đăng nhập: bấm Đăng nhập lại"}
    if taikhoan > 1:   # QĐ164 ý 1: chặn nối trùng
        moi = _dinh_danh(goi, taikhoan)
        for tk in range(1, SO_TAIKHOAN_TOIDA + 1):
            if tk != taikhoan and trang_thai(goi, tk)["da_noi"] and trung(moi, _dinh_danh(goi, tk)):
                _dang_xuat(goi, taikhoan)
                _don(goi, taikhoan)
                return {"loi": f"Tài khoản này đã kết nối ở tài khoản {tk:02d}", "trung_voi": tk}
    ghi_nguon(goi, taikhoan, nguoi=nguoi)
    return {"xong": True, **tt}


def go(goi: str, taikhoan: int, thumuc: Path | None = None) -> dict:
    """QĐ164 ý 2: gỡ tài khoản gói: đăng xuất CLI ở thư mục đó, G06 `trangthai` = `ngung` (giữ dòng, giữ lịch sử)."""
    _kiem(goi, taikhoan)
    p = _PHIEN.pop((goi, taikhoan), None)
    if p:
        _dung(p)
    if trang_thai(goi, taikhoan, bo_nho=True)["da_noi"] and not _dang_xuat(goi, taikhoan):
        return {"loi": f"Chưa đăng xuất được tài khoản {taikhoan:02d}: anh thử lại sau ít phút"}
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        so = cn.execute("UPDATE nguon_ai SET trangthai = 'ngung' WHERE ma = ?", (ma_nguon(goi, taikhoan),)).rowcount
    finally:
        cn.close()
    _don(goi, taikhoan, thumuc)
    return {"ok": True, "co_dong_g06": bool(so)}


def trang_thai(goi: str, taikhoan: int, bo_nho: bool = False) -> dict:
    """Hỏi CLI tài khoản này đã đăng nhập chưa (nhớ 30 giây)."""
    _kiem(goi, taikhoan)
    k = (goi, taikhoan)
    nho = _NHO_TRANGTHAI.get(k)
    if nho and not bo_nho and time.time() - nho[0] < NHO_GIAY:
        return nho[1]
    tm = thu_muc(goi, taikhoan)
    if tm is not None and not tm.is_dir():   # chưa có thư mục = chưa đăng nhập; chỉ hỏi thì không tạo thư mục
        return {"da_noi": False, "goi_dang_dung": None}
    lenh = ["auth", "status", "--json"] if goi == "claude" else ["login", "status"]
    try:
        r = subprocess.run([_cli(goi), *lenh], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=15, env=_env(goi, taikhoan, tao=False))
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


# Chữ loại gói ChatGPT theo Codex (`PlanType::display_name`, openai/codex `codex-rs/protocol/src/auth.rs`);
# QĐ170: mọi loại Pro (pro, prolite, promax) đều hiện "Pro", bỏ phần trong ngoặc.
TEN_GOI_CHATGPT = {"free": "Free", "go": "Go", "plus": "Plus", "pro": "Pro", "prolite": "Pro", "promax": "Pro",
                   "team": "Team", "business": "Business", "enterprise": "Enterprise", "ent26": "Enterprise",
                   "edu": "Edu", "edu_plus": "Edu Plus", "edu_pro": "Edu Pro"}
# Dòng mô tả gói (Z8): chỉ ghi khi có nguồn đã xác minh; chưa có thì bỏ dòng (không tự đặt chữ).
MOTA_GOI: dict[tuple, str] = {}
DAI_TOIDA = 60


def _chu_gon(v) -> str | None:
    return v.strip()[:DAI_TOIDA] if isinstance(v, str) and v.strip() else None


def _tep_hoso_claude(taikhoan: int) -> Path:
    """Tệp hồ sơ CLI Claude (CLI đặt `.claude.json` trong CLAUDE_CONFIG_DIR, không có biến thì ở `~`).
    Tài khoản 01: image đặt CLAUDE_CONFIG_DIR = ổ lưu `/home/igm/.claude` (QĐ173, Y29) nên hồ sơ còn sau khi dựng lại
    vùng chứa; máy không đặt biến thì `~/.claude.json`. Tài khoản N > 1: thư mục `taikhoan_NN` trong ổ lưu."""
    tm = thu_muc("claude", taikhoan)
    if tm is not None:
        return tm / ".claude.json"
    goc = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(goc) / ".claude.json" if goc else Path.home() / ".claude.json"


def _tep_auth_codex(taikhoan: int) -> Path:
    tm = thu_muc("chatgpt", taikhoan)
    return (tm or Path(os.environ.get("CODEX_HOME") or os.environ.get("IGM360_THUMUC_CHATGPT", GOI["chatgpt"]["thumuc"]))) / "auth.json"


def ho_so(goi: str, taikhoan: int, goi_dang_dung: str | None = None) -> dict:
    """{"ten_hien", "goi_ten", "mota_goi"} đọc sống; trường nào không đọc được thì None (giao diện lùi về
    "Tài khoản N"). `goi_dang_dung`: họ gói CLI trả (Claude `subscriptionType`), dùng khi không có tên gói."""
    ten = ten_goi = None
    try:
        if goi == "claude":
            oa = (json.loads(_tep_hoso_claude(taikhoan).read_text(encoding="utf-8")) or {}).get("oauthAccount") or {}
            ten, ten_goi = _chu_gon(oa.get("displayName")), _chu_gon(oa.get("planDisplayName"))
        else:
            tokens = (json.loads(_tep_auth_codex(taikhoan).read_text(encoding="utf-8")) or {}).get("tokens") or {}
            than = _jwt_than(tokens.get("id_token") or "")
            tho = (than.get("https://api.openai.com/auth") or {}).get("chatgpt_plan_type")
            ten, ten_goi = _chu_gon(than.get("name")), TEN_GOI_CHATGPT.get(tho) if isinstance(tho, str) else None
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    if not ten_goi and _chu_gon(goi_dang_dung):
        ten_goi = goi_dang_dung.strip().capitalize()   # đường lùi: họ gói như cũ ("max" → "Max")
    return {"ten_hien": ten, "goi_ten": ten_goi, "mota_goi": MOTA_GOI.get((goi, ten_goi))}


def nhan_dangnhap(goi: str, taikhoan: int) -> str:
    """Chữ ghi ở F04 mỗi lần đăng nhập gói xong (api.py ghi); màn 13 đọc lại để hiện lúc đăng nhập (N09)."""
    return f"{GOI[goi]['ten']} tài khoản {taikhoan:02d}"


def _lan_dangnhap(thumuc: Path | None = None) -> dict:
    """{chữ F04: lúc đăng nhập gần nhất}. Chưa có dòng nào = đăng nhập lúc cài máy (bước 2.04, ngoài phần mềm)."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        return dict(cn.execute("SELECT thamso_tomtat, max(luc) FROM nhatky_thaotac WHERE congcu = 'mohinh'"
                               " AND lenhcon = 'dangnhap_goi' AND ketqua = 'dat' GROUP BY thamso_tomtat").fetchall())
    finally:
        cn.close()


def ma_nguon(goi: str, taikhoan: int) -> str:
    return f"goi_{goi}_{taikhoan:02d}"


def ghi_nguon(goi: str, taikhoan: int, thumuc: Path | None = None, nguoi: str = "hethong") -> str:
    """Thêm hoặc bật lại dòng G06 của tài khoản gói; ưu tiên mới = sau nguồn cuối cùng.
    `nguoi`: "ai bấm" (mã tài khoản F01 hoặc mã máy, QĐ108)."""
    aibam.kiem(nguoi)
    ma = ma_nguon(goi, taikhoan)
    bay = datetime.now(MUIGIO_VN).isoformat(timespec="seconds")
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        d = cn.execute("SELECT id FROM nguon_ai WHERE ma = ?", (ma,)).fetchone()
        if d:
            cn.execute("UPDATE nguon_ai SET trangthai = 'dung', da_het_luc = NULL WHERE id = ?", (d[0],))
            return d[0]
        uu = (cn.execute("SELECT coalesce(max(uutien), 0) FROM nguon_ai").fetchone()[0] or 0) + 1
        return phienban.them(cn, "nguon_ai", {"ma": ma, "ten": f"{GOI[goi]['ten']} · tài khoản {taikhoan:02d}",
                                              "hieuluc_tu": bay[:10], "phienban": 1, "nguoi_khai": nguoi, "tao_luc": bay,
                                              "loai": "goi", "dungchung": 1, "uutien": uu,
                                              "hang": GOI[goi]["hang"], "cach_goi": "cli"})
    finally:
        cn.close()


# QĐ160 (N10 b): thứ tự dùng nguồn theo cách tính phí trước, `uutien` sau: gói (phí cố định tháng) luôn đứng trước
# mô hình chạy trên máy, rồi tới Khoá API (phí theo lượt); thêm gói thì tự đứng trước Khoá API (PTD-05 mục 3).
NHOM_PHI = {"goi": 0, "tuchay": 1, "khoa_api": 2}


def loai_nguon(d: dict) -> str:
    """Mã loại nguồn (QĐ187, PTD-08 Đ5, CDA K-MH5): 01 hàm duy nhất ở máy chủ. Mọi tài khoản cùng gói, mọi khoá cùng hãng
    chung 01 mã ("goi_claude_02" → "goi_claude", "khoa_anthropic_01" → "khoa_anthropic"); trùng 1–1 với nhóm
    "Hãng · Công cụ" ở giao diện. Nguồn khác giữ nguyên mã."""
    ma = d.get("ma") or ""
    m = re.fullmatch(r"(goi_(?:claude|chatgpt)|khoa_[a-z0-9]+?)_\d\d", ma)
    return m.group(1) if m else ma


def thu_tu(ds: list[dict]) -> list[dict]:
    """Thứ tự dùng nguồn 03 tầng (PTD-08 Đ5): (1) cách tính phí (QĐ160: gói → chạy trên máy → khoá API); (2) loại
    nguồn, xếp theo `uutien` nhỏ nhất trong loại; (3) `uutien` từng tài khoản. Tài khoản cùng loại đứng liền nhau:
    Claude 1 (1), ChatGPT 1 (2), Claude 2 (3) → Claude 1 → Claude 2 → ChatGPT 1."""
    nho: dict[str, int] = {}
    for d in ds:
        k = loai_nguon(d)
        nho[k] = min(nho.get(k, 10 ** 9), d.get("uutien") or 0)
    return sorted(ds, key=lambda d: (NHOM_PHI.get(d.get("loai"), 9), nho[loai_nguon(d)], loai_nguon(d),
                                     d.get("uutien") or 0, d.get("ma") or ""))


def _mohinh_gannhat(thumuc: Path | None = None) -> dict:
    """N15: {nguon_ai_id: mã mô hình} của lần gọi AI gần nhất có ghi mô hình (G04 `mohinh_id` → G08 `ma_mohinh`)."""
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cap = cn.execute("SELECT nguon_ai_id, mohinh_id FROM nhatky_ai WHERE mohinh_id IS NOT NULL ORDER BY luc").fetchall()
    finally:
        cn.close()
    if not cap:
        return {}
    gan = dict(cap)   # dòng sau đè dòng trước: còn lại lần gần nhất của mỗi nguồn
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        ten = dict(cn.execute(f"SELECT id, ma_mohinh FROM mohinh_ai WHERE id IN ({','.join('?' * len(gan))})",
                              list(gan.values())).fetchall())
    finally:
        cn.close()
    return {n: ten[m] for n, m in gan.items() if m in ten}


def danh_sach(thumuc: Path | None = None) -> list[dict]:
    """Thẻ màn 13: nguồn AI (G06) theo ưu tiên, kèm trạng thái đăng nhập của tài khoản gói."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cot = ["id", "ma", "ten", "loai", "hang", "uutien", "trangthai", "tran_tien_thang", "tyle_5gio", "tyle_tuan",
               "datlai_5gio_luc", "datlai_tuan_luc", "do_luc", "da_het_luc"]
        dong = thu_tu([dict(zip(cot, r)) for r in cn.execute(f"SELECT {', '.join(cot)} FROM nguon_ai")])
    finally:
        cn.close()
    gan = _mohinh_gannhat(thumuc)
    bay = datetime.now(MUIGIO_VN)
    for d in dong:
        d["mohinh_gannhat"] = gan.get(d["id"])
        for tl, dl in (("tyle_5gio", "datlai_5gio_luc"), ("tyle_tuan", "datlai_tuan_luc")):   # 0.7.7: qua giờ đặt lại = 0%
            try:
                if d.get(dl) and datetime.fromisoformat(d[dl]) <= bay:
                    if tl == "tyle_5gio":
                        d["da_datlai_luc"] = d[dl]   # Z12 tình huống (3): "Đã đặt lại lúc …"
                    d[tl], d[dl] = 0, None
            except ValueError:
                pass
    for d in dong:
        m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", d["ma"] or "")
        if m:
            d["goi"], d["taikhoan"] = m.group(1), int(m.group(2))
            d.update(trang_thai(d["goi"], d["taikhoan"]))
    return dong


def tinh_hinh_goi(thumuc: Path | None = None) -> dict:
    """Thẻ gói ở màn 13 (QĐ164 ý 3, bản vẽ Z6-TK): tài khoản 01 có sẵn trừ khi đã gỡ; tài khoản N > 1 chỉ hiện sau khi
    đăng nhập xong, tức có dòng G06 đang dùng (đang đăng nhập dở, đã huỷ, còn sót thư mục thì không hiện; khung đăng
    nhập ở giao diện tự hiện riêng). Tài khoản 01 đã đăng nhập mà chưa có dòng G06
    (ví dụ phiên Claude đăng nhập lúc cài máy, bước 2.04) thì tự ghi nguồn để Cổng AI dùng được; dòng đã gỡ (`ngung`)
    không tự bật lại, chỉ bật lại khi anh đăng nhập lại trên giao diện."""
    for k in [k for k, p in list(_PHIEN.items()) if time.time() - p["bat_luc"] > HAN_PHIEN_GIAY]:
        huy(*k)   # lượt bỏ dở quá 15 phút
    ra, lan, g06 = {}, _lan_dangnhap(thumuc), _g06(thumuc)
    for goi in GOI:
        ds = []
        for tk in range(1, SO_TAIKHOAN_TOIDA + 1):
            ma = ma_nguon(goi, tk)
            if g06.get(ma) == "ngung" or (tk > 1 and g06.get(ma) != "dung"):
                continue
            tt = trang_thai(goi, tk)
            if tt["da_noi"] and g06.get(ma) != "ngung" and (tk == 1 or ma in g06):
                ghi_nguon(goi, tk, thumuc)
            hs = ho_so(goi, tk, tt.get("goi_dang_dung")) if tt["da_noi"] else {"ten_hien": None, "goi_ten": None, "mota_goi": None}
            ds.append({"taikhoan": tk, "ma": ma_nguon(goi, tk), "dang_dangnhap": (goi, tk) in _PHIEN,
                       "dangnhap_luc": lan.get(nhan_dangnhap(goi, tk)), **tt, **hs})
        ra[goi] = ds
    return ra
