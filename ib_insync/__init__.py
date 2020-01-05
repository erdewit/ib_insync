# flake8: noqa

import sys
if sys.version_info < (3, 6, 0):
    raise RuntimeError('ib_insync requires Python 3.6 or higher')

from eventkit import Event

from .version import __version__, __version_info__
from .objects import (
    SoftDollarTier, PriceIncrement, Execution, CommissionReport,
    BarList, BarDataList, RealTimeBarList, BarData, RealTimeBar,
    HistogramData, NewsProvider, DepthMktDataDescription,
    ScannerSubscription, ScanDataList,
    ExecutionFilter, PnL, PnLSingle, AccountValue, TickData,
    TickByTickAllLast, TickByTickBidAsk, TickByTickMidPoint,
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast,
    TickAttrib, TickAttribBidAsk, TickAttribLast, FundamentalRatios,
    MktDepthData, DOMLevel, TradeLogEntry, FamilyCode, SmartComponent,
    PortfolioItem, Position, Fill, OptionComputation, OptionChain, Dividends,
    NewsArticle, HistoricalNews, NewsTick, NewsBulletin, ConnectionStats)
from .contract import (
    Contract, Stock, Option, Future, ContFuture, Forex, Index, CFD,
    Commodity, Bond, FuturesOption, MutualFund, Warrant, Bag,
    TagValue, ComboLeg, DeltaNeutralContract, ContractDetails,
    ContractDescription, ScanData)
from .order import (
    Order, Trade, LimitOrder, MarketOrder, StopOrder, StopLimitOrder,
    BracketOrder, OrderCondition, ExecutionCondition, MarginCondition,
    TimeCondition, PriceCondition, PercentChangeCondition, VolumeCondition,
    OrderStatus, OrderState, OrderComboLeg)
from .ticker import Ticker
from .ib import IB
from .client import Client
from .wrapper import Wrapper
from .flexreport import FlexReport, FlexError
from .ibcontroller import IBC, IBController, Watchdog
import ib_insync.util as util

__all__ = ['util', 'Event']
for _m in (
        objects, contract, order, ticker, ib,  # type: ignore
        client, wrapper, flexreport, ibcontroller):  # type: ignore
    __all__ += _m.__all__

# compatibility with old Object
import dataclasses
for obj in locals().copy().values():
    if dataclasses.is_dataclass(obj):
        obj.dict = util.dataclassAsDict
        obj.tuple = util.dataclassAsTuple
        obj.update = util.dataclassUpdate
        obj.nonDefaults = util.dataclassNonDefaults

del sys
del dataclasses
