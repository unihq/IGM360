"""Danh sách mô hình theo nguồn AI cho ô chọn mô hình (QĐ178, QĐ184, Y31; bản vẽ Z10, Z10b).

Ghi vào G08 `mohinh_ai` (bảng có sẵn, 0 đổi cấu trúc): mỗi mô hình 01 dòng theo nguồn, chỉ thêm, không xoá.
- Gói Claude: bí danh của Claude Code CLI (haiku, sonnet, opus, fable; thấy trong CLI 2.1.330). CLI tự hiểu bí danh
  là bản mới nhất của họ đó, nên không phải hỏi mạng.
- Gói ChatGPT: đọc tệp `models_cache.json` Codex tự lưu trong thư mục đăng nhập (danh sách mô hình tài khoản dùng
  được, mục `visibility` = "list"). Chưa có tệp thì nhóm chỉ còn "mặc định của Codex" (không tự đặt bảng cố định).
- Khoá API: hỏi danh sách mô hình của hãng (Anthropic, OpenAI) bằng khoá trong Két khoá; nhớ 24 giờ; hỏi ở luồng
  phụ, trong lúc hỏi giao diện ghi "Đang tải danh sách mô hình…".
Mô hình mặc định theo loại việc (màn 13, nút "Đổi") ghi ở G08 `macdinh_cho_json` (danh sách mã loại việc).
"""
import json
import os
import re
import threading
import time
from pathlib import Path

import httpx

from maychu.dulieu import ketnoi, maso
from maychu.hethong.kekhoa import kho
from maychu.hethong.mohinh import dangnhap_goi

LOAI_VIEC = {"trochuyen": "Trò chuyện AI", "trichvanban": "Trích văn bản (đường D)",
             "dexuat": "Đề xuất ở mục Chờ duyệt", "baocaosang": "Viết báo cáo sáng"}
BI_DANH_CLAUDE = ("haiku", "sonnet", "opus", "fable")
NHO_GIAY = 24 * 3600
URL_DS = {"anthropic": "https://api.anthropic.com/v1/models", "openai": "https://api.openai.com/v1/models"}
_BO_OPENAI = ("audio", "tts", "embedding", "image", "realtime", "transcribe", "search", "moderation", "whisper", "dall-e")
_NHO: dict[str, float] = {}       # nguon_id → lúc nạp xong gần nhất
_DANG_TAI: set[str] = set()
_KHOA = threading.Lock()


# ---------------- Lấy danh sách từng loại nguồn ----------------
def _goi_cua(d: dict) -> tuple[str, int] | None:
    m = re.fullmatch(r"goi_(claude|chatgpt)_(\d\d)", d.get("ma") or "")
    return (m.group(1), int(m.group(2))) if m else None


def _ds_codex(taikhoan: int) -> list[str]:
    tm = dangnhap_goi.thu_muc("chatgpt", taikhoan)
    goc = tm or Path(os.environ.get("CODEX_HOME") or os.environ.get("IGM360_THUMUC_CHATGPT",
                                                                     dangnhap_goi.GOI["chatgpt"]["thumuc"]))
    try:
        ds = (json.loads((goc / "models_cache.json").read_text(encoding="utf-8")) or {}).get("models") or []
    except (OSError, ValueError, AttributeError):
        return []
    ds = [m for m in ds if isinstance(m, dict) and isinstance(m.get("slug"), str) and m.get("visibility", "list") == "list"]
    return [m["slug"] for m in sorted(ds, key=lambda m: m.get("priority") if isinstance(m.get("priority"), int) else 999)]


def _hang_khoa(d: dict) -> str | None:
    ma = d.get("ma") or ""
    return "anthropic" if ma.startswith("khoa_anthropic") else "openai" if ma.startswith("khoa_openai") else None


def _ds_khoa(d: dict, thumuc=None, client=None) -> list[str] | None:
    """None = chưa hỏi được (giữ danh sách cũ, lần sau hỏi lại)."""
    hang = _hang_khoa(d)
    ma_khoa = kho.tim(d["ma"], thumuc) if hang else None
    if not ma_khoa:
        return None
    khoa = kho.doc(ma_khoa, thumuc)
    dau = {"x-api-key": khoa, "anthropic-version": "2023-06-01"} if hang == "anthropic" else {"Authorization": f"Bearer {khoa}"}
    c = client or httpx.Client(timeout=20)
    try:
        r = c.get(URL_DS[hang], headers=dau, params={"limit": 1000} if hang == "anthropic" else None)
        if r.status_code != 200:
            return None
        ids = [x.get("id") for x in (r.json().get("data") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)]
    except (httpx.HTTPError, ValueError):
        return None
    finally:
        if client is None:
            c.close()
    if hang == "openai":
        ids = sorted(i for i in ids if (i.startswith("gpt") or (i[:1] == "o" and i[1:2].isdigit())) and not any(b in i for b in _BO_OPENAI))
    return ids


# ---------------- Ghi G08 ----------------
def _them(cn, nguon_id: str, ds: list[str]) -> int:
    co = {r[0] for r in cn.execute("SELECT ma_mohinh FROM mohinh_ai WHERE nguon_ai_id = ?", (nguon_id,))}
    moi = [m for m in ds if m not in co]
    for m in moi:
        cn.execute("INSERT INTO mohinh_ai (id, nguon_ai_id, ma_mohinh, trangthai) VALUES (?, ?, ?, 'dung')", (maso.tao(), nguon_id, m))
    return len(moi)


