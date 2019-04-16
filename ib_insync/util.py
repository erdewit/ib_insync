import datetime
import logging
import math
import sys
import signal
import asyncio
import time
from typing import Iterator, AsyncIterator, Callable, Union

import eventkit as ev


globalErrorEvent = ev.Event()
"""
Event to emit global exceptions.
"""


UNSET_INTEGER = 2 ** 31 - 1
UNSET_DOUBLE = sys.float_info.max


def df(objs, labels=None):
    """
    Create pandas DataFrame from the sequence of same-type objects.
    When a list of labels is given then only retain those labels and
    drop the rest.
    """
    import pandas as pd
    from .objects import Object, DynamicObject
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
    from .objects import Object
    if isinstance(obj, (bool, int, float, str, bytes)):
        return obj
    elif isinstance(obj, (datetime.date, datetime.time)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: tree(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [tree(i) for i in obj]
    elif isinstance(obj, Object):
        return {obj.__class__.__qualname__: tree(obj.nonDefaults())}
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
        ohlcTups = [
            tuple(v) for v in bars[['open', 'high', 'low', 'close']].values]
    elif bars and hasattr(bars[0], 'open_'):
        ohlcTups = [(b.open_, b.high, b.low, b.close) for b in bars]
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


def logToFile(path, level=logging.INFO):
    """
    Create a log handler that logs to the given file.
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def logToConsole(level=logging.INFO):
    """
    Create a log handler that logs to the console.
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.handlers = [
        h for h in logger.handlers
        if type(h) is not logging.StreamHandler]
    logger.addHandler(handler)


def isNan(x: float) -> bool:
    """
    Not a number test.
    """
    return x != x


def formatSI(n) -> str:
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
            s += 'yzafpnum kMGTPEZY'[i + 8]
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


def run(*awaitables, timeout: float = None):
    """
    By default run the event loop forever.

    When awaitables (like Tasks, Futures or coroutines) are given then
    run the event loop until each has completed and return their results.

    An optional timeout (in seconds) can be given that will raise
    asyncio.TimeoutError if the awaitables are not ready within the
    timeout period.
    """
    loop = asyncio.get_event_loop()
    if not awaitables:
        if loop.is_running():
            return
        loop.run_forever()
        f = asyncio.gather(*asyncio.Task.all_tasks())
        f.cancel()
        result = None
        try:
            loop.run_until_complete(f)
        except asyncio.CancelledError:
            pass
    else:
        if len(awaitables) == 1:
            future = awaitables[0]
        else:
            future = asyncio.gather(*awaitables)
        if timeout:
            future = asyncio.wait_for(future, timeout)
        task = asyncio.ensure_future(future)

        def onError(_):
            task.cancel()

        globalErrorEvent.connect(onError)
        try:
            result = loop.run_until_complete(task)
        except asyncio.CancelledError as e:
            raise globalErrorEvent.value() or e
        finally:
            globalErrorEvent.disconnect(onError)

    return result


def _fillDate(time):
    # use today if date is absent
    if isinstance(time, datetime.time):
        dt = datetime.datetime.combine(datetime.date.today(), time)
    else:
        dt = time
    return dt


def schedule(
        time: Union[datetime.time, datetime.datetime],
        callback: Callable, *args):
    """
    Schedule the callback to be run at the given time with
    the given arguments.

    Args:
        time: Time to run callback. If given as :py:class:`datetime.time`
            then use today as date.
        callback: Callable scheduled to run.
        args: Arguments for to call callback with.
    """
    dt = _fillDate(time)
    now = datetime.datetime.now(dt.tzinfo)
    delay = (dt - now).total_seconds()
    loop = asyncio.get_event_loop()
    loop.call_later(delay, callback, *args)


def sleep(secs: float = 0.02) -> bool:
    """
    Wait for the given amount of seconds while everything still keeps
    processing in the background. Never use time.sleep().

    Args:
        secs (float): Time in seconds to wait.
    """
    run(asyncio.sleep(secs))
    return True


def timeRange(
        start: datetime.time, end: datetime.time,
        step: float) -> Iterator[datetime.datetime]:
    """
    Iterator that waits periodically until certain time points are
    reached while yielding those time points.

    Args:
        start: Start time, can be specified as datetime.datetime,
            or as datetime.time in which case today is used as the date
        end: End time, can be specified as datetime.datetime,
            or as datetime.time in which case today is used as the date
        step (float): The number of seconds of each period
    """
    assert step > 0
    start = _fillDate(start)
    end = _fillDate(end)
    delta = datetime.timedelta(seconds=step)
    t = start
    while t < datetime.datetime.now():
        t += delta
    while t <= end:
        waitUntil(t)
        yield t
        t += delta


def waitUntil(t: datetime.time) -> bool:
    """
    Wait until the given time t is reached.

    Args:
        t: The time t can be specified as datetime.datetime,
            or as datetime.time in which case today is used as the date.
    """
    t = _fillDate(t)
    now = datetime.datetime.now(t.tzinfo)
    secs = (t - now).total_seconds()
    run(asyncio.sleep(secs))
    return True


async def timeRangeAsync(
        start: datetime.time, end: datetime.time,
        step: float) -> AsyncIterator[datetime.datetime]:
    """
    Async version of :meth:`timeRange`.
    """
    assert step > 0
    start = _fillDate(start)
    end = _fillDate(end)
    delta = datetime.timedelta(seconds=step)
    t = start
    while t < datetime.datetime.now():
        t += delta
    while t <= end:
        await waitUntilAsync(t)
        yield t
        t += delta


async def waitUntilAsync(t: datetime.time) -> bool:
    """
    Async version of :meth:`waitUntil`.
    """
    t = _fillDate(t)
    now = datetime.datetime.now(t.tzinfo)
    secs = (t - now).total_seconds()
    await asyncio.sleep(secs)
    return True


def patchAsyncio():
    """
    Patch asyncio to allow nested event loops.
    """
    import nest_asyncio
    nest_asyncio.apply()


def startLoop():
    """
    Use nested asyncio event loop for Jupyter notebooks.
    """
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

    patchAsyncio()
    loop = asyncio.get_event_loop()
    if not loop.is_running():
        from ipykernel.eventloops import register_integration, enable_gui
        register_integration('asyncio')(_ipython_loop_asyncio)
        enable_gui('asyncio')


def useQt(qtLib: str = 'PyQt5', period: float = 0.01):
    """
    Run combined Qt5/asyncio event loop.

    Args:
        qtLib: Name of Qt library to use, can be 'PyQt5' or 'PySide2'.
        period: Period in seconds to poll Qt.
    """
    def qt_step():
        loop.call_later(period, qt_step)
        if not stack:
            qloop = QEventLoop()
            timer = QTimer()
            timer.timeout.connect(qloop.quit)
            stack.append((qloop, timer))
        qloop, timer = stack.pop()
        timer.start(0)
        qloop.exec_()
        timer.stop()
        stack.append((qloop, timer))

    if qtLib not in ('PyQt5', 'PySide2'):
        raise RuntimeError(f'Unknown Qt library: {qtLib}')
    if qtLib == 'PyQt5':
        from PyQt5.Qt import QApplication, QTimer, QEventLoop
    else:
        from PySide2.QtWidgets import QApplication
        from PySide2.QtCore import QTimer, QEventLoop
    global qApp
    qApp = QApplication.instance() or QApplication(sys.argv)
    loop = asyncio.get_event_loop()
    stack: list = []
    qt_step()


def formatIBDatetime(dt) -> str:
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
