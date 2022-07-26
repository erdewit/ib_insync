"""Utilities."""

import asyncio
import logging
import math
import signal
import sys
import time
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time as time_, timedelta, timezone
from typing import AsyncIterator, Awaitable, Callable, Iterator, List, Union

import eventkit as ev

globalErrorEvent = ev.Event()
"""
Event to emit global exceptions.
"""

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
UNSET_INTEGER = 2 ** 31 - 1
UNSET_DOUBLE = sys.float_info.max


def df(objs, labels: List[str] = None):
    """
    Create pandas DataFrame from the sequence of same-type objects.

    Args:
      labels: If supplied, retain only the given labels and drop the rest.
    """
    import pandas as pd
    from .objects import DynamicObject
    if objs:
        objs = list(objs)
        obj = objs[0]
        if is_dataclass(obj):
            df = pd.DataFrame.from_records(dataclassAsTuple(o) for o in objs)
            df.columns = [field.name for field in fields(obj)]
        elif isinstance(obj, DynamicObject):
            df = pd.DataFrame.from_records(o.__dict__ for o in objs)
        else:
            df = pd.DataFrame.from_records(objs)
        if isinstance(obj, tuple):
            _fields = getattr(obj, '_fields', None)
            if _fields:
                # assume it's a namedtuple
                df.columns = _fields
    else:
        df = None
    if labels:
        exclude = [label for label in df if label not in labels]
        df = df.drop(exclude, axis=1)
    return df


def dataclassAsDict(obj) -> dict:
    """
    Return dataclass values as ``dict``.
    This is a non-recursive variant of ``dataclasses.asdict``.
    """
    if not is_dataclass(obj):
        raise TypeError(f'Object {obj} is not a dataclass')
    return {field.name: getattr(obj, field.name) for field in fields(obj)}


def dataclassAsTuple(obj) -> tuple:
    """
    Return dataclass values as ``tuple``.
    This is a non-recursive variant of ``dataclasses.astuple``.
    """
    if not is_dataclass(obj):
        raise TypeError(f'Object {obj} is not a dataclass')
    return tuple(getattr(obj, field.name) for field in fields(obj))


def dataclassNonDefaults(obj) -> dict:
    """
    For a ``dataclass`` instance get the fields that are different from the
    default values and return as ``dict``.
    """
    if not is_dataclass(obj):
        raise TypeError(f'Object {obj} is not a dataclass')
    values = [getattr(obj, field.name) for field in fields(obj)]
    return {
        field.name: value for field, value in zip(fields(obj), values)
        if value != field.default
        and value == value
        and not (isinstance(value, list) and value == [])}


def dataclassUpdate(obj, *srcObjs, **kwargs) -> object:
    """
    Update fields of the given ``dataclass`` object from zero or more
    ``dataclass`` source objects and/or from keyword arguments.
    """
    if not is_dataclass(obj):
        raise TypeError(f'Object {obj} is not a dataclass')
    for srcObj in srcObjs:
        obj.__dict__.update(dataclassAsDict(srcObj))
    obj.__dict__.update(**kwargs)
    return obj


def dataclassRepr(obj) -> str:
    """
    Provide a culled representation of the given ``dataclass`` instance,
    showing only the fields with a non-default value.
    """
    attrs = dataclassNonDefaults(obj)
    clsName = obj.__class__.__qualname__
    kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
    return f'{clsName}({kwargs})'


def isnamedtupleinstance(x):
    """From https://stackoverflow.com/a/2166841/6067848"""
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n) == str for n in f)


