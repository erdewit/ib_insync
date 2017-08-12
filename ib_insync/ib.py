import asyncio
import logging
import datetime
import functools

import time
from typing import Iterator
from collections.abc import Awaitable  # @UnusedImport

from ibapi.account_summary_tags import AccountSummaryTags

from ib_insync.client import Client
from ib_insync.wrapper import Wrapper
from ib_insync.contract import Contract
from ib_insync.ticker import Ticker
from ib_insync.order import Order, LimitOrder, StopOrder, MarketOrder
from ib_insync.objects import *
import ib_insync.util as util

__all__ = ['IB']

_logger = logging.getLogger('ib_insync.ib')


def api(f): return f  # visual marker for API request methods

def rw_mode(f):       # access control
    @functools.wraps(f)
    def wrapper(self, *args, **kwds):
        if self.read_only == True:
            _logger.warning(f'rw_mode: Attempt to call {f.__qualname__} while in ro mode')
            pass
        else:
            return f(self, *args, **kwds)
    return wrapper

class IB:
    """
    Provides both a blocking and an asynchronous interface
    to the IB Python API, using asyncio networking and event loop. 
    
    The IB class offers direct access to the current state, such as
    orders, executions, positions, tickers etc. This state is
    automatically kept in sync with the TWS/IBG application.
      
    This class has most request methods of EClient, with the
    same names and parameters (except for the reqId parameter
    which is not needed anymore).
    Request methods that return a result come in two versions:
      
    * Blocking: Will block until complete and return the result.
      The current state will be kept updated while the request is ongoing;
        
    * Asynchronous: All methods that have the "Async" postfix.
      Implemented as coroutines or methods that return a Future and
      intended for advanced users.
    
    **The One Rule:**

    While some of the request methods are blocking from the perspective
    of the user, the framework will still keep spinning in the background
    and handle all messages received from TWS/IBG. It is important to
    not block the framework from doing its work. If, for example,
    the user code spends much time in a calculation, or uses time.sleep()
    with a long delay, the framework will stop spinning, messages
    accumulate and things may go awry.
    
    The one rule when working with the IB class is therefore that
    
    **user code may not block for too long**.
    
    To be clear, the IB request methods are okay to use and do not
    count towards the user operation time, no matter how long the
    request takes to finish.

    So what is "too long"? That depends on the situation. If, for example,
    the timestamp of tick data is to remain accurate within a millisecond,
    then the user code must not spend longer than a millisecond. If, on
    the other extreme, there is very little incoming data and there
    is no desire for accurate timestamps, then the user code can block
    for hours.
    
    If a user operation takes a long time then it can be farmed out
    to a different process. 
    Alternatively the operation can be made such that it periodically
    calls IB.sleep(0); This will let the framework handle any pending
    work and return when finished. The operation should be aware
    that the current state may have been updated during the sleep(0) call.
    
    For introducing a delay, never use time.sleep() but use
    :py:meth:`.sleep` instead.
    """
    def __init__(self):
        self.wrapper = Wrapper()
        self.client = Client(self.wrapper)

    def connect(self, host: str, port: int, clientId: int, timeout: float=2, read_only: bool=False):
        """
        Connect to a TWS or IB gateway application running at host:port.
        After the connect the client is immediately ready to serve requests. 
        
        This method is blocking.
        """
        self.read_only = read_only
        self.run(self.connectAsync(host, port, clientId, timeout))

    def disconnect(self):
        """
        Disconnect from a TWS or IB gateway application.
        This will clear all session state.  
        """
        self.wrapper.reset()
        if not self.client.isConnected():
            return
        stats = self.client.connectionStats()
        _logger.info(
            f'Disconnecting from {self.client.host}:{self.client.port}, '
            f'{util.formatSI(stats.numBytesSent)}B sent '
            f'in {stats.numMsgSent} messages, '
            f'{util.formatSI(stats.numBytesRecv)}B received '
            f'in {stats.numMsgRecv} messages, '
            f'session time {util.formatSI(stats.duration)}s.')
        self.client.disconnect()

    @staticmethod
    def run(*awaitables: [Awaitable]):
        """
        By default run the event loop forever.
        
        When awaitables (like Tasks, Futures or coroutines) are given then
        run the event loop until each has completed and return their results.
        """
        loop = asyncio.get_event_loop()
        if not awaitables:
            result = loop.run_forever()
        else:
            if len(awaitables) == 1:
                future = awaitables[0]
            else:
                future = asyncio.gather(*awaitables)
            result = util.syncAwait(future)
        return result

    @staticmethod
    def sleep(secs: [float]=0.02) -> True:
        """
        Wait for the given amount of seconds while everything still keeps
        processing in the background. Never use time.sleep().
        """
        IB.run(asyncio.sleep(secs))
        return True

    @staticmethod
    def timeRange(start: datetime.time, end: datetime.time,
                  step: float) -> Iterator[datetime.datetime]:
        """
        Iterator that waits periodically until certain time points are
        reached while yielding those time points.
        
        The startTime and dateTime parameters can be specified as
        datetime.datetime, or as datetime.time in which case today
        is used as the date.
        
        The step parameter is the number of seconds of each period.
        """
        assert step > 0
        if isinstance(start, datetime.time):
            start = datetime.datetime.combine(datetime.date.today(), start)
        if isinstance(end, datetime.time):
            end = datetime.datetime.combine(datetime.date.today(), end)
        delta = datetime.timedelta(seconds=step)
        t = start
        while t < datetime.datetime.now():
            t += delta
        while t <= end:
            IB.waitUntil(t)
            yield t
            t += delta

    @staticmethod
    def waitUntil(t: datetime.time):
        """
        Wait until the given time t is reached.
        
        The time can be specified as datetime.datetime,
        or as datetime.time in which case today is used as the date.
        """
        if isinstance(t, datetime.time):
            t = datetime.datetime.combine(datetime.date.today(), t)
        now = datetime.datetime.now(t.tzinfo)
        secs = (t - now).total_seconds()
        IB.run(asyncio.sleep(secs))
        return True

    def waitOnUpdate(self) -> True:
        """
        Wait on any new update to arrive from the network.
        """
        self.run(self.wrapper.updateEvent.wait())
        return True

    def loopUntil(self, condition=None, timeout: float=0) -> Iterator:
        """
        Iteratate until condition is met, with optional timeout in seconds.
        The given optional condition is tested after every network packet.
        The yielded value is that of the condition or False when timed out.
        """
        endTime = time.time() + timeout
        while True:
            test = condition and condition()
            if test:
                yield test
                return
            elif timeout and time.time() > endTime:
                yield False
                return
            else:
                yield test
            if timeout:
                try:
                    self.run(asyncio.wait_for(
                        self.wrapper.updateEvent.wait(),
                        endTime - time.time()))
                except asyncio.TimeoutError:
                    pass
            else:
                self.waitOnUpdate()

    def setCallback(self, eventName, callback):
        """
        Set an optional callback to be invoked after an event. Events::
        
            * updated()
            * pendingTickers(set(pendingTickers))
            * orderStatus(Trade)
            * execDetails(Trade, Fill)
            * commissionReport(Trade, Fill, CommissionReport)
            * updatePortfolio(PortfolioItem)
            * position(Position)
            * tickNews(NewsTick)
            
        Unsetting is done by supplying None as callback.
        """
        self.wrapper.setCallback(eventName, callback)

    def managedAccounts(self) -> [str]:
        """
        List of account names.
        """
        return list(self.wrapper.accounts)

    def accountValues(self) -> [AccountValue]:
        """
        List of account values for the default account.
        """
        account = self.wrapper.accounts[0]
        return [av for av in self.wrapper.accountValues.values()
                if av.account == account]

    def accountSummary(self, account: str='') -> [AccountValue]:
        """
        List of account values for the given account,
        or of all accounts if account is left blank.
        
        This method is blocking on first run, non-blocking after that.
        """
        if not self.wrapper.acctSummary:
            # loaded on demand since it takes ca. 250 ms
            self.reqAccountSummary()
        if account:
            return [v for v in self.wrapper.acctSummary.values()
                    if v.account == account]
        else:
            return list(self.wrapper.acctSummary.values())

    def portfolio(self) -> [PortfolioItem]:
        """
        List of portfolio items of the default account.
        """
        account = self.wrapper.accounts[0]
        return [v for v in self.wrapper.portfolio[account].values()]

    def positions(self, account: str='') -> [Position]:
        """
        List of positions for the given account,
        or of all accounts if account is left blank.
        """
        if account:
            return list(self.wrapper.positions[account].values())
        else:
            return [v for d in self.wrapper.positions.values()
                    for v in d.values()]

    def trades(self) -> [Trade]:
        """
        List of all order tickets from this session.
        """
        return list(self.wrapper.trades.values())

    def openTrades(self) -> [Trade]:
        """
        List of all open order tickets.
        """
        return [v for v in self.wrapper.trades.values()
                if v.orderStatus.status in OrderStatus.ActiveStates]

    def orders(self) -> [Order]:
        """
        List of all orders from this session.
        """
        return list(ticket.order
                for ticket in self.wrapper.trades.values())

    def openOrders(self) -> [Order]:
        """
        List of all open orders.
        """
        return [ticket.order for ticket in self.wrapper.trades.values()
                if ticket.orderStatus.status in OrderStatus.ActiveStates]

    def fills(self) -> [Fill]:
        """
        List of all fills from this session.
        """
        return list(self.wrapper.fills.values())

    def executions(self) -> [Execution]:
        """
        List of all executions from this session.
        """
        return list(fill.execution for fill in self.wrapper.fills.values())

    def ticker(self, contract: Contract) -> Ticker:
        """
        Get ticker of the given contract. It must have been requested before
        with reqMktData with the same contract object. The ticker may not be
        ready yet if called directly after :py:meth:`.reqMktData`.
        """
        return self.wrapper.tickers.get(id(contract))

    def tickers(self) -> [Ticker]:
        """
        Get a list of all tickers.
        """
        return list(self.wrapper.tickers.values())

    def pendingTickers(self) -> [Ticker]:
        """
        Get a list of all tickers that have pending ticks or domTicks.
        """
        return list(self.wrapper.pendingTickers)

    def realtimeBars(self):
        """
        Get a list of all live updated bars. These can be 5 second realtime
        bars or live updated historical bars.
        """
        return list(self.wrapper.reqId2Bars.values())

    def newsTicks(self) -> [NewsTick]:
        """
        List of ticks with headline news.
        The article itself can be retrieved with :py:meth:`.reqNewsArticle`.
        """
        return self.wrapper.newsTicks

    def newsBulletins(self) -> [NewsBulletin]:
        """
        List of IB news bulletins.
        """
        return list(self.wrapper.newsBulletins.values())

    def reqTickers(self, *contracts: [Contract],
            regulatorySnapshot: bool=False) -> [Ticker]:
        """
        Request and return a list of snapshot tickers for the given contracts.
        The list is returned when all tickers are ready.

        This method is blocking.
        """
        return self.run(self.reqTickersAsync(*contracts,
                regulatorySnapshot=regulatorySnapshot))

    def qualifyContracts(self, *contracts: [Contract]) -> [Contract]:
        """
        Fully qualify the given contracts in-place. This will fill in
        the missing fields in the contract, especially the conId.

        Returns a list of contracts that have been successfully qualified.

        This method is blocking.
        """
        return self.run(self.qualifyContractsAsync(*contracts))

    def bracketOrder(self, action: str, quantity: float,
            limitPrice: float, takeProfitPrice: float,
            stopLossPrice: float) -> BracketOrder:
        """
        Create a limit order that is bracketed by a take-profit order and
        a stop-loss order. Submit the bracket like:

        .. code-block:: python

            for o in bracket:
                ib.placeOrder(contract, o)

        https://interactivebrokers.github.io/tws-api/bracket_order.html
        """
        assert action in ('BUY', 'SELL')
        reverseAction = 'BUY' if action == 'SELL' else 'SELL'
        parent = LimitOrder(
                action, quantity, limitPrice,
                orderId=self.client.getReqId(),
                transmit=False)
        takeProfit = LimitOrder(
                reverseAction, quantity, takeProfitPrice,
                orderId=self.client.getReqId(),
                transmit=False,
                parentId=parent.orderId)
        stopLoss = StopOrder(
                reverseAction, quantity, stopLossPrice,
                orderId=self.client.getReqId(),
                transmit=True,
                parentId=parent.orderId)
        return BracketOrder(parent, takeProfit, stopLoss)

    def oneCancelsAll(self, orders: [Order],
                      ocaGroup: str, ocaType: int) -> [Order]:
        """
        Place the trades in the same OCA group.
        
        https://interactivebrokers.github.io/tws-api/oca.html
        """
        for o in orders:
            o.ocaGroup = ocaGroup
            o.ocaType = ocaType
        return orders

    @rw_mode
    def whatIfOrder(self, contract: Contract, order: Order) -> OrderState:
        """
        Retrieve commission and margin impact without actually
        placing the order. The given order will not be modified in any way.
        
        This method is blocking.
        """
        return self.run(self.whatIfOrderAsync(contract, order))

    @api
    @rw_mode
    def placeOrder(self, contract: Contract, order: Order) -> Trade:
        """
        Place a new order or modify an existing order.
        Returns an Trade that is kept live updated with
        status changes, fills, etc.
        """
        orderId = order.orderId or self.client.getReqId()
        self.client.placeOrder(orderId, contract, order)
        now = datetime.datetime.now(datetime.timezone.utc)
        if not isinstance(order, Order):
            order = Order(**order.__dict__)
        trade = self.wrapper.trades.get(orderId)
        if trade:
            # this is a modification of an existing order
            assert trade.orderStatus.status in OrderStatus.ActiveStates
            logEntry = TradeLogEntry(now,
                    trade.orderStatus.status, 'Modify')
            trade.log.append(logEntry)
            _logger.info(f'placeOrder: Modify order {trade}')
        else:
            # this is a new order
            order.orderId = orderId
            orderStatus = OrderStatus(status=OrderStatus.PendingSubmit)
            logEntry = TradeLogEntry(now, orderStatus.status, '')
            trade = Trade(
                    contract, order, orderStatus, [], [logEntry])
            self.wrapper.trades[orderId] = trade
            _logger.info(f'placeOrder: New order {trade}')
        return trade

    @api
    @rw_mode
    def cancelOrder(self, order: Order) -> Trade:
        """
        Cancel the order and return the Trade it belongs to.
        """
        self.client.cancelOrder(order.orderId)
        now = datetime.datetime.now(datetime.timezone.utc)
        trade = self.wrapper.trades.get(order.orderId)
        if trade:
            if trade.orderStatus.status in OrderStatus.ActiveStates:
                logEntry = TradeLogEntry(now, OrderStatus.PendingCancel, '')
                trade.log.append(logEntry)
            _logger.info(f'cancelOrder: {trade}')
        else:
            _logger.error(f'cancelOrder: Unknown orderId {order.orderId}')
        return trade

    @api
    @rw_mode
    def reqGlobalCancel(self) -> None:
        """
        Cancel all active trades including those placed by other
        clients or TWS/IB gateway.
        """
        self.client.reqGlobalCancel()
        _logger.info(f'reqGlobalCancel')

    @api
    def reqAccountUpdates(self) -> None:
        """
        This is called at startup - no need to call again.
        
        Request account and portfolio values of the default account
        and keep updated. Returns when both account values and portfolio
        are filled.

        This method is blocking.
        """
        self.run(self.reqAccountUpdatesAsync())

    @api
    def reqAccountSummary(self) -> None:
        """
        It is recommended to use :py:meth:`.accountSummary` instead.

        Request account values for all accounts and keep them updated.
        Returns when account summary is filled.

        This method is blocking.
        """
        self.run(self.reqAccountSummaryAsync())

    @api
    @rw_mode
    def reqOpenOrders(self) -> [Order]:
        """
        It is recommended to use :py:meth:`.openTrades` or
        :py:meth:`.openOrders` instead.

        Request and return a list a list of open orders.

        This method is blocking.
        """
        return self.run(self.reqOpenOrdersAsync())

    @api
    def reqExecutions(self,
            execFilter: ExecutionFilter=None) -> [Fill]:
        """
        It is recommended to use :py:meth:`.fills`  or
        :py:meth:`.executions` instead.

        Request and return a list a list of fills.

        This method is blocking.
        """
        return self.run(self.reqExecutionsAsync(execFilter))

    @api
    def reqPositions(self) -> [Position]:
        """
        It is recommended to use :py:meth:`.positions` instead.

        Request and return a list of positions for all accounts.

        This method is blocking.
        """
        return self.run(self.reqPositionsAsync())

    @api
    def reqContractDetails(self, contract: Contract) -> [ContractDetails]:
        """
        Get a list of contract details that match the given contract.
        If the returned list is empty then the contract is not known;
        If the list has multiple values then the contract is ambiguous.
    
        The fully qualified contract is available in the the
        ContractDetails.summary attribute.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/contract_details.html
        """
        return self.run(self.reqContractDetailsAsync(contract))

    @api
    def reqMatchingSymbols(self, pattern: str) -> [ContractDescription]:
        """
        Request contract descriptions of contracts that match the given
        pattern.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/matching_symbols.html
        """
        return self.run(self.reqMatchingSymbolsAsync(pattern))

    @api
    def reqRealTimeBars(self, contract, barSize, whatToShow,
            useRTH, realTimeBarsOptions=None) -> [RealTimeBar]:
        """
        Request realtime 5 second bars.
        
        https://interactivebrokers.github.io/tws-api/realtime_bars.html
        """
        reqId = self.client.getReqId()
        bars = self.wrapper.startLiveBars(reqId)
        self.client.reqRealTimeBars(reqId, contract, barSize, whatToShow,
                useRTH, realTimeBarsOptions)
        return bars

    @api
    def cancelRealTimeBars(self, bars):
        """
        Cancel the realtime bars subscription.
        """
        reqId = self.wrapper.endLiveBars(bars)
        if reqId:
            self.client.cancelRealTimeBars(reqId)
        else:
            _logger.error('cancelRealTimeBars: No reqId found')

    @api
    def reqHistoricalData(self, contract: Contract, endDateTime: object,
            durationStr: str, barSizeSetting: str,
            whatToShow: str, useRTH: bool,
            formatDate: int=1, keepUpToDate: bool=False,
            chartOptions=None) -> [BarData]:
        """
        The endDateTime can be set to '' to indicate the current time,
        or it can be given as a datetime.date or datetime.datetime,
        or it can be given as a string in 'yyyyMMdd HH:mm:ss' format.
        
        If formatDate=2 is used for an intraday request the returned date
        field will be a timezone-aware datetime.datetime with UTC timezone.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/historical_bars.html
        """
        return self.run(self.reqHistoricalDataAsync(contract, endDateTime,
                durationStr, barSizeSetting, whatToShow,
                useRTH, formatDate, keepUpToDate, chartOptions))

    @api
    def cancelHistoricalData(self, bars):
        """
        Cancel the update subscription for the historical bars.
        """
        reqId = self.wrapper.endLiveBars(bars)
        if reqId:
            self.client.cancelHistoricalData(reqId)
        else:
            _logger.error('cancelHistoricalData: No reqId found')

    @api
    def reqHistoricalTicks(self, contract, startDateTime, endDateTime,
            numberOfTicks, whatToShow, useRth, ignoreSize, miscOptions):
        """
        Request historical ticks.

        This method is blocking.
        
        https://interactivebrokers.github.io/tws-api/historical_time_and_sales.html
        """
        return self.run(self.reqHistoricalTicksAsync(contract,
            startDateTime, endDateTime, numberOfTicks, whatToShow, useRth,
            ignoreSize, miscOptions))

    @api
    def reqMarketDataType(self, marketDataType: int):
        """
        marketDataType:
            * 1 = Live
            * 2 = Frozen
            * 3 = Delayed
            * 4 = Delayed frozen
        
        https://interactivebrokers.github.io/tws-api/market_data_type.html
        """
        self.client.reqMarketDataType(marketDataType)

    @api
    def reqHeadTimeStamp(self, contract: Contract, whatToShow: str,
            useRTH: bool, formatDate: int=1) -> datetime.datetime:
        """
        Get the datetime of earliest available historical data for the contract.
        
        If formatDate=2 then the result is returned as a
        timezone-aware datetime.datetime with UTC timezone.
        """
        return self.run(self.reqHeadTimeStampAsync(contract, whatToShow,
                useRTH, formatDate))

    @api
    def reqMktData(self, contract: Contract, genericTickList: str,
                snapshot: bool, regulatorySnapshot: bool,
                mktDataOptions=None) -> Ticker:
        """
        Subscribe to tick data or request a snapshot.
        The results are available from the ticker() method.

        https://interactivebrokers.github.io/tws-api/md_request.html
        """
        reqId = self.client.getReqId()
        ticker = self.wrapper.startTicker(reqId, contract)
        self.client.reqMktData(reqId, contract, genericTickList,
                snapshot, regulatorySnapshot, mktDataOptions)
        return ticker

    def cancelMktData(self, contract: Contract):
        """
        Unsubscribe tick data for the given contract.
        The contract object must be the same as used to subscribe with.
        """
        ticker = self.ticker(contract)
        reqId = self.wrapper.endTicker(ticker)
        if reqId:
            self.client.cancelMktData(reqId)
        else:
            _logger.error('cancelMktData: '
                    f'No reqId found for contract {contract}')

    @api
    def reqMktDepthExchanges(self):
        """
        Get those exchanges that have have multiple market makers
        (and have ticks returned with marketMaker info). 
        """
        return self.run(self.reqMktDepthExchangesAsync())

    @api
    def reqMktDepth(self, contract: Contract, numRows: int=15,
                mktDepthOptions=None) -> Ticker:
        """
        """
        reqId = self.client.getReqId()
        ticker = self.wrapper.startTicker(reqId, contract, isMktDepth=True)
        self.client.reqMktDepth(reqId, contract, numRows, mktDepthOptions)
        return ticker

    @api
    def cancelMktDepth(self, contract: Contract):
        """
        Unsubscribe market depth data for the given contract.
        The contract object must be the same as used to subscribe with.
        """
        ticker = self.ticker(contract)
        reqId = self.wrapper.endTicker(ticker, isMktDepth=True)
        if reqId:
            self.client.cancelMktDepth(reqId)
        else:
            _logger.error('cancelMktDepth: '
                    f'No reqId found for contract {contract}')

    @api
    def reqHistogramData(self, contract: Contract,
            useRTH: bool, period: str) -> [HistogramData]:
        """
        Get histogram data of the contract over the period.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/histograms.html
        """
        return self.run(self.reqHistogramDataAsync(
                contract, useRTH, period))

    @api
    def reqFundamentalData(self, contract: Contract, reportType: str,
            fundamentalDataOptions=None) -> str:
        """
        Get Reuters' fundamental data of the contract in XML format.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/reuters_fundamentals.html
        """
        return self.run(self.reqFundamentalDataAsync(contract, reportType,
                fundamentalDataOptions))

    @api
    def reqScannerData(self, subscription: ScannerSubscription,
            scannerSubscriptionOptions=None) -> [ScanData]:
        """
        Do a market scan.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/market_scanners.html
        """
        return self.run(self.reqScannerSubscriptionAsync(
                subscription, scannerSubscriptionOptions))

    @api
    def reqScannerParameters(self) -> str:
        """
        Requests an XML list of scanner parameters.

        This method is blocking.
        """
        return self.run(self.reqScannerParametersAsync())

    @api
    def calculateImpliedVolatility(self, contract: Contract,
                optionPrice: float, underPrice: float,
                implVolOptions=None) -> OptionComputation:
        """
        Calculate the volatility given the option price.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/option_computations.html
        """
        return self.run(self.calculateImpliedVolatilityAsync(
                contract, optionPrice, underPrice, implVolOptions))

    @api
    def calculateOptionPrice(self, contract: Contract,
            volatility: float, underPrice: float,
            optPrcOptions=None) -> OptionComputation:
        """
        Calculate the option price given the volatility.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/option_computations.html
        """
        return self.run(self.calculateOptionPriceAsync(
                contract, volatility, underPrice, optPrcOptions))

    @api
    def reqSecDefOptParams(self, underlyingSymbol: str,
            futFopExchange: str, underlyingSecType: str,
            underlyingConId: str) -> [OptionChain]:
        """
        Get the option chain.
        
        This method is blocking.

        https://interactivebrokers.github.io/tws-api/options.html
        """
        return self.run(self.reqSecDefOptParamsAsync(underlyingSymbol,
                futFopExchange, underlyingSecType, underlyingConId))

    @api
    def exerciseOptions(self, contract, exerciseAction, exerciseQuantity,
            account, override):
        """
        https://interactivebrokers.github.io/tws-api/options.html
        """
        reqId = self.client.getReqId()
        self.client.exerciseOptions(reqId, contract, exerciseAction,
                exerciseQuantity, account, override)

    @api
    def reqNewsProviders(self) -> [NewsProvider]:
        """
        Get a list of news providers.

        This method is blocking.
        """
        return self.run(self.reqNewsProvidersAsync())

    @api
    def reqNewsArticle(self, providerCode: str, articleId: str):
        """
        Get the body of a news article.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/news.html
        """
        return self.run(self.reqNewsArticleAsync(providerCode, articleId))

    @api
    def reqHistoricalNews(self, conId: int, providerCodes: str,
            startDateTime: str, endDateTime: str, totalResults: int,
            historicalNewsOptions=None) -> HistoricalNews:
        """
        Get historical news headline.

        This method is blocking.
        """
        return self.run(self.reqHistoricalNewsAsync(conId, providerCodes,
                startDateTime, endDateTime, totalResults,
                historicalNewsOptions))

    @api
    def reqNewsBulletins(self, allMessages: bool):
        """
        Subscribe to IB news bulletins. If allMessages=True then fetch
        all messages for the day.
        """
        self.client.reqNewsBulletins(allMessages)

    @api
    def cancelNewsBulletins(self):
        """
        Cancel subscription to IB news bulletins.
        """
        self.client.cancelNewsBulletins()

    @api
    def requestFA(self, faDataType: int) -> str:
        """
        faDataType:
        
        * 1 = Groups;
        * 2 = Profiles;
        * 3 = Account Aliases.

        This method is blocking.
        
        https://interactivebrokers.github.io/tws-api/financial_advisor_methods_and_orders.html
        """
        return self.run(self.requestFAAsync(faDataType))

    @api
    def replaceFA(self, faDataType: int, xml: str):
        """
        https://interactivebrokers.github.io/tws-api/financial_advisor_methods_and_orders.html
        """
        self.client.replaceFA(faDataType, xml)

    # now entering the parallel async universe

    async def connectAsync(self, host, port, clientId, timeout=2):
        self.wrapper.clientId = clientId
        await self.client.connectAsync(host, port, clientId, timeout)
        if self.read_only == False:
            await asyncio.gather(
                    self.reqOpenOrdersAsync(),
                    self.reqAccountUpdatesAsync(),
                    self.reqPositionsAsync(),
                    self.reqExecutionsAsync())
        else:
            await asyncio.gather(
                    self.reqAccountUpdatesAsync(),
                    self.reqPositionsAsync(),
                    self.reqExecutionsAsync())
        _logger.info('Synchronization complete')

    async def qualifyContractsAsync(self, *contracts):
        detailsLists = await asyncio.gather(
                *(self.reqContractDetailsAsync(c) for c in contracts))
        result = []
        for contract, detailsList in zip(contracts, detailsLists):
            if not detailsList:
                _logger.error(f'Unknown contract: {contract}')
            elif len(detailsList) > 1:
                possibles = [details.summary for details in detailsList]
                _logger.error(f'Ambiguous contract: {contract}, '
                        f'possibles are {possibles}')
            else:
                details = detailsList[0]
                contract.update(**details.summary.dict())
                result.append(contract)
        return result

    async def reqTickersAsync(self, *contracts, regulatorySnapshot=False):
        futures = []
        for contract in contracts:
            reqId = self.client.getReqId()
            future = self.wrapper.startReq(reqId)
            futures.append(future)
            self.wrapper.startTicker(reqId, contract)
            self.client.reqMktData(reqId, contract, '',
                    True, regulatorySnapshot, [])
        await asyncio.gather(*futures)
        return [self.ticker(c) for c in contracts]

    def whatIfOrderAsync(self, contract, order):
        whatIfOrder = Order(**order.dict()).update(whatIf=True)
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.placeOrder(reqId, contract, whatIfOrder)
        return future

    def reqAccountUpdatesAsync(self,):
        defaultAccount = self.client.getAccounts()[0]
        future = self.wrapper.startReq('accountValues')
        self.client.reqAccountUpdates(True, defaultAccount)
        return future

    def reqAccountSummaryAsync(self):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqAccountSummary(reqId, groupName='All',
                tags=AccountSummaryTags.AllTags)
        return future

    def reqOpenOrdersAsync(self):
        future = self.wrapper.startReq('openOrders')
        self.client.reqOpenOrders()
        return future

    def reqExecutionsAsync(self, execFilter=None):
        execFilter = execFilter or ExecutionFilter()
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqExecutions(reqId, execFilter)
        return future

    def reqPositionsAsync(self):
        future = self.wrapper.startReq('positions')
        self.client.reqPositions()
        return future

    def reqContractDetailsAsync(self, contract):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqContractDetails(reqId, contract)
        return future

    async def reqMatchingSymbolsAsync(self, pattern):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqMatchingSymbols(reqId, pattern)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            _logger.error('reqMatchingSymbolsAsync: Timeout')

    def reqHistoricalDataAsync(self, contract, endDateTime,
            durationStr, barSizeSetting, whatToShow, useRTH,
            formatDate=1, keepUpToDate=False, chartOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        if keepUpToDate:
            self.wrapper.startLiveBars(reqId, historical=True)
        end = util.formatIBDatetime(endDateTime)
        self.client.reqHistoricalData(reqId, contract, end,
                durationStr, barSizeSetting, whatToShow,
                useRTH, formatDate, keepUpToDate, chartOptions)
        return future

    def reqHistoricalTicksAsync(self, contract, startDateTime, endDateTime,
            numberOfTicks, whatToShow, useRth, ignoreSize, miscOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        start = util.formatIBDatetime(startDateTime)
        end = util.formatIBDatetime(endDateTime)
        self.client.reqHistoricalTicks(reqId, contract, start, end,
                numberOfTicks, whatToShow, useRth,
                ignoreSize, miscOptions)
        return future

    def reqHeadTimeStampAsync(self, contract, whatToShow,
            useRTH, formatDate):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqHeadTimeStamp(reqId, contract, whatToShow,
            useRTH, formatDate)
        return future

    def reqMktDepthExchangesAsync(self):
        future = self.wrapper.startReq('mktDepthExchanges')
        self.client.reqMktDepthExchanges()
        return future

    def reqHistogramDataAsync(self, contract, useRTH, period):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqHistogramData(reqId, contract, useRTH, period)
        return future

    def reqFundamentalDataAsync(self, contract, reportType,
            fundamentalDataOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqFundamentalData(reqId, contract, reportType,
                fundamentalDataOptions)
        return future

    async def reqScannerSubscriptionAsync(self, subscription,
            scannerSubscriptionOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqScannerSubscription(reqId, subscription,
                scannerSubscriptionOptions)
        await future
        self.client.cancelScannerSubscription(reqId)
        return future.result()

    def reqScannerParametersAsync(self):
        future = self.wrapper.startReq('scannerParams')
        self.client.reqScannerParameters()
        return future

    async def calculateImpliedVolatilityAsync(self, contract, optionPrice,
            underPrice, implVolOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.calculateImpliedVolatility(reqId, contract, optionPrice,
                underPrice, implVolOptions)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            _logger.error('calculateImpliedVolatilityAsync: Timeout')
            return
        finally:
            self.client.cancelCalculateImpliedVolatility(reqId)

    async def calculateOptionPriceAsync(self, contract, volatility,
            underPrice, optPrcOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.calculateOptionPrice(reqId, contract, volatility,
                underPrice, optPrcOptions)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            _logger.error('calculateOptionPriceAsync: Timeout')
            return
        finally:
            self.client.cancelCalculateOptionPrice(reqId)

    def reqSecDefOptParamsAsync(self, underlyingSymbol,
            futFopExchange, underlyingSecType, underlyingConId):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqSecDefOptParams(reqId, underlyingSymbol,
                futFopExchange, underlyingSecType, underlyingConId)
        return future

    def reqNewsProvidersAsync(self):
        future = self.wrapper.startReq('newsProviders')
        self.client.reqNewsProviders()
        return future

    def reqNewsArticleAsync(self, providerCode, articleId):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqNewsArticle(reqId, providerCode, articleId)
        return future

    async def reqHistoricalNewsAsync(self, conId, providerCodes,
            startDateTime, endDateTime, totalResults,
            _historicalNewsOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        # API does not take historicalNewsOptions parameter
        self.client.reqHistoricalNews(reqId, conId, providerCodes,
            startDateTime, endDateTime, totalResults)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            _logger.error('reqHistoricalNewsAsync: Timeout')

    async def requestFAAsync(self, faDataType):
        future = self.wrapper.startReq('requestFA')
        self.client.requestFA(faDataType)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            _logger.error('requestFAAsync: Timeout')


if __name__ == '__main__':
#     import uvloop
#     asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    from ib_insync.contract import Stock, Forex, Index, Option, Future, CFD
    asyncio.get_event_loop().set_debug(True)
    util.logToConsole(logging.INFO)
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=21)

    aex = Index('EOE', 'FTA')
    eurusd = Forex('EURUSD')
    intc = Stock('INTC', 'SMART', 'USD', primaryExchange='NASDAQ')
    amd = Stock('AMD', 'SMART', 'USD')
    aapl = Stock('AAPL', 'SMART', 'USD')
    tsla = Stock('TSLA', 'SMART', 'USD')
    spy = Stock('SPY', 'ARCA')
    wrongContract = Forex('lalala')
    option = Option('EOE', '20171215', 490, 'P', 'FTA', multiplier=100)

    if 0:
        cds = ib.reqContractDetails(aex)
        print(cds)
        cd = cds[0]
        print(cd)
        conId = cd.summary.conId
        ib.qualifyContracts(aex, eurusd, intc)
        print(aex, eurusd, intc)
        print(ib.reqContractDetails(wrongContract))
    if 0:
        sub = ScannerSubscription(instrument='FUT.US',
                locationCode='FUT.GLOBEX', scanCode='TOP_PERC_GAIN')
        print(ib.reqScannerData(sub, []))
        print(len(ib.reqScannerParameters()))
    if 0:
        print(ib.calculateImpliedVolatility(option,
                optionPrice=6.1, underPrice=525))
        print(ib.calculateOptionPrice(option,
                volatility=0.14, underPrice=525))
    if 0:
        ib.qualifyContracts(amd)
        ticker = ib.reqTickers(amd)
        print(ticker)
    if 0:
        ib.qualifyContracts(aex)
        chains = ib.reqSecDefOptParams(aex.symbol, '', aex.secType, aex.conId)
        chain = next(c for c in chains if c.tradingClass == 'AEX')
        print(chain)
    if 0:
        print(ib.reqContractDetails(aapl))
        bars = ib.reqHistoricalData(
                aapl, '', '1 D', '1 hour', 'MIDPOINT', False, 1, False, None)
        print(len(bars))
        print(bars[0])
    if 0:
        bars = ib.reqHistoricalData(
                aapl, '', '1 D', '1 hour', 'MIDPOINT', False, 1, True, None)
        prevBar = None
        while ib.waitOnUpdate():
            currBar = bars[-1] if bars else None
            if prevBar != currBar:
                prevBar = currBar
                print(currBar)
    if 0:
        ib.reqMktData(tsla, '165,233', False, False, None)
        ib.sleep(20000)
    if 0:
        ib.reqMarketDataType(2)
        print(ib.reqTickers(amd))
        print(ib.reqTickers(eurusd))
        print(ib.reqTickers(amd, eurusd, aex))
    if 0:
        m = ib.reqMatchingSymbols('Intel')
        print(m)
    if 0:
        print(ib.requestFA(1))
    if 0:
        print(ib.reqHeadTimeStamp(intc, 'TRADES', True, 1))
    if 0:
        print(ib.reqFundamentalData(intc, 'ReportsFinSummary'))
    if 0:
        newsProviders = ib.reqNewsProviders()
        print(newsProviders)
        codes = '+'.join(np.code for np in newsProviders)
        ib.qualifyContracts(intc)
        headlines = ib.reqHistoricalNews(intc.conId, codes, "", "", 10)
        latest = headlines[0]
        print(latest)
        article = ib.reqNewsArticle(latest.providerCode, latest.articleId)
        print(article)
    if 0:
        ib.reqNewsBulletins(True)
        ib.sleep(5)
        print(ib.newsBulletins())
    if 0:
        ticker = ib.reqMktDepth(eurusd, 5)
        while ib.sleep(5):
            print([d.price for d in ticker.domBids],
                  [d.price for d in ticker.domAsks])
    if 0:
        order = MarketOrder('BUY', 100)
        state = ib.whatIfOrder(amd, order)
        print(state)
    if 0:
        start = datetime.datetime(2017, 7, 24, 16, 0, 0)
        end = ''
        ticks = ib.reqHistoricalTicks(
                eurusd, start, end, 100, 'MIDPOINT', True, False, [])
        print(ticks)
    if 0:
        start = datetime.time(10, 10, 10)
        end = datetime.time(14, 13)
        for t in ib.timeRange(start, end, 5):
            print(t)
    if 0:
        histo = ib.reqHistogramData(amd, True, '1 week')
        print(histo)

    # ib.disconnect()
