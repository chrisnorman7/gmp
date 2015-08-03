"""Various functions used in the program."""

import application, wx, os, requests, sys, random, library, logging
from accessible_output2.outputs.auto import Auto
from shutil import copy as shcopy, rmtree
RE = (requests.exceptions.RequestException, requests.adapters.ReadTimeoutError, IOError)
from sound_lib.main import BassError
from time import time, ctime
from gui.lyrics_viewer import LyricsViewer
from gui.search_frame import SearchFrame, songs
from copy import copy
from threading import Thread, current_thread

output = Auto()

id_fields = [
 'storeId',
 'id',
 'trackId',
 'nid',
]

def format_title(track):
 try:
  return application.config.get('windows', 'title_format').format(**track)
 except KeyError as e:
  return 'Error in title format: %s.' % e

def config_update(config, section, option, value):
 """Ran when apply or OK is clicked in the options window."""
 if section == 'sound':
  if option == 'repeat':
   application.main_frame.repeat.Check(value)
  elif option == 'repeat_track':
   application.main_frame.repeat_track.Check(value)
  elif option == 'stop_after':
   application.main_frame.stop_after.Check(value)
  elif option == 'volume':
   application.main_frame.volume.SetValue(value)
   application.main_frame.set_volume()
  elif option == 'pan':
   application.main_frame.pan.SetValue(value)
   application.main_frame.set_pan()
 elif section == 'windows':
  if option == 'play_controls_show':
   application.main_frame.play_controls_func(value)
 elif section == 'http' and option in ['enabled', 'hostname', 'port']:
  Thread(target = application.main_frame.reload_http_server).start()

application.config.updateFunc = config_update

def get_id(item):
 """Return the ID for the provided item."""
 for f in id_fields:
  if f in item:
   return item.get(f)

def in_library(id):
 """Checks if the given ID is in the library."""
 lib = library.library
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
  dlg = wx.SingleChoiceDialog(application.main_frame, 'Select an artist', 'This track has multiple artists', a.values())
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
 cr = application.main_frame.get_current_result()
 if application.main_frame.current_library or cr == -1:
  return bell() # Can't add stuff in the library to the library, or there's nothing selected to add.
 track = application.main_frame.get_results()[cr]
 id = get_id(track)
 try:
  application.mobile_api.add_aa_track(id)
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.MessageBox('Added %s to your library.' % format_title(track), 'Track Added')

def select_playlist(event = None, playlists = None, playlist = None, interactive = True):
 if not playlists:
  playlists = library.playlists
 if playlist:
  for p in playlists:
   if p['id'] == playlist:
    playlist = p
  else:
   return ValueError('Provided playlist does not exist.')
 else:
  dlg = wx.SingleChoiceDialog(frame, 'Select a playlist', 'Select Playlist', [x['name'] for x in playlists])
  if dlg.ShowModal() == wx.ID_OK:
   playlist = playlists[dlg.GetSelection()]
  dlg.Destroy()
 if interactive:
  if playlist:
   tracks = playlist['tracks']
   wx.CallAfter(application.main_frame.add_results, [x['track'] for x in tracks], True, playlist = playlist)
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
    tracks = application.mobile_api.get_station_tracks(station['id'], application.config.get('library', 'max_results'))
    wx.CallAfter(application.main_frame.add_results, tracks, True, station = station)
   except RE as e:
    return wx.MessageBox(*format_requests_error(e))
 else:
  return station

def play_pause(event = None):
 """Play or pause the music."""
 #announce('Play Pause')
 if application.main_frame.current_track:
  if application.main_frame.current_track.is_paused or application.main_frame.current_track.is_stopped:
   application.main_frame.current_track.play()
   application.main_frame.play_pause.SetLabel(application.config.get('windows', 'pause_label'))
  else:
   application.main_frame.current_track.pause()
   application.main_frame.play_pause.SetLabel(application.config.get('windows', 'play_label'))
 else:
  bell()

