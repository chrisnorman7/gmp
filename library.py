"""GMP's library functions."""

from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import os, errno
from application import directory

media_directory = os.path.join(directory, 'media')

if not os.path.isdir(media_directory):
 os.mkdir(media_directory)

track_extension = '.mp3'
db_path = os.path.join(media_directory, 'library.db')

engine = create_engine('sqlite:///%s' % db_path)
Base = declarative_base()

def make_path(path):
 try:
  os.makedirs(path)
 except OSError as exc: # Python >2.5
  if exc.errno == errno.EEXIST and os.path.isdir(path):
   pass
  else:
   raise

class Track(Base):
 """A track entry in the database."""
 __tablename__ = 'tracks'
 id = Column(String(27), primary_key = True, nullable = False)
 composer = Column(String(100))
 trackType = Column(String(10))
 creationTimestamp = Column(String)
 recentTimestamp = Column(String)
 albumArtist = Column(String(100))
 contentType = Column(String(10))
 deleted = Column(Boolean)
 estimatedSize = Column(Integer)
 lastModifiedTimestamp = Column(String)
 trackNumber = Column(Integer)
 title = Column(String(100))
 artist = Column(String(100))
 album = Column(String(100))
 discNumber = Column(Integer)
 durationMillis = Column(Integer)
 genre = Column(String(40))
 year = Column(Integer)
 playCount = Column(Integer, default = 0)
 downloaded = Column(Float, default = 0.0)
 
 @property
 def filename(self):
  """Returns the filename for this track."""
  return '%s%s - %s%s' % ('0' if self.trackNumber < 10 else '', self.trackNumber, self.title, track_extension)
 
 @property
 def path(self):
  """Get the path where the file should be stored."""
  p = os.path.join(media_directory, self.artist, self.album)
  if not os.path.isdir(p):
   make_path(p)
  return os.path.join(p, self.filename)
 
 def exists(self):
  """Figures out if the file exists."""
  return os.path.isfile(self.path)

Base.metadata.create_all(bind = engine)
session_factory = sessionmaker(bind = engine)
def create_session():
 """Get a session."""
 return scoped_session(session_factory)

def tracks():
 """Return all the tracks in the database."""
 return create_session().query(Track)

