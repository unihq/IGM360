# AGENTS.md – maychu/web/giaodien

Tệp này dùng cho `logo` (không có tệp riêng, QĐ269).

## 1. Vai thư mục

Giao diện 01 trang: `index.html` (khung, CSS), `app.js` (vẽ màn, gọi `/api`), `icon.js` (tên màn, icon), `dangnhap3d.css` (đồ họa trang đăng nhập, 0.8.9), `logo` (logo gốc của hãng ngoài và logo riêng IGM360: `igm360_bieutuong.svg`, `igm360_ngang.svg`, `favicon.ico`, `igm360_180.png` – chép nguyên tệp bộ logo đã duyệt QĐ342, QĐ345).

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
- Trang đăng nhập 0.8.9 (QĐ369, QĐ371; CDA SOAT-KH-088): màu ngoại lệ của khối xanh, phông nền chỉ đặt trong bộ chọn `#s01`; mọi quy tắc `dangnhap3d.css` nằm trong `#s01`; CSS ô đăng nhập (ô nhập, nút, 07 trạng thái) ở `index.html` để thiếu `dangnhap3d.css` vẫn đăng nhập được; đồ họa `aria-hidden`, `pointer-events: none`. Trạng thái linh vật dùng biến riêng `S.lv` (`dang`, `xong`), không thêm giá trị vào `S.dn` (07 giá trị); `dangNhap`, `xacNhanMa` trả `S.lv = null` trong `finally`. Chuyển động chỉ dùng `transform`, `opacity` (không `filter`, `box-shadow` trong khối keyframes); giảm chuyển động hoặc máy yếu (`hardwareConcurrency <= 2` hoặc `deviceMemory <= 2`) → lớp `.tinh`, đứng yên. Tên khối keyframes của đồ họa có tiền tố `dn3-`.
- 0.9.0 phông nền và khung (QĐ375, QĐ387): lớp phông `.pn` đặt ngay sau thẻ mở `body`, `aria-hidden`, không nhận bấm, không chữ, đứng yên (0 `animation`, 0 `transition`, 0 `backdrop-filter`, 0 `filter: blur`); khối CSS giữa `/* <PHONGNEN> */` và `/* </PHONGNEN> */` chép nguyên của DM, không tự sửa số. Mọi quy tắc khung chỉ áp `#app:not(.mb)`; khổ máy tính cuộn ở `.cuon-trong` (đổi màn về đầu, `vungCuon()`); thanh trên ẩn, khối `.vi-tri` (chuông, tài khoản) dời ngay dưới logo bằng `doiViTri()` (điện thoại giữ ở thanh trên); 02 bảng thả xuống mở từ cột menu dùng `position: fixed`, mép trái 08 px, top đặt lúc mở (`datTha`). Bóng tĩnh chỉ ở: thẻ `.the`, vùng làm việc, 02 khung Trò chuyện AI, mục menu đang chọn, vầng chọn ô nhập; không bóng trên bong bóng chữ chạy dần.
- 0.9.0 công tắc 02 lớp (QĐ390, QĐ397, QĐ398): khối `// <TAT2LOP>` của `app.js`; chữ ở `CHU_2LOP` chép nguyên bảng chữ màn 09 (anh duyệt QĐ397), không tự đặt chữ; đang tắt thì ẩn "Đổi máy nhận mã".
- N0 (QĐ344, QĐ350, QĐ352, QĐ355): khối `// <LUOT>` của `app.js`: gửi tin trò chuyện thì `api()` thêm `nen: true`, nghe `EventSource` của lượt; chữ chạy dần qua `cum()`, con trỏ `.dang-viet` là span rỗng ở cuối (không tô cả đoạn), chỉ bám đáy khi đang ở đáy (≤ 40 px), `aria-busy` khi đang chạy, xong thì vẽ lại bằng tin đã lưu; tin `hethong` có `phu.loai = 'luot_cat'` không có nút "Mở Mô hình AI"; không lưu gì ở trình duyệt.

## 4. Được chứa / không được chứa

- Được: `index.html`, `app.js`, `icon.js`, `dangnhap3d.css`, ảnh logo trong `logo`.
- Không: ảnh chụp dữ liệu thật, phông chữ, thư viện tải ngoài.

## 5. Quyết định đã chốt – không tự đảo

- QĐ88, QĐ89: bản vẽ đợt 1, tên màn, icon.
- QĐ92: logo gốc của hãng ngoài.
- QĐ135, QĐ136: thuật ngữ thông dụng, nhãn 02–04 tiếng.
- QĐ288, QĐ304, QĐ298: không dùng chữ "chụp"; mọi chữ viết dấu kiểu mới (Y50 đã đổi cả chữ dùng chung, nút "Hủy").

## 6. Kiểm trước bàn giao

- `node --check app.js`; bài kiểm giao diện chạy bằng node (thẻ tiến độ, công tắc) đạt, 0 chữ "undefined".
- Xem ở khổ điện thoại 390 điểm ảnh: không tràn ngang; ô bấm cao tối thiểu 44 điểm ảnh.
- CDO nghiệm thu bằng bản bấm thử.

## 7. Người giữ

CTO viết mã; CDO soát chữ, màu, icon.
