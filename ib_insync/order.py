from eventkit import Event

from .objects import Object, SoftDollarTier
from .util import UNSET_DOUBLE, UNSET_INTEGER

__all__ = (
    'Trade OrderStatus Order '
    'LimitOrder MarketOrder StopOrder StopLimitOrder '
    'OrderCondition ExecutionCondition MarginCondition TimeCondition '
    'PriceCondition PercentChangeCondition VolumeCondition '
    ).split()


class Trade(Object):
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
    events = (
        'statusEvent', 'modifyEvent', 'fillEvent',
        'commissionReportEvent', 'filledEvent',
        'cancelEvent', 'cancelledEvent')

    defaults = dict(
        contract=None,
        order=None,
        orderStatus=None,
        fills=None,
        log=None
    )
    __slots__ = tuple(defaults.keys()) + events + ('__dict__',)

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        Event.init(self, Trade.events)

    def isActive(self):
        """
        True if eligible for execution, false otherwise.
        """
        return self.orderStatus.status in OrderStatus.ActiveStates

    def isDone(self):
        """
        True if completely filled or cancelled, false otherwise.
        """
        return self.orderStatus.status in OrderStatus.DoneStates

    def filled(self):
        """
        Number of shares filled.
        """
        return sum(f.execution.shares for f in self.fills)

    def remaining(self):
        """
        Number of shares remaining to be filled.
        """
        return self.order.totalQuantity - self.filled()


class OrderStatus(Object):
    defaults = dict(
        orderId=0,
        status='',
        filled=0,
        remaining=0,
        avgFillPrice=0.0,
        permId=0,
        parentId=0,
        lastFillPrice=0.0,
        clientId=0,
        whyHeld='',
        mktCapPrice=0.0,
        lastLiquidity=0
    )
    __slots__ = defaults.keys()

    PendingSubmit = 'PendingSubmit'
    PendingCancel = 'PendingCancel'
    PreSubmitted = 'PreSubmitted'
    Submitted = 'Submitted'
    ApiPending = 'ApiPending'
    ApiCancelled = 'ApiCancelled'
    Cancelled = 'Cancelled'
    Filled = 'Filled'
    Inactive = 'Inactive'

    DoneStates = {'Filled', 'Cancelled', 'ApiCancelled'}
    ActiveStates = {'PendingSubmit', 'ApiPending', 'PreSubmitted', 'Submitted'}


