"""Various functions used in the program."""

import application, wx, os, requests, sys, random, library, logging, columns, config
from gmusicapi.exceptions import CallFailure
from accessible_output2.outputs.auto import Auto
from shutil import copy as shcopy, rmtree
RE = (requests.exceptions.RequestException, requests.adapters.ReadTimeoutError, IOError)
from sound_lib.main import BassError
from time import time, ctime
from gui.lyrics_viewer import LyricsViewer
from gui.search_frame import SearchFrame, songs
from gui.url_frame import URLFrame
from copy import copy
from threading import Thread, current_thread

output = Auto()
logger = logging.getLogger('Functions')

id_fields = [
 'storeId',
 'id',
 'trackId',
 'nid',
]

def format_title(track):
 stuff = {} # Stuff for format().
 try:
  for k, v in track.items():
   stuff[k] = getattr(columns, 'parse_%s' % k, lambda value: value)(v)
  return config.config.get('windows', 'title_format').format(**stuff)
 except KeyError as e:
  logger.exception(e)
  return 'Error in title format: %s.' % e

def config_update(config, section, option, value):
 """Ran when apply or OK is clicked in the options window."""
 if section == 'sound':
  if option == 'repeat':
   frame.repeat.Check(value)
  elif option == 'repeat_track':
   frame.repeat_track.Check(value)
  elif option == 'stop_after':
   frame.stop_after.Check(value)
  elif option == 'volume':
   frame.volume.SetValue(value)
   frame.set_volume()
  elif option == 'pan':
   frame.pan.SetValue(value)
   frame.set_pan()
 elif section == 'windows':
  if option == 'play_controls_show':
   frame.play_controls_func(value)
  elif option == 'title_format':
   frame.SetTitle()
   cr = frame.get_current_result()
   frame.reload_results()
   frame.results.SetSelection(cr)
 elif section == 'http' and option in ['enabled', 'hostname', 'port']:
  Thread(target = frame.reload_http_server).start()

def get_id(item):
 """Return the ID for the provided item."""
 for f in id_fields:
  if f in item:
   return item.get(f)

def in_library(id):
 """Checks if the given ID is in the library."""
 lib = application.mobile_api.get_all_songs()
 for l in lib:
  if get_id(l) == id:
   return True
 return False

def select_artist(artists):
 """Given a list of artists, selects one, with user intervention if there is more than one in the list."""
 artists = list(set(artists))
 if len(artists) >1:
  a = {}
  for x in artists:
   try:
    a[x] = application.mobile_api.get_artist_info(x).get('name', 'Unknown')
   except RE as e:
    return wx.MessageBox(*format_requests_error(e))
  dlg = wx.SingleChoiceDialog(frame, 'Select an artist', 'This track has multiple artists', a.values())
  if dlg.ShowModal() == wx.ID_OK:
   artist = a.keys()[dlg.GetSelection()]
   dlg.Destroy()
  else:
   artist = None
 else:
  artist = artists[0]
 return artist

def reveal_media(event):
 """Opens the media directory in the file manager."""
 if sys.platform == 'darwin':
  cmd = 'open'
 else:
  cmd = 'explorer'
 os.system('%s "%s"' % (cmd, library.media_directory()))

def add_to_library(event):
 """Adds the current result to the library."""
 cr = frame.get_current_result()
 if frame.current_library or cr == -1:
  return bell() # Can't add stuff in the library to the library, or there's nothing selected to add.
 track = frame.get_results()[cr]
 id = get_id(track)
 try:
  application.mobile_api.add_aa_track(id)
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.MessageBox('Added %s to your library.' % format_title(track), 'Track Added')

