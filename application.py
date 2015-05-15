from confmanager import ConfManager, parser

columns = [
 ['composer', ''],
 ['trackType', ''],
 ['creationTimestamp', ''],
 ['recentTimestamp', ''],
 ['albumArtist', ''],
 ['contentType', ''],
 ['deleted', ''],
 ['estimatedSize', ''],
 ['lastModifiedTimestamp', ''],
 ['trackNumber', 'Number'],
 ['title', 'Name'],
 ['artist', 'Artist'],
 ['album', 'Album'],
 ['discNumber', 'Disc Number'],
 ['durationMillis', 'Duration'],
 ['genre', 'Genre'],
 ['year', 'Year']
]

import wx, os, json, functions
from sound_lib.output import Output
from gmusicapi import Mobileclient, Webclient

sound_output = Output()

mobile_api = Mobileclient()
web_api = Webclient()
device_id = None

version = '1.0'
name = 'Google Music Player'
url = 'www.code-metropolis.com/gmplayer'
description = 'An app for playing tracks from Google Play Music (account required).'
vendor_name = 'Software Metropolis'
developers = ['Chris Norman']

info = wx.AboutDialogInfo()
info.SetName(name)
info.SetDescription(description)
info.SetVersion(version)
info.SetDevelopers(developers)

directory = os.path.expanduser('~/.%s' % name)
media_directory = os.path.join(directory, 'media')

if not os.path.isdir(directory):
 os.mkdir(directory)

config = ConfManager(name + ' Options')

config.add_section('login')
config.set('login', 'uid', '', title = 'The email address to log in with')
config.set('login', 'pwd', '', 'The password to log in with (stored in plain text)', kwargs = {'style': wx.TE_PASSWORD})
config.set('login', 'remember', False, title = 'Remember credentials across restarts')

config.add_section('library')
config.set('library', 'save_tracks', 1000, title = 'The number of tracks to save in the library before the oldest are deleted')
config.set('library', 'max_top_tracks', 50, title = 'The max top tracks to retrieve when getting artist info')

config.add_section('windows')
config.set('windows', 'title_format', '{artist} - {title}', title = 'The format for track names in the window title')
config.set('windows', 'uid_label', '&Username', title = 'The label for the username field')
config.set('windows', 'pwd_label', '&Password', title = 'The label for the password field')
config.set('windows', 'remember_label', '&Store my password in plain text', title = 'Label for the remember password checkbox')
config.set('windows', 'login_label', '&Login', title = 'The title for the login button')
config.set('windows', 'ok_label', '&OK', title = 'The title for OK buttons')
config.set('windows', 'cancel_label', '&Cancel', title = 'The title for the cancel field')
config.set('windows', 'close_label', '&Close', title = 'The label for close buttons')
config.set('windows', 'volume_label', '&Volume', title = 'The label for the volume var')
config.set('windows', 'previous_label', '&Previous', title = 'The title for the previous track button')
config.set('windows',  'play_label', '&Play', title = 'The label for the play button')
config.set('windows', 'pause_label', '&Pause', title = 'The label for the pause button')
config.set('windows', 'next_label', '&Next', title = 'The label for the next button')

config.add_section('sound')
config.set('sound', 'volume_increment', 10, title = 'The percent to increase the volume by when using the volume hotkey')
config.set('sound', 'volume_decrement', 10, title = 'The amount to decrement the volume by when using the hotkey')
config.set('sound', 'rewind_amount', 100000, title = 'The number of samples to rewind by when using the hotkey')
config.set('sound', 'fastforward_amount', 100000, title = 'The number of samples to fastforward by when using the hotkey')
config.set('sound', 'frequency', 50, title = 'The frequency to play songs at (50 is 44100)')
config.set('sound', 'volume', 1.0, title = 'The volume to play tracks at (between 0.0 and 1.0)')
config.set('sound', 'pan', 0.0, title = 'The left and right stereo balance to play songs at')

config_file = os.path.join(directory, 'config.json')

if os.path.isfile(config_file):
 with open(config_file, 'rb') as f:
  try:
   j = json.load(f)
   device_id = j.get('device_id', None)
   parser.parse_json(config, j.get('config', {}))
  except ValueError:
   pass

class MyApp(wx.App):
 def MainLoop(self, *args, **kwargs):
  """Overrides wx.App.MainLoop, to save the config at the end."""
  l = super(MyApp, self).MainLoop(*args, **kwargs)
  sound_output.stop()
  with open(config_file, 'wb') as f:
   json.dump({'config': config.get_dump(), 'device_id': device_id}, f, indent = 1)
  with open(library_file, 'wb') as f:
   json.dump(library, f, indent = 1)
  return l

app = MyApp(False)
app.SetAppDisplayName('%s (v %s)' % (name, version))
app.SetAppName(name)
app.SetVendorName(vendor_name)
app.SetVendorDisplayName(vendor_name)
from gui.main_frame import MainFrame
main_frame = MainFrame()
track_extension = '.mp3'

library_file = os.path.join(directory, 'library.json')
# Maintain a database of downloaded files.
if os.path.isfile(library_file):
 with open(library_file, 'rb') as f:
  library = json.load(f)
else:
 library = {}

if not os.path.isdir(media_directory):
 os.mkdir(media_directory)

for x in os.listdir(media_directory):
 # Delete all the files which don't belong here!
 (fname, ext) = os.path.splitext(x)
 if fname not in library:
  os.remove(functions.id_to_path(fname))

# Delete all the entries without files.
for l in library.keys():
 if not os.path.isfile(os.path.join(media_directory, l + track_extension)):
  del library[l]
