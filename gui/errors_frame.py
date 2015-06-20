"""Errors frame for GMP."""

import wx, application, sys, errors
from wx.lib.sized_controls import SizedFrame
from wx.dataview import DataViewListCtrl as DVLC
from time import ctime

class ErrorsFrame(SizedFrame):
 """Frame to show program errors."""
 def __init__(self):
  super(ErrorsFrame, self).__init__(application.main_frame, title = 'Error Log')
  application.errors_frame = self
  p = self.GetContentsPane()
  p.SetSizerType('vertical')
  wx.StaticText(p, label = '&Error Log')
  columns = [
   dict(args = ['Time'], kwargs = dict(width = 200)),
   dict(args = ['Message'], kwargs = dict(width = 900))
  ]
  if sys.platform == 'darwin':
   self.log = DVLC(p)
   for c in columns:
    self.log.AppendTextColumn(*c['args'], **c['kwargs'])
  else:
   self.log = wx.ListCtrl(p, style = wx.LC_REPORT)
   for x, c in enumerate(columns):
    self.log.InsertColumn(x, *c['args'], **c['kwargs'])
  b = wx.Button(p, label = application.config.get('windows', 'close_label'))
  b.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  b.SetDefault()
  self.Raise()
  for x in errors.log.log:
   self.append_item(x)
  self.Bind(wx.EVT_CLOSE, self.on_close)
  self.Show(True)
 
 def Show(self, value = True):
  """Show the frame."""
  res = super(ErrorsFrame, self).Show(value)
  self.Maximize(True)
  return res
 
 def append_item(self, value):
  """Append an item to the log."""
  time, text = value
  time = ctime(time)
  if sys.platform == 'darwin':
   func = self.log.AppendItem
  else:
   func = self.log.Append
  func([time, text])
 
 def on_close(self, event):
  """Close the frame gracefully."""
  application.errors_frame = None
  return event.Skip()
