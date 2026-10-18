import ctypes,re,subprocess
x=ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.restype=ctypes.c_void_p;x.XOpenDisplay.argtypes=[ctypes.c_char_p]
d=x.XOpenDisplay(None);assert d
x.XMoveResizeWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint]
x.XRaiseWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XFlush.argtypes=[ctypes.c_void_p]
listing=subprocess.check_output(['xwininfo','-root','-tree'],text=True)
for line in listing.splitlines():
 match=re.search(r'(0x[0-9a-f]+) "([^"]*)"',line)
 if not match:continue
 wid=int(match.group(1),16);title=match.group(2)
 if 'navigation.rviz' in title and '("rviz2"' in line:
  x.XMoveResizeWindow(d,wid,0,32,1280,970);x.XRaiseWindow(d,wid);print('RViz',hex(wid))
 if 'TurtleBot4 - YOLO camera' in title and 'mutter-x11-frames' not in line:
  x.XMoveResizeWindow(d,wid,1280,32,640,970);x.XRaiseWindow(d,wid);print('Camera',hex(wid))
x.XFlush(d)
