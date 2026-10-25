import ctypes as C
x=C.CDLL('libX11.so.6');x.XOpenDisplay.restype=C.c_void_p;d=x.XOpenDisplay(None)
x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong;root=x.XDefaultRootWindow(d)
x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_char_p)]
x.XMoveResizeWindow.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint]
x.XRaiseWindow.argtypes=[C.c_void_p,C.c_ulong];x.XFlush.argtypes=[C.c_void_p]
x.XFree.argtypes=[C.c_void_p]
def walk(w):
 r=C.c_ulong();p=C.c_ulong();cs=C.POINTER(C.c_ulong)();n=C.c_uint()
 if not x.XQueryTree(d,w,C.byref(r),C.byref(p),C.byref(cs),C.byref(n)):return
 ids=[cs[i] for i in range(n.value)];x.XFree(cs)
 for wid in ids:
  name=C.c_char_p()
  if x.XFetchName(d,wid,C.byref(name)) and name.value:
   title=name.value.decode(errors='replace');x.XFree(name)
   spec=None
   if title=='Gazebo Sim':spec=(0,111,1190,924)
   elif title.endswith(' - RViz') or title.endswith(' - RViz*'):spec=(1198,111,714,350)
   elif title.startswith('LAB 06 | Webcam'):spec=(1198,496,714,535)
   if spec:x.XMoveResizeWindow(d,wid,*spec);x.XRaiseWindow(d,wid)
   print(hex(wid),title[:100],spec)
  walk(wid)
walk(root);x.XFlush(d)
