import wx, application
from wx.lib.sized_controls import SizedFrame

class NewPlaylist(SizedFrame):
 """Use this frame to create a new playlist."""
 def __init__(self, playlist = {}):
  super(NewPlaylist, self).__init__(None, title = 'Edit Playlist' if playlist else 'Create A Playlist')
  p = self.GetContentsPane()
  self.playlist = playlist
  p.SetSizerType('form')
  wx.StaticText(p, label = application.config.get('windows', 'new_playlist_name_label'))
  self.name = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER, value = self.playlist.get('name', ''))
  self.name.Bind(wx.EVT_TEXT_ENTER, self.do_create)
  wx.StaticText(p, label = application.config.get('windows', 'new_playlist_description_label'))
  self.description = wx.TextCtrl(p, style = wx.TE_MULTILINE|wx.TE_RICH2, value = self.playlist.get('description', ''))
  wx.StaticText(p, label = application.config.get('windows', 'new_playlist_public_label'))
  self.public = wx.CheckBox(p, label = application.config.get('windows', 'new_playlist_public_label'))
  self.cancel = wx.Button(p, label = application.config.get('windows', 'cancel_label'))
  self.cancel.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.ok = wx.Button(p, label = application.config.get('windows', 'ok_label'))
  self.ok.Bind(wx.EVT_BUTTON, self.do_create)
  self.Maximize(True)
  self.Raise()
 
 def do_create(self, event):
  """Performs the actual creation."""
  name = self.name.GetValue()
  if not name:
   return wx.MessageBox('Playlists must have names.', 'Error')
  description = self.description.GetValue()
  public = self.public.GetValue()
  if self.playlist:
   p = application.mobile_api.edit_playlist(self.playlist.get('id', None), new_name = name, new_description = description, public = public)
  else:
   try:
    p = application.mobile_api.create_playlist(name, description = description, public = public)
   except Exception as e:
    return wx.MessageBox('Error %sing playlist: %s.' % ('creat' if not self.playlist else 'edit', str(e)), 'Error')
  self.Close(True)
