# AGENTS.md – maychu/ketnoi

## 1. Vai thư mục

Kết nối nền tảng ngoài: Google Drive cho bản sao lưu (`drive.py`), hộp tin nhận báo từ ngoài (`hoptin.py`). Luật của `maychu/mauketnoi` (thư mục ngang hàng) ghi ở `maychu/AGENTS.md`.

## 2. Đọc gì trước

- `drive.py`: quyền `drive.file`, lưu mã ứng dụng, đăng nhập, `dang_noi`, `day_hang_cho`, thử lại lùi dần.
- `hoptin.py`: chống trùng theo nguồn và mã sự kiện.
- AGENTS.md của `maychu/dulieu` (hàng chờ đẩy Drive đi theo tệp).

## 3. Luật bắt buộc

- Chỉ xin đúng quyền cần (`drive.file`); Google cấp quyền khác thì từ chối.
- Mã làm mới, mã truy cập cất ở két khóa; không ghi ra nhật ký.
- Mã chống giả khi đăng nhập chỉ dùng 01 lần.
- Đẩy xong mới xóa tệp tạm trên máy; lỗi thì thử lại lùi dần, không đẩy 01 tệp 02 lần.
- Module nền tảng ngoài đặt ở `maychu/ketnoi/<nền tảng>/`, không ghi thẳng 07 tệp dữ liệu (QĐ248).
- Bài kiểm giả lập Google bằng `httpx.MockTransport`, không gọi mạng.

## 4. Được chứa / không được chứa

- Được: mã kết nối.
- Không: mã ứng dụng thật, bí mật, địa chỉ trả về thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ87, QĐ232, QĐ246: kết nối Drive cho sao lưu mã hóa.
- QĐ248: ranh giới thư mục module nền tảng ngoài.
- QĐ277, QĐ283: công tắc Drive; bật mà chưa nối thì dọn như khi tắt.

## 6. Kiểm trước bàn giao

- Bài kiểm Drive ngày 05 (kết nối, từ chối sai quyền, đẩy, thử lại) và Y49 đạt.

## 7. Người giữ

CTO viết; CDA soát (dữ liệu ngoài vào).
