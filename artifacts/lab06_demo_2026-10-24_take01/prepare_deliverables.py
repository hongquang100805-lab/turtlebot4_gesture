from pathlib import Path
import collections,csv,json,shutil,statistics,subprocess,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/tmp/lab06_video_tools');import imageio_ffmpeg
B=Path(__file__).resolve().parent;F=B/'report_images';F.mkdir(exist_ok=True)
exe=imageio_ffmpeg.get_ffmpeg_exe();video=B/'demo_turtlebot4_gestures.mp4'
reader=imageio_ffmpeg.read_frames(str(video));metadata=next(reader);reader.close()
(B/'video_metadata.json').write_text(json.dumps(metadata,indent=2))
assert metadata['duration']>170 and tuple(metadata['size'])==(1920,1080)
with (B/'decode_check.log').open('w') as f:
 check=subprocess.run([exe,'-v','error','-i',str(video),'-f','null','-'],stdout=f,stderr=subprocess.STDOUT)
assert check.returncode==0
E=[json.loads(l) for l in (B/'events.jsonl').read_text().splitlines()]
O=[json.loads(l) for l in (B/'odometry.jsonl').read_text().splitlines()]
S=json.loads((B/'summary.json').read_text())
offset=statistics.median(e['wall_seconds']-int(e['file'].split('_')[0])/1000 for e in E if e['kind']=='screenshot')
# Frames come directly from the real recorded video, with no altered gesture labels.
shots=[('01_ready_overview',9.0),('02_selected_before_confirmation',14.0),('03_backforth_running',30.0),('04_backforth_completed',48.5),('05_circle_running',75.0),('06_circle_completed',94.2),('07_greeting_running',112.0),('08_greeting_completed',116.0),('09_open_palm_stopped',145.2),('10_closed_fist_idle',159.0),('11_signal_lost',173.0)]
for name,t in shots:
 subprocess.run([exe,'-y','-loglevel','error','-ss',str(t),'-i',str(video),'-frames:v','1',str(F/(name+'.png'))],check=True)
for gesture in S['observed_gestures']:
 shutil.copy2(B/'images'/('webcam_'+gesture+'.png'),F/('gesture_'+gesture+'.png'))
# Plot actual odometry only within successful full-motion intervals.
intervals={}
for stage in [1,2,3]:
 ev=[e for e in E if e['kind']=='robot_state' and e.get('stage')==stage]
 end=next(e['wall_seconds'] for e in ev if e['data']['state']=='COMPLETED')
 start=max(e['wall_seconds'] for e in ev if e['data']['state']=='RUNNING' and e['data']['step']==1 and e['wall_seconds']<end)
 intervals[stage]=(start-offset,end-offset)
 def dataset():return [r for r in O if start-offset<=r['seconds']<=end-offset]
 rows=dataset();t=np.array([r['seconds'] for r in rows]);t-=t[0]
 x=np.array([r['x'] for r in rows]);y=np.array([r['y'] for r in rows])
 fig,ax=plt.subplots(figsize=(7,4.3),layout='constrained')
 if stage==1:
  ax.plot(t,x-x[0],lw=2);ax.set(xlabel='Thời gian thực (s)',ylabel='Vị trí x tương đối (m)',title='Bốn chu kỳ tiến–lùi — dữ liệu /odom thực tế')
 elif stage==2:
  ax.plot(x,y,lw=2,label='Quỹ đạo đo được');ax.scatter([x[0]],[y[0]],s=45,label='Bắt đầu');ax.scatter([x[-1]],[y[-1]],s=45,marker='x',label='Kết thúc');ax.set_aspect('equal',adjustable='datalim');ax.legend();ax.set(xlabel='x trong odom (m)',ylabel='y trong odom (m)',title='Một vòng tròn — dữ liệu /odom thực tế')
 else:
  yaw=np.unwrap(np.array([np.arctan2(2*r['qw']*r['qz'],1-2*r['qz']**2) for r in rows]));ax.plot(t,yaw-yaw[0],lw=2);ax.set(xlabel='Thời gian thực (s)',ylabel='Góc quay tương đối (rad)',title='Động tác chào — dữ liệu /odom thực tế')
 ax.grid(alpha=.3);fig.savefig(F/f'odom_{stage}.png',dpi=180);fig.savefig(F/f'odom_{stage}.pdf');plt.close(fig)
retries=collections.Counter(e['stage'] for e in E if e['kind']=='attempt_interrupted')
with (B/'results.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['stage','behavior','result','video_seconds','interrupted_attempts'])
 for r in S['completed_stages']:w.writerow([r['stage'],r['behavior'],r['result'],r['at_seconds'],retries[r['stage']]])
(B/'measured_motion_intervals.json').write_text(json.dumps({'clock_offset_seconds':offset,'motion_intervals_video_clock':intervals,'note':'Wall-clock duration, not simulation time.'},indent=2))
print(json.dumps({'metadata':metadata,'report_image_count':len(list(F.glob('*.png'))),'retries':dict(retries),'intervals':intervals},indent=2))
