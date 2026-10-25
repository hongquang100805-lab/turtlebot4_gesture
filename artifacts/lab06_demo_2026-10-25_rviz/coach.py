import json,sys
from pathlib import Path
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import QApplication,QLabel
base=Path(__file__).resolve().parent
app=QApplication(sys.argv);label=QLabel('Đang chuẩn bị ghi hình — để tay ngoài webcam')
label.setWindowTitle('Lab 06 - Huong dan quay demo')
label.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
label.setAlignment(Qt.AlignCenter);label.setWordWrap(True)
label.setStyleSheet('background:#102334;color:white;font-size:21px;padding:8px;border:2px solid #32c2a2;')
screen=app.primaryScreen().geometry();label.setGeometry(0,30,screen.width(),82);label.show()
def tick():
 try:
  data=json.loads((base/'cue.json').read_text());label.setText(data['text'])
 except (OSError,ValueError):pass
 if (base/'coach_stop').exists():app.quit()
timer=QTimer();timer.timeout.connect(tick);timer.start(200);sys.exit(app.exec_())
