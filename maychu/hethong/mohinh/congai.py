"""Cổng AI 03 nguồn (F34, ngày 06): gói Claude, gói ChatGPT, khoá API. Mỗi lần gọi ghi 01 dòng G04.

Chọn nguồn theo ưu tiên ở G06 (màn 13): bỏ nguồn ngừng, gói đang báo hết hạn mức (chưa tới giờ đặt lại),
tài khoản gói chưa đăng nhập, khoá API chưa đặt trần tiền hoặc tháng này đã chạm trần. Nguồn đầu báo hết hạn
mức thì chuyển sang nguồn kế tiếp và đánh dấu `da_het_luc`.

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
        ra["het"] = True
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


def ghi_han_muc(nguon_id: str, hm: dict, thumuc=None) -> None:
    if not hm:
        return
    bay = _bay_gio()
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
    """Gói đang báo hết: còn chặn tới giờ đặt lại của cửa sổ đang đầy."""
    bay = _bay_gio()
    for tl, dl in (("tyle_5gio", "datlai_5gio_luc"), ("tyle_tuan", "datlai_tuan_luc")):
        if (d[tl] or 0) >= 100 and (not d[dl] or d[dl] > bay):
            return True
    if not d["da_het_luc"]:
        return False
    if any(d[dl] and d[dl] <= bay for dl in ("datlai_5gio_luc", "datlai_tuan_luc")):
        return False
    if not (d["datlai_5gio_luc"] or d["datlai_tuan_luc"]):   # gói báo hết mà không kèm giờ đặt lại: thử lại sau 60 phút
        moc = datetime.fromtimestamp(time.time() - 3600, MUIGIO_VN).isoformat(timespec="seconds")
        return (d.get("do_luc") or "") > moc
    return True


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
        if _het_luc_dat_lai(d):
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


def _goi_claude(taikhoan: int, cau: str, mohinh: str | None) -> dict:
    lenh = [dangnhap_goi._cli("claude"), "-p", "--output-format", "stream-json", "--verbose", "--max-turns", "1"]
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
        loi = (kq or {}).get("result") or (r.stderr or r.stdout)[-300:]
        if hm.get("het") or any(x in str(loi).lower() for x in HET_HANMUC):
            raise HetHanMuc(str(loi)[:300], hm)
        raise RuntimeError(f"Claude không trả lời được: {str(loi)[:300]}")
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
    `ghim`: lượt thử mô hình anh ghim; hết hạn mức thì chỉ ghi % hạn mức hãng báo, không đánh dấu cả nguồn hết
    (hạn mức riêng của 01 mô hình, ví dụ Opus, không chặn mô hình mặc định cùng gói)."""
    ten = d["ten"] + (" (mô hình đã chọn)" if ghim else "")
    ok, lydo = dung_duoc(d, thumuc)
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
        ghi_han_muc(d["id"], e.hanmuc if ghim else {**e.hanmuc, "het": True}, thumuc)
        bo_qua.append({"nguon": ten, "lydo": f"hết hạn mức: {e}"[:200]})
        return "hết hạn mức"
    except subprocess.TimeoutExpired:
        _ghi_g04(d, None, "quagio", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
        bo_qua.append({"nguon": ten, "lydo": "quá giờ"})
        return "quá giờ"
    except Exception as e:  # noqa: BLE001 - lỗi 01 nguồn thì thử nguồn sau
        _ghi_g04(d, None, "loi", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
        bo_qua.append({"nguon": ten, "lydo": str(e)[:200]})
        return "lỗi"
    ms = int((time.monotonic() - t0) * 1000)
    ghi_han_muc(d["id"], kq.get("hanmuc") or {}, thumuc)
    kq["nhatky_ai_id"] = _ghi_g04(d, kq, "xong", ms, viecnen_id, thumuc)
    return kq


def _tk(d: dict) -> int | None:
    m = re.fullmatch(r"goi_(?:claude|chatgpt)_(\d\d)", d.get("ma") or "")
    return int(m.group(1)) if m else None


def _den_luc(nguon_id: str, thumuc=None) -> str | None:
    """Giờ tài khoản đang nghỉ dùng lại được: giờ đặt lại của cửa sổ đã đầy; không rõ cửa sổ thì giờ đặt lại sớm nhất."""
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


def _chay_bang(d: dict, ds: list, nghi: dict, thumuc=None) -> dict:
    """QĐ189: tài khoản thực chạy; chạy dự phòng (tài khoản cùng loại đứng trước đang hết hạn mức) thì kèm tài khoản đó và
    giờ dùng lại được. Chỉ để giao diện hiện khi rê chuột."""
    tk = _tk(d)
    if tk is None:
        return {"chay_tk": None, "du_phong": None}
    loai = dangnhap_goi.loai_nguon(d)
    truoc = next((x for x in ds if x["id"] != d["id"] and dangnhap_goi.loai_nguon(x) == loai and x["id"] in nghi
                  and str(nghi[x["id"]]).startswith("hết hạn mức")), None)
    return {"chay_tk": tk, "du_phong": {"tk": _tk(truoc), "den": _den_luc(truoc["id"], thumuc)} if truoc else None}


def goi(cau: str, *, viecnen_id=None, chi_nguon_id=None, loai_viec=None, mohinh_id=None, thumuc=None,
        client=None) -> dict:
    """Gọi AI 01 lần theo thứ tự ưu tiên (hoặc chỉ 01 nguồn khi bấm Gọi thử). Trả {chu, nguon, nguon_id,
    nhatky_ai_id, mohinh_id, mohinh, ghim_hong, bo_qua} hoặc {loi, bo_qua}. `mohinh_id` (G08): mô hình ghim, thử trước;
    không dùng được thì `ghim_hong` = {mohinh_id, ma, het_hanmuc, lydo} và gọi theo mặc định."""
    bo_qua, ghim_hong, nghi = [], None, {}
    sem = _cho_phep()
    with sem:
        ds = _nguon(thumuc, loai_viec)
        if mohinh_id and not chi_nguon_id:
            # 0.7.6 (QĐ187, Đ1, Đ5): ghim "loại|mã" (dạng cũ id G08 đổi sang); thử lần lượt mọi tài khoản cùng loại có mô
            # hình đó, mỗi tài khoản qua đủ kiểm giá, hạn mức; hết mới về mặc định (QĐ183)
            khoa = danhmuc_mohinh.chuan_khoa(mohinh_id, thumuc)
            loai, ma = danhmuc_mohinh.tach_khoa(khoa) if khoa else (None, None)
            lydo, het, da_thu = "không còn dùng được", False, 0
            for d in (x for x in ds if ma and dangnhap_goi.loai_nguon(x) == loai):
                dong = danhmuc_mohinh.dong_cua(d["id"], ma, thumuc)
                if not dong:
                    continue
                da_thu += 1
                kq = _thu({**d, "mohinh": dong}, cau, bo_qua, viecnen_id, thumuc, client, ghim=True)
                if isinstance(kq, dict):
                    return {"chu": kq["chu"], "nguon": d["ten"], "nguon_id": d["id"], "nhatky_ai_id": kq["nhatky_ai_id"],
                            "mohinh_id": dong["id"], "mohinh": ma, "mohinh_bao": kq.get("mohinh_bao"), "ghim_hong": None,
                            "ghim_khoa": khoa, "bo_qua": bo_qua, **_chay_bang(d, ds, nghi, thumuc)}
                nghi[d["id"]] = kq
                het = het or str(kq).startswith("hết hạn mức")
                lydo = kq
            if not da_thu:   # mô hình ngừng, cả nhóm đã gỡ hoặc ngừng (Đ1, Đ2)
                bo_qua.append({"nguon": "Mô hình đã chọn", "lydo": lydo})
            ghim_hong = {"khoa": khoa or mohinh_id, "ma": ma, "het_hanmuc": het, "lydo": "hết hạn mức" if het else lydo}
        for d in ds:
            if chi_nguon_id and d["id"] != chi_nguon_id:
                continue
            kq = _thu(d, cau, bo_qua, viecnen_id, thumuc, client)
            if isinstance(kq, dict):
                mh = d["mohinh"] or {}
                return {"chu": kq["chu"], "nguon": d["ten"], "nguon_id": d["id"], "nhatky_ai_id": kq["nhatky_ai_id"],
                        "mohinh_id": mh.get("id"), "mohinh": mh.get("ma"), "mohinh_bao": kq.get("mohinh_bao"),
                        "ghim_hong": ghim_hong, "ghim_khoa": None, "bo_qua": bo_qua, **_chay_bang(d, ds, nghi, thumuc)}
            nghi.setdefault(d["id"], kq)
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
