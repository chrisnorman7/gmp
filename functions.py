"""Various functions used in the program."""

import application, wx, os, requests, sys
from sound_lib.main import BassError

id_fields = [
 'storeId',
 'nid',
 'id',
 'trackId'
]

def get_id(item):
 """Return the ID for the provided item."""
 for f in id_fields:
  if f in item:
   return item.get(f)

def in_library(id):
 """Checks if the given ID is in the library."""
 lib = application.mobile_api.get_all_songs()
 for l in lib:
  for f in id_fields:
   if l.get(f, None) == id:
    return True
 return False

def reveal_media(event):
 """Opens the media directory in the file manager."""
 if sys.platform == 'darwin':
  cmd = 'open'
 else:
  cmd = 'start'
 os.system('%s "%s"' % (cmd, application.media_directory))

def toggle_library(event):
 """Adds the currently selected song to the library."""
 frame = application.main_frame
 cr = frame.get_current_result()
 if cr == -1:
  return wx.Bell()
 track = frame.get_results()[cr]
 id = get_id(track)
 if in_library(id):
  application.mobile_api.add_aa_track(id)
 else:
  application.mobile_api.remove_songs(id)

def get_device_id(frame = None):
 """Get and return a device ID. If none can be found, and the user cancels, close the initiating frame if it's provided.."""
 if not application.device_id:
  ids = application.web_api.get_registered_devices()
  dlg = wx.SingleChoiceDialog(application.main_frame, 'Choose your mobile device from the list of devices which are enabled on your account:', 'Device Selection', [x['type'] for x in ids])
  if dlg.ShowModal() == wx.ID_OK:
   application.device_id = ids[dlg.GetSelection()]['id']
  else:
   if frame:
    frame.Close(True)
  dlg.Destroy()
 return application.device_id

def select_playlist(event):
 """Select a playlist."""
 frame = event.GetEventObject().GetWindow()
 playlists = application.mobile_api.get_all_playlists()
 dlg = wx.SingleChoiceDialog(frame, 'Select a playlist', 'Select Playlist', ['%s - %s' % (x['ownerName'], x['name']) for x in playlists])
 if dlg.ShowModal() == wx.ID_OK:
  frame.add_results([x['track'] for x in application.mobile_api.get_shared_playlist_contents(playlists[dlg.GetSelection()]['shareToken'])], True)
 dlg.Destroy()

def select_radio(event):
 """Select a radio station."""
 frame = event.GetEventObject().GetWindow()
 stations = application.mobile_api.get_all_stations()
 dlg = wx.SingleChoiceDialog(frame, 'Select a radio station', 'Select Station', [x['name'] for x in stations])
 if dlg.ShowModal() == wx.ID_OK:
  frame.add_results(application.mobile_api.get_station_tracks(stations[dlg.GetSelection()]['id']), True)
 dlg.Destroy()

def play_pause(event):
 """Play or pause the music."""
 frame = application.main_frame
 if frame.current_track:
  if frame.current_track.is_paused:
   frame.current_track.play()
   frame.play_pause.SetLabel(application.config.get('windows', 'pause_label'))
  else:
   frame.current_track.pause()
   frame.play_pause.SetLabel(application.config.get('windows', 'play_label'))
 else:
  wx.Bell()

def stop(event):
 """Stop the current track."""
 frame = application.main_frame
 if frame.current_track:
  frame.current_track.pause()
  frame.current_track.set_position(0) # Pause instead of stopping.
  frame.play_pause.SetLabel(application.config.get('windows', 'play_label'))

def volume_up(event):
 """Turn up the playing song."""
 frame = application.main_frame
 v = application.config.get('sound', 'volume_increment') + frame.volume.GetValue()
 if v > 100:
  wx.Bell()
 else:
  frame.volume.SetValue(v)
  frame.set_volume(event)

def volume_down(event):
 """Turn down the playing song."""
 frame = application.main_frame
 v = frame.volume.GetValue() - application.config.get('sound', 'volume_decrement')
 if v < 0:
  wx.Bell()
 else:
  frame.volume.SetValue(v)
  frame.set_volume(event)

def previous(event):
 """Select the previous track."""
 frame = application.main_frame
 if frame.current_track and (frame.track_position.GetValue() >= 1 or not frame.track_history):
  frame.current_track.set_position(0)
 else:
  frame.queue_tracks([frame.get_current_track()] + frame.get_queue(), True)
  frame.play(frame.track_history.pop(-1))
  frame.delete_history()

