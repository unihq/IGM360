# AGENTS.md – maychu

## 1. Vai thư mục

Mã máy chủ Python (FastAPI, uvicorn) của IGM360. Thư mục con: `dulieu` (07 tệp SQLite), `hethong` (cập nhật, an toàn, tài khoản, két khóa, AI, giám sát), `ketnoi` (Drive, hộp tin), `web` (đường gọi, giao diện), `mauketnoi` (mẫu kết nối).

Tệp này dùng cho `mauketnoi` (không có tệp riêng; thư mục cha gần nhất là `maychu`).

## 2. Đọc gì trước

- `khoidong.py`: thứ tự khởi động (tạo, nâng lược đồ → chế độ an toàn nếu lỗi → khởi tạo, lịch, kiểm sau cập nhật).
- `chay.py`: lệnh chạy của ảnh, chọn bản chạy (bản trong ảnh hay bản trước), trả dữ liệu khi quay về.
- AGENTS.md của thư mục con sắp sửa.

## 3. Luật bắt buộc

- Chỉ dùng thư viện đã khai ở `requirements.txt` và thư viện chuẩn; nạp module động bị cửa chặn chặn (luật 16).
- Đường dẫn dữ liệu lấy từ `ketnoi.thumuc_dulieu()` (biến `IGM360_THUMUC_DULIEU`), không ghi cứng.
- Chữ người dùng thấy đặt ở 01 chỗ (bảng CHU, hằng chữ) theo bảng chữ đã duyệt; không tự đổi chữ.
- Ghi thao tác vào F04 qua `maychu.hethong.nhatky.ghi` (đã che mã bí mật); không ghi khóa ra nhật ký.
- Ở chế độ an toàn chỉ mở được Cập nhật; việc ghi khác bị chặn (QĐ218).
- `mauketnoi`: chỉ mẫu cấu trúc kết nối (`.json`); không mã ứng dụng, không bí mật, không địa chỉ trả về thật.

## 4. Được chứa / không được chứa

- Được: mã `.py`, lược đồ `.sql`, tệp giao diện, mẫu kết nối `.json`.
- Không: dữ liệu thật, khóa, tệp tạm, chữ cấm (tên mã gốc).

## 5. Quyết định đã chốt – không tự đảo

- QĐ213, QĐ215: 05 lớp an toàn cập nhật; quay về chạy bản trước có trong ảnh, không cần mạng.
- QĐ237: quay về giữ nhật ký và hàng chờ ghi sau giờ nâng.
- QĐ211: mọi việc chạm cấu trúc dữ liệu có phiếu tác động của CDA trước.

## 6. Kiểm trước bàn giao

- Bài kiểm của bản (thư mục `kiemthu/banXXX`) và đủ bộ đạt.
- Đổi lược đồ: bài nâng từ bản trước, quay về.

## 7. Người giữ

CTO viết và giữ; CDA soát `dulieu`, `hethong`; CDO soát `web/giaodien`.
