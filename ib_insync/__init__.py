"""Python sync/async framework for Interactive Brokers API"""

import dataclasses
import sys

from eventkit import Event

from . import util
from .client import Client
from .contract import (
    Bag, Bond, CFD, ComboLeg, Commodity, ContFuture, Contract,
    ContractDescription, ContractDetails, Crypto, DeltaNeutralContract,
    Forex, Future, FuturesOption, Index, MutualFund, Option, ScanData, Stock,
    TagValue, Warrant)
from .flexreport import FlexError, FlexReport
from .ib import IB
from .ibcontroller import IBC, Watchdog
from .objects import (
    AccountValue, BarData, BarDataList, CommissionReport, ConnectionStats,
    DOMLevel, DepthMktDataDescription, Dividends, Execution, ExecutionFilter,
    FamilyCode, Fill, FundamentalRatios, HistogramData, HistoricalNews,
    HistoricalSchedule, HistoricalSession, HistoricalTick,
    HistoricalTickBidAsk, HistoricalTickLast, MktDepthData, NewsArticle,
    NewsBulletin, NewsProvider, NewsTick, OptionChain, OptionComputation,
    PnL, PnLSingle, PortfolioItem,
    Position, PriceIncrement, RealTimeBar, RealTimeBarList, ScanDataList,
    ScannerSubscription, SmartComponent, SoftDollarTier, TickAttrib,
    TickAttribBidAsk, TickAttribLast, TickByTickAllLast, TickByTickBidAsk,
    TickByTickMidPoint, TickData, TradeLogEntry, WshEventData)
from .order import (
    BracketOrder, ExecutionCondition, LimitOrder, MarginCondition, MarketOrder,
    Order, OrderComboLeg, OrderCondition, OrderState, OrderStatus,
    PercentChangeCondition, PriceCondition, StopLimitOrder, StopOrder,
    TimeCondition, Trade, VolumeCondition)
from .ticker import Ticker
from .version import __version__, __version_info__
from .wrapper import RequestError, Wrapper

__all__ = [
    'Event', 'util', 'Client',
    'Bag', 'Bond', 'CFD', 'ComboLeg', 'Commodity', 'ContFuture', 'Contract',
    'ContractDescription', 'ContractDetails', 'Crypto', 'DeltaNeutralContract',
    'Forex', 'Future', 'FuturesOption', 'Index', 'MutualFund', 'Option',
    'ScanData', 'Stock', 'TagValue', 'Warrant', 'FlexError', 'FlexReport',
    'IB', 'IBC', 'Watchdog',
    'AccountValue', 'BarData', 'BarDataList', 'CommissionReport',
    'ConnectionStats', 'DOMLevel', 'DepthMktDataDescription', 'Dividends',
    'Execution', 'ExecutionFilter', 'FamilyCode', 'Fill', 'FundamentalRatios',
    'HistogramData', 'HistoricalNews', 'HistoricalTick',
    'HistoricalTickBidAsk', 'HistoricalTickLast',
    'HistoricalSchedule', 'HistoricalSession', 'MktDepthData',
    'NewsArticle', 'NewsBulletin', 'NewsProvider', 'NewsTick', 'OptionChain',
    'OptionComputation', 'PnL', 'PnLSingle', 'PortfolioItem', 'Position',
    'PriceIncrement', 'RealTimeBar', 'RealTimeBarList', 'ScanDataList',
    'ScannerSubscription', 'SmartComponent', 'SoftDollarTier', 'TickAttrib',
    'TickAttribBidAsk', 'TickAttribLast', 'TickByTickAllLast', 'WshEventData',
    'TickByTickBidAsk', 'TickByTickMidPoint', 'TickData', 'TradeLogEntry',
    'BracketOrder', 'ExecutionCondition', 'LimitOrder', 'MarginCondition',
    'MarketOrder', 'Order', 'OrderComboLeg', 'OrderCondition', 'OrderState',
    'OrderStatus', 'PercentChangeCondition', 'PriceCondition',
    'StopLimitOrder', 'StopOrder', 'TimeCondition', 'Trade', 'VolumeCondition',
    'Ticker', '__version__', '__version_info__', 'RequestError', 'Wrapper'
]


# compatibility with old Object
for obj in locals().copy().values():
    if dataclasses.is_dataclass(obj):
        obj.dict = util.dataclassAsDict
        obj.tuple = util.dataclassAsTuple
        obj.update = util.dataclassUpdate
        obj.nonDefaults = util.dataclassNonDefaults

del sys
del dataclasses