def select_playlist(event = None, playlists = None, playlist = None, interactive = True):
 """Allows you to pick a playlist with a GUI."""
 api = application.mobile_api
 if not playlists:
  playlists = api.get_all_user_playlist_contents()
 if playlist:
  for p in playlists:
   if p['id'] == playlist:
    playlist = p
    break
  else:
   return ValueError('Provided playlist does not exist.')
 else:
  dlg = wx.SingleChoiceDialog(frame, 'Select a playlist', 'Select Playlist', [x['name'] for x in playlists])
  if dlg.ShowModal() == wx.ID_OK:
   playlist = playlists[dlg.GetSelection()]
  dlg.Destroy()
 if interactive:
  if playlist:
   try:
    tracks = application.mobile_api.get_shared_playlist_contents(playlist['shareToken'])
   except Exception as e:
    logging.exception(e)
    return wx.MessageBox('Could not load the %s playlist. See log for details.' % playlist['name'], 'Error Loading Playlist', style = wx.ICON_EXCLAMATION)
   stuff = [] # The actual tracks to pass to add_results.
   not_loaded = 0 # The number of tracks that couldn't be loaded.
   for t in tracks:
    if 'track' in t:
     logging.debug('Parsed track: %s.', format_title(t['track']))
     stuff.append(t['track'])
    else:
     logging.warning('No track data found for track (ID = %s): %s.', get_id(t), t)
     not_loaded += 1
   if not_loaded:
    wx.MessageBox('Failed to load %s track%s. See warning log for details.' % (not_loaded, '' if not_loaded == 1 else 's'), 'Load Error', style = wx.ICON_EXCLAMATION)
   wx.CallAfter(frame.add_results, stuff, True, playlist = playlist)
 else:
  return playlist

def select_station(event = None, station = None, interactive = True):
 """Select a radio station."""
 try:
  stations = application.mobile_api.get_all_stations()
 except RE as e:
  if interactive:
   return wx.MessageBox(*format_requests_error(e))
  else:
   return None
 if station:
  for s in stations:
   if s['id'] == station:
    station = s
 else:
  dlg = wx.SingleChoiceDialog(frame, 'Select a radio station', 'Select Station', [x['name'] for x in stations])
  if dlg.ShowModal() == wx.ID_OK:
   station = stations[dlg.GetSelection()]
  dlg.Destroy()
 if interactive:
  if station:
   try:
    tracks = application.mobile_api.get_station_tracks(station['id'], config.config.get('library', 'max_results'))
    wx.CallAfter(frame.add_results, tracks, True, station = station)
   except RE as e:
    return wx.MessageBox(*format_requests_error(e))
 else:
  return station

def play_pause(event = None):
 """Play or pause the music."""
 #announce('Play Pause')
 if frame.current_track:
  if frame.current_track.is_paused or frame.current_track.is_stopped:
   frame.current_track.play()
   frame.play_pause.SetLabel(config.config.get('windows', 'pause_label'))
  else:
   frame.current_track.pause()
   frame.play_pause.SetLabel(config.config.get('windows', 'play_label'))
 else:
  bell()

def stop(event = None):
 """Stop the current track."""
 #announce('Stop.')
 if frame.current_track:
  frame.current_track.pause()
  frame.current_track.set_position(0) # Pause instead of stopping.
  frame.play_pause.SetLabel(config.config.get('windows', 'play_label'))

def volume_up(event = None):
 """Turn up the playing song."""
 #announce('Volume Up.')
 v = config.config.get('sound', 'volume_increment') + frame.volume.GetValue()
 if v > 100:
  v = 100
  bell()
 set_volume(v)

def volume_down(event = None):
 """Turn down the playing song."""
 #announce('Volume Down.')
 v = frame.volume.GetValue() - config.config.get('sound', 'volume_decrement')
 if v < 0:
  v = 0
  bell()
 set_volume(v)

def set_volume(v):
 """Set the volume. Return True upon success, or False otherwise."""
 frame.volume.SetValue(v)
 frame.set_volume()

def get_previous_song(alter = False):
 """Get the song which will be played when the previous button is pressed. If alter is True, actually remove the track from the history buffer."""
 if frame.track_history:
  return frame.track_history[-1]
  if alter:
   del frame.track_history[-1]

def previous(event = None):
 """Select the previous track."""
 #announce('Previous.')
 if not frame.track_history:
  if frame.current_track:
   frame.current_track.play(True)
  else:
   return bell()
 else:
  q = frame.get_queue()
  if q:
   q.insert(0, frame.get_current_track())
  frame.queue_tracks(q, True)
  frame.play(get_previous_song(), history = False)

