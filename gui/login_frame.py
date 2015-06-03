"""Login frame for Google Music Player."""

import wx, application, requests
from wx.lib.sized_controls import SizedFrame as SF
from threading import Thread
from functions import format_requests_error

class LoginFrame(SF):
 """Frame to log in with."""
 def __init__(self):
  super(LoginFrame, self).__init__(None, title = 'Login')
  self.SetAcceleratorTable(wx.AcceleratorTable([]))
  self.processing = False # Set to true when we start the login process.
  p = self.GetContentsPane()
  p.SetSizerType('form')
  wx.StaticText(p, label = application.config.get('windows', 'uid_label'))
  self.uid = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER, value = application.config.get('login', 'uid'))
  self.uid.Bind(wx.EVT_TEXT_ENTER, self.do_login)
  wx.StaticText(p, label = application.config.get('windows', 'pwd_label'))
  self.pwd = wx.TextCtrl(p, style = wx.TE_PASSWORD|wx.TE_PROCESS_ENTER, value = application.config.get('login', 'pwd'))
  self.pwd.Bind(wx.EVT_TEXT_ENTER, self.do_login)
  if self.uid.GetValue():
   self.pwd.SetFocus()
  wx.StaticText(p, label = application.config.get('windows', 'remember_label'))
  self.remember = wx.CheckBox(p, label = application.config.get('windows', 'remember_label'))
  self.remember.SetValue(application.config.get('login', 'remember'))
  wx.Button(p, label = application.config.get('windows', 'cancel_label')).Bind(wx.EVT_BUTTON, self.do_cancel)
  self.login = wx.Button(p, label = application.config.get('windows', 'login_label'))
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
   return wx.Bell()
  self.processing = True
  self.login.SetLabel('Logging in...')
  self.login.Disable()
  self.uid.Disable()
  self.pwd.Disable()
  Thread(target = self._do_login).start()
 
 def _do_login(self):
  """Actually perform the login."""
  try:
   if application.mobile_api.login(self.uid.GetValue(), self.pwd.GetValue()):
    application.config.set('login', 'uid', self.uid.GetValue())
    if self.remember.GetValue():
     application.config.set('login', 'pwd', self.pwd.GetValue())
    else:
     application.config.set('login', 'pwd', '')
    application.config.set('login', 'remember', self.remember.GetValue())
    wx.CallAfter(self.post_login)
   else:
    wx.CallAfter(self.login.SetLabel, application.config.get('windows', 'login_label'))
    wx.CallAfter(self.login.Enable)
    wx.CallAfter(self.uid.Enable)
    wx.CallAfter(self.pwd.Enable)
    wx.CallAfter(wx.MessageBox, 'Login unsuccessful', 'Error')
    wx.CallAfter(self.uid.SetSelection, 0, -1)
    wx.CallAfter(self.pwd.SetSelection, 0, -1)
    self.processing = False
  except requests.exceptions.RequestException as e:
   wx.MessageBox(*format_requests_error(e))
   application.main_frame.Close(True)
   return self.Close(True)
 
 def do_cancel(self, event = None):
  """Closes this window and application.main_frame."""
  application.main_frame.Close(True)
  return self.Close(True)
 
 def post_login(self):
  """Closes this window and opens the main frame."""
  application.main_frame.Show(True)
  self.Close(True)
