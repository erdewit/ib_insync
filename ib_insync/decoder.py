"""Deserialize and dispatch messages."""

import dataclasses
import logging
from datetime import datetime, timezone
from typing import Any, cast

from .contract import (
    ComboLeg, Contract, ContractDescription, ContractDetails,
    DeltaNeutralContract)
from .objects import (
    BarData, CommissionReport, DepthMktDataDescription, Execution, FamilyCode,
    HistogramData, HistoricalSession, HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast, NewsProvider, PriceIncrement, SmartComponent,
    SoftDollarTier, TagValue, TickAttribBidAsk, TickAttribLast)
from .order import Order, OrderComboLeg, OrderCondition, OrderState
from .util import UNSET_DOUBLE, ZoneInfo, parseIBDatetime
from .wrapper import Wrapper


class Decoder:
    """Decode IB messages and invoke corresponding wrapper methods."""

    def __init__(self, wrapper: Wrapper, serverVersion: int):
        self.wrapper = wrapper
        self.serverVersion = serverVersion
        self.logger = logging.getLogger('ib_insync.Decoder')
        self.handlers = {
            1: self.priceSizeTick,
            2: self.wrap(
                'tickSize', [int, int, float]),
            3: self.wrap(
                'orderStatus', [
                    int, str, float, float, float, int, int,
                    float, int, str, float], skip=1),
            4: self.errorMsg,
            5: self.openOrder,
            6: self.wrap(
                'updateAccountValue', [str, str, str, str]),
            7: self.updatePortfolio,
            8: self.wrap(
                'updateAccountTime', [str]),
            9: self.wrap(
                'nextValidId', [int]),
            10: self.contractDetails,
            11: self.execDetails,
            12: self.wrap(
                'updateMktDepth', [int, int, int, int, float, float]),
            13: self.wrap(
                'updateMktDepthL2',
                [int, int, str, int, int, float, float, bool]),
            14: self.wrap(
                'updateNewsBulletin', [int, int, str, str]),
            15: self.wrap(
                'managedAccounts', [str]),
            16: self.wrap(
                'receiveFA', [int, str]),
            17: self.historicalData,
            18: self.bondContractDetails,
            19: self.wrap(
                'scannerParameters', [str]),
            20: self.scannerData,
            21: self.tickOptionComputation,
            45: self.wrap(
                'tickGeneric', [int, int, float]),
            46: self.wrap(
                'tickString', [int, int, str]),
            47: self.wrap(
                'tickEFP',
                [int, int, float, str, float, int, str, float, float]),
            49: self.wrap(
                'currentTime', [int]),
            50: self.wrap(
                'realtimeBar',
                [int, int, float, float, float, float, float, float, int]),
            51: self.wrap(
                'fundamentalData', [int, str]),
            52: self.wrap(
                'contractDetailsEnd', [int]),
            53: self.wrap(
                'openOrderEnd', []),
            54: self.wrap(
                'accountDownloadEnd', [str]),
            55: self.wrap(
                'execDetailsEnd', [int]),
            56: self.deltaNeutralValidation,
            57: self.wrap(
                'tickSnapshotEnd', [int]),
            58: self.wrap(
                'marketDataType', [int, int]),
            59: self.commissionReport,
            61: self.position,
            62: self.wrap(
                'positionEnd', []),
            63: self.wrap(
                'accountSummary', [int, str, str, str, str]),
            64: self.wrap(
                'accountSummaryEnd', [int]),
            65: self.wrap(
                'verifyMessageAPI', [str]),
            66: self.wrap(
                'verifyCompleted', [bool, str]),
            67: self.wrap(
                'displayGroupList', [int, str]),
            68: self.wrap(
                'displayGroupUpdated', [int, str]),
            69: self.wrap(
                'verifyAndAuthMessageAPI', [str, str]),
            70: self.wrap(
                'verifyAndAuthCompleted', [bool, str]),
            71: self.positionMulti,
            72: self.wrap(
                'positionMultiEnd', [int]),
            73: self.wrap(
                'accountUpdateMulti', [int, str, str, str, str, str]),
            74: self.wrap(
                'accountUpdateMultiEnd', [int]),
            75: self.securityDefinitionOptionParameter,
            76: self.wrap(
                'securityDefinitionOptionParameterEnd', [int], skip=1),
            77: self.softDollarTiers,
            78: self.familyCodes,
            79: self.symbolSamples,
            80: self.mktDepthExchanges,
            81: self.wrap(
                'tickReqParams', [int, float, str, int], skip=1),
            82: self.smartComponents,
            83: self.wrap(
                'newsArticle', [int, int, str], skip=1),
            84: self.wrap(
                'tickNews', [int, int, str, str, str, str], skip=1),
            85: self.newsProviders,
            86: self.wrap(
                'historicalNews', [int, str, str, str, str], skip=1),
            87: self.wrap(
                'historicalNewsEnd', [int, bool], skip=1),
            88: self.wrap(
                'headTimestamp', [int, str], skip=1),
            89: self.histogramData,
            90: self.historicalDataUpdate,
            91: self.wrap(
                'rerouteMktDataReq', [int, int, str], skip=1),
            92: self.wrap(
                'rerouteMktDepthReq', [int, int, str], skip=1),
            93: self.marketRule,
            94: self.wrap(
                'pnl', [int, float, float, float], skip=1),
            95: self.wrap(
                'pnlSingle', [int, float, float, float, float, float], skip=1),
            96: self.historicalTicks,
            97: self.historicalTicksBidAsk,
            98: self.historicalTicksLast,
            99: self.tickByTick,
            100: self.wrap(
                'orderBound', [int, int, int], skip=1),
            101: self.completedOrder,
            102: self.wrap(
                'completedOrdersEnd', [], skip=1),
            103: self.wrap(
                'replaceFAEnd', [int, str], skip=1),
            104: self.wrap(
                'wshMetaData', [int, str], skip=1),
            105: self.wrap(
                'wshEventData', [int, str], skip=1),
            106: self.historicalSchedule,
            107: self.wrap(
                'userInfo', [int, str], skip=1)
        }

    def wrap(self, methodName, types, skip=2):
        """
        Create a message handler that invokes a wrapper method
        with the in-order message fields as parameters, skipping over
        the first ``skip`` fields, and parsed according to the ``types`` list.
        """

        def handler(fields):
            method = getattr(self.wrapper, methodName, None)
            if method:
                try:
                    args = [
                        field if typ is str else
                        int(field or 0) if typ is int else
                        float(field or 0) if typ is float else
                        bool(int(field or 0))
                        for (typ, field) in zip(types, fields[skip:])]
                    method(*args)
                except Exception:
                    self.logger.exception(f'Error for {methodName}:')

        return handler

    def interpret(self, fields):
        """Decode fields and invoke corresponding wrapper method."""
        try:
            msgId = int(fields[0])
            handler = self.handlers[msgId]
            handler(fields)
        except Exception:
            self.logger.exception(f'Error handling fields: {fields}')

    def parse(self, obj):
        """Parse the object's properties according to its default types."""
        for field in dataclasses.fields(obj):
            typ = type(field.default)
            if typ is str:
                continue
            v = getattr(obj, field.name)
            if typ is int:
                setattr(obj, field.name, int(v) if v else field.default)
            elif typ is float:
                setattr(obj, field.name, float(v) if v else field.default)
            elif typ is bool:
                setattr(obj, field.name, bool(int(v)) if v else field.default)

    def priceSizeTick(self, fields):
        _, _, reqId, tickType, price, size, _ = fields

        if price:
            self.wrapper.priceSizeTick(
                int(reqId), int(tickType), float(price), float(size or 0))

    def errorMsg(self, fields):
        _, _, reqId, errorCode, errorString, *fields = fields
        advancedOrderRejectJson = ''
        if self.serverVersion >= 166:
            advancedOrderRejectJson, *fields = fields
        self.wrapper.error(
            int(reqId), int(errorCode), errorString, advancedOrderRejectJson)

    def updatePortfolio(self, fields):
        c = Contract()
        (
            _, _,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.primaryExchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            marketPrice,
            marketValue,
            averageCost,
            unrealizedPNL,
            realizedPNL,
            accountName) = fields

        self.parse(c)
        self.wrapper.updatePortfolio(
            c, float(position), float(marketPrice),
            float(marketValue), float(averageCost), float(unrealizedPNL),
            float(realizedPNL), accountName)

    def contractDetails(self, fields):
        cd = ContractDetails()
        cd.contract = c = Contract()
        if self.serverVersion < 164:
            fields.pop(0)
        (
            _,
            reqId,
            c.symbol,
            c.secType,
            lastTimes,
            c.strike,
            c.right,
            c.exchange,
            c.currency,
            c.localSymbol,
            cd.marketName,
            c.tradingClass,
            c.conId,
            cd.minTick,
            *fields) = fields
        if self.serverVersion < 164:
            fields.pop(0)  # obsolete mdSizeMultiplier
        (
            c.multiplier,
            cd.orderTypes,
            cd.validExchanges,
            cd.priceMagnifier,
            cd.underConId,
            cd.longName,
            c.primaryExchange,
            cd.contractMonth,
            cd.industry,
            cd.category,
            cd.subcategory,
            cd.timeZoneId,
            cd.tradingHours,
            cd.liquidHours,
            cd.evRule,
            cd.evMultiplier,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]
        (
            cd.aggGroup,
            cd.underSymbol,
            cd.underSecType,
            cd.marketRuleIds,
            cd.realExpirationDate,
            cd.stockType,
            *fields) = fields
        if self.serverVersion == 163:
            cd.suggestedSizeIncrement, *fields = fields
        if self.serverVersion >= 164:
            (
                cd.minSize,
                cd.sizeIncrement,
                cd.suggestedSizeIncrement,
                # cd.minCashQtySize,
                *fields) = fields

        times = lastTimes.split('-' if '-' in lastTimes else None)
        if len(times) > 0:
            c.lastTradeDateOrContractMonth = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]

        cd.longName = cd.longName.encode().decode('unicode-escape')
        self.parse(cd)
        self.parse(c)
        self.wrapper.contractDetails(int(reqId), cd)

    def bondContractDetails(self, fields):
        cd = ContractDetails()
        cd.contract = c = Contract()
        if self.serverVersion < 164:
            fields.pop(0)
        (
            _,
            reqId,
            c.symbol,
            c.secType,
            cd.cusip,
            cd.coupon,
            lastTimes,
            cd.issueDate,
            cd.ratings,
            cd.bondType,
            cd.couponType,
            cd.convertible,
            cd.callable,
            cd.putable,
            cd.descAppend,
            c.exchange,
            c.currency,
            cd.marketName,
            c.tradingClass,
            c.conId,
            cd.minTick,
            *fields) = fields
        if self.serverVersion < 164:
            fields.pop(0)  # obsolete mdSizeMultiplier
        (
            cd.orderTypes,
            cd.validExchanges,
            cd.nextOptionDate,
            cd.nextOptionType,
            cd.nextOptionPartial,
            cd.notes,
            cd.longName,
            cd.evRule,
            cd.evMultiplier,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]

        cd.aggGroup, cd.marketRuleIds, *fields = fields
        if self.serverVersion >= 164:
            (
                cd.minSize,
                cd.sizeIncrement,
                cd.suggestedSizeIncrement,
                # cd.minCashQtySize,
                *fields) = fields

        times = lastTimes.split('-' if '-' in lastTimes else None)
        if len(times) > 0:
            cd.maturity = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]
        if len(times) > 2:
            cd.timeZoneId = times[2]

        self.parse(cd)
        self.parse(c)
        self.wrapper.bondContractDetails(int(reqId), cd)

    def execDetails(self, fields):
        c = Contract()
        ex = Execution()
        (
            _,
            reqId,
            ex.orderId,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            ex.execId,
            timeStr,
            ex.acctNumber,
            ex.exchange,
            ex.side,
            ex.shares,
            ex.price,
            ex.permId,
            ex.clientId,
            ex.liquidation,
            ex.cumQty,
            ex.avgPrice,
            ex.orderRef,
            ex.evRule,
            ex.evMultiplier,
            ex.modelCode,
            ex.lastLiquidity) = fields

        self.parse(c)
        self.parse(ex)
        time = cast(datetime, parseIBDatetime(timeStr))
        if not time.tzinfo:
            tz = self.wrapper.ib.TimezoneTWS
            if tz:
                time = time.replace(tzinfo=ZoneInfo(str(tz)))
        ex.time = time.astimezone(timezone.utc)
        self.wrapper.execDetails(int(reqId), c, ex)

    def historicalData(self, fields):
        _, reqId, startDateStr, endDateStr, numBars, *fields = fields
        get = iter(fields).__next__

        for _ in range(int(numBars)):
            bar = BarData(
                date=get(),
                open=float(get()),
                high=float(get()),
                low=float(get()),
                close=float(get()),
                volume=float(get()),
                average=float(get()),
                barCount=int(get()))
            self.wrapper.historicalData(int(reqId), bar)

        self.wrapper.historicalDataEnd(int(reqId), startDateStr, endDateStr)

    def historicalDataUpdate(self, fields):
        _, reqId, *fields = fields
        get = iter(fields).__next__

        bar = BarData(
            barCount=int(get() or 0),
            date=get(),
            open=float(get() or 0),
            close=float(get() or 0),
            high=float(get() or 0),
            low=float(get() or 0),
            average=float(get() or 0),
            volume=float(get() or 0))

        self.wrapper.historicalDataUpdate(int(reqId), bar)

    def scannerData(self, fields):
        _, _, reqId, n, *fields = fields

        for _ in range(int(n)):
            cd = ContractDetails()
            cd.contract = c = Contract()
            (
                rank,
                c.conId,
                c.symbol,
                c.secType,
                c.lastTradeDateOrContractMonth,
                c.strike,
                c.right,
                c.exchange,
                c.currency,
                c.localSymbol,
                cd.marketName,
                c.tradingClass,
                distance,
                benchmark,
                projection,
                legsStr,
                *fields) = fields

            self.parse(cd)
            self.parse(c)
            self.wrapper.scannerData(
                int(reqId), int(rank), cd,
                distance, benchmark, projection, legsStr)

        self.wrapper.scannerDataEnd(int(reqId))

    def tickOptionComputation(self, fields):
        _, reqId, tickTypeInt, tickAttrib, *fields = fields
        impliedVol, delta, optPrice, pvDividend, \
            gamma, vega, theta, undPrice = fields

        self.wrapper.tickOptionComputation(
            int(reqId), int(tickTypeInt), int(tickAttrib),
            float(impliedVol), float(delta), float(optPrice),
            float(pvDividend), float(gamma), float(vega),
            float(theta), float(undPrice))

    def deltaNeutralValidation(self, fields):
        _, _, reqId, conId, delta, price = fields

        self.wrapper.deltaNeutralValidation(
            int(reqId), DeltaNeutralContract(
                int(conId), float(delta or 0), float(price or 0)))

    def commissionReport(self, fields):
        _, _, execId, commission, currency, realizedPNL, \
            yield_, yieldRedemptionDate = fields

        self.wrapper.commissionReport(
            CommissionReport(
                execId, float(commission or 0), currency,
                float(realizedPNL or 0), float(yield_ or 0),
                int(yieldRedemptionDate or 0)))

    def position(self, fields):
        c = Contract()
        (
            _, _,
            account,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost) = fields

        self.parse(c)
        self.wrapper.position(
            account, c, float(position or 0), float(avgCost or 0))

    def positionMulti(self, fields):
        c = Contract()
        (
            _, _,
            reqId,
            account,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost,
            modelCode) = fields

        self.parse(c)
        self.wrapper.positionMulti(
            int(reqId), account, modelCode, c,
            float(position or 0), float(avgCost or 0))

    def securityDefinitionOptionParameter(self, fields):
        _, reqId, exchange, underlyingConId, tradingClass, multiplier, \
            n, *fields = fields
        n = int(n)

        expirations = fields[:n]
        strikes = [float(field) for field in fields[n + 1:]]

        self.wrapper.securityDefinitionOptionParameter(
            int(reqId), exchange, underlyingConId, tradingClass,
            multiplier, expirations, strikes)

    def softDollarTiers(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        tiers = [
            SoftDollarTier(
                name=get(),
                val=get(),
                displayName=get())
            for _ in range(int(n))]

        self.wrapper.softDollarTiers(int(reqId), tiers)

    def familyCodes(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        familyCodes = [
            FamilyCode(
                accountID=get(),
                familyCodeStr=get())
            for _ in range(int(n))]

        self.wrapper.familyCodes(familyCodes)

    def symbolSamples(self, fields):
        _, reqId, n, *fields = fields

        cds = []
        for _ in range(int(n)):
            cd = ContractDescription()
            cd.contract = c = Contract()
            c.conId, c.symbol, c.secType, c.primaryExchange, c.currency, \
                m, *fields = fields
            c.conId = int(c.conId)
            m = int(m)
            cd.derivativeSecTypes = fields[:m]
            fields = fields[m:]
            if self.serverVersion >= 176:
                (
                    cd.contract.description,
                    cd.contract.issuerId,
                    *fields) = fields
            cds.append(cd)

        self.wrapper.symbolSamples(int(reqId), cds)

    def smartComponents(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        components = [
            SmartComponent(
                bitNumber=int(get()),
                exchange=get(),
                exchangeLetter=get())
            for _ in range(int(n))]

        self.wrapper.smartComponents(int(reqId), components)

    def mktDepthExchanges(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        descriptions = [
            DepthMktDataDescription(
                exchange=get(),
                secType=get(),
                listingExch=get(),
                serviceDataType=get(),
                aggGroup=int(get()))
            for _ in range(int(n))]

        self.wrapper.mktDepthExchanges(descriptions)

    def newsProviders(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        providers = [
            NewsProvider(
                code=get(),
                name=get())
            for _ in range(int(n))]

        self.wrapper.newsProviders(providers)

    def histogramData(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        histogram = [
            HistogramData(
                price=float(get()),
                count=int(get()))
            for _ in range(int(n))]

        self.wrapper.histogramData(int(reqId), histogram)

    def marketRule(self, fields):
        _, marketRuleId, n, *fields = fields
        get = iter(fields).__next__

        increments = [
            PriceIncrement(
                lowEdge=float(get()),
                increment=float(get()))
            for _ in range(int(n))]

        self.wrapper.marketRule(int(marketRuleId), increments)

    def historicalTicks(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            get()
            price = float(get())
            size = float(get())
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTick(dt, price, size))

        done = bool(int(get()))
        self.wrapper.historicalTicks(int(reqId), ticks, done)

    def historicalTicksBidAsk(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            mask = int(get())
            attrib = TickAttribBidAsk(
                askPastHigh=bool(mask & 1),
                bidPastLow=bool(mask & 2))
            priceBid = float(get())
            priceAsk = float(get())
            sizeBid = float(get())
            sizeAsk = float(get())
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTickBidAsk(
                    dt, attrib, priceBid, priceAsk, sizeBid, sizeAsk))

        done = bool(int(get()))
        self.wrapper.historicalTicksBidAsk(int(reqId), ticks, done)

    def historicalTicksLast(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            mask = int(get())
            attrib = TickAttribLast(
                pastLimit=bool(mask & 1),
                unreported=bool(mask & 2))
            price = float(get())
            size = float(get())
            exchange = get()
            specialConditions = get()
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTickLast(
                    dt, attrib, price, size, exchange, specialConditions))

        done = bool(int(get()))
        self.wrapper.historicalTicksLast(int(reqId), ticks, done)

    def tickByTick(self, fields):
        _, reqId, tickType, time, *fields = fields
        reqId = int(reqId)
        tickType = int(tickType)
        time = int(time)

        if tickType in (1, 2):
            price, size, mask, exchange, specialConditions = fields
            mask = int(mask)
            attrib: Any = TickAttribLast(
                pastLimit=bool(mask & 1),
                unreported=bool(mask & 2))

            self.wrapper.tickByTickAllLast(
                reqId, tickType, time, float(price), float(size),
                attrib, exchange, specialConditions)

        elif tickType == 3:
            bidPrice, askPrice, bidSize, askSize, mask = fields
            mask = int(mask)
            attrib = TickAttribBidAsk(
                bidPastLow=bool(mask & 1),
                askPastHigh=bool(mask & 2))

            self.wrapper.tickByTickBidAsk(
                reqId, time, float(bidPrice), float(askPrice),
                float(bidSize), float(askSize), attrib)

        elif tickType == 4:
            midPoint, = fields

            self.wrapper.tickByTickMidPoint(reqId, time, float(midPoint))

    def openOrder(self, fields):
        o = Order()
        c = Contract()
        st = OrderState()
        (
            _,
            o.orderId,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            o.action,
            o.totalQuantity,
            o.orderType,
            o.lmtPrice,
            o.auxPrice,
            o.tif,
            o.ocaGroup,
            o.account,
            o.openClose,
            o.origin,
            o.orderRef,
            o.clientId,
            o.permId,
            o.outsideRth,
            o.hidden,
            o.discretionaryAmt,
            o.goodAfterTime,
            _,
            o.faGroup,
            o.faMethod,
            o.faPercentage,
            o.faProfile,
            o.modelCode,
            o.goodTillDate,
            o.rule80A,
            o.percentOffset,
            o.settlingFirm,
            o.shortSaleSlot,
            o.designatedLocation,
            o.exemptCode,
            o.auctionStrategy,
            o.startingPrice,
            o.stockRefPrice,
            o.delta,
            o.stockRangeLower,
            o.stockRangeUpper,
            o.displaySize,
            o.blockOrder,
            o.sweepToFill,
            o.allOrNone,
            o.minQty,
            o.ocaType,
            o.eTradeOnly,
            o.firmQuoteOnly,
            o.nbboPriceCap,
            o.parentId,
            o.triggerMethod,
            o.volatility,
            o.volatilityType,
            o.deltaNeutralOrderType,
            o.deltaNeutralAuxPrice,
            *fields) = fields

        if o.deltaNeutralOrderType:
            (
                o.deltaNeutralConId,
                o.deltaNeutralSettlingFirm,
                o.deltaNeutralClearingAccount,
                o.deltaNeutralClearingIntent,
                o.deltaNeutralOpenClose,
                o.deltaNeutralShortSale,
                o.deltaNeutralShortSaleSlot,
                o.deltaNeutralDesignatedLocation,
                *fields) = fields
        (
            o.continuousUpdate,
            o.referencePriceType,
            o.trailStopPrice,
            o.trailingPercent,
            o.basisPoints,
            o.basisPointsType,
            c.comboLegsDescrip,
            *fields) = fields

        numLegs = int(fields.pop(0))
        c.comboLegs = []
        for _ in range(numLegs):
            leg: Any = ComboLeg()
            (
                leg.conId,
                leg.ratio,
                leg.action,
                leg.exchange,
                leg.openClose,
                leg.shortSaleSlot,
                leg.designatedLocation,
                leg.exemptCode,
                *fields) = fields
            self.parse(leg)
            c.comboLegs.append(leg)

        numOrderLegs = int(fields.pop(0))
        o.orderComboLegs = []
        for _ in range(numOrderLegs):
            leg = OrderComboLeg()
            leg.price = fields.pop(0)
            self.parse(leg)
            o.orderComboLegs.append(leg)

        numParams = int(fields.pop(0))
        if numParams > 0:
            o.smartComboRoutingParams = []
            for _ in range(numParams):
                tag, value, *fields = fields
                o.smartComboRoutingParams.append(
                    TagValue(tag, value))

        (
            o.scaleInitLevelSize,
            o.scaleSubsLevelSize,
            increment,
            *fields) = fields

        o.scalePriceIncrement = float(increment or UNSET_DOUBLE)
        if 0 < o.scalePriceIncrement < UNSET_DOUBLE:
            (
                o.scalePriceAdjustValue,
                o.scalePriceAdjustInterval,
                o.scaleProfitOffset,
                o.scaleAutoReset,
                o.scaleInitPosition,
                o.scaleInitFillQty,
                o.scaleRandomPercent,
                *fields) = fields

        o.hedgeType = fields.pop(0)
        if o.hedgeType:
            o.hedgeParam = fields.pop(0)

        (
            o.optOutSmartRouting,
            o.clearingAccount,
            o.clearingIntent,
            o.notHeld,
            dncPresent,
            *fields) = fields

        if int(dncPresent):
            conId, delta, price, *fields = fields
            c.deltaNeutralContract = DeltaNeutralContract(
                int(conId or 0), float(delta or 0), float(price or 0))

        o.algoStrategy = fields.pop(0)
        if o.algoStrategy:
            numParams = int(fields.pop(0))
            if numParams > 0:
                o.algoParams = []
                for _ in range(numParams):
                    tag, value, *fields = fields
                    o.algoParams.append(
                        TagValue(tag, value))

        (
            o.solicited,
            o.whatIf,
            st.status,
            st.initMarginBefore,
            st.maintMarginBefore,
            st.equityWithLoanBefore,
            st.initMarginChange,
            st.maintMarginChange,
            st.equityWithLoanChange,
            st.initMarginAfter,
            st.maintMarginAfter,
            st.equityWithLoanAfter,
            st.commission,
            st.minCommission,
            st.maxCommission,
            st.commissionCurrency,
            st.warningText,
            o.randomizeSize,
            o.randomizePrice,
            *fields) = fields

        if o.orderType == 'PEG BENCH':
            (
                o.referenceContractId,
                o.isPeggedChangeAmountDecrease,
                o.peggedChangeAmount,
                o.referenceChangeAmount,
                o.referenceExchangeId,
                *fields) = fields

        numConditions = int(fields.pop(0))
        if numConditions > 0:
            for _ in range(numConditions):
                condType = int(fields.pop(0))
                condCls = OrderCondition.createClass(condType)
                n = len(dataclasses.fields(condCls)) - 1
                cond = condCls(condType, *fields[:n])
                self.parse(cond)
                o.conditions.append(cond)
                fields = fields[n:]
            (
                o.conditionsIgnoreRth,
                o.conditionsCancelOrder,
                *fields) = fields

        (
            o.adjustedOrderType,
            o.triggerPrice,
            o.trailStopPrice,
            o.lmtPriceOffset,
            o.adjustedStopPrice,
            o.adjustedStopLimitPrice,
            o.adjustedTrailingAmount,
            o.adjustableTrailingUnit,
            o.softDollarTier.name,
            o.softDollarTier.val,
            o.softDollarTier.displayName,
            o.cashQty,
            o.dontUseAutoPriceForHedge,
            o.isOmsContainer,
            o.discretionaryUpToLimitPrice,
            o.usePriceMgmtAlgo,
            *fields) = fields

        if self.serverVersion >= 159:
            o.duration = fields.pop(0)
        if self.serverVersion >= 160:
            o.postToAts = fields.pop(0)
        if self.serverVersion >= 162:
            o.autoCancelParent = fields.pop(0)
        if self.serverVersion >= 170:
            (
                o.minTradeQty,
                o.minCompeteSize,
                o.competeAgainstBestOffset,
                o.midOffsetAtWhole,
                o.midOffsetAtHalf,
                *fields) = fields

        self.parse(c)
        self.parse(o)
        self.parse(st)
        self.wrapper.openOrder(o.orderId, c, o, st)

    def completedOrder(self, fields):
        o = Order()
        c = Contract()
        st = OrderState()

        (
            _,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            o.action,
            o.totalQuantity,
            o.orderType,
            o.lmtPrice,
            o.auxPrice,
            o.tif,
            o.ocaGroup,
            o.account,
            o.openClose,
            o.origin,
            o.orderRef,
            o.permId,
            o.outsideRth,
            o.hidden,
            o.discretionaryAmt,
            o.goodAfterTime,
            o.faGroup,
            o.faMethod,
            o.faPercentage,
            o.faProfile,
            o.modelCode,
            o.goodTillDate,
            o.rule80A,
            o.percentOffset,
            o.settlingFirm,
            o.shortSaleSlot,
            o.designatedLocation,
            o.exemptCode,
            o.startingPrice,
            o.stockRefPrice,
            o.delta,
            o.stockRangeLower,
            o.stockRangeUpper,
            o.displaySize,
            o.sweepToFill,
            o.allOrNone,
            o.minQty,
            o.ocaType,
            o.triggerMethod,
            o.volatility,
            o.volatilityType,
            o.deltaNeutralOrderType,
            o.deltaNeutralAuxPrice,
            *fields) = fields

        if o.deltaNeutralOrderType:
            (
                o.deltaNeutralConId,
                o.deltaNeutralShortSale,
                o.deltaNeutralShortSaleSlot,
                o.deltaNeutralDesignatedLocation,
                *fields) = fields
        (
            o.continuousUpdate,
            o.referencePriceType,
            o.trailStopPrice,
            o.trailingPercent,
            c.comboLegsDescrip,
            *fields) = fields

        numLegs = int(fields.pop(0))
        c.comboLegs = []
        for _ in range(numLegs):
            leg: Any = ComboLeg()
            (
                leg.conId,
                leg.ratio,
                leg.action,
                leg.exchange,
                leg.openClose,
                leg.shortSaleSlot,
                leg.designatedLocation,
                leg.exemptCode,
                *fields) = fields
            self.parse(leg)
            c.comboLegs.append(leg)

        numOrderLegs = int(fields.pop(0))
        o.orderComboLegs = []
        for _ in range(numOrderLegs):
            leg = OrderComboLeg()
            leg.price = fields.pop(0)
            self.parse(leg)
            o.orderComboLegs.append(leg)

        numParams = int(fields.pop(0))
        if numParams > 0:
            o.smartComboRoutingParams = []
            for _ in range(numParams):
                tag, value, *fields = fields
                o.smartComboRoutingParams.append(
                    TagValue(tag, value))
        (
            o.scaleInitLevelSize,
            o.scaleSubsLevelSize,
            increment,
            *fields) = fields

        o.scalePriceIncrement = float(increment or UNSET_DOUBLE)
        if 0 < o.scalePriceIncrement < UNSET_DOUBLE:
            (
                o.scalePriceAdjustValue,
                o.scalePriceAdjustInterval,
                o.scaleProfitOffset,
                o.scaleAutoReset,
                o.scaleInitPosition,
                o.scaleInitFillQty,
                o.scaleRandomPercent,
                *fields) = fields

        o.hedgeType = fields.pop(0)
        if o.hedgeType:
            o.hedgeParam = fields.pop(0)

        (
            o.clearingAccount,
            o.clearingIntent,
            o.notHeld,
            dncPresent,
            *fields) = fields

        if int(dncPresent):
            conId, delta, price, *fields = fields
            c.deltaNeutralContract = DeltaNeutralContract(
                int(conId or 0), float(delta or 0), float(price or 0))

        o.algoStrategy = fields.pop(0)
        if o.algoStrategy:
            numParams = int(fields.pop(0))
            if numParams > 0:
                o.algoParams = []
                for _ in range(numParams):
                    tag, value, *fields = fields
                    o.algoParams.append(
                        TagValue(tag, value))
        (
            o.solicited,
            st.status,
            o.randomizeSize,
            o.randomizePrice,
            *fields) = fields

        if o.orderType == 'PEG BENCH':
            (
                o.referenceContractId,
                o.isPeggedChangeAmountDecrease,
                o.peggedChangeAmount,
                o.referenceChangeAmount,
                o.referenceExchangeId,
                *fields) = fields

        numConditions = int(fields.pop(0))
        if numConditions > 0:
            for _ in range(numConditions):
                condType = int(fields.pop(0))
                condCls = OrderCondition.createClass(condType)
                n = len(dataclasses.fields(condCls)) - 1
                cond = condCls(condType, *fields[:n])
                self.parse(cond)
                o.conditions.append(cond)
                fields = fields[n:]
            (
                o.conditionsIgnoreRth,
                o.conditionsCancelOrder,
                *fields) = fields

        (
            o.trailStopPrice,
            o.lmtPriceOffset,
            o.cashQty,
            o.dontUseAutoPriceForHedge,
            o.isOmsContainer,
            o.autoCancelDate,
            o.filledQuantity,
            o.refFuturesConId,
            o.autoCancelParent,
            o.shareholder,
            o.imbalanceOnly,
            o.routeMarketableToBbo,
            o.parentPermId,
            st.completedTime,
            st.completedStatus,
            *fields) = fields

        if self.serverVersion >= 170:
            (
                o.minTradeQty,
                o.minCompeteSize,
                o.competeAgainstBestOffset,
                o.midOffsetAtWhole,
                o.midOffsetAtHalf,
                *fields) = fields

        self.parse(c)
        self.parse(o)
        self.parse(st)
        self.wrapper.completedOrder(c, o, st)

    def historicalSchedule(self, fields):
        (
            _,
            reqId,
            startDateTime,
            endDateTime,
            timeZone,
            count, *fields) = fields
        get = iter(fields).__next__
        sessions = [HistoricalSession(
            startDateTime=get(), endDateTime=get(), refDate=get())
            for _ in range(int(count))]
        self.wrapper.historicalSchedule(
            int(reqId), startDateTime, endDateTime, timeZone, sessions)
