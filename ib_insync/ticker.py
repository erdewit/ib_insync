from ib_insync.objects import Object
from ib_insync.util import isNan

__all__ = ['Ticker']


nan = float('nan')


class Ticker(Object):
    """
    Current market data such as bid, ask, last price, etc. for a contract.
            
    Streaming level-1 ticks of type ``TickData`` are stored in
    the ``ticks`` list.
    
    Streaming level-2 ticks of type ``MktDepthData`` are stored in the
    ``domTicks`` list. The order book (DOM) is available as lists of
    ``DOMLevel`` in ``domBids`` and ``domAsks``.
    """
    defaults = {
        'contract': None,
        'time': nan,
        'bid': nan,
        'bidSize': nan,
        'ask': nan,
        'askSize': nan,
        'last': nan,
        'lastSize': nan,
        'prevBid': nan,
        'prevBidSize': nan,
        'prevAsk': nan,
        'prevAskSize': nan,
        'prevLast': nan,
        'prevLastSize': nan,
        'volume': nan,
        'open': nan,
        'high': nan,
        'low': nan,
        'close': nan,
        'low13week': nan,
        'high13week': nan,
        'low26week': nan,
        'high26week': nan,
        'low52week': nan,
        'high52week': nan,
        'avVolume': nan,
        'putOpenInterest': nan,
        'callOpenInterest': nan,
        'putVolume': nan,
        'callVolume': nan,
        'futuresOpenInterest': nan,
        'ticks': None,
        'domBids': None,
        'domAsks': None,
        'domTicks': None }
    __slots__ = defaults.keys()
    __init__ = Object.__init__

    def __repr__(self):
        attrs = {}
        for k, d in self.__class__.defaults.items():
            v = getattr(self, k)
            if v != d and not isNan(v):
                attrs[k] = v
        # ticks can grow too large to display
        attrs.pop('ticks')
        attrs.pop('domTicks')
        attrs.pop('domBids')
        attrs.pop('domAsks')
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def marketPrice(self):
        """
        Return the first available one of
        
        * last price
        * average of bid and ask
        * close price
        """
        price = self.last
        if isNan(price):
            price = (self.bid + self.ask) / 2
        if isNan(price):
            price = self.close
        return price
