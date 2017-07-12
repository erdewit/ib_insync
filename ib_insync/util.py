import datetime
import logging
import sys
import math
import signal
import asyncio
import time

from ib_insync.objects import Object

__all__ = (
        'dateRange allowCtrlC logToFile logToConsole '
        'isNan formatSI timeit useQt').split()


def dateRange(startDate, endDate, skipWeekend=True):
    """
    Iterate the days from given start date up to and including end date.
    """
    day = datetime.timedelta(days=1)
    date = startDate
    while True:
        if skipWeekend:
            while date.weekday() >= 5:
                date += day
        if date > endDate:
            break
        yield date
        date += day

def df(objs, labels=None):
    """
    Create pandas DataFrame from the sequence of same-type objects.
    When a list of labels is given then only retain those labels and
    drop the rest.
    """
    import pandas as pd
    if objs:
        objs = list(objs)
        obj = objs[0]
        if isinstance(obj, Object):
            df = pd.DataFrame.from_records(o.tuple() for o in objs)
            df.columns = obj.__class__.defaults
        else:
            df = pd.DataFrame.from_records(objs)
        if isinstance(obj, tuple) and hasattr(obj, '_fields'):
            # assume it's a namedtuple
            df.columns = obj.__class__._fields
    else:
        df = None
    if labels:
        exclude = [label for label in df if label not in labels]
        df.drop(exclude)
    return df

def allowCtrlC():
    """
    Allow Control-C to end program.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def logToFile(path, level=logging.INFO, rootLevel=logging.ERROR):
    """
    Create a log handler that logs to the given file.
    """
    rootLogger = logging.getLogger()
    ibLogger = logging.getLogger('ib_insync')
    rootLogger.setLevel(rootLevel)
    ibLogger.setLevel(level)
    formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    rootLogger.addHandler(handler)


def logToConsole(level=logging.INFO, rootLevel=logging.ERROR):
    """
    Create a log handler that logs to the console.
    """
    rootLogger = logging.getLogger()
    ibLogger = logging.getLogger('ib_insync')
    rootLogger.setLevel(rootLevel)
    ibLogger.setLevel(level)
    formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    rootLogger.addHandler(handler)


def isNan(x: float):
    """
    Not a number test.
    """
    return x != x


def formatSI(n):
    """
    Format the integer or float n to 3 signficant digits + SI prefix.
    """
    s = ''
    if n < 0:
        n = -n
        s += '-'
    if type(n) is int and n < 1000:
        s = str(n) + ' '
    elif n < 1e-22:
        s = '0.00 '
    else:
        assert n < 9.99e26
        log = int(math.floor(math.log10(n)))
        i, j = divmod(log, 3)
        for _try in range(2):
            templ = '%.{}f'.format(2 - j)
            val = templ % (n * 10 ** (-3 * i))
            if val != '1000':
                break
            i += 1
            j = 0
        s += val + ' '
        if i != 0:
            s += 'yzafpnm kMGTPEZY'[i + 7]
    return s


class timeit:
    """
    Context manager for timing.
    """
    def __init__(self, title='Run'):
        self.title = title

    def __enter__(self):
        self.t0 = time.time()

    def __exit__(self, *_args):
        print(self.title + ' took ' + formatSI(time.time() - self.t0) + 's')


def useQt():
    """
    Let the Qt event loop spin the asycio event loop.
    """
    import PyQt5.Qt as qt
    import quamash

    if isinstance(asyncio.get_event_loop(), quamash.QEventLoop):
        return
    if not qt.QApplication.instance():
        _qApp = qt.QApplication(sys.argv)
    loop = quamash.QEventLoop()
    asyncio.set_event_loop(loop)

    # fix the issue were run_until_complete does not work in Jupyter
    def run_until_complete(self, future):
        future = asyncio.ensure_future(future)
        def stop(*_args):
            self.stop()
        future.add_done_callback(stop)
        qApp = qt.QApplication.instance()
        try:
            self.run_forever()
        finally:
            future.remove_done_callback(stop)
        while(not future.done()):
            qApp.processEvents()
            if future.done():
                break
            time.sleep(0.001)
        return future.result()
    quamash.QEventLoop.run_until_complete = run_until_complete

