"""GMP's library functions."""

import os, errno, string, application, wx, functions

downloaded = {} # The stuff that GMP has downloaded.
downloading = {} # The stuff that is currently downloading.

def valid_filename(name):
 """Takes a string and turns it into a valid filename."""
 valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
 return ''.join(c for c in name if c in valid_chars)

_media_directory = os.path.join(application.directory, 'media')
def media_directory():
 """Get the actual media directory."""
 dir = application.config.get('library', 'media_directory') or _media_directory
 if not os.path.isdir(dir):
  make_path(dir)
 return dir

track_extension = '.mp3'

def make_path(path):
 try:
  os.makedirs(path)
 except OSError as exc: # Python >2.5
  if exc.errno == errno.EEXIST and os.path.isdir(path):
   pass
  else:
   raise

def get_filename(item):
 """Returns the filename for this track."""
 return '%s%s - %s%s' % ('0' if item['trackNumber'] < 10 else '', item['trackNumber'], item['title'], track_extension)

def get_path(item):
 """Get the path where the file should be stored."""
 p = os.path.join(media_directory(), valid_filename(item['artist']), valid_filename(item['album']))
 if not os.path.isdir(p):
  make_path(p)
 return os.path.join(p, valid_filename(get_filename(item)))

def exists(item):
 """Figures out if the file exists."""
 return os.path.isfile(get_path(item))
