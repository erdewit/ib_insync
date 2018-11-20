import asyncio
import logging
import datetime
from collections import defaultdict

from ibapi.wrapper import EWrapper, iswrapper
from ibapi.common import UNSET_DOUBLE

from ib_insync.contract import Contract
from ib_insync.ticker import Ticker
from ib_insync.order import Order, OrderStatus, Trade
from ib_insync.objects import (
    AccountValue, PortfolioItem, Position, OrderState, TradeLogEntry,
    ContractDetails, ContractDescription, PriceIncrement, OptionChain,
    Execution, Fill, CommissionReport, RealTimeBar, BarData, Dividends,
    NewsTick, NewsArticle, NewsBulletin, NewsProvider, HistoricalNews,
    TickData, HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast,
    TickAttrib, TickByTickAllLast, TickByTickBidAsk, TickByTickMidPoint,
    MktDepthData, DOMLevel, DepthMktDataDescription,
    OptionComputation, ScanData, HistogramData,
    TagValue, ComboLeg, SoftDollarTier)
import ib_insync.util as util

__all__ = ['Wrapper']


class Wrapper(EWrapper):
    """
    Wrapper implementation for use with the IB class.
    """
    def __init__(self, ib):
        self.timeoutEv = asyncio.Event()
        self._updateEv = asyncio.Event()
        self._ib = ib
        self._logger = logging.getLogger('ib_insync.wrapper')
        self._timeoutHandle = None
        self.reset()

    def reset(self):
        self.accountValues = {}  # (acc, tag, curr, modelCode) -> AccountValue
        self.acctSummary = {}  # (account, tag, currency) -> AccountValue
        self.portfolio = defaultdict(dict)  # account -> conId -> PortfolioItem
        self.positions = defaultdict(dict)  # account -> conId -> Position
        self.trades = {}  # (client, orderId) or permId -> Trade
        self.fills = {}  # execId -> Fill
        self.newsTicks = []  # list of NewsTick
        self.newsBulletins = {}  # msgId -> NewsBulletin

        self.tickers = {}  # id(Contract) -> Ticker
        self.pendingTickers = set()
        self.reqId2Ticker = {}
        self.ticker2ReqId = defaultdict(dict)  # tickType -> Ticker -> reqId

        self.reqId2Subscriber = {}  # live subscribers (live bars, scan data)

        self.pnls = {}  # reqId -> PnL
        self.pnlSingles = {}  # reqId -> PnLSingle
        self.pnlKey2ReqId = {}  # (account, modelCode) -> reqId
        self.pnlSingleKey2ReqId = {}  # (account, modelCode, conId) -> reqId

        self._futures = {}  # futures and results are linked by key
        self._results = {}
        self._reqId2Contract = {}

        self.accounts = []
        self.clientId = -1
        self.lastTime = None  # datetime (UTC) of last network packet arrival
        self._waitingOnUpdate = False
        self._timeout = 0
        if self._timeoutHandle:
            self._timeoutHandle.cancel()
            self._timeoutHandle = None

    def _getContract(self, ibContract):
        """
        Create contract that corresponds to the given ibapi contract.
        """
        contract = Contract.create(**ibContract.__dict__)
        if ibContract.comboLegs:
            contract.comboLegs = [
                ComboLeg(**leg.__dict__)
                for leg in ibContract.comboLegs]
        return contract

    def startReq(self, key, contract=None, container=None):
        """
        Start a new request and return the future that is associated
        with with the key and container. The container is a list by default.
        """
        future = asyncio.Future()
        self._futures[key] = future
        self._results[key] = container if container is not None else []
        if contract:
            self._reqId2Contract[key] = contract
        return future

    def _endReq(self, key, result=None, success=True):
        """
        Finish the future of corresponding key with the given result.
        If no result is given then it will be popped of the general results.
        """
        future = self._futures.pop(key, None)
        self._reqId2Contract.pop(key, None)
        if future:
            if result is None:
                result = self._results.pop(key, [])
            if not future.done():
                if success:
                    future.set_result(result)
                else:
                    future.set_exception(result)

    def startTicker(self, reqId, contract, tickType):
        """
        Start a tick request that has the reqId associated with the contract.
        Return the ticker.
        """
        ticker = self.tickers.get(id(contract))
        if not ticker:
            ticker = Ticker(
                contract=contract, ticks=[], tickByTicks=[],
                domBids=[], domAsks=[], domTicks=[])
            self.tickers[id(contract)] = ticker
        self.reqId2Ticker[reqId] = ticker
        self._reqId2Contract[reqId] = contract
        self.ticker2ReqId[tickType][ticker] = reqId
        return ticker

    def endTicker(self, ticker, tickType):
        reqId = self.ticker2ReqId[tickType].pop(ticker, 0)
        self._reqId2Contract.pop(reqId, None)
        return reqId

    def startSubscription(self, reqId, subscriber, contract=None):
        """
        Register a live subscription.
        """
        self._reqId2Contract[reqId] = contract
        self.reqId2Subscriber[reqId] = subscriber

    def endSubscription(self, subscriber):
        """
        Unregister a live subscription.
        """
        self._reqId2Contract.pop(subscriber.reqId, None)
        self.reqId2Subscriber.pop(subscriber.reqId, None)

    def orderKey(self, clientId, orderId, permId):
        if orderId <= 0:
            # order is placed manually from TWS
            key = permId
        else:
            key = (clientId, orderId)
        return key

    def setTimeout(self, timeout):
        self.lastTime = datetime.datetime.now(datetime.timezone.utc)
        if self._timeoutHandle:
            self._timeoutHandle.cancel()
        self._timeout = timeout
        if timeout:
            self._setTimer(timeout)

    def _setTimer(self, delay=0):
        if not self.lastTime:
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = (now - self.lastTime).total_seconds()
        if not delay:
            delay = self._timeout - diff
        if delay > 0:
            loop = asyncio.get_event_loop()
            self._timeoutHandle = loop.call_later(delay, self._setTimer)
        else:
            self._logger.debug('Timeout')
            self.timeoutEv.set()
            self.timeoutEv.clear()
            self._timeout = 0
            self._timeoutHandle = None
            self._ib.timeoutEvent.emit(diff)

    @iswrapper
    def connectAck(self):
        pass

    @iswrapper
    def nextValidId(self, reqId):
        pass

    @iswrapper
    def managedAccounts(self, accountsList):
        self.accounts = accountsList.split(',')

    @iswrapper
    def updateAccountTime(self, timestamp):
        pass

    @iswrapper
    def updateAccountValue(self, tag, val, currency, account):
        key = (account, tag, currency, '')
        acctVal = AccountValue(account, tag, val, currency, '')
        self.accountValues[key] = acctVal
        self._ib.accountValueEvent.emit(acctVal)

    @iswrapper
    def accountDownloadEnd(self, _account):
        # sent after updateAccountValue and updatePortfolio both finished
        self._endReq('accountValues')

    @iswrapper
    def accountUpdateMulti(
            self, reqId, account, modelCode, tag, val, currency):
        key = (account, tag, currency, modelCode)
        acctVal = AccountValue(account, tag, val, currency, modelCode)
        self.accountValues[key] = acctVal
        self._ib.accountValueEvent.emit(acctVal)

    @iswrapper
    def accountUpdateMultiEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def accountSummary(self, _reqId, account, tag, value, currency):
        key = (account, tag, currency)
        acctVal = AccountValue(account, tag, value, currency, '')
        self.acctSummary[key] = acctVal
        self._ib.accountSummaryEvent.emit(acctVal)

    @iswrapper
    def accountSummaryEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def updatePortfolio(
            self, contract, posSize, marketPrice, marketValue,
            averageCost, unrealizedPNL, realizedPNL, account):
        contract = self._getContract(contract)
        portfItem = PortfolioItem(
            contract, posSize, marketPrice, marketValue,
            averageCost, unrealizedPNL, realizedPNL, account)
        portfolioItems = self.portfolio[account]
        if posSize == 0:
            portfolioItems.pop(contract.conId, None)
        else:
            portfolioItems[contract.conId] = portfItem
        self._logger.info(f'updatePortfolio: {portfItem}')
        self._ib.updatePortfolioEvent.emit(portfItem)

    @iswrapper
    def position(self, account, contract, posSize, avgCost):
        contract = self._getContract(contract)
        position = Position(account, contract, posSize, avgCost)
        positions = self.positions[account]
        if posSize == 0:
            positions.pop(contract.conId, None)
        else:
            positions[contract.conId] = position
        self._logger.info(f'position: {position}')
        results = self._results.get('positions')
        if results is not None:
            results.append(position)
        self._ib.positionEvent.emit(position)

    @iswrapper
    def positionEnd(self):
        self._endReq('positions')

    @iswrapper
    def pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL):
        pnl = self.pnls.get(reqId)
        if not pnl:
            return
        pnl.dailyPnL = dailyPnL
        pnl.unrealizedPnL = unrealizedPnL
        pnl.realizedPnL = realizedPnL
        self._ib.pnlEvent.emit(pnl)

    @iswrapper
    def pnlSingle(
            self, reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value):
        pnlSingle = self.pnlSingles.get(reqId)
        if not pnlSingle:
            return
        pnlSingle.position = pos
        pnlSingle.dailyPnL = dailyPnL
        pnlSingle.unrealizedPnL = unrealizedPnL
        pnlSingle.realizedPnL = realizedPnL
        pnlSingle.value = value
        self._ib.pnlSingleEvent.emit(pnlSingle)

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        """
        This wrapper is called to:

        * feed in open orders at startup;
        * feed in open orders or order updates from other clients and TWS
          if clientId=master id;
        * feed in manual orders and order updates from TWS if clientId=0.
        """
        if order.whatIf:
            # response to whatIfOrder
            orderState = OrderState(**orderState.__dict__)
            self._endReq(order.orderId, orderState)
        else:
            if order.softDollarTier:
                order.softDollarTier = SoftDollarTier(
                    **order.softDollarTier.__dict__)
            key = self.orderKey(order.clientId, order.orderId, order.permId)
            trade = self.trades.get(key)
            if trade:
                trade.order.update(**order.__dict__)
            else:
                contract = self._getContract(contract)
                order = Order(**order.__dict__)
                orderStatus = OrderStatus(status=orderState.status)
                trade = Trade(contract, order, orderStatus, [], [])
                self.trades[key] = trade
                self._logger.info(f'openOrder: {trade}')
            results = self._results.get('openOrders')
            if results is None:
                self._ib.openOrderEvent.emit(trade)
            else:
                # response to reqOpenOrders
                results.append(order)

    @iswrapper
    def openOrderEnd(self):
        self._endReq('openOrders')

    @iswrapper
    def orderStatus(
            self, orderId, status, filled, remaining, avgFillPrice,
            permId, parentId, lastFillPrice, clientId, whyHeld,
            mktCapPrice=0.0, lastLiquidity=0):
        key = self.orderKey(clientId, orderId, permId)
        trade = self.trades.get(key)
        if trade:
            oldStatus = trade.orderStatus.status
            new = dict(
                status=status, filled=filled,
                remaining=remaining, avgFillPrice=avgFillPrice,
                permId=permId, parentId=parentId,
                lastFillPrice=lastFillPrice, clientId=clientId,
                whyHeld=whyHeld, mktCapPrice=mktCapPrice,
                lastLiquidity=lastLiquidity)
            curr = trade.orderStatus.dict()
            isChanged = curr != {**curr, **new}
            if isChanged:
                trade.orderStatus.update(**new)
                msg = ''
            elif (status == 'Submitted' and trade.log and
                    trade.log[-1].message == 'Modify'):
                # order modifications are acknowledged
                msg = 'Modified'
            else:
                msg = None

            if msg is not None:
                logEntry = TradeLogEntry(self.lastTime, status, msg)
                trade.log.append(logEntry)
                self._logger.info(f'orderStatus: {trade}')
                self._ib.orderStatusEvent.emit(trade)
                trade.statusEvent.emit(trade)
                if status != oldStatus:
                    if status == OrderStatus.Filled:
                        trade.filledEvent.emit(trade)
                    elif status == OrderStatus.Cancelled:
                        trade.cancelledEvent.emit(trade)
        else:
            self._logger.error(
                'orderStatus: No order found for '
                'orderId %s and clientId %s', orderId, clientId)

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        """
        This wrapper handles both live fills and responses to reqExecutions.
        """
        if execution.orderId == 2147483647:
            # bug in TWS: executions of manual orders have orderId=2**31 - 1
            execution.orderId = 0
        key = self.orderKey(
            execution.clientId, execution.orderId, execution.permId)
        trade = self.trades.get(key)
        if trade and contract.conId == trade.contract.conId:
            contract = trade.contract
        else:
            contract = self._getContract(contract)
        execId = execution.execId
        execution = Execution(**execution.__dict__)
        execution.time = util.parseIBDatetime(execution.time). \
            astimezone(datetime.timezone.utc)
        isLive = reqId not in self._futures
        time = self.lastTime if isLive else execution.time
        fill = Fill(contract, execution, CommissionReport(), time)
        if execId not in self.fills:
            # first time we see this execution so add it
            self.fills[execId] = fill
            if trade:
                trade.fills.append(fill)
                logEntry = TradeLogEntry(
                    self.lastTime,
                    trade.orderStatus.status,
                    f'Fill {execution.shares}@{execution.price}')
                trade.log.append(logEntry)
                if isLive:
                    self._logger.info(f'execDetails: {fill}')
                    self._ib.execDetailsEvent.emit(trade, fill)
                    trade.fillEvent(trade, fill)
        if not isLive:
            self._results[reqId].append(fill)

    @iswrapper
    def execDetailsEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def commissionReport(self, commissionReport):
        if commissionReport.yield_ == UNSET_DOUBLE:
            commissionReport.yield_ = 0.0
        if commissionReport.realizedPNL == UNSET_DOUBLE:
            commissionReport.realizedPNL = 0.0
        fill = self.fills.get(commissionReport.execId)
        if fill:
            report = fill.commissionReport.update(
                **commissionReport.__dict__)
            self._logger.info(f'commissionReport: {report}')
            key = self.orderKey(
                fill.execution.clientId,
                fill.execution.orderId, fill.execution.permId)
            trade = self.trades.get(key)
            if trade:
                self._ib.commissionReportEvent.emit(trade, fill, report)
                trade.commissionReportEvent.emit(trade, fill, report)
            else:
                # this is not a live execution and the order was filled
                # before this connection started
                pass
        else:
            report = CommissionReport(**commissionReport.__dict__)
            self._logger.error(
                'commissionReport: ' 'No execution found for %s', report)

    @iswrapper
    def contractDetails(self, reqId, contractDetails):
        cd = ContractDetails(**contractDetails.__dict__)
        cd.contract = self._getContract(cd.contract)
        if cd.secIdList:
            cd.secIdList = [TagValue(s.tag, s.value) for s in cd.secIdList]
        self._results[reqId].append(cd)

    bondContractDetails = contractDetails

    @iswrapper
    def contractDetailsEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def symbolSamples(self, reqId, contractDescriptions):
        cds = [ContractDescription(
            **cd.__dict__) for cd in contractDescriptions]
        for cd in cds:
            cd.contract = self._getContract(cd.contract)
        self._endReq(reqId, cds)

    @iswrapper
    def marketRule(self, marketRuleId, priceIncrements):
        result = [
            PriceIncrement(pi.lowEdge, pi.increment)
            for pi in priceIncrements]
        self._endReq(f'marketRule-{marketRuleId}', result)

    @iswrapper
    def realtimeBar(
            self, reqId, time, open_, high, low, close, volume, wap, count):
        dt = datetime.datetime.fromtimestamp(time, datetime.timezone.utc)
        bar = RealTimeBar(dt, -1, open_, high, low, close, volume, wap, count)
        bars = self.reqId2Subscriber.get(reqId)
        if bars is not None:
            bars.append(bar)
            self._ib.barUpdateEvent.emit(bars, True)
            bars.updateEvent.emit(bars, True)

    @iswrapper
    def historicalData(self, reqId, bar):
        bar = BarData(**bar.__dict__)
        bar.date = util.parseIBDatetime(bar.date)
        self._results[reqId].append(bar)

    @iswrapper
    def historicalDataEnd(self, reqId, _start, _end):
        self._endReq(reqId)

    @iswrapper
    def historicalDataUpdate(self, reqId, bar):
        bar = BarData(**bar.__dict__)
        bars = self.reqId2Subscriber.get(reqId)
        if not bars:
            return
        bar.date = util.parseIBDatetime(bar.date)
        hasNewBar = len(bars) == 0 or bar.date > bars[-1].date
        if hasNewBar:
            bars.append(bar)
        elif bars[-1] != bar:
            bars[-1] = bar
        else:
            return
        self._ib.barUpdateEvent.emit(bars, hasNewBar)
        bars.updateEvent.emit(bars, hasNewBar)

    @iswrapper
    def headTimestamp(self, reqId, headTimestamp):
        try:
            dt = util.parseIBDatetime(headTimestamp)
            self._endReq(reqId, dt)
        except ValueError as exc:
            self._endReq(reqId, exc, False)

    @iswrapper
    def historicalTicks(self, reqId, ticks, done):
        self._results[reqId] += [
            HistoricalTick(
                datetime.datetime.fromtimestamp(t.time, datetime.timezone.utc),
                t.price, t.size)
            for t in ticks if t.size]
        if done:
            self._endReq(reqId)

    @iswrapper
    def historicalTicksBidAsk(self, reqId, ticks, done):
        self._results[reqId] += [
            HistoricalTickBidAsk(
                datetime.datetime.fromtimestamp(t.time, datetime.timezone.utc),
                t.mask, t.priceBid, t.priceAsk, t.sizeBid, t.sizeAsk)
            for t in ticks]
        if done:
            self._endReq(reqId)

    @iswrapper
    def historicalTicksLast(self, reqId, ticks, done):
        self._results[reqId] += [
            HistoricalTickLast(
                datetime.datetime.fromtimestamp(t.time, datetime.timezone.utc),
                t.mask, t.price, t.size, t.exchange, t.specialConditions)
            for t in ticks if t.size]
        if done:
            self._endReq(reqId)

    @iswrapper
    # additional wrapper method provided by Client
    def priceSizeTick(self, reqId, tickType, price, size):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            self._logger.error(f'priceSizeTick: Unknown reqId: {reqId}')
            return
        ticker.time = self.lastTime
        # https://interactivebrokers.github.io/tws-api/tick_types.html
        if tickType in (1, 66):
            if price != ticker.bid:
                ticker.prevBid = ticker.bid
                ticker.bid = price
            if size != ticker.bidSize:
                ticker.prevBidSize = ticker.bidSize
                ticker.bidSize = size
        elif tickType in (2, 67):
            if price != ticker.ask:
                ticker.prevAsk = ticker.ask
                ticker.ask = price
            if size != ticker.askSize:
                ticker.prevAskSize = ticker.askSize
                ticker.askSize = size
        elif tickType in (4, 68):
            if price != ticker.last:
                ticker.prevLast = ticker.last
                ticker.last = price
            if size != ticker.lastSize:
                ticker.prevLastSize = ticker.lastSize
                ticker.lastSize = size
        elif tickType in (6, 72):
            ticker.high = price
        elif tickType in (7, 73):
            ticker.low = price
        elif tickType == 9:
            ticker.close = price
        elif tickType == 14:
            ticker.open = price
        elif tickType == 15:
            ticker.low13week = price
        elif tickType == 16:
            ticker.high13week = price
        elif tickType == 17:
            ticker.low26week = price
        elif tickType == 18:
            ticker.high26week = price
        elif tickType == 19:
            ticker.low52week = price
        elif tickType == 20:
            ticker.high52week = price
        elif tickType == 50:
            ticker.bidYield = price
        elif tickType == 51:
            ticker.askYield = price
        elif tickType == 52:
            ticker.lastYield = price
        if price or size:
            tick = TickData(self.lastTime, tickType, price, size)
            ticker.ticks.append(tick)
            self.pendingTickers.add(ticker)

    @iswrapper
    def tickSize(self, reqId, tickType, size):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            self._logger.error(f'tickSize: Unknown reqId: {reqId}')
            return
        ticker.time = self.lastTime
        price = -1.0
        # https://interactivebrokers.github.io/tws-api/tick_types.html
        if tickType in (0, 69):
            price = ticker.bid
            if size != ticker.bidSize:
                ticker.prevBidSize = ticker.bidSize
                ticker.bidSize = size
        elif tickType in (3, 70):
            price = ticker.ask
            if size != ticker.askSize:
                ticker.prevAskSize = ticker.askSize
                ticker.askSize = size
        elif tickType in (5, 71):
            price = ticker.last
            if util.isNan(price):
                return
            if size != ticker.lastSize:
                ticker.prevLastSize = ticker.lastSize
                ticker.lastSize = size
        elif tickType in (8, 74):
            ticker.volume = size
        elif tickType == 21:
            ticker.avVolume = size
        elif tickType == 27:
            ticker.callOpenInterest = size
        elif tickType == 28:
            ticker.putOpenInterest = size
        elif tickType == 29:
            ticker.callVolume = size
        elif tickType == 30:
            ticker.putVolume = size
        elif tickType == 86:
            ticker.futuresOpenInterest = size
        if price or size:
            tick = TickData(self.lastTime, tickType, price, size)
            ticker.ticks.append(tick)
            self.pendingTickers.add(ticker)

    @iswrapper
    def tickSnapshotEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def tickByTickAllLast(
            self, reqId, tickType, time, price, size, attribs,
            exchange, specialConditions):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            self._logger.error(f'tickByTickAllLast: Unknown reqId: {reqId}')
            return
        attribs = TickAttrib(**attribs.__dict__)
        tick = TickByTickAllLast(
            tickType, self.lastTime, price, size, attribs,
            exchange, specialConditions)
        ticker.tickByTicks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickByTickBidAsk(
            self, reqId, time, bidPrice, askPrice, bidSize, askSize, attribs):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            self._logger.error(f'tickByTickBidAsk: Unknown reqId: {reqId}')
            return
        attribs = TickAttrib(**attribs.__dict__)
        tick = TickByTickBidAsk(
            self.lastTime, bidPrice, askPrice, bidSize, askSize, attribs)
        ticker.tickByTicks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickByTickMidPoint(self, reqId, time, midPoint):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            self._logger.error(f'tickByTickMidPoint: Unknown reqId: {reqId}')
            return
        tick = TickByTickMidPoint(self.lastTime, midPoint)
        ticker.tickByTicks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickString(self, reqId, tickType, value):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            return
        try:
            if tickType == 48:
                # RTVolume string format:
                # price;size;ms since epoch;total volume;VWAP;single trade
                # example:
                # 701.28;1;1348075471534;67854;701.46918464;true
                price, size, _, rtVolume, vwap, _ = value.split(';')
                if rtVolume:
                    ticker.rtVolume = int(rtVolume)
                if vwap:
                    ticker.vwap = float(vwap)
                if price == '':
                    return
                price = float(price)
                size = float(size)
                if price and size:
                    if ticker.prevLast != ticker.last:
                        ticker.prevLast = ticker.last
                        ticker.last = price
                    if ticker.prevLastSize != ticker.lastSize:
                        ticker.prevLastSize = ticker.lastSize
                        ticker.lastSize = size
                    tick = TickData(self.lastTime, tickType, price, size)
                    ticker.ticks.append(tick)
                    self.pendingTickers.add(ticker)
            elif tickType == 59:
                # https://interactivebrokers.github.io/tws-api/tick_types.html#ib_dividends
                if value == ",,,":
                    # no dividend
                    ticker.dividends = Dividends(0, 0, None, 0)
                else:
                    # example value: '0.83,0.92,20130219,0.23'
                    past12, next12, date, amount = value.split(',')
                    ticker.dividends = Dividends(
                        float(past12), float(next12),
                        util.parseIBDatetime(date), float(amount))
        except ValueError:
            self._logger.error(
                f'tickString with tickType {tickType}: '
                f'malformed value: {value!r}')

    @iswrapper
    def tickGeneric(self, reqId, tickType, value):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            return
        try:
            value = float(value)
            tick = TickData(self.lastTime, tickType, value, 0)
            ticker.ticks.append(tick)
            self.pendingTickers.add(ticker)
        except ValueError:
            self._logger.error(f'genericTick: malformed value: {value!r}')

    @iswrapper
    def tickReqParams(self, reqId, minTick, bboExchange, snapshotPermissions):
        pass

    @iswrapper
    def mktDepthExchanges(self, depthMktDataDescriptions):
        result = [
            DepthMktDataDescription(**d.__dict__)
            for d in depthMktDataDescriptions]
        self._endReq('mktDepthExchanges', result)

    @iswrapper
    def updateMktDepth(self, reqId, position, operation, side, price, size):
        self.updateMktDepthL2(
            reqId, position, '', operation, side, price, size)

    @iswrapper
    def updateMktDepthL2(
            self, reqId, position, marketMaker, operation, side, price, size):
        # operation: 0 = insert, 1 = update, 2 = delete
        # side: 0 = ask, 1 = bid
        ticker = self.reqId2Ticker[reqId]
        ticker.time = self.lastTime

        dom = ticker.domBids if side else ticker.domAsks
        if operation == 0:
            dom.insert(position, DOMLevel(price, size, marketMaker))
        elif operation == 1:
            dom[position] = DOMLevel(price, size, marketMaker)
        elif operation == 2:
            if position < len(dom):
                level = dom.pop(position)
                price = level.price
                size = 0

        tick = MktDepthData(
            self.lastTime, position, marketMaker, operation, side, price, size)
        ticker.domTicks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickOptionComputation(
            self, reqId, tickType, impliedVol, delta, optPrice, pvDividend,
            gamma, vega, theta, undPrice):
        comp = OptionComputation(
            impliedVol, delta, optPrice, pvDividend,
            gamma, vega, theta, undPrice)
        ticker = self.reqId2Ticker.get(reqId)
        if ticker:
            # reply from reqMktData
            # https://interactivebrokers.github.io/tws-api/tick_types.html
            if tickType in (10, 80):
                ticker.bidGreeks = comp
            elif tickType in (11, 81):
                ticker.askGreeks = comp
            elif tickType in (12, 82):
                ticker.lastGreeks = comp
            elif tickType in (13, 83):
                ticker.modelGreeks = comp
        elif reqId in self._futures:
            # reply from calculateImpliedVolatility or calculateOptionPrice
            self._endReq(reqId, comp)
        else:
            self._logger.error(
                f'tickOptionComputation: Unknown reqId: {reqId}')

    @iswrapper
    def fundamentalData(self, reqId, data):
        self._endReq(reqId, data)

    @iswrapper
    def scannerParameters(self, xml):
        self._endReq('scannerParams', xml)

    @iswrapper
    def scannerData(
            self, reqId, rank, contractDetails, distance, benchmark,
            projection, legsStr):
        cd = ContractDetails(**contractDetails.__dict__)
        if cd.contract:
            cd.contract = self._getContract(cd.contract)
        data = ScanData(rank, cd, distance, benchmark, projection, legsStr)
        dataList = self.reqId2Subscriber.get(reqId)
        if dataList is None:
            dataList = self._results.get(reqId)
        if dataList is not None:
            if rank == 0:
                dataList.clear()
            dataList.append(data)

    @iswrapper
    def scannerDataEnd(self, reqId):
        dataList = self._results.get(reqId)
        if dataList:
            self._endReq(reqId)
        else:
            dataList = self.reqId2Subscriber.get(reqId)
        if dataList is not None:
            self._ib.scannerDataEvent.emit(dataList)
            dataList.updateEvent.emit(dataList)

    @iswrapper
    def histogramData(self, reqId, items):
        result = [HistogramData(item.price, item.count) for item in items]
        self._endReq(reqId, result)

    @iswrapper
    def securityDefinitionOptionParameter(
            self, reqId, exchange, underlyingConId, tradingClass,
            multiplier, expirations, strikes):
        chain = OptionChain(
            exchange, underlyingConId, tradingClass, multiplier,
            expirations, strikes)
        self._results[reqId].append(chain)

    @iswrapper
    def securityDefinitionOptionParameterEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def newsProviders(self, newsProviders):
        newsProviders = [
            NewsProvider(code=p.code, name=p.name)
            for p in newsProviders]
        self._endReq('newsProviders', newsProviders)

    @iswrapper
    def tickNews(
            self, _reqId, timeStamp, providerCode, articleId,
            headline, extraData):
        news = NewsTick(
            timeStamp, providerCode, articleId, headline, extraData)
        self.newsTicks.append(news)
        self._ib.tickNewsEvent.emit(news)

    @iswrapper
    def newsArticle(self, reqId, articleType, articleText):
        article = NewsArticle(articleType, articleText)
        self._endReq(reqId, article)

    @iswrapper
    def historicalNews(self, reqId, time, providerCode, articleId, headline):
        article = HistoricalNews(time, providerCode, articleId, headline)
        self._results[reqId].append(article)

    @iswrapper
    def historicalNewsEnd(self, reqId, _hasMore):
        self._endReq(reqId)

    @iswrapper
    def updateNewsBulletin(self, msgId, msgType, message, origExchange):
        bulletin = NewsBulletin(msgId, msgType, message, origExchange)
        self.newsBulletins[msgId] = bulletin
        self._ib.newsBulletinEvent.emit(bulletin)

    @iswrapper
    def receiveFA(self, _faDataType, faXmlData):
        self._endReq('requestFA', faXmlData)

    @iswrapper
    def currentTime(self, time):
        dt = datetime.datetime.fromtimestamp(time, datetime.timezone.utc)
        self._endReq('currentTime', dt)

    @iswrapper
    def error(self, reqId, errorCode, errorString):
        # https://interactivebrokers.github.io/tws-api/message_codes.html
        warningCodes = {165, 202, 399, 434, 10167}
        isWarning = errorCode in warningCodes or 2100 <= errorCode < 2200
        msg = (
            f'{"Warning" if isWarning else "Error"} '
            f'{errorCode}, reqId {reqId}: {errorString}')
        contract = self._reqId2Contract.get(reqId)
        if contract:
            msg += f', contract: {contract}'

        if isWarning:
            self._logger.info(msg)
        else:
            self._logger.error(msg)
            if reqId in self._futures:
                # the request failed
                self._endReq(reqId)
            elif (self.clientId, reqId) in self.trades:
                # something is wrong with the order, cancel it
                trade = self.trades[(self.clientId, reqId)]
                if not trade.isDone():
                    status = trade.orderStatus.status = OrderStatus.Cancelled
                    logEntry = TradeLogEntry(self.lastTime, status, msg)
                    trade.log.append(logEntry)
                    self._logger.warning(f'Canceled order: {trade}')
                    self._ib.orderStatusEvent.emit(trade)
                    trade.cancelledEvent.emit(trade)
            elif errorCode == 317:
                # Market depth data has been RESET
                ticker = self.reqId2Ticker.get(reqId)
                if ticker:
                    for side, l in ((0, ticker.domAsks), (1, ticker.domBids)):
                        for position in reversed(l):
                            level = l.pop(position)
                            tick = MktDepthData(
                                self.lastTime, position, '', 2,
                                side, level.price, 0)
                            ticker.domTicks.append(tick)

        self._ib.errorEvent.emit(reqId, errorCode, errorString, contract)

    @iswrapper
    # additional wrapper method provided by Client
    def tcpDataArrived(self):
        self.lastTime = datetime.datetime.now(datetime.timezone.utc)

    @iswrapper
    # additional wrapper method provided by Client
    def tcpDataProcessed(self):
        if self._waitingOnUpdate:
            self._updateEv.set()
            self._updateEv.clear()
        else:
            self._emitPendingTickers()
            self._clearPendingTickers()
        self._ib.updateEvent.emit()

    def waitOnUpdate(self, timeout=0):
        self._clearPendingTickers()
        self._waitingOnUpdate = True
        coro = self._updateEv.wait()
        if timeout:
            try:
                util.run(asyncio.wait_for(coro, timeout))
            except asyncio.TimeoutError:
                pass
        else:
            util.run(coro)
        self._waitingOnUpdate = False
        self._emitPendingTickers()
        return True

    def _emitPendingTickers(self):
        if self.pendingTickers:
            self._ib.pendingTickersEvent.emit(list(self.pendingTickers))
            for ticker in (
                    t for t in self.pendingTickers if t.updateEvent.slots):
                ticker.updateEvent.emit(ticker)

    def _clearPendingTickers(self):
        for ticker in self.pendingTickers:
            ticker.ticks.clear()
            ticker.tickByTicks.clear()
            ticker.domTicks.clear()
        self.pendingTickers.clear()
