version = '2.2'
devel = False
compress = False
add_to_site = ['certifi', 'pkg_resources', 'mechanicalsoup', 'bs4', 'htmlentitydefs.py', 'HTMLParser.py', 'markupbase.py', 'pywintypes27.dll', 'pythoncom27.dll', 'cssselect']
update_url = 'https://www.dropbox.com/s/wjs54oeeorfbnp3/version.json?dl=1'

from sys import platform

streams = [['Dodge Radio', 'http://198.154.106.104:8496/stream']]
saved_results = {}
results_history = []

import wx, os, json
from sound_lib.output import Output
from my_mobileclient import MyMobileclient
sound_output = Output()

mobile_api = MyMobileclient(debug_logging = devel)
app_id = '1234567890abcdef'

device_id = None

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

directory = os.path.join(os.path.expanduser('~'), '.%s' % name)
artwork_directory = os.path.join(directory, 'artwork')
for d in (directory, artwork_directory):
 if not os.path.isdir(d):
  os.mkdir(d)

import config as _config
from confmanager import parser

class MyApp(wx.App):
 def MainLoop(self, *args, **kwargs):
  """Overrides wx.App.MainLoop, to save the config at the end."""
  res = super(MyApp, self).MainLoop(*args, **kwargs)
  sound_output.stop()
  stuff = {
   'streams': streams,
   'saved_results': saved_results,
   'config': _config.config.get_dump(),
   'device_id': device_id,
   'results_history': results_history,
   'library': library.downloaded
  }
  with open(config_file, 'wb') as f:
   json.dump(stuff, f, indent = 1)
  return res

app = MyApp(False)
app.SetAppDisplayName('%s (v %s)' % (name, version))
app.SetAppName(name)
app.SetVendorName(vendor_name)
app.SetVendorDisplayName(vendor_name)
lyrics_frame = None # The lyrics viewer.

import library

config_file = os.path.join(directory, 'config.json')

main_frame = None

config = {}

def load_config():
 if os.path.isfile(config_file):
  with open(config_file, 'rb') as f:
   try:
    j = json.load(f)
    library.downloaded = j.get('library', {})
    if type(library.downloaded) != dict:
     library.downloaded = {} # Better to clear the user's library than have them suffer tracebacks.
    device_id = j.get('device_id', None)
    s = j.get('streams', streams)
    while streams:
     del streams[0]
    for x in s:
     streams.append(s)
    parser.parse_json(_config.config, j.get('config', {}))
    config.update(**j)
   except ValueError as e:
      wx.MessageBox('Error in config file: %s. Resetting preferences.' % e.message, 'Config Error') # They've broken their config file.

def post_load_config():
 j = config
 try:
  for x, y in j.get('saved_results', {}).iteritems():
   main_frame.add_saved_result(name = x, results = y)
  results_history = j.get('results_history', [])
  if not _config.config.get('windows', 'load_library'):
   main_frame.current_library = None
  if type(_config.config.get('sound', 'volume')) == float:
   _config.config.set('sound', 'volume', 100)
  if type(_config.config.get('sound', 'pan')) == float:
   _config.config.set('sound', 'pan', 50)
  if not os.path.isdir(_config.config.get('library', 'media_directory')):
   _config.config.set('library', 'media_directory', '')
 except ValueError as e:
    wx.MessageBox('Error in config file: %s. Resetting preferences.' % e.message, 'Config Error') # They've broken their config file.
 finally:
  _config.config.updateFunc = functions.config_update

import functions
functions.clean_library()

gmusicapi_version = '9.0.1-dev'
