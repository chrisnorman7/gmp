"""The keystroke editor for GMP."""

import wx, wx.dataview as dv, application
from wx.lib.sized_controls import SizedFrame

class KeystrokeEditor(SizedFrame):
 """The keystroke editor frame."""
 def __init__(self):
  """Initialise the frame."""
  super(KeystrokeEditor, self).__init__(None, title = 'Keystroke Editor')
  p = self.GetContentsPane()
  p.SetSizerType('form')
  wx.StaticText(p, label = 'Actions')
  wx.StaticText(p, label = 'Keystrokes')
  if application.platform == 'darwin':
   self.actions = dv.DataViewListCtrl(p) # User friendly track list.
   self.actions.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.populate_keystrokes)
   self.keystrokes = dv.DataViewListCtrl(p) # User friendly track list.
  else:
   self.actions = wx.ListCtrl(p, style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
   self.actions.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.populate_keystrokes)
   self.keystrokes = wx.ListCtrl(p, style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
  self.actions.SetFocus()
  
  self.Maximize(True)
  self.Raise()
