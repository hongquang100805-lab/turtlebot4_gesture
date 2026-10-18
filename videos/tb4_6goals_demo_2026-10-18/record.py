from pathlib import Path
import time
from gi.repository import Gio,GLib
base=Path(__file__).resolve().parent;stop=base/'stop_recording';stop.unlink(missing_ok=True)
c=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(name,args):return c.call_sync('org.gnome.Shell.Screencast','/org/gnome/Shell/Screencast','org.gnome.Shell.Screencast',name,args,None,Gio.DBusCallFlags.NONE,60000,None).unpack()
options={'framerate':GLib.Variant('u',10),'draw-cursor':GLib.Variant('b',False),'pipeline':GLib.Variant('s','videoconvert n-threads=2 ! video/x-raw,format=I420 ! queue ! vp8enc cpu-used=16 max-quantizer=35 deadline=1 threads=2 target-bitrate=2500000 keyframe-max-dist=60 ! queue ! webmmux')}
r=call('ScreencastArea',GLib.Variant('(iiiisa{sv})',(0,32,1920,1008,str(base/'TurtleBot4_6Goals_Nav2_YOLO.webm'),options)))
assert r[0],r
(base/'recording_path.txt').write_text(r[1]);print('RECORDING',r[1],flush=True)
try:
 while not stop.exists():time.sleep(.2)
except KeyboardInterrupt:pass
finally:print('STOP',call('StopScreencast',None),flush=True)
