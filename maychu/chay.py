"""Lệnh chạy của ảnh (0.7.9 lớp 3, QĐ213, QĐ215; sửa Y38c R1, R3): chọn bản chạy rồi chạy uvicorn.

- Bình thường: chạy bản trong ảnh (`/app/maychu`), thay tiến trình (exec) như trước.
- Anh đã bấm "Quay về bản trước": tệp trạng thái `capnhat_trangthai.json` có mục `chay_ban_truoc` ghi đúng bản ảnh này
  và đúng bản trước để sẵn ở `/app/ban_truoc` → chạy mã ở đó.
  * R1: mục có `tra_du_lieu` thì trả 07 tệp từ bản chụp TRƯỚC khi chạy (chưa tiến trình nào mở tệp): chép từng tệp ra
    tệp tạm, kiểm `quick_check`, đủ cả mới thay; lỗi 01 tệp thì không thay tệp nào, bỏ cờ, chạy bản mới.
  * R3: bản trước chạy dưới sự canh của lệnh này: chưa lên được `/suckhoe` mà đã dừng thì đếm 01 lần hỏng; hỏng tới
    SO_LAN_HONG lần thì bỏ cờ, chạy lại bản mới (anh vẫn vào được giao diện). Lên được thì xoá số đếm.
- Ảnh mới hơn về (bấm Cập nhật ngay lên bản sửa): mục đó ghi bản ảnh cũ → bỏ mục, chạy bản mới.
Chỉ dùng thư viện chuẩn: bản trước chạy trên đúng thư viện của ảnh này. Lỗi ghi vào `quayve_loi` để bản mới ghi F04.
"""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
CONG = os.environ.get("IGM360_CONG", "8360")
LENH = ["-m", "uvicorn", "maychu.khoidong:app", "--host", "0.0.0.0", "--port", CONG, "--proxy-headers"]
TEN_TEP = "capnhat_trangthai.json"
SO_LAN_HONG = 3          # bản trước khởi động hỏng 03 lần liền thì về bản mới
CHO_LEN_GIAY = 120       # chờ bản trước trả lời /suckhoe tối đa 02 phút mỗi lần
MUIGIO_VN = timezone(timedelta(hours=7))