def stop(event = None):
 """Stop the current track."""
 #announce('Stop.')
 if application.main_frame.current_track:
  application.main_frame.current_track.pause()
  application.main_frame.current_track.set_position(0) # Pause instead of stopping.
  application.main_frame.play_pause.SetLabel(application.config.get('windows', 'play_label'))

def volume_up(event = None):
 """Turn up the playing song."""
 #announce('Volume Up.')
 v = application.config.get('sound', 'volume_increment') + application.main_frame.volume.GetValue()
 if v > 100:
  v = 100
  bell()
 set_volume(v)

def volume_down(event = None):
 """Turn down the playing song."""
 #announce('Volume Down.')
 v = application.main_frame.volume.GetValue() - application.config.get('sound', 'volume_decrement')
 if v < 0:
  v = 0
  bell()
 set_volume(v)

def set_volume(v):
 """Set the volume. Return True upon success, or False otherwise."""
 if v < 0 or v > 100:
  return False
 else:
  application.main_frame.volume.SetValue(v)
  application.main_frame.set_volume()
  return True

def get_previous_song(alter = False):
 """Get the song which will be played when the previous button is pressed. If alter is True, actually remove the track from the history buffer."""
 if application.main_frame.track_history:
  return application.main_frame.track_history[-1]
  if alter:
   del application.main_frame.track_history[-1]

def previous(event = None):
 """Select the previous track."""
 #announce('Previous.')
 if not application.main_frame.track_history:
  if application.main_frame.current_track:
   application.main_frame.current_track.play(True)
  else:
   return bell()
 else:
  q = application.main_frame.get_queue()
  if q:
   q.insert(0, application.main_frame.get_current_track())
  application.main_frame.queue_tracks(q, True)
  application.main_frame.play(get_previous_song(), history = False)

def get_next_song(clear = False):
 """Get the next song from the play queue or list of results. If clear is True, unqueue the resulting track."""
 q = application.main_frame.get_queue()
 if q:
  if clear:
   application.main_frame.unqueue_track(0)
  return q[0]
 else:
  q = application.main_frame.get_results()
  track = application.main_frame.get_current_track()
  if track in q:
   cr = q.index(track) + 1
   if cr == len(q):
    if application.config.get('sound', 'repeat') and q:
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
 if application.config.get('sound', 'repeat_track'):
  q = application.main_frame.get_current_track()
 else:
  q = get_next_song(True)
 if q:
  application.main_frame.play(q)
 else:
  return bell() if interactive else None

def rewind(event):
 """Rewind the track a bit."""
 #announce('Rewind.')
 track = application.main_frame.current_track
 if not track:
  bell()
 else:
  pos = track.get_position() - application.config.get('sound', 'rewind_amount')
  if pos < 0:
   pos = 0
  track.set_position(pos)

def fastforward(event):
 """Fastforward the track a bit."""
 #announce('Fast Forward.')
 track = application.main_frame.current_track
 if not track:
  bell()
 else:
  pos = min(track.get_position() + application.config.get('sound', 'rewind_amount'), track.get_length())
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
   t = os.path.getctime(library.get_path(track))
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
  while get_size(library.media_directory()) > ((application.config.get('library', 'library_size') * 1024) * 1024):
   prune_library()
  callback(info)
  return True
 else:
  logging.info('Download failed with status code %s.', g.status_code)
  return False

def track_seek(event):
 """Get the value of the seek slider and move the track accordingly."""
 track = application.main_frame.current_track
 if track:
  try:
   track.set_position(int((track.get_length() / 100.0) * application.main_frame.track_position.GetValue()))
  except BassError:
   pass # Don't care.

def do_search(event = None, search = None, type = None, interactive = True):
 """Search google music."""
 if not search:
  search = application.main_frame.last_search
 if type == None:
  type = application.main_frame.last_search_type
 s = SearchFrame(search, type)
 if interactive:
  s.Show(True)
 else:
  s.do_search()

def do_search_again(event):
 """Repeat the previous search."""
 announce('Find Again.')
 return do_search(search = application.main_frame.last_search, type = application.main_frame.last_search_type, interactive = False)

