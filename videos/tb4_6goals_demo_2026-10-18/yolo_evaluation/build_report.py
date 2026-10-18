"""Report sampled live YOLO observations without inventing per-frame ground truth."""
import csv
from datetime import datetime
from pathlib import Path
import json
import shutil
import statistics
from zoneinfo import ZoneInfo
import cv2

base=Path(__file__).resolve().parent
raw=json.loads((base/'parsed_log.json').read_text())
all_examples=json.loads((base/'example_timestamps.json').read_text())+json.loads((base/'transient_timestamps.json').read_text())
reviews={
 'person':('Đúng trong ảnh minh chứng','Mô hình người có hình dạng, vị trí và bounding box phù hợp. Chưa gán nhãn thủ công toàn bộ các box person.',0.0),
 'chair':('Sai trong ảnh minh chứng','Nhãn chair bao quanh các thùng đỏ trên kệ, không phải ghế.',0.7),
 'cup':('Sai trong ảnh minh chứng','Nhãn cup bao quanh thùng chứa màu xanh trên kệ, không phải cốc.',0.0),
 'airplane':('Sai trong ảnh minh chứng','Xe nâng tay màu vàng bị gán nhãn airplane.',0.7),
 'umbrella':('Sai trong ảnh minh chứng','Bộ phận màu đen phía trên ảnh bị gán nhãn umbrella; không phải ô.',0.7),
 'fire hydrant':('Chưa đủ tin cậy','Box rất nhỏ gần chân kệ; ảnh không đủ rõ để xác nhận trụ nước. Chỉ có một mẫu log, confidence 0.28.',0.2),
 'refrigerator':('Sai trong ảnh minh chứng','Cột đứng của nhà kho bị gán nhãn refrigerator.',0.2),
 'tv':('Sai trong ảnh minh chứng','Vùng kệ và nền nhà kho bị gán nhãn tv, không có màn hình TV trong box.',0.2),
 'skateboard':('Sai trong ảnh minh chứng','Vật thể màu vàng sát nền (xe nâng tay trong kho) bị gán nhãn skateboard.',0.7),
}
order=sorted(raw['classes'],key=lambda k:-len(raw['classes'][k]))
(base/'evidence').mkdir(exist_ok=True)
rows=[]
for name in order:
 vals=raw['classes'][name];verdict,note,delta=reviews[name]
 item=next(x for x in all_examples if x['name']==name and x['delta']==delta)
 stem=name.replace(' ','_')
 original=base/item['file'];full=base/'evidence'/f'{stem}_screen.png';shutil.copyfile(original,full)
 frame=cv2.imread(str(full));cv2.imwrite(str(base/'evidence'/f'{stem}_camera.png'),frame[85:565,1280:1920])
 cs=[v['confidence'] for v in vals]
 rows.append({'class':name,'logged_boxes':len(vals),'logged_samples':len(set(v['time'] for v in vals)),
              'confidence_min':min(cs),'confidence_mean':round(statistics.mean(cs),3),'confidence_max':max(cs),
              'example_review':verdict,'review_note':note,'image':f'evidence/{stem}_camera.png',
              'original_screenshot':f'evidence/{stem}_screen.png','video_pts_seconds':item['video_pts']})
