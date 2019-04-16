# flake8: noqa

import sys
if sys.version_info < (3, 6, 0):
    raise RuntimeError('ib_insync requires Python 3.6 or higher')

from eventkit import Event

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
    FamilyCode, SmartComponent,
    PortfolioItem, Position, Fill, OptionComputation, OptionChain, Dividends,
    NewsArticle, HistoricalNews, NewsTick, NewsBulletin, ConnectionStats)
from .contract import (
    Contract, Stock, Option, Future, ContFuture, Forex, Index, CFD,
    Commodity, Bond, FuturesOption, MutualFund, Warrant, Bag)
from .order import (
    Trade, OrderStatus, Order, LimitOrder, MarketOrder,
    StopOrder, StopLimitOrder,
    OrderCondition, ExecutionCondition, MarginCondition,
    TimeCondition, PriceCondition, PercentChangeCondition,
    VolumeCondition)
from .ticker import Ticker
from .ib import IB
from .client import Client
from .wrapper import Wrapper
from .flexreport import FlexReport, FlexError
from .ibcontroller import IBC, IBController, Watchdog

__all__ = ['util', 'Event']
for _m in (
        objects, contract, order, ticker, ib,
        client, wrapper, flexreport, ibcontroller):
    __all__ += _m.__all__

del sys
