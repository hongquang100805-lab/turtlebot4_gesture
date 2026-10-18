from pathlib import Path
import json,cv2
import gi
import numpy as np
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
b=Path(__file__).resolve().parent;root=b.parent
r=json.loads((b/'parsed_log.json').read_text());v=json.loads((root/'video_validation.json').read_text())
video=root/v['file']; start=video.stat().st_mtime-v['duration_seconds']
targets=[]
for name,records in r['classes'].items():
 if name not in ('fire hydrant','refrigerator','tv'):continue
 best=max(records,key=lambda x:x['confidence'])
 for delta in [round(i*.2,1) for i in range(-10,11)]:
  targets.append({'name':name,'confidence':best['confidence'],'log_time':best['time'],'seconds':best['time']-start+delta,'delta':delta})
targets.sort(key=lambda x:x['seconds']);idx=0
(b/'examples').mkdir(exist_ok=True)
p=Gst.parse_launch(f'filesrc location="{video}" ! matroskademux ! vp8dec ! videoconvert ! video/x-raw,format=BGR ! appsink name=sink sync=false')
sink=p.get_by_name('sink');p.set_state(Gst.State.PLAYING)
try:
 while idx<len(targets):
  sample=sink.emit('pull-sample')
  if sample is None:break
  buf=sample.get_buffer();sec=buf.pts/Gst.SECOND
  if sec<targets[idx]['seconds']:continue
  caps=sample.get_caps().get_structure(0);w=caps.get_value('width');h=caps.get_value('height');data=buf.extract_dup(0,buf.get_size());frame=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)
  while idx<len(targets) and sec>=targets[idx]['seconds']:
   t=targets[idx];stem=t['name'].replace(' ','_')+f'_{t["delta"]:+.1f}';cv2.imwrite(str(b/'examples'/f'{stem}.png'),frame)
   t['video_pts']=sec;t['file']=f'examples/{stem}.png';idx+=1
finally:p.set_state(Gst.State.NULL)
(b/'transient_timestamps.json').write_text(json.dumps(targets,indent=2))

for name in ('fire hydrant','refrigerator','tv'):
 canvas=np.zeros((5*280,5*320,3),np.uint8)
 for i,d in enumerate([round(v*.2,1) for v in range(-10,11)]):
  im=cv2.imread(str(b/'examples'/(name.replace(' ','_')+f'_{d:+.1f}.png')))
  tile=cv2.resize(im[80:650,1280:1920],(320,280))
  cv2.putText(tile,f'{d:+.1f}s',(5,270),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),1)
  canvas[(i//5)*280:(i//5+1)*280,(i%5)*320:(i%5+1)*320]=tile
 cv2.imwrite(str(b/('transient_'+name.replace(' ','_')+'.jpg')),canvas)
print('Transient screenshots extracted.')
