if __name__ == '__main__':
 import logging, argparse, sys, os.path
 if os.path.basename(sys.executable).startswith('pythonw'):
  sys.stdout = open(os.path.join(os.path.expanduser('~'), 'gmp.log'), 'w')
 parser = argparse.ArgumentParser()
 parser.add_argument('-l', '--logfile', metavar = 'filename', dest = 'log_file', type = argparse.FileType('w'), default = sys.stdout, help = 'Log program errors')
 parser.add_argument('-L', '--loglevel', metavar = 'level', dest = 'log_level', default = 'info', choices = ['debug', 'info', 'warning', 'error', 'critical'], help = 'The logging level')
 args = parser.parse_args()
 logging.basicConfig(stream = args.log_file, level = args.log_level.upper())
 try:
  import certifi, sys, os
  cwd = os.getcwd()
  sys.path.insert(0, os.path.join(cwd, 'library.zip', 'Crypto'))
  sys.path.insert(0, os.path.join(cwd, 'certifi'))
  logging.debug('Running from %s.', cwd)
  import requests, application, wx
  from gui.update_frame import UpdateFrame
  logging.debug('Checking for update...')
  u = UpdateFrame()
  from gmusicapi import __version__ as v
  logging.info('API Version: %s.', v)
  if application.gmusicapi_version > v:
   wx.MessageBox('Gmusicapi version %s is required, but only %s installed. Please install the correct version with the requirements.txt file.' % (application.gmusicapi_version, v), 'Incompatible Gmusicapi Version')
  else:
   from requests.packages.urllib3.exceptions import InsecureRequestWarning
   requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
   application.app.MainLoop()
   logging.info('Application closed.')
 except Exception as e:
  logging.exception(e)
