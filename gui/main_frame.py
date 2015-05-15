"""The main frame for Google Music Player"""

import wx, wx.dataview as dv, application, columns, functions, gmusicapi, requests, os, sys
from threading import Thread, Event
from sound_lib.stream import URLStream, FileStream
from sound_lib.main import BassError
from gui.python_console import PythonConsole

class TrackThread(Thread):
 """A thread which can be stopped."""
 def __init__(self, *args, **kwargs):
  super(TrackThread, self).__init__(*args, **kwargs)
  self.should_stop = Event()

class MainFrame(wx.Frame):
 """The main program interface."""
 def __init__(self, ):
  """Create the window."""
  super(MainFrame, self).__init__(None, title = application.name)
  self.last_search = '' # Whatever the user last searched for.
  self._current_track = None # The metadata for the currently playing track.
  self.current_track = None
  self._queue = [] # The actual queue of tracks.
  self.track_history = [] # The play history.
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  self.results = dv.DataViewListCtrl(p, style = wx.TE_PROCESS_ENTER) # User friendly track list.
  self.results.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.select_item)
  self.results.SetFocus()
  self.results.SetFocusFromKbd()
  self._results = [] # The raw json from Google.
  for real, friendly in application.columns:
   if friendly:
    self.results.AppendTextColumn(friendly)
  s1.Add(self.results, 7, wx.GROW)
  self.queue = dv.DataViewListCtrl(p)
  for x in ['Name', 'Artist', 'Album', 'Duration']:
   self.queue.AppendTextColumn(x)
  s1.Add(self.queue, 3, wx.GROW)
  s.Add(s1, 7, wx.GROW)
  s2 = wx.BoxSizer(wx.HORIZONTAL)
  s2.Add(wx.StaticText(p, label = '&Track Seek'), 0, wx.GROW)
  self.track_position = wx.Slider(p, name = 'Track Position')
  self.track_position.Bind(wx.EVT_SLIDER, functions.track_seek)
  s2.Add(self.track_position, 3, wx.GROW)
  self.previous = wx.Button(p, label = application.config.get('windows', 'previous_label'))
  self.Bind(wx.EVT_BUTTON, functions.previous)
  s2.Add(self.previous, 1, wx.GROW)
  self.play_pause = wx.Button(p, label = application.config.get('windows', 'play_label'))
  self.play_pause.Bind(wx.EVT_BUTTON, functions.play_pause)
  s2.Add(self.play_pause, 1, wx.GROW)
  self.next = wx.Button(p, label = application.config.get('windows', 'next_label'))
  self.next.Bind(wx.EVT_BUTTON, functions.next)
  s2.Add(self.next, 1, wx.GROW)
  s2.Add(wx.StaticText(p, label = '&Frequency'), 0, wx.GROW)
  self.frequency = wx.Slider(p, name = 'Track frequency', style = wx.SL_VERTICAL|wx.SL_INVERSE)
  self.frequency.Bind(wx.EVT_SLIDER, self.set_frequency)
  self.frequency.SetValue(application.config.get('sound', 'frequency'))
  s2.Add(self.frequency, 1, wx.GROW)
  s.Add(s2, 1, wx.GROW)
  s3 = wx.BoxSizer(wx.HORIZONTAL)
  s3.Add(wx.StaticText(p, label = application.config.get('windows', 'volume_label')), 0, wx.GROW)
  self.volume = wx.Slider(p, style = wx.SL_VERTICAL|wx.SL_INVERSE)
  self.volume.SetValue(application.config.get('sound', 'volume') * 100)
  self.volume.Bind(wx.EVT_SLIDER, self.set_volume)
  s3.Add(self.volume, 1, wx.GROW)
  s3.Add(wx.StaticText(p, label = '&Pan'), 0, wx.GROW)
  self.pan = wx.Slider(p)
  self.pan.SetValue((application.config.get('sound', 'pan') + 1.0) * 50.0)
  self.pan.Bind(wx.EVT_SLIDER, self.set_pan)
  s3.Add(self.pan, 1, wx.GROW)
  s.Add(s3, 1, wx.GROW)
  self.artist_bio = wx.StaticText(p, label = 'No song playing.')
  s.Add(self.artist_bio, 1, wx.GROW)
  p.SetSizerAndFit(s)
  mb = wx.MenuBar()
  file_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, functions.reveal_media, file_menu.Append(wx.ID_ANY, '&Reveal Media Directory\tCTRL+R', 'Open the media directory in %s' % ('Finder' if sys.platform == 'darwin' else 'Windows Explorer')))
  self.Bind(wx.EVT_MENU, lambda event: self.Close(True), file_menu.Append(wx.ID_EXIT, 'E&xit', 'Quit the program'))
  mb.Append(file_menu, '&File')
  edit_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, functions.do_search, edit_menu.Append(wx.ID_FIND, '&Find\tCTRL+F', 'Find a song'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.toggle_library, args = [event]).start(), edit_menu.Append(wx.ID_ANY, '&Add Or Remove From Library\tCTRL+/', 'Add or remove the current song from the library'))
  mb.Append(edit_menu, '&Edit')
  view_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, functions.focus_playing, view_menu.Append(wx.ID_ANY, '&Focus Current\tCTRL+L', 'Focus the currently playing track'))
  mb.Append(view_menu, '&View')
  source_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = self.init_results, args = [event]).start(), source_menu.Append(wx.ID_ANY, '&Library\tCTRL+0', 'Return to the library'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.select_playlist, args = [event]).start(), source_menu.Append(wx.ID_ANY, 'Select &Playlist...\tCTRL+1', 'Select a playlist'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.select_radio, args = [event]).start(), source_menu.Append(wx.ID_ANY, 'Select &Radio Station...\tCTRL+2', 'Select a radio station'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.thumbs_up_songs, args = [event]).start(), source_menu.Append(wx.ID_ANY, '&Thumbs Up Songs\tCTRL+3', 'Get a list of your thumbed up tracks'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.artist_tracks, args = [None]).start(), source_menu.Append(wx.ID_ANY, 'Go To &Artist\tCTRL+4', 'Get a list of all artist tracks'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.current_album, args = [None]).start(), source_menu.Append(wx.ID_ANY, 'Go To Current A&lbum\tCTRL+5', 'Go to the current album'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.artist_album, args = [None]).start(), source_menu.Append(wx.ID_ANY, '&Go To Album\tCTRL+6', 'Go to a particular album'))
  self.Bind(wx.EVT_MENU, lambda event: Thread(target = functions.related_artists, args = [None]).start(), source_menu.Append(wx.ID_ANY, '&Related Artists\tCTRL+7', 'Select a related artist to view tracks.'))
  mb.Append(source_menu, '&Source')
  play_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, lambda event: self.select_item(event) if self.results.HasFocus() else None, play_menu.Append(wx.ID_ANY, '&Select Current Item\tENTER', 'Selects the current item'))
  self.Bind(wx.EVT_MENU, functions.play_pause, play_menu.Append(wx.ID_ANY, '&Play or Pause\tCTRL+ENTER', 'Play or pause the currently playing song'))
  self.Bind(wx.EVT_MENU, functions.volume_up, play_menu.Append(wx.ID_ANY, 'Volume &up\tCTRL+UP', 'Volume + %s' % application.config.get('sound', 'volume_increment')))
  self.Bind(wx.EVT_MENU, functions.volume_down, play_menu.Append(wx.ID_ANY, 'Volume &Down\tCTRL+DOWN', 'Volume - %s' % application.config.get('sound', 'volume_decrement')))
  self.Bind(wx.EVT_MENU, functions.previous, play_menu.Append(wx.ID_ANY, '&Previous\tCTRL+LEFT', 'Play the previous track'))
  self.Bind(wx.EVT_MENU, functions.next, play_menu.Append(wx.ID_ANY, '&Next\tCTRL+RIGHT', 'Play the next track'))
  self.Bind(wx.EVT_MENU, functions.stop, play_menu.Append(wx.ID_ANY, '&Stop\tCTRL+.', 'Stop the currently playing song.'))
  self.Bind(wx.EVT_MENU, functions.rewind, play_menu.Append(wx.ID_ANY, '&Rewind\tSHIFT+LEFT', 'Rewind by %s' % application.config.get('sound', 'rewind_amount')))
  self.Bind(wx.EVT_MENU, functions.fastforward, play_menu.Append(wx.ID_ANY, '&Fastforward\tSHIFT+RIGHT', 'Fastforward by %s' % application.config.get('sound', 'fastforward_amount')))
  self.Bind(wx.EVT_MENU, lambda event: self.set_frequency(self.frequency.SetValue(min(100, self.frequency.GetValue() + 1))), play_menu.Append(wx.ID_ANY, 'Frequency &Up\tSHIFT+UP', 'Shift the frequency up a little'))
  self.Bind(wx.EVT_MENU, lambda event: self.set_frequency(self.frequency.SetValue(max(0, self.frequency.GetValue() - 1))), play_menu.Append(wx.ID_ANY, 'Frequency &Down\tSHIFT+DOWN', 'Shift the frequency down a little'))
  mb.Append(play_menu, '&Play')
  options_menu = wx.Menu()
  self.Bind(wx.EVT_MENU, lambda event: application.config.get_gui().Show(True), options_menu.Append(wx.ID_PREFERENCES, '&Preferences\tCTRL+,', 'Configure the program'))
  self.Bind(wx.EVT_MENU, functions.select_output, options_menu.Append(wx.ID_ANY, '&Select sound output...', 'Select a new output device for sound playback'))
  self.Bind(wx.EVT_MENU, lambda event: PythonConsole().Show(True), options_menu.Append(wx.ID_ANY, '&Python Console...', 'Launch a Python console for development purposes'))
  mb.Append(options_menu, '&Options')
  self.SetMenuBar(mb)
  self._thread = TrackThread(target = self.track_thread)
  self.Maximize()
  self.Raise()
 
 def Close(self, value = True):
  """Close the window, terminating the track thread in the process."""
  self._thread.should_stop.set()
  return super(MainFrame, self).Close(value)
 
 def get_current_track(self):
  """Gets the current track data."""
  return self._current_track
 
 def get_results(self):
  """Returns the results."""
  return self._results
 
 def add_history(self, item):
  """Adds an item to play history."""
  self.track_history.append(item)
 
 def delete_history(self, index = -1):
  """Deletes the history item at index."""
  del self.track_history[index]
 
 def clear_history(self):
  """Clears the track history."""
  self.track_history = []
 
 def add_result(self, result):
  """Given a list item from Google, add it to self._results, and add data to the table."""
  self._results.append(result)
  stuff = []
  for real, friendly in application.columns:
   if friendly:
    stuff.append(getattr(columns, 'parse_%s' % real, lambda data: unicode(data))(result.get(real, 'Unknown')))
  wx.CallAfter(self.results.AppendItem, stuff)
 
 def delete_result(self, result):
  """Deletes the result and the associated row in self._results."""
  self.results.remove(result)
  del self._results[result]
 
 def add_results(self, results, clear = False):
  """Adds multiple results using self.add_result."""
  if clear:
   self.clear_results()
  for x in results:
   self.add_result(x)
 
 def clear_results(self):
  """Clears the results table."""
  self._results = []
  self.results.DeleteAllItems()
 
 def init_results(self, event = None):
  """Initialises the results table."""
  self.add_results(application.mobile_api.get_all_songs(), True)
 
 def Show(self, value = True):
  """Shows the frame."""
  res = super(MainFrame, self).Show(value)
  self._thread.start()
  if not self._results:
   wx.CallAfter(self.init_results)
  return res
 
 def SetTitle(self, value = None):
  """Sets the title."""
  if value == None:
   try:
    value = application.config.get('windows', 'title_format').format(**self.get_current_track())
   except KeyError as e:
    value = 'Error in title format: %s.' % e
  return super(MainFrame, self).SetTitle('%s (%s)' % (application.name, value))
 
 def select_item(self, event):
  """Play the track under the mouse."""
  id = self.get_current_result()
  Thread(target = self.play, args = [self._results[id]]).start()
  self.queue_tracks(self._results[id + 1:], True)
 
 def get_queue(self):
  """Returns the queued tracks."""
  return self._queue
 
 def queue_track(self, value):
  """Add a track to the queue."""
  self._queue.append(value)
  self.queue.AppendItem([value['title'], value['artist'], value['album'], columns.parse_durationMillis(value['durationMillis'])])
 
 def queue_tracks(self, items, clear = False):
  """Add multiple items to the queue."""
  if clear:
   self.clear_queue()
  for x in items:
   self.queue_track(x)
 
 def unqueue_track(self, result):
  """Removes a track from the queue."""
  self.queue.DeleteItem(result)
  del self._queue[result]
 
 def clear_queue(self):
  """Clears the play queue."""
  self._queue = []
  self.queue.DeleteAllItems()
 
 def play(self, item, history = True):
  """Plays the track given in item. If history is True, add any current track to the history."""
  id = functions.get_id(item)
  print application.mobile_api.get_track_info(id).keys()
  track = None # The object to store the track in until it's ready for playing.
  error = None # Any error that occured.
  fname = id + application.track_extension
  path = functions.id_to_path(id)
  if id not in application.library or (application.library[id] and application.library[id] != item.get('lastModifiedTimestamp', application.library[id])): # Our version is older, download again
   device = functions.get_device_id()
   if device:
    try:
     url = application.mobile_api.get_stream_url(id, device)
    except gmusicapi.exceptions.CallFailure as e:
     application.device_id = None
     return wx.MessageBox('Cannot play with that device: %s.' % e, 'Invalid Device')
    try:
     track = URLStream(url = url)
    except BassError as e:
     error = e # Just store it for later alerting.
    Thread(target = functions.download_file, args = [id, url, item.get('lastModifiedTimestamp', 0)]).start()
   else:
    return None # Track is not downloaded, and can't get a device to download with.
  else:
   try:
    track = FileStream(file = path)
   except BassError as e:
    error = e # Same as above.
  if error:
   return wx.MessageBox(str(e), 'Error')
  if self.current_track:
   self.current_track.stop()
   if history:
    self.add_history(self._current_track)
  self._current_track = item
  self.current_track = track
  self.SetTitle()
  self.current_track.set_volume(application.config.get('sound', 'volume'))
  self.current_track.set_pan(application.config.get('sound', 'pan'))
  self.set_frequency()
  self.current_track.play()
  self.play_pause.SetLabel(application.config.get('windows', 'pause_label'))
  self.artist_info = application.mobile_api.get_artist_info(item['artistId'][0])
  self.artist_bio.SetLabel(self.artist_info.get('artistBio', 'No information available.'))
 
 def set_volume(self, event):
  """Sets the volume with the slider."""
  application.config.set('sound', 'volume', self.volume.GetValue() / 100.0)
  if self.current_track:
   self.current_track.set_volume(application.config.get('sound', 'volume'))
 
 def set_pan(self, event):
  """Sets pan with the slider."""
  application.config.set('sound', 'pan', (event.GetSelection() / 50.0) - 1.0)
  if self.current_track:
   self.current_track.set_pan(application.config.get('sound', 'pan'))
 
 def set_frequency(self, event = None):
  """Sets the frequency of the currently playing track by the frequency slider."""
  application.config.set('sound', 'frequency', self.frequency.GetValue())
  if self.current_track:
   self.current_track.set_frequency(self.frequency.GetValue() * 882)
 
 def track_thread(self):
  """Move track progress bars and play queued tracks."""
  while not self._thread.should_stop.is_set():
   if self.current_track:
    i = min(self.current_track.get_length(), int(self.current_track.get_position() / (self.current_track.get_length() / 100.0)))
    if not self.track_position.HasFocus() and i != self.track_position.GetValue():
     self.track_position.SetValue(i)
    if self.current_track.get_position() == self.current_track.get_length():
     functions.next(None, interactive = False)
 
 def get_current_result(self):
  """Returns the current result."""
  return self.results.GetSelection().GetID() - 1
