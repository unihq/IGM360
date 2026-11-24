# AGENTS.md – maychu/hethong/giamsat

## 1. Vai thư mục

Giám sát và chạy nền: lịch chạy nền (`lich.py`), chuông thông báo (`thongbao.py`), đo máy (`domay.py`).

## 2. Đọc gì trước

- `lich.py`: vòng 60 giây; giờ sao lưu; nhịp quét chuông, kiểm bản mới, đẩy Drive.
- `thongbao.py`: bảng loại tin (`LOAI`), `_mo` / `_dong` theo khóa, các hàm `quet_*`.
- `domay.py`: lệnh đo chạy trong máy, in số ra cửa sổ lệnh.

## 3. Luật bắt buộc

- Lỗi 01 lượt không được làm dừng lịch (bắt lỗi, ghi nhật ký máy chủ, chạy tiếp).
- Việc nặng gọi qua `asyncio.to_thread`; không chặn vòng lịch.
- Việc có thể chạy lâu (lượt kiểm công cụ AI 03:00: tải npm, kiểm thử) chạy thành việc nền riêng (`asyncio.create_task`, giữ tham chiếu, không chạy chồng); vòng lịch không chờ (CDA KT-Y46-3 L2).
- Chuông mở 01 dòng cho cả chuỗi lỗi liên tiếp, tự đóng khi hết lỗi; khóa chuông là chữ không dấu ổn định.
- Công tắc "Sao lưu Google Drive" tắt thì lịch không đẩy Drive, chuông Drive không mở (QĐ277).
- Lịch tắt khi `IGM360_LICH=tat` (bài kiểm, máy GitHub).
- `domay` không mở cổng ra ngoài mạng.

## 4. Được chứa / không được chứa

- Được: mã lịch, chuông, đo máy.
- Không: địa chỉ máy chủ, lệnh vào máy chủ có thông tin thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ165: mốc đọc chuông.
- QĐ261, QĐ262: chuông "Bản sao Drive lỗi" sau 03 lần đẩy nền lỗi.
- QĐ281: dọn bản sao trước khi nâng sau lượt sao lưu hằng ngày.
- QĐ271: công cụ AI tự kiểm bản mới từ 03:00 mỗi ngày, máy tắt lúc đó thì kiểm khi bật lại.
- QĐ271, QĐ307: chuông công cụ AI (`cli_nang`, `cli_loi`, `cli_o` thiếu ổ trống, `cli_mang` không kết nối được hãng); hoãn khi hết hạn mức không mở chuông.

## 6. Kiểm trước bàn giao

- Bài kiểm chuông (mở, tự đóng, không lặp), lịch, đo máy đạt.

## 7. Người giữ

CTO viết; CDO soát chữ chuông.