def do_search_quick(event):
 """Search quickly."""
 old_search_string = copy(application.main_frame.last_search)
 old_search_type = copy(application.main_frame.last_search_type)
 dlg = wx.TextEntryDialog(frame, 'Search for songs', 'Quick Search', old_search_string)
 if dlg.ShowModal() == wx.ID_OK:
  old_search_string = dlg.GetValue()
  do_search(search = old_search_string, type = songs, interactive = False)
 dlg.Destroy()
 application.main_frame.last_search = old_search_string
 application.main_frame.last_search_type = old_search_type

def select_output(event = None):
 """Selects a new audio output."""
 o = application.sound_output
 p = getattr(o, '__class__')
 dlg = wx.SingleChoiceDialog(frame, 'Select Output Device', 'Select an output device from the list', o.get_device_names())
 if dlg.ShowModal() == wx.ID_OK:
  if application.main_frame.current_track:
   loc = application.main_frame.current_track.get_position()
   playing = application.main_frame.current_track.is_playing
   item = application.main_frame.get_current_track()
   application.main_frame.current_track = None
  else:
   item = None
  o.free()
  application.sound_output = p(device = dlg.GetSelection() + 1)
  if item:
   application.main_frame.play(item, play = playing)
   application.main_frame.current_track.set_position(loc)
 dlg.Destroy()

def promoted_songs(event):
 """Get promoted songs."""
 return wx.MessageBox('This feature has been disabled until the API has been fixed.', 'Feature Disabled')
 try:
  songs = application.mobile_api.get_promoted_songs()
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(application.main_frame.add_results, songs, True)

def focus_playing(event):
 """Scrolls the results view to the currently playing track, if it's in the list."""
 #announce('Focus Playing.')
 track = application.main_frame.get_current_track()
 if track:
  if track in application.main_frame.get_results():
   pos = application.main_frame.get_results().index(track)
   if application.platform == 'darwin':
    application.main_frame.results.SelectRow(pos)
   else:
    application.main_frame.results.Select(pos)
    application.main_frame.results.Focus(pos)
  else:
   application.main_frame.add_results([track], clear = True, bypass_history = True)
 else:
  return bell()

def artist_tracks(event = None, id = None):
 """Get all tracks for a particular artist."""
 announce('Artist Tracks.')
 if id == None:
  cr = application.main_frame.get_current_result()
  if cr == -1:
   return bell() # There is no track selected yet.
  id = select_artist(application.main_frame.get_results()[cr]['artistId'])
 try:
  info = application.mobile_api.get_artist_info(id)
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(application.main_frame.clear_results)
 tracks = [] # The final list of tracks for add_results.
 for a in info['albums']:
  try:
   a = application.mobile_api.get_album_info(a['albumId'])
  except RE as e:
   wx.CallAfter(application.main_frame.add_results, tracks)
   return wx.MessageBox(*format_requests_error(e))
  tracks += a.get('tracks', [])
 wx.CallAfter(application.main_frame.add_results, tracks, True)

def current_album(event):
 """Selects the current album."""
 announce('Current Album.')
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell() # No row selected.
 try:
  songs = application.mobile_api.get_album_info(application.main_frame.get_results()[cr]['albumId']).get('tracks', [])
 except RE as e:
  return wx.MessageBox(*format_requests_error(e))
 wx.CallAfter(application.main_frame.add_results, songs, True)

def artist_album(event, albums = None):
 """Selects a particular artist album."""
 if albums:
  show_artists = True
 else:
  show_artists = False
  cr = application.main_frame.get_current_result()
  if cr == -1:
   return bell()
  artists = application.main_frame.get_results()[cr]['artistId']
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
   wx.CallAfter(application.main_frame.add_results, songs, True)
  except RE as e:
   wx.MessageBox(*format_requests_error(e))

def related_artists(event):
 """Selects and views tracks for a related artist."""
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell()
 artist = select_artist(application.main_frame.get_results()[cr]['artistId'])
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
  wx.CallAfter(application.main_frame.add_results, tracks, True)

