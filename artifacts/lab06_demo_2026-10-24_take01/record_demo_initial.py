"""Real Wayland screen recording; ROS subscriptions only, no robot commands."""
import json,os,signal,threading,time,uuid
from pathlib import Path
import cv2,numpy as np,gi

gi.require_version('Gst','1.0')
from gi.repository import Gio,GLib,Gst
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy,qos_profile_sensor_data
from std_msgs.msg import String
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry

BASE=Path(__file__).resolve().parent;IMAGE_DIR=BASE/'images';IMAGE_DIR.mkdir(exist_ok=True)
Gst.init(None);bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
PORTAL='org.freedesktop.portal.Desktop';PATH='/org/freedesktop/portal/desktop';IFACE='org.freedesktop.portal.ScreenCast'
events=(BASE/'events.jsonl').open('a',buffering=1);started=time.monotonic()
def log(kind,**data):
 row={'wall_seconds':round(time.monotonic()-started,3),'kind':kind,**data};events.write(json.dumps(row,ensure_ascii=False)+'\n')
 print(json.dumps(row,ensure_ascii=False),flush=True)
def cue(text):
 (BASE/'cue.json').write_text(json.dumps({'text':text},ensure_ascii=False));log('cue',text=text)
def request(method,args,signature):
 token='lab06_'+uuid.uuid4().hex
 args[-1]['handle_token']=GLib.Variant('s',token)
 path=PATH+'/request/'+bus.get_unique_name()[1:].replace('.','_')+'/'+token
 loop=GLib.MainLoop();answer=[]
 def response(connection,sender,obj,interface,name,params):
  answer.append(params.unpack());loop.quit()
 sub=bus.signal_subscribe(PORTAL,'org.freedesktop.portal.Request','Response',path,None,Gio.DBusSignalFlags.NONE,response)
 bus.call_sync(PORTAL,PATH,IFACE,method,GLib.Variant(signature,tuple(args)),None,Gio.DBusCallFlags.NONE,5000,None)
 loop.run();bus.signal_unsubscribe(sub)
 if not answer or answer[0][0]!=0:raise RuntimeError('ScreenCast request cancelled: '+str(answer))
 return answer[0][1]

cue('CHUẨN BỊ — Để tay ngoài webcam. Chọn màn hình và bấm CHIA SẺ khi hộp thoại xuất hiện.')
session=request('CreateSession',[{'session_handle_token':GLib.Variant('s','lab06_'+uuid.uuid4().hex)}],'(a{sv})')['session_handle']
request('SelectSources',[session,{'types':GLib.Variant('u',1),'multiple':GLib.Variant('b',False),'cursor_mode':GLib.Variant('u',1)}],'(oa{sv})')
stream=request('Start',[session,'',{}],'(osa{sv})')['streams'][0]
reply,fds=bus.call_with_unix_fd_list_sync(PORTAL,PATH,IFACE,'OpenPipeWireRemote',GLib.Variant('(oa{sv})',(session,{})),GLib.VariantType.new('(h)'),Gio.DBusCallFlags.NONE,5000,None,None)
fd=fds.get(reply.unpack()[0]);node_id=stream[0];log('portal_granted',node_id=node_id,properties=stream[1])
output=BASE/'demo_turtlebot4_gestures.webm'
pipeline=Gst.parse_launch(f'pipewiresrc name=source fd={fd} path={node_id} do-timestamp=true ! videoconvert ! videorate ! video/x-raw,framerate=20/1 ! tee name=t t. ! queue ! vp8enc deadline=1 cpu-used=8 threads=4 target-bitrate=5000000 keyframe-max-dist=40 ! webmmux ! filesink location="{output}" t. ! queue leaky=downstream max-size-buffers=1 ! videoconvert ! video/x-raw,format=BGR ! appsink name=frames emit-signals=true max-buffers=1 drop=true sync=false')
latest=None;frame_lock=threading.Lock();frames=0;finished=False;record_start=time.monotonic();state={};debug={};last_gesture='None';last_image=None;seen=set();stage_index=0;phase='prepare';phase_at=time.monotonic();results=[];phase_token=0
STAGES=[('back_and_forth','Pointing_Up','Giơ MỘT NGÓN TAY','complete'),('circle','Victory','Giơ HAI NGÓN chữ V','complete'),('greeting','Wave','XÒE TAY và VẪY TRÁI–PHẢI liên tục','complete'),('circle','Victory','Giơ HAI NGÓN chữ V','stop'),('circle','Victory','Giơ HAI NGÓN chữ V','cancel'),('circle','Victory','Giơ HAI NGÓN chữ V','loss')]