def get_next_song(clear = False):
 """Get the next song from the play queue or list of results. If clear is True, unqueue the resulting track."""
 q = copy(frame.get_queue())
 if q:
  if clear:
   frame.unqueue_track(0)
  return q[0]
 else:
  q = frame.get_results()
  track = frame.get_current_track()
  if track in q:
   cr = q.index(track) + 1
   if cr == len(q):
    if config.config.get('sound', 'repeat') and q:
     return q[0]
    else:
     return # User has not selected repeat or there are no results there.
   else:
    return q[cr]
  else:
   if q:
    return q[0]
   else:
    return # There are no results.

def next(event = None, interactive = True):
 """Plays the next track."""
 #announce('Next.')
 if config.config.get('sound', 'repeat_track'):
  q = frame.get_current_track()
 else:
  q = get_next_song(True)
 if q:
  frame.play(q)
  return True
 else:
  if interactive:
   bell()
  return False

def rewind(event):
 """Rewind the track a bit."""
 #announce('Rewind.')
 track = frame.current_track
 if not track:
  bell()
 else:
  pos = track.get_position() - config.config.get('sound', 'rewind_amount')
  if pos < 0:
   pos = 0
  track.set_position(pos)

def fastforward(event):
 """Fastforward the track a bit."""
 #announce('Fast Forward.')
 track = frame.current_track
 if not track:
  bell()
 else:
  pos = min(track.get_position() + config.config.get('sound', 'rewind_amount'), track.get_length())
  try:
   track.set_position(pos)
  except Exception as e:
   return bell() # Something went wrong.

def prune_library():
 """Delete the oldest track from the library."""
 delete_stamp = time()
 delete_id = None
 for id, track in library.downloaded.items():
  if library.exists(track):
   t = os.path.getatime(library.get_path(track))
   if t < delete_stamp:
    delete_stamp = t
    delete_id = id
  else:
   del library.downloaded[id]
 if delete_id:
  delete_path(library.get_path(library.downloaded[delete_id]))
  del library.downloaded[delete_id]
  clean_library()
  return delete_id

def clean_library():
 """Erase all the folders that don't have any entries in library.downloaded associated with them."""
 for artist in os.listdir(library.media_directory()):
  if artist not in [x['artist'] for x in library.downloaded.values()]:
   delete_path(os.path.join(library.media_directory(), artist))

def download_file(url, id, info, callback = lambda info: None):
 """Download the track from url, add ID to the list of downloaded tracks, and store it in the media directory. Finally call callback with the provided info as the only argument."""
 t = time()
 logging.info('Starting download of %s at %s.', format_title(info), ctime(t))
 library.downloading[id] = t
 try:
  g = requests.get(url)
  logging.info('Download completed successfully in %s seconds.', time() - t)
 except RE as e:
  logging.info('Download failed...')
  logging.exception(e)
 finally:
  del library.downloading[id]
 if g.status_code == 200:
  path = library.get_path(info)
  with open(path, 'wb') as f:
   f.write(g.content)
   logging.info('Dumped file to %s.', path)
  library.downloaded[id] = dict(
   artist = info.get('artist', 'Unknown Artist'),
   album = info.get('album', 'Unknown Album'),
   title = info.get('title', 'Unnamed'),
   trackNumber = info.get('trackNumber', 0)
  )
  while get_size(library.media_directory()) > ((config.config.get('library', 'library_size') * 1024) * 1024):
   prune_library()
  callback(info)
  return True
 else:
  logging.error('Download failed with status code %s.', g.status_code)
  return False

def track_seek(event):
 """Get the value of the seek slider and move the track accordingly."""
 track = frame.current_track
 if track:
  try:
   track.set_position(int((track.get_length() / 100.0) * frame.track_position.GetValue()))
  except BassError:
   pass # Don't care.

def do_search(event = None, search = None, type = None, interactive = True):
 """Search google music."""
 if not search:
  search = frame.last_search
 if type == None:
  type = frame.last_search_type
 s = SearchFrame(search, type)
 if interactive:
  s.Show(True)
 else:
  s.do_search()

def do_search_again(event):
 """Repeat the previous search."""
 announce('Find Again.')
 return do_search(search = frame.last_search, type = frame.last_search_type, interactive = False)