def _so(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _bay() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _doc(tep: Path) -> dict:
    try:
        d = json.loads(tep.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi(tep: Path, d: dict) -> None:
    tam = tep.with_name(f"{tep.name}.{os.getpid()}.chay.tam")
    try:
        fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tam, tep)
    except OSError:
        tam.unlink(missing_ok=True)


def _bo_co(tep: Path, tt: dict, loi: str | None = None, **them) -> None:
    """`them`: kieu ("tra" | "khoidong"), ban_truoc, ban_anh, so_lan, da_tra (giờ dữ liệu đã trả về) để bản mới ghi câu A4–A7."""
    tt.pop("chay_ban_truoc", None)
    if loi:
        tt["quayve_loi"] = {"chu": loi, "luc": _bay(), **them}
    _ghi(tep, tt)


DUOI = ("", "-wal", "-shm")


def _ten(dl: Path, t: str, d: str = "") -> Path:
    return dl / f"{t}.sqlite3{d}"


def _doi_ve_cu(dl: Path, tep: list) -> None:
    """V2: đổi các tệp `.cu` (dữ liệu trước lúc thay) về chỗ cũ; tệp đã thay bị ghi đè lại bằng tệp cũ."""
    for t in tep:
        for d in DUOI:
            cu = Path(str(_ten(dl, t, d)) + ".cu")
            if cu.exists():
                os.replace(cu, _ten(dl, t, d))
            elif d and _ten(dl, t, d).exists() and Path(str(_ten(dl, t)) + ".cu").exists():
                _ten(dl, t, d).unlink()


def _xoa_cu(dl: Path, tep: list) -> None:
    for t in tep:
        for d in DUOI:
            Path(str(_ten(dl, t, d)) + ".cu").unlink(missing_ok=True)


def _tep_tra(tra: dict) -> list:
    return [t for t in tra.get("tep", []) if isinstance(t, str) and t.isidentifier()]


def tra_du_lieu(dl: Path, tra: dict, ghi_buoc=lambda b: None) -> str | None:
    """R1, V2: trả các tệp ghi trong `tra` từ thư mục chụp. Bước 1: chép ra tệp tạm, `quick_check`, đủ cả mới sang bước 2.
    Bước 2 (ghi `buoc` = "thay" trước): tệp đang có (kèm -wal, -shm) đổi tên sang `.cu`, tệp tạm vào chỗ; lỗi ở tệp nào
    thì đổi các `.cu` về hết (07 tệp như trước lúc trả). Xong đủ thì ghi `buoc` = "xong_thay" rồi mới xoá `.cu`.
    Trả None khi xong; chuỗi lỗi khi không trả (dữ liệu giữ nguyên)."""
    noi = dl / "saoluu" / str(tra.get("thumuc", ""))
    tep = _tep_tra(tra)
    if not tep or not noi.is_dir():
        return "không có bản chụp để trả dữ liệu"
    tam = {}
    try:
        for t in tep:
            nguon = sqlite3.connect(noi / f"{t}.sqlite3")
            dich_duong = dl / f"{t}.sqlite3.trave.tam"
            dich_duong.unlink(missing_ok=True)
            tam[t] = dich_duong   # ghi tên trước để lỗi giữa chừng cũng dọn được tệp tạm này
            dich = sqlite3.connect(dich_duong)
            try:
                nguon.backup(dich)
                if dich.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError(f"{t}: bản chụp không đạt kiểm tra")
            finally:
                dich.close()
                nguon.close()
            os.chmod(dich_duong, 0o600)
    except (OSError, sqlite3.Error) as e:
        for p in tam.values():
            p.unlink(missing_ok=True)
        return f"không trả được dữ liệu: {type(e).__name__}"
    ghi_buoc("thay")
    try:
        for t, p in tam.items():
            for d in DUOI:
                if _ten(dl, t, d).exists():
                    os.replace(_ten(dl, t, d), Path(str(_ten(dl, t, d)) + ".cu"))
            os.replace(p, _ten(dl, t))
    except OSError as e:
        _doi_ve_cu(dl, tep)   # lỗi ở đây thì để lỗi lan ra: cờ còn `buoc` = "thay", lần khởi động sau đổi về tiếp
        for p in tam.values():
            p.unlink(missing_ok=True)
        ghi_buoc(None)
        return f"không trả được dữ liệu: {type(e).__name__}"
    ghi_buoc("xong_thay")
    _xoa_cu(dl, tep)
    return None


# ---- QĐ237 (G1, cách C): quay về có trả dữ liệu vẫn giữ nhật ký ghi sau giờ chụp ----
# 05 sổ chỉ ghi thêm ở Nhatky + M01 loại 'saoluu' (Hotho). Lọc theo `id` chưa có trong bản chụp (bảng chỉ ghi thêm).
TEP_GIU = "nhatky_giu.tam.sqlite3"
BANG_GIU = ("nhatky_thaotac", "nhatky_ai", "nhatky_noihayim", "saoluu", "theodoi_maychu")   # F04, G04, H05, N01, N02


def _co_bang(cn, sch: str, bang: str) -> bool:
    return bool(cn.execute(f"SELECT 1 FROM {sch}.sqlite_master WHERE type = 'table' AND name = ?", (bang,)).fetchone())


def _chep_giu(dl: Path, noi: Path) -> int:
    """Bước 1 (trước khi đổi tên tệp, để không mất phần WAL): chép dòng mới so với bản chụp ra tệp tạm (quyền 600).
    M01: chỉ `loai` = 'saoluu' còn tệp trên đĩa; không chép `filegoc`, `goi_banghigoc` (trỏ B02, B03 sẽ bị trả). Trả số dòng."""
    giu = dl / TEP_GIU
    giu.unlink(missing_ok=True)
    so = 0
    for ten, cac_bang, loc in (("Nhatky", BANG_GIU, ""), ("Hotho", ("cho_day_drive",), " AND loai = 'saoluu'")):
        if not (dl / f"{ten}.sqlite3").exists() or not (noi / f"{ten}.sqlite3").exists():
            continue
        cn = sqlite3.connect(dl / f"{ten}.sqlite3", isolation_level=None)
        try:
            cn.execute("ATTACH DATABASE ? AS chup", (str(noi / f"{ten}.sqlite3"),))
            cn.execute("ATTACH DATABASE ? AS giu", (str(giu),))
            for bang in cac_bang:
                if _co_bang(cn, "main", bang) and _co_bang(cn, "chup", bang):
                    cn.execute(f"CREATE TABLE giu.{bang} AS SELECT * FROM main.{bang}"
                               f" WHERE id NOT IN (SELECT id FROM chup.{bang}){loc}")
                    so += cn.execute(f"SELECT count(*) FROM giu.{bang}").fetchone()[0]
            if _co_bang(cn, "giu", "cho_day_drive"):
                for i, duong in cn.execute("SELECT id, duongdan_tam FROM giu.cho_day_drive").fetchall():
                    if not duong or not Path(duong).exists():
                        cn.execute("DELETE FROM giu.cho_day_drive WHERE id = ?", (i,))
                        so -= 1
        finally:
            cn.close()
    if giu.exists():
        os.chmod(giu, 0o600)
    return so


def _noi_bang(cn, bang: str, ban: int) -> None:
    cot = [r[1] for r in cn.execute(f"PRAGMA main.table_info({bang})")]
    cot = [c for c in cot if c in {r[1] for r in cn.execute(f"PRAGMA giu.table_info({bang})")}]
    lay = list(cot)
    if bang == "saoluu" and ban < 4:   # Nhatky trả về lược đồ 3: CHECK bản 3 không nhận 'truoc_capnhat' → 'hangngay' + "dip"
        lay = ["CASE WHEN loai = 'truoc_capnhat' THEN 'hangngay' ELSE loai END" if c == "loai" else
               "CASE WHEN loai = 'truoc_capnhat' AND json_valid(ketqua_tungbuoc_json)"
               " AND json_extract(ketqua_tungbuoc_json, '$.dip') IS NULL"
               " THEN json_set(ketqua_tungbuoc_json, '$.dip', 'truoc_capnhat') ELSE ketqua_tungbuoc_json END"
               if c == "ketqua_tungbuoc_json" else c for c in cot]
    cn.execute(f"INSERT OR IGNORE INTO main.{bang} ({', '.join(cot)}) SELECT {', '.join(lay)} FROM giu.{bang}")


def _ghi_noi_giu(dl: Path) -> None:
    """Bước 3 (sau khi thay đủ 07 tệp): ghi nối dòng đã giữ, `INSERT OR IGNORE` (chạy lại không ghi đôi). Lỗi thì để lỗi lan ra."""
    giu = dl / TEP_GIU
    for ten, cac_bang in (("Nhatky", BANG_GIU), ("Hotho", ("cho_day_drive",))):
        cn = sqlite3.connect(dl / f"{ten}.sqlite3", isolation_level=None)
        try:
            cn.execute("ATTACH DATABASE ? AS giu", (str(giu),))
            ban = cn.execute("PRAGMA main.user_version").fetchone()[0]
            cn.execute("BEGIN IMMEDIATE")
            try:
                for bang in cac_bang:
                    if _co_bang(cn, "giu", bang) and _co_bang(cn, "main", bang):
                        _noi_bang(cn, bang, ban)
                cn.execute("COMMIT")
            except Exception:
                cn.execute("ROLLBACK")
                raise
        finally:
            cn.close()
    giu.unlink(missing_ok=True)


def _thu_ghi_noi(dl: Path, tep: Path, tt: dict) -> None:
    """Ghi nối lỗi thì KHÔNG chặn quay về: giữ tệp tạm + cờ `giu_nhatky` (kèm lý do), lần khởi động sau ghi lại."""
    if not (dl / TEP_GIU).exists():
        if tt.pop("giu_nhatky", None) is not None:
            _ghi(tep, tt)
        return
    try:
        _ghi_noi_giu(dl)
        tt.pop("giu_nhatky", None)
    except (OSError, sqlite3.Error) as e:
        tt["giu_nhatky"] = {"tep": TEP_GIU, "loi": type(e).__name__, "luc": _bay()}
    _ghi(tep, tt)


def _ghi_f04_da_tra(dl: Path, yc: dict) -> None:
    try:
        from maychu.dulieu import maso
        cn = sqlite3.connect(dl / "Nhatky.sqlite3", isolation_level=None)
        try:
            nguoi = yc.get("nguoi")   # V2 nhỏ: ghi đúng người bấm quay về
            cn.execute("INSERT INTO nhatky_thaotac (id, luc, nguoi_loai, nguoi_id, congcu, lenhcon, thamso_tomtat, ketqua)"
                       " VALUES (?, ?, ?, ?, 'capnhat', 'quayve', ?, 'dat')",
                       (maso.tao(), _bay(), "anh" if nguoi else None, nguoi,
                        f"{yc.get('ban_anh')} → {yc.get('ban_truoc')} · đã trả dữ liệu về bản chụp trước lúc nâng"
                        + (" · chưa giữ được nhật ký sau giờ nâng" if yc.get("giu_loi") else "")))
        finally:
            cn.close()
    except Exception:  # noqa: BLE001 - không ghi được nhật ký thì vẫn chạy bản trước
        pass


def _xong_tra(dl: Path, tep: Path, tt: dict, yc: dict) -> None:
    _thu_ghi_noi(dl, tep, tt)   # QĐ237: nhật ký, M01 'saoluu' ghi sau giờ chụp nối lại TRƯỚC dòng "quayve"
    _ghi_f04_da_tra(dl, yc)   # dòng F04 "quayve" ghi trước khi trả đã bị trả về theo bản chụp: ghi lại
    yc.pop("tra_du_lieu", None)
    yc["da_tra"] = (tt.get("nang_luocdo") or {}).get("luc")   # QĐ219 A7: "Dữ liệu đã trả về lúc …"
    tt.pop("nang_luocdo", None)
    tt["chay_ban_truoc"] = yc
    _ghi(tep, tt)


def chon(thumuc_dulieu: Path | None = None, goc: Path = GOC) -> Path:
    """Thư mục mã sẽ chạy (và trả dữ liệu nếu cần, R1, V2). Bản trước hỏng quá SO_LAN_HONG lần thì bỏ cờ (R3)."""
    dl = thumuc_dulieu or Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))
    tep = dl / TEN_TEP
    tt = _doc(tep)
    yc = tt.get("chay_ban_truoc")
    if not isinstance(yc, dict):
        return goc
    tra = yc.get("tra_du_lieu") if isinstance(yc.get("tra_du_lieu"), dict) else None
    if not tra and tt.get("giu_nhatky"):   # QĐ237: lần trước ghi nối nhật ký lỗi → ghi lại trước khi chạy
        _thu_ghi_noi(dl, tep, tt)
    if tra and tra.get("buoc") == "thay":   # V2: lần trước dừng giữa lúc thay tệp (mất điện, bị dừng) → đổi `.cu` về, làm lại
        _doi_ve_cu(dl, _tep_tra(tra))
        tra.pop("buoc", None)
        _ghi(tep, tt)
    elif tra and tra.get("buoc") == "xong_thay":   # đã thay đủ, chưa kịp dọn `.cu`
        _xoa_cu(dl, _tep_tra(tra))
        _xong_tra(dl, tep, tt, yc)
        tra = None
    ban_truoc = goc / "ban_truoc"
    if not (yc.get("ban_anh") == _so(goc / "VERSION") and yc.get("ban_truoc") == _so(ban_truoc / "VERSION")
            and (ban_truoc / "maychu").is_dir()):
        _bo_co(tep, tt)   # ảnh đã đổi: về chạy bản trong ảnh
        return goc
    if int(yc.get("so_lan_hong") or 0) >= SO_LAN_HONG:
        _bo_co(tep, tt, f"bản {yc.get('ban_truoc')} khởi động hỏng {SO_LAN_HONG:02d} lần, đã chạy lại bản {yc.get('ban_anh')}",
               kieu="khoidong", ban_truoc=yc.get("ban_truoc"), ban_anh=yc.get("ban_anh"), so_lan=SO_LAN_HONG, da_tra=yc.get("da_tra"))
        return goc
    if tra:
        if tra.get("buoc") != "xong_thay":
            try:   # QĐ237 bước 1: đọc tệp đang chạy TRƯỚC khi đổi tên (lỗi thì vẫn quay về, ghi chú ở dòng "quayve")
                _chep_giu(dl, dl / "saoluu" / str(tra.get("thumuc", "")))
            except (OSError, sqlite3.Error):
                (dl / TEP_GIU).unlink(missing_ok=True)
                yc["giu_loi"] = True

        def ghi_buoc(b):
            if b:
                tra["buoc"] = b
            else:
                tra.pop("buoc", None)
            _ghi(tep, tt)
        loi = tra_du_lieu(dl, tra, ghi_buoc)
        if loi:   # dữ liệu đã đổi về như trước lúc trả: chạy bản mới (anh vẫn vào được giao diện)
            (dl / TEP_GIU).unlink(missing_ok=True)   # không trả thì nhật ký vẫn còn ở tệp đang chạy
            _bo_co(tep, tt, loi, kieu="tra", ban_truoc=yc.get("ban_truoc"), ban_anh=yc.get("ban_anh"))
            return goc
        _xoa_cu(dl, _tep_tra(tra))
        _xong_tra(dl, tep, tt, yc)
    return ban_truoc


