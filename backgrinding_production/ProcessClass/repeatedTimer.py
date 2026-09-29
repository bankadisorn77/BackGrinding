# Cradit : MestreLion https://stackoverflow.com/questions/3393612/run-certain-code-every-n-seconds
from threading import Timer

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        #self.start()

    def _run(self):
        try:
            if(self.is_running == False):
                self.stop()
                return
            self.is_running = False
            self.start()
            self.function(*self.args, **self.kwargs)
        except KeyboardInterrupt:
            self.stop()
            return

    def start(self):
        try:
            if not self.is_running:
                self._timer = Timer(self.interval, self._run)
                self._timer.start()
                self.is_running = True
        except KeyboardInterrupt:
            self.stop()
            return


    def stop(self):
        self._timer.cancel()
        self.is_running = False
