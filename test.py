import wx
for x in dir(wx):
 try:
  if getattr(wx, x, None) == 16:
    print x
 except Exception:
  pass

