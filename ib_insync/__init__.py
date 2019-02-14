# flake8: noqa

import sys
import importlib

if sys.version_info < (3, 6, 0):
    raise RuntimeError('ib_insync requires Python 3.6 or higher')

try:
    import ibapi
except ImportError:
    raise RuntimeError(
       'IB API from http://interactivebrokers.github.io is required')

from . import util
if util.ibapiVersionInfo() < (9, 74, 0):
    raise RuntimeError(
        f'Old version ({util.ibapiVersionInfo()} of ibapi package detected,\n'
        f'located at {ibapi.__path__}).\n'
        'Remove this old version and install latest from\n'
        'http://interactivebrokers.github.io')


from .version import __version__, __version_info__
from .objects import (
    Object, ContractDetails, ContractDescription,
    ComboLeg, DeltaNeutralContract, OrderComboLeg, OrderState,
    SoftDollarTier, PriceIncrement, Execution, CommissionReport,
    BarList, BarDataList, RealTimeBarList, BarData, RealTimeBar,
    HistogramData, NewsProvider, DepthMktDataDescription,
    ScannerSubscription, ScanData, ScanDataList,
    ExecutionFilter, PnL, PnLSingle, AccountValue, TickData,
    TickByTickAllLast, TickByTickBidAsk, TickByTickMidPoint,
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast,
    TickAttrib, TickAttribBidAsk, TickAttribLast, FundamentalRatios,
    MktDepthData, DOMLevel, BracketOrder, TradeLogEntry, TagValue,
    PortfolioItem, Position, Fill, OptionComputation, OptionChain, Dividends,
    NewsArticle, HistoricalNews, NewsTick, NewsBulletin, ConnectionStats,
    OrderCondition, ExecutionCondition, OperatorCondition, MarginCondition,
    ContractCondition, TimeCondition, PriceCondition, PercentChangeCondition,
    VolumeCondition)
from .event import Event
from .contract import (
    Contract, Stock, Option, Future, ContFuture, Forex, Index, CFD,
    Commodity, Bond, FuturesOption, MutualFund, Warrant, Bag)
from .order import (
    Trade, OrderStatus, Order, LimitOrder, MarketOrder,
    StopOrder, StopLimitOrder)
from .ticker import Ticker
from .ib import IB
from .client import Client
from .wrapper import Wrapper
from .flexreport import FlexReport, FlexError
from .ibcontroller import IBC, IBController, Watchdog

__all__ = ['util']
for _m in (
        objects, event, contract, order, ticker, ib,
        client, wrapper, flexreport, ibcontroller):
    __all__ += _m.__all__

del sys
del importlib
del ibapi
