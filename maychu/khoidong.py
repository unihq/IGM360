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

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from maychu.dulieu import khoitao
from maychu.hethong import antoan, capnhat
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
    viec = None
    from maychu.hethong import tiendo
    cua_luot = tiendo.vao_ban_moi(PHIENBAN)   # QĐ251: lượt cập nhật lên đúng bản này → bước 7 nâng lược đồ
    try:
        khoitao.tao_het(bao=(lambda i, n: tiendo.chi_tiet("nang", None, da=i, tong=n, xong=i == n)) if cua_luot else None)
    except Exception as e:  # noqa: BLE001 - 0.7.9 lớp 2: nâng dữ liệu không thành → chế độ an toàn, không khởi động lại mãi
        antoan.vao_an_toan(e)
        if cua_luot:
            tiendo.loi("an_toan")
    if not antoan.CHE_DO["an_toan"]:
        nguoidung.tao_quantri_tu_env()
        thongso.khoi_tao()
        capnhat.ghi_khoi_dong()
        try:   # QĐ264 (Y46): lên bản mới hơn bản đã quay về thì công cụ AI tự nâng lại
            from maychu.hethong.mohinh import nangcli
            nangcli.mo_lai_neu_len_ban_moi(capnhat.ban_dang_chay())
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception("mở lại tự nâng công cụ AI lỗi")
        try:   # QĐ279 (PTD-15 6.2 điểm 3): dọn 01 lần tệp sao lưu đã dồn, dòng chờ mất tệp; chạy lại không đổi gì
            from maychu.dulieu import saoluu
            saoluu.don_khi_khoidong()
        except Exception:  # noqa: BLE001 - dọn lỗi không chặn khởi động
            import logging
            logging.getLogger(__name__).exception("dọn tệp sao lưu lúc khởi động lỗi")
        try:   # Y50 (QĐ301): đổi 02 chữ dấu kiểu cũ đã lưu (05 điều kiện CDA); lỗi không chặn khởi động
            from maychu.dulieu import doidau
            doidau.doi_khi_khoidong()
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception("đổi chữ dấu kiểu mới lúc khởi động lỗi")
        try:   # N0 (QĐ344): lượt trò chuyện bị cắt do khởi động lại → đối chiếu, 01 tin báo (QĐ352), đóng G02
            from maychu.hethong.mohinh import luot
            luot.don_khi_khoidong()
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception("đóng lượt trò chuyện dở lúc khởi động lỗi")
        if os.environ.get("IGM360_LICH", "bat") != "tat":
            from maychu.hethong.giamsat import lich
            viec = asyncio.create_task(lich.chay_mai())
        antoan.bao_quay_ve_loi()   # Y38c R1, R3: lệnh chạy không trả được dữ liệu / bản trước hỏng → ghi F04
        from maychu.hethong.giamsat import thongbao
        thongbao.quet_quayve_loi()   # Y38d: tin chuông đỏ khi quay về hỏng
        if viec is not None and antoan.can_kiem():   # 0.7.9 lớp 4: bản mới lần đầu chạy → kiểm 06 điểm (chạy nền, không chặn
            # khởi động). Chỉ khi lịch chạy nền bật (máy chủ thật): bài kiểm tắt lịch nên không bao giờ chạm CLI của máy kiểm.
            # Y38c R6: chờ 30 giây rồi chấm điểm lịch theo việc lịch còn chạy thật
            if cua_luot:
                tiendo.sang("kiem", None, da=0, tong=6)   # QĐ251 bước 8: điểm k/06
            asyncio.get_running_loop().run_in_executor(None, antoan.kiem_sau_khi_chay, viec)
        elif cua_luot:
            tiendo.xong(PHIENBAN)   # không chạy kiểm (lịch tắt): lượt kết thúc sau bước 7
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
    return {"trangthai": "chay", "phienban": PHIENBAN, **({"an_toan": True} if antoan.CHE_DO["an_toan"] else {})}


GIAODIEN = Path(__file__).resolve().parent / "web" / "giaodien"
app.include_router(api.router)
app.mount("/tainguyen", StaticFiles(directory=GIAODIEN), name="tainguyen")


@app.middleware("http")
async def che_do_an_toan(request, call_next):
    """0.7.9 lớp 2: ở chế độ an toàn chỉ mở đăng nhập và Cài đặt › Cập nhật; đường khác trả câu báo."""
    if antoan.CHE_DO["an_toan"] and not antoan.duoc_mo(request.url.path):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": antoan.CHU["an_toan_chan"], "an_toan": True}, status_code=503)
    return await call_next(request)


@app.middleware("http")
async def dau_bao_ve(request, call_next):
    """Không cho trang khác nhúng IGM360, không đoán kiểu tệp, không gửi địa chỉ trang đi nơi khác."""
    res: Response = await call_next(request)
    res.headers["X-Frame-Options"] = "DENY"
    res.headers["X-Content-Type-Options"] = "nosniff"
    res.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/tainguyen/"):
        # Y17 (b): trình duyệt luôn hỏi lại máy chủ (không đổi thì trả 304), không tự giữ app.js cũ sau khi cập nhật
        res.headers["Cache-Control"] = "no-cache"
    res.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                              "img-src 'self' data:; font-src 'self' data:; frame-ancestors 'none'")
    return res


# Y17 (b): đường tệp mã giao diện gắn số bản (`?v=`), cập nhật xong trình duyệt buộc tải tệp mới ngay lần mở đầu.
TRANG_CHINH = (GIAODIEN / "index.html").read_text(encoding="utf-8").replace(
    'src="/tainguyen/icon.js"', f'src="/tainguyen/icon.js?v={PHIENBAN}"').replace(
    'src="/tainguyen/app.js"', f'src="/tainguyen/app.js?v={PHIENBAN}"').replace(
    'src="/tainguyen/chedo.js"', f'src="/tainguyen/chedo.js?v={PHIENBAN}"')   # QĐ562: chế độ màu


@app.get("/tls-check")
def tls_check(request: Request, domain: str = "") -> JSONResponse:
    """QĐ634: cổng gác Caddy On-Demand TLS. 200 chỉ khi tên = tên miền riêng đã lưu VÀ lời hỏi đi thẳng từ Caddy
    (không có tiêu đề chuyển tiếp); còn lại 403. Đừng đổi đường này (Caddy `ask` gọi đúng đường) và đừng thêm đường
    "bắt tất cả" trả 200: bản quay về không có đường này thì Caddy nhận 404, không cấp chứng chỉ (CDA PTD-20 mục 4 điểm 3)."""
    from maychu.hethong.caidat import tenmien
    if tenmien.cho_cap(domain, request.headers):
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False}, status_code=403)


@app.get("/")
def trang_chinh() -> HTMLResponse:
    return HTMLResponse(TRANG_CHINH, headers={"Cache-Control": "no-store"})

