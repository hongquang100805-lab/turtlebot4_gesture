"""Save genuine desktop frames from the active recording at navigation milestones."""
import cv2
import json
from pathlib import Path
import time
base=Path(__file__).resolve().parent
out=base/'report_images'
seen=set()
started=time.time()
def capture(name):
    path=Path((base/'recording_path.txt').read_text().strip())
    cap=cv2.VideoCapture(str(path));last=None;count=0
    while True:
        ok,frame=cap.read()
        if not ok:break
        count+=1;last=frame
    cap.release()
    if last is None:return
    cv2.imwrite(str(out/name),last)
    with (base/'capture_events.jsonl').open('a') as f:
        f.write(json.dumps({'file':name,'wall_time':time.time(),'frames_decoded':count,'video':path.name})+'\n')
    print('Saved',name,'at',count,'frames',flush=True)
while not (base/'stop_evidence').exists():
    try:
        r=json.loads((base/'results.json').read_text())
    except (FileNotFoundError,json.JSONDecodeError):
        time.sleep(2);continue
    for i,g in enumerate(r.get('goals',[]),1):
        key=f'{i}_{g["status"]}'
        if g['status']=='SUCCEEDED' and key not in seen:
            time.sleep(2)
            capture(f'goal_{i}_succeeded.png');seen.add(key)
        if g['status']=='ACCEPTED' and f'{i}_path' not in seen:
            # Let the global path appear, then capture while the robot is moving.
            time.sleep(8)
            capture(f'goal_{i}_navigation.png');seen.add(f'{i}_path')
    if r.get('status') in ('SUCCEEDED','FAILED','INTERRUPTED'):
        time.sleep(3);capture('09_final_results.png');break
    time.sleep(3)
