from updatecheck import UpdateCheckFrame as _Frame
import json, application

class UpdateFrame(_Frame):
 def __init__(self):
  """Initialise the update frame."""
  return super(UpdateFrame, self).__init__(application.name, application.version, application.update_url)
 
 def Show(self, value = True):
  """Show the frame."""
  res = super(UpdateFrame, self).Show(value)
  self.Raise()
  self.Maximize(True)
  return res
 
 def updateCheck(self):
  """Processes the json."""
  try:
   j = json.loads(self.request.content)
  except ValueError:
   return # The json object is malformed.
  if j.get('version', application.version) > application.version:
   self.Show(True)
   self.request = j
   self.updateButton.SetDefault()
   return '%s %s is available.' % (j['name'], j['version'])
  else:
   self.Close(True)
 
 def onUpdate(self, event):
  """Download the file."""
  import webbrowser, sys
  urls = self.request.get('urls', {})
  if sys.platform in urls:
   webbrowser.open(urls[sys.platform])
  else:
   wx.MessageBox('Sorry, but no download link could be found for your platform (%s).' % sys.platform, 'No URL Found')
  self.Close(True)