class Order(Object):
    """
    Order for trading contracts.

    https://interactivebrokers.github.io/tws-api/available_orders.html
    """
    defaults = dict(
        orderId=0,
        clientId=0,
        permId=0,
        action='',
        totalQuantity=0,
        orderType='',
        lmtPrice=UNSET_DOUBLE,
        auxPrice=UNSET_DOUBLE,
        tif='',
        activeStartTime='',
        activeStopTime='',
        ocaGroup='',
        ocaType=0,
        orderRef='',
        transmit=True,
        parentId=0,
        blockOrder=False,
        sweepToFill=False,
        displaySize=0,
        triggerMethod=0,
        outsideRth=False,
        hidden=False,
        goodAfterTime='',
        goodTillDate='',
        rule80A='',
        allOrNone=False,
        minQty=UNSET_INTEGER,
        percentOffset=UNSET_DOUBLE,
        overridePercentageConstraints=False,
        trailStopPrice=UNSET_DOUBLE,
        trailingPercent=UNSET_DOUBLE,
        faGroup='',
        faProfile='',
        faMethod='',
        faPercentage='',
        designatedLocation='',
        openClose="O",
        origin=0,
        shortSaleSlot=0,
        exemptCode=-1,
        discretionaryAmt=0,
        eTradeOnly=True,
        firmQuoteOnly=True,
        nbboPriceCap=UNSET_DOUBLE,
        optOutSmartRouting=False,
        auctionStrategy=0,
        startingPrice=UNSET_DOUBLE,
        stockRefPrice=UNSET_DOUBLE,
        delta=UNSET_DOUBLE,
        stockRangeLower=UNSET_DOUBLE,
        stockRangeUpper=UNSET_DOUBLE,
        randomizePrice=False,
        randomizeSize=False,
        volatility=UNSET_DOUBLE,
        volatilityType=UNSET_INTEGER,
        deltaNeutralOrderType='',
        deltaNeutralAuxPrice=UNSET_DOUBLE,
        deltaNeutralConId=0,
        deltaNeutralSettlingFirm='',
        deltaNeutralClearingAccount='',
        deltaNeutralClearingIntent='',
        deltaNeutralOpenClose='',
        deltaNeutralShortSale=False,
        deltaNeutralShortSaleSlot=0,
        deltaNeutralDesignatedLocation='',
        continuousUpdate=False,
        referencePriceType=UNSET_INTEGER,
        basisPoints=UNSET_DOUBLE,
        basisPointsType=UNSET_INTEGER,
        scaleInitLevelSize=UNSET_INTEGER,
        scaleSubsLevelSize=UNSET_INTEGER,
        scalePriceIncrement=UNSET_DOUBLE,
        scalePriceAdjustValue=UNSET_DOUBLE,
        scalePriceAdjustInterval=UNSET_INTEGER,
        scaleProfitOffset=UNSET_DOUBLE,
        scaleAutoReset=False,
        scaleInitPosition=UNSET_INTEGER,
        scaleInitFillQty=UNSET_INTEGER,
        scaleRandomPercent=False,
        scaleTable='',
        hedgeType='',
        hedgeParam='',
        account='',
        settlingFirm='',
        clearingAccount='',
        clearingIntent='',
        algoStrategy='',
        algoParams=None,
        smartComboRoutingParams=None,
        algoId='',
        whatIf=False,
        notHeld=False,
        solicited=False,
        modelCode='',
        orderComboLegs=None,
        orderMiscOptions=None,
        referenceContractId=0,
        peggedChangeAmount=0.0,
        isPeggedChangeAmountDecrease=False,
        referenceChangeAmount=0.0,
        referenceExchangeId='',
        adjustedOrderType='',
        triggerPrice=UNSET_DOUBLE,
        adjustedStopPrice=UNSET_DOUBLE,
        adjustedStopLimitPrice=UNSET_DOUBLE,
        adjustedTrailingAmount=UNSET_DOUBLE,
        adjustableTrailingUnit=0,
        lmtPriceOffset=UNSET_DOUBLE,
        conditions=None,
        conditionsCancelOrder=False,
        conditionsIgnoreRth=False,
        extOperator='',
        softDollarTier=None,
        cashQty=UNSET_DOUBLE,
        mifid2DecisionMaker='',
        mifid2DecisionAlgo='',
        mifid2ExecutionTrader='',
        mifid2ExecutionAlgo='',
        dontUseAutoPriceForHedge=False,
        isOmsContainer=False,
        discretionaryUpToLimitPrice=False,
        autoCancelDate='',
        filledQuantity=UNSET_DOUBLE,
        refFuturesConId=0,
        autoCancelParent=False,
        shareholder='',
        imbalanceOnly=False,
        routeMarketableToBbo=False,
        parentPermId=0,
        usePriceMgmtAlgo=False)
    __slots__ = defaults.keys()

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        if not self.conditions:
            self.conditions = []
        if not self.softDollarTier:
            self.softDollarTier = SoftDollarTier()

    def __repr__(self):
        attrs = self.nonDefaults()
        if self.__class__ is not Order:
            attrs.pop('orderType', None)
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


class LimitOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, lmtPrice, **kwargs):
        Order.__init__(
            self, orderType='LMT', action=action,
            totalQuantity=totalQuantity, lmtPrice=lmtPrice, **kwargs)


class MarketOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, **kwargs):
        Order.__init__(
            self, orderType='MKT', action=action,
            totalQuantity=totalQuantity, **kwargs)


class StopOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, stopPrice, **kwargs):
        Order.__init__(
            self, orderType='STP', action=action,
            totalQuantity=totalQuantity, auxPrice=stopPrice, **kwargs)


class StopLimitOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, lmtPrice, stopPrice, **kwargs):
        Order.__init__(
            self, orderType='STP LMT', action=action,
            totalQuantity=totalQuantity, lmtPrice=lmtPrice,
            auxPrice=stopPrice, **kwargs)


class OrderCondition(Object):
    __slots__ = ()

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

    def __repr__(self):
        clsName = self.__class__.__qualname__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in self.dict().items())
        return f'{clsName}({kwargs})'

    def And(self):
        self.conjunction = 'a'
        return self

    def Or(self):
        self.conjunction = 'o'
        return self


class PriceCondition(OrderCondition):
    defaults = dict(
        condType=1,
        conjunction='a',
        isMore=True,
        price=0.0,
        conId=0,
        exch='',
        triggerMethod=0)
    __slots__ = defaults.keys()


class TimeCondition(OrderCondition):
    defaults = dict(
        condType=3,
        conjunction='a',
        isMore=True,
        time='')
    __slots__ = defaults.keys()


class MarginCondition(OrderCondition):
    defaults = dict(
        condType=4,
        conjunction='a',
        isMore=True,
        percent=0)
    __slots__ = defaults.keys()


class ExecutionCondition(OrderCondition):
    defaults = dict(
        condType=5,
        conjunction='a',
        secType='',
        exch='',
        symbol='')
    __slots__ = defaults.keys()


class VolumeCondition(OrderCondition):
    defaults = dict(
        condType=6,
        conjunction='a',
        isMore=True,
        volume=0,
        conId=0,
        exch='')
    __slots__ = defaults.keys()


class PercentChangeCondition(OrderCondition):
    defaults = dict(
        condType=7,
        conjunction='a',
        isMore=True,
        changePercent=0.0,
        conId=0,
        exch='')
    __slots__ = defaults.keys()
