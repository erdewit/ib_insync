from ib_insync.objects import Object
from ib_insync.util import isNan

__all__ = ['Ticker']


nan = float('nan')


class Ticker(Object):
    """
    Current market data for a contract.
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
        'ticks': None }
    __slots__ = defaults.keys()
    __init__ = Object.__init__

    def __repr__(self):
        attrs = {}
        for k, d in self.__class__.defaults.items():
            v = getattr(self, k)
            if v != d and not isNan(v):
                attrs[k] = v
        if self.ticks:
            # ticks can grow too large to display
            attrs.pop('ticks')
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
