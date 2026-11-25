# AGENTS.md – maychu/dulieu

## 1. Vai thư mục

Lớp dữ liệu: mở 07 tệp SQLite, tạo và nâng lược đồ, mã dòng, phiên bản danh mục, sao lưu, sổ người, tìm chữ.

## 2. Đọc gì trước

- `ketnoi.py`: danh sách tệp (`CAC_FILE`), số bảng (`SO_BANG`), `mo()`, `thumuc_dulieu()`.
- `khoitao.py`: `PHIENBAN_LUOCDO`, `tao_het()`, bản sao trước khi nâng, dòng khởi tạo.
- `phienban.py` (danh mục có phiên bản), `maso.py` (mã ULID), `aibam.py` (giá trị "ai bấm").
- `saoluu.py` (sao lưu, dọn tệp, bản sao trước khi nâng), `timchu.py`.

## 3. Luật bắt buộc

- Không ghi số bảng, tên cột ra ngoài mã; đọc ở `ketnoi.SO_BANG` và tệp `.sql`.
- Mã dòng tạo bằng `maso.tao()`; cột người thao tác nhận giá trị qua `aibam.kiem()`.
- Danh mục có phiên bản: dòng mã mới dùng `phienban.them`; nội dung có ngày hiệu lực dùng `phienban.phienban_moi` (thêm phiên bản, không sửa đè, không xóa dòng cũ); cột trạng thái (không mang nghĩa phiên bản) sửa tại chỗ bằng `phienban.sua`.
- Ghi nhiều dòng dùng `BEGIN IMMEDIATE`, lỗi thì `ROLLBACK`.
- Sao lưu: không chép thẳng tệp đang chạy; dùng lệnh sao lưu trực tuyến, kiểm `integrity_check`, đổi tên 01 lần, mã hóa.
- Dòng hàng chờ Drive loại `saoluu` đi theo tệp: xóa tệp thì xóa dòng chờ (QĐ279); không đụng tệp gốc Hồ thô (QĐ54).
- Xóa thư mục bản sao trước khi nâng: đổi tên trước rồi mới xóa (Y49b N2).
- Tìm chữ: `timchu` đổi đ → d, FTS5 bỏ dấu khác; dùng cùng 01 hàm ở cả 02 phía.

## 4. Được chứa / không được chứa

- Được: mã lớp dữ liệu, thư mục `luocdo`.
- Không: tệp dữ liệu mẫu thật, khóa chủ, bản sao lưu.

## 5. Quyết định đã chốt – không tự đảo

- QĐ108: mã người số tăng dần 07 chữ số (sổ người A18).
- QĐ142, QĐ143: danh mục có phiên bản, chặn sửa mã.
- QĐ227: sổ sao lưu ghi loại hằng ngày / trước cập nhật.
- QĐ277, QĐ279, QĐ281, QĐ283: công tắc Drive, luật dọn 03 ngày / 02 lượt, giữ bản sao trước khi nâng 30 ngày.
- QĐ301: `doidau.doi_khi_khoidong` đổi 02 chữ kiểu cũ đã lưu (tên lịch qua `phienban_moi`, `ketnoi.loi_cuoi` theo đúng chữ cũ), 05 điều kiện CDA.

## 6. Kiểm trước bàn giao

- Bài kiểm số bảng, nâng từ bản trước, quay về, sao lưu – dọn tệp.
- Chạy lại hàm khởi tạo, dọn tệp không đổi gì thêm.

## 7. Người giữ

CTO viết; CDA soát (QĐ211).
