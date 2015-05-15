"""Functions for the parsing of columns."""
import datetime

def parse_trackNumber(data):
 """Converts from an integer to a string."""
 return '%s%s' % ((0 if data < 10 else ''), str(data))
def parse_year(data):
 """Returnes the year as a string."""
 return str(data)

def parse_durationMillis(data):
 """Returns data as minutes and seconds, rather than milliseconds."""
 d = datetime.timedelta(milliseconds = int(data))
 data = str(d)
 if data.startswith('0:'):
  data = data[2:]
 return data

def parse_trackAvailableForPurchase(data):
 """Prints a * for yes, and a space for no."""
 return '*' if data else ' '
