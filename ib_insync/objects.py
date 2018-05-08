from collections import namedtuple

import ibapi.scanner
import ibapi.contract
import ibapi.common
import ibapi.order
import ibapi.order_state
import ibapi.softdollartier
import ibapi.execution
import ibapi.commission_report

# order conditions are imported as-is from ibapi
from ibapi.order_condition import (OrderCondition, ExecutionCondition,
        OperatorCondition, MarginCondition, ContractCondition, TimeCondition,
        PriceCondition, PercentChangeCondition, VolumeCondition)

from ib_insync.event import Event

__all__ = (
    'Object ContractDetails ContractDescription '
    'ComboLeg UnderComp DeltaNeutralContract OrderComboLeg OrderState '
    'ScannerSubscription SoftDollarTier '
    'Execution CommissionReport ExecutionFilter '
    'BarList BarDataList RealTimeBarList BarData RealTimeBar '
    'HistogramData TickAttrib NewsProvider DepthMktDataDescription '
    'PnL PnLSingle AccountValue RealTimeBar TickData '
    'TickByTickAllLast TickByTickBidAsk TickByTickMidPoint '
    'HistoricalTick HistoricalTickBidAsk HistoricalTickLast '
    'MktDepthData DOMLevel BracketOrder TradeLogEntry ScanData TagValue '
    'PortfolioItem Position Fill OptionComputation OptionChain Dividends '
    'NewsArticle HistoricalNews NewsTick NewsBulletin ConnectionStats '
    'OrderCondition ExecutionCondition OperatorCondition MarginCondition '
    'ContractCondition TimeCondition PriceCondition PercentChangeCondition '
    'VolumeCondition'
    ).split()

nan = float('nan')


