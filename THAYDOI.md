# Thay đổi của IGM360

Mỗi bản 01 mục, viết bằng lời thường. Phần mềm đọc tệp này để hiện "Có bản mới" ở Cài đặt, ngăn Cập nhật.
Dòng "Tóm tắt:" ngắn (dưới 50 chữ cái) hiện ở bảng lịch sử cập nhật; các dòng "- " hiện ở khối có gì mới.

## 0.8.2
Tóm tắt: Cập nhật nhanh hơn
Nâng dữ liệu: không
- Từ bản sau, lần cập nhật chỉ đổi phần mềm tải khoảng 01–02 MB thay vì hàng trăm MB.
- Bản không nâng dữ liệu: bản sao Drive được đẩy ngay sau khi lên bản mới; bản sao trên máy chủ vẫn chụp trước như cũ.
- Lên bản mới là trang tải lại ngay; kiểm sau cập nhật chạy nền, kết quả hiện ở lịch sử cập nhật.

## 0.8.1
Tóm tắt: Tiến độ cập nhật theo 08 bước
- Thẻ Đang cập nhật hiện % và 08 bước, đã chạy bao lâu, còn khoảng bao lâu.
- Bước 5–7 ghi rõ "ước tính", tính theo các lần cập nhật trước.
- Lỗi trước khi gửi lệnh cập nhật: thẻ ghi dừng ở bước nào, bản đang dùng và dữ liệu giữ nguyên, có nút Thử lại.
- Cập nhật xong, thẻ hiện kết quả kiểm sau cập nhật rồi trang tự tải lại sau 03 giây.
- Sửa lỗi thẻ Đang cập nhật quay mãi dù đã lên bản mới; nay trang tự tải lại khi bản mới chạy.
- Chờ tải gói cài tối đa 30 phút (trước 10 phút), mạng chậm vẫn cập nhật được.

## 0.8.0
Tóm tắt: Nền dữ liệu bản 4
- Dữ liệu nâng lên bản 4 trong 01 lần: dựng sẵn chỗ lưu cho trò chuyện AI (ghim, lưu trữ, mục Đã xoá, Project, chia sẻ), gia hạn gói AI, đã đọc thông báo theo người. Các tính năng này bật dần ở các bản sau.
- Chuẩn bị tìm tin nhắn không dấu: phần mềm chỉ lưu các từ để tìm, không chép thêm nội dung tin nhắn.
- Bản sao ngay trước khi cập nhật được ghi riêng, không lẫn với sao lưu hằng ngày; chuông sao lưu chỉ báo theo lần sao lưu hằng ngày.
- Kiểm sau cập nhật kiểm thêm: số dòng dữ liệu không bị hụt sau khi nâng, chỉ mục tìm tin nhắn đủ.
- Quay về 0.7.9 sau khi lên 0.8.0 thì dữ liệu trả về lúc trước khi cập nhật; việc nhập sau lúc đó không giữ được.

## 0.7.9
Tóm tắt: 05 lớp an toàn khi cập nhật, tên gói Claude
- Trước khi cập nhật, phần mềm kiểm ổ trống; ổ không đủ thì khoá nút Cập nhật và ghi rõ còn bao nhiêu, cần bao nhiêu.
- Trước khi gửi lệnh cập nhật, phần mềm chụp bản sao 07 tệp dữ liệu, đẩy lên Drive (chờ tối đa 10 phút) rồi mới cập nhật.
- Bản mới nâng dữ liệu không thành thì dữ liệu trả về như trước và phần mềm chạy chế độ an toàn, chỉ mở Cài đặt › Cập nhật.
- Có nút Quay về bản trước: chạy lại bản liền trước để sẵn trong gói cài, không cần mạng.
- Sau khi lên bản mới, phần mềm tự kiểm 06 điểm và ghi kết quả ở lịch sử cập nhật; có điểm chưa đạt thì báo ở chuông.
- Quay về bản trước chưa được thì lịch sử cập nhật và chuông ghi rõ lý do; phần mềm chạy lại bản mới, vào được giao diện.
- Thẻ Claude hiện lại tên, gói khi dùng mã dài hạn; nút Lấy tên, gói lấy lại tên, gói khi cần; dòng Kiểm mã cho biết lần gọi thử đạt hay chưa.
- Chặn 02 tài khoản trùng nhau ở mọi ô, kể cả Tài khoản 1. Đăng nhập nhầm tài khoản của ô khác thì mã dài hạn giữ nguyên, phần mềm không ghi tên, gói sai và hiện nút Lấy tên, gói để làm lại.
- Dán mã dài hạn chép từ PowerShell không còn bị từ chối vì xuống dòng, dấu cách; dán nhầm ô mã xác nhận cũng nhận đúng; dán khoá API hoặc chuỗi khác thì báo rõ không phải mã dài hạn.
- Dán mã mới khi mã cũ còn hạn: gọi thử lỗi thì giữ mã cũ; gọi thử gặp hết hạn mức của gói thì vẫn lưu mã mới và báo rõ.
- Câu chữ trên màn hình, chuông và Trò chuyện AI xưng "bạn"; chữ không còn ngắt dòng giữa một cụm từ.
- Nhật ký thao tác ghi đúng trạng thái đăng nhập kiểu cũ sau khi đăng xuất.