def do_search_quick(event):
 """Search quickly."""
 old_search_string = copy(frame.last_search)
 old_search_type = copy(frame.last_search_type)
 dlg = wx.TextEntryDialog(frame, 'Search for songs', 'Quick Search', old_search_string)
 if dlg.ShowModal() == wx.ID_OK:
  old_search_string = dlg.GetValue()
  do_search(search = old_search_string, type = songs, interactive = False)
 dlg.Destroy()
 frame.last_search = old_search_string
 frame.last_search_type = old_search_type

def select_output(event = None):
 """Selects a new audio output."""
 o = application.sound_output
 p = getattr(o, '__class__')
 dlg = wx.SingleChoiceDialog(frame, 'Select Output Device', 'Select an output device from the list', ['Default'] + o.get_device_names())
 if dlg.ShowModal() == wx.ID_OK:
  if frame.current_track:
   loc = frame.current_track.get_position()
   playing = frame.current_track.is_playing
   item = frame.get_current_track()
   frame.current_track = None
  else:
   item = None
  o.free()
  res = dlg.GetSelection()
  if not res:
   res = -1
  logging.debug('Setting output device: %s.', res)
  application.sound_output = p(device = res)
  if item:
   frame.play(item, play = playing)
   frame.current_track.set_position(loc)
 dlg.Destroy()

def promoted_songs(event):
 """Get promoted songs."""
 try:
  songs = application.mobile_api.get_promoted_songs()
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(frame.add_results, songs, True)

def focus_playing(event):
 """Scrolls the results view to the currently playing track, if it's in the list."""
 announce('Focus Playing.')
 track = frame.get_current_track()
 if track:
  if track in frame.get_results():
   pos = frame.get_results().index(track)
   frame.results.Select(pos)
  else:
   frame.add_results([track], clear = True, bypass_history = True)
 else:
  return bell()

def artist_tracks(event = None, id = None):
 """Get all tracks for a particular artist."""
 announce('Artist Tracks.')
 if id == None:
  cr = frame.get_current_result()
  if cr == -1:
   return bell() # There is no track selected yet.
  id = select_artist(frame.get_results()[cr]['artistId'])
 try:
  info = application.mobile_api.get_artist_info(id)
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(frame.clear_results)
 tracks = [] # The final list of tracks for add_results.
 for a in info['albums']:
  try:
   a = application.mobile_api.get_album_info(a['albumId'])
  except RE as e:
   wx.CallAfter(frame.add_results, tracks)
   return wx.MessageBox(*format_requests_error(e))
  tracks += a.get('tracks', [])
 wx.CallAfter(frame.add_results, tracks, True)

def current_album(event):
 """Selects the current album."""
 announce('Current Album.')
 cr = frame.get_current_result()
 if cr == -1:
  return bell() # No row selected.
 try:
  songs = application.mobile_api.get_album_info(frame.get_results()[cr]['albumId']).get('tracks', [])
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(frame.add_results, songs, True)

def artist_album(event, albums = None):
 """Selects a particular artist album."""
 if albums:
  show_artists = True
 else:
  show_artists = False
  cr = frame.get_current_result()
  if cr == -1:
   return bell()
  artists = frame.get_results()[cr]['artistId']
  artist = select_artist(artists)
  if not artist:
   return
  try:
   albums = application.mobile_api.get_artist_info(artist).get('albums', [])
  except RE as e:
   return wx.MessageBox(*format_requests_error(e))
 dlg = wx.SingleChoiceDialog(frame, 'Select an album', 'Album Selection', ['%s%s (%s)' % (x.get('artist', 'Unknown') + ' - ' if show_artists else '', x.get('name', 'Unnamed'), x.get('year')) for x in albums])
 if dlg.ShowModal() == wx.ID_OK:
  res = dlg.GetSelection()
  dlg.Destroy()
  try:
   songs = application.mobile_api.get_album_info(albums[res]['albumId']).get('tracks', [])
   wx.CallAfter(frame.add_results, songs, True)
  except RE as e:
   wx.MessageBox(*format_requests_error(e))

def related_artists(event):
 """Selects and views tracks for a related artist."""
 cr = frame.get_current_result()
 if cr == -1:
  return bell()
 artist = select_artist(frame.get_results()[cr]['artistId'])
 if not artist:
  return # User canceled.
 try:
  related = application.mobile_api.get_artist_info(artist).get('related_artists', [])
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 dlg = wx.SingleChoiceDialog(frame, 'Select an artist', 'Related Artists', [x.get('name', 'Unknown') for x in related])
 if dlg.ShowModal() == wx.ID_OK:
  artist = related[dlg.GetSelection()].get('artistId')
  dlg.Destroy()
  if not artist:
   return # No clue...
  try:
   tracks = top_tracks(artist)
  except RE as e:
   return wx.MessageBox(*format_requests_error(e))
  wx.CallAfter(frame.add_results, tracks, True)

