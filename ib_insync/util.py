import datetime
import logging
import sys
import math
import signal
import asyncio
import time

from ib_insync.objects import Object, DynamicObject


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
        elif isinstance(obj, DynamicObject):
            df = pd.DataFrame.from_records(o.__dict__ for o in objs)
        else:
            df = pd.DataFrame.from_records(objs)
        if isinstance(obj, tuple) and hasattr(obj, '_fields'):
            # assume it's a namedtuple
            df.columns = obj.__class__._fields
    else:
        df = None
    if labels:
        exclude = [label for label in df if label not in labels]
        df = df.drop(exclude, axis=1)
    return df


def tree(obj):
    """
    Convert object to a tree of lists, dicts and simple values.
    The result can be serialized to JSON.
    """
    if isinstance(obj, (bool, int, float, str, bytes)):
        return obj
    elif isinstance(obj, (datetime.date, datetime.time)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: tree(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [tree(i) for i in obj]
    elif isinstance(obj, Object):
        return {obj.__class__.__name__: tree(obj.nonDefaults())}
    else:
        return str(obj)


def barplot(bars, title='', upColor='blue', downColor='red'):
    """
    Create candlestick plot for the given bars. The bars can be given as
    a DataFrame or as a list of bar objects.
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    if isinstance(bars, pd.DataFrame):
        ohlcTups = [tuple(v) for v in
                bars[['open', 'high', 'low', 'close']].values]
    else:
        ohlcTups = [(b.open, b.high, b.low, b.close) for b in bars]

    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.grid(True)
    fig.set_size_inches(10, 6)
    for n, (open_, high, low, close) in enumerate(ohlcTups):
        if close >= open_:
            color = upColor
            bodyHi, bodyLo = close, open_
        else:
            color = downColor
            bodyHi, bodyLo = open_, close
        line = Line2D(
                xdata=(n, n),
                ydata=(low, bodyLo),
                color=color,
                linewidth=1)
        ax.add_line(line)
        line = Line2D(
                xdata=(n, n),
                ydata=(high, bodyHi),
                color=color,
                linewidth=1)
        ax.add_line(line)
        rect = Rectangle(
                xy=(n - 0.3, bodyLo),
                width=0.6,
                height=bodyHi - bodyLo,
                edgecolor=color,
                facecolor=color,
                alpha=0.4,
                antialiased=True
        )
        ax.add_patch(rect)

    ax.autoscale_view()
    return fig


def allowCtrlC():
    """
    Allow Control-C to end program.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def logToFile(path, level=logging.INFO, ibapiLevel=logging.ERROR):
    """
    Create a log handler that logs to the given file.
    """
    logger = logging.getLogger()
    f = RootLogFilter(ibapiLevel)
    logger.addFilter(f)
    logger.setLevel(level)
    formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def logToConsole(level=logging.INFO, ibapiLevel=logging.ERROR):
    """
    Create a log handler that logs to the console.
    """
    logger = logging.getLogger()
    f = RootLogFilter(ibapiLevel)
    logger.addFilter(f)
    logger.setLevel(level)
    formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.handlers = [h for h in logger.handlers
            if type(h) is not logging.StreamHandler]
    logger.addHandler(handler)


class RootLogFilter:

    def __init__(self, ibapiLevel=logging.ERROR):
        self.ibapiLevel = ibapiLevel

    def filter(self, record):
        # if it's logged on the root logger assume it's from ibapi
        if record.name == 'root' and record.levelno < self.ibapiLevel:
            return False
        else:
            return True


def isNan(x: float):
    """
    Not a number test.
    """
    return x != x


def formatSI(n):
    """
    Format the integer or float n to 3 significant digits + SI prefix.
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


def patchAsyncio():
    """
    Patch asyncio to use pure Python implementation of Future and Task,
    to deal with nested event loops in syncAwait.
    """
    asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = \
            asyncio.tasks._PyTask
    asyncio.Future = asyncio.futures._CFuture = asyncio.futures.Future = \
            asyncio.futures._PyFuture


def syncAwait(future):
    """
    Synchronously wait until future is done, accounting for the possibility
    that the event loop is already running.
    """
    loop = asyncio.get_event_loop()

    try:
        import quamash
        isQuamash = isinstance(loop, quamash.QEventLoop)
    except ImportError:
        isQuamash = False

    if not loop.is_running():
        result = loop.run_until_complete(future)
    elif isQuamash:
        result = _syncAwaitQt(future)
    else:
        result = _syncAwaitAsyncio(future)
    return result


def _syncAwaitAsyncio(future):
    assert asyncio.Task is asyncio.tasks._PyTask, \
            'To allow nested event loops, use util.patchAsyncio()'
    loop = asyncio.get_event_loop()
    preserved_ready = list(loop._ready)
    loop._ready.clear()
    future = asyncio.ensure_future(future)
    current_tasks = asyncio.Task._current_tasks
    preserved_task = current_tasks.get(loop)
    while not future.done():
        loop._run_once()
        if loop._stopping:
            break
    loop._ready.extendleft(preserved_ready)
    if preserved_task is not None:
        current_tasks[loop] = preserved_task
    else:
        current_tasks.pop(loop, None)
    return future.result()


def _syncAwaitQt(future):
    import PyQt5.Qt as qt
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(future, loop=loop)
    qLoop = qt.QEventLoop()
    future.add_done_callback(lambda f: qLoop.quit())
    qLoop.exec_()
    return future.result() if future.done() else None


def startLoop():
    """
    Use asyncio event loop for Jupyter notebooks.
    """
    patchAsyncio()
    from ipykernel.eventloops import register_integration, enable_gui

    register_integration('asyncio')(_ipython_loop_asyncio)
    enable_gui('asyncio')


def _ipython_loop_asyncio(kernel):
    '''
    Use asyncio event loop for the given IPython kernel.
    '''
    loop = asyncio.get_event_loop()

    def kernel_handler():
        kernel.do_one_iteration()
        loop.call_later(kernel._poll_interval, kernel_handler)

    loop.call_soon(kernel_handler)
    try:
        if not loop.is_running():
            loop.run_forever()
    finally:
        if not loop.is_running():
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()


def useQt():
    """
    Integrate asyncio and Qt loops:
    Let the Qt event loop spin the asyncio event loop
    (does not work with nested event loops in Windows)
    """
    import PyQt5.Qt as qt
    import quamash
    if isinstance(asyncio.get_event_loop(), quamash.QEventLoop):
        return
    if not qt.QApplication.instance():
        _ = qt.QApplication(sys.argv)
    loop = quamash.QEventLoop()
    asyncio.set_event_loop(loop)


def formatIBDatetime(dt):
    """
    Format date or datetime to string that IB uses.
    """
    if not dt:
        s = ''
    elif isinstance(dt, datetime.datetime):
        if dt.tzinfo:
            # convert to local system timezone
            dt = dt.astimezone()
        s = dt.strftime('%Y%m%d %H:%M:%S')
    elif isinstance(dt, datetime.date):
        s = dt.strftime('%Y%m%d 23:59:59')
    else:
        s = dt
    return s


def parseIBDatetime(s):
    """
    Parse string in IB date or datetime format to datetime.
    """
    if len(s) == 8:
        # YYYYmmdd
        y = int(s[0:4])
        m = int(s[4:6])
        d = int(s[6:8])
        dt = datetime.date(y, m, d)
    elif s.isdigit():
        dt = datetime.datetime.fromtimestamp(
                int(s), datetime.timezone.utc)
    else:
        dt = datetime.datetime.strptime(s, '%Y%m%d  %H:%M:%S')
    return dt
