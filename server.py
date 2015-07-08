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
var vol, volpulse;
$(document).ready(function() {
 $("#volume").focus(function() {
  volpulse = setInterval(function(){
   if (vol != $("#volume").val()) {
    vol = $("#volume").val();
    $.ajax({
     url: "volume/" + $("#volume").val(),
     async: false
    });
   }
  }, 100);
 }).blur(function(){
  clearInterval(volpulse);
 });
 setInterval(function() {
  $.ajax({
   url: "getjson",
   dataType: "json",
   success: function(stuff) {
    if ("title" in stuff && document.title != stuff.title) {
     document.title = stuff.title;
    }
    if ("volume" in stuff && new String(stuff.volume) != new String($("#volume").val())) {
     vol = stuff.volume;
     if (!($("#volume").is("focus"))) {
      $("#volume").val(vol);
     }
    }
    if ("playpause" in stuff && stuff.playpause != $("#play").text()) {
     $("#play").text(stuff.playpause)
    }
    if ("nowplaying" in stuff && stuff.nowplaying != $("#nowplaying").text()) {
     $("#nowplaying").text(stuff.nowplaying);
    }
    if ("nexttrack" in stuff && stuff.nexttrack != $("#nexttrack").text()) {
     $("#next").text(stuff.nexttrack);
    }
    if ("previoustrack" in stuff && stuff.previoustrack != $("#previous").text()) {
     $("#previous").text(stuff.previoustrack);
    }
   }
  })
 }, 100);
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
  else:
   (uid, pwd) = None, None
  if uid == application.config.get('http', 'uid') and pwd == application.config.get('http', 'pwd'):
   self.do_HEAD(True)
   if self.path == '/getjson':
    next_track = application.config.get('windows', 'next_label').strip('&')
    n = functions.get_next_song()
    if n:
     next_track += ' (%s)' % functions.format_title(n)
    previous_track = application.config.get('windows', 'previous_label').strip('&')
    p = functions.get_previous_song()
    if p:
     previous_track += ' (%s)' % functions.format_title(p)
    self.wfile.write(
     json.dumps(
      dict(
       nexttrack = next_track,
       previoustrack = previous_track,
       title = frame.GetTitle(),
       volume = frame.volume.GetValue(),
       nowplaying = frame.hotkey_area.GetValue(),
       playpause = frame.play_pause.GetLabel().strip('&')
      )
     )
     )
   elif self.path.startswith('/volume/'):
    v = self.path.split('/')
    try:
     v = int(v[-1])
     functions.set_volume(v)
    except ValueError as e:
     self.wfile.write(str(e))
   elif self.path[1:] in urls:
    urls[self.path[1:]]()
   elif self.path == '/':
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
    <td><button id = "play">Play</button></td>
    <td><button id = "next">Next</button></td>
    </tr>
    <tr>
    <td><button id = "volume_down">Volume Down</button></td>
    <td><input type = "range" step = "5" id = "volume" value = "0" min = "0" max = "100"></td>
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
  else:
   self.do_HEAD(False) # Not authenticated.
   self.wfile.write('Not authenticated.')

server_class = BaseHTTPServer.HTTPServer

def get_server():
 """Get an instance of the web server."""
 return server_class((application.config.get('http', 'hostname'), application.config.get('http', 'port')), MyHandler)
