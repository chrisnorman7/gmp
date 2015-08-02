"""The lyrics viewer for gmp."""

import wx, requests, application, re, webbrowser, functions
from lyrics import lyricwikiurl, getlyrics
from unidecode import unidecode
from threading import Thread

abort_symbols = '[]()<>,!%~\\"?'
avoid_symbols = '.\'#'

class LyricsViewer(wx.Frame):
 """The lyrics frame."""
 def __init__(self, artist, title):
  """Takes an artist and a title and populates the frame with the lyrics, if available."""
  self.url = None
  super(LyricsViewer, self).__init__(application.main_frame)
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
 
 def format_string(self, value):
  """Strips all unnecessaries out of a string."""
  raw_value = ''
  for x in unidecode(unicode(value)).replace(' ', '').replace('&', 'and').lower():
   if x not in abort_symbols:
    if x not in avoid_symbols:
     raw_value += x
   else:
    break
  return raw_value
 
 def populate_lyrics(self, artist, title):
  """Fills self.lyrics with the lyrics from the included lyrics package."""
  self.SetTitle('Lyrics for %s - %s' % (artist, title))
  error = True
  try:
   self.url = lyricwikiurl(artist, title)
   l = getlyrics(artist, title)
   error = False
  except (IOError, UnicodeEncodeError):
   raw_title = self.format_string(title)
   raw_artist = unidecode(artist).replace(' ', '').replace('&', 'and').lower()
   if 'feat' in raw_artist:
    raw_artist = raw_artist[:raw_artist.index('feat')]
   raw_artist = self.format_string(raw_artist)
   if raw_artist.startswith('the'):
    raw_artist = raw_artist[3:]
   self.url = 'http://www.azlyrics.com/lyrics/%s/%s.html' % (raw_artist, raw_title)
   try:
    res = requests.get(self.url)
    if res.status_code != 200:
     l = 'No lyrics found.'
    else:
     l = res.content
     start = '<!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->'
     end = '</div>'
     if start in l:
      l = l[l.index(start) + len(start):].replace('<br>', '')
      if end in l:
       l = l[:l.index(end)]
       l = re.sub(r'\<[^>]+\>', '', l)
       while l.startswith('\n') or l.startswith('\r'):
        l = l[1:]
       error = False
     else:
      l = 'Error in HTML. Place marker not found.'
   except (requests.exceptions.RequestException, requests.adapters.ReadTimeoutError) as e:
    l = 'Could not get lyrics from %s: %s.' % (self.url, str(e))
  if error:
   wx.CallAfter(self.lyrics.SetValue, '')
   wx.CallAfter(self.browse.Disable)
  else:
   wx.CallAfter(self.lyrics.SetValue, 'Lyrics URL: %s\n\n' % self.url)
   wx.CallAfter(self.browse.Enable)
  wx.CallAfter(self.lyrics.write, l)
  wx.CallAfter(self.lyrics.SetInsertionPoint, 0)
 
 def do_browse(self, event):
  """Opens the URL in the web browser."""
  if self.url:
   webbrowser.open(self.url)
  else:
   functions.bell()()