def nap(d: dict, thumuc=None, client=None) -> bool:
    """Nạp danh sách mô hình của 01 nguồn vào G08. Trả True khi lấy được danh sách (kể cả rỗng)."""
    g = _goi_cua(d)
    if g and g[0] == "claude":
        ds = list(BI_DANH_CLAUDE)
    elif g:
        ds = _ds_codex(g[1])
    elif d.get("loai") == "khoa_api":
        ds = _ds_khoa(d, thumuc, client)
        if ds is None:
            return False
    else:
        ds = []
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        _them(cn, d["id"], ds)
    finally:
        cn.close()
    _NHO[d["id"]] = time.time()
    return True


def _nap_nen(d: dict, thumuc=None) -> None:
    try:
        nap(d, thumuc)
    finally:
        with _KHOA:
            _DANG_TAI.discard(d["id"])
            _NHO.setdefault(d["id"], time.time() - NHO_GIAY + 600)   # hỏi không được: 10 phút sau hỏi lại


def _cu(d: dict) -> bool:
    return time.time() - _NHO.get(d["id"], 0) > NHO_GIAY


# ---------------- Đọc ----------------
def _da_ket_noi(d: dict, thumuc=None) -> bool:
    if d.get("trangthai") != "dung":
        return False
    if d.get("goi"):
        return bool(d.get("da_noi"))
    if d.get("loai") == "khoa_api":
        return bool(kho.tim(d["ma"], thumuc))
    return True


def macdinh(thumuc=None) -> dict:
    """{mã loại việc: id G08}."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        rows = cn.execute("SELECT id, macdinh_cho_json FROM mohinh_ai WHERE macdinh_cho_json IS NOT NULL"
                          " AND coalesce(trangthai, 'dung') = 'dung' ORDER BY rowid").fetchall()
    finally:
        cn.close()
    kq = {}
    for i, j in rows:
        try:
            for lv in json.loads(j) or []:
                kq.setdefault(lv, i)
        except (ValueError, TypeError):
            continue
    return kq


def danh_sach(thumuc=None, nap_nen: bool = True) -> dict:
    """Nhóm theo nguồn đã kết nối (thứ tự ưu tiên), mỗi nhóm các mô hình G08 đang dùng. Nhóm khoá API chưa có
    danh sách hoặc đã cũ hơn 24 giờ thì hỏi hãng ở luồng phụ và ghi `dang_tai`."""
    nguon = [d for d in dangnhap_goi.danh_sach(thumuc) if _da_ket_noi(d, thumuc)]
    for d in nguon:
        if not _cu(d):
            continue
        if d.get("loai") == "khoa_api":
            with _KHOA:
                if d["id"] in _DANG_TAI or not nap_nen:
                    continue
                _DANG_TAI.add(d["id"])
            threading.Thread(target=_nap_nen, args=(d, thumuc), daemon=True).start()
        else:
            nap(d, thumuc)
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        nhom = []
        for i, d in enumerate(nguon):
            ds = [{"id": r[0], "ma": r[1]} for r in cn.execute(
                "SELECT id, ma_mohinh FROM mohinh_ai WHERE nguon_ai_id = ? AND coalesce(trangthai, 'dung') = 'dung'"
                " AND ma_mohinh IS NOT NULL ORDER BY rowid", (d["id"],))]
            nhom.append({"nguon_id": d["id"], "ma": d["ma"], "ten": d["ten"], "loai": d["loai"], "hang": d.get("hang"),
                         "goi": d.get("goi"), "taikhoan": d.get("taikhoan"), "chinh": i == 0, "dang_tai": d["id"] in _DANG_TAI and not ds, "mohinh": ds})
    finally:
        cn.close()
    return {"nhom": nhom, "macdinh": macdinh(thumuc), "loai_viec": LOAI_VIEC}


def mot(mohinh_id: str, thumuc=None) -> dict | None:
    """01 dòng G08 đang dùng: {id, nguon_ai_id, ma, gia_vao, gia_ra, tien_ma}; ngừng hoặc không có thì None."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        r = cn.execute("SELECT id, nguon_ai_id, ma_mohinh, gia_vao, gia_ra, tien_ma FROM mohinh_ai WHERE id = ?"
                       " AND coalesce(trangthai, 'dung') = 'dung'", (mohinh_id,)).fetchone()
    finally:
        cn.close()
    return dict(zip(("id", "nguon_ai_id", "ma", "gia_vao", "gia_ra", "tien_ma"), r)) if r else None


def dat_macdinh(loai_viec: str, mohinh_id: str | None, thumuc=None) -> dict:
    """Màn 13 nút "Đổi": 01 loại việc chỉ có 01 mô hình mặc định; `mohinh_id` None = về mặc định của nguồn."""
    if loai_viec not in LOAI_VIEC:
        raise ValueError("Loại việc không có")
    if mohinh_id is not None and not mot(mohinh_id, thumuc):
        raise ValueError("Mô hình không còn dùng được")
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        for i, j in cn.execute("SELECT id, macdinh_cho_json FROM mohinh_ai WHERE macdinh_cho_json IS NOT NULL").fetchall():
            try:
                ds = [x for x in (json.loads(j) or []) if x != loai_viec]
            except (ValueError, TypeError):
                ds = []
            cn.execute("UPDATE mohinh_ai SET macdinh_cho_json = ? WHERE id = ?", (json.dumps(ds) if ds else None, i))
        if mohinh_id is not None:
            j = cn.execute("SELECT macdinh_cho_json FROM mohinh_ai WHERE id = ?", (mohinh_id,)).fetchone()[0]
            try:
                ds = (json.loads(j) or []) if j else []
            except (ValueError, TypeError):
                ds = []
            cn.execute("UPDATE mohinh_ai SET macdinh_cho_json = ? WHERE id = ?", (json.dumps([*ds, loai_viec]), mohinh_id))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return macdinh(thumuc)
