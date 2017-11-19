import sys

if sys.version_info < (3, 6, 0):
    print("Python 3.6.0 or higher is required")
    sys.exit()

try:
    import ibapi
except ImportError:
    print('IB API from http://interactivebrokers.github.io is required')
    sys.exit()

try:
    from ibapi.common import RealTimeBar
except ImportError:
    print('Old version of ibapi module detected. '
        'The newest version from http://interactivebrokers.github.io is required')
    sys.exit()

from .objects import *
from .contract import *
from .order import *
from .ticker import *
from .ib import *
from .client import *
from .wrapper import *
from .flexreport import *
from . import util

__all__ = ['util']
for _m in (objects, contract, order, ticker, ib, client, wrapper, flexreport):
    __all__ += _m.__all__
