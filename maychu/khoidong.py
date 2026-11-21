"""Điểm vào máy chủ IGM360.

Bản khung tối thiểu: chưa có màn hình nào. Màn hình chỉ dựng theo bản vẽ đã duyệt.
Chỉ có 01 đường /suckhoe để Docker và cổng HTTPS kiểm máy chủ còn chạy.
Trang tài liệu tự sinh của FastAPI (/docs, /redoc, /openapi.json) tắt hẳn.
"""
from pathlib import Path

from fastapi import FastAPI

THUMUC_GOC = Path(__file__).resolve().parent.parent


def doc_phienban() -> str:
    """Đọc số phiên bản từ tệp VERSION ở gốc mã."""
    try:
        return (THUMUC_GOC / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "chưa rõ"


PHIENBAN = doc_phienban()

app = FastAPI(title="IGM360", version=PHIENBAN, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/suckhoe")
def suckhoe() -> dict:
    """Máy chủ còn chạy. Không trả số đo máy ra ngoài mạng."""
    return {"trangthai": "chay", "phienban": PHIENBAN}
