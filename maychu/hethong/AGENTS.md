# AGENTS.md – maychu/hethong

Tệp này dùng cho `caidat`, `nhatky` (không có tệp riêng, QĐ269).

## 1. Vai thư mục

Phần hệ thống: cập nhật (`capnhat.py`), an toàn cập nhật và quay về (`antoan.py`), tiến độ 08 bước (`tiendo.py`), thông số P01 (`caidat/thongso.py`), tên miền riêng (`caidat/tenmien.py`), nhật ký thao tác F04 (`nhatky`). Thư mục con có tệp riêng: `kekhoa`, `taikhoan`, `mohinh`, `giamsat`.

## 2. Đọc gì trước

- `antoan.py`: 05 lớp an toàn, tệp trạng thái (ghi nguyên tử), chế độ an toàn, `thong_tin_quayve`, bảng chữ `CHU`.
- `capnhat.py`: kiểm bản mới (GHCR, THAYDOI), `yeu_cau`, bản sao trước khi gửi lệnh, gửi lệnh cập nhật.
- `tiendo.py`: 08 bước, cách tính phần trăm, cờ treo.
- `caidat/thongso.py`: danh mục thông số, công tắc.
- `caidat/tenmien.py`: cổng gác `/tls-check`, kiểm DNS, đọc hạn chứng chỉ; khối Caddy ở `docker-compose.yml`.

## 3. Luật bắt buộc

- Tệp trạng thái ghi bằng `antoan.ghi` (ghi nguyên tử); không ghi tay.
- Chưa có bản sao thì không gửi lệnh cập nhật; mọi lỗi trước gửi lệnh đều báo lại, giữ bản đang chạy.
- Thông số P01: sửa là thêm 01 dòng có ngày áp dụng, đóng dòng đang dùng; không xóa dòng cũ. Công tắc chỉ đổi qua `thongso.gat` (QĐ278).
- Chữ người dùng thấy ở `antoan.CHU`, chữ tiến độ ở giao diện; đổi chữ phải theo bảng chữ đã duyệt.
- F04 chỉ ghi thêm, không sửa, không xóa dòng cũ.
- Tên miền (QĐ634): `/tls-check` chỉ trả 200 cho tên riêng đã lưu và lời hỏi không có tiêu đề chuyển tiếp; không đổi đường này, không thêm đường "bắt tất cả" trả 200; luôn giữ khối tên gốc `{$DOMAIN_NAME}`; dò DNS, đọc chứng chỉ chỉ trong luồng riêng có hạn giờ, không gọi dịch vụ ngoài.
- Tác động của 01 lần cập nhật do mã của bản ĐANG CHẠY quyết định; báo trước khi cập nhật phải đọc mã bản đang chạy.

## 4. Được chứa / không được chứa

- Được: mã hệ thống.
- Không: khóa, mật khẩu, địa chỉ máy chủ.

## 5. Quyết định đã chốt – không tự đảo

- QĐ213, QĐ215, QĐ218: 05 lớp an toàn, chế độ an toàn, hộp hỏi.
- QĐ249–QĐ256: thẻ tiến độ 08 bước, chờ 35 phút.
- QĐ258, QĐ261: bản không nâng dữ liệu thì Drive đẩy nền sau khi lên bản.
- QĐ277, QĐ284, QĐ287: công tắc Drive mặc định tắt; khóa Quay về khi bản sao trước khi nâng đã xóa.
- QĐ634 (B), QĐ650, QĐ651: tên miền riêng đổi ở thẻ Chung, chỉ Chủ + mật khẩu + mã 02 lớp; tên gốc luôn chạy.
- QĐ636: múi giờ D-a (`maychu/dulieu/muigio.py`).

## 6. Kiểm trước bàn giao

- Bài kiểm cập nhật, quay về, tiến độ, thông số của các bản `ban079` trở đi đạt.
- Không gọi watchtower, Docker thật trong bài kiểm.

## 7. Người giữ

CTO viết; CDA soát.
