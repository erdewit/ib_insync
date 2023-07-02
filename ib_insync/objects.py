"""Object hierarchy."""

from dataclasses import dataclass, field
from datetime import date as date_, datetime
from typing import List, NamedTuple, Optional, Union

from eventkit import Event

from .contract import Contract, ScanData, TagValue
from .util import EPOCH, UNSET_DOUBLE, UNSET_INTEGER

nan = float('nan')


@dataclass
class ScannerSubscription:
    numberOfRows: int = -1
    instrument: str = ''
    locationCode: str = ''
    scanCode: str = ''
    abovePrice: float = UNSET_DOUBLE
    belowPrice: float = UNSET_DOUBLE
    aboveVolume: int = UNSET_INTEGER
    marketCapAbove: float = UNSET_DOUBLE
    marketCapBelow: float = UNSET_DOUBLE
    moodyRatingAbove: str = ''
    moodyRatingBelow: str = ''
    spRatingAbove: str = ''
    spRatingBelow: str = ''
    maturityDateAbove: str = ''
    maturityDateBelow: str = ''
    couponRateAbove: float = UNSET_DOUBLE
    couponRateBelow: float = UNSET_DOUBLE
    excludeConvertible: bool = False
    averageOptionVolumeAbove: int = UNSET_INTEGER
    scannerSettingPairs: str = ''
    stockTypeFilter: str = ''


@dataclass
class SoftDollarTier:
    name: str = ''
    val: str = ''
    displayName: str = ''

    def __bool__(self):
        return bool(self.name or self.val or self.displayName)


@dataclass
class Execution:
    execId: str = ''
    time: datetime = field(default=EPOCH)
    acctNumber: str = ''
    exchange: str = ''
    side: str = ''
    shares: float = 0.0
    price: float = 0.0
    permId: int = 0
    clientId: int = 0
    orderId: int = 0
    liquidation: int = 0
    cumQty: float = 0.0
    avgPrice: float = 0.0
    orderRef: str = ''
    evRule: str = ''
    evMultiplier: float = 0.0
    modelCode: str = ''
    lastLiquidity: int = 0


@dataclass
class CommissionReport:
    execId: str = ''
    commission: float = 0.0
    currency: str = ''
    realizedPNL: float = 0.0
    yield_: float = 0.0
    yieldRedemptionDate: int = 0


@dataclass
class ExecutionFilter:
    clientId: int = 0
    acctCode: str = ''
    time: str = ''
    symbol: str = ''
    secType: str = ''
    exchange: str = ''
    side: str = ''


@dataclass
class BarData:
    date: Union[date_, datetime] = EPOCH
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0
    average: float = 0.0
    barCount: int = 0


@dataclass
class RealTimeBar:
    time: datetime = EPOCH
    endTime: int = -1
    open_: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    wap: float = 0.0
    count: int = 0


@dataclass
class TickAttrib:
    canAutoExecute: bool = False
    pastLimit: bool = False
    preOpen: bool = False


@dataclass
class TickAttribBidAsk:
    bidPastLow: bool = False
    askPastHigh: bool = False


@dataclass
class TickAttribLast:
    pastLimit: bool = False
    unreported: bool = False


@dataclass
class HistogramData:
    price: float = 0.0
    count: int = 0


@dataclass
class NewsProvider:
    code: str = ''
    name: str = ''


@dataclass
class DepthMktDataDescription:
    exchange: str = ''
    secType: str = ''
    listingExch: str = ''
    serviceDataType: str = ''
    aggGroup: int = UNSET_INTEGER


@dataclass
class PnL:
    account: str = ''
    modelCode: str = ''
    dailyPnL: float = nan
    unrealizedPnL: float = nan
    realizedPnL: float = nan


@dataclass
class TradeLogEntry:
    time: datetime
    status: str = ''
    message: str = ''
    errorCode: int = 0


@dataclass
class PnLSingle:
    account: str = ''
    modelCode: str = ''
    conId: int = 0
    dailyPnL: float = nan
    unrealizedPnL: float = nan
    realizedPnL: float = nan
    position: int = 0
    value: float = nan


@dataclass
class HistoricalSession:
    startDateTime: str = ''
    endDateTime: str = ''
    refDate: str = ''


@dataclass
class HistoricalSchedule:
    startDateTime: str = ''
    endDateTime: str = ''
    timeZone: str = ''
    sessions: List[HistoricalSession] = field(default_factory=list)


@dataclass
class WshEventData:
    conId: int = UNSET_INTEGER
    filter: str = ''
    fillWatchlist: bool = False
    fillPortfolio: bool = False
    fillCompetitors: bool = False
    startDate: str = ''
    endDate: str = ''
    totalLimit: int = UNSET_INTEGER


class AccountValue(NamedTuple):
    account: str
    tag: str
    value: str
    currency: str
    modelCode: str


