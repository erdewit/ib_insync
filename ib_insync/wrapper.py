import asyncio
import logging
import datetime
from collections import defaultdict

from ibapi.wrapper import EWrapper, iswrapper

from ib_insync.contract import Contract
from ib_insync.ticker import Ticker
from ib_insync.order import Order, OrderStatus, Trade
from ib_insync.objects import *
import ib_insync.util as util

__all__ = ['Wrapper']

_logger = logging.getLogger('ib_insync.wrapper')


class Wrapper(EWrapper):
    """
    Wrapper implementation for use with the IB class.
    """

    def __init__(self):
        self.reset()
        self._callbacks = {}  # eventName -> callback

    def reset(self):
        self.accountValues = {}  # (account, tag, currency) -> AccountValue
        self.acctSummary = {}  # (account, tag, currency) -> AccountValue
        self.portfolio = defaultdict(dict)  # account -> conId -> PortfolioItem
        self.positions = defaultdict(dict)  # account -> conId -> Position
        self.trades = {}  # (client, orderId) -> Trade
        self.fills = {}  # execId -> Fill
        self.newsTicks = []  # list of NewsTick
        self.newsBulletins = {}  # msgId -> NewsBulletin

        self.tickers = {}  # id(Contract) -> Ticker
        self.pendingTickers = set()
        self.reqId2Ticker = {}
        self.ticker2MktDataReqId = {}
        self.ticker2MktDepthReqId = {}

        self.reqId2Bars = {}  # realtime bars + keepUpToDate historical bars
        self.barsIdentity2ReqId = {}

        self._futures = {}  # futures and results are linked by key
        self._results = {}

        self.accounts = []
        self.clientId = -1
        self.lastTime = None  # datetime (UTC) of last network packet arrival
        self.updateEvent = asyncio.Event()

    def startReq(self, key, container=None):
        """
        Start a new request and return the future that is associated
        with with the key and container. The container is a list by default.
        """
        future = asyncio.Future()
        self._futures[key] = future
        self._results[key] = container if container is not None else []
        return future

    def _endReq(self, key, result=None):
        """
        Finish the future of corresponding key with the given result.
        If no result is given then it will be popped of the general results.
        """
        future = self._futures.pop(key, None)
        if future:
            if result is None:
                result = self._results.pop(key, [])
            if not future.done():
                future.set_result(result)

    def startTicker(self, reqId, contract, isMktDepth=False):
        """
        Start a snapshot, tick stream or market depth stream that has the
        reqId associated with the contract. Return the ticker.
        """
        ticker = self.tickers.get(id(contract))
        if not ticker:
            ticker = Ticker(contract=contract, ticks=[],
                    domBids=[], domAsks=[], domTicks=[])
            self.tickers[id(contract)] = ticker
        self.reqId2Ticker[reqId] = ticker
        if isMktDepth:
            self.ticker2MktDepthReqId[ticker] = reqId
        else:
            self.ticker2MktDataReqId[ticker] = reqId
        return ticker

    def endTicker(self, ticker, isMktDepth=False):
        if isMktDepth:
            reqId = self.ticker2MktDepthReqId.pop(ticker, 0)
        else:
            reqId = self.ticker2MktDataReqId.pop(ticker, 0)
        self.reqId2Ticker.pop(reqId, 0)
        return reqId

    def startLiveBars(self, reqId, bars):
        """
        Associate the reqId with the given live bars.
        """
        self.reqId2Bars[reqId] = bars
        self.barsIdentity2ReqId[id(bars)] = reqId

    def endLiveBars(self, bars):
        reqId = self.barsIdentity2ReqId.pop(id(bars), 0)
        self.reqId2Bars.pop(reqId, 0)
        return reqId

    def setCallback(self, eventName, callback):
        self._callbacks[eventName] = callback

    def _handleEvent(self, eventName, *args):
        # invoke optional callback
        cb = self._callbacks.get(eventName)
        if cb:
            try:
                cb(*args)
            except Exception:
                _logger.exception('Event %s(%s)', eventName, args)

    @iswrapper
    def managedAccounts(self, accountsList):
        self.accounts = accountsList.split(',')

    @iswrapper
    def updateAccountValue(self, tag, val, currency, account):
        key = (account, tag, currency)
        self.accountValues[key] = AccountValue(
                account, tag, val, currency)

    @iswrapper
    def accountDownloadEnd(self, _account):
        # sent after updateAccountValue and updatePortfolio both finished
        self._endReq('accountValues')

    @iswrapper
    def accountSummary(self, _reqId, account, tag, value, currency):
        key = (account, tag, currency)
        self.acctSummary[key] = AccountValue(
                account, tag, value, currency)

    @iswrapper
    def accountSummaryEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def updatePortfolio(self, contract, posSize, marketPrice, marketValue,
            averageCost, unrealizedPNL, realizedPNL, account):
        contract = Contract(**contract.__dict__)
        portfItem = PortfolioItem(
                contract, posSize, marketPrice, marketValue,
                averageCost, unrealizedPNL, realizedPNL, account)
        portfolioItems = self.portfolio[account]
        if posSize == 0:
            portfolioItems.pop(contract.conId, None)
        else:
            portfolioItems[contract.conId] = portfItem
        self._handleEvent('updatePortfolio', portfItem)
        _logger.info(f'updatePortfolio: {portfItem}')

    @iswrapper
    def position(self, account, contract, posSize, avgCost):
        contract = Contract(**contract.__dict__)
        position = Position(account, contract, posSize, avgCost)
        positions = self.positions[account]
        if posSize == 0:
            positions.pop(contract.conId, None)
        else:
            positions[contract.conId] = position
        self._handleEvent('position', position)
        _logger.info(f'position: {position}')
        results = self._results.get('positions')
        if results is not None:
            results.append(position)

    @iswrapper
    def positionEnd(self):
        self._endReq('positions')

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        if order.whatIf:
            # response to whatIfOrder
            orderState = OrderState(**orderState.__dict__)
            self._endReq(orderId, orderState)
        else:
            contract = Contract(**contract.__dict__)
            order = Order(**order.__dict__)
            orderStatus = OrderStatus(status=orderState.status)
            if order.softDollarTier:
                order.softDollarTier = SoftDollarTier(
                        **order.softDollarTier.__dict__)
            trade = Trade(contract, order, orderStatus, [], [])
            key = (order.clientId, orderId)
            if key not in self.trades:
                self.trades[key] = trade
                _logger.info(f'openOrder: {trade}')
            results = self._results.get('openOrders')
            if results is not None:
                # response to reqOpenOrders
                results.append(order)

    @iswrapper
    def openOrderEnd(self):
        self._endReq('openOrders')

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
            permId, parentId, lastFillPrice, clientId, whyHeld,
            mktCapPrice=0.0, lastLiquidity=0):
        key = (clientId, orderId)
        trade = self.trades.get(key)
        if trade:
            statusChanged = trade.orderStatus.status != status
            trade.orderStatus.update(status=status, filled=filled,
                    remaining=remaining, avgFillPrice=avgFillPrice,
                    permId=permId, parentId=parentId,
                    lastFillPrice=lastFillPrice, clientId=clientId,
                    whyHeld=whyHeld, mktCapPrice=mktCapPrice,
                    lastLiquidity=lastLiquidity)
            if statusChanged:
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
                _logger.info(f'orderStatus: {trade}')
                self._handleEvent('orderStatus', trade)
        elif orderId <= 0:
            # order originates from manual trading or other API client
            pass
        else:
            _logger.error('orderStatus: No order found for '
                    'orderId %s and clientId %s', orderId, clientId)

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        # must handle both live fills and responses to reqExecutions
        key = (execution.clientId, execution.orderId)
        trade = self.trades.get(key)
        if trade:
            contract = trade.contract
        else:
            contract = Contract(**contract.__dict__)
        execId = execution.execId
        execution = Execution(**execution.__dict__)
        fill = Fill(contract, execution, CommissionReport(), self.lastTime)
        isLive = reqId not in self._futures
        if execId not in self.fills:
            # first time we see this execution so add it
            self.fills[execId] = fill
            if trade:
                becomesFilled = (trade.remaining() <= 0 and
                        trade.orderStatus.status != OrderStatus.Filled)
                trade.fills.append(fill)
                if becomesFilled:
                    # orderStatus might not have set status to Filled
                    trade.orderStatus.status = OrderStatus.Filled
                logEntry = TradeLogEntry(self.lastTime,
                        trade.orderStatus.status,
                        f'Fill {execution.shares}@{execution.price}')
                trade.log.append(logEntry)
                if isLive:
                    self._handleEvent('execDetails', trade, fill)
                    _logger.info(f'execDetails: {fill}')
                    if becomesFilled:
                        self._handleEvent('orderStatus', trade)
        if not isLive:
            self._results[reqId].append(fill)

    @iswrapper
    def execDetailsEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def commissionReport(self, commissionReport):
        fill = self.fills.get(commissionReport.execId)
        if fill:
            report = fill.commissionReport.update(
                    **commissionReport.__dict__)
            _logger.info(f'commissionReport: {report}')
            key = (fill.execution.clientId, fill.execution.orderId)
            trade = self.trades.get(key)
            if trade:
                self._handleEvent('commissionReport',
                        trade, fill, report)
            else:
                # this is not a live execution and the order was filled
                # before this connection started
                pass
        else:
            report = CommissionReport(**commissionReport.__dict__)
            _logger.error('commissionReport: '
                    'No execution found for %s', report)

    @iswrapper
    def contractDetails(self, reqId, contractDetails):
        cd = ContractDetails(**contractDetails.__dict__)
        cd.summary = Contract(**cd.summary.__dict__)
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
            cd.contract = Contract(**cd.contract.__dict__)
        self._endReq(reqId, cds)

    @iswrapper
    def realtimeBar(self, reqId, time, open_, high, low, close, volume,
            wap, count):
        dt = datetime.datetime.fromtimestamp(time)
        bar = RealTimeBar(dt, -1, open_, high, low, close, volume, wap, count)
        bars = self.reqId2Bars[reqId]
        bars.append(bar)
        self._handleEvent('barUpdate', bars, True)

    @iswrapper
    def historicalData(self, reqId , bar):
        bar = BarData(**bar.__dict__)
        bar.date = util.parseIBDatetime(bar.date)
        self._results[reqId].append(bar)

    @iswrapper
    def historicalDataEnd(self, reqId, _start, _end):
        self._endReq(reqId)

    @iswrapper
    def historicalDataUpdate(self, reqId, bar):
        bars = self.reqId2Bars[reqId]
        bar.date = util.parseIBDatetime(bar.date)
        if len(bars) == 0 or bar.date > bars[-1].date:
            bars.append(bar)
            self._handleEvent('barUpdate', bars, True)
        elif bars[-1] != bar:
            bars[-1] = bar
            self._handleEvent('barUpdate', bars, False)

    @iswrapper
    def headTimestamp(self, reqId, headTimestamp):
        dt = util.parseIBDatetime(headTimestamp)
        self._endReq(reqId, dt)

    @iswrapper
    def historicalTicks(self, reqId, ticks, done):
        self._results[reqId] += [HistoricalTick(
                datetime.datetime.fromtimestamp(t.time),
                t.price, t.size) for t in ticks]
        if done:
            self._endReq(reqId)

    @iswrapper
    def historicalTicksBidAsk(self, reqId, ticks, done):
        self._results[reqId] += [HistoricalTickBidAsk(
                datetime.datetime.fromtimestamp(t.time),
                t.mask, t.priceBid, t.priceAsk, t.sizeBid, t.sizeAsk)
                for t in ticks]
        if done:
            self._endReq(reqId)

    @iswrapper
    def historicalTicksLast(self, reqId, ticks, done):
        self._results[reqId] += [HistoricalTickLast(
                datetime.datetime.fromtimestamp(t.time),
                t.mask, t.price, t.size, t.exchange, t.specialConditions)
                for t in ticks]
        if done:
            self._endReq(reqId)

    @iswrapper
    # additional wrapper method provided by Client
    def priceSizeTick(self, reqId, tickType, price, size):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            _logger.error(f'priceSizeTick: Unknown reqId: {reqId}')
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
        tick = TickData(self.lastTime, tickType, price, size)
        ticker.ticks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickSize(self, reqId, tickType, size):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            _logger.error(f'tickSize: Unknown reqId: {reqId}')
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
        tick = TickData(self.lastTime, tickType, price, size)
        ticker.ticks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickSnapshotEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def tickString(self, reqId, tickType, value):
        ticker = self.reqId2Ticker.get(reqId)
        if not ticker:
            return
        if tickType == 48:
            # RTVolume string format:
            # price;size;time in ms since epoch;total volume;VWAP;single trade
            # example:
            # 701.28;1;1348075471534;67854;701.46918464;true
            try:
                price, size, _, _, vwap, _ = value.split(';')
                if price == '':
                    return
                price = float(price)
                size = float(size)
                if price and size:
                    ticker.prevLast = ticker.last
                    ticker.prevLastSize = ticker.lastSize
                    ticker.last = price
                    ticker.lastSize = size
                    if vwap:
                        ticker.vwap = float(vwap)
                    tick = TickData(self.lastTime, tickType, price, size)
                    ticker.ticks.append(tick)
                    self.pendingTickers.add(ticker)
            except ValueError:
                _logger.error(f'tickString: malformed value: {value!r}')

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
            _logger.error(f'genericTick: malformed value: {value!r}')

    @iswrapper
    def mktDepthExchanges(self, depthMktDataDescriptions):
        result = [DepthMktDataDescription(**d.__dict__)
                for d in depthMktDataDescriptions]
        self._endReq('mktDepthExchanges', result)

    @iswrapper
    def updateMktDepth(self, reqId, position, operation, side, price, size):
        self.updateMktDepthL2(reqId, position, '', operation, side, price, size)

    @iswrapper
    def updateMktDepthL2(self, reqId, position, marketMaker, operation,
            side, price, size):
        # operation: 0 = insert, 1 = update, 2 = delete
        # side: 0 = ask, 1 = bid
        ticker = self.reqId2Ticker[reqId]
        ticker.time = self.lastTime

        l = ticker.domBids if side else ticker.domAsks
        if operation == 0:
            l.insert(position, DOMLevel(price, size, marketMaker))
        elif operation == 1:
            l[position] = DOMLevel(price, size, marketMaker)
        elif operation == 2:
            if position < len(l):
                level = l.pop(position)
                price = level.price
                size = 0

        tick = MktDepthData(self.lastTime, position, marketMaker,
                operation, side, price, size)
        ticker.domTicks.append(tick)
        self.pendingTickers.add(ticker)

    @iswrapper
    def tickOptionComputation(self, reqId, tickType, impliedVol,
            delta, optPrice, pvDividend, gamma, vega, theta, undPrice):
        comp = OptionComputation(impliedVol,
                delta, optPrice, pvDividend, gamma, vega, theta, undPrice)
        ticker = self.reqId2Ticker.get(reqId)
        if ticker:
            # reply from reqMktData
            if tickType == 10:
                ticker.bidGreeks = comp
            elif tickType == 11:
                ticker.askGreeks = comp
            elif tickType == 12:
                ticker.lastGreeks = comp
            elif tickType == 13:
                ticker.modelGreeks = comp
        elif reqId in self._futures:
            # reply from calculateImpliedVolatility or calculateOptionPrice
            self._endReq(reqId, comp)
        else:
            _logger.error(f'tickOptionComputation: Unknown reqId: {reqId}')

    @iswrapper
    def fundamentalData(self, reqId, data):
        self._endReq(reqId, data)

    @iswrapper
    def scannerParameters(self, xml):
        self._endReq('scannerParams', xml)

    @iswrapper
    def scannerData(self, reqId, rank, contractDetails, distance,
            benchmark, projection, legsStr):
        cd = ContractDetails(**contractDetails.__dict__)
        if cd.summary:
            cd.summary = Contract(**cd.summary.__dict__)
        data = ScanData(rank, cd, distance, benchmark, projection, legsStr)
        self._results[reqId].append(data)

    @iswrapper
    def scannerDataEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def histogramData(self, reqId, items):
        result = [HistogramData(item.price, item.count) for item in items]
        self._endReq(reqId, result)

    @iswrapper
    def securityDefinitionOptionParameter(self, reqId, exchange,
            underlyingConId, tradingClass, multiplier, expirations, strikes):
        chain = OptionChain(exchange, underlyingConId,
                tradingClass, multiplier, expirations, strikes)
        self._results[reqId].append(chain)

    @iswrapper
    def securityDefinitionOptionParameterEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def newsProviders(self, newsProviders):
        newsProviders = [NewsProvider(code=p.code, name=p.name)
                for p in newsProviders]
        self._endReq('newsProviders', newsProviders)

    @iswrapper
    def tickNews(self, _reqId, timeStamp, providerCode, articleId,
            headline, extraData):
        news = NewsTick(timeStamp, providerCode, articleId, headline, extraData)
        self.newsTicks.append(news)
        self._handleEvent('tickNews', news)

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

    @iswrapper
    def receiveFA(self, _faDataType, faXmlData):
        self._endReq('requestFA', faXmlData)

    @iswrapper
    def error(self, reqId, errorCode, errorString):
        # https://interactivebrokers.github.io/tws-api/message_codes.html
        isWarning = errorCode in (202, 399, 10167) or 2100 <= errorCode < 2200
        msg = (f'{"Warning" if isWarning else "Error"} '
                f'{errorCode}, reqId {reqId}: {errorString}')
        if isWarning:
            _logger.info(msg)
        else:
            _logger.error(msg)
            if reqId in self._futures:
                # the request failed
                self._endReq(reqId)
            elif (self.clientId, reqId) in self.trades:
                # something is wrong with the order, cancel it
                trade = self.trades[(self.clientId, reqId)]
                if trade.isActive():
                    status = trade.orderStatus.status = OrderStatus.Cancelled
                    logEntry = TradeLogEntry(self.lastTime, status, msg)
                    trade.log.append(logEntry)
                    _logger.warning(f'Canceled order: {trade}')
                    self._handleEvent('orderStatus', trade)
            elif errorCode == 317:
                # Market depth data has been RESET
                ticker = self.reqId2Ticker.get(reqId)
                if ticker:
                    for side, l in ((0, ticker.domAsks), (1, ticker.domBids)):
                        for position in reversed(range(l)):
                            level = l.pop(position)
                            tick = MktDepthData(self.lastTime, position,
                                    '', 2, side, level.price, 0)
                            ticker.domTicks.append(tick)
        self._handleEvent('error', errorCode, errorString)

    @iswrapper
    # additional wrapper method provided by Client
    def tcpDataArrived(self):
        self.lastTime = datetime.datetime.now(datetime.timezone.utc)
        # clear pending tickers and their ticks
        for ticker in self.pendingTickers:
            del ticker.ticks[:]
            del ticker.domTicks[:]
        self.pendingTickers.clear()

    @iswrapper
    # additional wrapper method provided by Client
    def tcpDataProcessed(self):
        if self.pendingTickers:
            self._handleEvent('pendingTickers', self.pendingTickers)
        self.updateEvent.set()
        self.updateEvent.clear()
        self._handleEvent('updated')

