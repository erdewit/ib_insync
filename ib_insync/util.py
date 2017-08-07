import datetime
import logging
import sys
import math
import signal
import asyncio
import time

from ib_insync.objects import Object


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


def syncAwait(future):
    """
    Synchronously wait until future is done, accounting for the possibilty
    that the event loop is already running.
    """
    try:
        import quamash
    except ImportError:
        quamash = None

    loop = asyncio.get_event_loop()
    if loop.is_running():
        if quamash and isinstance(loop, quamash.QEventLoop):
            result = syncAwaitQt(future)
        else:
            result = syncAwaitAsyncio(future)
    else:
        result = loop.run_until_complete(future)
    return result


def syncAwaitAsyncio(future):
    assert asyncio.Task is asyncio.tasks._PyTask
    asyncio._asyncAwait = True
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
    asyncio._asyncAwait = False
    return future.result()


def syncAwaitQt(self, future):
    import PyQt5.Qt as qt

    future = asyncio.ensure_future(future)
    def stop(*_args):
        self.stop()
    future.add_done_callback(stop)
    qApp = qt.QApplication.instance()
    try:
        self.run_forever()
    finally:
        future.remove_done_callback(stop)
    while not future.done():
        qApp.processEvents()
        if future.done():
            break
        time.sleep(0.005)
    return future.result()


def patchAsyncio():
    """
    Patch asyncio to use pure Python implementation of Future and Task,
    to deal with nested event loops in asynAwait.
    """
    if asyncio.Task is not asyncio.tasks._PyTask:
        asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = \
                asyncio.tasks._PyTask
        asyncio.Future = asyncio.futures._CFuture = asyncio.futures.Future = \
                asyncio.futures._PyFuture
    asyncio._asyncAwait = False


def startLoop():
    """
    Use asyncio event loop for Jupyter notebooks.
    """
    patchAsyncio()
    from ipykernel.eventloops import register_integration, enable_gui

    @register_integration('asyncio')
    def loop_asyncio(kernel):
        '''
        Start a kernel with asyncio event loop support.
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
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    enable_gui('asyncio')


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


def formatIBDatetime(dt):
    """
    Format date or datetime to what string that IB uses.
    """
    if not dt:
        s = ''
    elif isinstance(dt, datetime.datetime):
        s = dt.strftime('%Y%m%d %H:%M:%S')
    elif isinstance(dt, datetime.date):
        s = dt.strftime('%Y%m%d 23:59:59')
    else:
        s = dt
    return s


def parseIBDatetime(s):
    """
    Parse string in IB date or datatime format to datetime.
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