def all_playlist_tracks(event):
 """Add every track from every playlist."""
 announce('Load All Playlist Tracks.')
 tracks = [x['tracks'] for x in library.playlists] # The final results.
 wx.CallAfter(application.main_frame.add_results, tracks, clear = True)

def queue_result(event):
 """Adds the current result to the queue."""
 announce('Queue Result.')
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell() # No row selected.
 application.main_frame.queue_track(application.main_frame.get_results()[cr])

def add_to_playlist(event = None, playlist = None):
 """Add the current result to a playlist."""
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell() # No item selected.
 id = get_id(application.main_frame.get_results()[cr])
 if not playlist:
  playlist = select_playlist(interactive = False)
 application.main_frame.add_to_playlist = playlist
 if playlist:
  try:
   application.mobile_api.add_songs_to_playlist(playlist.get('id'), id)
  except Exception as e:
   return wx.MessageBox('Error adding songs to the %s playlist: %s' % (playlist.get('name', 'Unnamed'), str(e)), 'Error')

def add_again_to_playlist(event):
 """Adds again to the last playlist used."""
 announce('Add To Previous Playlist.')
 add_to_playlist(playlist = application.main_frame.add_to_playlist)

def delete(event):
 """Deletes an item from the focused playlist, or the library if that is focused."""
 if application.main_frame.queue.HasFocus():
  # They pressed delete from the play queue.
  q = application.main_frame.get_current_queue_result()
  if q == -1:
   return bell() # There is no item selected.
  application.main_frame.unqueue_track(q)
 else:
  cr = application.main_frame.get_current_result()
  playlist = application.main_frame.current_playlist
  library = application.main_frame.current_library
  if (not playlist and not library) or cr == -1:
   return bell()
  track = application.main_frame.get_results()[cr]
  form = lambda value: value # The lambda to format the values as required.
  if playlist: # Deal with the playlist side of things first.
   source = '%s playlist' % playlist.get('name', 'Unnamed')
   for t in playlist.get('tracks', []):
    if t.get('track', {}).get('nid') == track.get('nid'):
     form = lambda value: [t.get('id')]
     break
   else:
    return wx.MessageBox('Cannot find that track in %s.' % source, 'Error')
   func = application.mobile_api.remove_entries_from_playlist
  else: # Now the library:
   source = 'library'
   func = application.mobile_api.delete_songs
  if wx.MessageBox('Are you sure you want to delete %s from the %s?' % (format_title(track), source), 'Are You Sure', style = wx.YES_NO) == wx.YES:
   try:
    func(form(track.get('id', get_id(track))))
    application.main_frame.delete_result(cr)
   except RE as e:
    return wx.MessageBox(*format_requests_error(e))

def delete_thing(event):
 """Deletes the current playlist, station or saved result."""
 if application.main_frame.current_playlist:
  # We are working on a playlist.
  name = '%s playlist' % application.main_frame.current_playlist.get('name', 'Untitled')
  func = application.mobile_api.delete_playlist
  thing = application.main_frame.current_playlist['id']
 elif application.main_frame.current_station:
  # We are working on a radio station.
  name = '%s station' % application.main_frame.current_station.get('name', 'Unnamed')
  func = application.mobile_api.delete_stations
  thing = application.main_frame.current_station['id']
 elif application.main_frame.current_saved_result:
  # We are working with a saved result.
  name = '%s saved result' % application.main_frame.current_saved_result
  func = application.main_frame.delete_saved_result
  thing = application.main_frame.current_saved_result
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
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell()
 track = application.main_frame.get_results()[cr]
 dlg = wx.TextEntryDialog(frame, 'Enter a name for your new station', 'Create A Station', 'Station based on %s - %s' % (track.get('artist', 'Unknown Artist'), track.get('title', 'Untitled Track')))
 if dlg.ShowModal() and dlg.GetValue():
  name = dlg.GetValue()
  dlg.Destroy()
  try:
   id = application.mobile_api.create_station(name, track_id = get_id(track))
   select_station(station = id, interactive = True)
  except RE as e:
   return wx.MessageBox(*format_request_error(e))