def next(event, interactive = True):
 """Plays the next track."""
 frame = application.main_frame
 q = frame.get_queue()
 if not q:
  if interactive:
   wx.Bell()
 else:
  frame.play(q[0])
  frame.unqueue_track(0)

def rewind(event):
 """Rewind the track a bit."""
 track = application.main_frame.current_track
 if not track:
  wx.Bell()
 else:
  pos = track.get_position() - application.config.get('sound', 'rewind_amount')
  if pos < 0:
   pos = 0
  track.set_position(pos)

def fastforward(event):
 """Fastforward the track a bit."""
 track = application.main_frame.current_track
 if not track:
  wx.Bell()
 else:
  pos = min(track.get_position() + application.config.get('sound', 'rewind_amount'), track.get_length())
  track.set_position(pos)

def prune_library(self):
 """Delete the oldest track from the library."""
 id = None # The id of the track to delete.
 path = None # The path to the file to be deleted.
 stamp = None # The last modified time stamp of the file.
 for x in os.listdir(application.media_directory):
  p = os.path.join(application.media_directory, x)
  if not stamp or os.path.getmtime(p) < stamp:
   id = x[:-4]
   path = p
 if path:
  os.remove(path)
  del application.library[id]
  return id

def id_to_path(id):
 """Returns the path to the file suggested by id."""
 return os.path.join(application.media_directory, id + application.track_extension)

def download_file(id, url, timestamp):
 """Download the track from url, add it to the library database, and store it with a filename derived from id."""
 path = id_to_path(id)
 g = requests.get(url)
 with open(path, 'wb') as f:
  f.write(g.content)
 application.library[id] = timestamp
 while len(os.listdir(application.media_directory)) > application.config.get('library', 'save_tracks'):
  prune_library()

def track_seek(event):
 """Get the value of the seek slider and move the track accordingly."""
 frame = application.main_frame
 track = frame.current_track
 if track:
  try:
   track.set_position(int((track.get_length() / 100.0) * frame.track_position.GetValue()))
  except BassError:
   pass # Don't care.

def do_search(event):
 """Search google music."""
 frame = application.main_frame
 dlg = wx.TextEntryDialog(frame, 'Find', 'Search Google Music', frame.last_search)
 if dlg.ShowModal() == wx.ID_OK:
  results = application.mobile_api.search_all_access(dlg.GetValue())['song_hits']
  if not results:
   wx.MessageBox('No results found', 'Error')
  else:
   frame.add_results([x['track'] for x in results], True)
 dlg.Destroy()

def select_output(event = None):
 """Selects a new audio output."""
 frame = application.main_frame
 o = application.sound_output
 p = getattr(o, '__class__')
 dlg = wx.SingleChoiceDialog(frame, 'Select Output Device', 'Select an output device from the list', o.get_device_names())
 if dlg.ShowModal() == wx.ID_OK:
  if frame.current_track:
   loc = frame.current_track.get_position()
   item = frame.get_current_track()
   frame.current_track = None
  else:
   item = None
  o.free()
  application.sound_output = p(device = dlg.GetSelection() + 1)
  if item:
   frame.play(item)
   frame.current_track.set_position(loc)
 dlg.Destroy()

def thumbs_up_songs(event):
 """Get thumbs up tracks (may be empty)."""
 frame = application.main_frame
 frame.clear_results()
 frame.add_results(application.mobile_api.get_thumbs_up_songs())

def focus_playing(event):
 """Scrolls the results view to the currently playing track, if it's in the list."""
 frame = application.main_frame
 track = frame.get_current_track()
 results = frame.get_results()
 if track:
  if track in results:
   print results.index(track)
 else:
  wx.Bell()

def artist_tracks(event):
 """Get all tracks for a particular artist."""
 frame = application.main_frame
 cr = frame.get_current_result()
 if cr == -1:
  return wx.Bell() # There is no track selected yet.
 info = application.mobile_api.get_artist_info(frame.get_results()[cr]['artistId'][0])
 frame.clear_results()
 for a in info['albums']:
  a = application.mobile_api.get_album_info(a['albumId'])
  frame.add_results(a['tracks'])

def current_album(event):
 """Selects the current album."""
 frame = application.main_frame
 cr = frame.get_current_result()
 if cr == -1:
  return wx.Bell() # No row selected.
 frame.add_results(application.mobile_api.get_album_info(frame.get_results()[cr]['albumId'])['tracks'], True)

def artist_album(event):
 """Selects a particular artist album."""
 pass

def related_artists(event):
 """Selects and views tracks for a related artist."""
 pass
