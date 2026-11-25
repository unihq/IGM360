"""Danh sách mô hình theo nguồn AI cho ô chọn mô hình (QĐ178, QĐ184, Y31; bản vẽ Z10, Z10b).

Ghi vào G08 `mohinh_ai` (bảng có sẵn, 0 đổi cấu trúc): mỗi mô hình 01 dòng theo nguồn, chỉ thêm, không xóa.
- Gói Claude: bí danh của Claude Code CLI (haiku, sonnet, opus, fable; thấy trong CLI 2.1.330). CLI tự hiểu bí danh
  là bản mới nhất của họ đó, nên không phải hỏi mạng.
- Gói ChatGPT: đọc tệp `models_cache.json` Codex tự lưu trong thư mục đăng nhập (danh sách mô hình tài khoản dùng
  được, mục `visibility` = "list"). Chưa có tệp thì nhóm chỉ còn "mặc định của Codex" (không tự đặt bảng cố định).
- Khóa API: hỏi danh sách mô hình của hãng (Anthropic, OpenAI) bằng khóa trong Két khóa; nhớ 24 giờ; hỏi ở luồng
  phụ, trong lúc hỏi giao diện ghi "Đang tải danh sách mô hình…".
Mô hình mặc định theo loại việc (màn 13, nút "Đổi") ghi ở G08 `macdinh_cho_json` (danh sách mã loại việc).
"Mặc định của nguồn" (Z10c, S6): 01 dòng G08 của nguồn có `ma_mohinh` trống, chỉ để giữ nguồn mặc định của loại việc;
không hiện trong danh sách mô hình; cổng AI gặp dòng này thì dùng mô hình mặc định của nguồn đó.
Bản 0.7.6 (QĐ187, PTD-08 Đ5, Đ6, CDA K-MH5): chọn theo mô hình, không chia tài khoản. Danh sách gộp theo loại nguồn
(`dangnhap_goi.loai_nguon`); mỗi mô hình có khóa "mã loại nguồn|mã mô hình" (`khoa_mh`, 01 hàm duy nhất; "loại|" =
mặc định của loại nguồn). Ghim, mặc định dùng khóa này; dòng G08 mang dấu mặc định chỉ là đại diện của loại + mã.
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
             "dexuat": "Đề xuất ở mục Chờ duyệt", "baocaosang": "Viết báo cáo sáng",
             "viecnen_chung": "Việc nền chung"}   # QĐ192, K-VN Đ3: mã tránh trùng bảng G02 `viecnen`; tên QĐ194 (từ điển dòng 63)
# Loại việc chạy nền (không phải trò chuyện): chưa đặt riêng thì theo "Việc nền chung"; không đọc ghim (K-VN Đ2)
VIEC_NEN = ("trichvanban", "dexuat", "baocaosang")
VIEC_NEN_CHUNG = "viecnen_chung"
BI_DANH_CLAUDE = ("haiku", "sonnet", "opus", "fable")
# Y46 phần D (QĐ265, PTD-14 mục 8.1): bản Claude Code tối thiểu theo tài liệu Anthropic code.claude.com/docs/en/model-config
# (đọc 24/11/2026). CHỈ dùng dự phòng khi tệp danh mục để trống trường `min_claude_code_version`.
BAN_TOI_THIEU_TAILIEU = {"claude-opus-5-5": "2.1.280", "claude-sonnet-5-5": "2.1.284", "claude-haiku-5-5": "2.1.293",
                         "claude-fable-5-2": "2.1.321"}
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


def _thumuc_claude(taikhoan: int) -> Path:
    tm = dangnhap_goi.thu_muc("claude", taikhoan)
    return tm or Path(os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("IGM360_THUMUC_CLAUDE",
                                                                            dangnhap_goi.GOI["claude"]["thumuc"]))


def _danhmuc_claude(taikhoan: int) -> dict[str, str | None]:
    """Y46 phần D (QĐ265): {mã mô hình: bản Claude Code tối thiểu hoặc None} đọc từ tệp danh mục Claude Code tự tải theo
    tài khoản (`<thư mục đăng nhập>/cache/model-catalog/*.json`, chỉ có tên mô hình, không có khóa). Ưu tiên
    tệp của Claude Code dòng lệnh (`surface` = "cc"); không có thì dùng tệp khác. Chưa có tệp: {} (chỉ còn 04 bí danh)."""
    cc: dict[str, str | None] = {}
    khac: dict[str, str | None] = {}
    try:
        tep = sorted((_thumuc_claude(taikhoan) / "cache" / "model-catalog").glob("*.json"))
    except OSError:
        return {}
    for p in tep:
        try:
            c = (json.loads(p.read_text(encoding="utf-8")) or {}).get("catalog")
            ms = (c.get("config") or {}).get("models")
        except (OSError, ValueError, AttributeError):
            continue
        if not isinstance(ms, list):
            continue
        dich = cc if c.get("surface") == "cc" else khac
        for m in ms:
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]:
                v = m.get("min_claude_code_version")
                if not dich.get(m["id"]):
                    dich[m["id"]] = v if isinstance(v, str) and v else None
    return cc or khac


def _danh_dau_claude(nhom: dict, nguon: list[dict], thumuc=None) -> None:
    """QĐ265 (Z20 dòng 16, 17): mô hình cần Claude Code cao hơn bản đang dùng → `can_nang` (dòng xám, không chọn được);
    vừa dùng được nhờ lần nâng gần nhất → `moi` (nhãn "mới"). Trường trống mà tài liệu cũng không ghi: dùng được."""
    toi_thieu: dict[str, str | None] = {}
    for d in nguon:
        g = _goi_cua(d)
        if g and g[0] == "claude":
            for k, v in _danhmuc_claude(g[1]).items():
                if not toi_thieu.get(k):
                    toi_thieu[k] = v
    from maychu.hethong.mohinh import nangcli
    ban = None
    for k, nh in nhom.items():
        if k != "goi_claude":   # mã loại nguồn gói Claude (dangnhap_goi.loai_nguon)
            continue
        for m in nh["mohinh"]:
            can = toi_thieu.get(m["ma"]) or BAN_TOI_THIEU_TAILIEU.get(m["ma"])
            if not can:
                continue
            if ban is None:
                ban = nangcli.ban_cli("claude", thumuc)   # hỏi số bản 01 lần, chỉ khi có mô hình ghi bản tối thiểu
            dang, truoc = ban
            if not dang:
                continue
            if nangcli._khoa_so(can) > nangcli._khoa_so(dang):
                m.update(can_nang=can, ban_dang=dang)
            elif truoc and nangcli._khoa_so(truoc) < nangcli._khoa_so(can):
                m["moi"] = True


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
    if g and g[0] == "claude":   # 04 bí danh + danh mục theo tài khoản (phần D, QĐ265); G08 chỉ thêm dòng
        ds = list(BI_DANH_CLAUDE) + [m for m in _danhmuc_claude(g[1]) if m not in BI_DANH_CLAUDE]
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


def khoa_mh(loai: str, ma: str | None) -> str:
    """Khóa "mã loại nguồn|mã mô hình" (PTD-08 mục 0.1): giao diện chỉ dùng lại, không tự ghép; bản 4 chép nguyên văn."""
    return f"{loai}|{ma or ''}"


def tach_khoa(khoa: str) -> tuple[str, str | None]:
    loai, _, ma = (khoa or "").partition("|")
    return loai, (ma or None)


def _nguon_dung(cn) -> list[dict]:
    cot = ("id", "ma", "loai", "uutien")
    return dangnhap_goi.thu_tu([dict(zip(cot, r)) for r in cn.execute(
        "SELECT id, ma, loai, uutien FROM nguon_ai WHERE trangthai = 'dung'")])


def dong_cua(nguon_id: str, ma: str, thumuc=None) -> dict | None:
    """Dòng G08 đang dùng của 01 tài khoản theo mã mô hình."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        r = cn.execute("SELECT id, ma_mohinh, gia_vao, gia_ra, tien_ma FROM mohinh_ai WHERE nguon_ai_id = ? AND ma_mohinh = ?"
                       " AND coalesce(trangthai, 'dung') = 'dung' ORDER BY rowid LIMIT 1", (nguon_id, ma)).fetchone()
    finally:
        cn.close()
    return dict(zip(("id", "ma", "gia_vao", "gia_ra", "tien_ma"), r)) if r else None


