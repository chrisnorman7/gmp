"""The column editor."""

import wx, wx.dataview as dv, application
from wx.lib.sized_controls import SizedFrame
from wx.lib.intctrl import IntCtrl

class ColumnEditor(SizedFrame):
 """The Column Editor frame."""
 def __init__(self):
  """Creates the frame."""
  super(ColumnEditor, self).__init__(None, title = 'Column Editor')
  self._columns = application.columns
  self.current_column = -1 # The index of the last column.
  self.column_spec = None # The short name of the current column.
  p = self.GetContentsPane()
  p.SetSizerType('form')
  if application.platform == 'darwin':
   self.columns = dv.DataViewListCtrl(p)
   self.columns.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.populate_column)
   self.columns.AppendTextColumn('Column')
  else:
   self.columns = wx.ListCtrl(p, style = wx.LC_REPORT)
   self.columns.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.populate_column)
   self.columns.InsertColumn(0, 'Column')
  self.init_columns()
  self.include = wx.CheckBox(p, label = '&Include')
  wx.StaticText(p, label = '&Friendly Name')
  self.friendly_name = wx.TextCtrl(p, style = wx.TE_PROCESS_ENTER)
  self.friendly_name.Bind(wx.EVT_TEXT_ENTER, self.do_apply)
  wx.StaticText(p, label = 'Column &Width')
  self.width = IntCtrl(p, min = -1, max = 1500)
  wx.Button(p, label = 'Move &Up').Bind(wx.EVT_BUTTON, self.do_move_up)
  wx.Button(p, label = 'Move &Down').Bind(wx.EVT_BUTTON, self.do_move_down)
  self.apply = wx.Button(p, label = '&Apply')
  self.apply.Bind(wx.EVT_BUTTON, self.do_apply)
  self.apply.SetDefault()
  wx.Button(p, label = '&Close').Bind(wx.EVT_BUTTON, lambda event: self.Close(True))
  self.Maximize(True)
  self.Raise()
  self.Bind(wx.EVT_CLOSE, self.do_close)
 
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
  application.columns = self._columns
  try:
   application.main_frame.reload_results()
  except Exception as e:
   wx.MessageBox('Can\'t update results table: %s.' % str(e), 'Error')
 
 def init_columns(self):
  """Get the table ready and populate it with the columns in their correct order."""
  self.columns.DeleteAllItems()
  for x, y in self._columns:
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
  self.do_apply()
  return event.Skip(True)
