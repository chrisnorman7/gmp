import BaseHTTPServer, functions, functions, application, json
from base64 import decodestring

urls = {
 'previous': lambda: functions.previous(None),
 'play': functions.play_pause,
 'next': lambda: functions.next(None),
 'volume_down': functions.volume_down,
 'stop': functions.stop,
 'volume_up': functions.volume_up
}

urls_js = """
$(document).ready(function() {
 setInterval(function() {
  $.ajax({
   url: "getjson",
   dataType: "json",
   success: function(stuff) {
    if ("title" in stuff) {
     document.title = stuff.title;
    }
    if ("volume" in stuff) {
     $("#volume").html(stuff.volume + "%");
    }
    if ("nowplaying" in stuff) {
     $("#nowplaying").html(stuff.nowplaying);
    }
   }
  })
 }, 1000);
"""
for k in urls.keys():
 urls_js += """ $("#%s").click(function() {$.ajax({url: "%s", async: true})});\n""" % (k, k)
urls_js += ' }\n);\n'

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
    if self.path == '/getjson':
     self.wfile.write(json.dumps(dict(title = frame.GetTitle(), volume = frame.volume.GetValue(), nowplaying = frame.hotkey_area.GetValue())))
     return
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
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
    <script>%s</script>
    <title></title>
    </head>
    <body>
    <h1>%s: Web Interface</h1>
    <p>Control your music from any device with a web browser</p>
    <div role="complementary">
    <p>Disable the server in the application's Preferences.</p>
    </div>
    <div role = "main">
    <h2 id="nowplaying">Now playing</h2>
    <table>
    <tr>
    <td><button id = "previous">Previous</button></td>
    <td><button id = "play">Play / Pause</button></td>
    <td><button id = "next">Next</button></td>
    </tr>
    <tr>
    <td><button id = "volume_down">Volume Down</button></td>
    <td id = "volume">0%%</td>
    <td><button id = "volume_up">Volume Up</button></td>
    </tr>
    </table>
    </div>
    <div role = "contentinfo">
    <p>Served by %s on %s.</p>
    </div>
    </body>
    </html>
    """ %
    (urls_js, application.name, self.server_version, self.sys_version)
    )
    return
  self.do_HEAD(False) # Not authenticated.
  self.wfile.write('Not authenticated.')

server_class = BaseHTTPServer.HTTPServer

def get_server():
 """Get an instance of the web server."""
 return server_class((application.config.get('http', 'hostname'), application.config.get('http', 'port')), MyHandler)
