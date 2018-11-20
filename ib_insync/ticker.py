from ib_insync.objects import Object
from ib_insync.util import isNan
from ib_insync.event import Event

__all__ = ['Ticker']

nan = float('nan')


class Ticker(Object):
    """
    Current market data such as bid, ask, last price, etc. for a contract.

    Streaming level-1 ticks of type :class:`.TickData` are stored in
    the ``ticks`` list.

    Streaming level-2 ticks of type :class:`.MktDepthData` are stored in the
    ``domTicks`` list. The order book (DOM) is available as lists of
    :class:`.DOMLevel` in ``domBids`` and ``domAsks``.

    Streaming tick-by-tick ticks are stored in ``tickByTicks``.

    For options the :class:`.OptionComputation` values for the bid, ask, resp.
    last price are stored in the ``bidGreeks``, ``askGreeks`` resp.
    ``lastGreeks`` attributes. There is also ``modelGreeks`` that conveys
    the greeks as calculated by Interactive Brokers' option model.

    Events:
        * ``updateEvent`` (ticker: :class:`.Ticker`)
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
        futuresOpenInterest=nan,
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

    def hasBidAsk(self) -> bool:
        """
        See if this ticker has a valid bid and ask.
        """
        return (
            self.bid != -1 and not isNan(self.bid) and self.bidSize > 0 and
            self.ask != -1 and not isNan(self.ask) and self.askSize > 0)

    def midpoint(self) -> float:
        """
        Return average of bid and ask, or NaN if no valid bid and ask
        are available.
        """
        return (self.bid + self.ask) / 2 if self.hasBidAsk() else nan

    def marketPrice(self) -> float:
        """
        Return the first available one of

        * last price if within current bid/ask;
        * average of bid and ask (midpoint);
        * close price.
        """
        price = self.last if (
            self.hasBidAsk() and self.bid <= self.last <= self.ask) else \
            self.midpoint()
        if isNan(price):
            price = self.close
        return price
