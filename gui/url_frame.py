"""
GMP URL streams.

Test stream: http://198.154.106.104:8496/stream
"""

import wx, application, logging, functions
from wx.lib.sized_controls import SizedFrame
from sound_lib.stream import URLStream
from sound_lib.main import BassError

logger = logging.getLogger('URL Frame')

class URLFrame(SizedFrame):
 """Load a URL."""
 def __init__(self, url = '', title = ''):
  super(URLFrame, self).__init__(application.main_frame, title = 'URL Streams')
  p = self.GetContentsPane()
  p.SetSizerType('form')
  self._streams = application.streams
  self.streams = wx.ListBox(p, choices = ['%s (%s)' % (x, y) for x, y in self._streams], style = wx.LB_SINGLE)
  self.streams.Bind(wx.EVT_LISTBOX, self.update_form)
  wx.Button(p, label = '&Delete').Bind(wx.EVT_BUTTON, self.on_delete)
  wx.StaticText(p, label = '&URL')
  self.url = wx.TextCtrl(p, value = url, style = wx.TE_PROCESS_ENTER)
  self.url.SetFocus()
  self.url.Bind(wx.EVT_TEXT_ENTER, self.do_load)
  wx.StaticText(p, label = '&Title')
  self.title = wx.TextCtrl(p, value = title, style = wx.TE_PROCESS_ENTER)
  self.title.Bind(wx.EVT_TEXT_ENTER, self.do_load)
  wx.Button(p, label = '&Cancel').Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.ok = wx.Button(p, label = '&OK')
  self.ok.SetDefault()
  self.ok.Bind(wx.EVT_BUTTON, self.do_load)
  self.Bind(wx.EVT_CLOSE, self.on_close)
 
 def Show(self, *args, **kwargs):
  res = super(URLFrame, self).Show(*args, **kwargs)
  self.Maximize(True)
  return res
 
 def do_load(self, event):
  """OK button was clicked."""
  frame = application.main_frame
  url = self.url.GetValue().strip()
  title = self.title.GetValue().strip() or url
  logger.info('Playing URL "%s" from url %s.', title, url)
  try:
   s = URLStream(url)
   result = [title, url]
   if result not in self._streams:
    self._streams.append(result)
   if frame.current_track:
    frame.current_track.stop()
   frame.current_track = s
   frame.duration = 0.0
   frame.set_volume()
   frame.set_pan()
   frame.set_frequency()
   frame.SetTitle(title)
   frame.current_track.play()
   self.Close(True)
  except BassError as e:
   return wx.MessageBox(str(e), 'Error', style = wx.ICON_EXCLAMATION)
 
 def update_form(self, event):
  """Update url and title as the streams change."""
  title, url = self._streams[self.streams.GetSelection()]
  self.url.SetValue(url)
  self.title.SetValue(title)
 
 def on_delete(self, event):
  cr = self.streams.GetSelection()
  if cr == -1:
   return functions.bell()
  else:
   if wx.MessageBox('Really delete the %s stream?' % self._streams[cr][0], 'Are You Sure', style = wx.ICON_EXCLAMATION | wx.YES_NO) == wx.YES:
    del self._streams[cr]
    self.streams.Delete(cr)
 
 def on_close(self, event):
  """Closing..."""
  application.streams = self._streams
  event.Skip(True)
