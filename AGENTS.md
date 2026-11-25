# AGENTS.md – gốc kho IGM360

Tệp hướng dẫn cho AI làm mã trong kho này (QĐ269, QĐ272). Trước khi sửa tệp ở thư mục nào: đọc tệp này và AGENTS.md của thư mục đó.

## 1. Vai thư mục

Gốc kho mã IGM360: phần mềm quản trị vận hành chạy 01 vùng chứa Docker trên máy chủ, ảnh đóng ở GHCR, máy chủ chỉ kéo ảnh về.

Thư mục không có tệp riêng thì đọc tệp của thư mục cha gần nhất có tệp. Tệp này dùng cho: `.github` (gồm `CODEOWNERS`), `.github/cua` (công cụ cửa chặn tự gộp), `tailieu`.

## 2. Đọc gì trước

- `VERSION` (số bản đang làm), `THAYDOI.md` (mỗi bản 01 mục: "Tóm tắt:", "Nâng dữ liệu: có/không", các dòng "- ").
- `Dockerfile` (ảnh nền ghim theo sha256, 02 CLI ghim bằng ARG, thứ tự lớp ít đổi trước – hay đổi sau, QĐ258).
- `docker-compose.yml`, `.dockerignore`, `requirements.txt`.
- AGENTS.md của thư mục sắp sửa.

## 3. Luật bắt buộc

- Không đặt CLAUDE.md trong kho mã (QĐ269).
- Kho công khai: không địa chỉ IP, tên máy chủ, đường dẫn ổ đĩa máy cá nhân, email, khóa bí mật; không tài liệu thiết kế nghiệp vụ; không dữ liệu khách hàng.
- Quét thông tin nhạy cảm là 01 bước riêng trước khi đẩy kho, đọc kết quả rồi mới đẩy.
- Thư viện, phần mềm cài thêm (requirements.txt, Dockerfile) phải được duyệt trước.
- Chữ người dùng thấy: tiếng Việt có dấu; số 1–9 trước danh từ đếm ghi 02 chữ số; mọi chữ viết dấu kiểu mới (xóa, khóa, hóa, hủy – QĐ304; Y50 đổi toàn kho theo QĐ298, QĐ302).
- Không viết chữ cấm (tên mã gốc) trong maychu, kiemthu, mauketnoi (bài kiểm `kiemthu/test_chucam.py`).
- Đổi số bản: sửa `VERSION` và thêm mục mới đầu `THAYDOI.md`; mục cũ không đổi dòng "Nâng dữ liệu".
- Quy ước số bản (QĐ396): số đầu giữ 0; bản có tính năng mới: +1 số giữa, số cuối về 0 (0.9.0, 0.10.0); bản chỉ sửa lỗi: +1 số cuối (0.8.10, 0.9.1); mỗi lần gộp `main` = 01 bản. Máy cập nhật so từng phần số (`capnhat._khoa_so`, `tiendo.da_len`) nên số giữa lớn dần không cần đổi mã.
- Tên tệp, thư mục, hàm, biến: tiếng Việt không dấu.
- `.github/cua`: chỉ thư viện chuẩn Python; chỉ đọc phần đổi bằng git, không chạy mã của nhánh; in loại và vị trí, không in giá trị nhạy cảm.
- `.github/CODEOWNERS`: không đổi người giữ `/.github/` khi chưa có QĐ (QĐ293, QĐ294).
- `tailieu`: chỉ tài liệu kỹ thuật công khai; sửa riêng thư mục này không chạy máy GitHub.

## 4. Được chứa / không được chứa

- Được: mã phần mềm (`maychu`), bài kiểm (`kiemthu`), tệp luồng GitHub (`.github`), tài liệu kỹ thuật công khai (`tailieu`).
- Không: dữ liệu thật, bản sao lưu, tệp khóa, nhật ký máy chủ, tài liệu nghiệp vụ nội bộ (chỉ ghi "tài liệu thiết kế nội bộ, hỏi người giữ").

## 5. Quyết định đã chốt – không tự đảo

- QĐ258: ghim ảnh nền theo sha256 và ghim 02 CLI; đổi thứ tự lớp phải đo lại số MB tải.
- QĐ259, QĐ266: chỉ nhánh `sualoi/*` qua cửa chặn mới tự gộp main; tính năng, dữ liệu, chữ, giao diện là bản loại 2 (soát, duyệt gộp).
- QĐ269, QĐ272: 14 tệp AGENTS.md; AI đọc bằng luật đọc bắt buộc.
- QĐ289: luật bảo vệ main không khóa tài khoản quản trị.

## 6. Kiểm trước bàn giao

- `python -m unittest discover -s kiemthu -t .` đạt (trên Windows chỉ còn các lỗi đã biết do quyền tệp, lệnh hệ điều hành).
- 0 lần gọi CLI thật trong bài kiểm.
- Quét nhạy cảm ĐẠT 0; máy GitHub "Kiểm và đóng image (GHCR)" xanh.

## 7. Người giữ

CTO viết và giữ; CDA soát phần dữ liệu, CDO soát phần giao diện; CPO nghiệm thu.
