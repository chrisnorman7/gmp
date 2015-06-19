from time import sleep
from shutil import rmtree, copytree, copy
from application import name as appName, version as appVersion
try:
 from application import compress as appCompress
except ImportError:
 appCompress = True

try:
 from application import add_to_site as appAddToSite
except ModuleError:
 appAddToSite = []

from os import system, rename, listdir, walk, path, mkdir, chdir, getcwd, remove
import zipfile, plistlib
import sys

cwd = getcwd()

dels = [
 'dist',
 'build',
 '%s.app' % appName,
 appName
]

for d in dels:
 if d in listdir('.'):
  print 'Deleting %s...' % d
  if path.isfile(d):
   remove(d)
  else:
   rmtree(d)
 else:
  print 'Directory not found so not deleting: %s.' % d

if sys.platform.startswith('win'):
 if 'setup.py' in listdir('.'):
  system('python setup.py py2exe')
  rename('dist', appName)
  while 'main.exe' not in listdir(path.join(cwd, appName)):
   continue
  rename(path.join(cwd, appName, 'main.exe'), path.join(cwd, appName, appName + '.exe'))
  if not appCompress:
   y = path.join(cwd, appName, 'library')
   z = y + '.zip'
   system('unzip "%s" -d "%s"' % (z, y))
   remove(z)
   while 1:
    try:
     rename(y, z)
     break
    except OSError:
     pass
  sp = z
  # GMP-Specific code:
  rmtree(path.join(sp, 'Crypto'))
  copytree('Crypto-win', path.join(sp, 'Crypto'))
 else:
  system('pyinstaller -wy --clean --log-level WARN -n "%s" --distpath . main.py' % appName)
  sp = path.join(cwd, appName)
 output = appName
 xd = appName
elif sys.platform == 'darwin':
 system('py2applet main.py')
 n = '%s.app' % appName
 while 1:
  try:
   rename('main.app', n)
   break
  except OSError:
   continue
 output = n
 x = path.join(cwd, n, 'Contents', 'Resources')
 if not appCompress:
  y = path.join(x, 'lib', 'python2.7', 'site-packages')
  z = y + '.zip'
  print 'Decompressing %s...' % z
  system('unzip "%s" -d "%s"' % (z, y))
  remove(z)
  rename(y, z)
 sp = z
 xd = x
 mkdir(path.join(x, 'English.lproj'))
 pf = path.join(n, 'Contents', 'Info.plist')
 p = plistlib.readPlist(pf)
 p.LSHasLocalizedDisplayName = True
 plistlib.writePlist(p, pf)
 with open(path.join(x, 'English.lproj', 'InfoPlist.strings'), 'w') as f:
  f.write('CFBundleName="%s";\nCFBundleDisplayName="%s";\n' % (appName, appName))
else:
 quit("Don't know how to run on %s." % sys.platform)

def copy(origin, dest):
 print 'Copying to %s.' % dest
 if path.exists(dest):
  if path.isfile(dest):
   remove(dest)
  else:
   rmtree(dest)
 try:
  if path.isdir(origin):
   copytree(origin, dest)
  else:
   copy(origin, dest)
  return True
 except OSError:
  return False

for d in listdir('xtras'):
 if d.startswith('.'):
  continue # Don't copy .ds_store files...
 origin = path.join(cwd, 'xtras', d)
 dest = path.join((sp if d in appAddToSite else xd), d)
 print 'Copying %s to %s.' % (d, dest)
 if not copy(origin, dest):
  print 'Error copying.'

print 'Creating Zipfile...'
z = '%s-%s-%s.zip' % (appName, appVersion, sys.platform)
zf = zipfile.ZipFile(z, 'w')
for root, dirs, files in walk(output):
 for file in files:
  p = path.join(root, file)
  zf.write(p)
zf.close()
print 'Zip file created.'
