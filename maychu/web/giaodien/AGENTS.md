# AGENTS.md – maychu/web/giaodien

Tệp này dùng cho `logo` (không có tệp riêng, QĐ269).

## 1. Vai thư mục

Giao diện 01 trang: `index.html` (khung, CSS), `app.js` (vẽ màn, gọi `/api`), `icon.js` (tên màn, icon), `logo` (logo gốc của hãng ngoài).

## 2. Đọc gì trước

- Đầu `app.js`: `api()`, `S`, `D`, `cum()`, `esc()`, `icoMau()`, `xacnhan()`.
- Khối chữ của màn đang sửa (`CHU_CN`, `SL`, `TD8`, `CHU_Z21`…): chữ viết ở 01 chỗ.
- `icon.js`: icon Lucide (giấy phép ISC) sinh từ bản vẽ đã duyệt.
- Bản vẽ và bảng chữ đã duyệt của màn (tài liệu thiết kế nội bộ, hỏi người giữ).

## 3. Luật bắt buộc

- Chữ, màu, icon đúng bản vẽ và bảng chữ đã duyệt; không tự đổi chữ (luật 21 cửa chặn).
- Không nền đỏ, hồng; tối đa 04 màu nền; tương phản chữ từ 4,5:1.
- Icon đúng bản chất; icon Lucide lấy đúng nét trong bản vẽ; hãng ngoài dùng logo gốc của hãng, không tự vẽ.
- Không hiện đường dẫn thư mục, tài liệu cho người dùng.
- Chữ đưa vào HTML phải qua `esc()` hoặc `cum()`; không ghép chữ từ máy chủ thẳng vào HTML.
- Không thêm thư viện JS ngoài; không tải tệp từ mạng ngoài lúc chạy.
- Tiếng Việt có dấu, không ngắt dòng giữa 01 cụm từ; số 1–9 trước danh từ đếm ghi 02 chữ số.
- Chữ người dùng thấy xưng "bạn", không xưng "anh" (QĐ219, QĐ220).
- Dùng đúng từ điển thuật ngữ (tài liệu nội bộ, hỏi người giữ); nhãn, tên chỉ số 02–04 tiếng (QĐ135, QĐ136).
- Số: dấu chấm ngăn nghìn, dấu phẩy thập phân, bỏ số 0 thừa, đơn vị đặt sau số (ví dụ 1.250 MB, 0,5%).
- Chữ màu Đạt #258832 và Cảnh báo #E22E28 chỉ đặt trên nền trắng, luôn có icon hoặc chấm đi kèm.

## 4. Được chứa / không được chứa

- Được: `index.html`, `app.js`, `icon.js`, ảnh logo trong `logo`.
- Không: ảnh chụp dữ liệu thật, phông chữ, thư viện tải ngoài.

## 5. Quyết định đã chốt – không tự đảo

- QĐ88, QĐ89: bản vẽ đợt 1, tên màn, icon.
- QĐ92: logo gốc của hãng ngoài.
- QĐ135, QĐ136: thuật ngữ thông dụng, nhãn 02–04 tiếng.
- QĐ288, QĐ304: không dùng chữ "chụp"; chữ mới viết dấu kiểu mới.

## 6. Kiểm trước bàn giao

- `node --check app.js`; bài kiểm giao diện chạy bằng node (thẻ tiến độ, công tắc) đạt, 0 chữ "undefined".
- Xem ở khổ điện thoại 390 điểm ảnh: không tràn ngang; ô bấm cao tối thiểu 44 điểm ảnh.
- CDO nghiệm thu bằng bản bấm thử.

## 7. Người giữ

CTO viết mã; CDO soát chữ, màu, icon.
