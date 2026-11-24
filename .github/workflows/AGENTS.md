# AGENTS.md – .github/workflows

## 1. Vai thư mục

Tệp luồng máy GitHub: `dongimage.yml` (kiểm mọi nhánh, chỉ main đóng ảnh GHCR), `tugop.yml` (tự gộp bản sửa lỗi `sualoi/*`). Luật của `.github/cua` và `.github/CODEOWNERS` ghi ở AGENTS.md gốc.

## 2. Đọc gì trước

- `dongimage.yml`: việc `kiemthu` (tên dùng làm kiểm bắt buộc của luật main), việc `dongimage` (`needs: kiemthu`, chỉ `refs/heads/main`).
- `tugop.yml` và `.github/cua/kiem_sualoi.py`, `.github/cua/quet_chung.py`.
- AGENTS.md ở gốc kho.

## 3. Luật bắt buộc

- `permissions: {}` ở đầu tệp; từng việc xin đúng quyền cần, không xin thêm.
- Không đổi tên việc `kiemthu` (luật main yêu cầu kiểm này; tên việc phải không trùng giữa các tệp luồng).
- Bước "Chạy bài kiểm": đầu ra bài kiểm ghi vào tệp, chú thích "Ket qua bai kiem" ghi xong mới in đầu ra, bọc `::stop-commands::` mã ngẫu nhiên (Y44e N5).
- `tugop.yml`: công cụ cửa chặn lấy từ main, chỉ đọc phần đổi, không chạy mã của nhánh; gộp bằng `--match-head-commit`.
- Không thêm khóa bí mật mới khi chưa được duyệt.
- Thêm hoặc sửa tệp trong thư mục này: máy quét trước khi đẩy chặn (QĐ293), chỉ cho qua khi ghi số QĐ.

## 4. Được chứa / không được chứa

- Được: tệp `.yml` luồng đã duyệt, tệp hướng dẫn này.
- Không: tệp luồng thử để lâu dài, khóa, địa chỉ máy chủ, lệnh vào máy chủ.

## 5. Quyết định đã chốt – không tự đảo

- QĐ229: SQLite trong ảnh phải từ 3.43 trở lên, thấp hơn thì không đẩy ảnh.
- QĐ215: thử khởi động bản này và bản trước trong ảnh rồi mới đẩy.
- QĐ258: main đẩy nhãn `latest`, nhãn commit và nhãn số bản; đọc thêm bộ nhớ đệm gắn trong ảnh `latest`.
- QĐ259, QĐ266, QĐ270: danh sách chặn ở `.github/cua/kiem_sualoi.py`; mục THAYDOI khuôn "Sửa lỗi …".
- QĐ293: chủ mã giữ `/.github/`.

## 6. Kiểm trước bàn giao

- `kiemthu/ban082/test_y44.py` đạt (cửa chặn, quét chung, tệp luồng tự gộp, bước kiểm N5).
- Lượt chạy thật trên nhánh thử trước khi gộp; đọc chú thích "Ket qua bai kiem" (đúng 01).

## 7. Người giữ

CTO viết và giữ; CDA soát danh sách chặn; CPO nghiệm thu.
