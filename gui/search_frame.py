"""The search frame for gmp."""

import wx, application, functions
from wx.lib.sized_controls import SizedFrame
from threading import Thread

search_types = [
 ['Songs', 'song_hits'],
 ['Artists', 'artist_hits'],
 ['Albums', 'album_hits'],
 ['Playlists', 'playlist_hits']
]

# Search type constants:
songs = 0
artists = 1
albums = 2
playlists = 3

class SearchFrame(SizedFrame):
 """The frame to use to search for stuff."""
 def __init__(self, search, type):
  """
  search - The search string.
  type - The type of search to perform.
  """
  super(SearchFrame, self).__init__(application.main_frame, title = 'Search Google Music')
  p = self.GetContentsPane()
  wx.StaticText(p, label = '&Find')
  self.search = wx.TextCtrl(p, value = search, style = wx.TE_PROCESS_ENTER)
  self.search.SetSelection(-1, -1)
  self.search.Bind(wx.EVT_TEXT_ENTER, self.do_search)
  wx.StaticText(p, label = 'Search &Type')
  self.type = wx.Choice(p, choices = [x[0] for x in search_types])
  self.type.SetSelection(type)
  wx.Button(p, label = application.config.get('windows', 'cancel_label')).Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  b = wx.Button(p, label = application.config.get('windows', 'search_label'))
  b.SetDefault()
  b.Bind(wx.EVT_BUTTON, self.do_search)
 
 def Show(self, value = True):
  """Sow the window and maximize."""
  s = super(SearchFrame, self).Show(value)
  self.Raise()
  self.Maximize(True)
  return s
 
 def do_search(self, event = None):
  """Perform a search."""
  search = self.search.GetValue()
  type = self.type.GetSelection()
  if not search:
   return wx.MessageBox('You must search for something.', 'Nothing to search for')
  try:
   results = application.mobile_api.search_all_access(search, max_results = application.config.get('library', 'max_results'))
  except functions.RE as e:
   return wx.MessageBox(*functions.format_requests_error(e))
  results = results.get(search_types[type][1])
  if not results:
   wx.MessageBox('No %s found for %s.' % (search_types[type][0].lower(), search), 'Nothing Found')
  else:
   application.main_frame.last_search = search
   application.main_frame.last_search_type = type
   if type == artists:
    results = [x['artist'] for x in results]
    dlg = wx.SingleChoiceDialog(self, 'Select an artist', 'Artist Results', [x['name'] for x in results])
    if dlg.ShowModal() == wx.ID_OK:
     res = dlg.GetSelection()
    else:
     res = None
    dlg.Destroy()
    if res != None:
     functions.top_tracks(functions.select_artist([results[dlg.GetSelection()]['artistId']]), interactive = True)
   elif type == albums:
    functions.artist_album(None, albums = [x['album'] for x in results])
   elif type == playlists:
    functions.select_playlist(playlists = [x['playlist'] for x in results])
   else:
    # Must be songs.
    wx.CallAfter(application.main_frame.add_results, [x['track'] for x in results], clear = True)
   self.Close(True)
