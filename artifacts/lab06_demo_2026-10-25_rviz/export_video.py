import json, subprocess, shutil, zipfile, hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
ff=Path('/tmp/lab06_video_tools/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')
s=json.loads((p/'summary.json').read_text())
if not s['all_six_stages_completed']:raise SystemExit('Recording is incomplete; preserve raw video and inspect results.')
mp4=p/'demo_turtlebot4_gestures_rviz.mp4'
with (p/'export.log').open('w') as log:
 subprocess.run([str(ff),'-y','-i',str(p/'demo_turtlebot4_gestures.webm'),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart','-an',str(mp4)],stdout=log,stderr=subprocess.STDOUT,check=True)
with (p/'decode_check.log').open('w') as log:
 subprocess.run([str(ff),'-v','error','-i',str(mp4),'-f','null','-'],stdout=log,stderr=subprocess.STDOUT,check=True)
selected=p/'screenshots';selected.mkdir(exist_ok=True)
patterns=['*00_ready_overview.png','*01_selected.png','*01_completed_visible.png','*02_completed_visible.png','*03_running_visible.png','*03_completed_visible.png','*04_stopped_visible.png','*05_idle_visible.png','*06_signal_lost_visible.png']
for pattern in patterns:
 for image in sorted((p/'images').glob(pattern))[-1:]:shutil.copy2(image,selected/image.name)
for image in (p/'images').glob('webcam_*.png'):shutil.copy2(image,selected/image.name)
with zipfile.ZipFile(p/'anh_minh_chung_rviz.zip','w',zipfile.ZIP_DEFLATED) as z:
 for image in sorted(selected.glob('*.png')):z.write(image,'screenshots/'+image.name)
(p/'checksums.json').write_text(json.dumps({'mp4_sha256':hashlib.sha256(mp4.read_bytes()).hexdigest(),'decode_ok':True,'all_six_stages_completed':True,'screenshots':len(list(selected.glob('*.png')))},indent=2))
print(json.dumps({'video':str(mp4),'bytes':mp4.stat().st_size,'results':s['completed_stages'],'screenshots':len(list(selected.glob('*.png')))},ensure_ascii=False,indent=2))
