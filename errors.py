"""GMP Error handling functions."""

import application, functions
from time import time

class Log(object):
 """The error log."""
 def __init__(self):
  self.log = []
 
 def write(self, text):
  """Write an item to the log."""
  self.log.append([time(), text])

log = Log()
