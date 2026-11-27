"""Thư mục bộ não ngoài 07 tệp dữ liệu (bản 5, 0.10.0; Đ-a CDA 9.38, QĐ578, QĐ584; L03 – CPO áp A).

Cây từ bản đầu: `<dữ liệu>/bonao/chung/` là bộ não duy nhất lúc đầu, mỗi bộ não 01 kho git riêng (QĐ474). 0.10.0 chỉ
tạo thư mục và kho git `chung/` (chưa ghi tri thức – 0.12.0; chưa commit nên chưa cần tên người commit). Kho git ở
thư mục cha `bonao/` cho bộ quy tắc chung tạo ở 0.11.0 cùng nút tải, kèm `.gitignore` loại trừ thư mục con (L03).
Chạy lại không sao. Thiếu git (ảnh chưa cài) thì báo, không chặn khởi động; kiểm sau cập nhật chấm điểm "lược đồ" chưa đạt.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

from maychu.dulieu import ketnoi

TEN_THUMUC = "bonao"
CHUNG = "chung"
GIAY_GIT = 30
log = logging.getLogger(__name__)


def thumuc_bonao(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / TEN_THUMUC


def _git() -> str | None:
    return shutil.which("git")


def la_kho_git(noi: Path) -> bool:
    """Kho git hợp lệ: có `.git/HEAD` và git tự nhận là thư mục làm việc của 01 kho."""
    git = _git()
    if not git or not (noi / ".git" / "HEAD").is_file():
        return False
    r = subprocess.run([git, "-C", str(noi), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True,
                       timeout=GIAY_GIT)
    return r.returncode == 0 and r.stdout.strip() == "true"


def khoi_tao(thumuc: Path | None = None) -> dict:
    """Tạo `bonao/chung/` (quyền 700) và `git init` cho `chung/`. Trả {"chung": "moi" | "co_san" | "thieu_git" | "loi"}."""
    goc = thumuc_bonao(thumuc)
    chung = goc / CHUNG
    chung.mkdir(parents=True, exist_ok=True)
    for p in (goc, chung):
        os.chmod(p, 0o700)
    if la_kho_git(chung):
        return {"chung": "co_san"}
    git = _git()
    if not git:
        log.warning("chưa có git trong máy: chưa tạo kho git bộ não chung")
        return {"chung": "thieu_git"}
    r = subprocess.run([git, "-C", str(chung), "init", "-q"], capture_output=True, text=True, timeout=GIAY_GIT)
    if r.returncode != 0 or not la_kho_git(chung):
        log.error("tạo kho git bộ não chung lỗi: mã thoát %s", r.returncode)
        return {"chung": "loi"}
    return {"chung": "moi"}


def hop_le(thumuc: Path | None = None) -> bool:
    """Kiểm sau cập nhật (bản 5): `bonao/chung/` là kho git hợp lệ."""
    return la_kho_git(thumuc_bonao(thumuc) / CHUNG)
