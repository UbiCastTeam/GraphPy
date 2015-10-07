import threading
import logging
logger = logging.getLogger('GankPy.threaded')

class Thread(threading.Thread):
    """Used to run a function or method in a thread"""
    
    def __init__(self, func, *args, **kwargs):
        threading.Thread.__init__(self)
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.result = None
        self.success = None
    
    def _get_my_tid(self):
        """determines this (self's) thread id"""
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")
 
        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id
 
        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid
        raise AssertionError("could not determine the thread's id")
    
    def run(self):
        try:
            return_value = self._func(*self._args, **self._kwargs)
            self.result = return_value
            self.success = True
        except Exception as e:
            self.result = e
            self.success = False
    
    def get_result(self):
        if self.success is None:
            raise Exception("Execution is not finished")
        if self.success:
            return self.result
        raise self.result
    
    def raise_exc(self, exctype):
        """raises the given exception type in the context of this thread"""
        _async_raise(self._get_my_tid(), exctype)
 
    def terminate(self):
        """raises SystemExit in the context of the given thread, which should 
        cause the thread to exit silently (unless caught)"""
        self.raise_exc(SystemExit)

def _thread_it(daemon, func, *args, **kwargs):
    thread = Thread(func, *args, **kwargs)
    thread.daemon = daemon
    try:
        thread.start()
    except Exception as e:
        logger.error("Cannot start thread %s for function %s with args %s and kwargs %s. Error is: %s", thread, func, args, kwargs, e)
        logger.info("Number of active threads: %s", threading.active_count())
        logger.info("Threads: %s", threading._active)
        logger.info("Current frames: %s", sys._current_frames())
        raise
    return thread

def thread_it(func, *args, **kwargs):
    """Run function or method in a thread and return this thread"""
    return _thread_it(False, func, *args, **kwargs)
