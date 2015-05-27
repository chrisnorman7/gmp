"""The column editor."""

import wx, wx.dataview as dv, application
from wx.lib.intctrl import IntCtrl

class ColumnEditor(wx.Frame):
 """The Column Editor frame."""
 def __init__(self):
  """Creates the frame."""
  super(ColumnEditor, self).__init__(application.main_frame, title = 'Column Editor')
  n = 'Column Name'
  w = 500
  self._columns = application.columns
  self.current_column = -1 # The index of the last column.
  self.column_spec = None # The short name of the current column.
  p = wx.Panel(self)
  s = wx.BoxSizer(wx.VERTICAL)
  s1 = wx.BoxSizer(wx.HORIZONTAL)
  if application.platform == 'darwin':
   self.columns = dv.DataViewListCtrl(p)
   self.columns.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.populate_column)
   self.columns.AppendTextColumn(n, width = w)
  else:
   self.columns = wx.ListCtrl(p, style = wx.LC_REPORT)
   self.columns.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.populate_column)
   self.columns.InsertColumn(0, n, width = w)
  self.init_columns()
  s1.Add(self.columns, 1, wx.GROW)
  s2 = wx.BoxSizer(wx.VERTICAL)
  self.include = wx.CheckBox(p, label = '&Include')
  s2.Add(self.include, 1, wx.GROW)
  self.move_up = wx.Button(p, label = 'Move &Up')
  s2.Add(self.move_up, 1, wx.GROW)
  self.move_up.Bind(wx.EVT_BUTTON, self.do_move_up)
  self.move_down = wx.Button(p, label = 'Move &Down')
  s2.Add(self.move_down, 1, wx.GROW)
  self.move_down.Bind(wx.EVT_BUTTON, self.do_move_down)
  s1.Add(s2, 0, wx.GROW)
  s.Add(s1, 1, wx.GROW)
  s3 = wx.BoxSizer(wx.HORIZONTAL)
  s3.Add(wx.StaticText(p, label = '&Friendly Name'), 0, wx.GROW)
  self.friendly_name = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER)
  s3.Add(self.friendly_name, 1, wx.GROW)
  self.friendly_name.Bind(wx.EVT_TEXT_ENTER, self.do_apply)
  s.Add(s3, 0, wx.GROW)
  s4 = wx.BoxSizer(wx.HORIZONTAL)
  s4.Add(wx.StaticText(p, label = '&Column Width'), 0, wx.GROW)
  self.width = IntCtrl(p, min = -1, max = 1500)
  s4.Add(self.width, 1, wx.GROW)
  s.Add(s4, 0, wx.GROW)
  s5 = wx.BoxSizer(wx.HORIZONTAL)
  self.set_default = wx.Button(p, label = '&Set Default')
  s5.Add(self.set_default, 1, wx.GROW)
  self.set_default.Bind(wx.EVT_BUTTON, lambda event: self.init_columns(setattr(self, '_columns', application.default_columns)) if wx.MessageBox('Are you sure you want to set the layout of all columns to their default values?', 'Are You Sure', style = wx.YES_NO) == wx.YES else None)
  self.close = wx.Button(p, label = 'Close &Window')
  s5.Add(self.close, 1, wx.GROW)
  self.close.Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.close.SetDefault()
  s.Add(s5, 0, wx.GROW)
  p.SetSizerAndFit(s)
  self.Raise()
  self.Bind(wx.EVT_CLOSE, self.do_close)
 
 def Show(self, value = True):
  """Shows the window, maximizing first."""
  s = super(ColumnEditor, self).Show(value)
  self.Maximize(True)
  return s
 
 def get_current_column(self):
  """Returns the current result."""
  if application.platform == 'darwin':
   return self.columns.GetSelection().GetID() - 1
  else:
   return self.columns.GetFocusedItem()
 
 def populate_column(self, event):
  """Fills out the form with the stuff from application.columns."""
  if self.current_column != -1:
   self._columns[self.current_column] = [
    self.column_spec,
    {
     'friendly_name': self.friendly_name.GetValue(),
     'include': self.include.GetValue(),
     'width': self.width.GetValue()
    }
   ]
  self.current_column = self.get_current_column()
  spec, column = self._columns[self.current_column]
  self.column_spec = spec
  self.friendly_name.SetValue(column.get('friendly_name', spec.title()))
  self.include.SetValue(column.get('include', False))
  self.width.SetValue(column.get('width', -1))
 
 def do_apply(self, event = None):
  """Writes the current column to the columns list. Suppress bell sound if silent is set. Update the results table in the main frame if update is True."""
  self.populate_column(None)
  application.columns = self._columns
  try:
   application.main_frame.reload_results()
  except Exception as e:
   wx.MessageBox('Can\'t update results table: %s.' % str(e), 'Error')
 
 def init_columns(self, event = None):
  """Get the table ready and populate it with the columns in their correct order."""
  self.columns.DeleteAllItems()
  for x in self._columns:
   x, y = x
   x = y.get('friendly_name', 'Unknown')
   if application.platform == 'darwin':
    self.columns.AppendItem([x])
   else:
    self.columns.Append([x])
 
 def do_move_up(self, event):
  """Move the current entry up the pecking order."""
  self.current_column = -1
  cr = self.get_current_column()
  if cr < 1:
   return wx.Bell() # It's already at the top.
  self._columns.insert(cr - 1, self._columns.pop(cr))
  self.init_columns()
 
 def do_move_down(self, event):
  """Move the current entry down the pecking order."""
  self.current_column = -1
  cr = self.get_current_column()
  if cr == (len(self._columns) - 1):
   return wx.Bell() # It's already at the bottom.
  self._columns.insert(cr + 1, self._columns.pop(cr))
  self.init_columns()
 
 def do_close(self, event):
  """Applies, and closes the window."""
  try:
   self.do_apply()
  except Exception:
   pass # Ignore any failures, they're probably down to quit being issued anyways.
  return event.Skip()