def frame_received(sink):
 global latest,frames
 sample=sink.emit('pull-sample');caps=sample.get_caps().get_structure(0);w=caps.get_value('width');h=caps.get_value('height')
 buffer=sample.get_buffer();ok,m=buffer.map(Gst.MapFlags.READ)
 if ok:
  stride=len(m.data)//h
  arr=np.frombuffer(m.data,dtype=np.uint8).reshape(h,stride)[:,:w*3].reshape(h,w,3).copy()
  buffer.unmap(m)
  with frame_lock:latest=arr;frames+=1
 return Gst.FlowReturn.OK
pipeline.get_by_name('frames').connect('new-sample',frame_received)

def capture(name):
 with frame_lock:im=None if latest is None else latest.copy()
 if im is not None:
  filename=f'{int((time.monotonic()-record_start)*1000):07d}_{name}.png'
  cv2.imwrite(str(IMAGE_DIR/filename),im);log('screenshot',file=filename,state=state,gesture=last_gesture)
 return False

def stage_select():
 global phase,phase_at,phase_token
 phase='select';phase_at=time.monotonic();phase_token+=1
 behavior,gesture,instruction,mode=STAGES[stage_index]
 cue(f'CẢNH {stage_index+1}/6 — {instruction}. Chờ SELECTED, chưa giơ ngón cái.')

def next_stage():
 global stage_index,phase,phase_at
 stage_index+=1
 if stage_index==len(STAGES):
  phase='done';phase_at=time.monotonic();cue('HOÀN THÀNH DEMO — Robot đã dừng. Để tay ngoài webcam; đang lưu video và ảnh báo cáo.')
  GLib.timeout_add(5000,stop_recording)
 else:stage_select()
 return False

def process_state(s):
 global state,phase,phase_at,phase_token
 old=state;state=s
 if s.get('state')!=old.get('state') or s.get('step')!=old.get('step'):log('robot_state',data=s,stage=stage_index+1,phase=phase)
 if phase in ['prepare','done','finishing']:return False
 behavior,gesture,instruction,mode=STAGES[stage_index];now=time.monotonic();status=s['state']
 if phase=='select' and status=='SELECTED' and s.get('selected')==behavior:
  capture(f'{stage_index+1:02d}_selected')
  if stage_index==0:
   phase='selected_hold';phase_at=now;cue('CẢNH 1 — ĐÃ CHỌN. Giữ MỘT NGÓN thêm 2 giây: robot đứng yên khi chưa xác nhận.')
  else:
   phase='confirm';phase_at=now;cue(f'CẢNH {stage_index+1} — ĐÃ CHỌN. Chuyển sang NGÓN CÁI 👍 để XÁC NHẬN, rồi giữ trong khung hình.')
 elif phase in ['confirm','selected_hold'] and status=='RUNNING' and s.get('selected')==behavior:
  phase='running';phase_at=now;capture(f'{stage_index+1:02d}_running');GLib.timeout_add(300,lambda:capture(f'{stage_index+1:02d}_running_visible'))
  cue(f'CẢNH {stage_index+1} — ĐANG CHẠY. Giữ NGÓN CÁI 👍 rõ trong webcam.'+(' Chờ COMPLETED.' if mode=='complete' else ' Chờ hướng dẫn dừng.'))
 elif phase=='running' and mode=='complete' and status=='COMPLETED':
  phase='finishing';capture(f'{stage_index+1:02d}_completed');GLib.timeout_add(400,lambda:capture(f'{stage_index+1:02d}_completed_visible'))
  results.append({'stage':stage_index+1,'behavior':behavior,'result':'COMPLETED','at_seconds':round(now-record_start,2)})
  cue(f'CẢNH {stage_index+1} — COMPLETED, đã hoàn thành. Để tay ngoài khung hình và chờ cảnh tiếp theo.');GLib.timeout_add(3000,next_stage)
 elif phase in ['running','action'] and mode!='complete' and status=={'stop':'STOPPED','cancel':'IDLE','loss':'SIGNAL_LOST'}[mode]:
  if phase!='action':
   log('attempt_interrupted',stage=stage_index+1,data=s);stage_select();return False
  phase='finishing';capture(f'{stage_index+1:02d}_{status.lower()}');GLib.timeout_add(450,lambda:capture(f'{stage_index+1:02d}_{status.lower()}_visible'))
  results.append({'stage':stage_index+1,'behavior':behavior,'result':status,'at_seconds':round(now-record_start,2)})
  cue(f'CẢNH {stage_index+1} — {status}: robot đã dừng đúng yêu cầu. Để tay ngoài khung hình.');GLib.timeout_add(3500,next_stage)
 elif phase in ['confirm','selected_hold','running','action'] and status in ['STOPPED','IDLE','SIGNAL_LOST','NOT_READY','SAFETY_STOP','OBSTACLE_STOP','TIMEOUT'] and status!=old.get('state'):
  log('attempt_interrupted',stage=stage_index+1,data=s);capture(f'{stage_index+1:02d}_interrupted_{status.lower()}');stage_select()
 return False

