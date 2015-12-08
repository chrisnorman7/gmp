import wx, application, logging
from wx.lib.sized_controls import SizedFrame
from sound_lib.stream import URLStream

logger = logging.getLogger('URL Frame')

class URLFrame(SizedFrame):
 """Load a URL."""
 def __init__(self, url = '', title = ''):
  super(URLFrame, self).__init__(application.main_frame, title = 'Load A URL')
  p = self.GetContentsPane()
  p.SetSizerType('form')
  wx.StaticText(p, label = '&URL')
  self.url = wx.TextCtrl(p, value = url, style = wx.TE_PROCESS_ENTER)
  self.url.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
  wx.StaticText(p, label = '&Title')
  self.title = wx.TextCtrl(p, value = title, style = wx.TE_PROCESS_ENTER)
  self.title.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
  wx.Button(p, label = '&Cancel').Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.ok = wx.Button(p, label = '&OK')
  self.ok.SetDefault()
  self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
 
 def Show(self, *args, **kwargs):
  res = super(URLFrame, self).Show(*args, **kwargs)
  self.Maximize(True)
  return res
 
 def on_ok(self, event):
  """OK button was clicked."""
  frame = application.main_frame
  url = self.url.GetValue().strip()
  title = self.title.GetValue().strip() or url
  logger.info('Playing URL "%s" from url %s.', title, url)
  try:
   s = URLStream(url)
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
