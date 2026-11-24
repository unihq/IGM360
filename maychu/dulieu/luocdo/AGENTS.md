# AGENTS.md – maychu/dulieu/luocdo

## 1. Vai thư mục

Lược đồ 07 tệp SQLite, mỗi tệp 01 tệp `.sql`. `khoitao.py` chạy các tệp này khi tạo mới và khi nâng.

## 2. Đọc gì trước

- `maychu/dulieu/khoitao.py`: `PHIENBAN_LUOCDO`, đường nâng từng bản, bản sao trước khi nâng.
- `maychu/dulieu/ketnoi.py`: `SO_BANG` (số bảng mỗi tệp, kiểm sau cập nhật đọc số này).
- Phiếu tác động của CDA cho việc đang làm.

## 3. Luật bắt buộc

- Chỉ thêm; không xóa, không đổi tên bảng hay cột khi chưa có phiếu tác động và QĐ.
- Đổi lược đồ: tăng `PHIENBAN_LUOCDO`, có khung nâng từ bản trước, cập nhật `SO_BANG`, mục THAYDOI ghi "Nâng dữ liệu: có".
- Câu tạo, sửa, xóa cấu trúc ở mọi tệp ngoài kiemthu bị cửa chặn tự gộp chặn (luật 15).
- Ràng buộc chống trùng, CHECK đặt trong lược đồ làm lưới an toàn; lớp ghi vẫn kiểm trước.
- Bảng tìm chữ FTS5 dùng bộ tách `unicode61 remove_diacritics 2`.
- Chú thích dòng `--` ghi mã bảng và 01 dòng = 01 gì; không ghi dữ liệu thật.

## 4. Được chứa / không được chứa

- Được: chỉ tệp `.sql` lược đồ.
- Không: dữ liệu mẫu thật, câu xóa dữ liệu.

## 5. Quyết định đã chốt – không tự đảo

- QĐ211: CDA phân tích kiến trúc trước khi đổi cấu trúc.
- QĐ229: tìm chữ cần SQLite từ 3.43 (`contentless_delete`).
- QĐ237: quay về giữ 05 sổ nhật ký và hàng chờ ghi sau giờ nâng.

## 6. Kiểm trước bàn giao

- Bài kiểm số bảng đủ theo `SO_BANG`, nâng từ bản trước, quay về.
- Kiểm sau cập nhật (06 điểm) đạt điểm "lược đồ".

## 7. Người giữ

CTO viết; CDA soát.
