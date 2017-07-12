import ibapi

from ib_insync.objects import Object

__all__ = 'Order LimitOrder MarketOrder StopOrder StopLimitOrder '.split()


class Order(Object):
    """
    Order for trading contracts.
    
    https://interactivebrokers.github.io/tws-api/available_orders.html
    """
    defaults = ibapi.order.Order().__dict__
    __slots__ = list(defaults.keys()) + \
            ['sharesAllocation', 'orderComboLegsCount',
                'smartComboRoutingParamsCount', 'conditionsSize']  # bugs in decoder.py
    __init__ = Object.__init__

    def __repr__(self):
        attrs = self.nonDefaults()
        if self.__class__ is not Order:
            attrs.pop('orderType', None)
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__


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