def chuan_khoa(gia_tri: str | None, thumuc=None) -> str | None:
    """Ghim gửi lên: khóa "loại|mã" giữ nguyên; dạng cũ (id G08 của 0.7.5) đổi sang khóa; dòng trống mã hoặc không có thì None."""
    if not gia_tri:
        return None
    if "|" in gia_tri:
        return gia_tri if tach_khoa(gia_tri)[1] else None
    m = mot(gia_tri, thumuc)
    if not m or not m["ma"]:
        return None
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        r = cn.execute("SELECT ma FROM nguon_ai WHERE id = ?", (m["nguon_ai_id"],)).fetchone()
    finally:
        cn.close()
    return khoa_mh(dangnhap_goi.loai_nguon({"ma": r[0]}), m["ma"]) if r else None


def _dong_macdinh(cn, nguon_id: str) -> str:
    """Dòng "mặc định của nguồn" (ma_mohinh trống) của 01 nguồn; chưa có thì thêm."""
    r = cn.execute("SELECT id FROM mohinh_ai WHERE nguon_ai_id = ? AND ma_mohinh IS NULL ORDER BY rowid LIMIT 1", (nguon_id,)).fetchone()
    if r:
        cn.execute("UPDATE mohinh_ai SET trangthai = 'dung' WHERE id = ?", (r[0],))
        return r[0]
    mid = maso.tao()
    cn.execute("INSERT INTO mohinh_ai (id, nguon_ai_id, ma_mohinh, trangthai) VALUES (?, ?, NULL, 'dung')", (mid, nguon_id))
    return mid


