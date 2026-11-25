# AGENTS.md – maychu/hethong/taikhoan

## 1. Vai thư mục

Tài khoản và đăng nhập: người dùng (`nguoidung.py`), mật khẩu (`matkhau.py`), mã 02 lớp (`totp.py`), phiên (`phien.py`), chặn đoán mật khẩu (`chan.py`), đặt lại tài khoản chủ bằng lệnh (`datlai.py`).

## 2. Đọc gì trước

- `chan.py`: ngưỡng sai liền, thời gian khóa theo địa chỉ.
- `totp.py`: RFC 6238, lệch 01 bước, không nhận lại mã của bước đã dùng.
- `phien.py`: mã phiên, thu hồi phiên.

## 3. Luật bắt buộc

- Mật khẩu chỉ lưu dạng băm; không ghi mật khẩu, mã 02 lớp, mã phiên ra nhật ký.
- Không nới ngưỡng chặn đoán, thời gian khóa khi chưa có QĐ.
- Tài khoản chủ tạo từ biến môi trường lúc khởi động; mật khẩu do người dùng tự gõ, không gửi qua chat.
- Câu báo lỗi đăng nhập không cho biết sai tên hay sai mật khẩu.
- Bài kiểm dùng mật khẩu, địa chỉ giả ghép lúc chạy.

## 4. Được chứa / không được chứa

- Được: mã tài khoản, đăng nhập.
- Không: mật khẩu, mã thật, danh sách địa chỉ thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ90: chặn đoán mật khẩu.
- QĐ390 (thay "02 lớp bắt buộc, không có cách tắt trên web"): 02 lớp mặc định bật; Chủ tắt được ở Cài đặt › Tài khoản và 02 lớp (đường `/api/2lop/tat`, hỏi mật khẩu + mã, sai đếm `chan.py`); bật lại bằng 01 mã của khóa cũ (`/api/2lop/bat`), không sinh khóa mới. Cờ P01 `dangnhap_2lop` chỉ ghi qua `thongso.ghi_co_2lop` (đường sửa, gạt thông số chung từ chối – `thongso.CHI_DUONG_RIENG`); đọc lỗi hoặc trống coi là bật. Lần đầu chưa có khóa vẫn bắt bật. Chế độ an toàn không cho tắt.
- QĐ391: tắt 02 lớp không kiểm độ dài mật khẩu (`matkhau.py` giữ nguyên).
- QĐ393: bật lại thì thu hồi mọi phiên khác (giữ phiên vừa bật); `datlai` (có hay không `--tat-2lop`) đặt cờ về bật, đóng chuông "đang tắt", ghi F04; không thêm hỏi lại ở đường nhạy cảm; đổi máy nhận mã đếm sai, đang khóa thì từ chối như đăng nhập.
- QĐ398: 02 lớp đang tắt thì `/api/2lop/doimay/batdau`, `/xacnhan` từ chối (đọc cờ lúc xử lý, mã tạm cũ cũng bị từ chối).
- QĐ266: không thêm thư mục này vào danh sách chặn tự gộp; giữ các bộ bài kiểm đăng nhập, tài khoản sẵn có.

## 6. Kiểm trước bàn giao

- Bài kiểm đăng nhập, mã 02 lớp, chặn đoán, phiên (ngày 04) đạt.
- 0 chỗ in mật khẩu, mã ra nhật ký.

## 7. Người giữ

CTO viết; CDA soát.
