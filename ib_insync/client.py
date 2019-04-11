import struct
import asyncio
import logging
import time
import io
from collections import deque
from typing import List

import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper, iswrapper
from eventkit import Event

from ib_insync.objects import ConnectionStats
from ib_insync.contract import Contract
import ib_insync.util as util
from .util import UNSET_INTEGER, UNSET_DOUBLE

__all__ = ['Client']


class Client(EClient):
    """
    Modification of ``ibapi.client.EClient`` that uses asyncio.

    The client is fully asynchronous and has its own
    event-driven networking code that replaces the
    networking code of the standard EClient.
    It also replaces the infinite loop of ``EClient.run()``
    with the asyncio event loop. It can be used as a drop-in
    replacement for the standard EClient as provided by IBAPI.

    Compared to the standard EClient this client has the following
    additional features:

    * ``client.connect()`` will block until the client is ready to
      serve requests; It is not necessary to wait for ``nextValidId``
      to start requests as the client has already done that.
      The reqId is directly available with :py:meth:`.getReqId()`.

    * ``client.connectAsync()`` is a coroutine for connecting asynchronously.

    * When blocking, ``client.connect()`` can be made to time out with
      the timeout parameter (default 2 seconds).

    * Optional ``wrapper.priceSizeTick(reqId, tickType, price, size)`` that
      combines price and size instead of the two wrapper methods
      priceTick and sizeTick.

    * Automatic request throttling.

    * Optional ``wrapper.tcpDataArrived()`` method;
      If the wrapper has this method it is invoked directly after
      a network packet has arrived.
      A possible use is to timestamp all data in the packet with
      the exact same time.

    * Optional ``wrapper.tcpDataProcessed()`` method;
      If the wrapper has this method it is invoked after the
      network packet's data has been handled.
      A possible use is to write or evaluate the newly arrived data in
      one batch instead of item by item.

    Attributes:
      MaxRequests (int):
        Throttle the number of requests to ``MaxRequests`` per
        ``RequestsInterval`` seconds. Set to 0 to disable throttling.
      RequestsInterval (float):
        Time interval (in seconds) for request throttling.
      MaxClientVersion (int):
        Client protocol version.

    Events:
      * ``apiStart`` ()
      * ``apiEnd`` ()
      * ``apiError`` (errorMsg: str)
    """

    events = ('apiStart', 'apiEnd', 'apiError')

    MaxRequests = 45
    RequestsInterval = 1
    MaxClientVersion = 148

    def __init__(self, wrapper):
        self._readyEvent = asyncio.Event()
        EClient.__init__(self, wrapper)
        Event.init(self, Client.events)
        self._loop = asyncio.get_event_loop()
        self._logger = logging.getLogger('ib_insync.client')

        # extra optional wrapper methods
        self._priceSizeTick = getattr(wrapper, 'priceSizeTick', None)
        self._tcpDataArrived = getattr(wrapper, 'tcpDataArrived', None)
        self._tcpDataProcessed = getattr(wrapper, 'tcpDataProcessed', None)

    def reset(self):
        EClient.reset(self)
        self._readyEvent.clear()
        self._data = b''
        self._connectOptions = b''
        self._reqIdSeq = 0
        self._accounts = None
        self._startTime = time.time()
        self._numBytesRecv = 0
        self._numMsgRecv = 0
        self._isThrottling = False
        self._msgQ = deque()
        self._timeQ = deque()

    def run(self):
        self._loop.run_forever()

    def isReady(self) -> bool:
        """
        Is the API connection up and running?
        """
        return self._readyEvent.is_set()

    def connectionStats(self) -> ConnectionStats:
        """
        Get statistics about the connection.
        """
        if not self.isReady():
            raise ConnectionError('Not connected')
        return ConnectionStats(
            self._startTime,
            time.time() - self._startTime,
            self._numBytesRecv, self.conn.numBytesSent,
            self._numMsgRecv, self.conn.numMsgSent)

    def getReqId(self) -> int:
        """
        Get new request ID.
        """
        if not self.isReady():
            raise ConnectionError('Not connected')
        newId = self._reqIdSeq
        self._reqIdSeq += 1
        return newId

    def getAccounts(self) -> List[str]:
        """
        Get the list of account names that are under management.
        """
        if not self.isReady():
            raise ConnectionError('Not connected')
        return self._accounts

    def setConnectOptions(self, connectOptions: str):
        """
        Set additional connect options.

        Args:
            connectOptions: Use "+PACEAPI" to use request-pacing built
                into TWS/gateway 974+.
        """
        self._connectOptions = connectOptions.encode()

    def connect(
            self, host: str, port: int, clientId: int, timeout: float = 2):
        """
        Connect to a running TWS or IB gateway application.

        Args:
            host: Host name or IP address.
            port: Port number.
            clientId: ID number to use for this client; must be unique per
                connection.
            timeout: If establishing the connection takes longer than
                ``timeout`` seconds then the ``asyncio.TimeoutError`` exception
                is raised. Set to 0 to disable timeout.
        """
        util.run(self.connectAsync(host, port, clientId, timeout))

    async def connectAsync(self, host, port, clientId, timeout=2):
        self._logger.info(
            f'Connecting to {host}:{port} with clientId {clientId}...')
        self.host = host
        self.port = port
        self.clientId = clientId
        self.setConnState(EClient.CONNECTING)
        self.conn = Connection(host, port)
        self.conn.connected = self._onSocketConnected
        self.conn.hasData = self._onSocketHasData
        self.conn.disconnected = self._onSocketDisconnected
        self.conn.hasError = self._onSocketHasError
        try:
            await asyncio.sleep(0)  # in case of a not yet finished disconnect
            fut = asyncio.gather(self.conn.connect(), self._readyEvent.wait())
            await asyncio.wait_for(fut, timeout)
            self._logger.info('API connection ready')
            self.apiStart.emit()
        except Exception as e:
            self.reset()
            msg = f'API connection failed: {e!r}'
            self._logger.error(msg)
            self.apiError.emit(msg)
            if isinstance(e, ConnectionRefusedError):
                msg = 'Make sure API port on TWS/IBG is open'
                self._logger.error(msg)
            await fut  # consume exception
            raise

    def sendMsg(self, msg):
        t = self._loop.time()
        times = self._timeQ
        msgs = self._msgQ
        while times and t - times[0] > self.RequestsInterval:
            times.popleft()
        if msg:
            msgs.append(msg)
        while msgs and (len(times) < self.MaxRequests or not self.MaxRequests):
            msg = msgs.popleft()
            self.conn.sendMsg(self._prefix(msg.encode()))
            times.append(t)
        if msgs:
            if not self._isThrottling:
                self._isThrottling = True
                self._logger.warning('Started to throttle requests')
            self._loop.call_at(
                times[0] + self.RequestsInterval,
                self.sendMsg, None)
        else:
            if self._isThrottling:
                self._isThrottling = False
                self._logger.warning('Stopped to throttle requests')

    def _prefix(self, msg):
        # prefix a message with its length
        return struct.pack('>I', len(msg)) + msg

    def _onSocketConnected(self):
        self._logger.info('Connected')
        # start handshake
        msg = b'API\0'
        minVer = ibapi.server_versions.MIN_CLIENT_VER
        maxVer = min(
            self.MaxClientVersion, ibapi.server_versions.MAX_CLIENT_VER)
        connectOptions = b' ' + self._connectOptions if self._connectOptions \
            else b''
        msg += self._prefix(b'v%d..%d%s' % (minVer, maxVer, connectOptions))
        self.conn.sendMsg(msg)
        self.decoder = ibapi.decoder.Decoder(self.wrapper, None)

    def _onSocketHasData(self, data):
        debug = self._logger.isEnabledFor(logging.DEBUG)
        if self._tcpDataArrived:
            self._tcpDataArrived()

        self._data += data
        self._numBytesRecv += len(data)

        while True:
            if len(self._data) <= 4:
                break
            # 4 byte prefix tells the message length
            msgEnd = 4 + struct.unpack('>I', self._data[:4])[0]
            if len(self._data) < msgEnd:
                # insufficient data for now
                break
            msg = self._data[4:msgEnd]
            self._data = self._data[msgEnd:]
            fields = msg.split(b'\0')
            fields.pop()  # pop off last empty element
            self._numMsgRecv += 1

            if debug:
                self._logger.debug(
                    '<<< %s', ','.join(
                        f.decode(errors='backslashreplace') for f in fields))

            if not self.serverVersion_ and len(fields) == 2:
                # this concludes the handshake
                version, _connTime = fields
                self.serverVersion_ = int(version)
                self.decoder.serverVersion = self.serverVersion_
                self.setConnState(EClient.CONNECTED)
                self.startApi()
                self.wrapper.connectAck()
                self._logger.info(
                    f'Logged on to server version {self.serverVersion_}')
            else:
                # decode and handle the message
                try:
                    self._decode(fields)
                except Exception:
                    self._logger.exception('Decode failed')

        if self._tcpDataProcessed:
            self._tcpDataProcessed()

    def _onSocketDisconnected(self):
        if self.isConnected():
            msg = f'Peer closed connection'
            self._logger.error(msg)
            if not self.isReady():
                msg = f'clientId {self.clientId} already in use?'
                self._logger.error(msg)
            self.apiError.emit(msg)
        else:
            self._logger.info('Disconnected')
        self.reset()
        self.apiEnd.emit()

    def _onSocketHasError(self, msg):
        self._logger.error(msg)
        self.reset()
        self.apiError.emit(msg)

    def send(self, *fields):
        msg = self._encode(*fields)
        self.sendMsg(msg)

    def _encode(self, *fields):
        """
        Serialize the given fields to a string conforming to the
        IB socket protocol.
        """
        result = io.StringIO()
        for field in fields:
            if field in (None, UNSET_INTEGER, UNSET_DOUBLE):
                s = ''
            elif isinstance(field, Contract):
                c = field
                s = '\0'.join(str(f) for f in (
                    c.conId, c.symbol, c.secType,
                    c.lastTradeDateOrContractMonth, c.strike,
                    c.right, c.multiplier, c.exchange,
                    c.primaryExchange, c.currency,
                    c.localSymbol, c.tradingClass))
            elif type(field) is list:
                # list of TagValue
                s = ''.join(f'{v.tag}={v.value};' for v in field)
            elif type(field) is bool:
                s = '1' if field else '0'
            else:
                s = str(field)

            result.write(s)
            result.write('\0')
        return result.getvalue()

    def _decode(self, fields):
        """
        Decode the fields of the single response and call the appropriate
        callback handler.
        """
        msgId = int(fields[0])

        # bypass the ibapi decoder for ticks for more efficiency
        if msgId == 2:
            _, _, reqId, tickType, size = fields
            self.wrapper.tickSize(
                int(reqId), int(tickType), int(size))
            return
        elif msgId == 1:
            if self._priceSizeTick:
                _, _, reqId, tickType, price, size, _ = fields
                if price:
                    self._priceSizeTick(
                        int(reqId), int(tickType),
                        float(price), int(size))
                return
        elif msgId == 12:
            _, _, reqId, position, operation, side, price, size = fields
            self.wrapper.updateMktDepth(
                int(reqId), int(position),
                int(operation), int(side), float(price), int(size))
            return
        elif msgId == 46:
            _, _, reqId, tickType, value = fields
            self.wrapper.tickString(
                int(reqId), int(tickType), value.decode())
            return

        # snoop for nextValidId and managedAccounts response,
        # when both are in then the client is ready
        elif msgId == 9:
            _, _, validId = fields
            self._reqIdSeq = int(validId)
            if self._accounts:
                self._readyEvent.set()
        elif msgId == 15:
            _, _, accts = fields
            self._accounts = [a for a in accts.decode().split(',') if a]
            if self._reqIdSeq:
                self._readyEvent.set()

        self.decoder.interpret(fields)

    def reqMktData(
            self, reqId, contract, genericTickList, snapshot,
            regulatorySnapshot, mktDataOptions):
        fields = [1, 11, reqId, contract]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(contract.comboLegs)]
            for leg in legs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [
            genericTickList, snapshot, regulatorySnapshot, mktDataOptions]
        self.send(*fields)

    def cancelMktData(self, reqId):
        self.send(2, 2, reqId)

    def placeOrder(self, orderId, contract, order):
        version = self.serverVersion()
        fields = [3]
        if version < 145:
            fields += [27]
        fields += [
            orderId,
            contract,
            contract.secIdType,
            contract.secId,
            order.action,
            order.totalQuantity,
            order.orderType,
            order.lmtPrice,
            order.auxPrice,
            order.tif,
            order.ocaGroup,
            order.account,
            order.openClose,
            order.origin,
            order.orderRef,
            order.transmit,
            order.parentId,
            order.blockOrder,
            order.sweepToFill,
            order.displaySize,
            order.triggerMethod,
            order.outsideRth,
            order.hidden]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [
                    leg.conId,
                    leg.ratio,
                    leg.action,
                    leg.exchange,
                    leg.openClose,
                    leg.shortSaleSlot,
                    leg.designatedLocation,
                    leg.exemptCode]

            legs = order.orderComboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.price]

            params = order.smartComboRoutingParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            '',
            order.discretionaryAmt,
            order.goodAfterTime,
            order.goodTillDate,
            order.faGroup,
            order.faMethod,
            order.faPercentage,
            order.faProfile,
            order.modelCode,
            order.shortSaleSlot,
            order.designatedLocation,
            order.exemptCode,
            order.ocaType,
            order.rule80A,
            order.settlingFirm,
            order.allOrNone,
            order.minQty,
            order.percentOffset,
            order.eTradeOnly,
            order.firmQuoteOnly,
            order.nbboPriceCap,
            order.auctionStrategy,
            order.startingPrice,
            order.stockRefPrice,
            order.delta,
            order.stockRangeLower,
            order.stockRangeUpper,
            order.overridePercentageConstraints,
            order.volatility,
            order.volatilityType,
            order.deltaNeutralOrderType,
            order.deltaNeutralAuxPrice]

        if order.deltaNeutralOrderType:
            fields += [
                order.deltaNeutralConId,
                order.deltaNeutralSettlingFirm,
                order.deltaNeutralClearingAccount,
                order.deltaNeutralClearingIntent,
                order.deltaNeutralOpenClose,
                order.deltaNeutralShortSale,
                order.deltaNeutralShortSaleSlot,
                order.deltaNeutralDesignatedLocation]

        fields += [
            order.continuousUpdate,
            order.referencePriceType,
            order.trailStopPrice,
            order.trailingPercent,
            order.scaleInitLevelSize,
            order.scaleSubsLevelSize,
            order.scalePriceIncrement]

        if (order.scalePriceIncrement != UNSET_DOUBLE
                and order.scalePriceIncrement > 0.0):
            fields += [
                order.scalePriceAdjustValue,
                order.scalePriceAdjustInterval,
                order.scaleProfitOffset,
                order.scaleAutoReset,
                order.scaleInitPosition,
                order.scaleInitFillQty,
                order.scaleRandomPercent]

        fields += [
            order.scaleTable,
            order.activeStartTime,
            order.activeStopTime,
            order.hedgeType]

        if order.hedgeType:
            fields += [order.hedgeParam]

        fields += [
            order.optOutSmartRouting,
            order.clearingAccount,
            order.clearingIntent,
            order.notHeld]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [order.algoStrategy]
        if order.algoStrategy:
            params = order.algoParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            order.algoId,
            order.whatIf,
            order.orderMiscOptions,
            order.solicited,
            order.randomizeSize,
            order.randomizePrice]

        if order.orderType == 'PEG BENCH':
            fields += [
                order.referenceContractId,
                order.isPeggedChangeAmountDecrease,
                order.peggedChangeAmount,
                order.referenceChangeAmount,
                order.referenceExchangeId]

        fields += [order.conditions]
        if order.conditions:
            for cond in order.conditions:
                fields += [cond.type()]
                fields += cond.make_fields()
            fields += [
                order.conditionsIgnoreRth,
                order.conditionsCancelOrder]

        fields += [
            order.adjustedOrderType,
            order.triggerPrice,
            order.lmtPriceOffset,
            order.adjustedStopPrice,
            order.adjustedStopLimitPrice,
            order.adjustedTrailingAmount,
            order.adjustableTrailingUnit,
            order.extOperator,
            order.softDollarTier.name,
            order.softDollarTier.val,
            order.cashQty]

        if version >= 138:
            fields += [order.mifid2DecisionMaker, order.mifid2DecisionAlgo]
        if version >= 139:
            fields += [order.mifid2ExecutionTrader, order.mifid2ExecutionAlgo]
        if version >= 141:
            fields += [order.dontUseAutoPriceForHedge]
        if version >= 145:
            fields += [order.isOmsContainer]
        if version >= 148:
            fields += [order.discretionaryUpToLimitPrice]
        if version >= 151:
            fields += [order.usePriceMgmtAlgo]

        self.send(*fields)

    def cancelOrder(self, orderId):
        self.send(4, 1, orderId)

    def reqOpenOrders(self):
        self.send(5, 1)

    def reqAccountUpdates(self, subscribe, acctCode):
        self.send(6, 2, subscribe, acctCode)

    def reqExecutions(self, reqId, execFilter):
        self.send(
            7, 3, reqId,
            execFilter.clientId,
            execFilter.acctCode,
            execFilter.time,
            execFilter.symbol,
            execFilter.secType,
            execFilter.exchange,
            execFilter.side)

    def reqIds(self, numIds):
        self.send(8, 1)

    def reqContractDetails(self, reqId, contract):
        self.send(
            9, 8, reqId, contract, contract.includeExpired,
            contract.secIdType, contract.secId)

    def reqMktDepth(
            self, reqId, contract, numRows, isSmartDepth, mktDepthOptions):
        self.send(
            10, 5, reqId, contract, numRows, isSmartDepth, mktDepthOptions)

    def cancelMktDepth(self, reqId, isSmartDepth):
        self.send(11, 1, reqId, isSmartDepth)

    def reqNewsBulletins(self, allMsgs):
        self.send(12, 1, allMsgs)

    def cancelNewsBulletins(self):
        self.send(13, 1)

    def reqAutoOpenOrders(self, bAutoBind):
        self.send(15, 1, bAutoBind)

    def reqAllOpenOrders(self):
        self.send(16, 1)

    def reqManagedAccts(self):
        self.send(17, 1)

    def requestFA(self, faData):
        self.send(18, 1, faData)

    def replaceFA(self, faData, cxml):
        self.send(19, 1, faData, cxml)

    def reqHistoricalData(
            self, reqId, contract, endDateTime, durationStr, barSizeSetting,
            whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        fields = [20]
        if self.serverVersion() < 124:
            fields += [6]
        fields += [
            reqId, contract, contract.includeExpired,
            endDateTime, barSizeSetting, durationStr, useRTH,
            whatToShow, formatDate]

        if contract.secType == 'BAG':
            fields += [len(contract.comboLegs)]
            for leg in contract.comboLegs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        fields += [keepUpToDate, chartOptions]
        self.send(*fields)

    def exerciseOptions(
            self, reqId, contract, exerciseAction,
            exerciseQuantity, account, override):
        self.send(
            21, 2, contract, exerciseAction,
            exerciseQuantity, account, override)

    def cancelHistoricalData(self, reqId):
        self.send(25, 1, reqId)

    def reqCurrentTime(self):
        self.send(49, 1)

    def calculateImpliedVolatility(
            self, reqId, contract, optionPrice, underPrice, implVolOptions):
        self.send(
            54, 3, reqId, contract, optionPrice, underPrice,
            len(implVolOptions), implVolOptions)

    def calculateOptionPrice(
            self, reqId, contract, volatility, underPrice, optPrcOptions):
        self.send(
            55, 3, reqId, contract, volatility, underPrice,
            len(optPrcOptions), optPrcOptions)

    def cancelCalculateImpliedVolatility(self, reqId):
        self.send(56, 1, reqId)

    def cancelCalculateOptionPrice(self, reqId):
        self.send(57, 1, reqId)

    def reqGlobalCancel(self):
        self.send(58, 1)

    def reqMarketDataType(self, marketDataType):
        self.send(59, 1)

    def reqPositions(self):
        self.send(61, 1)

    def reqAccountSummary(self, reqId, groupName, tags):
        self.send(62, 1, reqId, groupName, tags)

    def cancelAccountSummary(self, reqId):
        self.send(63, 1, reqId)

    def cancelPositions(self):
        self.send(64, 1)

    def reqPositionsMulti(self, reqId, account, modelCode):
        self.send(74, 1, reqId, account, modelCode)

    def cancelPositionsMulti(self, reqId):
        self.send(75, 1, reqId)

    def reqAccountUpdatesMulti(self, reqId, account, modelCode, ledgerAndNLV):
        self.send(76, 1, reqId, account, modelCode, ledgerAndNLV)

    def cancelAccountUpdatesMulti(self, reqId):
        self.send(77, 1, reqId)

    def reqMktDepthExchanges(self):
        self.send(82)

    def reqSmartComponents(self, reqId, bboExchange):
        self.send(83, reqId, bboExchange)

    def reqHeadTimeStamp(
            self, reqId, contract, whatToShow, useRTH, formatDate):
        self.send(
            87, reqId, contract, contract.includeExpired,
            useRTH, whatToShow, formatDate)

    def cancelHeadTimeStamp(self, reqId):
        self.send(90, reqId)

    def reqMarketRule(self, marketRuleId):
        self.send(91, marketRuleId)

    def reqPnL(self, reqId, account, modelCode):
        self.send(92, reqId, account, modelCode)

    def cancelPnL(self, reqId):
        self.send(93, reqId)

    def reqPnLSingle(self, reqId, account, modelCode, conid):
        self.send(94, reqId, account, modelCode, conid)

    def cancelPnLSingle(self, reqId: int):
        self.send(95, reqId)

    def reqTickByTickData(
            self, reqId, contract, tickType, numberOfTicks, ignoreSize):
        self.send(97, contract, tickType, numberOfTicks, ignoreSize)

    def cancelTickByTickData(self, reqId):
        self.send(98, reqId)


class Connection:
    """
    Replacement for ibapi.connection.Connection that uses asyncio.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.numBytesSent = 0
        self.numMsgSent = 0
        self._logger = logging.getLogger('ib_insync.connection')

        # the following are callbacks for socket events
        self.connected = None
        self.disconnected = None
        self.hasError = None
        self.hasData = None

    def _onConnectionCreated(self, future):
        if not future.exception():
            _, self.socket = future.result()
            self.connected()

    def connect(self):
        loop = asyncio.get_event_loop()
        coro = loop.create_connection(
            lambda: Socket(self), self.host, self.port)
        future = asyncio.ensure_future(coro)
        future.add_done_callback(self._onConnectionCreated)
        return future

    def disconnect(self):
        if self.socket:
            self.socket.transport.close()
            self.socket = None

    def isConnected(self):
        return self.socket is not None

    def sendMsg(self, msg):
        self.socket.transport.write(msg)
        self.numBytesSent += len(msg)
        self.numMsgSent += 1
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(
                '>>> %s', ','.join(f.decode() for f in msg[4:].split(b'\0')))


class Socket(asyncio.Protocol):

    def __init__(self, connection):
        self.transport = None
        self.connection = connection

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        if exc:
            self.connection.hasError(exc.strerror)
        else:
            self.connection.disconnected()

    def data_received(self, data):
        self.connection.hasData(data)


class TestClient(Client, EWrapper):
    """
    Test to connect to a running TWS or gateway server.
    """
    def __init__(self):
        Client.__init__(self, wrapper=self)

    @iswrapper
    def managedAccounts(self, accountsList):
        print(self.__class__.__name__, accountsList)


if __name__ == '__main__':
    util.logToConsole(logging.DEBUG)
    client = TestClient()
    client.connect(host='127.0.0.1', port=7497, clientId=1)
    client.disconnect()
