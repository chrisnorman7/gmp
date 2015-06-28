import BaseHTTPServer, functions, functions, application
from base64 import decodestring

urls = {
 'previous': lambda: functions.previous(None),
 'play': functions.play_pause,
 'next': lambda: functions.next(None),
 'volume_down': functions.volume_down,
 'stop': functions.stop,
 'volume_up': functions.volume_up
}

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
 def do_HEAD(self, authorized = False):
  if authorized:
   self.send_response(200)
  else:
   self.send_response(401)
   self.send_header('WWW-Authenticate', 'Basic realm="%s"' % application.name)
  self.send_header("Content-type", "text/html")
  self.end_headers()
 
 def do_GET(self):
  """Respond to a GET request."""
  auth =  self.headers.getheader('authorization')
  frame = application.main_frame
  if auth and auth.lower().startswith('basic '):
   (uid, pwd) = decodestring(auth[6:]).split(':')
   if uid == application.config.get('http', 'uid') and pwd == application.config.get('http', 'pwd'):
    self.do_HEAD(True)
    urls.get(self.path[1:], lambda: None)()
    self.wfile.write(u"""
    <!doctype html>
    <html lang = "en">
    <head>
    <style>
    table, th, td {
    border: 1px solid black;
    }
    </style>
    <title>%s</title>
    </head>
    <body>
    <h1>%s: Web Interface</h1>
    <p>Control your music from any device with a web browser</p>
    <div role="complementary">
    <p>Disable the server in the application's Preferences.</p>
    </div>
    <div role = "main">
    <table>
    <tr>
    <td><a href = "previous">Previous</a></td>
    <td><a href = "play">Play / Pause</a></td>
    <td><a href = "next">Next</a></td>
    </tr>
    <tr>
    <td><a href = "volume_down">Volume Down</a></td>
    <td>Volume: %s%%</td>
    <td><a href = "volume_up">Volume Up</a></td>
    </tr>
    </table>
    </div>
    <div role = "contentinfo">
    <p>Served by %s on %s.</p>
    </div>
    </body>
    </html>
    """ %
    (frame.GetTitle(), application.name, frame.volume.GetValue(), self.server_version, self.sys_version)
    )
    return
  self.do_HEAD(False) # Not authenticated.
  self.wfile.write('Not authenticated.')

server_class = BaseHTTPServer.HTTPServer

def get_server():
 """Get an instance of the web server."""
 return server_class((application.config.get('http', 'hostname'), application.config.get('http', 'port')), MyHandler)