def tree(obj):
    """
    Convert object to a tree of lists, dicts and simple values.
    The result can be serialized to JSON.
    """
    if isinstance(obj, (bool, int, float, str, bytes)):
        return obj
    elif isinstance(obj, (date, time_)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: tree(v) for k, v in obj.items()}
    elif isnamedtupleinstance(obj):
        return {f: tree(getattr(obj, f)) for f in obj._fields}
    elif isinstance(obj, (list, tuple, set)):
        return [tree(i) for i in obj]
    elif is_dataclass(obj):
        return {obj.__class__.__qualname__: tree(dataclassNonDefaults(obj))}
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
    """Allow Control-C to end program."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def logToFile(path, level=logging.INFO):
    """Create a log handler that logs to the given file."""
    logger = logging.getLogger()
    if logger.handlers:
        logging.getLogger('ib_insync').setLevel(level)
    else:
        logger.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s')
    handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def logToConsole(level=logging.INFO):
    """Create a log handler that logs to the console."""
    logger = logging.getLogger()
    stdHandlers = [
        h for h in logger.handlers
        if type(h) is logging.StreamHandler and h.stream is sys.stderr]
    if stdHandlers:
        # if a standard stream handler already exists, use it and
        # set the log level for the ib_insync namespace only
        logging.getLogger('ib_insync').setLevel(level)
    else:
        # else create a new handler
        logger.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def isNan(x: float) -> bool:
    """Not a number test."""
    return x != x


def formatSI(n: float) -> str:
    """Format the integer or float n to 3 significant digits + SI prefix."""
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
    """Context manager for timing."""

    def __init__(self, title='Run'):
        self.title = title

    def __enter__(self):
        self.t0 = time.time()

    def __exit__(self, *_args):
        print(self.title + ' took ' + formatSI(time.time() - self.t0) + 's')


def run(*awaitables: Awaitable, timeout: float = None):
    """
    By default run the event loop forever.

    When awaitables (like Tasks, Futures or coroutines) are given then
    run the event loop until each has completed and return their results.

    An optional timeout (in seconds) can be given that will raise
    asyncio.TimeoutError if the awaitables are not ready within the
    timeout period.
    """
    loop = getLoop()
    if not awaitables:
        if loop.is_running():
            return
        loop.run_forever()
        result = None
        if sys.version_info >= (3, 7):
            all_tasks = asyncio.all_tasks(loop)  # type: ignore
        else:
            all_tasks = asyncio.Task.all_tasks()  # type: ignore
        if all_tasks:
            # cancel pending tasks
            f = asyncio.gather(*all_tasks)
            f.cancel()
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


def _fillDate(time: Union[time_, datetime]) -> datetime:
    # use today if date is absent
    if isinstance(time, time_):
        dt = datetime.combine(date.today(), time)
    else:
        dt = time
    return dt


def schedule(
        time: Union[time_, datetime], callback: Callable, *args):
    """
    Schedule the callback to be run at the given time with
    the given arguments.
    This will return the Event Handle.

    Args:
        time: Time to run callback. If given as :py:class:`datetime.time`
            then use today as date.
        callback: Callable scheduled to run.
        args: Arguments for to call callback with.
    """
    dt = _fillDate(time)
    now = datetime.now(dt.tzinfo)
    delay = (dt - now).total_seconds()
    loop = getLoop()
    return loop.call_later(delay, callback, *args)


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
        start: Union[time_, datetime],
        end: Union[time_, datetime],
        step: float) -> Iterator[datetime]:
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
    delta = timedelta(seconds=step)
    t = _fillDate(start)
    tz = timezone.utc if t.tzinfo else None
    now = datetime.now(tz)
    while t < now:
        t += delta
    while t <= _fillDate(end):
        waitUntil(t)
        yield t
        t += delta


def waitUntil(t: Union[time_, datetime]) -> bool:
    """
    Wait until the given time t is reached.

    Args:
        t: The time t can be specified as datetime.datetime,
            or as datetime.time in which case today is used as the date.
    """
    now = datetime.now(t.tzinfo)
    secs = (_fillDate(t) - now).total_seconds()
    run(asyncio.sleep(secs))
    return True


async def timeRangeAsync(
        start: Union[time_, datetime],
        end: Union[time_, datetime],
        step: float) -> AsyncIterator[datetime]:
    """Async version of :meth:`timeRange`."""
    assert step > 0
    delta = timedelta(seconds=step)
    t = _fillDate(start)
    tz = timezone.utc if t.tzinfo else None
    now = datetime.now(tz)
    while t < now:
        t += delta
    while t <= _fillDate(end):
        await waitUntilAsync(t)
        yield t
        t += delta


async def waitUntilAsync(t: Union[time_, datetime]) -> bool:
    """Async version of :meth:`waitUntil`."""
    now = datetime.now(t.tzinfo)
    secs = (_fillDate(t) - now).total_seconds()
    await asyncio.sleep(secs)
    return True


def patchAsyncio():
    """Patch asyncio to allow nested event loops."""
    import nest_asyncio
    nest_asyncio.apply()


def getLoop():
    """Get the asyncio event loop for the current thread."""
    return asyncio.get_event_loop_policy().get_event_loop()


def startLoop():
    """Use nested asyncio event loop for Jupyter notebooks."""
    patchAsyncio()


def useQt(qtLib: str = 'PyQt5', period: float = 0.01):
    """
    Run combined Qt5/asyncio event loop.

    Args:
        qtLib: Name of Qt library to use:

          * PyQt5
          * PyQt6
          * PySide2
          * PySide6
        period: Period in seconds to poll Qt.
    """
    def qt_step():
        loop.call_later(period, qt_step)
        if not stack:
            qloop = qc.QEventLoop()
            timer = qc.QTimer()
            timer.timeout.connect(qloop.quit)
            stack.append((qloop, timer))
        qloop, timer = stack.pop()
        timer.start(0)
        qloop.exec() if qtLib == 'PyQt6' else qloop.exec_()
        timer.stop()
        stack.append((qloop, timer))
        qApp.processEvents()

    if qtLib not in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6'):
        raise RuntimeError(f'Unknown Qt library: {qtLib}')
    from importlib import import_module
    qc = import_module(qtLib + '.QtCore')
    qw = import_module(qtLib + '.QtWidgets')
    global qApp
    qApp = (qw.QApplication.instance()     # type: ignore
            or qw.QApplication(sys.argv))  # type: ignore
    loop = getLoop()
    stack: list = []
    qt_step()


def formatIBDatetime(dt: Union[date, datetime, str, None]) -> str:
    """Format date or datetime to string that IB uses."""
    if not dt:
        s = ''
    elif isinstance(dt, datetime):
        if dt.tzinfo:
            # convert to local system timezone
            dt = dt.astimezone(tz=None)
        s = dt.strftime('%Y%m%d %H:%M:%S')
    elif isinstance(dt, date):
        s = dt.strftime('%Y%m%d 23:59:59')
    else:
        s = dt
    return s


def parseIBDatetime(s: str) -> Union[date, datetime]:
    """Parse string in IB date or datetime format to datetime."""
    if len(s) == 8:
        # YYYYmmdd
        y = int(s[0:4])
        m = int(s[4:6])
        d = int(s[6:8])
        dt = date(y, m, d)
    elif s.isdigit():
        dt = datetime.fromtimestamp(int(s), timezone.utc)
    else:
        # YYYYmmdd  HH:MM:SS
        # or
        # YYYY-mm-dd HH:MM:SS.0
        ss = s.replace(' ', '').replace('-', '')[:16]
        dt = datetime.strptime(ss, '%Y%m%d%H:%M:%S')
    return dt
