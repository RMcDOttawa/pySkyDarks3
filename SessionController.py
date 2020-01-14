# Class with an instance shared by the main event controller and the session worker
# Using mutex-lock, basic status such as "cancel the thread" can be set by the main controller
# and safely read and responded to by the worker.
# Another lock is available externally and is used to ensure only one thread at a time
# sends TCP commands to the TheSkyX server



class SessionController:

    def __init__(self):
        self._mutex = QMutex()
        self._thread_ok_to_run = True

    def cancel_thread(self):
        self._mutex.lock()
        self._thread_ok_to_run = False
        self._mutex.unlock()

    def thread_running(self):
        self._mutex.lock()
        result = self._thread_ok_to_run
        self._mutex.unlock()
        return result

    def thread_cancelled(self):
        return not self.thread_running()

