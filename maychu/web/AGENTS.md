# AGENTS.md – maychu/web

## 1. Vai thư mục

Đường gọi HTTP của máy chủ (`api.py`, tiền tố `/api`) và giao diện tĩnh (`giaodien`, có tệp AGENTS.md riêng).

## 2. Đọc gì trước

- `api.py`: phần bảo vệ ở đầu tệp (lệnh không phải GET phải có đầu báo `X-IGM360`), `can_dang_nhap`, các mô hình đầu vào, cách trả lỗi `HTTPException`.
- `maychu/khoidong.py`: lớp chặn ở chế độ an toàn, đầu báo bảo mật gắn vào câu trả lời (`dau_bao_ve`).

## 3. Luật bắt buộc

- Mọi đường gọi cần đăng nhập dùng `Depends(can_dang_nhap)`; chỉ vài đường công khai đã chốt (sức khỏe, trang về của đăng nhập Drive).
- Mã phiên ở cookie HttpOnly, SameSite=Strict, Secure.
- Đường ghi (POST) yêu cầu đầu báo của giao diện; không thêm đường ghi bằng GET.
- Luồng sự kiện (N0): `GET /api/trochuyen/luot/{id}/sukien` chỉ đọc, `text/event-stream`, `Cache-Control: no-cache`; không thêm lớp nén cho đường này.
- Thao tác thay đổi ghi F04 (ai, lúc, việc gì) qua `ghi_f04`.
- Câu lỗi trả về là chữ người dùng thấy: tiếng Việt có dấu, xưng "bạn" không xưng "anh" (QĐ219, QĐ220), đúng từ điển thuật ngữ (tài liệu nội bộ, hỏi người giữ; QĐ135, QĐ136); không lộ khóa, đường dẫn, chi tiết kỹ thuật.
- Số trong câu trả về theo cách hiện số của giao diện (chấm ngăn nghìn, phẩy thập phân, bỏ số 0 thừa, đơn vị sau số).
- Không trả bản mã khóa, mật khẩu, mã dài hạn trong câu trả lời.

## 4. Được chứa / không được chứa

- Được: đường gọi, mô hình đầu vào.
- Không: logic nghiệp vụ dài (đặt ở `hethong`, `dulieu`), khóa, địa chỉ máy chủ.

## 5. Quyết định đã chốt – không tự đảo

- QĐ88 (màn Đăng nhập), QĐ90 (bảo mật đăng nhập).
- QĐ218 dòng 37: chế độ an toàn chỉ mở được Cập nhật.
- QĐ266: `api.py` không nằm trong danh sách chặn tự gộp; giữ bộ bài kiểm đăng nhập, tài khoản, két khóa.

## 6. Kiểm trước bàn giao

- Bài kiểm đường gọi (đăng nhập, két khóa, cập nhật, thông số) đạt.

## 7. Người giữ

CTO viết; CDA soát đường ghi dữ liệu.
