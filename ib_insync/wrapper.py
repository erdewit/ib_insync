import asyncio
import logging
import datetime
from collections import defaultdict

from ibapi.wrapper import EWrapper, iswrapper

from ib_insync.contract import Contract
from ib_insync.ticker import Ticker
from ib_insync.order import Order
from ib_insync.objects import *  # @UnusedImport

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
        self.portfolio = defaultdict(dict)  # account -> conId -> PorfolioItem
        self.positions = defaultdict(dict)  # account -> conId -> Position
        self.trades = {}  # orderId -> Trade
        self.fills = {}  # execId -> Fill
        self.newsTicks = []  # list of NewsTick

        self._reqId2Contract = {}  # reqId -> reqMktData Contract
        self._contractIdentity2ReqId = {}  # id(reqMktData Contract) -> reqId
        self._reqId2Ticker = {}  # reqId -> Ticker
        self._pendingTickers = {}  # # id(reqMktData Contract) -> Ticker

        self._futures = {}  # futures and results are linked by key
        self._results = defaultdict(list)

        self.accounts = []
        self.clientId = -1
        self.lastTime = None  # datetime (UTC) of last network packet arrival
        self.updateEvent = asyncio.Event()

    def startReq(self, key):
        """
        Start a new request and return the future that is associated
        with with the key.
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._futures[key] = future
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

    def startReqMktData(self, reqId, contract):
        """
        Start a snapshot or tick subscription that has the
        reqId associated with the contract.
        """
        self._contractIdentity2ReqId[id(contract)] = reqId
        self._reqId2Contract[reqId] = contract
        ticker = self.getTicker(contract)
        if not ticker:
            ticker = Ticker(contract=contract, ticks=[])
            self._reqId2Ticker[reqId] = ticker

    def getTicker(self, contract):
        """
        Get the Ticker for the exact contract object for which ticks
        are streaming, or None if not found.
        """
        reqId = self._contractIdentity2ReqId.get(id(contract))
        return self._reqId2Ticker.get(reqId)

    def getTickers(self):
        """
        Get a list of all tickers.
        """
        return list(self._reqId2Ticker.values())

    def getPendingTickers(self):
        """
        Get a list of all tickers that have pending ticks.
        """
        return list(self._pendingTickers.values())

    def clearPendingTickers(self):
        """
        Clear both the list of pending tickers and their pending ticks.
        """
        for ticker in self._pendingTickers.values():
            del ticker.ticks[:]
        self._pendingTickers.clear()

    def getTickerReqId(self, contract):
        """
        Get the reqId of the Ticker for the exact contract
        object for which ticks are streaming, or None if not found.
        """
        reqId = self._contractIdentity2ReqId.get(id(contract))
        return reqId

    def _registerCallback(self, eventName, callback):
        """
        Invoke callback after an event. Events::
        
            * orderStatus(Trade)
            * execDetails(Trade, Fill)
            * commissionReport(Trade, Fill, CommissionReport)
            * updatePortfolio(PortfolioItem)
            * position(Position)
            * tickNews(NewsTick)
            
        Unregistering is done by setting the callback to None.
        """
        self._callbacks[eventName] = callback

    def _handleEvent(self, eventName, *args):
        cb = self._callbacks.get(eventName)
        if cb:
            try:
                cb(*args)
            except Exception:
                _logger.execption('Event %s(%s)', eventName, args)

    @iswrapper
    def nextValidId(self, reqId):
        self._reqIdSeq = reqId

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

    @iswrapper
    def positionEnd(self):
        self._endReq('positions')

    @iswrapper
    def openOrder(self, orderId, contract, order, orderState):
        contract = Contract(**contract.__dict__)
        order = Order(**order.__dict__)
        orderStatus = OrderStatus(status=orderState.status)
        trade = Trade(contract, order, orderStatus, [], [])
        self._results['openOrders'].append(trade)
        if order.clientId == self.clientId and orderId not in self.trades:
            self.trades[orderId] = trade
            _logger.info(f'openOrder: {trade}')

    @iswrapper
    def openOrderEnd(self):
        self._endReq('openOrders')

    @iswrapper
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
            permId, parentId, lastFillPrice, clientId, whyHeld):
        trade = self.trades.get(orderId)
        if trade:
            statusChanged = trade.orderStatus.status != status
            trade.orderStatus.update(status=status, filled=filled,
                    remaining=remaining, avgFillPrice=avgFillPrice,
                    permId=permId, parentId=parentId,
                    lastFillPrice=lastFillPrice, clientId=clientId,
                    whyHeld=whyHeld)
            if statusChanged:
                logEntry = TradeLogEntry(self.lastTime, status, '')
                trade.log.append(logEntry)
                _logger.info(f'orderStatus: {trade}')
                self._handleEvent('orderStatus', trade)
        else:
            _logger.error('orderStatus: No order found for '
                    'orderId %s and clientId %s', orderId, clientId)

    @iswrapper
    def execDetails(self, reqId, contract, execution):
        # must handle both live fills and responses to reqExecutions
        trade = self.trades.get(execution.orderId)
        if trade:
            contract = trade.contract
        else:
            contract = Contract(**contract.__dict__)
        execId = execution.execId
        execution = Execution(**execution.__dict__)
        fill = Fill(contract, execution, CommissionReport(), self.lastTime)
        if reqId in self._futures:
            # not live
            self._results[reqId].append(fill)
        if execId not in self.fills:
            # first time we see this execution so add it
            self.fills[execId] = fill
            if trade:
                trade.fills.append(fill)
                if trade.orderStatus.status != OrderStatus.Filled:
                    # orderStatus might not have set status to Filled
                    if sum(f.execution.shares for f in trade.fills) == \
                            trade.order.totalQuantity:
                        trade.orderStatus.status = OrderStatus.Filled
                logEntry = TradeLogEntry(self.lastTime,
                        trade.orderStatus.status,
                        f'Fill {execution.shares}@{execution.price}')
                trade.log.append(logEntry)
                self._handleEvent('execDetails', trade, fill)
        _logger.info(f'execDetails: {fill}')

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
            trade = self.trades.get(fill.execution.orderId)
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
    def historicalData(self, reqId , bar):
        bar = BarData(**bar.__dict__)
        date = bar.date
        if len(date) == 8:
            # YYYYmmdd
            y = int(date[0:4])
            m = int(date[4:6])
            d = int(date[6:8])
            dt = datetime.date(y, m, d)
        elif date.isdigit():
            dt = datetime.datetime.fromtimestamp(
                    int(date), datetime.timezone.utc)
        else:
            dt = datetime.datetime.strptime(date, '%Y%m%d  %H:%M:%S')
        bar.date = dt
        self._results[reqId].append(bar)

    @iswrapper
    def historicalDataEnd(self, reqId, start, end):
        self._endReq(reqId)

    @iswrapper
    def tickPrice(self, reqId , tickType, price, attrib):
        contract = self._reqId2Contract.get(reqId)
        ticker = self.getTicker(contract)
        if not ticker:
            _logger.error(f'tickPrice: Unknown reqId: {reqId}')
            return
        ticker.time = self.lastTime
        # https://interactivebrokers.github.io/tws-api/tick_types.html
        if tickType in (1, 66):
            ticker.prevBid = ticker.bid
            ticker.bid = price
            return
        elif tickType in (2, 67):
            ticker.prevAsk = ticker.ask
            ticker.ask = price
            return
        elif tickType in (4, 68):
            ticker.prevLast = ticker.last
            ticker.last = price
            return
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
        elif tickType == 21:
            ticker.avVolume = price
        tick = TickData(self.lastTime, tickType, price, 0)
        ticker.ticks.append(tick)
        self._pendingTickers[id(contract)] = ticker

    @iswrapper
    def tickSize(self, reqId, tickType, size):
        contract = self._reqId2Contract.get(reqId)
        ticker = self.getTicker(contract)
        if not ticker:
            _logger.error(f'tickSize: Unknown reqId: {reqId}')
            return
        ticker.time = self.lastTime
        # https://interactivebrokers.github.io/tws-api/tick_types.html
        if tickType in (0, 69):
            ticker.prevBidSize = ticker.bidSize
            ticker.bidSize = size
        elif tickType in (3, 70):
            ticker.prevAskSize = ticker.askSize
            ticker.askSize = size
        elif tickType in (5, 71):
            ticker.prevLastSize = ticker.lastSize
            ticker.lastSize = size
        elif tickType in (8, 74):
            ticker.volume = size
        elif tickType == 27:
            ticker.putOpenInterest = size
        elif tickType == 28:
            ticker.callOpenInterest = size
        elif tickType == 29:
            ticker.callVolume = size
        elif tickType == 30:
            ticker.putVolume = size
        elif tickType == 86:
            ticker.futuresOpenInterest = size
        tick = TickData(self.lastTime, tickType, ticker.last, size)
        ticker.ticks.append(tick)
        self._pendingTickers[id(contract)] = ticker

    @iswrapper
    def tickSnapshotEnd(self, reqId):
        self._endReq(reqId)

    @iswrapper
    def tickString(self, reqId, tickType, value):
        contract = self._reqId2Contract.get(reqId)
        ticker = self.getTicker(contract)
        if not ticker:
            return
        if tickType == 48:
            # RTVolume string format:
            # price;size;time in ms since epoch;total volume;VWAP;single trade
            # example:
            # 701.28;1;1348075471534;67854;701.46918464;true
            try:
                price, size, _, _, _, _ = value.split(';')
                if price == '':
                    return
                price = float(price)
                size = float(size)
                if price and size:
                    ticker.last = price
                    ticker.lastSize = size
                    tick = TickData(self.lastTime, tickType, price, size)
                    ticker.ticks.append(tick)
                    self._pendingTickers[id(contract)] = ticker
            except ValueError:
                _logger.error(f'tickString: malformed value: {value!r}')

    @iswrapper
    def tickGeneric(self, reqId, tickType, value):
        contract = self._reqId2Contract.get(reqId)
        ticker = self.getTicker(contract)
        if not ticker:
            return
        try:
            value = float(value)
            tick = TickData(self.lastTime, tickType, value, 0)
            ticker.ticks.append(tick)
            self._pendingTickers[id(contract)] = ticker
        except ValueError:
            _logger.error(f'genericTick: malformed value: {value!r}')

    @iswrapper
    def tickOptionComputation(self, reqId, tickType, impliedVol,
            delta, optPrice, pvDividend, gamma, vega, theta, undPrice):
        comp = OptionComputation(tickType, impliedVol,
                delta, optPrice, pvDividend, gamma, vega, theta, undPrice)
        if reqId in self._futures:
            # reply from calculateImpliedVolatility or calculateOptionPrice
            self._endReq(reqId, comp)
        else:
            # TODO: from streaming option ticks?
            pass

    @iswrapper
    def scannerParameters(self, xml):
        self._endReq('scannerParams', xml)

    @iswrapper
    def scannerData(self, reqId, rank, contractDetails, distance,
            benchmark, projection, legsStr):
        cd = ContractDetails(**contractDetails.__dict__)
        if cd.summary:
            cd.summary = Contract(cd.summary.__dict__)
        data = ScanData(rank, cd, distance, benchmark, projection, legsStr)
        self._results[reqId].append(data)

    @iswrapper
    def scannerDataEnd(self, reqId):
        return self._endReq(reqId)

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
        return self._endReq(reqId, article)

    @iswrapper
    def historicalNews(self, reqId, time, providerCode, articleId, headline):
        article = HistoricalNews(time, providerCode, articleId, headline)
        self._results[reqId].append(article)

    @iswrapper
    def historicalNewsEnd(self, reqId, _hasMore):
        return self._endReq(reqId)

    @iswrapper
    def error(self, reqId, errorCode, errorString):
        # https://interactivebrokers.github.io/tws-api/message_codes.html
        msg = f'Error {errorCode}, reqId {reqId}: {errorString}'
        if errorCode in (202, 2104, 2106):
            _logger.info(msg)
        else:
            _logger.error(msg)
        if reqId in self._futures:
            # the request failed
            future = self._futures.pop(reqId, None)
            future.set_result([])
            self._results.pop(reqId, None)
        elif errorCode not in (202,) and reqId in self.trades:
            # something is wrong with the order
            trade = self.trades[reqId]
            orderStatus = trade.orderStatus
            orderStatus.status = OrderStatus.Cancelled
            logEntry = TradeLogEntry(self.lastTime, orderStatus.status, msg)
            trade.log.append(logEntry)

    # additional wrapper methods provided by Client

    @iswrapper
    def tcpDataArrived(self):
        self.lastTime = datetime.datetime.now(datetime.timezone.utc)

    @iswrapper
    def tcpDataProcessed(self):
        self.updateEvent.set()
        self.updateEvent.clear()