def macdinh_chi_tiet(thumuc=None) -> dict:
    """{mã loại việc: {khoa, nhom, ma, mat, mohinh_id, nguon_id}} (Đ6): đọc theo loại nguồn + mã mô hình, không theo tài
    khoản đang giữ dấu; `ma` trống = mặc định của loại nguồn; `mat` = cả nhóm không còn tài khoản nào đang dùng (về nguồn
    ưu tiên 1, giao diện báo)."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        ma_nguon = dict(cn.execute("SELECT id, ma FROM nguon_ai"))
        con = {dangnhap_goi.loai_nguon(d) for d in _nguon_dung(cn)}
    finally:
        cn.close()
    kq = {}
    for lv, mid in macdinh(thumuc).items():
        m = mot(mid, thumuc)
        if m and m["nguon_ai_id"] in ma_nguon:
            k = dangnhap_goi.loai_nguon({"ma": ma_nguon[m["nguon_ai_id"]]})
            kq[lv] = {"khoa": khoa_mh(k, m["ma"]), "nhom": k, "ma": m["ma"], "mat": k not in con,
                      "mohinh_id": m["id"], "nguon_id": m["nguon_ai_id"]}
    return kq


def la_viec_nen(loai_viec: str | None) -> bool:
    return loai_viec in VIEC_NEN or loai_viec == VIEC_NEN_CHUNG


def macdinh_khoa(loai_viec: str, thumuc=None) -> tuple[str, str | None] | None:
    """(loại nguồn, mã mô hình hoặc None) mặc định của 01 loại việc. Thứ tự tìm 03 bậc, chỉ ở hàm này (K-VN Đ1, thiết kế G08
    quy tắc 6): (a) loại việc đặt riêng; (b) "Việc nền chung", chỉ cho việc nền, trò chuyện bỏ qua; (c) không có
    thì None: cổng AI theo thứ tự nguồn Đ5. Bậc nào cả nhóm nguồn đã mất (`mat`) thì xuống bậc sau."""
    ct = macdinh_chi_tiet(thumuc)
    bac = [loai_viec] + ([VIEC_NEN_CHUNG] if loai_viec in VIEC_NEN else [])
    for lv in bac:
        c = ct.get(lv)
        if c and not c["mat"]:
            return c["nhom"], c["ma"]
    return None


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
    """Nhóm theo nguồn đã kết nối (thứ tự ưu tiên), mỗi nhóm các mô hình G08 đang dùng. Nhóm khóa API chưa có
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
        nhom: dict[str, dict] = {}   # QĐ187: 01 nhóm mỗi loại nguồn, gộp mô hình mọi tài khoản cùng loại (theo thứ tự Đ5)
        for d in nguon:
            k = dangnhap_goi.loai_nguon(d)
            g = nhom.setdefault(k, {"nhom": k, "khoa_md": khoa_mh(k, None), "nguon_id": d["id"], "nguon_ids": [], "ma": d["ma"],
                                    "ten": d["ten"], "loai": d["loai"], "hang": d.get("hang"), "goi": d.get("goi"),
                                    "chinh": not nhom, "dang_tai": False, "mohinh": [], "_ma": {}})
            g["nguon_ids"].append(d["id"])
            for i, ma in cn.execute("SELECT id, ma_mohinh FROM mohinh_ai WHERE nguon_ai_id = ? AND coalesce(trangthai, 'dung') = 'dung'"
                                    " AND ma_mohinh IS NOT NULL ORDER BY rowid", (d["id"],)):
                if ma in g["_ma"]:
                    g["_ma"][ma]["ids"].append(i)
                else:
                    g["_ma"][ma] = {"khoa": khoa_mh(k, ma), "ma": ma, "id": i, "ids": [i]}
                    g["mohinh"].append(g["_ma"][ma])
            g["dang_tai"] = g["dang_tai"] or d["id"] in _DANG_TAI
        _danh_dau_claude(nhom, nguon, thumuc)
        nhom = [{**{k: v for k, v in g.items() if k != "_ma"}, "dang_tai": g["dang_tai"] and not g["mohinh"]} for g in nhom.values()]
    finally:
        cn.close()
    return {"nhom": nhom, "macdinh": macdinh(thumuc), "macdinh_ct": macdinh_chi_tiet(thumuc), "loai_viec": LOAI_VIEC}


