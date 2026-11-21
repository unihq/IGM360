"""Điểm vào máy chủ IGM360.

Màn hình dựng đúng bản vẽ đã duyệt (QĐ79, QĐ88): ngày 04 có màn 01, 02, 09.
Khi khởi động: tạo hoặc nâng 07 file dữ liệu, tạo tài khoản chủ từ .env (lần đầu), ghi thông số
mặc định, ghi lịch sử bản đang chạy, rồi bật lịch chạy nền (đo máy, sao lưu).
Đặt IGM360_LICH=tat để tắt lịch (dùng khi chạy bài kiểm).
Trang tài liệu tự sinh của FastAPI (/docs, /redoc, /openapi.json) tắt hẳn.
"""
import asyncio
import contextlib
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from maychu.dulieu import khoitao
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.taikhoan import nguoidung
from maychu.web import api

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
    nguoidung.tao_quantri_tu_env()
    thongso.khoi_tao()
    capnhat.ghi_khoi_dong()
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


GIAODIEN = Path(__file__).resolve().parent / "web" / "giaodien"
app.include_router(api.router)
app.mount("/tainguyen", StaticFiles(directory=GIAODIEN), name="tainguyen")


@app.middleware("http")
async def dau_bao_ve(request, call_next):
    """Không cho trang khác nhúng IGM360, không đoán kiểu tệp, không gửi địa chỉ trang đi nơi khác."""
    res: Response = await call_next(request)
    res.headers["X-Frame-Options"] = "DENY"
    res.headers["X-Content-Type-Options"] = "nosniff"
    res.headers["Referrer-Policy"] = "no-referrer"
    res.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                              "img-src 'self' data:; font-src 'self' data:; frame-ancestors 'none'")
    return res


@app.get("/")
def trang_chinh() -> FileResponse:
    return FileResponse(GIAODIEN / "index.html", headers={"Cache-Control": "no-store"})

