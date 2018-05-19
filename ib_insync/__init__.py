import sys

__version__ = '0.9.22'

if sys.version_info < (3, 6, 0):
    print("Python 3.6.0 or higher is required")
    sys.exit()

try:
    import ibapi
except ImportError:
    print('IB API from http://interactivebrokers.github.io is required')
    sys.exit()

if tuple(int(i) for i in ibapi.__version__.split('.')) < (9, 73, 6):
    print('Old version of ibapi module detected. '
        'The newest version from http://interactivebrokers.github.io '
        'is required')
    sys.exit()

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
