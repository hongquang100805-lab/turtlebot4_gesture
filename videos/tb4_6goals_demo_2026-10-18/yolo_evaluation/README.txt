Phần bổ sung phân tích YOLO cho báo cáo 6 goal.

Đọc PHAN_TICH_YOLO.md trước để hiểu phạm vi đếm.
yolo_summary.csv: mở bằng Excel, UTF-8 BOM.
yolo_section.tex: phần nội dung để ghép vào báo cáo LaTeX.
yolo_analysis.tex: bản độc lập; chạy pdflatex trong thư mục này (cần bộ hỗ trợ tiếng Việt T5/vietnamese và graphicx).
Máy hiện tại không có pdflatex trong PATH, nên bộ này chỉ cung cấp mã nguồn LaTeX; chưa có PDF biên dịch.

evidence/*_camera.png: cắt vùng camera từ video thật, giữ nguyên nhãn và box do YOLO vẽ.
evidence/*_screen.png: ảnh màn hình gốc tương ứng.
reviewed_examples.json: nhận xét thủ công theo ảnh mẫu và timestamp video.
parsed_log.json: thống kê các mẫu log trong khoảng gửi Goal 1 đến Goal 6 SUCCEEDED.
yolo.log: log nguồn đầy đủ.

Không dùng số box trong bảng làm số người/đồ vật duy nhất, hoặc coi nhận xét ảnh mẫu là nhãn ground truth cho mọi detection.