class Object:
    """
    Base object, with:
    
    * __slots__ to avoid typos;
    * A general constructor;
    * A general string representation;
    * A default equality testing that compares attributes.
    """
    __slots__ = ()
    defaults = {}

    def __init__(self, *args, **kwargs):
        """
        Attribute values can be given positionally or as keyword.
        If an attribute is not given it will take its value from the
        'defaults' class member. If an attribute is given both positionally
        and as keyword, the keyword wins.
        """
        defaults = self.__class__.defaults
        d = {**defaults, **dict(zip(defaults, args)), **kwargs}
        for k, v in d.items():
            setattr(self, k, v)

    def __repr__(self):
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in self.nonDefaults().items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__

    def __eq__(self, other):
        return isinstance(other, Object) and self.dict() == other.dict()

    def tuple(self):
        """
        Return values as a tuple.
        """
        return tuple(getattr(self, k) for k in self.__class__.defaults)

    def dict(self):
        """
        Return key-value pairs as a dictionary.
        """
        return {k: getattr(self, k) for k in self.__class__.defaults}

    def update(self, **kwargs):
        """
        Update key values.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def diff(self, other):
        """
        Return differences between self and other as dictionary of 2-tuples.
        """
        diff = {}
        for k in self.__class__.defaults:
            l = getattr(self, k)
            r = getattr(other, k)
            if l != r:
                diff[k] = (l, r)
        return diff

    def nonDefaults(self):
        """
        Get a dictionary of all attributes that differ from the default.
        """
        nonDefaults = {}
        for k, d in self.__class__.defaults.items():
            v = getattr(self, k)
            if v != d and (v == v or d == d):  # tests for NaN too
                nonDefaults[k] = v
        return nonDefaults


class DynamicObject:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{clsName}({kwargs})'


class ContractDetails(Object):
    defaults = ibapi.contract.ContractDetails().__dict__
    defaults['summary'] = None
    defaults.pop('contract', None)
    __slots__ = list(defaults.keys()) + \
            ['secIdListCount']  # bug in ibapi decoder

    # summary is renamed to contract in ibapi v9.73.07
    @property
    def contract(self):
        return self.summary

    @contract.setter
    def contract(self, c):
        self.summary = c


class ContractDescription(Object):
    defaults = ibapi.contract.ContractDescription().__dict__
    defaults['contract'] = None
    __slots__ = defaults.keys()


class ComboLeg(Object):
    defaults = ibapi.contract.ComboLeg().__dict__
    __slots__ = defaults.keys()


class UnderComp(Object):
    defaults = dict(
       conId=0,
       delta=0.0,
       price=0.0)
    __slots__ = defaults.keys()
# UnderComp is renamed to DeltaNeutralContract in ibapi v9.73.07
DeltaNeutralContract = UnderComp


class OrderComboLeg(Object):
    defaults = ibapi.order.OrderComboLeg().__dict__
    __slots__ = defaults.keys()


class OrderState(Object):
    defaults = ibapi.order_state.OrderState().__dict__
    __slots__ = defaults.keys()


class ScannerSubscription(Object):
    defaults = ibapi.scanner.ScannerSubscription().__dict__
    __slots__ = defaults.keys()


class SoftDollarTier(Object):
    defaults = ibapi.softdollartier.SoftDollarTier().__dict__
    __slots__ = defaults.keys()


class Execution(Object):
    defaults = ibapi.execution.Execution().__dict__
    __slots__ = defaults.keys()


class CommissionReport(Object):
    defaults = ibapi.commission_report.CommissionReport().__dict__
    __slots__ = defaults.keys()


class ExecutionFilter(Object):
    defaults = ibapi.execution.ExecutionFilter().__dict__
    __slots__ = defaults.keys()


class BarData(Object):
    defaults = ibapi.common.BarData().__dict__
    __slots__ = defaults.keys()


class RealTimeBar(Object):
    defaults = ibapi.common.RealTimeBar().__dict__
    __slots__ = defaults.keys()


class TickAttrib(Object):
    defaults = ibapi.common.TickAttrib().__dict__
    __slots__ = defaults.keys()


class HistogramData(Object):
    defaults = ibapi.common.HistogramData().__dict__
    __slots__ = defaults.keys()


class NewsProvider(Object):
    defaults = ibapi.common.NewsProvider().__dict__
    __slots__ = defaults.keys()


class DepthMktDataDescription(Object):
    defaults = ibapi.common.DepthMktDataDescription().__dict__
    __slots__ = defaults.keys()


class PnL(Object):
    defaults = dict(
        account='',
        modelCode='',
        dailyPnL=nan,
        unrealizedPnL=nan,
        realizedPnL=nan)
    __slots__ = defaults.keys()


class PnLSingle(Object):
    defaults = dict(
        account='',
        modelCode='',
        conId=0,
        dailyPnL=nan,
        unrealizedPnL=nan,
        realizedPnL=nan,
        position=0,
        value=nan)
    __slots__ = defaults.keys()


class BarList(list):
    """
    Events:
        * ``updateEvent(bars, hasNewBar)``
    """
    events = ('updateEvent',)
    
    __slots__ = events

    def __init__(self, *args):
        list.__init__(self, *args)
        Event.init(self, BarList.events)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class BarDataList(BarList):
    __slots__ = ('reqId', 'contract', 'endDateTime', 'durationStr',
            'barSizeSetting', 'whatToShow', 'useRTH', 'formatDate',
            'keepUpToDate', 'chartOptions')


class RealTimeBarList(BarList):
    __slots__ = ('reqId', 'contract', 'barSize', 'whatToShow', 'useRTH',
            'realTimeBarsOptions')


AccountValue = namedtuple('AccountValue',
    'account tag value currency modelCode')

TickData = namedtuple('TickData',
    'time tickType price size')

HistoricalTick = namedtuple('HistoricalTick',
    'time price size')

HistoricalTickBidAsk = namedtuple('HistoricalTickBidAsk',
    'time mask priceBid priceAsk sizeBid sizeAsk')

HistoricalTickLast = namedtuple('HistoricalTickLast',
    'time mask price size exchange specialConditions')

TickByTickAllLast = namedtuple('TickByTickAllLast',
    'tickType time price size attribs exchange specialConditions')

TickByTickBidAsk = namedtuple('TickByTickBidAsk',
    'time bidPrice askPrice bidSize askSize attribs')

TickByTickMidPoint = namedtuple('TickByTickMidPoint',
    'time midPoint')

MktDepthData = namedtuple('MktDepthData',
    'time position marketMaker operation side price size')

DOMLevel = namedtuple('DOMLevel',
    'price size marketMaker')

BracketOrder = namedtuple('BracketOrder',
    'parent takeProfit stopLoss')

TradeLogEntry = namedtuple('TradeLogEntry',
    'time status message')

ScanData = namedtuple('ScanData',
    'rank contractDetails distance benchmark projection legsStr')

TagValue = namedtuple('TagValue',
    'tag value')

PortfolioItem = namedtuple('PortfolioItem', (
    'contract position marketPrice marketValue averageCost '
    'unrealizedPNL realizedPNL account'))

Position = namedtuple('Position',
    'account contract position avgCost')

Fill = namedtuple('Fill',
    'contract execution commissionReport time')

OptionComputation = namedtuple('OptionComputation',
    'impliedVol delta optPrice pvDividend gamma vega theta undPrice')

OptionChain = namedtuple('OptionChain',
    'exchange underlyingConId tradingClass multiplier expirations strikes')

Dividends = namedtuple('Dividends',
    'past12Months next12Months nextDate nextAmount')

NewsArticle = namedtuple('NewsArticle',
    'articleType articleText')

HistoricalNews = namedtuple('HistoricalNews',
    'time providerCode articleId headline')

NewsTick = namedtuple('NewsTick',
    'timeStamp providerCode articleId headline extraData')

NewsBulletin = namedtuple('NewsBulletin',
    'msgId msgType message origExchange')

ConnectionStats = namedtuple('ConnectionStats',
    'startTime duration numBytesRecv numBytesSent numMsgRecv numMsgSent')
