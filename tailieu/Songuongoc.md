# SỔ NGUỒN GỐC

Mỗi tính năng chuyển từ mã có sẵn ghi 01 dòng. Chưa chuyển tính năng nào trong 19 tính năng F32-F50; dòng dưới là phần hạ tầng học cách làm của mã có sẵn rồi viết lại.

| Tính năng | Tệp gốc | Commit | Đoạn đã lấy (hàm) | Chỗ đặt trong IGM360 | Phần viết mới | Người rà | Ngày |
|---|---|---|---|---|---|---|---|
| Hạ tầng đóng image và chạy trên VPS | `Dockerfile`, `docker-compose.yml`, `docker-compose.https.yml`, `.github/workflows/docker-publish.yml` của UNI MATE 0.455.0 | 764206b | 02 dòng tạo lối tắt `npm`, `npx` và 01 dòng kiểm sức khoẻ viết cùng kiểu mã gốc; phần còn lại không chép, chỉ học cách làm: lấy Node.js từ image chính thức, cài Claude Code CLI và Codex CLI bằng npm, chạy bằng người dùng thường, kiểm sức khoẻ bằng thư viện chuẩn Python, cấu hình watchtower (nhận lệnh cập nhật có mã, dọn image cũ), lấy số phiên bản CLI trước khi đóng image | `Dockerfile`, `docker-compose.yml`, `.github/workflows/dongimage.yml` | Viết lại toàn bộ: không cài gói hệ điều hành và phần trình duyệt; cổng HTTPS theo tên miền cố định; phần mềm không mở cổng ra ngoài; giới hạn dung lượng nhật ký Docker; bài kiểm chạy trước khi đóng image | CTO | 21/11/2026 |
