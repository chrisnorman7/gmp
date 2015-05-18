"""The main frame for Google Music Player"""

import wx, wx.dataview as dv, application, columns, functions, gmusicapi, requests, os, sys
from threading import Thread, Event
from sound_lib.stream import URLStream, FileStream
from sound_lib.main import BassError
from gui.python_console import PythonConsole
from gui.new_playlist import NewPlaylist

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
  self.current_playlist = None # The current playlist
  self.current_station = None # The current radio station.
  self.current_library = None # The library in it's current state.
  self._current_track = None # The metadata for the currently playing track.
  self.current_track = None
  self._queue = [] # The actual queue of tracks.
  self.track_history = [] # The play history.
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  if application.platform == 'darwin':
   self.results = dv.DataViewListCtrl(p, style = wx.TE_PROCESS_ENTER) # User friendly track list.
   self.results.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.select_item)
   self.queue = dv.DataViewListCtrl(p)
  else:
   self.results = wx.ListCtrl(p, style = wx.LC_REPORT)
   self.results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.select_item)
   self.queue = wx.ListCtrl(p, style = wx.LC_REPORT)
  self.results.SetFocus()
  self._results = [] # The raw json from Google.
  self.init_results_columns()
  for x, y in enumerate(['Name', 'Artist', 'Album', 'Duration']):
   if application.platform == 'darwin':
    self.queue.AppendTextColumn(x)
   else:
    self.queue.InsertColumn(x, y)
  s1.Add(self.results, 7, wx.GROW)
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
  self.Bind(
  wx.EVT_MENU,
  lambda event: NewPlaylist().Show(True),
  file_menu.Append(
  wx.ID_ANY,
  '&New Playlist\tCTRL+N',
  'Create a new playlist'
  ))
  station_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.station_from_result, event]).start(),
  station_menu.Append(
  wx.ID_ANY,
  'Create Station From Current &Result\tCTRL+9',
  'Creates a radio station from the currently focused result'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.station_from_artist, event]).start(),
  station_menu.Append(
  wx.ID_ANY,
  'Create Station From Current &Artist\tALT+4', 'Create a radio station based on the currently focused artist'))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.station_from_album, event]).start(),
  station_menu.Append(
  wx.ID_ANY,
  'Create Station From Current A&lbum\tALT+5',
  'Create a radio station based on the currently focused album'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.station_from_genre, event]).start(),
  station_menu.Append(
  wx.ID_ANY,
  'Create Station From &Genre\tALT+6',
  'Create a radio station based on a particular genre'
  ))
  file_menu.AppendMenu(wx.ID_ANY, 'Create &Station', station_menu, 'Create radio stations from various sources')
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.add_to_playlist, event]).start(),
  file_menu.Append(
  wx.ID_ANY,
  'Add Current Result To &Playlist...\tCTRL+8',
  'Add the current result to one of your playlists'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.delete, event]).start(),file_menu.Append(
  wx.ID_ANY,
  '&Delete Current Result\tDELETE',
  'Removes an item from the library or the currently focused playlist'))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.rename_playlist, event]).start(),
  file_menu.Append(
  wx.ID_ANY,
  '&Rename Current Playlist...\tF2',
  'Rename the currently focused playlist'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.delete_playlist_or_station, event]).start(),
  file_menu.Append(
  wx.ID_ANY,
  '&Delete Current Playlist Or Station\tCTRL+DELETE',
  'Deletes the currently selected playlist or station'
  ))
  file_menu.AppendSeparator()
  self.Bind(
  wx.EVT_MENU,
  functions.reveal_media,
  file_menu.Append(
  wx.ID_ANY,
  '&Reveal Media Directory\t',
  'Open the media directory in %s' % ('Finder' if sys.platform == 'darwin' else 'Windows Explorer')
  ))
  file_menu.AppendSeparator()
  self.Bind(
  wx.EVT_MENU,
  lambda event: self.Close(True),
  file_menu.Append(
  wx.ID_EXIT,
  'E&xit',
  'Quit the program'
  ))
  mb.Append(file_menu, '&File')
  edit_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.do_search, event]).start(),
  edit_menu.Append(
  wx.ID_FIND,
  '&Find...\tCTRL+F',
  'Find a song'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.do_search, event, self.last_search]).start(),
  edit_menu.Append(
  wx.ID_ANY,
  'Find &Again\tCTRL+G',
  'Repeat the previous search'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.add_to_library, event]).start(),
  edit_menu.Append(
  wx.ID_ANY,
  '&Add To Library\tCTRL+/',
  'Add or remove the current song from the library'
  ))
  mb.Append(edit_menu, '&Edit')
  view_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  functions.focus_playing,
  view_menu.Append(
  wx.ID_ANY,
  '&Focus Current\tALT+ENTER',
  'Focus the currently playing track'
  ))
  mb.Append(view_menu, '&View')
  source_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [self.init_results, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  '&Library\tCTRL+l',
  'Return to the library'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.select_playlist, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Select &Playlist...\tCTRL+1',
  'Select a playlist'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.select_station, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Select &Station...\tCTRL+2',
  'Select a radio station'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.thumbs_up_tracks, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  '&Thumbs Up Songs\tCTRL+3',
  'Get a list of your thumbed up tracks'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.artist_tracks, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Go To Current &Artist\tCTRL+4',
  'Get a list of all artist tracks'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.current_album, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Go To Current A&lbum\tCTRL+5',
  'Go to the current album'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.artist_album, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Select Al&bum...\tCTRL+6',
  'Go to a particular album'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.related_artists, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Select &Related Artist...\tCTRL+7',
  'Select a related artist to view tracks.'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.all_playlist_tracks, event]).start(),
  source_menu.Append(
  wx.ID_ANY,
  'Loa&d All Playlist Tracks\tCTRL+0',
  'Load every item from every playlist into the results table'))
  mb.Append(source_menu, '&Source')
  track_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.queue_result, event]).start(),
  track_menu.Append(
  wx.ID_ANY,
  '&Queue Item\tCTRL+ENTER',
  'Add the currently selected item to the play queue'
  ))
  mb.Append(track_menu, '&Track')
  play_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: self.select_item(event) if self.results.HasFocus() else None,
  play_menu.Append(
  wx.ID_ANY,
  '&Select Current Item\tENTER',
  'Selects the current item'
  ))
  self.Bind(
  wx.EVT_MENU,
  functions.play_pause,
  play_menu.Append(
  wx.ID_ANY,
  '&Play or Pause\tSPACE',
  'Play or pause the currently playing song'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.volume_up, event]).start(),
  play_menu.Append(
  wx.ID_ANY,
  'Volume &Up\tCTRL+UP',
  'Increase the Volume'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.volume_down, event]).start(),
  play_menu.Append(
  wx.ID_ANY,
  'Volume &Down\tCTRL+DOWN',
  'Decrease the volume'
  ))
  self.Bind(wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.previous, event]).start(),
  play_menu.Append(
  wx.ID_ANY,
  '&Previous\tCTRL+LEFT',
  'Play the previous track'
  ))
  self.Bind(wx.
  EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.next, event]).start(),
  play_menu.Append(
  wx.ID_ANY, 
  '&Next\tCTRL+RIGHT',
  'Play the next track'
  ))
  self.Bind(wx.
  EVT_MENU,
  functions.stop,
  play_menu.Append(
  wx.ID_ANY,
  '&Stop\tCTRL+.',
  'Stop the currently playing song.'
  ))
  self.stop_after = play_menu.AppendCheckItem(
  wx.ID_ANY,
  'Stop &After\tCTRL+SHIFT+.',
  'Stop after the currently playing track has finished'
  )
  self.Bind(
  wx.EVT_MENU,
  lambda event: application.config.set('sound', 'stop_after', self.stop_after.IsChecked()),
  self.stop_after
  )
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.rewind, event]).start(),
  play_menu.Append(
  wx.ID_ANY,'&Rewind\tSHIFT+LEFT',
  'Rewind'
  ))
  self.Bind(
  wx.EVT_MENU,lambda event: Thread(target = wx.CallAfter, args = [functions.fastforward, event]).start(),
  play_menu.Append(
  wx.ID_ANY,
  '&Fastforward\tSHIFT+RIGHT',
  'Fastforward'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: self.set_frequency(self.frequency.SetValue(min(100, self.frequency.GetValue() + 1))),
  play_menu.Append(
  wx.ID_ANY,
  'Frequency &Up\tSHIFT+UP',
  'Shift the frequency up a little'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: self.set_frequency(self.frequency.SetValue(max(0, self.frequency.GetValue() - 1))),
  play_menu.Append(
  wx.ID_ANY,
  'Frequency &Down\tSHIFT+DOWN',
  'Shift the frequency down a little'
  ))
  mb.Append(play_menu, '&Play')
  options_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: application.config.get_gui().Show(True),
  options_menu.Append(
  wx.ID_PREFERENCES,
  '&Preferences\tCTRL+,',
  'Configure the program'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: Thread(target = wx.CallAfter, args = [functions.select_output, event]).start(),
  options_menu.Append(
  wx.ID_ANY,
  '&Select sound output...\tF12',
  'Select a new output device for sound playback'
  ))
  self.Bind(
  wx.EVT_MENU,
  lambda event: PythonConsole().Show(True),
  options_menu.Append(
  wx.ID_ANY,
  '&Python Console...\tF11',
  'Launch a Python console for development purposes'
  ))
  self.repeat = options_menu.AppendCheckItem(
  wx.ID_ANY,
  '&Repeat\tCTRL+R',
  'Repeat tracks'
  )
  self.repeat.Check(application.config.get('sound', 'repeat'))
  self.Bind(
  wx.EVT_MENU,
  lambda event: application.config.set('sound', 'repeat', self.repeat.IsChecked()),
  self.repeat)
  mb.Append(options_menu, '&Options')
  help_menu = wx.Menu()
  self.Bind(
  wx.EVT_MENU,
  lambda event: wx.AboutBox(application.info),
  help_menu.Append(wx.ID_ABOUT, '&About...', 'About the program'
  ))
  mb.Append(help_menu, '&Help')
  self.SetMenuBar(mb)
  self._thread = TrackThread(target = self.track_thread)
  self.Maximize()
  self.Raise()
  self.Bind(wx.EVT_CLOSE, self.do_close)
 
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
  for spec, column in application.columns:
   if type(column) != dict:
    application.columns.remove([spec, column])
    column = application.default_columns.get('spec', {})
    application.columns.append([spec, column])
   if column.get('include', False):
    stuff.append(getattr(columns, 'parse_%s' % spec, lambda data: unicode(data))(result.get(spec, 'Unknown')))
  wx.CallAfter(self.results.AppendItem if application.platform == 'darwin' else self.results.Append, stuff)
 
 def delete_result(self, result):
  """Deletes the result and the associated row in self._results."""
  self.results.DeleteItem(result)
  del self._results[result]
 
 def add_results(self, results, clear = False, playlist = None, station = None, library = None):
  """Adds multiple results using self.add_result. If playlist is provided, store the ID of the current playlist so we can perform operations on it."""
  self.current_playlist = playlist # Keep a record of what playlist we're in, so we can delete items and reload them.
  self.current_station = station # The current station for delete and such.
  self.current_library = library
  if clear:
   self.clear_results()
  map(self.add_result, results)
 
 def clear_results(self):
  """Clears the results table."""
  self._results = []
  self.results.DeleteAllItems()
 
 def init_results(self, event = None):
  """Initialises the results table."""
  songs = application.mobile_api.get_all_songs()
  self.add_results(songs, True, library = songs)
 
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
   value = functions.format_title(self.get_current_track())
  return super(MainFrame, self).SetTitle('%s (%s)' % (application.name, value))
 
 def select_item(self, event):
  """Play the track under the mouse."""
  id = self.get_current_result()
  if id == -1:
   return wx.Bell()
  Thread(target = self.play, args = [self.get_results()[id]]).start()
 
 def get_queue(self):
  """Returns the queued tracks."""
  return self._queue
 
 def queue_track(self, value):
  """Add a track to the queue."""
  self._queue.append(value)
  wx.CallAfter(self.queue.AppendItem if application.platform == 'darwin' else self.queue.Append, [value['title'], value['artist'], value['album'], columns.parse_durationMillis(value['durationMillis'])])
 
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
    return # Track is not downloaded, and can't get a device to download with.
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
    self.add_history(self.get_current_track())
  self._current_track = item
  self.current_track = track
  self.SetTitle()
  self.current_track.set_volume(application.config.get('sound', 'volume'))
  self.current_track.set_pan(application.config.get('sound', 'pan'))
  self.set_frequency()
  self.current_track.play()
  application.mobile_api.increment_song_playcount(id)
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
   try:
    if self.current_track:
     i = min(self.current_track.get_length(), int(self.current_track.get_position() / (self.current_track.get_length() / 100.0)))
     if not self.track_position.HasFocus() and i != self.track_position.GetValue():
      self.track_position.SetValue(i)
     if self.current_track.get_position() == self.current_track.get_length() and not self.stop_after.IsChecked():
      functions.next(None, interactive = False)
   except Exception as e:
    print 'Problem with the track thread: %s.' % str(e)
  self.Close(True)
 
 def get_current_result(self):
  """Returns the current result."""
  if application.platform == 'darwin':
   return self.results.GetSelection().GetID() - 1
  else:
   return self.results.GetFocusedItem()
 
 def do_close(self, event):
  """Closes the window after shutting down the track thread."""
  self._thread.should_stop.set()
  event.Skip()
 
 def init_results_columns(self):
  """Creates columns for the results table."""
  if application.platform == 'darwin':
   self.results.ClearColumns()
  else:
   self.results.ClearAll()
  for i, (spec, column) in enumerate(application.columns):
   if column.get('include', False):
    name = column.get('friendly_name', spec.title())
    if application.platform == 'darwin':
     self.results.AppendTextColumn(name)
    else:
     self.results.InsertColumn(i, name)
