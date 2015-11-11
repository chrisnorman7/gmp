from distutils.core import setup
import py2exe

setup(
 windows = ['main.py'],
 name = 'GMP',
 zipfile = None,
 modules = ['Carbon', 'Carbon.Files', 'Crypto.Cipher', 'Crypto.PublicKey', 'OpenSSL.SSL', '_datetime', '_scproxy', '_sysconfigdata', 'appdirs', 'backports.ssl_match_hostname', 'ca_certs_locater', 'dateutil.parser', 'dbm.dumb', 'dbm.gnu', 'dbm.ndbm', 'email.FeedParser', 'email.Message', 'email.Utils', 'espeak.core', 'gdbm', 'google.appengine.api', 'google.appengine.api.urlfetch', 'google.protobuf', 'google.protobuf.descriptor', 'google.protobuf.message', 'google3.apphosting.api', 'google3.apphosting.api.urlfetch', 'libloader.load_library', 'mechanicalsoup', 'mutagen', 'oauth2client', 'oauth2client.client', 'oauth2client.file', 'packages.ssl_match_hostname.CertificateError', 'packages.ssl_match_hostname.match_hostname', 'packages.urllib3.util.Timeout', 'packages.urllib3.util.parse_url', 'pyasn1.codec.der', 'pyasn1.type', 'reprlib.recursive_repr', 'simplejson', 'test.support', 'unittest2', 'urllib.parse', 'urllib.request', '_thread.get_ident'],
 compress = False
)
