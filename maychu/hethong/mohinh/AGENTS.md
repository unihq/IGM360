# AGENTS.md – maychu/hethong/mohinh

## 1. Vai thư mục

Cổng AI 03 nguồn (`congai.py`: gói Claude, gói ChatGPT, khóa API), đăng nhập gói (`dangnhap_goi.py`), mã dài hạn (`madaihan.py`), danh sách mô hình (`danhmuc_mohinh.py`), trò chuyện (`trochuyen.py`).

## 2. Đọc gì trước

- `congai.py`: chọn nguồn theo ưu tiên, hết hạn mức, ghi 01 dòng mỗi lần gọi.
- `dangnhap_goi.py`, `madaihan.py`: thư mục tài khoản riêng từng gói, cách đọc tên, gói.
- `danhmuc_mohinh.py`: chỉ thêm mô hình, không xóa.

## 3. Luật bắt buộc

- Bài kiểm KHÔNG gọi CLI thật: trỏ `IGM360_CLAUDE_CLI`, `IGM360_CODEX_CLI` tới đường không có, giả lập tiến trình.
- Mã dài hạn, khóa API không ghi ra nhật ký, câu lỗi; dùng `che.che`.
- Gọi CLI bằng danh sách đối số (không ghép chuỗi lệnh shell).
- Hết hạn mức tính là xếp hàng, không báo kẹt (QĐ113).
- Mỗi gói 01 thư mục tài khoản riêng; không dùng chung tệp đăng nhập.
- Bản CLI ghim trong Dockerfile; đổi cách nâng CLI theo kế hoạch đã duyệt (QĐ263–QĐ265, QĐ271).

## 4. Được chứa / không được chứa

- Được: mã cổng AI, đăng nhập gói, danh sách mô hình.
- Không: mã dài hạn, khóa API, tệp phiên thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ110, QĐ113: cứu việc AI kẹt (ngắt bước treo rồi tiếp phiên cũ), nhắc lại 01 lần sau 30 phút.
- QĐ178, QĐ184: ô chọn mô hình theo nguồn.
- QĐ198: đăng nhập gói Claude bằng mã dài hạn.

## 6. Kiểm trước bàn giao

- Bài kiểm ngày 06 và các bản sau đạt; đếm số lần gọi CLI thật = 0.

## 7. Người giữ

CTO viết; CDA soát phần ghi dữ liệu.
