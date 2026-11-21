"""Lịch chạy nền tối thiểu (trước khi có lõi bot F23 ở ngày 07):
- đo máy mỗi giờ, ghi N02;
- sao lưu hằng ngày từ 02:00 giờ Việt Nam, ghi N01;
- cập nhật đang chờ việc AI chạy xong (tối đa 30 phút).
Việc nặng chạy ở luồng phụ để không chặn máy chủ web.
"""
import asyncio
import logging
from datetime import datetime

from maychu.dulieu import saoluu
from maychu.hethong import capnhat
from maychu.hethong.giamsat import domay

GIO_SAOLUU = 2
log = logging.getLogger("igm360.lich")


async def chay_mai() -> None:
    gio_do_cuoi = None
    while True:
        bay_gio = datetime.now(saoluu.MUIGIO_VN)
        try:
            moc = bay_gio.strftime("%Y-%m-%d %H")
            if moc != gio_do_cuoi:
                await asyncio.to_thread(domay.ghi_n02)
                gio_do_cuoi = moc
            capnhat.xu_ly_cho()
            if bay_gio.hour >= GIO_SAOLUU and not saoluu.da_co_hom_nay(bay_gio=bay_gio):
                kq = await asyncio.to_thread(saoluu.chay)
                log.info("sao lưu: %s", kq["ketqua"])
        except Exception:  # lỗi 01 lượt không được làm dừng lịch
            log.exception("lịch chạy nền gặp lỗi")
        await asyncio.sleep(60)