def _dem_hong(tep: Path, dat: bool) -> None:
    tt = _doc(tep)
    yc = tt.get("chay_ban_truoc")
    if isinstance(yc, dict):
        yc["so_lan_hong"] = 0 if dat else int(yc.get("so_lan_hong") or 0) + 1
        tt["chay_ban_truoc"] = yc
        _ghi(tep, tt)


def da_len(cong: str = CONG, giay: float = 3) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{cong}/suckhoe", timeout=giay) as r:
            return r.status == 200
    except OSError:
        return False


def canh_ban_truoc(noi: Path, tep: Path, cho_len: float = CHO_LEN_GIAY, hoi=da_len) -> int:
    """R3: chạy bản trước làm tiến trình con, chuyển tín hiệu dừng cho nó; chưa lên được mà đã dừng thì đếm hỏng."""
    con = subprocess.Popen([sys.executable, *LENH, "--app-dir", str(noi)], cwd=noi)
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda so, _k: con.send_signal(so))
    het, len_ = time.monotonic() + cho_len, False
    while con.poll() is None and not len_ and time.monotonic() < het:
        len_ = hoi()
        if not len_:
            time.sleep(2)
    if len_:
        _dem_hong(tep, True)
    ma = con.wait()
    if not len_:
        _dem_hong(tep, False)
    return ma


