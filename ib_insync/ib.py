import asyncio
import logging
import datetime
import time
from contextlib import suppress
from typing import List, Iterator, Awaitable, Union

from eventkit import Event

import ib_insync.util as util
from ib_insync.client import Client
from ib_insync.wrapper import Wrapper
from ib_insync.contract import Contract
from ib_insync.ticker import Ticker
from ib_insync.order import Order, OrderStatus, Trade, LimitOrder, StopOrder
from ib_insync.objects import (
    BarList, BarDataList, RealTimeBarList,
    AccountValue, PortfolioItem, Position, Fill, Execution, BracketOrder,
    TradeLogEntry, OrderState, ExecutionFilter, TagValue, PnL, PnLSingle,
    ContractDetails, ContractDescription, OptionChain, OptionComputation,
    NewsTick, NewsBulletin, NewsArticle, NewsProvider, HistoricalNews,
    ScannerSubscription, ScanDataList, HistogramData, PriceIncrement,
    DepthMktDataDescription)

__all__ = ['IB']


class IB:
    """
    Provides both a blocking and an asynchronous interface
    to the IB API, using asyncio networking and event loop.

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
    :meth:`.sleep` instead.

    Attributes:
        RequestTimeout (float): Timeout (in seconds) to wait for a request
          to finish before raising ``asyncio.TimeoutError``.
          The default value of 0 will wait indefinitely.

    Events:
        * ``connectedEvent`` ():
          Is emitted after connecting and synchronzing with TWS/gateway.

        * ``disconnectedEvent`` ():
          Is emitted after disconnecting from TWS/gateway.

        * ``updateEvent`` ():
          Is emitted after a network packet has been handeled.

        * ``pendingTickersEvent`` (tickers: Set[:class:`.Ticker`]):
          Emits the set of tickers that have been updated during the last
          update and for which there are new ticks, tickByTicks or domTicks.

        * ``barUpdateEvent`` (bars: :class:`.BarDataList`,
          hasNewBar: bool): Emits the bar list that has been updated in
          real time. If a new bar has been added then hasNewBar is True,
          when the last bar has changed it is False.

        * ``newOrderEvent`` (trade: :class:`.Trade`):
          Emits a newly placed trade.

        * ``orderModifyEvent`` (trade: :class:`.Trade`):
          Emits when order is modified.

        * ``cancelOrderEvent`` (trade: :class:`.Trade`):
          Emits a trade directly after requesting for it to be cancelled.

        * ``openOrderEvent`` (trade: :class:`.Trade`):
          Emits the trade with open order.

        * ``orderStatusEvent`` (trade: :class:`.Trade`):
          Emits the changed order status of the ongoing trade.

        * ``execDetailsEvent`` (trade: :class:`.Trade`, fill: :class:`.Fill`):
          Emits the fill together with the ongoing trade it belongs to.

        * ``commissionReportEvent`` (trade: :class:`.Trade`,
          fill: :class:`.Fill`, report: :class:`.CommissionReport`):
          The commission report is emitted after the fill that it belongs to.

        * ``updatePortfolioEvent`` (item: :class:`.PortfolioItem`):
          A portfolio item has changed.

        * ``positionEvent`` (position: :class:`.Position`):
          A position has changed.

        * ``accountValueEvent`` (value: :class:`.AccountValue`):
          An account value has changed.

        * ``accountSummaryEvent`` (value: :class:`.AccountValue`):
          An account value has changed.

        * ``pnlEvent`` (entry: :class:`.PnL`):
          A profit- and loss entry is updated.

        * ``pnlSingleEvent`` (entry: :class:`.PnLSingle`):
          A profit- and loss entry for a single position is updated.

        * ``tickNewsEvent`` (news: :class:`.NewsTick`):
          Emit a new news headline.

        * ``newsBulletinEvent`` (bulletin: :class:`.NewsBulletin`):
          Emit a new news bulletin.

        * ``scannerDataEvent`` (data: :class:`.ScanDataList`):
          Emit data from a scanner subscription.

        * ``errorEvent`` (reqId: int, errorCode: int, errorString: str,
          contract: :class:`.Contract`):
          Emits the reqId/orderId and TWS error code and string (see
          https://interactivebrokers.github.io/tws-api/message_codes.html)
          together with the contract the error applies to (or None if no
          contract applies).

        * ``timeoutEvent`` (idlePeriod: float):
          Is emitted if no data is received for longer than the timeout period
          specified with :meth:`.setTimeout`. The value emitted is the period
          in seconds since the last update.

        Note that it is not advisable to place new requests inside an event
        handler as it may lead to too much recursion.
    """

    events = (
        'connectedEvent', 'disconnectedEvent', 'updateEvent',
        'pendingTickersEvent', 'barUpdateEvent',
        'newOrderEvent', 'orderModifyEvent', 'cancelOrderEvent',
        'openOrderEvent', 'orderStatusEvent',
        'execDetailsEvent', 'commissionReportEvent',
        'updatePortfolioEvent', 'positionEvent', 'accountValueEvent',
        'accountSummaryEvent', 'pnlEvent', 'pnlSingleEvent',
        'scannerDataEvent', 'tickNewsEvent', 'newsBulletinEvent',
        'errorEvent', 'timeoutEvent')

    RequestTimeout = 0

    def __init__(self):
        Event.init(self, IB.events)
        self.wrapper = Wrapper(self)
        self.client = Client(self.wrapper)
        self.client.apiEnd += self.disconnectedEvent
        self._logger = logging.getLogger('ib_insync.ib')

    def __del__(self):
        self.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.disconnect()

    def __repr__(self):
        conn = (f'connected to {self.client.host}:'
                f'{self.client.port} clientId={self.client.clientId}' if
                self.client.isConnected() else 'not connected')
        return f'<{self.__class__.__qualname__} {conn}>'

    def connect(
            self, host: str = '127.0.0.1', port: int = 7497,
            clientId: int = 1, timeout: float = 2):
        """
        Connect to a running TWS or IB gateway application.
        After the connection is made the client is fully synchronized
        and ready to serve requests.

        This method is blocking.

        Args:
            host: Host name or IP address.
            port: Port number.
            clientId: ID number to use for this client; must be unique per
                connection. Setting clientId=0 will automatically merge manual
                TWS trading with this client.
            timeout: If establishing the connection takes longer than
                ``timeout`` seconds then the ``asyncio.TimeoutError`` exception
                is raised. Set to 0 to disable timeout.
        """
        return self._run(self.connectAsync(host, port, clientId, timeout))

    def disconnect(self):
        """
        Disconnect from a TWS or IB gateway application.
        This will clear all session state.
        """
        if not self.client.isConnected():
            return
        stats = self.client.connectionStats()
        self._logger.info(
            f'Disconnecting from {self.client.host}:{self.client.port}, '
            f'{util.formatSI(stats.numBytesSent)}B sent '
            f'in {stats.numMsgSent} messages, '
            f'{util.formatSI(stats.numBytesRecv)}B received '
            f'in {stats.numMsgRecv} messages, '
            f'session time {util.formatSI(stats.duration)}s.')
        self.client.disconnect()

    def isConnected(self) -> bool:
        """
        Is there is an API connection to TWS or IB gateway?
        """
        return self.client.isConnected()

    run = staticmethod(util.run)
    schedule = staticmethod(util.schedule)
    sleep = staticmethod(util.sleep)
    timeRange = staticmethod(util.timeRange)
    timeRangeAsync = staticmethod(util.timeRangeAsync)
    waitUntil = staticmethod(util.waitUntil)

    def _run(self, *awaitables: List[Awaitable]):
        return util.run(*awaitables, timeout=self.RequestTimeout)

    def waitOnUpdate(self, timeout: float = 0) -> bool:
        """
        Wait on any new update to arrive from the network.

        Args:
            timeout: Maximum time in seconds to wait.
                If 0 then no timeout is used.

        .. note::
            A loop with ``waitOnUpdate`` should not be used to harvest
            tick data from tickers, since some ticks can go missing.
            This happens when multiple updates occur almost simultaneously;
            The ticks from the first update are then cleared.
            Use events instead to prevent this.
        """
        if timeout:
            with suppress(asyncio.TimeoutError):
                util.run(asyncio.wait_for(self.updateEvent, timeout))
        else:
            util.run(self.updateEvent)
        return True

    def loopUntil(
            self, condition=None, timeout: float = 0) -> Iterator[object]:
        """
        Iterate until condition is met, with optional timeout in seconds.
        The yielded value is that of the condition or False when timed out.

        Args:
            condition: Predicate function that is tested after every network
            update.
            timeout: Maximum time in seconds to wait.
                If 0 then no timeout is used.
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
            self.waitOnUpdate(endTime - time.time() if timeout else 0)

    def setTimeout(self, timeout: float = 60):
        """
        Set a timeout for receiving messages from TWS/IBG, emitting
        ``timeoutEvent`` if there is no incoming data for too long.

        The timeout fires once per connected session but can be set again
        after firing or after a reconnect.

        Args:
            timeout: Timeout in seconds.
        """
        self.wrapper.setTimeout(timeout)

    def managedAccounts(self) -> List[str]:
        """
        List of account names.
        """
        return list(self.wrapper.accounts)

    def accountValues(self, account: str = '') -> List[AccountValue]:
        """
        List of account values for the given account,
        or of all accounts if account is left blank.

        Args:
            account: If specified, filter for this account name.
        """
        if account:
            return [v for v in self.wrapper.accountValues.values()
                    if v.account == account]
        else:
            return list(self.wrapper.accountValues.values())

    def accountSummary(self, account: str = '') -> List[AccountValue]:
        """
        List of account values for the given account,
        or of all accounts if account is left blank.

        This method is blocking on first run, non-blocking after that.

        Args:
            account: If specified, filter for this account name.
        """
        if not self.wrapper.acctSummary:
            # loaded on demand since it takes ca. 250 ms
            self.reqAccountSummary()
        if account:
            return [v for v in self.wrapper.acctSummary.values()
                    if v.account == account]
        else:
            return list(self.wrapper.acctSummary.values())

    def portfolio(self) -> List[PortfolioItem]:
        """
        List of portfolio items of the default account.
        """
        account = self.wrapper.accounts[0]
        return [v for v in self.wrapper.portfolio[account].values()]

    def positions(self, account: str = '') -> List[Position]:
        """
        List of positions for the given account,
        or of all accounts if account is left blank.

        Args:
            account: If specified, filter for this account name.
        """
        if account:
            return list(self.wrapper.positions[account].values())
        else:
            return [v for d in self.wrapper.positions.values()
                    for v in d.values()]

    def pnl(self, account='', modelCode='') -> List[PnL]:
        """
        List of subscribed :class:`.PnL` objects (profit and loss),
        optionally filtered by account and/or modelCode.

        The :class:`.PnL` objects are kept live updated.

        Args:
            account: If specified, filter for this account name.
            modelCode: If specified, filter for this account model.
        """
        return [v for v in self.wrapper.pnls.values() if
                (not account or v.account == account) and
                (not modelCode or v.modelCode == modelCode)]

    def pnlSingle(
            self, account: str = '', modelCode: str = '',
            conId: int = 0) -> List[PnLSingle]:
        """
        List of subscribed :class:`.PnLSingle` objects (profit and loss for
        single positions).

        The :class:`.PnLSingle` objects are kept live updated.

        Args:
            account: If specified, filter for this account name.
            modelCode: If specified, filter for this account model.
            conId: If specified, filter for this contract ID.
        """
        return [v for v in self.wrapper.pnlSingles.values() if
                (not account or v.account == account) and
                (not modelCode or v.modelCode == modelCode) and
                (not conId or v.conId == conId)]

    def trades(self) -> List[Trade]:
        """
        List of all order trades from this session.
        """
        return list(self.wrapper.trades.values())

    def openTrades(self) -> List[Trade]:
        """
        List of all open order trades.
        """
        return [v for v in self.wrapper.trades.values()
                if v.orderStatus.status not in OrderStatus.DoneStates]

    def orders(self) -> List[Order]:
        """
        List of all orders from this session.
        """
        return list(
            trade.order for trade in self.wrapper.trades.values())

    def openOrders(self) -> List[Order]:
        """
        List of all open orders.
        """
        return [trade.order for trade in self.wrapper.trades.values()
                if trade.orderStatus.status not in OrderStatus.DoneStates]

    def fills(self) -> List[Fill]:
        """
        List of all fills from this session.
        """
        return list(self.wrapper.fills.values())

    def executions(self) -> List[Execution]:
        """
        List of all executions from this session.
        """
        return list(fill.execution for fill in self.wrapper.fills.values())

    def ticker(self, contract: Contract) -> Ticker:
        """
        Get ticker of the given contract. It must have been requested before
        with reqMktData with the same contract object. The ticker may not be
        ready yet if called directly after :meth:`.reqMktData`.

        Args:
            contract: Contract to get ticker for.
        """
        return self.wrapper.tickers.get(id(contract))

    def tickers(self) -> List[Ticker]:
        """
        Get a list of all tickers.
        """
        return list(self.wrapper.tickers.values())

    def pendingTickers(self) -> List[Ticker]:
        """
        Get a list of all tickers that have pending ticks or domTicks.
        """
        return list(self.wrapper.pendingTickers)

    def realtimeBars(self) -> BarList:
        """
        Get a list of all live updated bars. These can be 5 second realtime
        bars or live updated historical bars.
        """
        return list(self.wrapper.reqId2Subscriber.values())

    def newsTicks(self) -> List[NewsTick]:
        """
        List of ticks with headline news.
        The article itself can be retrieved with :meth:`.reqNewsArticle`.
        """
        return self.wrapper.newsTicks

    def newsBulletins(self) -> List[NewsBulletin]:
        """
        List of IB news bulletins.
        """
        return list(self.wrapper.newsBulletins.values())

    def reqTickers(
            self, *contracts: List[Contract],
            regulatorySnapshot: bool = False) -> List[Ticker]:
        """
        Request and return a list of snapshot tickers.
        The list is returned when all tickers are ready.

        This method is blocking.

        Args:
            contracts: Contracts to get tickers for.
            regulatorySnapshot: Request NBBO snapshots (may incur a fee).
        """
        return self._run(
            self.reqTickersAsync(
                *contracts, regulatorySnapshot=regulatorySnapshot))

    def qualifyContracts(self, *contracts: List[Contract]) -> List[Contract]:
        """
        Fully qualify the given contracts in-place. This will fill in
        the missing fields in the contract, especially the conId.

        Returns a list of contracts that have been successfully qualified.

        This method is blocking.

        Args:
            contracts: Contracts to qualify.
        """
        return self._run(self.qualifyContractsAsync(*contracts))

    def bracketOrder(
            self, action: str, quantity: float,
            limitPrice: float, takeProfitPrice: float,
            stopLossPrice: float, **kwargs) -> BracketOrder:
        """
        Create a limit order that is bracketed by a take-profit order and
        a stop-loss order. Submit the bracket like:

        .. code-block:: python

            for o in bracket:
                ib.placeOrder(contract, o)

        https://interactivebrokers.github.io/tws-api/bracket_order.html

        Args:
            action: 'BUY' or 'SELL'.
            quantity: Size of order.
            limitPrice: Limit price of entry order.
            takeProfitPrice: Limit price of profit order.
            stopLossPrice: Stop price of loss order.
        """
        assert action in ('BUY', 'SELL')
        reverseAction = 'BUY' if action == 'SELL' else 'SELL'
        parent = LimitOrder(
            action, quantity, limitPrice,
            orderId=self.client.getReqId(),
            transmit=False,
            **kwargs)
        takeProfit = LimitOrder(
            reverseAction, quantity, takeProfitPrice,
            orderId=self.client.getReqId(),
            transmit=False,
            parentId=parent.orderId,
            **kwargs)
        stopLoss = StopOrder(
            reverseAction, quantity, stopLossPrice,
            orderId=self.client.getReqId(),
            transmit=True,
            parentId=parent.orderId,
            **kwargs)
        return BracketOrder(parent, takeProfit, stopLoss)

    @staticmethod
    def oneCancelsAll(
            orders: List[Order], ocaGroup: str, ocaType: int) -> List[Order]:
        """
        Place the trades in the same One Cancels All (OCA) group.

        https://interactivebrokers.github.io/tws-api/oca.html

        Args:
            orders: The orders that are to be placed together.
        """
        for o in orders:
            o.ocaGroup = ocaGroup
            o.ocaType = ocaType
        return orders

    def whatIfOrder(self, contract: Contract, order: Order) -> OrderState:
        """
        Retrieve commission and margin impact without actually
        placing the order. The given order will not be modified in any way.

        This method is blocking.

        Args:
            contract: Contract to test.
            order: Order to test.
        """
        return self._run(self.whatIfOrderAsync(contract, order))

    def placeOrder(self, contract: Contract, order: Order) -> Trade:
        """
        Place a new order or modify an existing order.
        Returns a Trade that is kept live updated with
        status changes, fills, etc.

        Args:
            contract: Contract to use for order.
            order: The order to be placed.
        """
        orderId = order.orderId or self.client.getReqId()
        self.client.placeOrder(orderId, contract, order)
        now = datetime.datetime.now(datetime.timezone.utc)
        key = self.wrapper.orderKey(
            self.wrapper.clientId, orderId, order.permId)
        trade = self.wrapper.trades.get(key)
        if trade:
            # this is a modification of an existing order
            assert trade.orderStatus.status not in OrderStatus.DoneStates
            logEntry = TradeLogEntry(now, trade.orderStatus.status, 'Modify')
            trade.log.append(logEntry)
            self._logger.info(f'placeOrder: Modify order {trade}')
            trade.modifyEvent.emit(trade)
            self.orderModifyEvent.emit(trade)
        else:
            # this is a new order
            order.clientId = self.wrapper.clientId
            order.orderId = orderId
            orderStatus = OrderStatus(status=OrderStatus.PendingSubmit)
            logEntry = TradeLogEntry(now, orderStatus.status, '')
            trade = Trade(
                contract, order, orderStatus, [], [logEntry])
            self.wrapper.trades[key] = trade
            self._logger.info(f'placeOrder: New order {trade}')
            self.newOrderEvent.emit(trade)
        return trade

    def cancelOrder(self, order: Order) -> Trade:
        """
        Cancel the order and return the Trade it belongs to.

        Args:
            order: The order to be canceled.
        """
        self.client.cancelOrder(order.orderId)
        now = datetime.datetime.now(datetime.timezone.utc)
        key = self.wrapper.orderKey(
            order.clientId, order.orderId, order.permId)
        trade = self.wrapper.trades.get(key)
        if trade:
            if not trade.isDone():
                status = trade.orderStatus.status
                if (status == OrderStatus.PendingSubmit and not order.transmit
                        or status == OrderStatus.Inactive):
                    newStatus = OrderStatus.Cancelled
                else:
                    newStatus = OrderStatus.PendingCancel
                logEntry = TradeLogEntry(now, newStatus, '')
                trade.log.append(logEntry)
                trade.orderStatus.status = newStatus
                self._logger.info(f'cancelOrder: {trade}')
                trade.cancelEvent.emit(trade)
                trade.statusEvent.emit(trade)
                self.cancelOrderEvent.emit(trade)
                self.orderStatusEvent.emit(trade)
                if newStatus == OrderStatus.Cancelled:
                    trade.cancelledEvent.emit(trade)
        else:
            self._logger.error(f'cancelOrder: Unknown orderId {order.orderId}')
        return trade

    def reqGlobalCancel(self):
        """
        Cancel all active trades including those placed by other
        clients or TWS/IB gateway.
        """
        self.client.reqGlobalCancel()
        self._logger.info(f'reqGlobalCancel')

    def reqCurrentTime(self) -> datetime.datetime:
        """
        Request TWS current time.

        This method is blocking.
        """
        return self._run(self.reqCurrentTimeAsync())

    def reqAccountUpdates(self, account: str = ''):
        """
        This is called at startup - no need to call again.

        Request account and portfolio values of the account
        and keep updated. Returns when both account values and portfolio
        are filled.

        This method is blocking.

        Args:
            account: If specified, filter for this account name.
        """
        self._run(self.reqAccountUpdatesAsync(account))

    def reqAccountUpdatesMulti(
            self, account: str = '', modelCode: str = ''):
        """
        It is recommended to use :meth:`.accountValues` instead.

        Request account values of multiple accounts and keep updated.

        This method is blocking.

        Args:
            account: If specified, filter for this account name.
            modelCode: If specified, filter for this account model.
        """
        self._run(self.reqAccountUpdatesMultiAsync(account, modelCode))

    def reqAccountSummary(self):
        """
        It is recommended to use :meth:`.accountSummary` instead.

        Request account values for all accounts and keep them updated.
        Returns when account summary is filled.

        This method is blocking.
        """
        self._run(self.reqAccountSummaryAsync())

    def reqAutoOpenOrders(self, autoBind: bool = True):
        """
        Bind manual TWS orders so that they can be managed from this client.
        The clientId must be 0 and the TWS API setting "Use negative numbers
        to bind automatic orders" must be checked.

        This request is automatically called when clientId=0.

        https://interactivebrokers.github.io/tws-api/open_orders.html
        https://interactivebrokers.github.io/tws-api/modifying_orders.html

        Args:
            autoBind: Set binding on or off.
        """
        self.client.reqAutoOpenOrders(autoBind)

    def reqOpenOrders(self) -> List[Order]:
        """
        Request and return a list a list of open orders.

        This method can give stale information where a new open order is not
        reported or an already filled or cancelled order is reported as open.
        It is recommended to use the more reliable and much faster
        :meth:`.openTrades` or :meth:`.openOrders` methods instead.

        This method is blocking.
        """
        return self._run(self.reqOpenOrdersAsync())

    def reqAllOpenOrders(self) -> List[Order]:
        """
        Request and return a list of all open orders over all clients.
        Note that the orders of other clients will not be kept in sync,
        use the master clientId mechanism instead to see other
        client's orders that are kept in sync.
        """
        return self._run(self.reqAllOpenOrdersAsync())

    def reqExecutions(
            self, execFilter: ExecutionFilter = None) -> List[Fill]:
        """
        It is recommended to use :meth:`.fills`  or
        :meth:`.executions` instead.

        Request and return a list a list of fills.

        This method is blocking.

        Args:
            execFilter: If specified, return executions that match the filter.
        """
        return self._run(self.reqExecutionsAsync(execFilter))

    def reqPositions(self) -> List[Position]:
        """
        It is recommended to use :meth:`.positions` instead.

        Request and return a list of positions for all accounts.

        This method is blocking.
        """
        return self._run(self.reqPositionsAsync())

    def reqPnL(self, account: str, modelCode: str = '') -> PnL:
        """
        Start a subscription for profit and loss events.

        Returns a :class:`.PnL` object that is kept live updated.
        The result can also be queried from :meth:`.pnl`.

        https://interactivebrokers.github.io/tws-api/pnl.html

        Args:
            account: Subscribe to this account.
            modelCode: If specified, filter for this account model.
        """
        key = (account, modelCode)
        assert key not in self.wrapper.pnlKey2ReqId
        reqId = self.client.getReqId()
        self.wrapper.pnlKey2ReqId[key] = reqId
        pnl = PnL(account, modelCode)
        self.wrapper.pnls[reqId] = pnl
        self.client.reqPnL(reqId, account, modelCode)
        return pnl

    def cancelPnL(self, account, modelCode: str = ''):
        """
        Cancel PnL subscription.

        Args:
            account: Cancel for this account.
            modelCode: If specified, cancel for this account model.
        """
        key = (account, modelCode)
        reqId = self.wrapper.pnlKey2ReqId.pop(key, None)
        if reqId:
            self.client.cancelPnL(reqId)
            self.wrapper.pnls.pop(reqId, None)
        else:
            self._logger.error(
                'cancelPnL: No subscription for '
                f'account {account}, modelCode {modelCode}')

    def reqPnLSingle(
            self, account: str, modelCode: str, conId: int) -> PnLSingle:
        """
        Start a subscription for profit and loss events for single positions.

        Returns a :class:`.PnLSingle` object that is kept live updated.
        The result can also be queried from :meth:`.pnlSingle`.

        https://interactivebrokers.github.io/tws-api/pnl.html

        Args:
            account: Subscribe to this account.
            modelCode: Filter for this account model.
            conId: Filter for this contract ID.
        """
        key = (account, modelCode, conId)
        assert key not in self.wrapper.pnlSingleKey2ReqId
        reqId = self.client.getReqId()
        self.wrapper.pnlSingleKey2ReqId[key] = reqId
        pnlSingle = PnLSingle(account, modelCode, conId)
        self.wrapper.pnlSingles[reqId] = pnlSingle
        self.client.reqPnLSingle(reqId, account, modelCode, conId)
        return pnlSingle

    def cancelPnLSingle(
            self, account: str, modelCode: str, conId: int):
        """
        Cancel PnLSingle subscription for the given account, modelCode
        and conId.

        Args:
            account: Cancel for this account name.
            modelCode: Cancel for this account model.
            conId: Cancel for this contract ID.
        """
        key = (account, modelCode, conId)
        reqId = self.wrapper.pnlSingleKey2ReqId.pop(key, None)
        if reqId:
            self.client.cancelPnLSingle(reqId)
            self.wrapper.pnlSingles.pop(reqId, None)
        else:
            self._logger.error(
                'cancelPnLSingle: No subscription for '
                f'account {account}, modelCode {modelCode}, conId {conId}')

    def reqContractDetails(self, contract: Contract) -> List[ContractDetails]:
        """
        Get a list of contract details that match the given contract.
        If the returned list is empty then the contract is not known;
        If the list has multiple values then the contract is ambiguous.

        The fully qualified contract is available in the the
        ContractDetails.contract attribute.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/contract_details.html

        Args:
            contract: The contract to get details for.
        """
        return self._run(self.reqContractDetailsAsync(contract))

    def reqMatchingSymbols(self, pattern: str) -> List[ContractDescription]:
        """
        Request contract descriptions of contracts that match a pattern.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/matching_symbols.html

        Args:
            pattern: The first few letters of the ticker symbol, or for
                longer strings a character sequence matching a word in
                the security name.
        """
        return self._run(self.reqMatchingSymbolsAsync(pattern))

    def reqMarketRule(self, marketRuleId: int) -> PriceIncrement:
        """
        Request price increments rule.

        https://interactivebrokers.github.io/tws-api/minimum_increment.html

        Args:
            marketRuleId: ID of market rule.
                The market rule IDs for a contract can be obtained
                via :meth:`.reqContractDetails` from
                :class:`.ContractDetails`.marketRuleIds,
                which contains a comma separated string of market rule IDs.
        """
        return self._run(self.reqMarketRuleAsync(marketRuleId))

    def reqRealTimeBars(
            self, contract: Contract, barSize: int,
            whatToShow: str, useRTH: bool,
            realTimeBarsOptions: List[TagValue] = None) -> RealTimeBarList:
        """
        Request realtime 5 second bars.

        https://interactivebrokers.github.io/tws-api/realtime_bars.html

        Args:
            contract: Contract of interest.
            barSize: Must be 5.
            whatToShow: Specifies the source for constructing bars.
                Can be 'TRADES', 'MIDPOINT', 'BID' or 'ASK'.
            useRTH: If True then only show data from within Regular
                Trading Hours, if False then show all data.
            realTimeBarsOptions: Unknown.
        """
        reqId = self.client.getReqId()
        bars = RealTimeBarList()
        bars.reqId = reqId
        bars.contract = contract
        bars.barSize = barSize
        bars.whatToShow = whatToShow
        bars.useRTH = useRTH
        bars.realTimeBarsOptions = realTimeBarsOptions
        self.wrapper.startSubscription(reqId, bars, contract)
        self.client.reqRealTimeBars(
            reqId, contract, barSize, whatToShow, useRTH, realTimeBarsOptions)
        return bars

    def cancelRealTimeBars(self, bars: RealTimeBarList):
        """
        Cancel the realtime bars subscription.

        Args:
            bars: The bar list that was obtained from ``reqRealTimeBars``.
        """
        self.client.cancelRealTimeBars(bars.reqId)
        self.wrapper.endSubscription(bars)

    def reqHistoricalData(
            self, contract: Contract, endDateTime: object,
            durationStr: str, barSizeSetting: str,
            whatToShow: str, useRTH: bool,
            formatDate: int = 1, keepUpToDate: bool = False,
            chartOptions: List[TagValue] = None) -> BarDataList:
        """
        Request historical bar data.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/historical_bars.html

        Args:
            contract: Contract of interest.
            endDateTime: Can be set to '' to indicate the current time,
                or it can be given as a datetime.date or datetime.datetime,
                or it can be given as a string in 'yyyyMMdd HH:mm:ss' format.
                If no timezone is given then the TWS login timezone is used.
            durationStr: Time span of all the bars. Examples:
                '60 S', '30 D', '13 W', '6 M', '10 Y'.
            barSizeSetting: Time period of one bar. Must be one of:
                '1 secs', '5 secs', '10 secs' 15 secs', '30 secs',
                '1 min', '2 mins', '3 mins', '5 mins', '10 mins', '15 mins',
                '20 mins', '30 mins',
                '1 hour', '2 hours', '3 hours', '4 hours', '8 hours',
                '1 day', '1 week', '1 month'.
            whatToShow: Specifies the source for constructing bars.
                Must be one of:
                'TRADES', 'MIDPOINT', 'BID', 'ASK', 'BID_ASK',
                'ADJUSTED_LAST', 'HISTORICAL_VOLATILITY',
                'OPTION_IMPLIED_VOLATILITY', 'REBATE_RATE', 'FEE_RATE',
                'YIELD_BID', 'YIELD_ASK', 'YIELD_BID_ASK', 'YIELD_LAST'.
            useRTH: If True then only show data from within Regular
                Trading Hours, if False then show all data.
            formatDate: For an intraday request setting to 2 will cause
                the returned date fields to be timezone-aware
                datetime.datetime with UTC timezone, instead of local timezone
                as used by TWS.
            keepUpToDate: If True then a realtime subscription is started
                to keep the bars updated; ``endDateTime`` must be set
                empty ('') then.
            chartOptions: Unknown.
        """
        return self._run(
            self.reqHistoricalDataAsync(
                contract, endDateTime, durationStr, barSizeSetting, whatToShow,
                useRTH, formatDate, keepUpToDate, chartOptions))

    def cancelHistoricalData(self, bars: BarDataList):
        """
        Cancel the update subscription for the historical bars.

        Args:
            bars: The bar list that was obtained from ``reqHistoricalData``
                with a keepUpToDate subscription.

        """
        self.client.cancelHistoricalData(bars.reqId)
        self.wrapper.endSubscription(bars)

    def reqHistoricalTicks(
            self, contract: Contract,
            startDateTime: Union[str, datetime.date],
            endDateTime: Union[str, datetime.date],
            numberOfTicks: int, whatToShow: str, useRth: bool,
            ignoreSize: bool = False,
            miscOptions: List[TagValue] = None) -> List:
        """
        Request historical ticks. The time resolution of the ticks
        is one second.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/historical_time_and_sales.html

        Args:
            contract: Contract to query.
            startDateTime: Can be given as a datetime.date or
                datetime.datetime, or it can be given as a string in
                'yyyyMMdd HH:mm:ss' format.
                If no timezone is given then the TWS login timezone is used.
            endDateTime: One of ``startDateTime`` or ``endDateTime`` can
                be given, the other must be blank.
            numberOfTicks: Number of ticks to request (1000 max). The actual
                result can contain a bit more to accommodate all ticks in
                the latest second.
            whatToShow: One of 'Bid_Ask', 'Midpoint' or 'Trades'.
            useRTH: If True then only show data from within Regular
                Trading Hours, if False then show all data.
            ignoreSize: Ignore bid/ask ticks that only update the size.
            miscOptions: Unknown.
        """
        return self._run(
            self.reqHistoricalTicksAsync(
                contract, startDateTime, endDateTime, numberOfTicks,
                whatToShow, useRth, ignoreSize, miscOptions))

    def reqMarketDataType(self, marketDataType: int):
        """
        Set the market data type used throughout.

        Args:
            marketDataType: One of:

                * 1 = Live
                * 2 = Frozen
                * 3 = Delayed
                * 4 = Delayed frozen

        https://interactivebrokers.github.io/tws-api/market_data_type.html
        """
        self.client.reqMarketDataType(marketDataType)

    def reqHeadTimeStamp(
            self, contract: Contract, whatToShow: str,
            useRTH: bool, formatDate: int = 1) -> datetime.datetime:
        """
        Get the datetime of earliest available historical data
        for the contract.

        Args:
            contract: Contract of interest.
            useRTH: If True then only show data from within Regular
                Trading Hours, if False then show all data.
            formatDate: If set to 2 then the result is returned as a
                timezone-aware datetime.datetime with UTC timezone.
        """
        return self._run(
            self.reqHeadTimeStampAsync(
                contract, whatToShow, useRTH, formatDate))

    def reqMktData(
            self, contract: Contract, genericTickList: str = '',
            snapshot: bool = False, regulatorySnapshot: bool = False,
            mktDataOptions: List[TagValue] = None) -> Ticker:
        """
        Subscribe to tick data or request a snapshot.
        Returns the Ticker that holds the market data. The ticker will
        initially be empty and gradually (after a couple of seconds)
        be filled.

        https://interactivebrokers.github.io/tws-api/md_request.html

        Args:
            contract: Contract of interest.
            genericTickList: Comma separated IDs of desired
                generic ticks that will cause corresponding Ticker fields
                to be filled:

                =====  ================================================
                ID     Ticker fields
                =====  ================================================
                100    ``putVolume``, ``callVolume`` (for options)
                101    ``putOpenInterest``, ``callOpenInterest`` (for options)
                104    ``histVolatility`` (for options)
                105    ``avOptionVolume`` (for options)
                106    ``impliedVolatility`` (for options)
                162    ``indexFuturePremium``
                165    ``low13week``, ``high13week``, ``low26week``,
                       ``high26week``, ``low52week``, ``high52week``,
                       ``avVolume``
                221    ``markPrice``
                233    ``last``, ``lastSize``, ``rtVolume``, ``vwap``
                       (Time & Sales)
                236    ``shortableShares``
                258    ``fundamentalRatios`` (of type
                       :class:`ib_insync.objects.FundamentalRatios`)
                293    ``tradeCount``
                294    ``tradeRate``
                295    ``volumeRate``
                411    ``rtHistVolatility``
                456    ``dividends`` (of type
                       :class:`ib_insync.objects.Dividends`)
                588    ``futuresOpenInterest``
                =====  ================================================

            snapshot: If True then request a one-time snapshot, otherwise
                subscribe to a stream of realtime tick data.
            regulatorySnapshot: Request NBBO snapshot (may incur a fee).
            mktDataOptions: Unknown
        """
        reqId = self.client.getReqId()
        ticker = self.wrapper.startTicker(reqId, contract, 'mktData')
        self.client.reqMktData(
            reqId, contract, genericTickList, snapshot,
            regulatorySnapshot, mktDataOptions)
        return ticker

    def cancelMktData(self, contract: Contract):
        """
        Unsubscribe from realtime streaming tick data.

        Args:
            contract: The exact contract object that was used to
                subscribe with.
        """
        ticker = self.ticker(contract)
        reqId = self.wrapper.endTicker(ticker, 'mktData')
        if reqId:
            self.client.cancelMktData(reqId)
        else:
            self._logger.error(
                'cancelMktData: ' f'No reqId found for contract {contract}')

    def reqTickByTickData(
            self, contract: Contract, tickType: str,
            numberOfTicks: int = 0, ignoreSize: bool = False) -> Ticker:
        """
        Subscribe to tick-by-tick data and return the Ticker that
        holds the ticks in ticker.tickByTicks.

        https://interactivebrokers.github.io/tws-api/tick_data.html

        Args:
            contract: Contract of interest.
            tickType: One of  'Last', 'AllLast', 'BidAsk' or 'MidPoint'.
            numberOfTicks: Number of ticks or 0 for unlimited.
            ignoreSize: Ignore bid/ask ticks that only update the size.
        """
        reqId = self.client.getReqId()
        ticker = self.wrapper.startTicker(reqId, contract, tickType)
        self.client.reqTickByTickData(
            reqId, contract, tickType, numberOfTicks, ignoreSize)
        return ticker

    def cancelTickByTickData(self, contract: Contract, tickType: str):
        """
        Unsubscribe from tick-by-tick data

        Args:
            contract: The exact contract object that was used to
                subscribe with.
        """
        ticker = self.ticker(contract)
        reqId = self.wrapper.endTicker(ticker, tickType)
        if reqId:
            self.client.cancelTickByTickData(reqId)
        else:
            self._logger.error(
                f'cancelMktData: No reqId found for contract {contract}')

    def reqMktDepthExchanges(self) -> List[DepthMktDataDescription]:
        """
        Get those exchanges that have have multiple market makers
        (and have ticks returned with marketMaker info).
        """
        return self._run(self.reqMktDepthExchangesAsync())

    def reqMktDepth(
            self, contract: Contract, numRows: int = 5,
            isSmartDepth: bool = False, mktDepthOptions=None) -> Ticker:
        """
        Subscribe to market depth data (a.k.a. DOM, L2 or order book).

        https://interactivebrokers.github.io/tws-api/market_depth.html

        Args:
            contract: Contract of interest.
            numRows: Number of depth level on each side of the order book
                (5 max).
            isSmartDepth: Consolidate the order book across exchanges.
            mktDepthOptions: Unknown.

        Returns:
            The Ticker that holds the market depth in ``ticker.domBids``
            and ``ticker.domAsks`` and the list of MktDepthData in
            ``ticker.domTicks``.
        """
        reqId = self.client.getReqId()
        ticker = self.wrapper.startTicker(reqId, contract, 'mktDepth')
        self.client.reqMktDepth(
            reqId, contract, numRows, isSmartDepth, mktDepthOptions)
        return ticker

    def cancelMktDepth(self, contract: Contract, isSmartDepth=False):
        """
        Unsubscribe from market depth data.

        Args:
            contract: The exact contract object that was used to
                subscribe with.
        """
        ticker = self.ticker(contract)
        reqId = self.wrapper.endTicker(ticker, 'mktDepth')
        if reqId:
            self.client.cancelMktDepth(reqId, isSmartDepth)
        else:
            self._logger.error(
                f'cancelMktDepth: No reqId found for contract {contract}')

    def reqHistogramData(
            self, contract: Contract,
            useRTH: bool, period: str) -> List[HistogramData]:
        """
        Request histogram data.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/histograms.html

        Args:
            contract: Contract to query.
            useRTH: If True then only show data from within Regular
                Trading Hours, if False then show all data.
            period: Period of which data is being requested, for example
                '3 days'.
        """
        return self._run(
            self.reqHistogramDataAsync(contract, useRTH, period))

    def reqFundamentalData(
            self, contract: Contract, reportType: str,
            fundamentalDataOptions: List[TagValue] = None) -> str:
        """
        Get fundamental data of a contract in XML format.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/fundamentals.html

        Args:
            contract: Contract to query.
            reportType:

                * 'ReportsFinSummary': Financial summary
                * 'ReportsOwnership': Company's ownership
                * 'ReportSnapshot': Company's financial overview
                * 'ReportsFinStatements': Financial Statements
                * 'RESC': Analyst Estimates
                * 'CalendarReport': Company's calendar
            fundamentalDataOptions: Unknown
        """
        return self._run(
            self.reqFundamentalDataAsync(
                contract, reportType, fundamentalDataOptions))

    def reqScannerData(
            self, subscription: ScannerSubscription,
            scannerSubscriptionOptions: List[TagValue] = None,
            scannerSubscriptionFilterOptions:
            List[TagValue] = None) -> ScanDataList:
        """
        Do a blocking market scan by starting a subscription and canceling it
        after the initial list of results are in.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/market_scanners.html

        Args:
            subscription: Basic filters.
            scannerSubscriptionOptions: Unknown.
            scannerSubscriptionFilterOptions: Advanced generic filters.
        """
        return self._run(
            self.reqScannerDataAsync(
                subscription, scannerSubscriptionOptions,
                scannerSubscriptionFilterOptions))

    def reqScannerSubscription(
            self, subscription: ScannerSubscription,
            scannerSubscriptionOptions: List[TagValue] = None,
            scannerSubscriptionFilterOptions:
            List[TagValue] = None) -> ScanDataList:
        """
        Subscribe to market scan data.

        https://interactivebrokers.github.io/tws-api/market_scanners.html

        Args:
            subscription: What to scan for.
            scannerSubscriptionOptions: Unknown.
            scannerSubscriptionFilterOptions: Unknown.
        """
        reqId = self.client.getReqId()
        dataList = ScanDataList()
        dataList.reqId = reqId
        dataList.subscription = subscription
        dataList.scannerSubscriptionOptions = scannerSubscriptionOptions
        dataList.scannerSubscriptionFilterOptions = \
            scannerSubscriptionFilterOptions
        self.wrapper.startSubscription(reqId, dataList)
        self.client.reqScannerSubscription(
            reqId, subscription, scannerSubscriptionOptions,
            scannerSubscriptionFilterOptions)
        return dataList

    def cancelScannerSubscription(self, dataList: ScanDataList):
        """
        Cancel market data subscription.

        https://interactivebrokers.github.io/tws-api/market_scanners.html

        Args:
            dataList: The scan data list that was obtained from
                :meth:`.reqScannerSubscription`.
        """
        self.client.cancelScannerSubscription(dataList.reqId)
        self.wrapper.endSubscription(dataList)

    def reqScannerParameters(self) -> str:
        """
        Requests an XML list of scanner parameters.

        This method is blocking.
        """
        return self._run(self.reqScannerParametersAsync())

    def calculateImpliedVolatility(
            self, contract: Contract,
            optionPrice: float, underPrice: float,
            implVolOptions: List[TagValue] = None) -> OptionComputation:
        """
        Calculate the volatility given the option price.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/option_computations.html

        Args:
            contract: Option contract.
            optionPrice: Option price to use in calculation.
            underPrice: Price of the underlier to use in calculation
            implVolOptions: Unknown
        """
        return self._run(
            self.calculateImpliedVolatilityAsync(
                contract, optionPrice, underPrice, implVolOptions))

    def calculateOptionPrice(
            self, contract: Contract,
            volatility: float, underPrice: float,
            optPrcOptions=None) -> OptionComputation:
        """
        Calculate the option price given the volatility.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/option_computations.html

        Args:
            contract: Option contract.
            volatility: Option volatility to use in calculation.
            underPrice: Price of the underlier to use in calculation
            implVolOptions: Unknown
        """
        return self._run(
            self.calculateOptionPriceAsync(
                contract, volatility, underPrice, optPrcOptions))

    def reqSecDefOptParams(
            self, underlyingSymbol: str,
            futFopExchange: str, underlyingSecType: str,
            underlyingConId: int) -> List[OptionChain]:
        """
        Get the option chain.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/options.html

        Args:
            underlyingSymbol: Symbol of underlier contract.
            futFopExchange: Exchange (only for ``FuturesOption``, otherwise
                leave blank).
            underlyingSecType: The type of the underlying security, like
                'STK' or 'FUT'.
            underlyingConId: conId of the underlying contract.
        """
        return self._run(
            self.reqSecDefOptParamsAsync(
                underlyingSymbol, futFopExchange,
                underlyingSecType, underlyingConId))

    def exerciseOptions(
            self, contract: Contract, exerciseAction: int,
            exerciseQuantity: int, account: str, override: int):
        """
        Exercise an options contract.

        https://interactivebrokers.github.io/tws-api/options.html

        Args:
            contract: The option contract to be exercised.
            exerciseAction:
                * 1 = exercise the option
                * 2 = let the option lapse
            exerciseQuantity: Number of contracts to be exercised.
            account: Destination account.
            override:
                * 0 = no override
                * 1 = override the system's natural action
        """
        reqId = self.client.getReqId()
        self.client.exerciseOptions(
            reqId, contract, exerciseAction, exerciseQuantity,
            account, override)

    def reqNewsProviders(self) -> List[NewsProvider]:
        """
        Get a list of news providers.

        This method is blocking.
        """
        return self._run(self.reqNewsProvidersAsync())

    def reqNewsArticle(
            self, providerCode: str, articleId: str,
            newsArticleOptions: List[TagValue] = None) -> NewsArticle:
        """
        Get the body of a news article.

        This method is blocking.

        https://interactivebrokers.github.io/tws-api/news.html

        Args:
            providerCode: Code indicating news provider, like 'BZ' or 'FLY'.
            articleId: ID of the specific article.
            newsArticleOptions: Unknown.
        """
        return self._run(
            self.reqNewsArticleAsync(
                providerCode, articleId, newsArticleOptions))

    def reqHistoricalNews(
            self, conId: int, providerCodes: str,
            startDateTime: Union[str, datetime.date],
            endDateTime: Union[str, datetime.date],
            totalResults: int,
            historicalNewsOptions: List[TagValue] = None) -> HistoricalNews:
        """
        Get historical news headline.

        https://interactivebrokers.github.io/tws-api/news.html

        This method is blocking.

        Args:
            conId: Search news articles for contract with this conId.
            providerCodes: A '+'-separated list of provider codes, like
                'BZ+FLY'.
            startDateTime: The (exclusive) start of the date range.
                Can be given as a datetime.date or datetime.datetime,
                or it can be given as a string in 'yyyyMMdd HH:mm:ss' format.
                If no timezone is given then the TWS login timezone is used.
            endDateTime: The (inclusive) end of the date range.
                Can be given as a datetime.date or datetime.datetime,
                or it can be given as a string in 'yyyyMMdd HH:mm:ss' format.
                If no timezone is given then the TWS login timezone is used.
            totalResults: Maximum number of headlines to fetch (300 max).
            historicalNewsOptions: Unknown.
        """
        return self._run(
            self.reqHistoricalNewsAsync(
                conId, providerCodes, startDateTime, endDateTime,
                totalResults, historicalNewsOptions))

    def reqNewsBulletins(self, allMessages: bool):
        """
        Subscribe to IB news bulletins.

        https://interactivebrokers.github.io/tws-api/news.html

        Args:
            allMessages: If True then fetch all messages for the day.
        """
        self.client.reqNewsBulletins(allMessages)

    def cancelNewsBulletins(self):
        """
        Cancel subscription to IB news bulletins.
        """
        self.client.cancelNewsBulletins()

    def requestFA(self, faDataType: int):
        """
        Requests to change the FA configuration.

        This method is blocking.

        Args:
            faDataType:

                * 1 = Groups: Offer traders a way to create a group of
                  accounts and apply a single allocation method to all
                  accounts in the group.
                * 2 = Profiles: Let you allocate shares on an
                  account-by-account basis using a predefined calculation
                  value.
                * 3 = Account Aliases: Let you easily identify the accounts
                  by meaningful names rather than account numbers.
        """
        return self._run(self.requestFAAsync(faDataType))

    def replaceFA(self, faDataType: int, xml: str):
        """
        Replaces Financial Advisor's settings.

        Args:
            faDataType: See :meth:`.requestFA`.
            xml: The XML-formatted configuration string.
        """
        self.client.replaceFA(faDataType, xml)

    # now entering the parallel async universe

    async def connectAsync(
            self, host='127.0.0.1', port=7497, clientId=1, timeout=2):
        self.wrapper.clientId = clientId
        await self.client.connectAsync(host, port, clientId, timeout)
        accounts = self.client.getAccounts()
        await asyncio.gather(
            self.reqAccountUpdatesAsync(accounts[0]),
            *(self.reqAccountUpdatesMultiAsync(a) for a in accounts),
            self.reqPositionsAsync(),
            self.reqExecutionsAsync())
        if clientId == 0:
            # autobind manual orders
            self.reqAutoOpenOrders(True)
        self._logger.info('Synchronization complete')
        self.connectedEvent.emit()
        return self

    async def qualifyContractsAsync(self, *contracts):
        detailsLists = await asyncio.gather(
            *(self.reqContractDetailsAsync(c) for c in contracts))
        result = []
        for contract, detailsList in zip(contracts, detailsLists):
            if not detailsList:
                self._logger.error(f'Unknown contract: {contract}')
            elif len(detailsList) > 1:
                possibles = [details.contract for details in detailsList]
                self._logger.error(
                    f'Ambiguous contract: {contract}, '
                    f'possibles are {possibles}')
            else:
                c = detailsList[0].contract
                expiry = c.lastTradeDateOrContractMonth
                if expiry:
                    # remove time and timezone part as it will cause problems
                    expiry = expiry.split()[0]
                    c.lastTradeDateOrContractMonth = expiry
                if contract.exchange == 'SMART':
                    # overwriting 'SMART' exchange can create invalid contract
                    c.exchange = contract.exchange
                contract.update(**c.dict())
                result.append(contract)
        return result

    async def reqTickersAsync(self, *contracts, regulatorySnapshot=False):
        futures = []
        tickers = []
        for contract in contracts:
            reqId = self.client.getReqId()
            future = self.wrapper.startReq(reqId, contract)
            futures.append(future)
            ticker = self.wrapper.startTicker(reqId, contract, 'snapshot')
            tickers.append(ticker)
            self.client.reqMktData(
                reqId, contract, '', True, regulatorySnapshot, [])
        await asyncio.gather(*futures)
        for ticker in tickers:
            self.wrapper.endTicker(ticker, 'snapshot')
        return tickers

    def whatIfOrderAsync(self, contract, order):
        whatIfOrder = Order(**order.dict()).update(whatIf=True)
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.placeOrder(reqId, contract, whatIfOrder)
        return future

    def reqCurrentTimeAsync(self):
        future = self.wrapper.startReq('currentTime')
        self.client.reqCurrentTime()
        return future

    def reqAccountUpdatesAsync(self, account):
        future = self.wrapper.startReq('accountValues')
        self.client.reqAccountUpdates(True, account)
        return future

    def reqAccountUpdatesMultiAsync(self, account, modelCode=''):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqAccountUpdatesMulti(reqId, account, modelCode, False)
        return future

    def reqAccountSummaryAsync(self):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        tags = (
            'AccountType,NetLiquidation,TotalCashValue,SettledCash,'
            'AccruedCash,BuyingPower,EquityWithLoanValue,'
            'PreviousEquityWithLoanValue,GrossPositionValue,ReqTEquity,'
            'ReqTMargin,SMA,InitMarginReq,MaintMarginReq,AvailableFunds,'
            'ExcessLiquidity,Cushion,FullInitMarginReq,FullMaintMarginReq,'
            'FullAvailableFunds,FullExcessLiquidity,LookAheadNextChange,'
            'LookAheadInitMarginReq,LookAheadMaintMarginReq,'
            'LookAheadAvailableFunds,LookAheadExcessLiquidity,'
            'HighestSeverity,DayTradesRemaining,Leverage,$LEDGER:ALL')
        self.client.reqAccountSummary(reqId, 'All', tags)
        return future

    def reqOpenOrdersAsync(self):
        future = self.wrapper.startReq('openOrders')
        self.client.reqOpenOrders()
        return future

    def reqAllOpenOrdersAsync(self):
        future = self.wrapper.startReq('openOrders')
        self.client.reqAllOpenOrders()
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
        future = self.wrapper.startReq(reqId, contract)
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
            self._logger.error('reqMatchingSymbolsAsync: Timeout')

    def reqMarketRuleAsync(self, marketRuleId):
        future = self.wrapper.startReq(f'marketRule-{marketRuleId}')
        self.client.reqMarketRule(marketRuleId)
        return future

    def reqHistoricalDataAsync(
            self, contract, endDateTime,
            durationStr, barSizeSetting, whatToShow, useRTH,
            formatDate=1, keepUpToDate=False, chartOptions=None):
        reqId = self.client.getReqId()
        bars = BarDataList()
        bars.reqId = reqId
        bars.contract = contract
        bars.endDateTime = endDateTime
        bars.durationStr = durationStr
        bars.barSizeSetting = barSizeSetting
        bars.whatToShow = whatToShow
        bars.useRTH = useRTH
        bars.formatDate = formatDate
        bars.keepUpToDate = keepUpToDate
        bars.chartOptions = chartOptions
        future = self.wrapper.startReq(reqId, contract, container=bars)
        if keepUpToDate:
            self.wrapper.startSubscription(reqId, bars, contract)
        end = util.formatIBDatetime(endDateTime)
        self.client.reqHistoricalData(
            reqId, contract, end, durationStr, barSizeSetting,
            whatToShow, useRTH, formatDate, keepUpToDate, chartOptions)
        return future

    def reqHistoricalTicksAsync(
            self, contract, startDateTime, endDateTime,
            numberOfTicks, whatToShow, useRth,
            ignoreSize=False, miscOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        start = util.formatIBDatetime(startDateTime)
        end = util.formatIBDatetime(endDateTime)
        self.client.reqHistoricalTicks(
            reqId, contract, start, end, numberOfTicks, whatToShow, useRth,
            ignoreSize, miscOptions or [])
        return future

    def reqHeadTimeStampAsync(
            self, contract, whatToShow, useRTH, formatDate):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.reqHeadTimeStamp(
            reqId, contract, whatToShow, useRTH, formatDate)
        return future

    def reqMktDepthExchangesAsync(self):
        future = self.wrapper.startReq('mktDepthExchanges')
        self.client.reqMktDepthExchanges()
        return future

    def reqHistogramDataAsync(self, contract, useRTH, period):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.reqHistogramData(reqId, contract, useRTH, period)
        return future

    def reqFundamentalDataAsync(
            self, contract, reportType, fundamentalDataOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.reqFundamentalData(
            reqId, contract, reportType, fundamentalDataOptions)
        return future

    async def reqScannerDataAsync(
            self, subscription, scannerSubscriptionOptions=None,
            scannerSubscriptionFilterOptions=None):
        dataList = self.reqScannerSubscription(
            subscription, scannerSubscriptionOptions,
            scannerSubscriptionFilterOptions)
        future = self.wrapper.startReq(dataList.reqId, container=dataList)
        await future
        self.client.cancelScannerSubscription(dataList.reqId)
        return future.result()

    def reqScannerParametersAsync(self):
        future = self.wrapper.startReq('scannerParams')
        self.client.reqScannerParameters()
        return future

    async def calculateImpliedVolatilityAsync(
            self, contract, optionPrice, underPrice, implVolOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.calculateImpliedVolatility(
            reqId, contract, optionPrice, underPrice, implVolOptions)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            self._logger.error('calculateImpliedVolatilityAsync: Timeout')
            return
        finally:
            self.client.cancelCalculateImpliedVolatility(reqId)

    async def calculateOptionPriceAsync(
            self, contract, volatility, underPrice, optPrcOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId, contract)
        self.client.calculateOptionPrice(
            reqId, contract, volatility, underPrice, optPrcOptions)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            self._logger.error('calculateOptionPriceAsync: Timeout')
            return
        finally:
            self.client.cancelCalculateOptionPrice(reqId)

    def reqSecDefOptParamsAsync(
            self, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqSecDefOptParams(
            reqId, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId)
        return future

    def reqNewsProvidersAsync(self):
        future = self.wrapper.startReq('newsProviders')
        self.client.reqNewsProviders()
        return future

    def reqNewsArticleAsync(
            self, providerCode, articleId, newsArticleOptions):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        self.client.reqNewsArticle(
            reqId, providerCode, articleId, newsArticleOptions)
        return future

    async def reqHistoricalNewsAsync(
            self, conId, providerCodes, startDateTime, endDateTime,
            totalResults, historicalNewsOptions=None):
        reqId = self.client.getReqId()
        future = self.wrapper.startReq(reqId)
        start = util.formatIBDatetime(startDateTime)
        end = util.formatIBDatetime(endDateTime)
        self.client.reqHistoricalNews(
            reqId, conId, providerCodes, start, end,
            totalResults, historicalNewsOptions)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            self._logger.error('reqHistoricalNewsAsync: Timeout')

    async def requestFAAsync(self, faDataType):
        future = self.wrapper.startReq('requestFA')
        self.client.requestFA(faDataType)
        try:
            await asyncio.wait_for(future, 4)
            return future.result()
        except asyncio.TimeoutError:
            self._logger.error('requestFAAsync: Timeout')


if __name__ == '__main__':
    asyncio.get_event_loop().set_debug(True)
    util.logToConsole(logging.DEBUG)
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    ib.disconnect()
