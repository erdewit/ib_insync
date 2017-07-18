from collections import namedtuple

import ibapi.scanner
import ibapi.contract
import ibapi.common
import ibapi.order
import ibapi.order_state
import ibapi.softdollartier
import ibapi.execution
import ibapi.commission_report

__all__ = (
    'Object ContractDetails ContractDescription '
    'ComboLeg UnderComp OrderComboLeg OrderState OrderStatus '
    'ScannerSubscription SoftDollarTier '
    'Execution CommissionReport ExecutionFilter '
    'BarData RealTimeBar HistogramData '
    'NewsProvider DepthMktDataDescription '
    'AccountValue RealTimeBar TickData MktDepthData BracketOrder '
    'DOMLevel Trade TradeLogEntry ScanData TagValue '
    'PortfolioItem Position Fill '
    'OptionComputation OptionChain '
    'NewsArticle HistoricalNews NewsTick NewsBulletin '
    'ConnectionStats '
    ).split()


class Object:
    """
    Base object, with:
    
    * __slots__ set to avoid typos;
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
        for k, v in self.__class__.defaults.items():
            setattr(self, k, v)
        for k, v in zip(self.__class__.defaults, args):
            setattr(self, k, v)
        for k, v in kwargs.items():
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
        Get a dicionary of all attributes that differ from the default.
        """
        nonDefaults = {}
        for k, d in self.__class__.defaults.items():
            v = getattr(self, k)
            if v != d:
                nonDefaults[k] = v
        return nonDefaults


class ContractDetails(Object):
    defaults = ibapi.contract.ContractDetails().__dict__
    defaults['summary'] = None
    __slots__ = list(defaults.keys()) + \
            ['secIdListCount']  # bug in ibapi decoder
    __init__ = Object.__init__

class ContractDescription(Object):
    defaults = ibapi.contract.ContractDescription().__dict__
    defaults['contract'] = None
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class ComboLeg(Object):
    defaults = ibapi.contract.ComboLeg().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class UnderComp(Object):
    defaults = ibapi.contract.UnderComp().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class OrderComboLeg(Object):
    defaults = ibapi.order.OrderComboLeg().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class OrderState(Object):
    defaults = ibapi.order_state.OrderState().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class OrderStatus(Object):
    defaults = {
        'orderId': 0,
        'status': '',
        'filled': 0,
        'remaining': 0,
        'avgFillPrice': 0.0,
        'permId': 0,
        'parentId': 0,
        'lastFillPrice': 0.0,
        'clientId': 0,
        'whyHeld': '' }
    __slots__ = defaults.keys()
    __init__ = Object.__init__
    OrderStates = ('PendingSubmit', 'PendingCancel', 'PreSubmitted',
            'Submitted', 'ApiCanceled', 'Cancelled', 'Filled', 'Inactive')
for k in OrderStatus.OrderStates:
    setattr(OrderStatus, k, k)
OrderStatus.ActiveStates = (OrderStatus.PendingSubmit,
        OrderStatus.PreSubmitted, OrderStatus.Submitted)

class ScannerSubscription(Object):
    defaults = ibapi.scanner.ScannerSubscription().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class SoftDollarTier(Object):
    defaults = ibapi.softdollartier.SoftDollarTier().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class Execution(Object):
    defaults = ibapi.execution.Execution().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class CommissionReport(Object):
    defaults = ibapi.commission_report.CommissionReport().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class ExecutionFilter(Object):
    defaults = ibapi.execution.ExecutionFilter().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class BarData(Object):
    defaults = ibapi.common.BarData().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class RealTimeBar(Object):
    defaults = ibapi.common.RealTimeBar().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class HistogramData(Object):
    defaults = ibapi.common.HistogramData().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class NewsProvider(Object):
    defaults = ibapi.common.NewsProvider().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__

class DepthMktDataDescription(Object):
    defaults = ibapi.common.DepthMktDataDescription().__dict__
    __slots__ = defaults.keys()
    __init__ = Object.__init__


class Trade(namedtuple('Trade', 'contract order orderStatus fills log')):
    __slots__ = ()

    def isActive(self):
        """
        Is this an ongoing trade?
        """
        return self.orderStatus.status in OrderStatus.ActiveStates

    def filled(self):
        """
        Number of shares filled.
        """
        return sum(f.execution.shares for f in self.fills)

    def remaining(self):
        """
        Number of share remaining to be filled.
        """
        return self.order.totalQuantity - self.filled()


AccountValue = namedtuple('AccountValue',
    'account tag value currency')

TickData = namedtuple('TickData',
    'time tickType price size')

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
    'tickType impliedVol delta optPrice pvDividend gamma vega theta undPrice')

OptionChain = namedtuple('OptionChain',
    'exchange underlyingConId tradingClass multiplier expirations strikes')

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

