from eventkit import Event, Op

from ib_insync.objects import Object, BarList
from ib_insync.util import isNan

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
        markPrice=nan,
        halted=nan,
        rtHistVolatility=nan,
        rtVolume=nan,
        avVolume=nan,
        tradeCount=nan,
        tradeRate=nan,
        volumeRate=nan,
        shortableShares=nan,
        indexFuturePremium=nan,
        futuresOpenInterest=nan,
        putOpenInterest=nan,
        callOpenInterest=nan,
        putVolume=nan,
        callVolume=nan,
        avOptionVolume=nan,
        histVolatility=nan,
        impliedVolatility=nan,
        dividends=None,
        fundamentalRatios=None,
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
    __slots__ = tuple(defaults.keys()) + events + ('__dict__',)

    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.updateEvent = TickerUpdateEvent('updateEvent')

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


class TickerUpdateEvent(Event):
    __slots__ = ()

    def trades(self) -> "Tickfilter":
        """
        Emit trade ticks.
        """
        return Tickfilter((4, 5, 48, 68, 71), self)

    def bids(self) -> "Tickfilter":
        """
        Emit bid ticks.
        """
        return Tickfilter((0, 1, 66, 69), self)

    def asks(self) -> "Tickfilter":
        """
        Emit ask ticks.
        """
        return Tickfilter((2, 3, 67, 70), self)

    def bidasks(self) -> "Tickfilter":
        """
        Emit bid and ask ticks.
        """
        return Tickfilter((0, 1, 66, 69, 2, 3, 67, 70), self)

    def midpoints(self) -> "Tickfilter":
        """
        Emit midpoint ticks.
        """
        return Midpoints((), self)


class Tickfilter(Op):
    """
    Tick filtering event operators that ``emit(time, price, size)``.
    """
    __slots__ = ('_tickTypes',)

    def __init__(self, tickTypes, source=None):
        Op.__init__(self, source)
        self._tickTypes = set(tickTypes)

    def on_source(self, ticker):
        for t in ticker.ticks:
            if t.tickType in self._tickTypes:
                self.emit(t.time, t.price, t.size)

    def timebars(self, timer: Event) -> "TimeBars":
        """
        Aggregate ticks into time bars, where the timing of new bars
        is derived from a timer event.
        Emits a completed :class:`Bar`.

        This event stores a :class:`BarList` of all created bars in the
        ``bars`` property.

        Args:
            timer: Event for timing when a new bar starts.
        """
        return TimeBars(timer, self)

    def tickbars(self, count: int) -> "TickBars":
        """
        Aggregate ticks into bars that have the same number of ticks.
        Emits a completed :class:`Bar`.

        This event stores a :class:`BarList` of all created bars in the
        ``bars`` property.

        Args:
            count: Number of ticks to use to form one bar.
        """
        return TickBars(count, self)


class Midpoints(Tickfilter):
    __slots__ = ()

    def on_source(self, ticker):
        if ticker.ticks:
            self.emit(ticker.time, ticker.midpoint(), 0)


class Bar(Object):
    defaults = dict(
        time=None,
        open=nan,
        high=nan,
        low=nan,
        close=nan,
        volume=0,
        count=0
    )
    __slots__ = defaults


class TimeBars(Op):
    __slots__ = ('_timer', 'bars',)
    __doc__ = Tickfilter.timebars.__doc__

    def __init__(self, timer, source=None):
        Op.__init__(self, source)
        self._timer = timer
        self._timer.connect(self._on_timer, None, self._on_timer_done)
        self.bars: BarList = BarList()

    def on_source(self, time, price, size):
        if not self.bars:
            return
        bar = self.bars[-1]
        if isNan(bar.open):
            bar.open = bar.high = bar.low = price
        bar.high = max(bar.high, price)
        bar.low = min(bar.low, price)
        bar.close = price
        bar.volume += size
        bar.count += 1
        self.bars.updateEvent.emit(self.bars, False)

    def _on_timer(self, time):
        if self.bars:
            bar = self.bars[-1]
            if isNan(bar.close) and len(self.bars) > 1:
                bar.open = bar.high = bar.low = bar.close = \
                    self.bars[-2].close
            self.bars.updateEvent.emit(self.bars, True)
            self.emit(bar)
        self.bars.append(Bar(time))

    def _on_timer_done(self, timer):
        self._timer = None
        self.set_done()


class TickBars(Op):
    __slots__ = ('_count', 'bars')
    __doc__ = Tickfilter.tickbars.__doc__

    def __init__(self, count, source=None):
        Op.__init__(self, source)
        self._count = count
        self.bars: BarList = BarList()

    def on_source(self, time, price, size):
        if not self.bars or self.bars[-1].count == self._count:
            bar = Bar(time, price, price, price, price, size, 1)
            self.bars.append(bar)
        else:
            bar = self.bars[-1]
            bar.high = max(bar.high, price)
            bar.low = min(bar.low, price)
            bar.close = price
            bar.volume += size
            bar.count += 1
        if bar.count == self._count:
            self.bars.updateEvent.emit(self.bars, True)
            self.emit(self.bars)
