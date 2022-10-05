"""Order types used by Interactive Brokers."""

from dataclasses import dataclass, field
from typing import ClassVar, List, NamedTuple, Set

from eventkit import Event

from .contract import Contract, TagValue
from .objects import Fill, SoftDollarTier, TradeLogEntry
from .util import UNSET_DOUBLE, UNSET_INTEGER, dataclassNonDefaults


@dataclass
class Order:
    """
    Order for trading contracts.

    https://interactivebrokers.github.io/tws-api/available_orders.html
    """

    orderId: int = 0
    clientId: int = 0
    permId: int = 0
    action: str = ''
    totalQuantity: float = 0.0
    orderType: str = ''
    lmtPrice: float = UNSET_DOUBLE
    auxPrice: float = UNSET_DOUBLE
    tif: str = ''
    activeStartTime: str = ''
    activeStopTime: str = ''
    ocaGroup: str = ''
    ocaType: int = 0
    orderRef: str = ''
    transmit: bool = True
    parentId: int = 0
    blockOrder: bool = False
    sweepToFill: bool = False
    displaySize: int = 0
    triggerMethod: int = 0
    outsideRth: bool = False
    hidden: bool = False
    goodAfterTime: str = ''
    goodTillDate: str = ''
    rule80A: str = ''
    allOrNone: bool = False
    minQty: int = UNSET_INTEGER
    percentOffset: float = UNSET_DOUBLE
    overridePercentageConstraints: bool = False
    trailStopPrice: float = UNSET_DOUBLE
    trailingPercent: float = UNSET_DOUBLE
    faGroup: str = ''
    faProfile: str = ''
    faMethod: str = ''
    faPercentage: str = ''
    designatedLocation: str = ''
    openClose: str = "O"
    origin: int = 0
    shortSaleSlot: int = 0
    exemptCode: int = -1
    discretionaryAmt: float = 0.0
    eTradeOnly: bool = False
    firmQuoteOnly: bool = False
    nbboPriceCap: float = UNSET_DOUBLE
    optOutSmartRouting: bool = False
    auctionStrategy: int = 0
    startingPrice: float = UNSET_DOUBLE
    stockRefPrice: float = UNSET_DOUBLE
    delta: float = UNSET_DOUBLE
    stockRangeLower: float = UNSET_DOUBLE
    stockRangeUpper: float = UNSET_DOUBLE
    randomizePrice: bool = False
    randomizeSize: bool = False
    volatility: float = UNSET_DOUBLE
    volatilityType: int = UNSET_INTEGER
    deltaNeutralOrderType: str = ''
    deltaNeutralAuxPrice: float = UNSET_DOUBLE
    deltaNeutralConId: int = 0
    deltaNeutralSettlingFirm: str = ''
    deltaNeutralClearingAccount: str = ''
    deltaNeutralClearingIntent: str = ''
    deltaNeutralOpenClose: str = ''
    deltaNeutralShortSale: bool = False
    deltaNeutralShortSaleSlot: int = 0
    deltaNeutralDesignatedLocation: str = ''
    continuousUpdate: bool = False
    referencePriceType: int = UNSET_INTEGER
    basisPoints: float = UNSET_DOUBLE
    basisPointsType: int = UNSET_INTEGER
    scaleInitLevelSize: int = UNSET_INTEGER
    scaleSubsLevelSize: int = UNSET_INTEGER
    scalePriceIncrement: float = UNSET_DOUBLE
    scalePriceAdjustValue: float = UNSET_DOUBLE
    scalePriceAdjustInterval: int = UNSET_INTEGER
    scaleProfitOffset: float = UNSET_DOUBLE
    scaleAutoReset: bool = False
    scaleInitPosition: int = UNSET_INTEGER
    scaleInitFillQty: int = UNSET_INTEGER
    scaleRandomPercent: bool = False
    scaleTable: str = ''
    hedgeType: str = ''
    hedgeParam: str = ''
    account: str = ''
    settlingFirm: str = ''
    clearingAccount: str = ''
    clearingIntent: str = ''
    algoStrategy: str = ''
    algoParams: List[TagValue] = field(default_factory=list)
    smartComboRoutingParams: List[TagValue] = field(default_factory=list)
    algoId: str = ''
    whatIf: bool = False
    notHeld: bool = False
    solicited: bool = False
    modelCode: str = ''
    orderComboLegs: List['OrderComboLeg'] = field(default_factory=list)
    orderMiscOptions: List[TagValue] = field(default_factory=list)
    referenceContractId: int = 0
    peggedChangeAmount: float = 0.0
    isPeggedChangeAmountDecrease: bool = False
    referenceChangeAmount: float = 0.0
    referenceExchangeId: str = ''
    adjustedOrderType: str = ''
    triggerPrice: float = UNSET_DOUBLE
    adjustedStopPrice: float = UNSET_DOUBLE
    adjustedStopLimitPrice: float = UNSET_DOUBLE
    adjustedTrailingAmount: float = UNSET_DOUBLE
    adjustableTrailingUnit: int = 0
    lmtPriceOffset: float = UNSET_DOUBLE
    conditions: List['OrderCondition'] = field(default_factory=list)
    conditionsCancelOrder: bool = False
    conditionsIgnoreRth: bool = False
    extOperator: str = ''
    softDollarTier: SoftDollarTier = field(default_factory=SoftDollarTier)
    cashQty: float = UNSET_DOUBLE
    mifid2DecisionMaker: str = ''
    mifid2DecisionAlgo: str = ''
    mifid2ExecutionTrader: str = ''
    mifid2ExecutionAlgo: str = ''
    dontUseAutoPriceForHedge: bool = False
    isOmsContainer: bool = False
    discretionaryUpToLimitPrice: bool = False
    autoCancelDate: str = ''
    filledQuantity: float = UNSET_DOUBLE
    refFuturesConId: int = 0
    autoCancelParent: bool = False
    shareholder: str = ''
    imbalanceOnly: bool = False
    routeMarketableToBbo: bool = False
    parentPermId: int = 0
    usePriceMgmtAlgo: bool = False
    duration: int = UNSET_INTEGER
    postToAts: int = UNSET_INTEGER
    advancedErrorOverride: str = ''
    manualOrderTime: str = ''
    minTradeQty: int = UNSET_INTEGER
    minCompeteSize: int = UNSET_INTEGER
    competeAgainstBestOffset: float = UNSET_DOUBLE
    midOffsetAtWhole: float = UNSET_DOUBLE
    midOffsetAtHalf: float = UNSET_DOUBLE

    def __repr__(self):
        attrs = dataclassNonDefaults(self)
        if self.__class__ is not Order:
            attrs.pop('orderType', None)
        if not self.softDollarTier:
            attrs.pop('softDollarTier')
        clsName = self.__class__.__qualname__
        kwargs = ', '.join(
            f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class LimitOrder(Order):

    def __init__(self, action: str, totalQuantity: float, lmtPrice: float,
                 **kwargs):
        Order.__init__(
            self, orderType='LMT', action=action,
            totalQuantity=totalQuantity, lmtPrice=lmtPrice, **kwargs)


class MarketOrder(Order):

    def __init__(self, action: str, totalQuantity: float, **kwargs):
        Order.__init__(
            self, orderType='MKT', action=action,
            totalQuantity=totalQuantity, **kwargs)


class StopOrder(Order):

    def __init__(self, action: str, totalQuantity: float, stopPrice: float,
                 **kwargs):
        Order.__init__(
            self, orderType='STP', action=action,
            totalQuantity=totalQuantity, auxPrice=stopPrice, **kwargs)


class StopLimitOrder(Order):

    def __init__(self, action: str, totalQuantity: float, lmtPrice: float,
                 stopPrice: float, **kwargs):
        Order.__init__(
            self, orderType='STP LMT', action=action,
            totalQuantity=totalQuantity, lmtPrice=lmtPrice,
            auxPrice=stopPrice, **kwargs)


@dataclass
class OrderStatus:
    orderId: int = 0
    status: str = ''
    filled: float = 0.0
    remaining: float = 0.0
    avgFillPrice: float = 0.0
    permId: int = 0
    parentId: int = 0
    lastFillPrice: float = 0.0
    clientId: int = 0
    whyHeld: str = ''
    mktCapPrice: float = 0.0

    PendingSubmit: ClassVar[str] = 'PendingSubmit'
    PendingCancel: ClassVar[str] = 'PendingCancel'
    PreSubmitted: ClassVar[str] = 'PreSubmitted'
    Submitted: ClassVar[str] = 'Submitted'
    ApiPending: ClassVar[str] = 'ApiPending'
    ApiCancelled: ClassVar[str] = 'ApiCancelled'
    Cancelled: ClassVar[str] = 'Cancelled'
    Filled: ClassVar[str] = 'Filled'
    Inactive: ClassVar[str] = 'Inactive'

    DoneStates: ClassVar[Set[str]] = {'Filled', 'Cancelled', 'ApiCancelled'}
    ActiveStates: ClassVar[Set[str]] = {
        'PendingSubmit', 'ApiPending', 'PreSubmitted', 'Submitted'}


@dataclass
class OrderState:
    status: str = ''
    initMarginBefore: str = ''
    maintMarginBefore: str = ''
    equityWithLoanBefore: str = ''
    initMarginChange: str = ''
    maintMarginChange: str = ''
    equityWithLoanChange: str = ''
    initMarginAfter: str = ''
    maintMarginAfter: str = ''
    equityWithLoanAfter: str = ''
    commission: float = UNSET_DOUBLE
    minCommission: float = UNSET_DOUBLE
    maxCommission: float = UNSET_DOUBLE
    commissionCurrency: str = ''
    warningText: str = ''
    completedTime: str = ''
    completedStatus: str = ''


@dataclass
class OrderComboLeg:
    price: float = UNSET_DOUBLE


@dataclass
class Trade:
    """
    Trade keeps track of an order, its status and all its fills.

    Events:
        * ``statusEvent`` (trade: :class:`.Trade`)
        * ``modifyEvent`` (trade: :class:`.Trade`)
        * ``fillEvent`` (trade: :class:`.Trade`, fill: :class:`.Fill`)
        * ``commissionReportEvent`` (trade: :class:`.Trade`,
          fill: :class:`.Fill`, commissionReport: :class:`.CommissionReport`)
        * ``filledEvent`` (trade: :class:`.Trade`)
        * ``cancelEvent`` (trade: :class:`.Trade`)
        * ``cancelledEvent`` (trade: :class:`.Trade`)
    """

    events: ClassVar = (
        'statusEvent', 'modifyEvent', 'fillEvent',
        'commissionReportEvent', 'filledEvent',
        'cancelEvent', 'cancelledEvent')

    contract: Contract = field(default_factory=Contract)
    order: Order = field(default_factory=Order)
    orderStatus: 'OrderStatus' = field(default_factory=OrderStatus)
    fills: List[Fill] = field(default_factory=list)
    log: List[TradeLogEntry] = field(default_factory=list)
    advancedError: str = ''

    def __post_init__(self):
        self.statusEvent = Event('statusEvent')
        self.modifyEvent = Event('modifyEvent')
        self.fillEvent = Event('fillEvent')
        self.commissionReportEvent = Event('commissionReportEvent')
        self.filledEvent = Event('filledEvent')
        self.cancelEvent = Event('cancelEvent')
        self.cancelledEvent = Event('cancelledEvent')

    def isActive(self):
        """True if eligible for execution, false otherwise."""
        return self.orderStatus.status in OrderStatus.ActiveStates

    def isDone(self):
        """True if completely filled or cancelled, false otherwise."""
        return self.orderStatus.status in OrderStatus.DoneStates

    def filled(self):
        """Number of shares filled."""
        fills = self.fills
        if self.contract.secType == 'BAG':
            # don't count fills for the leg contracts
            fills = [f for f in fills if f.contract.secType == 'BAG']
        return sum(f.execution.shares for f in fills)

    def remaining(self):
        """Number of shares remaining to be filled."""
        return self.order.totalQuantity - self.filled()


class BracketOrder(NamedTuple):
    parent: Order
    takeProfit: Order
    stopLoss: Order


@dataclass
class OrderCondition:

    @staticmethod
    def createClass(condType):
        d = {
            1: PriceCondition,
            3: TimeCondition,
            4: MarginCondition,
            5: ExecutionCondition,
            6: VolumeCondition,
            7: PercentChangeCondition}
        return d[condType]

    def And(self):
        self.conjunction = 'a'
        return self

    def Or(self):
        self.conjunction = 'o'
        return self


@dataclass
class PriceCondition(OrderCondition):
    condType: int = 1
    conjunction: str = 'a'
    isMore: bool = True
    price: float = 0.0
    conId: int = 0
    exch: str = ''
    triggerMethod: int = 0


@dataclass
class TimeCondition(OrderCondition):
    condType: int = 3
    conjunction: str = 'a'
    isMore: bool = True
    time: str = ''


@dataclass
class MarginCondition(OrderCondition):
    condType: int = 4
    conjunction: str = 'a'
    isMore: bool = True
    percent: int = 0


@dataclass
class ExecutionCondition(OrderCondition):
    condType: int = 5
    conjunction: str = 'a'
    secType: str = ''
    exch: str = ''
    symbol: str = ''


@dataclass
class VolumeCondition(OrderCondition):
    condType: int = 6
    conjunction: str = 'a'
    isMore: bool = True
    volume: int = 0
    conId: int = 0
    exch: str = ''


@dataclass
class PercentChangeCondition(OrderCondition):
    condType: int = 7
    conjunction: str = 'a'
    isMore: bool = True
    changePercent: float = 0.0
    conId: int = 0
    exch: str = ''
