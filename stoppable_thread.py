from threading import Thread, Event

class StoppableThread(Thread):
 """A thread which can be stopped."""
 def __init__(self, *args, **kwargs):
  super(StoppableThread, self).__init__(*args, **kwargs)
  self.should_stop = Event()
