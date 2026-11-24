"""Lịch chạy nền tối thiểu (trước khi có lõi bot F23 ở ngày 07):
- đo máy mỗi giờ, ghi N02;
- sao lưu hằng ngày từ 02:00 giờ Việt Nam, ghi N01;
- cập nhật đang chờ việc AI chạy xong (tối đa 30 phút);
- đẩy bản sao lưu đã mã hoá lên Google Drive theo hàng chờ M01 (ngày 05), mỗi 05 phút;
- quét nguồn thông báo ở chuông mỗi 10 phút (QĐ165); đo máy, sao lưu xong thì quét ngay phần của mình;
- tin "có bản mới" quét riêng theo nhịp dò bản mới (QĐ174: 05 phút, `capnhat.nhip_kiem_giay`);
- đọc tệp phiên Codex mới nhất mỗi 10 phút để cập nhật % hạn mức gói ChatGPT, không gọi AI (QĐ192, bản 0.7.7).
Việc nặng chạy ở luồng phụ để không chặn máy chủ web.
"""
import asyncio
import logging
from datetime import datetime

from maychu.dulieu import saoluu
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.giamsat import domay, thongbao
from maychu.hethong.mohinh import congai
from maychu.ketnoi import drive

GIO_SAOLUU = 2
NHIP_THONGBAO_GIAY = 600   # ước lượng, chưa đo: gói AI hỏi CLI mỗi lần quét
log = logging.getLogger("igm360.lich")


async def chay_mai() -> None:
    gio_do_cuoi = None
    lan_day_cuoi = 0.0
    lan_tb_cuoi = None
    lan_bm_cuoi = None
    while True:
        bay_gio = datetime.now(saoluu.MUIGIO_VN)
        try:
            moc = bay_gio.strftime("%Y-%m-%d %H")
            if moc != gio_do_cuoi:
                await asyncio.to_thread(domay.ghi_n02)
                await asyncio.to_thread(thongbao.quet_maychu)
                gio_do_cuoi = moc
            capnhat.xu_ly_cho()
            if bay_gio.hour >= GIO_SAOLUU and not saoluu.da_co_hom_nay(bay_gio=bay_gio):
                kq = await asyncio.to_thread(saoluu.chay)
                log.info("sao lưu: %s", kq["ketqua"])
                await asyncio.to_thread(saoluu.don_truoc_nangcap)   # D1 (QĐ281): mốc 30 ngày tự đến
                await asyncio.to_thread(thongbao.quet_saoluu)
            if lan_tb_cuoi is None or asyncio.get_running_loop().time() - lan_tb_cuoi >= NHIP_THONGBAO_GIAY:
                lan_tb_cuoi = asyncio.get_running_loop().time()
                await asyncio.to_thread(congai.quet_codex)   # 0.7.7: đọc tệp phiên Codex, không gọi AI
                kq = await asyncio.to_thread(thongbao.quet)
                if any(v != "dat" for v in kq.values()):
                    log.info("quét thông báo: %s", kq)
            if lan_bm_cuoi is None or asyncio.get_running_loop().time() - lan_bm_cuoi >= capnhat.nhip_kiem_giay():
                lan_bm_cuoi = asyncio.get_running_loop().time()
                await asyncio.to_thread(thongbao.quet_banmoi, None, True)
            if asyncio.get_running_loop().time() - lan_day_cuoi >= 300:
                lan_day_cuoi = asyncio.get_running_loop().time()
                # QĐ277: công tắc "Sao lưu Google Drive" tắt thì lịch không đẩy
                kq = await asyncio.to_thread(drive.day_hang_cho) if thongso.drive_bat() else {}
                if kq.get("day") or kq.get("loi"):
                    log.info("đẩy Drive: %s", kq)
        except Exception:  # lỗi 01 lượt không được làm dừng lịch
            log.exception("lịch chạy nền gặp lỗi")
        await asyncio.sleep(60)