rclpy.init();ros=Node('lab06_demo_observer')
ros.create_subscription(String,'/robot_behavior_state',lambda m:GLib.idle_add(process_state,json.loads(m.data)),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
def on_gesture(m):
 global last_gesture
 last_gesture=m.data
 if m.data not in seen and m.data!='None':
  seen.add(m.data);GLib.idle_add(capture,'gesture_'+m.data)
ros.create_subscription(String,'/detected_gesture',on_gesture,1)
def on_debug(m):
 global debug
 debug=json.loads(m.data)
ros.create_subscription(String,'/gesture_recognition/debug',on_debug,1)
def on_image(m):
 gesture=last_gesture
 if gesture=='None':return
 name='webcam_'+gesture+'.png'
 if (IMAGE_DIR/name).exists():return
 arr=np.frombuffer(m.data,dtype=np.uint8).reshape(m.height,m.step)[:,:m.width*3].reshape(m.height,m.width,3)
 cv2.imwrite(str(IMAGE_DIR/name),arr);log('webcam_gesture',gesture=gesture,file=name,debug=debug)
ros.create_subscription(Image,'/gesture_recognition/image',on_image,1)
def on_odom(m):
 p=m.pose.pose.position
 with (BASE/'odometry.jsonl').open('a') as f:f.write(json.dumps({'seconds':round(time.monotonic()-record_start,3),'stage':stage_index+1,'x':p.x,'y':p.y,'qz':m.pose.pose.orientation.z,'qw':m.pose.pose.orientation.w})+'\n')
ros.create_subscription(Odometry,'/odom',on_odom,qos_profile_sensor_data)
threading.Thread(target=lambda:rclpy.spin(ros),daemon=True).start()
main=GLib.MainLoop();gst_bus=pipeline.get_bus();gst_bus.add_signal_watch()

def stop_recording(*args):
 global finished
 if finished:return False
 finished=True;cue('ĐANG LƯU VIDEO — để tay ngoài webcam.');pipeline.send_event(Gst.Event.new_eos())
 GLib.timeout_add(10000,lambda:(main.quit(),False)[1]);return False

def gst_message(bus,message):
 if message.type==Gst.MessageType.ERROR:
  err,detail=message.parse_error();log('recording_error',error=str(err),details=detail);main.quit()
 elif message.type==Gst.MessageType.EOS:log('video_saved',file=str(output));main.quit()
gst_bus.connect('message',gst_message)

def timer():
 global phase,phase_at
 now=time.monotonic()
 if (BASE/'stop_recording').exists():return stop_recording()
 if phase=='prepare' and state.get('ready') and frames>30 and now-record_start>8:
  capture('00_ready_overview');stage_select()
 elif phase=='selected_hold' and now-phase_at>2:
  phase='confirm';phase_at=now;cue('CẢNH 1 — Giờ giơ NGÓN CÁI 👍 để XÁC NHẬN. Giữ đến khi hoàn thành 4 chu kỳ tiến–lùi.')
 elif phase=='running' and STAGES[stage_index][3]!='complete' and now-phase_at>3:
  phase='action';phase_at=now;mode=STAGES[stage_index][3]
  text={'stop':'XÒE BÀN TAY và GIỮ ĐỨNG YÊN để DỪNG.','cancel':'NẮM TAY để HỦY hành vi.','loss':'ĐƯA TAY HOÀN TOÀN RA KHỎI WEBCAM để kiểm tra mất tín hiệu.'}[mode]
  cue(f'CẢNH {stage_index+1} — '+text)
 return True
GLib.timeout_add(200,timer)
for sig in (signal.SIGINT,signal.SIGTERM):GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,sig,stop_recording)
pipeline.set_state(Gst.State.PLAYING);log('recording_started',file=str(output));cue('ĐÃ BẮT ĐẦU GHI HÌNH — để tay ngoài webcam, chờ CẢNH 1 trên thanh hướng dẫn.')
try:main.run()
finally:
 pipeline.set_state(Gst.State.NULL)
 try:bus.call_sync(PORTAL,session,'org.freedesktop.portal.Session','Close',None,None,Gio.DBusCallFlags.NONE,3000,None)
 except Exception:pass
 if rclpy.ok():rclpy.shutdown()
 summary={'source':'Real webcam gestures and real Wayland desktop recording; no synthetic gesture or velocity publications','completed_stages':results,'observed_gestures':sorted(seen),'frames':frames,'duration_seconds':round(time.monotonic()-record_start,2),'all_six_stages_completed':len(results)==6,'video':str(output)}
 (BASE/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False));events.close();(BASE/'coach_stop').touch()
 print(json.dumps(summary,ensure_ascii=False),flush=True)
