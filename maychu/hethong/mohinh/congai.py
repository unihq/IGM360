"""Cổng AI 03 nguồn (F34, ngày 06): gói Claude, gói ChatGPT, khoá API. Mỗi lần gọi ghi 01 dòng G04.

Chọn nguồn theo ưu tiên ở G06 (màn 13): bỏ nguồn ngừng, gói đang báo hết hạn mức (chưa tới giờ đặt lại),
tài khoản gói chưa đăng nhập, khoá API chưa đặt trần tiền hoặc tháng này đã chạm trần. Nguồn đầu báo hết hạn
mức thì chuyển sang nguồn kế tiếp. Giờ nghỉ do 01 chỗ quyết (Y36d): lượt bị từ chối → mốc nghỉ riêng `_HET_TK`
(`ghi_het_tai_khoan`); số đo → cửa sổ đã đầy (`_het_luc_dat_lai`). Cột `da_het_luc` chỉ còn ghi lại, không dùng để chặn.

- Gói Claude: Claude Code CLI chế độ không tương tác `claude -p --output-format stream-json --verbose`;
  đọc dòng `result` (chữ trả lời, lượng chữ, `total_cost_usd` = tiền quy đổi tham khảo, không phải tiền chi
  thêm) và dòng `rate_limit_event` (% cửa sổ 05 giờ, tuần, giờ đặt lại).
- Gói ChatGPT: Codex CLI `codex exec --json --skip-git-repo-check`; đọc `item.completed` loại `agent_message`,
  `turn.completed` (lượng chữ); % hạn mức đọc từ dòng `rate_limits` cuối cùng trong tệp phiên của Codex.
- Khoá API: Anthropic hoặc OpenAI qua httpx (thư viện đã duyệt); tiền thật = lượng chữ × giá G08.
Số việc AI chạy cùng lúc ≤ thông số `so_viec_ai_songsong` (QĐ71).
Bản 0.7.5 (QĐ178–QĐ183, PTD-08, Y31): `goi()` nhận `loai_viec` (mô hình mặc định theo loại việc, màn 13) và
`mohinh_id` (mô hình anh ghim cho cuộc trò chuyện; chỉ trò chuyện gửi, việc tự chạy và bot không đọc ghim). Mô hình
ghim vẫn qua đủ kiểm (đã kết nối, hạn mức, trần tiền, có giá); không dùng được thì tự dùng mặc định, trả `ghim_hong`
để ghi 01 dòng dưới câu trả lời; không tự chọn khoá API thay cho mô hình ghim (QĐ183).
Tiền ghi số nguyên theo phần triệu đơn vị tiền ở `tien_ma` (1 USD = 1.000.000); giá G08 là phần triệu USD
cho 1.000.000 chữ (token).
"""
import contextvars
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx

from maychu.dulieu import ketnoi, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.caidat import thongso
from maychu.hethong.kekhoa import kho
from maychu.hethong.mohinh import dangnhap_goi, danhmuc_mohinh

TRIEU = 1_000_000
GIAY_TOIDA = 600
HET_HANMUC = ("usage limit", "rate limit", "limit reached", "hit your limit", "quota", "429", "out of credits")
URL_ANTHROPIC = "https://api.anthropic.com/v1/messages"
URL_OPENAI = "https://api.openai.com/v1/chat/completions"
_CUNGLUC: dict = {"so": None, "sem": None}
_KHOA_SEM = threading.Lock()


class HetHanMuc(Exception):
    def __init__(self, loi: str, hanmuc: dict | None = None):
        super().__init__(loi)
        self.hanmuc = hanmuc or {}


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _cho_phep():
    so = max(1, int(thongso.doc_mot("so_viec_ai_songsong", "3") or 3))
    with _KHOA_SEM:
        if _CUNGLUC["so"] != so:
            _CUNGLUC.update(so=so, sem=threading.BoundedSemaphore(so))
        return _CUNGLUC["sem"]


# ---------------- Hạn mức gói ----------------
def _cua_so(ty_le, dat_lai):
    try:
        p = max(0.0, min(100.0, float(ty_le)))
    except (TypeError, ValueError):
        return None
    try:
        r = int(float(dat_lai)) if dat_lai else None
    except (TypeError, ValueError):
        r = None
    return {"pct": p, "datlai": r}


# Khung hạn mức riêng của 01 mô hình trong `rateLimitType` của CLI Claude (đọc mã CLI 2.1.330; chưa gặp lượt từ chối thật):
# five_hour, seven_day, overage = cả tài khoản; 03 khung dưới = riêng mô hình (Y36b P1, QĐ192 "hết theo từng mô hình").
HET_CA_TK = "hết hạn mức · cả tài khoản"   # lượt ghim gặp khung cả tài khoản: lượt mặc định không gọi lại tài khoản đó
KHUNG_MH = {"seven_day_opus": "Opus", "seven_day_sonnet": "Sonnet", "seven_day_overage_included": None}


def han_muc_claude(info: dict) -> dict:
    """Dòng `rate_limit_event` của Claude Code → {5gio, tuan}; bản cũ chỉ gửi cửa sổ đang chặn."""
    info = info.get("raw", info) if isinstance(info, dict) else {}
    ra = {}
    uw = info.get("unifiedWindows")
    if isinstance(uw, dict):
        for k, ten in (("five_hour", "5gio"), ("seven_day", "tuan")):
            w = uw.get(k)
            if isinstance(w, dict) and w.get("utilization") is not None:
                cs = _cua_so(float(w["utilization"]) * 100, w.get("resetsAt"))
                if cs:
                    ra[ten] = cs
    elif info.get("rateLimitType") in ("five_hour", "seven_day") and info.get("utilization") is not None:
        cs = _cua_so(float(info["utilization"]) * 100, info.get("resetsAt"))
        if cs:
            ra["5gio" if info["rateLimitType"] == "five_hour" else "tuan"] = cs
    if str(info.get("status", "")).lower() in ("rejected", "blocked"):
        loai = info.get("rateLimitType")
        try:
            dl = int(float(info["resetsAt"])) if info.get("resetsAt") else None
        except (TypeError, ValueError):
            dl = None
        if loai in KHUNG_MH:   # riêng 01 mô hình: chỉ ghi dấu mô hình, không đánh dấu cả tài khoản
            ra["het_mh"] = {"loai": loai, "datlai": dl}
        elif loai in ("five_hour", "seven_day", "overage"):
            ra["het"], ra["het_datlai"] = True, dl
        else:
            ra["het_khongro"] = {"datlai": dl}   # hãng không nói khung nào; Y36c P3: có resetsAt thì giữ
    return ra


