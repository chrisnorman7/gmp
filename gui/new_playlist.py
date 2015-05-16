import wx, application
from wx.lib.sized_controls import SizedFrame

class NewPlaylist(SizedFrame):
 """Use this frame to create a new playlist."""
 def __init__(self):
  super(NewPlaylist, self).__init__(None, title = 'Create A Playlist')
  p = self.GetContentsPane()
  p.SetSizerType('form')
  wx.StaticText(p, label = application.config.get('windows', 'new_playlist_name_label'))
  self.name = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER)
  self.name.Bind(wx.EVT_TEXT_ENTER, self.do_create)
  wx.StaticText(p, label = application.config.get('windows', 'new_playlist_public_label'))
  self.public = wx.CheckBox(p, label = application.config.get('windows', 'new_playlist_public_label'))
  self.cancel = wx.Button(p, label = application.config.get('windows', 'cancel_label'))
  self.cancel.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.create = wx.Button(p, label = application.config.get('windows', 'create_label'))
  self.create.Bind(wx.EVT_BUTTON, self.do_create)
  self.Maximize(True)
  self.Raise()
 
 def do_create(self, event):
  """Performs the actual creation."""
  name = self.name.GetValue()
  if name:
   p = application.mobile_api.create_playlist(name, self.public.GetValue())
   wx.MessageBox('Playlist %s created. The ID is %s.' % (name, p), 'Playlist Created')
   self.Close(True)
  else:
   wx.MessageBox('Playlists must have names.', 'Error')
