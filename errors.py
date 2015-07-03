"""GMP Error handling functions."""

import application, functions
from time import time

class Log(object):
 """The error log."""
 def __init__(self):
  self.log = []
 
 def write(self, text):
  """Write an item to the log."""
  v = [time(), text]
  self.log.append(v)
  if application.errors_frame:
   application.errors_frame.append_item(v)

log = Log()