def all_playlist_tracks(event):
 """Add every track from every playlist."""
 announce('Load All Playlist Tracks.')
 tracks = [x['tracks'] for x in library.playlists()] # The final results.
 wx.CallAfter(frame.add_results, tracks, clear = True)

def queue_result(event):
 """Adds the current result to the queue."""
 announce('Queue Result.')
 cr = frame.get_current_result()
 if cr == -1:
  return bell() # No row selected.
 frame.queue_track(frame.get_results()[cr])

def add_to_playlist(event = None, playlist = None):
 """Add the current result to a playlist."""
 cr = frame.get_current_result()
 if cr == -1:
  return bell() # No item selected.
 id = get_id(frame.get_results()[cr])
 if not playlist:
  playlist = select_playlist(interactive = False)
 frame.add_to_playlist = playlist
 if playlist:
  try:
   application.mobile_api.add_songs_to_playlist(playlist.get('id'), id)
  except Exception as e:
   return wx.MessageBox('Error adding songs to the %s playlist: %s' % (playlist.get('name', 'Unnamed'), str(e)), 'Error')

def add_again_to_playlist(event):
 """Adds again to the last playlist used."""
 announce('Add To Previous Playlist.')
 add_to_playlist(playlist = frame.add_to_playlist)

def delete(event):
 """Deletes an item from the focused playlist, or the library if that is focused."""
 if frame.queue.HasFocus():
  # They pressed delete from the play queue.
  q = frame.get_current_queue_result()
  if q == -1:
   return bell() # There is no item selected.
  frame.unqueue_track(q)
 else:
  cr = frame.get_current_result()
  playlist = frame.current_playlist
  library = frame.current_library
  if (not playlist and not library) or cr == -1:
   return bell()
  track = frame.get_results()[cr]
  form = lambda value: value # The lambda to format the values as required.
  if playlist: # Deal with the playlist side of things first.
   source = '%s playlist' % playlist.get('name', 'Unnamed')
   for t in playlist.get('tracks', []):
    if t.get('track', {}).get('nid') == track.get('nid'):
     form = lambda value, track = t: track.get('id')
     break
   else:
    return wx.MessageBox('Cannot find that track in %s.' % source, 'Error')
   func = application.mobile_api.remove_entries_from_playlist
  else: # Now the library:
   source = 'library'
   func = application.mobile_api.delete_songs
  if wx.MessageBox('Are you sure you want to delete %s from the %s?' % (format_title(track), source), 'Are You Sure', style = wx.YES_NO) == wx.YES:
   try:
    logging.debug('Result of func: %s.', func(form(track.get('id', get_id(track)))))
    frame.delete_result(cr)
   except RE as e:
    return wx.MessageBox(*format_requests_error(e))

def delete_thing(event):
 """Deletes the current playlist, station or saved result."""
 if frame.current_playlist:
  # We are working on a playlist.
  name = '%s playlist' % frame.current_playlist.get('name', 'Untitled')
  func = application.mobile_api.delete_playlist
  thing = frame.current_playlist['id']
 elif frame.current_station:
  # We are working on a radio station.
  name = '%s station' % frame.current_station.get('name', 'Unnamed')
  func = application.mobile_api.delete_stations
  thing = frame.current_station['id']
 elif frame.current_saved_result:
  # We are working with a saved result.
  name = '%s saved result' % frame.current_saved_result
  func = frame.delete_saved_result
  thing = frame.current_saved_result
 else:
  # There is no playlist or station selected.
  return bell()
 if wx.MessageBox('Are you sure you want to delete the %s?' % name, 'Are You Sure', style = wx.YES_NO) == wx.YES:
  try:
   func(thing)
  except Exception as e:
   return wx.MessageBox('Error deleting the %% (%s).' % (name, str(e)), 'Error')

