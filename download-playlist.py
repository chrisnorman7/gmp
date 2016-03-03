import os, sys, string, argparse, logging

parser = argparse.ArgumentParser(version = '1.0')
parser.add_argument('dir', default = os.getcwd(), nargs = '?', help = 'The directory in which the resulting MP3 files should be saved')
parser.add_argument('-u', '--username', help = 'The username to log in with')
parser.add_argument('-p', '--password', help = 'The login password')
parser.add_argument('-w', '--wait', default = 10.0, type = float, help = 'Time to wait between downloads')
parser.add_argument('-r', '--random-id', action = 'store_true', help = 'Randomise the android Id')
parser.add_argument('-l', '--logfile', type = argparse.FileType('w'), default = sys.stdout, help = 'Log program output')
parser.add_argument('--loglevel', default = 'warning', help = 'The logging level')

args = parser.parse_args()

try:
 logging.basicConfig(stream = args.logfile, level = args.loglevel.upper())
except ValueError as v:
 quit(logging.critical(v))

if not os.path.isdir(args.dir):
 try:
  logging.warning('Creating output directory %s.', args.dir)
  os.mkdir(args.dir)
 except OSError:
  quit(logging.critical('Could not make directory: %s.', args.dir))

id_fields = [
 'storeId',
 'id',
 'trackId',
 'nid',
]

def get_id(item):
 """Return the ID for the provided item."""
 for x in id_fields:
  if x in item:
   return item[x]

def valid_filename(name):
 """Takes a string and turns it into a valid filename."""
 valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
 return ''.join(c for c in name if c in valid_chars)

from time import time, ctime, sleep
from random import choice
from gmusicapi import Mobileclient
from gmusicapi.exceptions import CallFailure
from getpass import getpass
from requests import get
from shutil import copyfileobj
from cmenu import Menu

api = Mobileclient(debug_logging = False)

if not args.username:
 args.username = raw_input('Username: ')
if not args.password:
 args.password = getpass('Password:')

logging.debug('Logging in uwer %s.', args.username)
if not api.login(args.username, args.password, ''.join([choice('1234567890abcdef') for x in xrange(16)]) if args.random_id else api.FROM_MAC_ADDRESS):
 quit('Login failed.')

m = Menu('Select source to download')
m.add_entry('Library', api.get_all_songs)
for p in api.get_all_playlists():
 m.add_entry('%s playlist' % p.get('name', 'Untitled'), lambda token = p['shareToken']: [x['track'] for x in api.get_shared_playlist_contents(token)])
res = m.get_selection()
if res:
 logging.debug('Getting source contents.')
 program_start = time()
 logging.info('Started the download at %s.', ctime(program_start))
 total = 0.0 # The average download time.
 try:
  for i, r in enumerate(res()):
   logging.debug('Result = %s', r)
   artist = valid_filename(r.get('artist', 'Unknown Artist'))
   album = valid_filename(r.get('album', 'Unknown Album'))
   number = r.get('trackNumber', 0)
   if number < 10:
    number = '0%s' % number
   else:
    number = str(number)
   title = valid_filename(r.get('title', 'Untitled'))
   filename = u'%s - %s.mp3' % (number, title)
   path = os.path.join(args.dir, artist, album)
   filename = os.path.join(path, filename)
   if os.path.isfile(filename):
    print('Track already downloaded: %s - %s.' % (artist, title))
    continue
   if not os.path.isdir(path):
    logging.debug('Creating directory for downloaded track: %s', path)
    os.makedirs(path)
   if args.wait:
    print('Waiting %.2f seconds between tracks.' % args.wait)
    sleep(args.wait)
   print(u'Downloading %s - %s to %s.' % (artist, title, filename))
   start = time()
   logging.debug('Started download at %s.', ctime(start))
   try:
    url = api.get_stream_url(get_id(r))
   except CallFailure as e:
    print('Error getting track URL from google.')
    continue
   logging.debug('URL = %s', url)
   while True:
    try:
     g = get(url, stream = True)
     if g.status_code != 200:
      logging.critical('Download failed with status code %s.', g.status_code)
      break
     else:
      g.raw.decode_content = True
      with open(filename, 'wb') as f:
       copyfileobj(g.raw, f)
       logging.debug('Wrote %s bytes.', len(g.content))
       track_total = time() - start
       total += track_total
       print('Download completed in %.2f seconds.' % track_total)
      break
    except Exception as e:
     logging.exception(e)
 except KeyboardInterrupt:
  logging.debug('Program terminated by user.')
  print('Exiting.')
 print('Downloaded %s %s in %.2f seconds (%.2f average).' % (i + 1, 'file' if not i else 'files', time() - program_start, total / (i + 1)))
else:
 quit('Exiting.')
