"""Functions for the parsing of columns."""

import datetime, logging
from time import ctime

logger = logging.getLogger('Columns')
def parse_trackNumber(data):
 """Converts from an integer to a string."""
 return '%s%s' % ((0 if data < 10 else ''), str(data))

def parse_year(data):
 """Returnes the year as a string."""
 return str(data)

def parse_durationMillis(data):
 """Returns data as minutes and seconds, rather than milliseconds."""
 data = int(data)
 data = data - (data % 1000)
 d = datetime.timedelta(milliseconds = data)
 data = str(d)
 if data.startswith('0:'):
  data = data[2:]
 return data

def boolean_as_string(data):
 """Prints a * for yes, and a space for no."""
 return '*' if data else ' '

parse_trackAvailableForPurchase = boolean_as_string
parse_deleted = boolean_as_string

def time_as_string(data):
 """Returns floating point times as a string."""
 logger.debug('Converting %s to time.', data)
 try:
  return ctime(float(data))
 except Exception as e:
  logger.exception(e)
  return '(Error) %s' % data

parse_creationTimestamp = time_as_string
parse_recentTimestamp = time_as_string
