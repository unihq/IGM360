# Thay đổi của IGM360

Mỗi bản 01 mục, viết bằng lời thường. Phần mềm đọc tệp này để hiện "Có bản mới" ở Cài đặt, ngăn Cập nhật.
Dòng "Tóm tắt:" ngắn (dưới 50 chữ cái) hiện ở bảng lịch sử cập nhật; các dòng "- " hiện ở khối có gì mới.

## 0.7.3
Tóm tắt: Thẻ gói AI ghi tên và tên gói
- Ô tài khoản gói Claude, gói ChatGPT ghi tên tài khoản và tên gói theo hãng (ví dụ "Tên · Ultra") thay cho "Tài khoản 1". Phần mềm đọc mỗi lần mở màn, không lưu lại.
- Hãng chưa trả tên thì vẫn ghi "Tài khoản 1" như trước.
- Thẻ gói ChatGPT và hộp Thêm nguồn AI dùng logo gốc của OpenAI.

## 0.7.2
Tóm tắt: Chuông báo tin mới, tự cập nhật
- Chuông ở thanh trên báo thêm: gói AI hết phiên đăng nhập hoặc dùng gần hết hạn mức tuần, khoá kết nối sắp hết hạn hoặc đã hết hạn, sao lưu không xong, ổ cứng máy chủ đầy, có bản phần mềm mới.
- Mỗi dòng ghi rõ việc gì, có số; bấm vào thì mở đúng màn cần xử lý. Số trên chuông tự cập nhật mỗi phút.
- Nút "Đọc hết" đưa số về 0; việc chưa xử lý xong vẫn nằm ở nhóm "Đã xem, còn mở" để không bị sót.
- Ngưỡng báo hạn mức tuần của gói AI đặt ở Cài đặt › Thông số, mặc định 80%.

## 0.7.1
Tóm tắt: Sửa lỗi trùng tài khoản gói AI
- Đăng nhập lại đúng tài khoản gói AI đã kết nối thì phần mềm báo "Tài khoản Claude này đã kết nối ở Tài khoản 1", không thêm ô mới.
- Mỗi tài khoản gói Claude, gói ChatGPT có nút Gỡ tài khoản, hỏi lại 01 lần trước khi gỡ; lịch sử dùng AI vẫn giữ.
- Ô tài khoản thứ 02 chỉ hiện sau khi đăng nhập xong; nút thêm đổi thành "Thêm tài khoản Claude khác".

## 0.7.0
Tóm tắt: Nền dữ liệu mới, tên gọi chuẩn, sửa lỗi nhỏ
- Dữ liệu chuyển sang cấu trúc mới: sổ người chung, mã cố định cho danh mục, sẵn chỗ cho phân quyền tài khoản và thêm nguồn AI. Dữ liệu đang có được giữ nguyên, tự chuyển khi cập nhật.
- Tên màn và nhãn đổi theo từ điển thuật ngữ: Chờ duyệt, Mô hình AI, Phí theo lượt, Phí cố định tháng, Hạn mức chi tháng.
- Gói AI (phí cố định tháng) luôn được dùng trước Khoá API (phí theo lượt); số ưu tiên hiện đúng thứ tự dùng.
- Cập nhật xong, trình duyệt tự tải giao diện mới, không cần xoá dữ liệu trang; nút Kiểm tra lại báo rõ khi có lỗi.
- Chữ không còn bị tách cụm khi xuống dòng ở màn Mô hình AI, Trò chuyện AI; đầu khung trò chuyện ghi gói và mô hình đang dùng.

## 0.6.0
Tóm tắt: Giao diện mới, tiền AI ra đồng Việt
- Màn Đăng nhập, menu, Cài đặt, Model và Trò chuyện AI dựng lại đúng bản vẽ đã duyệt.
- Thẻ Khoá API tính tiền theo tháng, kèm số tiền quy ra đồng Việt để tham khảo; chưa có tỷ giá thì ghi rõ "chưa có tỷ giá".
- Bảng lịch sử cập nhật có dòng tóm tắt ngắn cho mỗi bản; chữ không bị ngắt giữa cụm từ khi xuống dòng.
- Mỗi lần sửa mã đều được kiểm tự động trên máy chủ Linux trước khi đóng bản; các thư viện phần mềm dùng đã ghim đúng bản đã kiểm.

## 0.5.0
Tóm tắt: Đăng nhập gói AI, gọi AI qua 03 nguồn
- Đăng nhập gói Claude, gói ChatGPT ngay trên phần mềm, thêm được tài khoản thứ 02.
- Phần mềm gọi được AI qua gói Claude, gói ChatGPT, khoá API; ghi lại mỗi lần dùng AI và mức đã dùng của gói.
- Có sẵn phần trò chuyện với trợ lý AI (màn hình có ở bản sau).
- Ngưỡng tiền để AI tự áp dụng chuyển sang giai đoạn 2; giai đoạn 1 mọi đề xuất chờ anh bấm.

## 0.4.0
Tóm tắt: Sao lưu mã hoá, Két khoá, sẵn Google Drive
- Bản sao lưu hằng ngày được mã hoá, chờ đẩy lên Google Drive khi anh kết nối Drive.
- Két khoá cất được khoá kết nối, báo trước khi khoá sắp hết hạn.
- Có sẵn phần kết nối Google Drive (màn kết nối có ở bản sau).

## 0.3.0
Tóm tắt: Đăng nhập 02 lớp, menu, Cài đặt
- Có màn Đăng nhập, bật đăng nhập 02 lớp.
- Có menu, ngăn Thông số, ngăn Tài khoản và 02 lớp, ngăn Cập nhật ở Cài đặt.
- Dữ liệu tự nâng lên bản mới khi cập nhật, có chụp bản sao trước khi nâng.
- Báo khi máy chủ dùng tệp hoán đổi quá 100 MB.

## 0.2.0
Tóm tắt: Dữ liệu 104 bảng, sao lưu, đo máy
- Tạo 07 file dữ liệu, sao lưu hằng ngày trên máy chủ, đo máy mỗi giờ.

## 0.1.0
Tóm tắt: Bản đầu tiên của GĐ 1
- Bản đầu tiên: phần mềm chạy trên máy chủ, kiểm được qua HTTPS.