def mot(mohinh_id: str, thumuc=None) -> dict | None:
    """01 dòng G08 đang dùng: {id, nguon_ai_id, ma, gia_vao, gia_ra, tien_ma}; ngừng hoặc không có thì None."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        r = cn.execute("SELECT id, nguon_ai_id, ma_mohinh, gia_vao, gia_ra, tien_ma FROM mohinh_ai WHERE id = ?"
                       " AND coalesce(trangthai, 'dung') = 'dung'", (mohinh_id,)).fetchone()
    finally:
        cn.close()
    return dict(zip(("id", "nguon_ai_id", "ma", "gia_vao", "gia_ra", "tien_ma"), r)) if r else None


def dat_macdinh(loai_viec: str, mohinh_id: str | None = None, thumuc=None, nguon_id: str | None = None,
                khoa: str | None = None) -> dict:
    """Màn 13 nút "Đổi": 01 loại việc chỉ có 01 mô hình mặc định. `khoa` "loại|mã" (0.7.6): dấu đặt lên dòng G08 của
    tài khoản đầu tiên cùng loại có mô hình đó; "loại|" = mặc định của loại nguồn. Dạng cũ: `mohinh_id`, hoặc trống +
    `nguon_id` (S6); tất cả trống: bỏ đặt (theo nguồn ưu tiên 1)."""
    if loai_viec not in LOAI_VIEC:
        raise ValueError("Loại việc không có")
    if khoa:
        loai, ma = tach_khoa(khoa)
        cn = ketnoi.mo("Viecnen", thumuc)
        try:
            cung = [d for d in _nguon_dung(cn) if dangnhap_goi.loai_nguon(d) == loai]
        finally:
            cn.close()
        if not cung:
            raise ValueError("Nguồn không còn dùng được")
        if ma:
            dong = next((r for r in (dong_cua(d["id"], ma, thumuc) for d in cung) if r), None)
            if not dong:
                raise ValueError("Mô hình không còn dùng được")
            mohinh_id = dong["id"]
        else:
            nguon_id = cung[0]["id"]
    if mohinh_id is not None and not mot(mohinh_id, thumuc):
        raise ValueError("Mô hình không còn dùng được")
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        if mohinh_id is None and nguon_id is not None:
            if not cn.execute("SELECT 1 FROM nguon_ai WHERE id = ? AND trangthai = 'dung'", (nguon_id,)).fetchone():
                raise ValueError("Nguồn không còn dùng được")
            mohinh_id = _dong_macdinh(cn, nguon_id)
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
        if cn.in_transaction:
            cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    return macdinh(thumuc)
