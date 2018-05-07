import ibapi

from .objects import Object
from ib_insync.event import Event

__all__ = ('Trade OrderStatus Order '
        'LimitOrder MarketOrder StopOrder StopLimitOrder').split()


class Trade(Object):
    """
    Trade keeps track of an order, its status and all its fills.
    
    Events:
        * ``statusEvent(trade)``
        * ``modifyEvent(trade)``
        * ``fillEvent(trade, fill)``
        * ``commissionReportEvent(trade, fill, commissionReport)``
        * ``filledEvent(trade)``
        * ``cancelEvent(trade)``
        * ``cancelledEvent(trade)``
    """
    events = ('statusEvent', 'modifyEvent', 'fillEvent',
            'commissionReportEvent', 'filledEvent',
            'cancelEvent', 'cancelledEvent')

    defaults = dict(
        contract=None,
        order=None,
        orderStatus=None,
        fills=None,
        log=None
    )
    __slots__ = tuple(defaults.keys()) + events

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        Event.init(self, Trade.events)

    def isActive(self):
        """
        True if eliglible for execution, false otherwise.
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
    ApiPending = 'ApiPending'  # undocumented, can be returned from req(All)OpenOrders
    ApiCancelled = 'ApiCancelled'
    Cancelled = 'Cancelled'
    Filled = 'Filled'
    Inactive = 'Inactive'

    DoneStates = {'Cancelled', 'Filled', 'ApiCancelled', 'Inactive'}
    ActiveStates = {'PendingSubmit', 'ApiPending', 'PreSubmitted', 'Submitted'}


class Order(Object):
    """
    Order for trading contracts.
    
    https://interactivebrokers.github.io/tws-api/available_orders.html
    """
    defaults = ibapi.order.Order().__dict__
    __slots__ = list(defaults.keys()) + [
            'sharesAllocation', 'orderComboLegsCount', 'algoParamsCount',
            'smartComboRoutingParamsCount', 'conditionsSize',
            'conditionType']  # bugs in decoder.py

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        if not self.conditions:
            self.conditions = []

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
        Order.__init__(self, orderType='LMT', action=action,
                totalQuantity=totalQuantity, lmtPrice=lmtPrice, **kwargs)


class MarketOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, **kwargs):
        Order.__init__(self, orderType='MKT', action=action,
                totalQuantity=totalQuantity, **kwargs)


class StopOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, stopPrice, **kwargs):
        Order.__init__(self, orderType='STP', action=action,
                totalQuantity=totalQuantity, auxPrice=stopPrice, **kwargs)


class StopLimitOrder(Order):
    __slots__ = ()

    def __init__(self, action, totalQuantity, lmtPrice, stopPrice, **kwargs):
        Order.__init__(self, orderType='STP LMT', action=action,
                totalQuantity=totalQuantity, lmtPrice=lmtPrice,
                auxPrice=stopPrice, **kwargs)

