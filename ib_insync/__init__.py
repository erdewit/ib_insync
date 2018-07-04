import sys

# Module information
__author__ ='Ewald R. de Wit'
__license__ = 'BSD'
__version__ = '0.9.25'
__maintainer__ = __author__
__email__ = 'ewald.de.wit@gmail.com'

if sys.version_info < (3, 6, 0):
    raise SystemError("Python 3.6.0 or higher is required")

try:
    import ibapi
except ImportError:
    raise ImportError('IB API from http://interactivebrokers.github.io is \
required')

if tuple(int(i) for i in ibapi.__version__.split('.')) < (9, 73, 6):
    raise ImportError('Old version of ibapi module detected. The newest verion \
from http://interactivebrokers.github.io is required')

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
