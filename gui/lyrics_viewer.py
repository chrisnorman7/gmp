"""The lyrics viewer for gmp."""

import requests, wx, application, re, webbrowser, functions
from threading import Thread

class LyricsViewer(wx.Frame):
 """The lyrics frame."""
 def __init__(self, artist, title):
  """Takes an artist and a title and populates the frame with the lyrics, if available."""
  self.url = None
  super(LyricsViewer, self).__init__(application.main_frame, title = 'Lyrics for %s - %s' % (artist, title))
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  s1.Add(wx.StaticText(p, label = '&Lyrics'), 0, wx.GROW)
  self.lyrics = wx.TextCtrl(p, value = 'Loading lyrics...', style = wx.TE_MULTILINE|wx.TE_READONLY)
  s1.Add(self.lyrics, 1, wx.GROW)
  s.Add(s1, 1, wx.GROW)
  s2 = wx.BoxSizer(wx.HORIZONTAL)
  self.close = wx.Button(p, label = 'Close &Window')
  s2.Add(self.close, 1, wx.GROW)
  self.close.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.browse = wx.Button(p, label = '&Open In Browser')
  s2.Add(self.browse, 1, wx.GROW)
  self.browse.Bind(wx.EVT_BUTTON, self.do_browse)
  s.Add(s2, 0, wx.GROW)
  p.SetSizerAndFit(s)
  self.Bind(wx.EVT_CLOSE, self.do_close)
  Thread(target = self.populate_lyrics, args = [artist, title]).start()
  self.Raise()
  self.Show(True)
  self.Maximize(True)
 
 def do_close(self, event):
  """Makes sure the frame property of this module gets set to None before the frame closes."""
  application.lyrics_frame = None
  return event.Skip()
 
 def populate_lyrics(self, artist, title):
  """Fills self.lyrics with the lyrics from A-Z Lyrics."""
  symbols = '[]()<>.,!%~\\"\'?'
  raw_title = ''
  for x in title.replace(' ', '').replace('&', 'and').lower():
   if x not in symbols:
    raw_title += x
   else:
    break
  raw_artist = ''
  temp_artist = artist.replace(' ', '').replace('&', 'and').lower()
  if 'feat' in temp_artist:
   temp_artist = temp_artist[:temp_artist.index('feat')]
  for x in temp_artist:
   if x not in symbols:
    raw_artist += x
   else:
    break
  if raw_artist.startswith('the'):
   raw_artist = raw_artist[3:]
  self.url = 'http://www.azlyrics.com/lyrics/%s/%s.html' % (raw_artist, raw_title)
  wx.CallAfter(self.lyrics.SetValue, 'Lyrics URL: %s' % self.url)
  try:
   res = requests.get(self.url)
  except (requests.exceptions.RequestException, requests.adapters.ReadTimeoutError) as e:
   wx.CallAfter(self.lyrics.write, '\n\nCould not get lyrics: %s.' % str(e))
  if res.status_code != 200:
   wx.CallAfter(self.lyrics.write, '\n\nNo lyrics found.')
   wx.CallAfter(self.browse.Disable)
  else:
   l = res.content
   start = '<!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->'
   end = '</div>'
   if start in l:
    l = l[l.index(start) + len(start):].replace('<br>', '')
    if end in l:
     l = l[:l.index(end)]
     wx.CallAfter(self.lyrics.write, re.sub(r'\<[^>]+\>', '', l))
     return wx.CallAfter(self.lyrics.SetInsertionPoint, 0)
   wx.MessageBox('Error in HTML. Place marker not found.', 'Error')
   self.Close(True)
 
 def do_browse(self, event):
  """Opens the URL in the web browser."""
  if self.url:
   webbrowser.open(self.url)
  else:
   functions.bell()()
