import sys
import importlib

if sys.version_info < (3, 6, 0):
    raise RuntimeError('ib_insync requires Python 3.6 or higher')

try:
    import ibapi
except ImportError:
    raise RuntimeError(
        'IB API from http://interactivebrokers.github.io is required')

from . import util  # noqa
if util.ibapiVersionInfo() < (9, 74, 0):
    raise RuntimeError(
        f'Old version ({util.ibapiVersionInfo()} of ibapi package detected,\n'
        f'located at {ibapi.__path__}).\n'
        'Remove this old version and install latest from\n'
        'http://interactivebrokers.github.io')

from .version import __version__, __version_info__  # noqa
from .objects import *  # noqa
from .event import *  # noqa
from .contract import *  # noqa
from .order import *  # noqa
from .ticker import *  # noqa
from .ib import *  # noqa
from .client import *  # noqa
from .wrapper import *  # noqa
from .flexreport import *  # noqa
from .ibcontroller import *  # noqa

__all__ = ['util']
for _m in (
        objects, event, contract, order, ticker, ib,  # noqa
        client, wrapper, flexreport, ibcontroller):  # noqa
    __all__ += _m.__all__

del sys
del importlib
del ibapi