## 0.7.8
Tóm tắt: Mã dài hạn 365 ngày cho gói Claude
- Gói Claude kết nối bằng mã dài hạn dùng 365 ngày, không còn hết phiên giữa chừng như kiểu đăng nhập cũ.
- Thẻ Claude ở mục Mô hình AI: chưa kết nối có nút Kết nối Claude và Dán mã; đã có mã thì có Lấy mã mới, Dán mã; tài khoản đăng nhập kiểu cũ có nút Chuyển sang mã dài hạn.
- Thẻ hiện 04 ký tự cuối của mã, ngày hết hạn, số ngày còn lại; 14 ngày cuối đổi màu cảnh báo. Mã hết hạn thì thẻ ghi rõ và phần mềm dùng tài khoản khác rồi tới nguồn kế tiếp.
- Chuông nhắc mỗi ngày từ 07 ngày trước khi mã hết hạn; lấy mã mới hoặc gỡ tài khoản thì tin nhắc tự đóng.
- Gỡ tài khoản xoá luôn mã dài hạn khỏi Két khoá. Mã cất đã mã hoá, không hiện lại trên màn, không ghi vào nhật ký.
- Rê chuột nút chọn mô hình ghi tên ngắn như dòng chữ vàng (ví dụ "Opus"); trên điện thoại, hộp hỏi lại nằm giữa màn.
- Sửa 01 bài kiểm tự động hỏng khi sang ngày mới.

## 0.7.7
Tóm tắt: Tự cập nhật hạn mức, mô hình việc nền
- Mục Mô hình AI tự cập nhật số hạn mức mỗi phút, không cần mở lại màn hay bấm Gọi thử.
- Qua giờ đặt lại, hạn mức hiện 0% ngay.
- Gói ChatGPT: phần mềm tự đọc số hạn mức mỗi 10 phút, không tốn lượt hỏi AI.
- Mô hình hoặc tài khoản bị hãng báo hết hạn mức thì phần mềm tạm không gọi tới giờ đặt lại; hãng không báo giờ thì nghỉ 01 giờ. Các mô hình khác vẫn dùng.
- Bảng mô hình mặc định có thêm dòng "Việc nền chung": việc chạy nền chưa đặt riêng thì dùng mô hình của dòng này.
- Trên điện thoại, ô báo rộng hết màn và nằm trên thanh dưới.
- Trò chuyện AI qua Claude được tra web và dùng nhiều bước trong 01 câu trả lời, không còn bị cắt ở bước đầu; vẫn không chạy lệnh máy, không ghi, sửa tệp. Dòng chữ vàng ghi rõ loại lỗi.

## 0.7.6
Tóm tắt: Chọn theo mô hình, tự xoay tài khoản
- Sửa lỗi bản 0.7.5: bấm chọn mô hình ở khung trò chuyện không đổi được khi chưa đặt mô hình mặc định.
- Chọn mô hình ở khung trò chuyện: dùng ngay cho cuộc đang mở và làm mặc định cho các cuộc trò chuyện mới.
- Bảng chọn mô hình gộp theo hãng và công cụ (Claude · Code, ChatGPT · Codex…), không chia theo tài khoản.
- Có nhiều tài khoản cùng loại: phần mềm dùng tài khoản đang chạy, hết hạn mức mới sang tài khoản dự phòng, dùng hết tài khoản cùng loại rồi mới sang loại khác.
- Mô hình đã chọn hết hạn mức: phần mềm thử các tài khoản cùng loại còn lại, hết thì dùng mô hình mặc định; cả gói hết hạn mức thì tự chuyển sang hãng khác theo thứ tự nguồn (ví dụ Claude hết thì sang ChatGPT) và ghi rõ dưới câu trả lời.
- Dòng dưới câu trả lời ghi hãng, công cụ và tên mô hình ngắn, không ghi tài khoản; rê chuột thấy bản cụ thể và tài khoản thực chạy.
- Thêm tài khoản thứ 02 cho cùng 01 gói: phần mềm nhắc hãng có thể khoá tài khoản khi dùng nhiều tài khoản.

## 0.7.5
Tóm tắt: Chọn mô hình AI ngay dưới khung trò chuyện
- Nút chọn mô hình dưới khung trò chuyện: tìm theo tên, xem theo từng nguồn đã kết nối; chọn khác mặc định thì chỉ áp cho cuộc trò chuyện đó.
- Tên mô hình ghi ngắn: Haiku, Sonnet, Opus; rê chuột thấy bản cụ thể.
- Mô hình đã chọn đang hết hạn mức thì phần mềm tự dùng mô hình mặc định và ghi 01 dòng dưới câu trả lời.
- Mục Mô hình AI: nút "Đổi" chọn mô hình mặc định cho từng loại việc.
- Máy khác hoặc trình duyệt khác chưa nhớ mô hình đã chọn của cuộc trò chuyện (bản sau lưu trên máy chủ).

## 0.7.4
Tóm tắt: Giữ tên tài khoản Claude sau mỗi lần cập nhật
- Tên tài khoản và tên gói Claude được lưu trong ổ lưu của máy chủ, không mất khi bấm "Cập nhật ngay".
- Tên nguồn AI ghi theo hãng và công cụ: "Claude · Code", "ChatGPT · Codex" ở thẻ, hộp Thêm nguồn AI, cột Nguồn, câu báo kết nối, gỡ; thẻ khoá đổi tên "Khoá API", từng khoá ghi "Claude · API", "OpenAI · API"…
- Phần mềm tự dò bản mới mỗi 05 phút; có bản mới thì báo ở chuông, không phải bấm "Kiểm tra lại".
- Sau lần cập nhật này: anh gỡ rồi đăng nhập lại tài khoản Claude 1 một lần để thẻ ghi đúng tên và tên gói; làm tương tự với tài khoản ChatGPT 1 nếu thẻ ghi sai gói.

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
