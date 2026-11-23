"""Lệnh chạy của ảnh (0.7.9 lớp 3, QĐ213, QĐ215): chọn bản chạy rồi chạy uvicorn.

- Bình thường: chạy bản trong ảnh (`/app/maychu`).
- Anh đã bấm "Quay về bản trước": tệp trạng thái `capnhat_trangthai.json` có mục `chay_ban_truoc` ghi đúng bản ảnh
  này và đúng bản trước để sẵn ở `/app/ban_truoc` → chạy mã ở đó. Docker bật lại vùng chứa sau khi phần mềm tự dừng.
- Ảnh mới hơn về (bấm Cập nhật ngay lên bản sửa): mục đó ghi bản ảnh cũ → bỏ mục, chạy bản mới.
Chỉ dùng thư viện chuẩn: bản trước chạy trên đúng thư viện của ảnh này.
"""
import json
import os
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
THUMUC_BAN_TRUOC = GOC / "ban_truoc"
LENH = ["-m", "uvicorn", "maychu.khoidong:app", "--host", "0.0.0.0", "--port", os.environ.get("IGM360_CONG", "8360"),
        "--proxy-headers"]


def _so(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def chon(thumuc_dulieu: Path | None = None, goc: Path = GOC) -> Path:
    """Thư mục mã sẽ chạy."""
    tep = (thumuc_dulieu or Path(os.environ.get("IGM360_THUMUC_DULIEU", "/dulieu"))) / "capnhat_trangthai.json"
    try:
        tt = json.loads(tep.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return goc
    yc = tt.get("chay_ban_truoc") if isinstance(tt, dict) else None
    if not isinstance(yc, dict):
        return goc
    ban_truoc = goc / "ban_truoc"
    if yc.get("ban_anh") == _so(goc / "VERSION") and yc.get("ban_truoc") == _so(ban_truoc / "VERSION") \
            and (ban_truoc / "maychu").is_dir():
        return ban_truoc
    tt.pop("chay_ban_truoc", None)   # ảnh đã đổi: về chạy bản trong ảnh
    tam = tep.with_name(tep.name + ".tam")
    try:
        fd = os.open(tam, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tt, f, ensure_ascii=False)
        os.replace(tam, tep)
    except OSError:
        pass
    return goc


def main() -> None:   # pragma: no cover - chạy trong ảnh
    noi = chon()
    os.chdir(noi)   # `python -m` đặt thư mục hiện tại lên đầu đường tìm mã: chạy đúng mã của bản đã chọn
    os.execv(sys.executable, [sys.executable, *LENH, "--app-dir", str(noi)])


if __name__ == "__main__":
    main()
