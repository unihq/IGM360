# AGENTS.md – maychu/hethong/kekhoa

## 1. Vai thư mục

Két khóa: khóa chủ (`khoachu.py`), cất – đọc – đổi – xóa khóa (`kho.py`), che mã bí mật trong chữ ghi ra (`che.py`).

## 2. Đọc gì trước

- `khoachu.py`: khóa chủ là 01 tệp quyền 600 trong ổ dữ liệu, không nằm trong bản sao lưu.
- `kho.py`: chỉ lưu bản mã và 04 ký tự cuối.
- `che.py`: mẫu mã dài hạn và dấu che.

## 3. Luật bắt buộc

- Không bao giờ ghi khóa, mã dài hạn, mật khẩu ra nhật ký, câu lỗi, câu trả lời API; chữ ghi ra phải qua `che.che`.
- Danh sách két khóa trả cho giao diện không có bản mã.
- Khóa nội bộ (ví dụ mã 02 lớp) không hiện ở danh sách.
- Tệp khóa chủ quyền 600; không chép vào kho, không đưa vào bản sao lưu 07 tệp.
- Bài kiểm dùng khóa giả ghép lúc chạy; không khóa thật.
- AI không đọc, không in giá trị khóa thật trên máy chủ.

## 4. Được chứa / không được chứa

- Được: mã két khóa.
- Không: khóa thật, tệp khóa, giá trị mẫu giống khóa thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ89: khóa chủ, mã hóa két khóa.
- PTD-09 Đ3: che mã dài hạn ở mọi lớp ghi.

## 6. Kiểm trước bàn giao

- Bài kiểm két khóa (ngày 05), che mã (bản 0.7.8), khóa chủ không khớp thì báo, không giải mã.
- Quét nhạy cảm ĐẠT 0.

## 7. Người giữ

CTO viết; CDA soát (dữ liệu nhạy cảm).