def moc_khoidong(dl: Path, goc: Path = GOC) -> None:
    """QĐ251: vùng chứa bản mới bắt đầu chạy = hết bước 5 (watchtower kéo gói, thay vùng chứa), vào bước 6.
    Chỉ ghi khi lượt cập nhật đang chờ đúng bản trong ảnh này, 01 lần. Lỗi thì bỏ qua."""
    try:
        tep = dl / TEN_TEP
        tt = _doc(tep)
        td = tt.get("tien_do")
        if isinstance(td, dict) and not td.get("xong") and not td.get("loi") and td.get("den") == _so(goc / "VERSION") \
                and "khoidong" not in (td.get("moc") or {}):
            td["moc"] = {**(td.get("moc") or {}), "khoidong": _bay()}
            td["buoc"] = "khoidong"
            _ghi(tep, tt)
    except Exception:  # noqa: BLE001 - tiến độ không chặn khởi động
        pass


def main() -> None:   # pragma: no cover - chạy trong ảnh
    dl = Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))
    moc_khoidong(dl)
    noi = chon(dl)
    os.chdir(noi)   # `python -m` đặt thư mục hiện tại lên đầu đường tìm mã: chạy đúng mã của bản đã chọn
    if noi == GOC:
        os.execv(sys.executable, [sys.executable, *LENH, "--app-dir", str(noi)])
    sys.exit(canh_ban_truoc(noi, dl / TEN_TEP))


if __name__ == "__main__":
    main()
