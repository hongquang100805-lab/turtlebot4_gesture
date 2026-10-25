# Báo cáo Bài thực hành 6 — pdfLaTeX

## Mở trên Overleaf

1. Tải toàn bộ ZIP mã nguồn báo cáo lên dự án, giữ `main.tex` và thư mục `images/` cùng cấp.
2. Chọn `main.tex` làm file chính, compiler **pdfLaTeX**.
3. Recompile; hệ thống có thể cần chạy lại để cập nhật mục lục và số hình.
4. Sửa các trường `[ ... ]` trên trang bìa: tên trường/khoa, học phần, giảng viên, sinh viên, mã số và lớp. Có thể sửa `pdfauthor` trong `\hypersetup`.

Không chỉ dán riêng main.tex vào một dự án trống vì sẽ thiếu ảnh. Báo cáo dùng UTF-8, font encoding T5 và Babel tiếng Việt; không dùng fontspec/XeLaTeX, minted hoặc lệnh cần shell-escape. Các sơ đồ được vẽ trực tiếp bằng TikZ, không cần phần mềm ngoài khi biên dịch. Không có danh mục hình ảnh.

## Biên dịch khi đã có TeX Live đầy đủ

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Các gói cần thiết là những gói TeX Live thông dụng, bao gồm hỗ trợ tiếng Việt (vntex/babel-vietnamese), TikZ/PGF, graphicx, booktabs, tabularx, caption/subcaption, listings, hyperref và xurl.

## Nội dung và nguồn số liệu

Bản cô đọng gồm 13 trang (bản trước 18 trang), giữ cỡ chữ phần thân 12 pt. Bảy chương: giới thiệu; kiến trúc và cấu trúc mã nguồn; nhận diện MediaPipe và Wave; điều khiển; triển khai và câu lệnh; kết quả thực nghiệm; kết luận.

Chương 2 có cây thư mục kèm chức năng ngắn của từng file. Luồng hệ thống, luồng xử lý ảnh, phân biệt Wave và máy trạng thái được trình bày bằng sơ đồ. Ba đồ thị chuyển động được gộp thành một hình tổng quan; phần tham số và kết quả dùng bảng để dễ đối chiếu. Tài liệu tham khảo dùng các nguồn chính thức. Trang bìa để thông tin mẫu.

Ảnh và đồ thị lấy từ lượt webcam thật ngày 24/10/2026. Video MP4 gốc nằm ở `artifacts/lab06_demo_2026-10-24_take01/demo_turtlebot4_gestures.mp4` trong workspace; video không đưa vào ZIP LaTeX để giảm dung lượng. Các file `data/` giữ lại bảng kết quả và các giá trị đã dùng trong phân tích; chúng không phải đầu vào bắt buộc của LaTeX.

Lưu ý về kết quả:

- Sáu cảnh đạt sau quá trình thao tác; có một lần lựa chọn Wave bị xóa và một lần mất tín hiệu ngoài ý muốn khi chuyển sang Open Palm.
- Confidence trong bảng là điểm của ảnh mẫu, không phải tỷ lệ đúng trên tập kiểm thử.
- Confidence Wave là điểm Open Palm kết hợp điều kiện chuyển động, không phải một bộ phân loại Wave độc lập.
- Đồ thị lấy từ /odom; bán kính khớp và độ khép kín trong odom chưa phải sai số so với ground truth.
- Thời gian chạy 29,85 / 35,70 / 5,15 giây là đồng hồ thực của ba hành vi thành công, không phải thời gian mô phỏng.
- Video không có cảnh riêng giơ Thumb Up sau khi dừng/mất tín hiệu; báo cáo không nhận là đã quay cảnh đó.

PDF đã được biên dịch bằng pdfTeX/pdfLaTeX, không chuyển từ Word hoặc HTML.
