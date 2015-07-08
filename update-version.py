import json
from application import name, version

with open('version.json', 'w') as f:
 url = 'http://code-metropolis.com/download/%s-%s-{platform}.zip' % (name, version)
 j = {}
 j['name'] = name
 j['version'] = version
 urls = {
  'darwin': url.format(platform = 'darwin'),
  'win32': url.format(platform = 'win32')
 }
 j['urls'] = urls
 json.dump(j, f)
