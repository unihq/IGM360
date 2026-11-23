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


def _bo_co(tep: Path, tt: dict, loi: str | None = None) -> None:
    tt.pop("chay_ban_truoc", None)
    if loi:
        tt["quayve_loi"] = {"chu": loi, "luc": _bay()}
    _ghi(tep, tt)


def tra_du_lieu(dl: Path, tra: dict) -> str | None:
    """R1: trả các tệp ghi trong `tra` từ thư mục chụp; đủ cả mới thay. Trả None khi xong, chuỗi lỗi khi không trả."""
    noi = dl / "saoluu" / str(tra.get("thumuc", ""))
    tep = [t for t in tra.get("tep", []) if isinstance(t, str) and t.isidentifier()]
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
        for t, p in tam.items():   # đủ 07 tệp tạm mới thay: bỏ nhật ký WAL của tệp cũ rồi đổi tên
            for duoi in ("-wal", "-shm"):
                (dl / f"{t}.sqlite3{duoi}").unlink(missing_ok=True)
            os.replace(p, dl / f"{t}.sqlite3")
        return None
    except (OSError, sqlite3.Error) as e:
        for p in tam.values():
            p.unlink(missing_ok=True)
        return f"không trả được dữ liệu: {type(e).__name__}"


def _ghi_f04_da_tra(dl: Path, yc: dict) -> None:
    try:
        from maychu.dulieu import maso
        cn = sqlite3.connect(dl / "Nhatky.sqlite3", isolation_level=None)
        try:
            cn.execute("INSERT INTO nhatky_thaotac (id, luc, congcu, lenhcon, thamso_tomtat, ketqua) VALUES (?, ?, 'capnhat', 'quayve', ?, 'dat')",
                       (maso.tao(), _bay(), f"{yc.get('ban_anh')} → {yc.get('ban_truoc')} · đã trả dữ liệu về bản chụp trước lúc nâng"))
        finally:
            cn.close()
    except Exception:  # noqa: BLE001 - không ghi được nhật ký thì vẫn chạy bản trước
        pass


def chon(thumuc_dulieu: Path | None = None, goc: Path = GOC) -> Path:
    """Thư mục mã sẽ chạy (và trả dữ liệu nếu cần, R1). Bản trước hỏng quá SO_LAN_HONG lần thì bỏ cờ (R3)."""
    dl = thumuc_dulieu or Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))
    tep = dl / TEN_TEP
    tt = _doc(tep)
    yc = tt.get("chay_ban_truoc")
    if not isinstance(yc, dict):
        return goc
    ban_truoc = goc / "ban_truoc"
    if not (yc.get("ban_anh") == _so(goc / "VERSION") and yc.get("ban_truoc") == _so(ban_truoc / "VERSION")
            and (ban_truoc / "maychu").is_dir()):
        _bo_co(tep, tt)   # ảnh đã đổi: về chạy bản trong ảnh
        return goc
    if int(yc.get("so_lan_hong") or 0) >= SO_LAN_HONG:
        _bo_co(tep, tt, f"bản {yc.get('ban_truoc')} khởi động hỏng {SO_LAN_HONG:02d} lần, đã chạy lại bản {yc.get('ban_anh')}")
        return goc
    if yc.get("tra_du_lieu"):
        loi = tra_du_lieu(dl, yc["tra_du_lieu"])
        if loi:
            _bo_co(tep, tt, loi)
            return goc
        _ghi_f04_da_tra(dl, yc)   # dòng F04 "quayve" ghi trước khi trả đã bị trả về theo bản chụp: ghi lại
        yc.pop("tra_du_lieu", None)
        tt.pop("nang_luocdo", None)
        tt["chay_ban_truoc"] = yc
        _ghi(tep, tt)
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


def main() -> None:   # pragma: no cover - chạy trong ảnh
    dl = Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))
    noi = chon(dl)
    os.chdir(noi)   # `python -m` đặt thư mục hiện tại lên đầu đường tìm mã: chạy đúng mã của bản đã chọn
    if noi == GOC:
        os.execv(sys.executable, [sys.executable, *LENH, "--app-dir", str(noi)])
    sys.exit(canh_ban_truoc(noi, dl / TEN_TEP))


if __name__ == "__main__":
    main()
