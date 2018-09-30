import sys
import importlib

from .version import __version__, __version_info__  # noqa
from . import util


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

__all__ = ['util']
for _name in (
        'objects', 'event', 'contract', 'order', 'ticker', 'ib',
        'client', 'wrapper', 'flexreport', 'ibcontroller'):
    _mod = importlib.import_module(f'ib_insync.{_name}')
    __all__ += _mod.__all__
    locals().update((k, getattr(_mod, k)) for k in _mod.__all__)

del sys
del importlib
del ibapi
