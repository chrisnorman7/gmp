"""Login frame for Google Music Player."""

import wx, application, requests, functions, logging, config
from wx.lib.sized_controls import SizedFrame as SF
from threading import Thread
from functions import format_requests_error

logger = logging.getLogger('Login Frame')

class LoginFrame(SF):
 """Frame to log in with."""
 def __init__(self):
  super(LoginFrame, self).__init__(None, title = 'Login')
  self.processing = False # Set to true when we start the login process.
  p = self.GetContentsPane()
  p.SetSizerType('form')
  wx.StaticText(p, label = config.config.get('windows', 'uid_label'))
  self.uid = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER, value = config.config.get('login', 'uid'))
  self.uid.Bind(wx.EVT_TEXT_ENTER, self.do_login)
  wx.StaticText(p, label = config.config.get('windows', 'pwd_label'))
  self.pwd = wx.TextCtrl(p, style = wx.TE_PASSWORD|wx.TE_PROCESS_ENTER, value = config.config.get('login', 'pwd'))
  self.pwd.Bind(wx.EVT_TEXT_ENTER, self.do_login)
  if self.uid.GetValue():
   self.pwd.SetFocus()
  wx.StaticText(p, label = config.config.get('windows', 'remember_label'))
  self.remember = wx.CheckBox(p, label = config.config.get('windows', 'remember_label'))
  self.remember.SetValue(config.config.get('login', 'remember'))
  wx.Button(p, label = config.config.get('windows', 'cancel_label')).Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.login = wx.Button(p, label = config.config.get('windows', 'login_label'))
  self.login.SetDefault()
  self.login.Bind(wx.EVT_BUTTON, self.do_login)
  self.Maximize()
  self.Show(True)
  self.Raise()
  if self.uid.GetValue() and self.pwd.GetValue():
   self.do_login()
 
 def do_login(self, event = None):
  """Starts the thread that performs the login, so the GUI doesn't freeze."""
  if self.processing:
   return functions.bell()()
  self.processing = True
  self.login.SetLabel('Logging in...')
  self.login.Disable()
  self.uid.Disable()
  self.pwd.Disable()
  Thread(target = self._do_login, args = [self.uid.GetValue(), self.pwd.GetValue()]).start()
 
 def _do_login(self, uid, pwd):
  """Actually perform the login."""
  try:
   if application.mobile_api.login(uid, pwd, application.mobile_api.FROM_MAC_ADDRESS):
    logger.info('Login successful.')
    config.config.set('login', 'uid', self.uid.GetValue())
    if self.remember.GetValue():
     config.config.set('login', 'pwd', self.pwd.GetValue())
    else:
     config.config.set('login', 'pwd', '')
    config.config.set('login', 'remember', self.remember.GetValue())
    wx.CallAfter(self.post_login)
   else:
    logger.warning('Login failed.')
    wx.CallAfter(self.login.SetLabel, config.config.get('windows', 'login_label'))
    wx.CallAfter(self.login.Enable)
    wx.CallAfter(self.uid.Enable)
    wx.CallAfter(self.pwd.Enable)
    wx.CallAfter(wx.MessageBox, 'Login unsuccessful. If this is your first time logging in, please try again, and report if the error persists.', 'Error')
    wx.CallAfter(self.uid.SetSelection, 0, -1)
    wx.CallAfter(self.pwd.SetSelection, 0, -1)
    self.processing = False
  except requests.exceptions.RequestException as e:
   wx.MessageBox(*format_requests_error(e), style = wx.ICON_EXCLAMATION)
   return self.Close(True)
  except wx.PyDeadObjectError:
   logger.warning('User closed the main frame before login could be completed.')
 
 def post_login(self):
  """Closes this window and opens the main frame."""
  try:
   from gui.main_frame import MainFrame
   application.main_frame = MainFrame()
   application.main_frame.Show(True)
  except wx.PyDeadObjectError:
   pass # The user closed it already.
  finally:
   self.Close(True)
