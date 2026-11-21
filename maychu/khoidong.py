"""Điểm vào máy chủ IGM360.

Chưa có màn hình nào: màn hình chỉ dựng theo bản vẽ đã duyệt.
Khi khởi động: tạo 07 file dữ liệu (nếu chưa có) và bật lịch chạy nền (đo máy, sao lưu).
Đặt IGM360_LICH=tat để tắt lịch (dùng khi chạy bài kiểm).
Trang tài liệu tự sinh của FastAPI (/docs, /redoc, /openapi.json) tắt hẳn.
"""
import asyncio
import contextlib
import os
from pathlib import Path

from fastapi import FastAPI

from maychu.dulieu import khoitao

THUMUC_GOC = Path(__file__).resolve().parent.parent


def doc_phienban() -> str:
    """Đọc số phiên bản từ tệp VERSION ở gốc mã."""
    try:
        return (THUMUC_GOC / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "chưa rõ"


PHIENBAN = doc_phienban()


@contextlib.asynccontextmanager
async def vongdoi(_app: FastAPI):
    khoitao.tao_het()
    viec = None
    if os.environ.get("IGM360_LICH", "bat") != "tat":
        from maychu.hethong.giamsat import lich
        viec = asyncio.create_task(lich.chay_mai())
    try:
        yield
    finally:
        if viec:
            viec.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await viec


app = FastAPI(title="IGM360", version=PHIENBAN, docs_url=None, redoc_url=None, openapi_url=None, lifespan=vongdoi)


@app.get("/suckhoe")
def suckhoe() -> dict:
    """Máy chủ còn chạy. Không trả số đo máy ra ngoài mạng."""
    return {"trangthai": "chay", "phienban": PHIENBAN}
