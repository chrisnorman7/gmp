"""A Python console for Google Music Player."""

import wx, sys, application, os, functions, copy

class PythonConsole(wx.Frame):
 """A python console."""
 def __init__(self):
  self.stdout = copy.copy(sys.stdout)
  self.stderr = copy.copy(sys.stderr)
  super(PythonConsole, self).__init__(application.main_frame, title = 'Python Console')
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  self.output = wx.TextCtrl(p, style = wx.TE_MULTILINE|wx.TE_READONLY)
  s.Add(self.output, 1, wx.GROW)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  self.prompt = wx.StaticText(p, label = '&Entry')
  s1.Add(self.prompt, 0, wx.GROW)
  self.entry = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER)
  self.entry.SetFocus()
  self.entry.Bind(wx.EVT_TEXT_ENTER, self.exec_code)
  s1.Add(self.entry, 1, wx.GROW)
  self.close_button = wx.Button(p, label = application.config.get('windows', 'close_label'))
  self.close_button.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  s1.Add(self.close_button, 0, wx.GROW)
  s.Add(s1, 0, wx.GROW)
  p.SetSizerAndFit(s)
  self.Raise()
  self.Bind(wx.EVT_CLOSE, self.on_close)
 
 def Show(self, value = True):
  """Show the window."""
  if value == True:
   sys.stdout = self.output
   sys.stderr = self.output
  s = super(PythonConsole, self).Show(value)
  self.Maximize(True)
  return s
 
 def on_close(self, event):
  """Closes the window."""
  sys.stderr = self.stderr
  sys.stdout = self.stdout
  return event.Skip()
 
 def exec_code(self, event):
  """Executes code."""
  code = self.entry.GetValue()
  print 'Command: %s' % code
  eval(compile(code, self.GetTitle(), 'exec'))
  self.entry.Clear()

if __name__ == '__main__':
 a = wx.App()
 p = PythonConsole()
 p.Show(True)
 a.MainLoop()
 print 'Exiting Python Console...'