def station_from_result(event):
 """Creates a station from the current result."""
 cr = frame.get_current_result()
 if cr == -1:
  return bell()
 track = frame.get_results()[cr]
 dlg = wx.TextEntryDialog(frame, 'Enter a name for your new station', 'Create A Station', 'Station based on %s - %s' % (track.get('artist', 'Unknown Artist'), track.get('title', 'Untitled Track')))
 if dlg.ShowModal() == wx.ID_OK and dlg.GetValue():
  name = dlg.GetValue()
  dlg.Destroy()
  try:
   id = application.mobile_api.create_station(name, track_id = get_id(track))
   select_station(station = id, interactive = True)
  except RE as e:
   return wx.MessageBox(*format_request_error(e))

def station_from_artist(event):
 """Create a station based on the currently selected artist."""
 cr = frame.get_current_result()
 if cr == -1:
  return bell()
 track = frame.get_results()[cr]
 dlg = wx.TextEntryDialog(frame, 'Enter a name for your new station', 'Create A Station', 'Station based on %s' % (track.get('artist', 'Unknown Artist')))
 if dlg.ShowModal() == wx.ID_OK and dlg.GetValue():
  value = dlg.GetValue()
  dlg.Destroy()
  try:
   id = application.mobile_api.create_station(value, artist_id = get_id(track))
   select_station(station = id, interactive = True)
  except RE as e:
   return wx.MessageBox(*format_request_error(e))

def station_from_album(event):
 """Create a station from the currently selected album."""
 cr = frame.get_current_result()
 if cr == -1:
  return bell()
 track = frame.get_results()[cr]
 dlg = wx.TextEntryDialog(frame, 'Enter a name for your new station', 'Create A Station', 'Station based on %s - %s' % (track.get('artist', 'Unknown Artist'), track.get('album', 'Unknown Album')))
 if dlg.ShowModal() == wx.ID_OK and dlg.GetValue():
  value = dlg.GetValue()
  dlg.Destroy()
  try:
   id = application.mobile_api.create_station(value, album_id = get_id(track))
   select_station(station = id, interactive = True)
  except RE as e:
   return wx.MessageBox(*format_request_error(e))

def station_from_genre(event):
 """Creates a station based on a genre."""
 try:
  genres = application.mobile_api.get_genres()
 except RE as e:
  return wx.MessageBox(*format_request_error(e))
 dlg = wx.SingleChoiceDialog(frame, 'Select a genre to build a station', 'Select A Genre', [g['name'] for g in genres])
 if dlg.ShowModal() == wx.ID_OK:
  value = dlg.GetValue()
  dlg.Destroy()
  genre = genres[dlg.GetSelection()]
  dlg = wx.TextEntryDialog(frame, 'Enter a name for your new station', 'Create A Station', 'Genre station for %s' % genre['name'])
  if dlg.ShowModal() == wx.ID_OK and dlg.GetValue():
   value = dlg.GetValue()
   dlg.Destroy()
   try:
    id = application.mobile_api.create_station(value, genre_id = genre['id'])
    select_station(station = id, interactive = True)
   except RE as e:
    return wx.MessageBox(*format_request_error(e))

def reset_fx(event):
 """Resets pan and frequency to defaults."""
 #announce('Reset FX.')
 frame.frequency.SetValue(50)
 frame.set_frequency()
 frame.pan.SetValue(50)
 frame.set_pan()

def shuffle(stuff):
 """Shuffles things, and returns them, allowing shuffle to be used from a lambda."""
 announce('Shuffle.')
 random.shuffle(stuff)
 return stuff

def top_tracks(artist = None, interactive = False):
 """Returns top tracks for an artist."""
 announce('Top Tracks.')
 if not artist:
  if not interactive:
   raise ValueError('Must supply an artist when not in interactive mode.')
  cr = frame.get_current_result()
  if cr == -1:
   return bell()
  artist = select_artist(frame.get_results()[cr].get('artistId', []))
 try:
  tracks = application.mobile_api.get_artist_info(artist, max_top_tracks = config.config.get('library', 'max_top_tracks')).get('topTracks', [])
 except RE as e:
  if interactive:
   return wx.MessageBox(*format_request_error(e))
  else:
   return []
 if interactive:
  wx.CallAfter(frame.add_results, tracks, clear = True)
 else:
  return tracks

