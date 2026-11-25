# AGENTS.md – maychu/hethong/mohinh

## 1. Vai thư mục

Cổng AI 03 nguồn (`congai.py`: gói Claude, gói ChatGPT, khóa API), đăng nhập gói (`dangnhap_goi.py`), mã dài hạn (`madaihan.py`), danh sách mô hình (`danhmuc_mohinh.py`), trò chuyện (`trochuyen.py`), sổ lượt trò chuyện chạy nền (`luot.py`, N0), công cụ AI tự nâng (`nangcli.py`, Y46).

## 2. Đọc gì trước

- `congai.py`: chọn nguồn theo ưu tiên, hết hạn mức, ghi 01 dòng mỗi lần gọi.
- `dangnhap_goi.py`, `madaihan.py`: thư mục tài khoản riêng từng gói, cách đọc tên, gói.
- `danhmuc_mohinh.py`: chỉ thêm mô hình, không xóa.
- `nangcli.py`: tệp trạng thái `/dulieu/cli/trangthai.json`, `nang` (01 lượt nâng 01 gói), `ve_ban_truoc`, `chan_vi` (K1), `xem` (khối Công cụ AI).

## 3. Luật bắt buộc

- Bài kiểm KHÔNG gọi CLI thật: trỏ `IGM360_CLAUDE_CLI`, `IGM360_CODEX_CLI` tới đường không có, giả lập tiến trình.
- Mã dài hạn, khóa API không ghi ra nhật ký, câu lỗi; dùng `che.che`.
- Gọi CLI bằng danh sách đối số (không ghép chuỗi lệnh shell).
- Hết hạn mức tính là xếp hàng, không báo kẹt (QĐ113).
- Mỗi gói 01 thư mục tài khoản riêng; không dùng chung tệp đăng nhập.
- Bản CLI ghim trong Dockerfile; đổi cách nâng CLI theo kế hoạch đã duyệt (QĐ263–QĐ265, QĐ271).
- Đường tệp chạy CLI chỉ lấy qua `dangnhap_goi._cli`: biến môi trường (bài kiểm) > bản đã nâng đạt kiểm (con trỏ) > bản trong gói.
- Bộ nâng không chạy khi đang cập nhật, ở chế độ an toàn, có cờ quay về, tự nâng tạm dừng (K1, `chan_vi`); "Về bản trước" cũng bị chặn như vậy (QĐ218 dòng 37).
- Tệp trạng thái công cụ AI: đọc – sửa – ghi dưới `_KHOA_TT` (`_sua_goi`); ghi nguyên tử.
- Bài kiểm không gọi npm thật: truyền `chay`, `client` giả (móc `kiemthu/__init__.py` báo hỏng nếu có lần chạy npm).
- Hết hạn mức lúc kiểm thử bản mới thì hoãn, không ghi bản hỏng (QĐ306).
- N0 (QĐ344, QĐ349, QĐ351): chỉ lượt trò chuyện có người nghe (`congai._NGHE`) đọc dần đầu ra CLI qua `_chay_dan` (nhóm tiến trình riêng; Dừng, quá giờ: TERM cả nhóm, chờ 02 giây, KILL). Việc nền, bot, Gọi thử, kiểm bản CLI mới (truyền `cli`) giữ `_chay`. Không đổi phần đọc kết quả, hết hạn mức, tự chuyển tài khoản, ghim, dòng vàng.
- N0 `luot.py` (QĐ344, CDA KT-N0, S1–S5, X1–X4, C1–C2): mỗi lượt 01 dòng G02 `trochuyen`; vào sổ trước khi ghi G02, rời sổ sau khi đóng G02; đóng G02 chỉ bằng `WHERE id = ? AND trangthai = 'dangchay'` + `xong_luc`; không truyền `viecnen_id` vào `congai.goi`; tin ghi 01 lần qua `trochuyen._ghi_tin` rồi mới đóng G02; khởi động và lượt kẹt dùng chung `doi_chieu_dong`; chữ câu báo theo QĐ352.
- N0 Đ3 (QĐ349, QĐ351, CDA K1–K7): lượt có người nghe gọi ChatGPT qua `codex app-server` (`_chay_as`): 01 tiến trình/lượt trong nhóm riêng, 01 luồng mới, `thread/start` mang `sandbox: read-only`, `approvalPolicy: never`, mô hình; mọi yêu cầu app-server gửi lên trả từ chối; chưa bắt đầu được lượt thì chạy lại `codex exec` cùng nguồn. Kiểm thử bản CLI mới thêm 01 lượt app-server thật (`kiem_app_server`, tối đa 300 giây, K1a–K1e); không ghi G02, G04.
- Gói Claude: danh sách mô hình = 04 bí danh + tệp danh mục Claude Code tự tải theo tài khoản (`cache/model-catalog`); mô hình cần bản công cụ cao hơn hiện xám (QĐ265).

## 4. Được chứa / không được chứa

- Được: mã cổng AI, đăng nhập gói, danh sách mô hình.
- Không: mã dài hạn, khóa API, tệp phiên thật.

## 5. Quyết định đã chốt – không tự đảo

- QĐ110, QĐ113: cứu việc AI kẹt (ngắt bước treo rồi tiếp phiên cũ), nhắc lại 01 lần sau 30 phút.
- QĐ178, QĐ184: ô chọn mô hình theo nguồn.
- QĐ198: đăng nhập gói Claude bằng mã dài hạn.
- QĐ263, QĐ264, QĐ265, QĐ271: công cụ AI tự nâng mỗi ngày 03:00, chỉ nhận bản đã ra từ 24 giờ, kiểm thử đạt mới dùng; quay về bản IGM360 trước thì tạm dừng; mô hình mới theo tài khoản.
- QĐ306, QĐ307, QĐ308, QĐ309: hoãn khi hết hạn mức; chữ chuông, khối Công cụ AI.

## 6. Kiểm trước bàn giao

- Bài kiểm ngày 06 và các bản sau đạt; đếm số lần gọi CLI thật = 0.

## 7. Người giữ

CTO viết; CDA soát phần ghi dữ liệu.
