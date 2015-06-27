import BaseHTTPServer, functions, functions, application

urls = {
 'previous': lambda: functions.previous(None),
 'play': functions.play_pause,
 'next': lambda: functions.next(None),
 'volume_down': functions.volume_down,
 'stop': functions.stop,
 'volume_up': functions.volume_up
}

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
 def do_HEAD(self):
  self.send_response(200)
  self.send_header("Content-type", "text/html")
  self.end_headers()
 
 def do_GET(self):
  """Respond to a GET request."""
  self.send_response(200)
  self.send_header("Content-type", "text/html")
  self.end_headers()
  urls.get(self.path[1:], lambda: None)()
  self.wfile.write("""
  <html>
  <head>
  <title>GMP Web Interface</title>
  </head>
  <body>
  <h1>Control GMP from any device with a web browser</h1>
  <p>Disable the server in GMP's Preferences.</p>
  <table>
  <tr>
  <td><a href = "previous">Previous</a></td>
  <td><a href = "play">Play / Pause</a></td>
  <td><a href = "next">Next</a></td>
  </tr>
  <br/>
  <tr>
  <td><a href = "volume_down">Volume Down</a></td>
  <td>Volume: %s%%</td>
  <td><a href = "volume_up">Volume Up</a></td>
  </tr>
  </table>
  </body>
  </html>
  """ % application.main_frame.volume.GetValue())

server_class = BaseHTTPServer.HTTPServer

def get_server():
 """Get an instance of the web server."""
 return server_class((application.config.get('http', 'hostname'), application.config.get('http', 'port')), MyHandler)
