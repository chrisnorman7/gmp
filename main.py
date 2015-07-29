if __name__ == '__main__':
 import logging, errors
 logging.basicConfig(stream = errors.log, level = logging.INFO)
 import certifi, sys, os
 #sys.stderr = errors.log
 #sys.stdout = errors.log
 sys.path.insert(0, os.path.join(os.getcwd(), 'library.zip', 'Crypto'))
 sys.path.insert(0, os.path.join(os.getcwd(), 'certifi'))
 import requests, application, wx
 from gui.update_frame import UpdateFrame
 u = UpdateFrame()
 from gmusicapi import __version__ as v
 if application.gmusicapi_version > v:
  wx.MessageBox('Gmusicapi version %s is required, but only %s installed. Please install the correct version with the requirements.txt file.' % (application.gmusicapi_version, v), 'Incompatible Gmusicapi Version')
 else:
  from gui.login_frame import LoginFrame
  from requests.packages.urllib3.exceptions import InsecureRequestWarning
  requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
  LoginFrame()
  application.app.MainLoop()