with (base/'yolo_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(base/'reviewed_examples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
start=datetime.fromtimestamp(raw['start'],ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%H:%M:%S')
end=datetime.fromtimestamp(raw['end'],ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%H:%M:%S')
md=['# Phân tích YOLO trong lần chạy tự động qua 6 goal','',
    '## Phạm vi và cách đếm','',
    f'Phân tích từ lúc gửi Goal 1 đến khi Goal 6 thành công: {start}–{end} ngày 18/10/2026 (giờ Việt Nam), khoảng {raw["end"]-raw["start"]:.1f} giây thực.',
    'Dữ liệu lấy từ yolo.log của lần chạy thật, đối chiếu với video TurtleBot4_6Goals_Nav2_YOLO.webm.',
    'YOLO11n, CPU, confidence threshold 0.25; camera RGB 320×240, giới hạn suy luận 2 khung hình/giây.','',
    f'Có **{raw["sampled_frames"]} mẫu kết quả được in ra log**, trong đó **{raw["empty_frames"]} mẫu không có detection**, **{raw["sampled_frames"]-raw["empty_frames"]} mẫu có detection**, tổng cộng **{sum(len(v) for v in raw["classes"].values())} bounding box** thuộc **{len(rows)} lớp**.',
    'Log được giới hạn khoảng một dòng mỗi 2 giây. Vì vậy, đây là thống kê mẫu log, KHÔNG phải tổng detection của tất cả ảnh trong phiên chạy.',
    'Một vật thể có thể được nhận diện lặp lại ở nhiều mẫu. Một mẫu có thể có nhiều box cùng lớp. Số box không phải số vật thể duy nhất.',
    'Tóm tắt perception_summary.json của TOÀN PHIÊN (cả trước và sau chuỗi goal) ghi 1013 kết quả ảnh nhận được, 418 ảnh có detection và 14 lớp từng xuất hiện. File này không lưu số box theo lớp và không cho phép suy ra số lần từng lớp trong toàn bộ ảnh. Không trộn hai phạm vi dữ liệu này.','',
    '## Bảng thống kê và đối chiếu ảnh','',
    '| Lớp YOLO | Số box trong log | Số mẫu có lớp | Confidence min–max | Nhận xét ảnh minh chứng |',
    '|---|---:|---:|---|---|']
for r in rows:
 md.append(f'| {r["class"]} | {r["logged_boxes"]} | {r["logged_samples"]} | {r["confidence_min"]:.2f}–{r["confidence_max"]:.2f} | {r["example_review"]} |')
md.extend(['','**Cách hiểu nhận xét:** kết luận đúng/sai áp dụng cho ảnh đã đối chiếu, không gán toàn bộ box của lớp đó là TP hay FP. Chưa có ground truth cho từng box nên không báo cáo precision, recall, mAP hoặc tỷ lệ chính xác.',
           'Các ảnh được trích quanh thời điểm mẫu log trong video. Camera và text JSON là hai topic cập nhật độc lập; ảnh lân cận có thể có confidence khác mẫu log. Confidence trên ảnh không được dùng thay cho số liệu bảng.',
           'Confidence cao vẫn có thể đi cùng nhận diện sai; số lần lặp lại nhiều cũng không chứng minh lớp đó đúng.','',
           '## Ảnh minh chứng từng lớp',''])
for r in rows:
 md.extend([f'### {r["class"]}: {r["example_review"]}',r['review_note'],
            f'Ảnh trong video tại khoảng {r["video_pts_seconds"]:.2f} giây. [Ảnh màn hình gốc]({r["original_screenshot"]}).',
            f'![{r["class"]}]({r["image"]})',''])
md.extend(['## Nhận xét đưa vào báo cáo','',
    'Trong môi trường mô phỏng depot, YOLO11n có thể phát hiện mô hình người khi người nằm trong góc nhìn và đủ rõ. Các ảnh đối chiếu đồng thời cho thấy nhiều nhận diện nhầm trên thùng chứa, kệ và cột. Việc gán nhãn lặp lại ở nhiều thời điểm không đồng nghĩa phát hiện thêm nhiều vật thể khác nhau.',
    'Nguyên nhân cần được trình bày như giả thuyết: khác biệt hình ảnh mô phỏng so với dữ liệu huấn luyện, độ phân giải camera nhỏ, vật thể bị che khuất và góc nhìn thay đổi khi robot quay. Lần chạy này chưa có thí nghiệm riêng để định lượng ảnh hưởng từng yếu tố.',
    'YOLO chỉ phục vụ nhận diện/hiển thị; chương trình không dùng nhãn YOLO để quyết định tránh vật cản. Robot lập đường và tránh vật cản bằng Nav2 cùng dữ liệu cảm biến. Navigation 6/6 thành công không phải bằng chứng YOLO phân loại chính xác.',
    'Hướng cải thiện: lưu JSON của mọi kết quả cùng ảnh và timestamp; gán nhãn một tập ảnh đại diện; so sánh ngưỡng confidence trên cùng tập ảnh; cân nhắc tăng độ phân giải hoặc fine-tune bằng ảnh mô phỏng. Với lớp cần cho bài như person, có thể lọc danh sách lớp hiển thị, nhưng việc lọc không tự cải thiện chất lượng nhận diện hay chứng minh các nhãn còn lại đúng.'])
(base/'PHAN_TICH_YOLO.md').write_text('\n'.join(md)+'\n')

# This section uses only standard LaTeX tables and graphicx, suitable for an existing pdfLaTeX report.
tex=[r'\section{Đánh giá nhận diện vật thể bằng YOLO}',
     r'\subsection{Thiết lập và phạm vi thống kê}',
     'Hệ thống sử dụng YOLO11n với ngưỡng confidence 0,25, camera RGB độ phân giải '+r'$320\times240$'+', suy luận trên CPU và giới hạn 2 ảnh/giây. Robot thực hiện tuần tự 6 goal bằng node ROS 2.',
     f'Khoảng thống kê từ {start} đến {end} ngày 18/10/2026, tương ứng thời điểm gửi Goal 1 đến khi Goal 6 thành công. Log chỉ in khoảng một kết quả mỗi 2 giây. Có 160 mẫu log, gồm 109 mẫu rỗng và 51 mẫu có detection, tổng cộng 94 bounding box thuộc 9 lớp.',
     r'\textbf{Số liệu dưới đây là số box trong mẫu log, không phải tổng detection của mọi khung hình hoặc số vật thể duy nhất.} Một vật thể có thể được đếm nhiều lần khi xuất hiện ở nhiều mẫu.',
     r'\begin{table}[htbp]\centering\small',r'\caption{Thống kê lớp nhận diện trong 160 mẫu log của chuỗi 6 goal.}',
     r'\begin{tabular}{lrrcl}\hline',r'Lớp & Số box & Số mẫu & Conf. min--max & Ảnh đối chiếu \\ \hline']
for r in rows:
 verdict='Đúng (ảnh mẫu)' if r['class']=='person' else ('Chưa tin cậy' if r['class']=='fire hydrant' else 'Sai (ảnh mẫu)')
 tex.append(f'{r["class"]} & {r["logged_boxes"]} & {r["logged_samples"]} & {r["confidence_min"]:.2f}--{r["confidence_max"]:.2f} & {verdict} '+r'\\')
tex.extend([r'\hline\end{tabular}\end{table}',
            'Kết luận đúng/sai chỉ áp dụng cho các ảnh đã kiểm tra. Chưa gán nhãn từng box trong toàn bộ video nên không tính precision, recall hay mAP. Confidence trên ảnh minh họa có thể khác thống kê log vì ảnh được trích tại thời điểm lân cận.',
            r'\subsection{Đối chiếu ảnh thực nghiệm}'])
for r in rows:
 caption=r['review_note'].replace('_',r'\_')
 tex.extend([r'\begin{figure}[htbp]\centering',r'\includegraphics[width=0.72\linewidth]{'+r['image']+'}',r'\caption{'+r['class']+': '+caption+'}',r'\end{figure}'])
tex.extend([r'\clearpage',r'\subsection{Nhận xét và hạn chế}',
 'Ảnh minh chứng cho thấy hệ thống phát hiện được mô hình người, đồng thời có nhiều nhận diện nhầm trên thùng chứa và kết cấu kho. Các mẫu rỗng không tự chứng minh bỏ sót vì có thể không có đối tượng phù hợp trong góc nhìn. Không suy ra số đối tượng thực tế bằng cách cộng số bounding box qua các mẫu.',
 'Khác biệt ảnh mô phỏng so với dữ liệu huấn luyện, độ phân giải nhỏ, che khuất và góc nhìn thay đổi là các giả thuyết có thể ảnh hưởng kết quả; chưa có thí nghiệm riêng để định lượng từng yếu tố.',
 'YOLO chạy song song để nhận diện và hiển thị, không điều khiển tránh vật cản. Kết quả 6/6 goal thành công xác nhận hoạt động navigation; không thay thế đánh giá độ chính xác của YOLO.',
 'Cần lưu đầy đủ JSON và ảnh theo timestamp, gán nhãn một tập đánh giá đại diện, rồi so sánh các ngưỡng confidence hoặc mô hình trên cùng tập dữ liệu trước khi kết luận chất lượng được cải thiện.'])
(base/'yolo_section.tex').write_text('\n'.join(tex)+'\n')
(base/'yolo_analysis.tex').write_text(r'''\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T5]{fontenc}
\usepackage[vietnamese]{babel}
\usepackage[margin=2cm]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\begin{document}
\input{yolo_section.tex}
\end{document}
''')
print('Generated statistics, reviewed screenshots, Markdown, and pdfLaTeX source.')
