from ib_insync.objects import Object
from ib_insync.util import isNan
from ib_insync.event import Event

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
    
    Streaming tick-by-tick ticks are stored in ``tickByTicks``.
    
    For options the ``OptionComputation`` values for the bid, ask, resp.
    last price are stored in the ``bidGreeks``, ``askGreeks`` resp.
    ``lastGreeks`` attributes. There is also ``modelGreeks`` that conveys
    the greeks as calculated by Interactive Brokers' option model.
    
    Events:
        * ``updateEvent(ticker)``
    """

    events = ('updateEvent',)

    defaults = dict(
        contract=None,
        time=None,
        bid=nan,
        bidSize=nan,
        ask=nan,
        askSize=nan,
        last=nan,
        lastSize=nan,
        prevBid=nan,
        prevBidSize=nan,
        prevAsk=nan,
        prevAskSize=nan,
        prevLast=nan,
        prevLastSize=nan,
        volume=nan,
        open=nan,
        high=nan,
        low=nan,
        close=nan,
        vwap=nan,
        low13week=nan,
        high13week=nan,
        low26week=nan,
        high26week=nan,
        low52week=nan,
        high52week=nan,
        bidYield=nan,
        askYield=nan,
        lastYield=nan,
        rtVolume=nan,
        avVolume=nan,
        putOpenInterest=nan,
        callOpenInterest=nan,
        putVolume=nan,
        callVolume=nan,
        dividends=None,
        ticks=None,
        tickByTicks=None,
        domBids=None,
        domAsks=None,
        domTicks=None,
        bidGreeks=None,
        askGreeks=None,
        lastGreeks=None,
        modelGreeks=None
    )
    __slots__ = tuple(defaults.keys()) + events

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        Event.init(self, Ticker.events)

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def midpoint(self):
        """
        Return average of bid and ask.
        """
        return (self.bid + self.ask) / 2

    def marketPrice(self):
        """
        Return the first available one of
        
        * last price if within current bid/ask;
        * average of bid and ask (midpoint);
        * close price.
        """
        midpoint = self.midpoint()
        price = self.last if (isNan(midpoint) or
                self.bid <= self.last <= self.ask) else nan
        if isNan(price):
            price = midpoint
        if isNan(price) or price == -1:
            price = self.close
        return price
