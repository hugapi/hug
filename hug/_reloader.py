"""hug/_reloader.py
Taken from Bottle framework
"""
from collections import namedtuple
import os.path
import threading
import sys
import time
import _thread as thread

status = namedtuple('Status', ('ok', 'reload', 'error', 'exit'))(0, 1, 2, 3)


class FileCheckerThread(threading.Thread):
    """Utility class to interrupt main-thread as soon as a changed module file is detected,
       the lockfile gets deleted or gets too old.
    """
    def __init__(self, lockfile, interval):
        threading.Thread.__init__(self)
        self.lockfile, self.interval = lockfile, interval
        self.status = status.ok

    def run(self):
        exists = os.path.exists
        mtime = lambda path: os.stat(path).st_mtime
        files = dict()

        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', '')
            if path[-4:] in ('.pyo', '.pyc'):
                path = path[:-1]
            if path and exists(path):
                files[path] = mtime(path)

        while not self.status:
            if not (exists(self.lockfile)
            or mtime(self.lockfile) < time.time() - self.interval - 5):
                self.status = status.error
                thread.interrupt_main()
            for path, lmtime in list(files.items()):
                if not exists(path) or mtime(path) > lmtime:
                    self.status = status.reload
                    thread.interrupt_main()
                    break
            time.sleep(self.interval)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.status:
            self.status = status.exit # silent exit
        self.join()
        return exc_type is not None and issubclass(exc_type, KeyboardInterrupt)
