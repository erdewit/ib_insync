import sys

if sys.version_info < (3, 6, 0):
    raise RuntimeError('ib_insync requires Python 3.6 or higher')

try:
    import ibapi
except ImportError:
    raise RuntimeError(
        'IB API from http://interactivebrokers.github.io is required')

if tuple(int(i) for i in ibapi.__version__.split('.')) < (9, 73, 6):
    raise RuntimeError(
        f'Old version ({ibapi.__version__}) of ibapi package detected. '
        'The newest version from http://interactivebrokers.github.io '
        'is required')

from .version import __version__, __version_info__
from .objects import *
from .event import *
from .contract import *
from .order import *
from .ticker import *
from .ib import *
from .client import *
from .wrapper import *
from .flexreport import *
from .ibcontroller import *
from . import util

__all__ = ['util']
for _m in (objects, event, contract, order, ticker, ib, client, wrapper,
        flexreport, ibcontroller):
    __all__ += _m.__all__