class TickData(NamedTuple):
    time: datetime
    tickType: int
    price: float
    size: float


class HistoricalTick(NamedTuple):
    time: datetime
    price: float
    size: float


class HistoricalTickBidAsk(NamedTuple):
    time: datetime
    tickAttribBidAsk: TickAttribBidAsk
    priceBid: float
    priceAsk: float
    sizeBid: float
    sizeAsk: float


class HistoricalTickLast(NamedTuple):
    time: datetime
    tickAttribLast: TickAttribLast
    price: float
    size: float
    exchange: str
    specialConditions: str


class TickByTickAllLast(NamedTuple):
    tickType: int
    time: datetime
    price: float
    size: float
    tickAttribLast: TickAttribLast
    exchange: str
    specialConditions: str


class TickByTickBidAsk(NamedTuple):
    time: datetime
    bidPrice: float
    askPrice: float
    bidSize: float
    askSize: float
    tickAttribBidAsk: TickAttribBidAsk


class TickByTickMidPoint(NamedTuple):
    time: datetime
    midPoint: float


class MktDepthData(NamedTuple):
    time: datetime
    position: int
    marketMaker: str
    operation: int
    side: int
    price: float
    size: float


class DOMLevel(NamedTuple):
    price: float
    size: float
    marketMaker: str


class PriceIncrement(NamedTuple):
    lowEdge: float
    increment: float


class PortfolioItem(NamedTuple):
    contract: Contract
    position: float
    marketPrice: float
    marketValue: float
    averageCost: float
    unrealizedPNL: float
    realizedPNL: float
    account: str


class Position(NamedTuple):
    account: str
    contract: Contract
    position: float
    avgCost: float


class Fill(NamedTuple):
    contract: Contract
    execution: Execution
    commissionReport: CommissionReport
    time: datetime


class OptionComputation(NamedTuple):
    tickAttrib: int
    impliedVol: Optional[float]
    delta: Optional[float]
    optPrice: Optional[float]
    pvDividend: Optional[float]
    gamma: Optional[float]
    vega: Optional[float]
    theta: Optional[float]
    undPrice: Optional[float]


class OptionChain(NamedTuple):
    exchange: str
    underlyingConId: int
    tradingClass: str
    multiplier: str
    expirations: List[str]
    strikes: List[float]


class Dividends(NamedTuple):
    past12Months: Optional[float]
    next12Months: Optional[float]
    nextDate: Optional[date_]
    nextAmount: Optional[float]


class NewsArticle(NamedTuple):
    articleType: int
    articleText: str


class HistoricalNews(NamedTuple):
    time: datetime
    providerCode: str
    articleId: str
    headline: str


class NewsTick(NamedTuple):
    timeStamp: int
    providerCode: str
    articleId: str
    headline: str
    extraData: str


class NewsBulletin(NamedTuple):
    msgId: int
    msgType: int
    message: str
    origExchange: str


class FamilyCode(NamedTuple):
    accountID: str
    familyCodeStr: str


class SmartComponent(NamedTuple):
    bitNumber: int
    exchange: str
    exchangeLetter: str


class ConnectionStats(NamedTuple):
    startTime: float
    duration: float
    numBytesRecv: int
    numBytesSent: int
    numMsgRecv: int
    numMsgSent: int


class BarDataList(List[BarData]):
    """
    List of :class:`.BarData` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.BarDataList`, hasNewBar: bool)
    """

    reqId: int
    contract: Contract
    endDateTime: Union[datetime, date_, str, None]
    durationStr: str
    barSizeSetting: str
    whatToShow: str
    useRTH: bool
    formatDate: int
    keepUpToDate: bool
    chartOptions: List[TagValue]

    def __init__(self, *args):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class RealTimeBarList(List[RealTimeBar]):
    """
    List of :class:`.RealTimeBar` that also stores all request parameters.

    Events:

        * ``updateEvent``
          (bars: :class:`.RealTimeBarList`, hasNewBar: bool)
    """

    reqId: int
    contract: Contract
    barSize: int
    whatToShow: str
    useRTH: bool
    realTimeBarsOptions: List[TagValue]

    def __init__(self, *args):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class ScanDataList(List[ScanData]):
    """
    List of :class:`.ScanData` that also stores all request parameters.

    Events:
        * ``updateEvent`` (:class:`.ScanDataList`)
    """

    reqId: int
    subscription: ScannerSubscription
    scannerSubscriptionOptions: List[TagValue]
    scannerSubscriptionFilterOptions: List[TagValue]

    def __init__(self, *args):
        super().__init__(*args)
        self.updateEvent = Event('updateEvent')

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class DynamicObject:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{clsName}({kwargs})'


class FundamentalRatios(DynamicObject):
    """
    See:
    https://web.archive.org/web/20200725010343/https://interactivebrokers.github.io/tws-api/fundamental_ratios_tags.html
    """

    pass