def results_history_back(event):
 """Move back through the results history."""
 announce('Back.')
 if not application.results_history:
  return bell()
 i = application.results_history_index - 1
 if i < 0:
  return bell() # We're at the start of the history.
 frame.select_results_history(i)

def results_history_forward(event):
 """Moves forward through the results history."""
 announce('Forward.')
 if not application.results_history:
  return bell()
 i = application.results_history_index + 1
 if i >= len(application.results_history):
  return bell()
 frame.select_results_history(i)

def format_requests_error(err, title = 'Connection Error'):
 """Formats an error into a string to complain about connection problems."""
 return ['No connection could be made. Please ensure you are connected to the internet (%s).' % str(err), title]

def get_lyrics(event, track = None):
 """Loads up a lyrics viewer frame with the lyrics of the supplied track, or the currently playing track if None is provided."""
 if not track:
  cr = frame.get_current_result()
  if cr == -1:
   return bell()
  track = frame.get_results()[cr]
 artist = track.get('artist')
 title = track.get('title')
 if application.lyrics_frame:
  Thread(target = application.lyrics_frame.populate_lyrics, args = [artist, title]).start()
 else:
  application.lyrics_frame = LyricsViewer(artist, title)

def bell():
 """Play a bell sound."""
 return wx.Bell() if config.config.get('sound', 'interface_sounds') else None

def get_size(start_path = '.'):
 total_size = 0
 for dirpath, dirnames, filenames in os.walk(start_path):
  for f in filenames:
   fp = os.path.join(dirpath, f)
   total_size += os.path.getsize(fp)
 return total_size

def save_result(event = None):
 """Save the current result."""
 track = frame.get_current_track()
 if not track:
  return wx.Bell()
 if exists(track):
  dlg = wx.FileDialog(frame, defaultDir = os.path.expanduser('~'), wildcard = '*%s' % application.track_extension, defaultFile = format_title(track).replace('\\', ',').replace('/', ','), style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
  if dlg.ShowModal() == wx.ID_OK:
   new_path = dlg.GetPath()
  else:
   new_path = None
  dlg.Destroy()
  if new_path:
   try:
    if not new_path.endswith(application.track_extension):
     new_path += application.track_extension
    shcopy(library.get_path(track), new_path)
   except Exception as e:
    wx.MessageBox(str(e), 'Error')
 else:
  return wx.MessageBox('That track is not downloaded. Please check your library settings and try playing the track again.', 'File Not Downloaded')

def announce(stuff):
 """Accessible alerts as were."""
 if config.config.get('accessibility', 'announcements'):
  output.output(stuff)

def results_to_library(event = None):
 """Adds everything in the current list of results to the library."""
 if frame.current_library:
  return bell()
 else:
  return results_to_target(frame.get_results(), application.mobile_api.add_aa_track)

def results_to_playlist(event = None):
 """Add the current results to a playlist."""
 results = frame.get_results()
 if not results:
  return wx.Bell()
 playlist = select_playlist(interactive = False)
 if playlist:
  results_to_target(results, lambda id, playlist = playlist['id']: application.mobile_api.add_songs_to_playlist(playlist, id))

def results_to_target(results, func):
 """Run results through func."""
 l = len(results)
 dlg = wx.ProgressDialog('Add Results', 'Adding %s songs to your library.' % l, l, frame, wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME|wx.PD_ESTIMATED_TIME)
 def finish(msg = 'Finishing up...'):
  """Finish up."""
  dlg.Update(l, msg)
  dlg.Destroy()
 for i, r in enumerate(results):
  i += 1
  cont, skip = dlg.Update(i, '(%s/%s) Adding %s.' % (i, l, format_title(r)))
  try:
   func(get_id(r))
  except CallFailure:
   wx.CallAfter(finish, 'Cann\'t add any more tracks.')
   break
  if not cont:
   wx.CallAfter(finish)
   break
 wx.CallAfter(finish)

def delete_path(path):
 """Delete something."""
 if os.path.isfile(path):
  os.remove(path)
 else:
   rmtree(path)

def reverse_results(results):
 """Reverses the provided results."""
 res = copy(results)
 res.reverse()
 return res

def load_url(event):
 """Load and play a URL."""
 URLFrame().Show(True)
