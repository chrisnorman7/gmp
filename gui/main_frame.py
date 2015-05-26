"""The main frame for Google Music Player"""

import wx, wx.dataview as dv, application, columns, functions, gmusicapi, requests, os, sys
from threading import Thread, Event
from time import sleep
from inspect import getdoc
from sound_lib.stream import URLStream, FileStream
from sound_lib.main import BassError
from gui.python_console import PythonConsole
from gui.column_editor import ColumnEditor
from gui.new_playlist import NewPlaylist

keys = {} # Textual key names.
mods = {} # Textual modifiers
for x in dir(wx):
 if x.startswith('WXK_'):
  keys[getattr(wx, x)] = x[4:]

osx = application.platform == 'darwin'
mods[wx.ACCEL_CTRL] = 'CMD' if osx else 'CTRL'
mods[wx.ACCEL_ALT] = 'OPT' if osx else 'ALT'
mods[wx.ACCEL_SHIFT] = 'SHIFT'

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
  self.current_pos = 0.0 # The position in the currently playing track for the Winamp-style control.
  self.duration = None # The duration of the track as a string.
  self.title = None # The title of the current track.
  self.add_to_playlist = None
  self._accelerator_table = [] # The raw accelerator table as a list. Add entries with add_accelerator.
  self.accelerator_table = {} # The human-readable accelerator table.
  self.frequency_up = lambda event: self.set_frequency(self.frequency.SetValue(min(100, self.frequency.GetValue() + 1)))
  self.frequency_down = lambda event: self.set_frequency(self.frequency.SetValue(max(0, self.frequency.GetValue() - 1)))
  self.pan_left = lambda event: self.set_pan(self.pan.SetValue(max(0, self.pan.GetValue() - 1)))
  self.pan_right = lambda event: self.set_pan(self.pan.SetValue(min(100, self.pan.GetValue() + 1)))
  self.hotkeys = {
   (0, ord('X')): lambda event: self.current_track.play(True) if self.current_track else functions.play_pause(),
   (0, ord('C')): functions.play_pause,
   (0, ord('Z')): functions.previous,
   (0, ord('B')): functions.next,
   (0, ord('V')): functions.stop,
   (0, ord(';')): functions.reset_fx,
   (0, wx.WXK_UP): functions.volume_up,
   (0, wx.WXK_DOWN): functions.volume_down,
   (0, wx.WXK_LEFT): functions.rewind,
   (0, wx.WXK_RIGHT): functions.fastforward,
   (0, ord('J')): self.pan_left,
   (0, ord('L')): self.pan_right,
   (0, ord('I')): self.frequency_up,
   (0, ord('K')): self.frequency_down,
   (0, ord('F')): functions.do_search,
   (0, ord('G')): lambda event: functions.do_search(search = self.last_search),
   (0, ord('8')): lambda event: Thread(target = functions.add_again_to_playlist, args = [event]).start(),
   (0, wx.WXK_RETURN): functions.focus_playing
  }
  self.last_search = '' # Whatever the user last searched for.
  self.current_playlist = None # The current playlist
  self.current_station = None # The current radio station.
  self.current_library = None # The library in it's current state.
  self.current_saved_result = None # The index of the currently focused daved result.
  self.saved_results_indices = {} # IDs of saved results.
  self._current_track = None # The metadata for the currently playing track.
  self.current_track = None
  self._queue = [] # The actual queue of tracks.
  self.track_history = [] # The play history.
  self.results_history_index = 0 # The index of the results history.
  self.bypass_history = False # Bypass the results history on the next insertion.
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  if application.platform == 'darwin':
   self.results = dv.DataViewListCtrl(p) # User friendly track list.
   self.results.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.select_item)
   self.queue = dv.DataViewListCtrl(p)
   self.queue.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.select_item)
  else:
   self.results = wx.ListCtrl(p, style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
   self.results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.select_item)
   self.queue = wx.ListCtrl(p, style = wx.LC_REPORT)
   self.queue.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.select_item)
  self.results.SetFocus()
  self._results = [] # The raw json from Google.
  self.init_results_columns()
  for x, y in enumerate(['Name', 'Artist', 'Album', 'Duration']):
   if application.platform == 'darwin':
    self.queue.AppendTextColumn(y)
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
  s2.Add(wx.StaticText(p, label = application.config.get('windows', 'frequency_label')), 0, wx.GROW)
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
  s3.Add(wx.StaticText(p, label = application.config.get('windows', 'pan_label')), 0, wx.GROW)
  self.pan = wx.Slider(p)
  self.pan.SetValue((application.config.get('sound', 'pan') + 1.0) * 50.0)
  self.pan.Bind(wx.EVT_SLIDER, self.set_pan)
  s3.Add(self.pan, 1, wx.GROW)
  s.Add(s3, 1, wx.GROW)
  l = 'No song playing.'
  if application.platform == 'darwin':
   self.artist_bio = wx.StaticText(p, label = l)
   self.set_artist_bio = lambda value: self.artist_bio.SetLabel(value)
  else:
   self.artist_bio = wx.TextCtrl(p, style = wx.TE_MULTILINE|wx.TE_READONLY, value = l)
   self.set_artist_bio = lambda value: self.artist_bio.SetValue(value)
  s.Add(self.artist_bio, 1, wx.GROW)
  s4 = wx.BoxSizer(wx.HORIZONTAL)
  s4.Add(wx.StaticText(p, label = application.config.get('windows', 'now_playing_label')), 0, wx.GROW)
  self.hotkey_area = wx.TextCtrl(p)
  self.hotkey_area.Bind(wx.EVT_KEY_DOWN, self.hotkey_parser)
  s4.Add(self.hotkey_area, 1, wx.GROW)
  s.Add(s4, 0, wx.GROW)
  p.SetSizerAndFit(s)
  mb = wx.MenuBar()
  file_menu = wx.Menu()
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'n',
  lambda event: NewPlaylist().Show(True),
  '&New Playlist...',
  'Create a new playlist.'
  ))
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 's',
  lambda event: self.add_saved_result(),
  '&Save Results...',
  'Save the current results to the saved results list.'
  ))
  station_menu = wx.Menu()
  station_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '9',
  lambda event: Thread(target = functions.station_from_result, args = [event]).start(),
  'Create Station From Current &Result...',
  'Creates a radio station from the currently focused result.'
  ))
  station_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_ALT, '4',
  lambda event: Thread(target = functions.station_from_artist, args = [event]).start(),
  'Create Station From Current &Artist',
  'Create a radio station based on the currently focused artist.'
  ))
  station_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_ALT, '5',
  lambda event: Thread(target = functions.station_from_album, args = [event]).start(),
  'Create Station From Current A&lbum',
  'Create a radio station based on the currently focused album.'
  ))
  station_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_ALT, '6',
  lambda event: Thread(target = functions.station_from_genre, args = [event]).start(),
  'Create Station From &Genre',
  'Create a radio station based on a particular genre.'
  ))
  file_menu.AppendMenu(wx.ID_ANY, 'Create &Station', station_menu, 'Create radio stations from various sources')
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '8',
  lambda event: Thread(target = functions.add_to_playlist, args = [event]).start(),
  'Add Current Result To &Playlist...',
  'Add the current result to one of your playlists.'
  ))
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_DELETE,
  functions.delete,
  '&Delete',
  'Removes an item from the play queue if selected, the library or the currently focused playlist.'
  ))
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_F2,
  lambda event: NewPlaylist(self.current_playlist).Show() if self.current_playlist else wx.Bell(),
  '&Edit Current Playlist...',
  'Edit the properties of the currently focused playlist.'
  ))
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_DELETE,
  functions.delete_thing,
  '&Delete Currently focused thing'
  ))
  file_menu.AppendSeparator()
  self.Bind(
  wx.EVT_MENU,
  functions.reveal_media,
  file_menu.Append(
  wx.ID_ANY,
  '&Reveal Media Directory',
  'Open the media directory in %s' % ('Finder' if sys.platform == 'darwin' else 'Windows Explorer')
  ))
  file_menu.AppendSeparator()
  file_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'q',
  lambda event: self.Close(True),
  'E&xit',
  'Quit the program.'
  ))
  mb.Append(file_menu, '&File')
  edit_menu = wx.Menu()
  edit_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'f',
  lambda event: Thread(target = functions.do_search, args = [event]).start(),
  '&Find...',
  'Find a song.'
  ))
  edit_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'g',
  lambda event: Thread(target = functions.do_search, args = [event, self.last_search]).start(),
  'Find &Again',
  'Repeat the previous search.'
  ))
  edit_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '/',
  lambda event: Thread(target = functions.add_to_library, args = [event]).start(),
  '&Add To Library',
  'Add the current song to the library.'
  ))
  mb.Append(edit_menu, '&Edit')
  view_menu = wx.Menu()
  view_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_ALT, wx.WXK_RETURN,
  functions.focus_playing,
  '&Focus Current',
  'Focus the currently playing track.'
  ))
  view_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL|wx.ACCEL_SHIFT, 'l',
  functions.get_lyrics,
  'View &Lyrics',
  'View lyrics for the currently selected result.'
  ))
  mb.Append(view_menu, '&View')
  source_menu = wx.Menu()
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'l',
  lambda event: Thread(target = self.init_results, args = [event]).start(),
  '&Library',
  'Return to the library.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '1',
  lambda event: Thread(target = functions.select_playlist, args = [event]).start(),
  'Select &Playlist...',
  'Select a playlist.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_SHIFT, wx.WXK_RETURN,
  lambda event: Thread(target = functions.add_again_to_playlist, args = [event]).start(),
  'Add A&gain To The Previously Selected Playlist',
  'Adds the current result to the playlist which items were last added too.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '2',
  lambda event: Thread(target = functions.select_station, args = [event]).start(),
  'Select &Station...',
  'Select a radio station.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, ';',
  lambda event: Thread(target = functions.top_tracks, kwargs = {'interactive': True}).start(),
  'Artist &Top Tracks',
  'Get the top tracks for the artist of the currently selected song.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '3',
  lambda event: Thread(target = functions.promoted_songs, args = [event]).start(),
  '&Promoted Songs',
  'Get a list of promoted tracks.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '4',
  lambda event: Thread(target = functions.artist_tracks, args = [event]).start(),
  'Go To Current &Artist',
  'Get a list of all tracks by the artist of the currently selected song.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '5',
  lambda event: Thread(target = functions.current_album, args = [event]).start(),
  'Go To Current A&lbum',
  'Go to the current album.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '6',
  lambda event: Thread(target = functions.artist_album, args = [event]).start(),
  'Select Al&bum...',
  'Go to a particular album.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '7',
  lambda event: Thread(target = functions.related_artists, args = [event]).start(),
  'Select &Related Artist...',
  'Select a related artist to view tracks.'
  ))
  source_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '0',
  lambda event: Thread(target = functions.all_playlist_tracks, args = [event]).start(),
  'Loa&d All Playlist Tracks',
  'Load every item from every playlist into the results table.'
  ))
  mb.Append(source_menu, '&Source')
  track_menu = wx.Menu()
  track_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_RETURN,
  lambda event: Thread(target = functions.queue_result, args = [event]).start(),
  '&Queue Item',
  'Add the currently selected item to the play queue.'
  ))
  mb.Append(track_menu, '&Track')
  play_menu = wx.Menu()
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_RETURN,
  self.select_item,
  '&Select Current Item',
  'Selects the current item.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, ' ',
  functions.play_pause,
  '&Play or Pause',
  'Play or pause the currently playing song.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_UP,
  lambda event: Thread(target = functions.volume_up, args = [event]).start(),
  'Volume &Up',
  'Increase the Volume.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_DOWN,
  lambda event: Thread(target = functions.volume_down, args = [event]).start(),
  'Volume &Down',
  'Decrease the volume.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_LEFT,
  lambda event: event.Skip() if self.artist_bio.HasFocus() else Thread(target = functions.previous, args = [event]).start(),
  '&Previous',
  'Play the previous track.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, wx.WXK_RIGHT,
  lambda event: event.Skip() if self.artist_bio.HasFocus() else Thread(target = functions.next, args = [event]).start(),
  '&Next',
  'Play the next track.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '.',
  functions.stop,
  '&Stop',
  'Stop the currently playing song.'
  ))
  self.stop_after = play_menu.AppendCheckItem(
  *self.add_accelerator(
  wx.ACCEL_CTRL|wx.ACCEL_SHIFT, '.',
  self.toggle_stop_after,
  'Stop &After',
  'Stop after the currently playing track has finished playing.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_SHIFT, wx.WXK_LEFT,
  lambda event: Thread(target = functions.rewind, args = [event]).start(),
  '&Rewind',
  'Rewind.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_SHIFT, wx.WXK_RIGHT,
  lambda event: Thread(target = functions.fastforward, args = [event]).start(),
  '&Fastforward',
  'Fastforward.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'h',
  lambda event: self.add_results(functions.shuffle(self.get_results()), True, playlist = self.current_playlist, station = self.current_station, library = self.current_library),
  'Shuffle &Results',
  'Shuffle the currently shown results.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL|wx.ACCEL_SHIFT, 'h',
  lambda event: self.queue_tracks(functions.shuffle(self.get_queue()), True),
  'Shuffle &Queue',
  'Shuffle the play queue.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_SHIFT, wx.WXK_UP,
  self.frequency_up,
  'Frequency &Up',
  'Shift the frequency up a little.'
  ))
  play_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_SHIFT, wx.WXK_DOWN,
  self.frequency_down,
  'Frequency &Down',
  'Shift the frequency down a little.'
  ))
  mb.Append(play_menu, '&Play')
  self.history_menu = wx.Menu()
  self.history_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '[',
  functions.results_history_back,
  '&Back',
  'Moves back through the results history.'
  ))
  self.history_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, ']',
  functions.results_history_forward,
  '&Forward',
  'Move forward through the results history.'
  ))
  mb.Append(self.history_menu, '&History')
  options_menu = wx.Menu()
  options_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, ',',
  lambda event: application.config.get_gui().Show(True),
  '&Preferences',
  'Configure the program.',
  id = wx.ID_PREFERENCES
  ))
  options_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, '\\',
  functions.reset_fx,
  '&Reset FX',
  'Reset pan and frequency.'
  ))
  options_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_F12,
  lambda event: Thread(target = functions.select_output, args = [event]).start(),
  '&Select sound output...',
  'Select a new output device for sound playback.'
  ))
  options_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'j',
  lambda event: ColumnEditor().Show(True),
  '&View Options...',
  'Configure the columns for the table of results.'
  ))
  options_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_F11,
  lambda event: PythonConsole().Show(True),
  '&Python Console...',
  'Launch a Python console for development purposes.'
  ))
  self.repeat = options_menu.AppendCheckItem(
  *self.add_accelerator(
  wx.ACCEL_CTRL, 'r',
  self.toggle_repeat,
  '&Repeat',
  'Repeat tracks.'
  ))
  self.repeat.Check(application.config.get('sound', 'repeat'))
  mb.Append(options_menu, '&Options')
  help_menu = wx.Menu()
  help_menu.Append(
  *self.add_accelerator(
  wx.ACCEL_NORMAL, wx.WXK_F1,
  lambda event: wx.AboutBox(application.info),
  '&About...',
  'About the program.',
  id = wx.ID_ABOUT
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
  #self._results.remove(self.get_results()[result])
 
 def add_results(self, results, clear = False, bypass_history = False, scroll_history = True, playlist = None, station = None, library = None, saved_result = None):
  """Adds multiple results using self.add_result. If playlist is provided, store the ID of the current playlist so we can perform operations on it."""
  if not self.bypass_history:
   r = self.get_results()
   if r and (not application.results_history or r != application.results_history[-1]): # Don't save blank or duplicate results.
    application.results_history.append([[r], {'playlist': self.current_playlist, 'library': self.current_library, 'station': self.current_station, 'saved_result': self.current_saved_result, 'clear': True}])
    while len(application.results_history) > application.config.get('library', 'history_length'):
     del application.results_history[0] # Make sure the results history doesn't get too large.
  if scroll_history:
   application.results_history_index = len(application.results_history)
  self.bypass_history = bypass_history
  self.current_playlist = playlist # Keep a record of what playlist we're in, so we can delete items and reload them.
  self.current_station = station # The current station for delete and such.
  self.current_library = library
  self.current_saved_result = saved_result
  if clear:
   self.clear_results()
  map(self.add_result, results)
  self.results.SetFocus()
 
 def clear_results(self):
  """Clears the results table."""
  self._results = []
  self.results.DeleteAllItems()
 
 def init_results(self, event = None):
  """Initialises the results table."""
  songs = application.mobile_api.get_all_songs()
  wx.CallAfter(self.add_results, songs, True, library = songs)
 
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
   self.title = functions.format_title(self.get_current_track()) if self.get_current_track() else None
  else:
   self.title = value
  self.hotkey_area.SetValue(self.title)
  title = application.name
  if self.title:
   title += ' (%s)' % self.title
  return super(MainFrame, self).SetTitle(title)
 
 def select_item(self, event):
  """Play the track under the mouse."""
  ctrl = self.FindFocus()
  if application.platform == 'darwin':
   ctrl = self.results
   func = self.get_results
  elif ctrl == self.queue:
   func = self.get_queue
  elif ctrl == self.results:
   func = self.get_results
  else:
   return event.Skip()
  id = self.get_current_result(ctrl)
  if id == -1:
   return wx.Bell()
  track = func()[id]
  if ctrl == self.queue:
   self.unqueue_item(id)
  Thread(target = self.play, args = [track]).start()
 
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
 
 def get_current_queue_result(self):
  """Same as get_current_result, but with the queue."""
  if application.platform == 'darwin':
   return self.queue.GetSelection().GetID() - 1
  else:
   return self.queue.GetFocusedItem()
 
 def play(self, item, history = True, play = True):
  """Plays the track given in item. If history is True, add any current track to the history."""
  id = functions.get_id(item)
  track = None # The object to store the track in until it's ready for playing.
  error = None # Any error that occured.
  fname = id + application.track_extension
  path = functions.id_to_path(id)
  if id not in application.library or (application.library[id] and application.library[id] != item.get('lastModifiedTimestamp', application.library[id])): # Our version is older, download again
   try:
    url = application.mobile_api.get_stream_url(id)
   except gmusicapi.exceptions.CallFailure as e:
    application.device_id = None
    return wx.MessageBox('Cannot play with that device: %s.' % e, 'Invalid Device')
   except functions.RE as e:
    if self.current_track:
     self.current_track.set_position(self.current_track.get_length() - 1)
     self.play_pause.SetLabel(application.config.get('windows', 'play_label'))
    return wx.MessageBox(*functions.format_requests_error(e))
   try:
    track = URLStream(url = url)
   except BassError as e:
    error = e # Just store it for later alerting.
   Thread(target = functions.download_file, args = [id, url, item.get('lastModifiedTimestamp', 0)]).start()
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
  if application.lyrics_frame:
   Thread(target = application.lyrics_frame.populate_lyrics, args = [item.get('artist'), item.get('title')]).start()
  self.current_track = track
  self.SetTitle()
  self.duration = columns.parse_durationMillis(self.get_current_track().get('durationMillis'))
  self.update_hotkey_area()
  self.current_track.set_volume(application.config.get('sound', 'volume'))
  self.current_track.set_pan(application.config.get('sound', 'pan'))
  self.set_frequency()
  if play:
   self.current_track.play()
   self.play_pause.SetLabel(application.config.get('windows', 'pause_label'))
  else:
   self.play_pause.SetLabel(application.config.get('windows', 'play_label'))
  try:
   application.mobile_api.increment_song_playcount(id)
   self.artist_info = application.mobile_api.get_artist_info(item['artistId'][0])
   try:
    self.set_artist_bio(self.artist_info.get('artistBio', 'No information available.'))
   except wx.PyDeadObjectError:
    pass # The frame has been deleted.
  except functions.RE:
   pass # We are not connected to the internet, but we can still play stuff.
 
 def set_volume(self, event):
  """Sets the volume with the slider."""
  application.config.set('sound', 'volume', self.volume.GetValue() / 100.0)
  if self.current_track:
   self.current_track.set_volume(application.config.get('sound', 'volume'))
 
 def set_pan(self, event = None):
  """Sets pan with the slider."""
  application.config.set('sound', 'pan', (self.pan.GetValue() / 50.0) - 1.0)
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
    self.update_hotkey_area()
    if self.current_track:
     p = self.current_track.get_position()
     l = self.current_track.get_length()
     self.current_pos = p / (l / int(self.get_current_track().get('durationMillis')))
     i = min(l, int(p / (l / 100.0)))
     if not self.track_position.HasFocus() and i != self.track_position.GetValue():
      self.track_position.SetValue(i)
     if self.current_track.get_position() == self.current_track.get_length() and not self.stop_after.IsChecked():
      functions.next(None, interactive = False)
    sleep(1)
   except wx.PyDeadObjectError:
    pass # The window has probably closed.
 
 def get_current_result(self, ctrl = None):
  """Returns the current result."""
  if not ctrl:
   ctrl = self.results
  if application.platform == 'darwin':
   return ctrl.GetSelection().GetID() - 1
  else:
   return ctrl.GetFocusedItem()
 
 def do_close(self, event):
  """Closes the window after shutting down the track thread."""
  if not application.config.get('windows', 'confirm_quit') or wx.MessageBox('Are you sure you want to close the program?', 'Really Close', style = wx.YES_NO) == wx.YES:
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
    width = column.get('width', -1)
    if application.platform == 'darwin':
     self.results.AppendTextColumn(name, width = width)
    else:
     self.results.InsertColumn(i, name, width = width)
 
 def reload_results(self):
  """Reloads the results table."""
  self.init_results_columns()
  self.add_results(self.get_results(), clear = True, playlist = self.current_playlist, library = self.current_library, station = self.current_station)
 
 def hotkey_parser(self, event):
  """Handles Winamp-Style hotkeys."""
  k = (event.GetModifiers(), event.GetKeyCode())
  if k in self.hotkeys:
   self.hotkeys[k](event)
  else:
   event.Skip()
 
 def toggle_stop_after(self, event):
  """Toggles the stop after menu item."""
  application.config.toggle('sound', 'stop_after')
  self.stop_after.Check(application.config.get('sound', 'stop_after'))
 
 def toggle_repeat(self, event):
  """Toggles the repeat setting."""
  application.config.toggle('sound', 'repeat')
  self.repeat.Check(application.config.get('sound', 'repeat'))
 
 def add_accelerator(self, modifiers, key, func, title, description = None, id = None):
  """Adds an accelerator to the table."""
  if not description:
   description = getdoc(func)
  key = ord(key.upper()) if issubclass(type(key), basestring) else key
  if not id:
   id = wx.NewId()
  self.Bind(wx.EVT_MENU, func, id = id)
  self._accelerator_table.append((modifiers, key, id))
  self.accelerator_table[id] = {
   'title': title.strip('&'),
   'description': description
  }
  self.SetAcceleratorTable(wx.AcceleratorTable(self._accelerator_table))
  key_str = ''
  for m, v in mods.iteritems():
   if modifiers & m == m:
    key_str += '%s%s' % ('+' if key_str else '', v)
  if key_str:
   key_str += '+'
  if key in keys:
   key_str += keys.get(key)
  else:
   key_str += chr(key)
  key_str = ' %s' % key_str
  return [id, title + key_str, description]
 
 def select_results_history(self, pos):
  """Selects an item from the results history."""
  args, kwargs = application.results_history[pos]
  kwargs['bypass_history'] = True
  kwargs['scroll_history'] = False
  self.add_results(*args, **kwargs)
  application.results_history_index = pos
 
 def add_saved_result(self, name = None, results = None):
  """Saves results to the config and the history menu."""
  if not results:
   results = self.get_results()
  if not results:
   return wx.Bell()
  if not name:
   dlg = wx.TextEntryDialog(self, 'Enter a name for this result', 'Save Result')
   if dlg.ShowModal() == wx.ID_OK:
    name = dlg.GetValue()
   dlg.Destroy()
  if name:
   if name not in application.saved_results or wx.MessageBox('There is already a saved result by that name. Replace?', 'Duplicate Name', style = wx.YES_NO) == wx.YES:
    application.saved_results[name] = results
    self.current_saved_result = name
    id = wx.NewId()
    self.saved_results_indices[name] = id
    self.Bind(
    wx.EVT_MENU,
    lambda event: self.add_results(application.saved_results[name], clear = True, saved_result = name),
    self.history_menu.Append(
    id,
    '&%s' % name,
    'Load the %s saved history item.' % name
    ))
 
 def delete_saved_result(self, name):
  """Deletes the saved result pointed too by id."""
  self.history_menu.Delete(self.saved_results_indices[name])
  del self.saved_results_indices[name]
  del application.saved_results[name]
 
 
 def update_hotkey_area(self):
  """Updates the value of self.hotkey_area."""
  if self.current_track:
   self.hotkey_area.SetValue(application.config.get('windows', 'now_playing_format').format(pos = columns.parse_durationMillis(self.current_pos), duration = self.duration, title = self.title))
  else:
   self.hotkey_area.SetValue('No track playing.')
