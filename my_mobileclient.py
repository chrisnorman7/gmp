from gmusicapi import Mobileclient
import application, gmusicapi

class MyMobileclient(Mobileclient):
 """My custom Mobileclient."""
 def get_stream_url(self, id): 
  """Gets a device automatically."""
  def f(d):
   """Tries to get a URL with the provided device d."""
   try:
    return super(MyMobileclient, self).get_stream_url(id, d)
   except gmusicapi.exceptions.CallFailure as e:
    return None
  if application.device_id:
   url = f(application.device_id)
   if url:
    return url
  for d in self.get_registered_devices():
   d = d['id']
   url = f(d)
   if url:
    application.device_id = d
    return url
  else:
   raise gmusicapi.exceptions.CallFailure('Cannot get download URLs with any of the devices registered on your account. Please conect to Google Play Music with a mobile device and try again.', 'get_stream_url')
