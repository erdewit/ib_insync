from collections import namedtuple

from .util import UNSET_DOUBLE, UNSET_INTEGER

from eventkit import Event

__all__ = (
    'Object ContractDetails ContractDescription '
    'ComboLeg DeltaNeutralContract OrderComboLeg OrderState '
    'SoftDollarTier PriceIncrement Execution CommissionReport '
    'BarList BarDataList RealTimeBarList BarData RealTimeBar '
    'HistogramData NewsProvider DepthMktDataDescription '
    'ScannerSubscription ScanData ScanDataList FundamentalRatios '
    'ExecutionFilter PnL PnLSingle AccountValue TickData '
    'TickByTickAllLast TickByTickBidAsk TickByTickMidPoint '
    'HistoricalTick HistoricalTickBidAsk HistoricalTickLast '
    'TickAttrib TickAttribBidAsk TickAttribLast '
    'MktDepthData DOMLevel BracketOrder TradeLogEntry TagValue '
    'FamilyCode SmartComponent '
    'PortfolioItem Position Fill OptionComputation OptionChain Dividends '
    'NewsArticle HistoricalNews NewsTick NewsBulletin ConnectionStats'
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
    __slots__ = ('__weakref__',)
    defaults: dict = {}

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
        clsName = self.__class__.__qualname__
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
            left = getattr(self, k)
            right = getattr(other, k)
            if left != right:
                diff[k] = (left, right)
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
    defaults = dict(
        contract=None,
        marketName='',
        minTick=0.0,
        orderTypes='',
        validExchanges='',
        priceMagnifier=0,
        underConId=0,
        longName='',
        contractMonth='',
        industry='',
        category='',
        subcategory='',
        timeZoneId='',
        tradingHours='',
        liquidHours='',
        evRule='',
        evMultiplier=0,
        mdSizeMultiplier=0,
        aggGroup=0,
        underSymbol='',
        underSecType='',
        marketRuleIds='',
        secIdList=None,
        realExpirationDate='',
        lastTradeTime='',
        cusip='',
        ratings='',
        descAppend='',
        bondType='',
        couponType='',
        callable=False,
        putable=False,
        coupon=0,
        convertible=False,
        maturity='',
        issueDate='',
        nextOptionDate='',
        nextOptionType='',
        nextOptionPartial=False,
        notes='')
    __slots__ = defaults.keys()


class ContractDescription(Object):
    defaults = dict(
        contract=None,
        derivativeSecTypes=None
    )
    __slots__ = defaults.keys()


class ComboLeg(Object):
    defaults = dict(
        conId=0,
        ratio=0,
        action='',
        exchange='',
        openClose=0,
        shortSaleSlot=0,
        designatedLocation='',
        exemptCode=-1
        )
    __slots__ = defaults.keys()


class DeltaNeutralContract(Object):
    defaults = dict(
        conId=0,
        delta=0.0,
        price=0.0)
    __slots__ = defaults.keys()


class OrderComboLeg(Object):
    defaults = dict(
        price=UNSET_DOUBLE)
    __slots__ = defaults.keys()


class OrderState(Object):
    defaults = dict(
        status='',
        initMarginBefore='',
        maintMarginBefore='',
        equityWithLoanBefore='',
        initMarginChange='',
        maintMarginChange='',
        equityWithLoanChange='',
        initMarginAfter='',
        maintMarginAfter='',
        equityWithLoanAfter='',
        commission=UNSET_DOUBLE,
        minCommission=UNSET_DOUBLE,
        maxCommission=UNSET_DOUBLE,
        commissionCurrency='',
        warningText='',
        completedTime='',
        completedStatus='')
    __slots__ = defaults.keys()


class ScannerSubscription(Object):
    defaults = dict(
        numberOfRows=-1,
        instrument='',
        locationCode='',
        scanCode='',
        abovePrice=UNSET_DOUBLE,
        belowPrice=UNSET_DOUBLE,
        aboveVolume=UNSET_INTEGER,
        marketCapAbove=UNSET_DOUBLE,
        marketCapBelow=UNSET_DOUBLE,
        moodyRatingAbove='',
        moodyRatingBelow='',
        spRatingAbove='',
        spRatingBelow='',
        maturityDateAbove='',
        maturityDateBelow='',
        couponRateAbove=UNSET_DOUBLE,
        couponRateBelow=UNSET_DOUBLE,
        excludeConvertible=False,
        averageOptionVolumeAbove=UNSET_INTEGER,
        scannerSettingPairs='',
        stockTypeFilter='')
    __slots__ = defaults.keys()


class SoftDollarTier(Object):
    defaults = dict(
        name='',
        val='',
        displayName='')
    __slots__ = defaults.keys()


class Execution(Object):
    defaults = dict(
        execId='',
        time='',
        acctNumber='',
        exchange='',
        side='',
        shares=0.0,
        price=0.0,
        permId=0,
        clientId=0,
        orderId=0,
        liquidation=0,
        cumQty=0.0,
        avgPrice=0.0,
        orderRef='',
        evRule='',
        evMultiplier=0.0,
        modelCode='',
        lastLiquidity=0)
    __slots__ = defaults.keys()


class CommissionReport(Object):
    defaults = dict(
        execId='',
        commission=0.0,
        currency='',
        realizedPNL=0.0,
        yield_=0.0,
        yieldRedemptionDate=0)
    __slots__ = defaults.keys()


class ExecutionFilter(Object):
    defaults = dict(
        clientId=0,
        acctCode='',
        time='',
        symbol='',
        secType='',
        exchange='',
        side='')
    __slots__ = defaults.keys()


class BarData(Object):
    defaults = dict(
        date='',
        open=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        volume=0,
        average=0.0,
        barCount=0)
    __slots__ = defaults.keys()


class RealTimeBar(Object):
    defaults = dict(
        time=0,
        endTime=-1,
        open_=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        volume=0.0,
        wap=0.0,
        count=0)
    __slots__ = defaults.keys()


class TickAttrib(Object):
    defaults = dict(
        canAutoExecute=False,
        pastLimit=False,
        preOpen=False)
    __slots__ = defaults.keys()


class TickAttribBidAsk(Object):
    defaults = dict(
        bidPastLow=False,
        askPastHigh=False)
    __slots__ = defaults.keys()


class TickAttribLast(Object):
    defaults = dict(
        pastLimit=False,
        unreported=False)
    __slots__ = defaults.keys()


class HistogramData(Object):
    defaults = dict(
        price=0.0,
        count=0)
    __slots__ = defaults.keys()


class NewsProvider(Object):
    defaults = dict(
        code='',
        name='')
    __slots__ = defaults.keys()


class DepthMktDataDescription(Object):
    defaults = dict(
        exchange='',
        secType='',
        listingExch='',
        serviceDataType='',
        aggGroup=UNSET_INTEGER)
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


class FundamentalRatios(DynamicObject):
    """
    https://interactivebrokers.github.io/tws-api/fundamental_ratios_tags.html
    """
    pass


class BarList(list):
    """
    Base class for bar lists.
    """
    events = ('updateEvent',)

    __slots__ = events + ('__weakref__',)

    def __init__(self, *args):
        list.__init__(self, *args)
        Event.init(self, BarList.events)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class BarDataList(BarList):
    """
    List of :class:`.BarData` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.BarDataList`, hasNewBar: bool)
    """
    __slots__ = (
        'reqId', 'contract', 'endDateTime', 'durationStr',
        'barSizeSetting', 'whatToShow', 'useRTH', 'formatDate',
        'keepUpToDate', 'chartOptions')


class RealTimeBarList(BarList):
    """
    List of :class:`.RealTimeBar` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.RealTimeBarList`, hasNewBar: bool)
    """
    __slots__ = (
        'reqId', 'contract', 'barSize', 'whatToShow', 'useRTH',
        'realTimeBarsOptions')


class ScanDataList(list):
    """
    List of :class:`.ScanData` that also stores all request parameters.

    Events:
        * ``updateEvent`` (:class:`.ScanDataList`)
    """
    events = ('updateEvent',)

    __slots__ = events + (
        'reqId', 'subscription', 'scannerSubscriptionOptions',
        'scannerSubscriptionFilterOptions', '__weakref__')

    def __init__(self, *args):
        list.__init__(self, *args)
        Event.init(self, ScanDataList.events)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


TagValue = namedtuple(
    'TagValue',
    'tag value')

AccountValue = namedtuple(
    'AccountValue',
    'account tag value currency modelCode')

TickData = namedtuple(
    'TickData',
    'time tickType price size')

HistoricalTick = namedtuple(
    'HistoricalTick',
    'time price size')

HistoricalTickBidAsk = namedtuple(
    'HistoricalTickBidAsk',
    'time tickAttribBidAsk priceBid priceAsk sizeBid sizeAsk')

HistoricalTickLast = namedtuple(
    'HistoricalTickLast',
    'time tickAttribLast price size exchange specialConditions')

TickByTickAllLast = namedtuple(
    'TickByTickAllLast',
    'tickType time price size tickAttribLast exchange specialConditions')

TickByTickBidAsk = namedtuple(
    'TickByTickBidAsk',
    'time bidPrice askPrice bidSize askSize tickAttribBidAsk')

TickByTickMidPoint = namedtuple(
    'TickByTickMidPoint',
    'time midPoint')

MktDepthData = namedtuple(
    'MktDepthData',
    'time position marketMaker operation side price size')

DOMLevel = namedtuple(
    'DOMLevel',
    'price size marketMaker')

BracketOrder = namedtuple(
    'BracketOrder',
    'parent takeProfit stopLoss')

TradeLogEntry = namedtuple(
    'TradeLogEntry',
    'time status message')

PriceIncrement = namedtuple(
    'PriceIncrement',
    'lowEdge increment')

ScanData = namedtuple(
    'ScanData',
    'rank contractDetails distance benchmark projection legsStr')

PortfolioItem = namedtuple(
    'PortfolioItem',
    'contract position marketPrice marketValue averageCost '
    'unrealizedPNL realizedPNL account')

Position = namedtuple(
    'Position',
    'account contract position avgCost')

Fill = namedtuple(
    'Fill',
    'contract execution commissionReport time')

OptionComputation = namedtuple(
    'OptionComputation',
    'impliedVol delta optPrice pvDividend gamma vega theta undPrice')

OptionChain = namedtuple(
    'OptionChain',
    'exchange underlyingConId tradingClass multiplier expirations strikes')

Dividends = namedtuple(
    'Dividends',
    'past12Months next12Months nextDate nextAmount')

NewsArticle = namedtuple(
    'NewsArticle',
    'articleType articleText')

HistoricalNews = namedtuple(
    'HistoricalNews',
    'time providerCode articleId headline')

NewsTick = namedtuple(
    'NewsTick',
    'timeStamp providerCode articleId headline extraData')

NewsBulletin = namedtuple(
    'NewsBulletin',
    'msgId msgType message origExchange')

FamilyCode = namedtuple(
    'FamilyCode',
    'accountID familyCodeStr')

SmartComponent = namedtuple(
    'SmartComponent',
    'bitNumber exchange exchangeLetter')

ConnectionStats = namedtuple(
    'ConnectionStats',
    'startTime duration numBytesRecv numBytesSent numMsgRecv numMsgSent')
