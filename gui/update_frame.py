from updatecheck import UpdateCheckFrame as _Frame
import application, wx

class UpdateFrame(_Frame):
 def __init__(self):
  """Initialise the update frame."""
  return super(UpdateFrame, self).__init__(application.name, application.version, application.update_url)
 
 def Show(self, value = True):
  """Show the frame."""
  self.status.SetWindowStyle(wx.TE_READONLY|wx.TE_MULTILINE)
  res = super(UpdateFrame, self).Show(value)
  self.Raise()
  self.Maximize(True)
  return res
 
 def updateCheck(self):
  """Processes the json."""
  try:
   j = self.request.json()
  except ValueError:
   return # The json object is malformed, or the URL is invalid.
  if j.get('version', application.version) > application.version:
   self.Show(True)
   self.request = j
   self.updateButton.SetDefault()
   return '%s %s is available.\n\nChangelog for this version:\n%s' % (j['name'], j['version'], j.get('changelog', 'No changelog available.'))
  else:
   if self.Shown:
    wx.MessageBox('%s %s is already the latest version' % (application.name, application.version), 'No Update Available')
   wx.CallAfter(self.Close, True)
 
 def onUpdate(self, event):
  """Download the file."""
  import webbrowser, sys
  urls = self.request.get('urls', {})
  if sys.platform in urls:
   webbrowser.open(urls[sys.platform])
  else:
   wx.MessageBox('Sorry, but no download link could be found for your platform (%s).' % sys.platform, 'No URL Found')
  wx.CallAfter(self.Close, True)
