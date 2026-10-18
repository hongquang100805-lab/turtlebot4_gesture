from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None);base=Path(__file__).resolve().parent
out=Gst.parse_launch(f'appsrc name=source format=time block=true ! webmmux ! filesink location="{base / "TurtleBot4_Nav2_YOLO_demo.webm"}"')
source=out.get_by_name('source')
stream=Gst.parse_launch(f'filesrc location="{base / "TurtleBot4_Nav2_YOLO.webm"}" ! matroskademux ! video/x-vp8 ! appsink name=sink emit-signals=true sync=false')
sink=stream.get_by_name('sink');state={'i':0,'last_pts':0}
def sample(sink):
 s=sink.emit('pull-sample');b=s.get_buffer();i=state['i'];state['i']+=1
 if i<=2800:
  if i==0:source.set_property('caps',s.get_caps())
  result=source.emit('push-buffer',b.copy_deep())
  assert result==Gst.FlowReturn.OK,result
  state['last_pts']=b.pts
 return Gst.FlowReturn.OK
sink.connect('new-sample',sample);out.set_state(Gst.State.PLAYING);stream.set_state(Gst.State.PLAYING)
m=stream.get_bus().timed_pop_filtered(Gst.CLOCK_TIME_NONE,Gst.MessageType.EOS|Gst.MessageType.ERROR)
if m.type==Gst.MessageType.ERROR:raise RuntimeError(m.parse_error())
source.emit('end-of-stream')
m=out.get_bus().timed_pop_filtered(Gst.CLOCK_TIME_NONE,Gst.MessageType.EOS|Gst.MessageType.ERROR)
if m.type==Gst.MessageType.ERROR:raise RuntimeError(m.parse_error())
stream.set_state(Gst.State.NULL);out.set_state(Gst.State.NULL)
print('Trimmed tail only; last frame PTS:',state['last_pts']/Gst.SECOND)
