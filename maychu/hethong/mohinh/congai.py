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
from maychu.hethong.mohinh import dangnhap_goi

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
def _nguon(thumuc=None) -> list[dict]:
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cot = ["id", "ma", "ten", "loai", "uutien", "tran_tien_thang", "tyle_5gio", "tyle_tuan", "datlai_5gio_luc",
               "datlai_tuan_luc", "do_luc", "da_het_luc"]
        ds = [dict(zip(cot, r)) for r in cn.execute(f"SELECT {', '.join(cot)} FROM nguon_ai WHERE trangthai = 'dung'"
                                                     " ORDER BY uutien, ma")]
        for d in ds:
            m = cn.execute("SELECT id, ma_mohinh, gia_vao, gia_ra, tien_ma FROM mohinh_ai WHERE nguon_ai_id = ?"
                           " AND coalesce(trangthai, 'dung') = 'dung' ORDER BY rowid LIMIT 1", (d["id"],)).fetchone()
            d["mohinh"] = dict(zip(("id", "ma", "gia_vao", "gia_ra", "tien_ma"), m)) if m else None
        return ds
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
        return False, "chưa đặt trần tiền"
    if not kho.tim(d["ma"], thumuc):
        return False, "chưa có khoá"
    if not d["mohinh"] or d["mohinh"]["gia_vao"] is None or d["mohinh"]["gia_ra"] is None:
        return False, "chưa có giá mô hình"
    if tien_thang(d["id"], thumuc) >= d["tran_tien_thang"] * TRIEU:
        return False, "chạm trần tiền tháng"
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
    kq, hm = None, {}
    for dong in r.stdout.splitlines():
        try:
            o = json.loads(dong)
        except ValueError:
            continue
        if o.get("type") == "rate_limit_event":
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
            "sotien_thamkhao": round(float(tk) * TRIEU) if tk is not None else None, "tien_ma": "USD", "hanmuc": hm}


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
            "hanmuc": hm}


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
    return {"chu": chu, "vao": vao, "ra": ra, "sotien": tien, "sotien_thamkhao": None, "tien_ma": m["tien_ma"] or "USD",
            "hanmuc": {}}


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


def goi(cau: str, *, viecnen_id=None, chi_nguon_id=None, thumuc=None, client=None) -> dict:
    """Gọi AI 01 lần theo thứ tự ưu tiên (hoặc chỉ 01 nguồn khi bấm Gọi thử). Trả {chu, nguon, nhatky_ai_id, bo_qua}
    hoặc {loi, bo_qua}."""
    bo_qua = []
    sem = _cho_phep()
    with sem:
        for d in _nguon(thumuc):
            if chi_nguon_id and d["id"] != chi_nguon_id:
                continue
            ok, lydo = dung_duoc(d, thumuc)
            if not ok:
                bo_qua.append({"nguon": d["ten"], "lydo": lydo})
                continue
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
                ghi_han_muc(d["id"], {**e.hanmuc, "het": True}, thumuc)
                bo_qua.append({"nguon": d["ten"], "lydo": f"hết hạn mức: {e}"[:200]})
                continue
            except subprocess.TimeoutExpired:
                _ghi_g04(d, None, "quagio", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
                bo_qua.append({"nguon": d["ten"], "lydo": "quá giờ"})
                continue
            except Exception as e:  # noqa: BLE001 - lỗi 01 nguồn thì thử nguồn sau
                _ghi_g04(d, None, "loi", int((time.monotonic() - t0) * 1000), viecnen_id, thumuc)
                bo_qua.append({"nguon": d["ten"], "lydo": str(e)[:200]})
                continue
            ms = int((time.monotonic() - t0) * 1000)
            ghi_han_muc(d["id"], kq.get("hanmuc") or {}, thumuc)
            ma = _ghi_g04(d, kq, "xong", ms, viecnen_id, thumuc)
            return {"chu": kq["chu"], "nguon": d["ten"], "nguon_id": d["id"], "nhatky_ai_id": ma, "bo_qua": bo_qua}
    return {"loi": "Chưa có nguồn AI nào dùng được" if not bo_qua else "Mọi nguồn AI đều chưa dùng được", "bo_qua": bo_qua}


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