def han_muc_codex(snap: dict) -> dict:
    """`rate_limits` của Codex (primary, secondary; used_percent, window_minutes, resets_at)."""
    ra = {}
    for ten_goc, macdinh in (("primary", "5gio"), ("secondary", "tuan")):
        w = snap.get(ten_goc) if isinstance(snap, dict) else None
        if not isinstance(w, dict):
            continue
        phut = w.get("window_minutes") or w.get("windowDurationMins")
        k = macdinh if not phut else ("5gio" if float(phut) <= 720 else "tuan")
        dl = w.get("resets_at") or w.get("resetsAt")
        if dl is None and w.get("resets_in_seconds") is not None:
            dl = time.time() + float(w["resets_in_seconds"])
        cs = _cua_so(w.get("used_percent", w.get("usedPercent")), dl)
        if cs:
            ra[k] = cs
    return ra


def _doc_han_muc_codex(thu_muc: Path | None) -> dict:
    """Dòng `rate_limits` cuối cùng trong tệp phiên mới nhất của Codex (chỉ đọc đuôi tệp)."""
    goc = (thu_muc or Path(os.environ.get("CODEX_HOME", "/home/igm/.codex"))) / "sessions"
    if not goc.exists():
        return {}
    tep = sorted(goc.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not tep:
        return {}
    with open(tep[-1], "rb") as f:
        f.seek(max(0, f.seek(0, 2) - 256_000))
        dong = f.read().decode("utf-8", "replace").splitlines()
    for d in reversed(dong):
        if '"rate_limits"' not in d:
            continue
        try:
            o = json.loads(d)
        except ValueError:
            continue
        p = o.get("payload", o)
        if isinstance(p, dict) and isinstance(p.get("rate_limits"), dict):
            return han_muc_codex(p["rate_limits"])
    return {}


def _mohinh_codex(thu_muc: Path | None) -> str | None:
    """Y31c S4: mô hình Codex thực dùng = trường `model` của dòng `turn_context` cuối trong tệp phiên mới nhất
    (`codex-rs/protocol/src/protocol.rs` `TurnContextItem.model`; chưa thấy trên máy thật). Không đọc được thì None."""
    goc = (thu_muc or Path(os.environ.get("CODEX_HOME", "/home/igm/.codex"))) / "sessions"
    tep = sorted(goc.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime) if goc.exists() else []
    if not tep:
        return None
    with open(tep[-1], "rb") as f:
        f.seek(max(0, f.seek(0, 2) - 256_000))
        dong = f.read().decode("utf-8", "replace").splitlines()
    for d in reversed(dong):
        if '"turn_context"' not in d:
            continue
        try:
            o = json.loads(d)
        except ValueError:
            continue
        p = o.get("payload") if isinstance(o, dict) else None
        if o.get("type") == "turn_context" and isinstance(p, dict) and isinstance(p.get("model"), str) and p["model"].strip():
            return p["model"].strip()[:80]
    return None


# ---------------- Đo hạn mức bị động (QĐ192, bản 0.7.7) ----------------
# Không gọi thêm lượt AI nào, không đọc khoá đăng nhập. Số đo đến từ (1) mỗi lượt gọi thật (rate_limit_event của Claude,
# tệp phiên Codex) và (2) lịch nền 10 phút đọc tệp phiên Codex mới nhất (`quet_codex`; tệp không đổi thì không đọc lại).
_DA_QUET: dict[str, float] = {}   # đường dẫn tệp phiên → mtime đã đọc
_HET_MH: dict[tuple, float] = {}  # (nguồn, mã mô hình; "" = mặc định của nguồn) → giờ dùng lại được (epoch); mất khi khởi động lại
_KHUNG_HET: dict[tuple, str] = {}  # (nguồn, mã) → khung hãng báo (seven_day_opus…), để giao diện ghi tên mô hình
_TEN_HET: dict[tuple, str] = {}    # (nguồn, mã) → mô hình CLI báo ở lượt bị từ chối (claude-opus-…)
_HET_TK: dict[str, float] = {}     # Y36c P2: nguồn gói → giờ cả tài khoản dùng lại được (epoch); mất khi khởi động lại
_KHOA_HET = threading.Lock()
HET_MACDINH_GIAY = 3600           # hãng không báo giờ đặt lại thì coi hết 01 giờ


def _tep_phien_moi(thu_muc: Path | None) -> Path | None:
    goc = (thu_muc or Path(os.environ.get("CODEX_HOME", "/home/igm/.codex"))) / "sessions"
    if not goc.exists():
        return None
    tep = sorted(goc.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return tep[-1] if tep else None


def quet_codex(thumuc=None) -> dict:
    """Lịch nền (10 phút): mỗi tài khoản gói ChatGPT đang dùng, đọc tệp phiên Codex mới nhất; tệp mới hơn lần đọc trước
    thì ghi % hạn mức với giờ đo = giờ của tệp. Trả {mã nguồn: "ghi" | "khong_doi" | "khong_co"}."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        ds = cn.execute("SELECT id, ma FROM nguon_ai WHERE trangthai = 'dung' AND ma LIKE 'goi_chatgpt_%'").fetchall()
    finally:
        cn.close()
    kq = {}
    for nid, ma in ds:
        m = re.fullmatch(r"goi_chatgpt_(\d\d)", ma or "")
        if not m:
            continue
        tk = int(m.group(1))
        tm = dangnhap_goi.thu_muc("chatgpt", tk)
        if tm is None:
            tm = Path(os.environ.get("CODEX_HOME") or os.environ.get("IGM360_THUMUC_CHATGPT", dangnhap_goi.GOI["chatgpt"]["thumuc"]))
        tep = _tep_phien_moi(tm)
        if tep is None:
            kq[ma] = "khong_co"
            continue
        mt = tep.stat().st_mtime
        if _DA_QUET.get(str(tep)) == mt:
            kq[ma] = "khong_doi"
            continue
        _DA_QUET[str(tep)] = mt
        hm = _doc_han_muc_codex(tm)
        if hm:
            ghi_han_muc(nid, hm, thumuc, luc=datetime.fromtimestamp(mt, MUIGIO_VN).isoformat(timespec="seconds"))
        kq[ma] = "ghi" if hm else "khong_co"
    return kq


def _gio_dung_lai(hm: dict) -> float:
    rieng = (hm or {}).get("het_mh") or {}
    if rieng.get("datlai") and rieng["datlai"] > time.time():   # giờ đặt lại của khung riêng mô hình
        return rieng["datlai"]
    sau = [w.get("datlai") for k, w in (hm or {}).items() if k != "het_mh" and isinstance(w, dict) and w.get("datlai")]
    sau = [x for x in sau if x and x > time.time()]
    return max(sau) if sau else time.time() + HET_MACDINH_GIAY


def het_mo_hinh(nguon_id: str, ma: str | None) -> float:
    """Mô hình này của nguồn này đang bị hãng từ chối vì hết hạn mức: trả giờ dùng lại được (epoch), không thì 0."""
    k = (nguon_id, ma or "")
    with _KHOA_HET:
        tg = _HET_MH.get(k, 0)
        if tg and tg <= time.time():
            _HET_MH.pop(k, None)
            _KHUNG_HET.pop(k, None)
            tg = 0
    return tg


def ghi_het_mo_hinh(nguon_id: str, ma: str | None, hm: dict | None, bao: str | None = None) -> None:
    k = (nguon_id, ma or "")
    with _KHOA_HET:
        _HET_MH[k] = _gio_dung_lai(hm or {})
        loai = ((hm or {}).get("het_mh") or {}).get("loai")
        if loai:
            _KHUNG_HET[k] = loai
        if bao:
            _TEN_HET[k] = bao


def het_tai_khoan(nguon_id: str) -> float:
    """Y36c P2: cả tài khoản gói đang nghỉ vì hãng từ chối: giờ dùng lại được (epoch), không thì 0."""
    with _KHOA_HET:
        tg = _HET_TK.get(nguon_id, 0)
        if tg and tg <= time.time():
            _HET_TK.pop(nguon_id, None)
            tg = 0
    return tg


def ghi_het_tai_khoan(nguon_id: str, datlai: float | None, hm: dict | None = None) -> float:
    """Y36c P2, P3: mốc nghỉ riêng của cả tài khoản tính từ lúc bị từ chối, không trông vào giờ đặt lại cũ đã lưu.
    Giờ lấy theo thứ tự: resetsAt hãng báo ở lượt từ chối (P3) → giờ đặt lại của cửa sổ đã đầy (≥ 100%) → 01 giờ
    (không báo giờ thì nghỉ 01 giờ; nguồn tham khảo ghi ở tailieu/Songuongoc.md)."""
    bay = time.time()
    if not (datlai and datlai > bay):
        day = [w.get("datlai") for w in (hm or {}).values() if isinstance(w, dict) and (w.get("pct") or 0) >= 100]
        day = [x for x in day if x and x > bay]
        datlai = max(day) if day else bay + HET_MACDINH_GIAY
    with _KHOA_HET:
        _HET_TK[nguon_id] = datlai
    return datlai


def tk_nghi_den(d: dict) -> str | None:
    """N5 (Y36e): màn 13 – cả tài khoản gói đang tạm nghỉ (mốc nghỉ riêng hoặc cửa sổ đã đầy) thì trả giờ dùng lại."""
    if d.get("loai") != "goi":
        return None
    return _den_luc(d["id"]) if het_tai_khoan(d["id"]) or _het_luc_dat_lai(d) else None


def mo_ta_het(nguon_id: str, ma: str | None) -> dict:
    """Mô hình đang hết của 01 nguồn để giao diện ghi tên: {ma (None = mặc định), ten_khung (Opus…), bao (mã CLI báo)}."""
    k = (nguon_id, ma or "")
    with _KHOA_HET:
        loai, bao = _KHUNG_HET.get(k), _TEN_HET.get(k)
    return {"ma": ma or None, "ten_khung": KHUNG_MH.get(loai) if loai else None, "bao": bao}


def bo_het_mo_hinh(nguon_id: str, ma: str | None) -> None:
    with _KHOA_HET:
        _HET_MH.pop((nguon_id, ma or ""), None)
        _KHUNG_HET.pop((nguon_id, ma or ""), None)
        _TEN_HET.pop((nguon_id, ma or ""), None)


def ds_het_mo_hinh(nguon_id: str) -> list[dict]:
    """Màn 13 (Y36b): mô hình của nguồn này đang hết hạn mức riêng: [{ma (None = mặc định), ten_khung, den}]."""
    bay = time.time()
    with _KHOA_HET:
        ds = [(k[1], tg, _KHUNG_HET.get(k), _TEN_HET.get(k)) for k, tg in _HET_MH.items() if k[0] == nguon_id and tg > bay]
    return [{"ma": ma or None, "ten_khung": KHUNG_MH.get(loai) if loai else None, "bao": bao,
             "den": _iso(tg)} for ma, tg, loai, bao in sorted(ds, key=lambda x: x[0])]


def _iso(tg: float) -> str:
    return datetime.fromtimestamp(tg, MUIGIO_VN).isoformat(timespec="seconds")


def ghi_han_muc(nguon_id: str, hm: dict, thumuc=None, luc: str | None = None) -> None:
    """`luc`: giờ số đo (mặc định: bây giờ); quét tệp phiên Codex ghi giờ của tệp (0.7.7)."""
    if not hm:
        return
    bay = luc or _bay_gio()
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cot, gt = ["do_luc = ?"], [bay]
        for ten, c_tl, c_dl in (("5gio", "tyle_5gio", "datlai_5gio_luc"), ("tuan", "tyle_tuan", "datlai_tuan_luc")):
            if ten in hm:
                cot += [f"{c_tl} = ?", f"{c_dl} = ?"]
                dl = hm[ten]["datlai"]
                gt += [round(hm[ten]["pct"]), datetime.fromtimestamp(dl, MUIGIO_VN).isoformat(timespec="seconds") if dl else None]
        if hm.get("het"):
            cot.append("da_het_luc = 1")
        cn.execute(f"UPDATE nguon_ai SET {', '.join(cot)} WHERE id = ?", [*gt, nguon_id])
    finally:
        cn.close()


# ---------------- Nguồn ----------------
_COT_MH = ("id", "ma", "gia_vao", "gia_ra", "tien_ma")


def _nguon(thumuc=None, loai_viec=None) -> list[dict]:
    """Nguồn đang dùng theo ưu tiên, mỗi nguồn kèm mô hình sẽ gọi:
    - loại việc có mô hình mặc định (màn 13) → nguồn của mô hình đó đứng đầu, gọi đúng mô hình đó;
    - gói khác: mô hình mặc định của CLI (không truyền --model);
    - khoá API khác: dòng G08 đầu tiên đã có giá (cũ: dòng đầu tiên)."""
    md = danhmuc_mohinh.macdinh_khoa(loai_viec, thumuc) if loai_viec else None   # Đ6: (loại nguồn, mã) hoặc None
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cot = ["id", "ma", "ten", "loai", "uutien", "tran_tien_thang", "tyle_5gio", "tyle_tuan", "datlai_5gio_luc",
               "datlai_tuan_luc", "do_luc", "da_het_luc"]
        ds = dangnhap_goi.thu_tu([dict(zip(cot, r)) for r in cn.execute(
            f"SELECT {', '.join(cot)} FROM nguon_ai WHERE trangthai = 'dung'")])   # QĐ160: gói trước Khoá API
        for d in ds:
            d["macdinh_loai"] = bool(md and dangnhap_goi.loai_nguon(d) == md[0])   # mọi tài khoản cùng loại (Đ6)
            dong = danhmuc_mohinh.dong_cua(d["id"], md[1], thumuc) if d["macdinh_loai"] and md[1] else None
            if dong:
                d["mohinh"] = dong
            elif d["loai"] == "goi":   # gói: mô hình mặc định của CLI; "mặc định của nguồn" (Z10c) cũng vậy
                d["mohinh"] = None
            else:
                m = cn.execute("SELECT id, ma_mohinh, gia_vao, gia_ra, tien_ma FROM mohinh_ai WHERE nguon_ai_id = ?"
                               " AND coalesce(trangthai, 'dung') = 'dung' AND ma_mohinh IS NOT NULL"
                               " ORDER BY (gia_vao IS NULL), rowid LIMIT 1",
                               (d["id"],)).fetchone()
                d["mohinh"] = dict(zip(_COT_MH, m)) if m else None
        return sorted(ds, key=lambda d: not d.get("macdinh_loai"))
    finally:
        cn.close()


def _het_luc_dat_lai(d: dict) -> bool:
    """Số đo cho thấy cửa sổ đã đầy (≥ 100%): chặn tới giờ đặt lại của cửa sổ đó; cửa sổ đầy mà không có giờ đặt lại
    thì chặn 60 phút từ lần đo. Y36d P3: KHÔNG xét cờ `da_het_luc` nữa: lượt bị từ chối do mốc nghỉ riêng `_HET_TK`
    quyết (đúng `resetsAt` hãng báo), để giờ đặt lại đã lưu của cửa sổ chưa đầy không đè mốc đó."""
    bay = _bay_gio()
    moc = datetime.fromtimestamp(time.time() - 3600, MUIGIO_VN).isoformat(timespec="seconds")
    for tl, dl in (("tyle_5gio", "datlai_5gio_luc"), ("tyle_tuan", "datlai_tuan_luc")):
        if (d[tl] or 0) >= 100 and (d[dl] > bay if d[dl] else (d.get("do_luc") or "") > moc):
            return True
    return False


def _ly_do_nghi(d: dict, ma: str | None, kq) -> dict:
    """Y36d P3b: nguồn bỏ qua vì CẢ tài khoản đang tạm nghỉ (mô hình được chọn chưa bị từ chối riêng) thì trả
    {tk_nghi, den, nguon_id} để giao diện ghi "Tài khoản Claude đang tạm nghỉ đến …", không ghi "<mô hình> hết hạn mức"."""
    if d.get("loai") != "goi":
        return {}
    nghi = bool(het_tai_khoan(d["id"])) or _het_luc_dat_lai(d)
    if not nghi or (het_mo_hinh(d["id"], ma) and kq != HET_CA_TK):
        return {}
    return {"tk_nghi": True, "den": _den_luc(d["id"]), "nguon_id": d["id"]}


def tien_thang(nguon_id: str, thumuc=None) -> int:
    thang = _bay_gio()[:7]
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        return cn.execute("SELECT coalesce(sum(sotien), 0) FROM nhatky_ai WHERE nguon_ai_id = ? AND substr(luc, 1, 7) = ?",
                          (nguon_id, thang)).fetchone()[0]
    finally:
        cn.close()


def dung_duoc(d: dict, thumuc=None) -> tuple[bool, str]:
    m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", d["ma"] or "")
    if d["loai"] == "goi":
        if not m:
            return False, "mã nguồn gói không đúng"
        if _het_luc_dat_lai(d) or het_tai_khoan(d["id"]):   # Y36c P2: mốc nghỉ riêng, không bỏ qua vì giờ đặt lại cũ đã qua
            return False, "hết hạn mức"
        if not dangnhap_goi.trang_thai(m.group(1), int(m.group(2)))["da_noi"]:
            return False, "chưa đăng nhập"
        return True, ""
    if not d["tran_tien_thang"]:
        return False, "chưa đặt hạn mức"
    if not kho.tim(d["ma"], thumuc):
        return False, "chưa có khoá"
    if not d["mohinh"] or d["mohinh"]["gia_vao"] is None or d["mohinh"]["gia_ra"] is None:
        return False, "chưa có giá mô hình"
    if tien_thang(d["id"], thumuc) >= d["tran_tien_thang"] * TRIEU:
        return False, "chạm hạn mức chi tháng"
    return True, ""


# ---------------- 03 cách gọi ----------------
def _chay(lenh: list, env: dict, vao: str | None = None, giay: int = GIAY_TOIDA) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as cho_lam:   # việc trò chuyện không cần thư mục mã, không cho đụng tệp
        return subprocess.run(lenh, input=vao, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=giay, env=env, cwd=cho_lam)


# QĐ195 (Y36e, lỗi H17): trò chuyện của anh không đặt trần lượt, được tra web; vẫn cấm lệnh máy, cấm ghi/sửa tệp
# (giống Codex `--sandbox read-only`). Phanh kẹt vòng: 600 giây/câu (GIAY_TOIDA). Việc khác (Gọi thử, việc nền) giữ 01 lượt.
_TRA_WEB: contextvars.ContextVar = contextvars.ContextVar("igm360_tra_web", default=False)
CONGCU_TRA_WEB = "WebSearch,WebFetch"                      # công cụ duy nhất có mặt và được phép
CONGCU_CAM = "Bash,PowerShell,Write,Edit,MultiEdit,NotebookEdit"   # chặn thêm 01 lớp, phòng cài đặt máy bật lại
LOI_CLAUDE = {"error_max_turns": "chạm trần số lượt", "error_during_execution": "lỗi khi chạy",
              "error_max_budget_usd": "chạm trần chi phí", "error_max_structured_output_retries": "lỗi định dạng trả lời"}


class LoiAI(RuntimeError):
    """Lỗi 01 lượt gọi AI: `ngan` (chữ ngắn cho anh), `ct` (loại lỗi và câu hãng báo, để rê chuột)."""
    def __init__(self, hang: str, ngan: str, ct: str = ""):
        super().__init__(f"{hang} {ngan}" + (f" ({ct})" if ct else ""))
        self.ngan, self.ct = ngan, ct


def _loi_claude(kq: dict | None, r) -> tuple[str, str]:
    """Y36e: đọc đúng loại lỗi Claude từ dòng `result` (`subtype` + `errors`), không lấy đuôi chữ JSON."""
    if kq:
        sub = str(kq.get("subtype") or "")
        loi = [str(x) for x in (kq.get("errors") or []) if x]
        if isinstance(kq.get("result"), str) and kq["result"].strip():
            loi.append(kq["result"].strip())
        ct = (sub + (": " if sub and loi else "") + "; ".join(loi))[:200]
        return LOI_CLAUDE.get(sub, "báo lỗi"), ct
    dong = [d.strip() for d in (r.stderr or "").splitlines() if d.strip() and not d.strip().startswith("{")]
    return "không trả kết quả", (dong[-1][:200] if dong else "")


def _goi_claude(taikhoan: int, cau: str, mohinh: str | None) -> dict:
    lenh = [dangnhap_goi._cli("claude"), "-p", "--output-format", "stream-json", "--verbose"]
    if _TRA_WEB.get():
        lenh += ["--tools", CONGCU_TRA_WEB, "--allowedTools", CONGCU_TRA_WEB, "--disallowedTools", CONGCU_CAM,
                 "--strict-mcp-config"]
    else:
        lenh += ["--max-turns", "1"]
    if mohinh:
        lenh += ["--model", mohinh]
    r = _chay(lenh, dangnhap_goi._env("claude", taikhoan), vao=cau)
    kq, hm, bao = None, {}, None
    for dong in r.stdout.splitlines():
        try:
            o = json.loads(dong)
        except ValueError:
            continue
        if o.get("type") == "system" and o.get("subtype") == "init" and isinstance(o.get("model"), str):
            bao = o["model"].strip()[:80] or None   # Y31c S4: mô hình CLI thực dùng (dòng khởi đầu stream-json)
        elif o.get("type") == "rate_limit_event":
            hm.update(han_muc_claude(o.get("rate_limit_info") or {}))
        elif o.get("type") == "result":
            kq = o
    if not kq or kq.get("is_error") or kq.get("subtype") not in (None, "success"):
        ngan, ct = _loi_claude(kq, r)
        if hm.get("het") or hm.get("het_mh") or hm.get("het_khongro") or any(x in ct.lower() for x in HET_HANMUC):
            if bao:
                hm["mh_bao"] = bao
            raise HetHanMuc(ct[:300] or "hết hạn mức", hm)
        raise LoiAI("Claude", ngan, ct)
    u = kq.get("usage") or {}
    vao = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    tk = kq.get("total_cost_usd")
    return {"chu": kq.get("result") or "", "vao": vao, "ra": int(u.get("output_tokens") or 0), "sotien": None,
            "sotien_thamkhao": round(float(tk) * TRIEU) if tk is not None else None, "tien_ma": "USD", "hanmuc": hm,
            "mohinh_bao": bao}


def _goi_chatgpt(taikhoan: int, cau: str, mohinh: str | None) -> dict:
    lenh = [dangnhap_goi._cli("chatgpt"), "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only"]
    if mohinh:
        lenh += ["-m", mohinh]
    lenh.append("-")   # đọc câu hỏi từ đầu vào chuẩn
    env = dangnhap_goi._env("chatgpt", taikhoan)
    r = _chay(lenh, env, vao=cau)
    chu, vao, ra, loi = [], 0, 0, ""
    for dong in r.stdout.splitlines():
        try:
            o = json.loads(dong)
        except ValueError:
            continue
        t = o.get("type")
        if t == "item.completed" and (o.get("item") or {}).get("type") == "agent_message":
            chu.append(o["item"].get("text") or "")
        elif t == "turn.completed":
            u = o.get("usage") or {}
            vao += int(u.get("input_tokens") or 0)
            ra += int(u.get("output_tokens") or 0) + int(u.get("reasoning_output_tokens") or 0)
        elif t in ("turn.failed", "error"):
            loi = (o.get("error") or {}).get("message") if t == "turn.failed" else o.get("message")
    tm = Path(env["CODEX_HOME"]) if "CODEX_HOME" in env else None
    hm = _doc_han_muc_codex(tm)
    if loi or r.returncode != 0 or not chu:
        loi = loi or (r.stderr or r.stdout)[-300:]
        if any(x in str(loi).lower() for x in HET_HANMUC):
            raise HetHanMuc(str(loi)[:300], hm)
        raise RuntimeError(f"ChatGPT không trả lời được: {str(loi)[:300]}")
    return {"chu": "\n".join(chu), "vao": vao, "ra": ra, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD",
            "hanmuc": hm, "mohinh_bao": _mohinh_codex(tm)}


def _goi_khoa(d: dict, cau: str, thumuc=None, client=None) -> dict:
    khoa = kho.doc(kho.tim(d["ma"], thumuc), thumuc)
    m = d["mohinh"]
    c = client or httpx.Client(timeout=GIAY_TOIDA)
    if d["ma"].startswith("khoa_anthropic"):
        r = c.post(URL_ANTHROPIC, headers={"x-api-key": khoa, "anthropic-version": "2023-06-01"},
                   json={"model": m["ma"], "max_tokens": 4096, "messages": [{"role": "user", "content": cau}]})
        if r.status_code == 429:
            raise HetHanMuc("Anthropic báo vượt hạn mức (429)")
        r.raise_for_status()
        o = r.json()
        chu = "".join(x.get("text", "") for x in o.get("content", []) if x.get("type") == "text")
        vao, ra = int(o["usage"]["input_tokens"]), int(o["usage"]["output_tokens"])
    elif d["ma"].startswith("khoa_openai"):
        r = c.post(URL_OPENAI, headers={"Authorization": f"Bearer {khoa}"},
                   json={"model": m["ma"], "messages": [{"role": "user", "content": cau}]})
        if r.status_code == 429:
            raise HetHanMuc("OpenAI báo vượt hạn mức (429)")
        r.raise_for_status()
        o = r.json()
        chu = o["choices"][0]["message"]["content"] or ""
        vao, ra = int(o["usage"]["prompt_tokens"]), int(o["usage"]["completion_tokens"])
    else:
        raise RuntimeError("Khoá API chưa rõ của hãng nào (mã nguồn phải bắt đầu bằng khoa_anthropic hoặc khoa_openai)")
    tien = round((vao * m["gia_vao"] + ra * m["gia_ra"]) / TRIEU)
    bao = o.get("model") if isinstance(o.get("model"), str) else None   # Y31c S4: hãng trả mô hình thực dùng
    return {"chu": chu, "vao": vao, "ra": ra, "sotien": tien, "sotien_thamkhao": None, "tien_ma": m["tien_ma"] or "USD",
            "hanmuc": {}, "mohinh_bao": bao}


# ---------------- Gọi ----------------
def _ghi_g04(d: dict, kq: dict | None, ketqua: str, ms: int, viecnen_id=None, thumuc=None) -> str:
    ma = maso.tao()
    kq = kq or {}
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        cn.execute("INSERT INTO nhatky_ai (id, luc, nguon_ai_id, mohinh_id, viecnen_id, luong_vao, luong_ra, sotien,"
                   " sotien_thamkhao, tien_ma, ketqua, thoigian_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (ma, _bay_gio(), d["id"], (d.get("mohinh") or {}).get("id"), viecnen_id, kq.get("vao"), kq.get("ra"),
                    kq.get("sotien"), kq.get("sotien_thamkhao"), kq.get("tien_ma"), ketqua, ms))
    finally:
        cn.close()
    return ma


def _thu(d: dict, cau: str, bo_qua: list, viecnen_id=None, thumuc=None, client=None, ghim: bool = False):
    """Gọi 01 nguồn với mô hình `d["mohinh"]`. Được thì trả kết quả gọi; không được thì ghi `bo_qua`, trả lý do.
    `ghim`: lượt thử mô hình anh ghim. Hết hạn mức riêng của 01 mô hình (ví dụ Opus) chỉ ghi dấu mô hình đó, không chặn
    mô hình khác cùng tài khoản (Y36b P1)."""
    ten = d["ten"] + (" (mô hình đã chọn)" if ghim else "")
    ma_mh = (d.get("mohinh") or {}).get("ma")
    ok, lydo = dung_duoc(d, thumuc)
    if ok and het_mo_hinh(d["id"], ma_mh):   # 0.7.7: mô hình vừa bị từ chối vì hết hạn mức thì không gọi lại tới giờ dùng lại
        ok, lydo = False, "hết hạn mức (mô hình)"
    if not ok:
        bo_qua.append({"nguon": ten, "lydo": lydo})
        return lydo
    m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", d["ma"] or "")
    t0 = time.monotonic()
    try:
        if m and m.group(1) == "claude":
            kq = _goi_claude(int(m.group(2)), cau, (d["mohinh"] or {}).get("ma"))
        elif m:
            kq = _goi_chatgpt(int(m.group(2)), cau, (d["mohinh"] or {}).get("ma"))
        else:
            kq = _goi_khoa(d, cau, thumuc, client)
    except HetHanMuc as e:
        _ghi_g04(d, None, "het_hanmuc", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
        hm = dict(e.hanmuc or {})
        rieng = hm.pop("het_mh", None)
        khongro = hm.pop("het_khongro", None) or {}
        dl_tk = hm.pop("het_datlai", None) or khongro.get("datlai")
        bao = hm.pop("mh_bao", None)
        # Y36b P1: hãng báo khung riêng 01 mô hình → chỉ ghi dấu mô hình đó, cả tài khoản vẫn dùng được (mô hình khác);
        # hãng báo khung cả tài khoản (05 giờ, tuần) → đánh dấu cả tài khoản, kể cả lượt ghim;
        # không rõ khung: lượt ghim chỉ ghi dấu mô hình, lượt thường đánh dấu cả tài khoản như cũ.
        tk_het = bool(hm.get("het")) or (not ghim and not rieng)
        if ma_mh or rieng:
            ghi_het_mo_hinh(d["id"], ma_mh, {**hm, "het_mh": rieng or {"datlai": khongro.get("datlai")}}, bao)   # P3
        elif bao:
            with _KHOA_HET:
                _TEN_HET[(d["id"], "")] = bao
        if tk_het and d["loai"] == "goi":   # khoá API báo 429 thường là giới hạn theo phút: không nghỉ 01 giờ
            ghi_het_tai_khoan(d["id"], dl_tk, hm)
        hm["het"] = tk_het
        ghi_han_muc(d["id"], hm, thumuc)
        bo_qua.append({"nguon": ten, "lydo": f"hết hạn mức: {e}"[:200]})
        return HET_CA_TK if tk_het else "hết hạn mức"
    except subprocess.TimeoutExpired:
        _ghi_g04(d, None, "quagio", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
        bo_qua.append({"nguon": ten, "lydo": "quá giờ"})
        return "quá giờ"
    except Exception as e:  # noqa: BLE001 - lỗi 01 nguồn thì thử nguồn sau
        _ghi_g04(d, None, "loi", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
        bo_qua.append({"nguon": ten, "lydo": str(e)[:200], **({"loi": e.ngan, "loi_ct": e.ct} if isinstance(e, LoiAI) else {})})
        return "lỗi"
    ms = int((time.monotonic() - t0) * 1000)
    bo_het_mo_hinh(d["id"], ma_mh)
    ghi_han_muc(d["id"], kq.get("hanmuc") or {}, thumuc)
    kq["nhatky_ai_id"] = _ghi_g04(d, kq, "xong", ms, viecnen_id, thumuc)
    return kq


def _tk(d: dict) -> int | None:
    m = re.fullmatch(r"goi_(?:claude|chatgpt)_(\d\d)", d.get("ma") or "")
    return int(m.group(1)) if m else None


def _den_luc(nguon_id: str, thumuc=None) -> str | None:
    """Giờ tài khoản đang nghỉ dùng lại được: mốc nghỉ riêng (Y36c P2); không có thì giờ đặt lại của cửa sổ đã đầy;
    không rõ cửa sổ thì giờ đặt lại sớm nhất."""
    tg = het_tai_khoan(nguon_id)
    if tg:
        return _iso(tg)
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        r = cn.execute("SELECT tyle_5gio, datlai_5gio_luc, tyle_tuan, datlai_tuan_luc FROM nguon_ai WHERE id = ?", (nguon_id,)).fetchone()
    finally:
        cn.close()
    if not r:
        return None
    bay = _bay_gio()
    day = [dl for tl, dl in ((r[0], r[1]), (r[2], r[3])) if (tl or 0) >= 100 and dl and dl > bay]
    sau = sorted(dl for dl in (r[1], r[3]) if dl and dl > bay)
    return max(day) if day else (sau[0] if sau else None)


def _chay_bang(d: dict, ds: list, nghi: dict, thumuc=None, nghi_mh: dict | None = None) -> dict:
    """QĐ189: tài khoản thực chạy; chạy dự phòng (tài khoản cùng loại đứng trước đang hết hạn mức) thì kèm tài khoản đó và
    giờ dùng lại được. Chỉ để giao diện hiện khi rê chuột."""
    tk = _tk(d)
    if tk is None:
        return {"chay_tk": None, "du_phong": None}
    loai = dangnhap_goi.loai_nguon(d)
    truoc = next((x for x in ds if x["id"] != d["id"] and dangnhap_goi.loai_nguon(x) == loai and x["id"] in nghi
                  and str(nghi[x["id"]]).startswith("hết hạn mức")), None)
    if not truoc:
        return {"chay_tk": tk, "du_phong": None}
    ma = (nghi_mh or {}).get(truoc["id"])
    tg = het_mo_hinh(truoc["id"], ma)
    if tg and nghi[truoc["id"]] != HET_CA_TK and not het_tai_khoan(truoc["id"]) and not _het_luc_dat_lai(truoc):
        # N4: riêng 01 mô hình hết → giao diện ghi "Opus của tài khoản 1 hết hạn mức đến …" như màn 13
        return {"chay_tk": tk, "du_phong": {"tk": _tk(truoc), "den": _iso(tg), "rieng": True, **mo_ta_het(truoc["id"], ma)}}
    return {"chay_tk": tk, "du_phong": {"tk": _tk(truoc), "den": _den_luc(truoc["id"], thumuc)}}


def goi(cau: str, *, viecnen_id=None, chi_nguon_id=None, loai_viec=None, mohinh_id=None, thumuc=None,
        client=None) -> dict:
    """Gọi AI 01 lần theo thứ tự ưu tiên (hoặc chỉ 01 nguồn khi bấm Gọi thử). Trả {chu, nguon, nguon_id,
    nhatky_ai_id, mohinh_id, mohinh, ghim_hong, bo_qua} hoặc {loi, bo_qua}. `mohinh_id` (G08): mô hình ghim, thử trước;
    không dùng được thì `ghim_hong` = {mohinh_id, ma, het_hanmuc, lydo} và gọi theo mặc định."""
    bo_qua, ghim_hong, nghi, nghi_mh, het_dau = [], None, {}, {}, None
    sem = _cho_phep()
    tra_web = _TRA_WEB.set(loai_viec == "trochuyen" and not chi_nguon_id)   # QĐ195: chỉ trò chuyện của anh
    try:
        return _goi_trong(cau, bo_qua, sem, viecnen_id, chi_nguon_id, loai_viec, mohinh_id, thumuc, client)
    finally:
        _TRA_WEB.reset(tra_web)


def _goi_trong(cau, bo_qua, sem, viecnen_id, chi_nguon_id, loai_viec, mohinh_id, thumuc, client) -> dict:
    ghim_hong, nghi, nghi_mh, het_dau, loi_dau, da_ghim = None, {}, {}, None, None, {}
    with sem:
        ds = _nguon(thumuc, loai_viec)
        if danhmuc_mohinh.la_viec_nen(loai_viec) or viecnen_id is not None:
            mohinh_id = None   # K-VN Đ2: lượt gọi từ việc nền hoặc bot không đọc ghim, chặn ở cổng (không trông vào nơi gọi)
        if mohinh_id and not chi_nguon_id:
            # 0.7.6 (QĐ187, Đ1, Đ5): ghim "loại|mã" (dạng cũ id G08 đổi sang); thử lần lượt mọi tài khoản cùng loại có mô
            # hình đó, mỗi tài khoản qua đủ kiểm giá, hạn mức; hết mới về mặc định (QĐ183)
            khoa = danhmuc_mohinh.chuan_khoa(mohinh_id, thumuc)
            loai, ma = danhmuc_mohinh.tach_khoa(khoa) if khoa else (None, None)
            lydo, het, da_thu, ly_tk, loi_ghim = "không còn dùng được", False, 0, [], {}
            for d in (x for x in ds if ma and dangnhap_goi.loai_nguon(x) == loai):
                dong = danhmuc_mohinh.dong_cua(d["id"], ma, thumuc)
                if not dong:
                    continue
                da_thu += 1
                kq = _thu({**d, "mohinh": dong}, cau, bo_qua, viecnen_id, thumuc, client, ghim=True)
                if isinstance(kq, dict):
                    return {"chu": kq["chu"], "nguon": d["ten"], "nguon_id": d["id"], "nhatky_ai_id": kq["nhatky_ai_id"],
                            "mohinh_id": dong["id"], "mohinh": ma, "mohinh_bao": kq.get("mohinh_bao"), "ghim_hong": None,
                            "ghim_khoa": khoa, "bo_qua": bo_qua, **_chay_bang(d, ds, nghi, thumuc, nghi_mh)}
                nghi[d["id"]], nghi_mh[d["id"]], da_ghim[d["id"]] = kq, ma, ma
                het = het or str(kq).startswith("hết hạn mức")
                ly_tk.append(_ly_do_nghi(d, ma, kq) if str(kq).startswith("hết hạn mức") else {})
                loi_ghim = {k: bo_qua[-1][k] for k in ("loi", "loi_ct") if kq == "lỗi" and bo_qua and k in bo_qua[-1]}
                lydo = kq
            if not da_thu:   # mô hình ngừng, cả nhóm đã gỡ hoặc ngừng (Đ1, Đ2)
                bo_qua.append({"nguon": "Mô hình đã chọn", "lydo": lydo})
            ghim_hong = {"khoa": khoa or mohinh_id, "ma": ma, "het_hanmuc": het, "lydo": "hết hạn mức" if het else lydo}
            if ly_tk and all(ly_tk):   # P3b: chỉ vì tài khoản đang tạm nghỉ
                ghim_hong.update(min(ly_tk, key=lambda x: x["den"] or "9"))
            elif not het and loi_ghim:   # Y36e: dòng vàng ghi đúng loại lỗi (ví dụ "chạm trần số lượt")
                ghim_hong.update(loi_ghim)
        for d in ds:
            if chi_nguon_id and d["id"] != chi_nguon_id:
                continue
            if nghi.get(d["id"]) == HET_CA_TK:   # Y36b: vừa bị từ chối cả tài khoản ở lượt ghim, không gọi lại
                continue
            if d["id"] in da_ghim and (d["mohinh"] or {}).get("ma") == da_ghim[d["id"]]:
                continue   # Y36g N9: mô hình mặc định trùng mô hình ghim vừa thử ở nguồn này (mọi loại lỗi): không gọi lại
            kq = _thu(d, cau, bo_qua, viecnen_id, thumuc, client)
            if isinstance(kq, dict):
                mh = d["mohinh"] or {}
                # Y36c: lượt thường (chưa ghim), mô hình mặc định của nguồn đứng trước hết hạn mức, đã sang hãng khác
                md_hong = None
                if not ghim_hong and het_dau and dangnhap_goi.loai_nguon(het_dau) != dangnhap_goi.loai_nguon(d):
                    ma0 = (het_dau["mohinh"] or {}).get("ma")
                    if loi_dau is not None:   # Y36f N6: nguồn đứng trước lỗi (không phải hạn mức) rồi sang hãng khác
                        md_hong = {"nguon_id": het_dau["id"], "het_hanmuc": False, **loi_dau}
                    else:
                        md_hong = {**mo_ta_het(het_dau["id"], ma0), "nguon_id": het_dau["id"], "het_hanmuc": True,
                                   **_ly_do_nghi(het_dau, ma0, nghi.get(het_dau["id"]))}   # P3b
                return {"chu": kq["chu"], "nguon": d["ten"], "nguon_id": d["id"], "nhatky_ai_id": kq["nhatky_ai_id"],
                        "mohinh_id": mh.get("id"), "mohinh": mh.get("ma"), "mohinh_bao": kq.get("mohinh_bao"),
                        "ghim_hong": ghim_hong, "md_hong": md_hong, "ghim_khoa": None, "bo_qua": bo_qua,
                        **_chay_bang(d, ds, nghi, thumuc, nghi_mh)}
            if het_dau is None and str(kq).startswith("hết hạn mức"):
                het_dau = d
            elif het_dau is None and kq in ("lỗi", "quá giờ"):   # Y36f N6
                het_dau = d
                b = bo_qua[-1] if bo_qua else {}
                loi_dau = {"loi": b.get("loi") or kq, "loi_ct": b.get("loi_ct") or ""}
            nghi.setdefault(d["id"], kq)
            nghi_mh.setdefault(d["id"], (d["mohinh"] or {}).get("ma"))
    return {"loi": "Chưa có nguồn AI nào dùng được" if not bo_qua else "Mọi nguồn AI đều chưa dùng được", "bo_qua": bo_qua,
            "ghim_hong": ghim_hong}


def tom_tat_thang(thumuc=None) -> dict:
    """Thẻ Khoá API màn 13 (QĐ122, bản vẽ "Tiền thật tháng 11"): tiền thật từ ngày 01 tháng này, giờ Việt Nam."""
    bay = datetime.now(MUIGIO_VN)
    tu = bay.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        r = cn.execute("SELECT count(*), coalesce(sum(sotien), 0) FROM nhatky_ai WHERE luc >= ?", (tu,)).fetchone()
    finally:
        cn.close()
    return {"thang": bay.month, "luot": r[0], "tien_that_usd": r[1] / TRIEU}


def tom_tat_tuan(thumuc=None) -> dict:
    """Số cho màn 13, 10: tiền thật (khoá API) và quy đổi tham khảo (gói) 07 ngày, tách riêng, không cộng lẫn."""
    tu = datetime.fromtimestamp(time.time() - 7 * 86400, MUIGIO_VN).isoformat(timespec="seconds")
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        r = cn.execute("SELECT count(*), coalesce(sum(sotien), 0), sum(sotien_thamkhao), sum(ketqua = 'xong')"
                       " FROM nhatky_ai WHERE luc >= ?", (tu,)).fetchone()
    finally:
        cn.close()
    return {"luot": r[0], "tien_that_usd": r[1] / TRIEU, "quydoi_thamkhao_usd": (r[2] / TRIEU) if r[2] is not None else None,
            "xong": r[3] or 0}