def station_from_artist(event):
 """Create a station based on the currently selected artist."""
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell()
 track = application.main_frame.get_results()[cr]
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
 cr = application.main_frame.get_current_result()
 if cr == -1:
  return bell()
 track = application.main_frame.get_results()[cr]
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
 application.main_frame.frequency.SetValue(50)
 application.main_frame.set_frequency()
 application.main_frame.pan.SetValue(50)
 application.main_frame.set_pan()

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
  cr = application.main_frame.get_current_result()
  if cr == -1:
   return bell()
  artist = select_artist(application.main_frame.get_results()[cr].get('artistId', []))
 try:
  tracks = application.mobile_api.get_artist_info(artist, max_top_tracks = application.config.get('library', 'max_top_tracks')).get('topTracks', [])
 except RE as e:
  if interactive:
   return wx.MessageBox(*format_request_error(e))
  else:
   return []
 if interactive:
  wx.CallAfter(application.main_frame.add_results, tracks, clear = True)
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
 application.main_frame.select_results_history(i)

def results_history_forward(event):
 """Moves forward through the results history."""
 announce('Forward.')
 if not application.results_history:
  return bell()
 i = application.results_history_index + 1
 if i >= len(application.results_history):
  return bell()
 application.main_frame.select_results_history(i)

def format_requests_error(err, title = 'Connection Error'):
 """Formats an error into a string to complain about connection problems."""
 return ['No connection could be made. Please ensure you are connected to the internet (%s).' % str(err), title]

def get_lyrics(event, track = None):
 """Loads up a lyrics viewer frame with the lyrics of the supplied track, or the currently playing track if None is provided."""
 if not track:
  cr = application.main_frame.get_current_result()
  if cr == -1:
   return bell()
  track = application.main_frame.get_results()[cr]
 artist = track.get('artist')
 title = track.get('title')
 if application.lyrics_frame:
  Thread(target = application.lyrics_frame.populate_lyrics, args = [artist, title]).start()
 else:
  application.lyrics_frame = LyricsViewer(artist, title)

def bell():
 """Play a bell sound."""
 return wx.Bell() if application.config.get('sound', 'interface_sounds') else None

def get_size(start_path = '.'):
 total_size = 0
 for dirpath, dirnames, filenames in os.walk(start_path):
  for f in filenames:
   fp = os.path.join(dirpath, f)
   total_size += os.path.getsize(fp)
 return total_size

def save_result(event = None):
 """Save the current result."""
 track = application.main_frame.get_current_track()
 if not track:
  return wx.Bell()
 track = library.get_track(get_id(track))
 if track.exists() and track.downloaded:
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
    shcopy(path, new_path)
   except Exception as e:
    wx.MessageBox(str(e), 'Error')
 else:
  return wx.MessageBox('That track is not downloaded. Please check your library settings and try playing the track again.', 'File Not Downloaded')

def announce(stuff):
 """Accessible alerts as were."""
 output.output(stuff)

def results_to_library(event = None):
 """Adds everything in the current list of results to the library."""
 if application.main_frame.current_library:
  return bell()
 results = application.main_frame.get_results()
 l = len(results)
 dlg = wx.ProgressDialog('Add To Library', 'Adding %s songs to your library.' % l, l, frame, wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME|wx.PD_ESTIMATED_TIME)
 for i, r in enumerate(results):
  i += 1
  cont, skip = dlg.Update(i, '(%s/%s) Adding %s to library.' % (i, l, format_title(r)))
  application.mobile_api.add_aa_track(get_id(r))
  if not cont:
   wx.CallAfter(dlg.Update, l, 'Finishing up...')
   wx.CallAfter(dlg.Destroy)
   break
 wx.CallAfter(dlg.Destroy)

def delete_path(path):
 """Delete something."""
 if os.path.isfile(path):
  os.remove(path)
 else:
   rmtree(path)
