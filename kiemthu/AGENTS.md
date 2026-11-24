# AGENTS.md – kiemthu

Tệp này dùng cho mọi thư mục con `banXXX`, `ngayXX` (không có tệp riêng, QĐ269).

## 1. Vai thư mục

Bài kiểm unittest của toàn phần mềm. Mỗi bản có 01 thư mục `banXXX` (ví dụ `ban083` cho 0.8.3); các ngày giai đoạn 1 ở `ngayXX`.

## 2. Đọc gì trước

- Bài kiểm của bản gần nhất cùng phần đang sửa (khung dựng thư mục dữ liệu tạm, giả CLI, giả Google).
- `kiemthu/test_chucam.py` (chữ cấm).
- AGENTS.md của thư mục mã đang kiểm.

## 3. Luật bắt buộc

- Mỗi bài dùng thư mục dữ liệu tạm (`tempfile`), đặt `IGM360_THUMUC_DULIEU`, dọn khi xong; không đụng dữ liệu thật.
- Không gọi CLI thật (Claude, Codex): trỏ `IGM360_CLAUDE_CLI`, `IGM360_CODEX_CLI` tới đường không có; giả lập bằng `mock`.
- Không gọi mạng thật: Google, GHCR, GitHub giả lập (`httpx.MockTransport`, `mock`).
- Lịch chạy nền tắt trong bài kiểm (`IGM360_LICH=tat`).
- Bài kiểm cũ: không xóa, không sửa câu kiểm; chỉ thêm dòng ở phần chuẩn bị khi hành vi mặc định đổi theo QĐ (luật 18 cửa chặn). Câu kiểm ghi nguyên văn chữ đã được QĐ đổi thì đổi theo QĐ và ghi rõ trong báo cáo.
- Giá trị giống khóa, IP, email trong bài kiểm: ghép từ nhiều mảnh lúc chạy để kho không chứa chuỗi đó.
- Không in dòng lệnh của máy GitHub (dòng bắt đầu bằng 02 dấu hai chấm) trong bài kiểm.

## 4. Được chứa / không được chứa

- Được: `test_*.py`, `__init__.py`, khung dùng chung trong bài kiểm.
- Không: dữ liệu thật, tệp lớn, khóa thật, đường dẫn máy cá nhân.

## 5. Quyết định đã chốt – không tự đảo

- QĐ267, QĐ268: kết luận phải có dữ liệu kiểm chứng; bài kiểm mới cho lỗi phải hỏng trên mã cũ, đạt trên mã mới.
- QĐ259 luật 18: số bài chạy không ít hơn, số bài bỏ qua không nhiều hơn main.

## 6. Kiểm trước bàn giao

- Chạy đủ bộ `python -m unittest discover -s kiemthu -t .`; đếm số lần gọi CLI thật = 0.
- Trên Windows: chỉ còn các lỗi đã biết (quyền tệp, lệnh hệ điều hành); so dòng hỏng với main khi nghi lỗi bị che.
- Máy GitHub (Linux) xanh.

## 7. Người giữ

CTO viết và giữ; CDA, CDO đọc khi soát.
