import logging

from .contract import Contract
from .order import Order, OrderCondition
from .objects import (
    ContractDetails, ContractDescription, ComboLeg, OrderComboLeg,
    OrderState, TagValue, Execution, CommissionReport,
    BarData, DeltaNeutralContract, SoftDollarTier, FamilyCode,
    SmartComponent, DepthMktDataDescription, NewsProvider,
    TickAttribBidAsk, TickAttribLast, HistogramData, PriceIncrement,
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast)
from .util import UNSET_DOUBLE, UNSET_INTEGER

__all__ = ['Decoder']


_parseFunc = {
    'f': lambda s: float(s or 0),
    'fu': lambda s: float(s or UNSET_DOUBLE),
    'i': lambda s: int(s or 0),
    'iu': lambda s: int(s or UNSET_INTEGER),
    'b': lambda s: bool(int(s or 0))}


class Parser:

    def dict(self):
        d = {}
        for k, v in self.__dict__.items():
            if '_' in k:
                k, postfix = k.split('_')
                v = _parseFunc[postfix](v)
            d[k] = v
        return d


class Decoder:

    def __init__(self, wrapper, serverVersion):
        self.wrapper = wrapper
        self.serverVersion = serverVersion
        self.logger = logging.getLogger('ib_insync.Decoder')
        self.handlers = {
            1: self.priceSizeTick,
            2: self.wrap(
                'tickSize', [int, int, int]),
            3: self.wrap(
                'orderStatus', [
                    int, str, float, float, float, int, int,
                    float, int, str, float], skip=1),
            4: self.wrap(
                'error', [int, int, str]),
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
                'updateMktDepth', [int, int, int, int, float, int]),
            13: self.wrap(
                'updateMktDepthL2',
                [int, int, str, int, int, float, int, bool]),
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
                [int, int, float, float, float, float, int, float, int]),
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
                'pnlSingle', [int, int, float, float, float, float], skip=1),
            96: self.historicalTicks,
            97: self.historicalTicksBidAsk,
            98: self.historicalTicksLast,
            99: self.tickByTick,
            100: self.wrap(
                'orderBound', [int, int, int], skip=1),
            101: self.completedOrder,
            102: self.wrap(
                'completedOrdersEnd', [], skip=1),
        }

    def wrap(self, methodName, types, skip=2):

        def handler(fields):
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

        method = getattr(self.wrapper, methodName, None)
        return handler if method else lambda *args: None

    def interpret(self, fields):
        msgId = int(fields[0])
        handler = self.handlers[msgId]
        handler(fields)

    def priceSizeTick(self, fields):
        _, _, reqId, tickType, price, size, _ = fields

        if price:
            self.wrapper.priceSizeTick(
                int(reqId), int(tickType), float(price), int(size))

    def updatePortfolio(self, fields):
        c = Parser()
        (
            _, _,
            c.conId_i,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike_f,
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

        contract = Contract(**c.dict())
        self.wrapper.updatePortfolio(
            contract, float(position), float(marketPrice),
            float(marketValue), float(averageCost), float(unrealizedPNL),
            float(realizedPNL), accountName)

    def contractDetails(self, fields):
        cd = Parser()
        cd.contract = c = Parser()
        (
            _, _,
            reqId,
            c.symbol,
            c.secType,
            lastTimes,
            c.strike_f,
            c.right,
            c.exchange,
            c.currency,
            c.localSymbol,
            cd.marketName,
            c.tradingClass,
            c.conId_i,
            cd.minTick_f,
            cd.mdSizeMultiplier_i,
            c.multiplier,
            cd.orderTypes,
            cd.validExchanges,
            cd.priceMagnifier,
            cd.underConId_i,
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
            cd.evMultiplier_i,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]
        (
            cd.aggGroup_i,
            cd.underSymbol,
            cd.underSecType,
            cd.marketRuleIds,
            cd.realExpirationDate) = fields

        times = lastTimes.split()
        if len(times) > 0:
            c.lastTradeDateOrContractMonth = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]

        contractDetails = ContractDetails(**cd.dict())
        contractDetails.contract = Contract(**c.dict())
        self.wrapper.contractDetails(int(reqId), contractDetails)

    def bondContractDetails(self, fields):
        cd = Parser()
        cd.contract = c = Parser()
        (
            _, _,
            reqId,
            c.symbol,
            c.secType,
            cd.cusip,
            cd.coupon_i,
            lastTimes,
            cd.issueDate,
            cd.ratings,
            cd.bondType,
            cd.couponType,
            cd.convertible_b,
            cd.callable_b,
            cd.putable_b,
            cd.descAppend,
            c.exchange,
            c.currency,
            cd.marketName,
            c.tradingClass,
            c.conId_i,
            cd.minTick_f,
            cd.mdSizeMultiplier_i,
            cd.orderTypes,
            cd.validExchanges,
            cd.nextOptionDate,
            cd.nextOptionType,
            cd.nextOptionPartial_b,
            cd.notes,
            cd.longName,
            cd.evRule,
            cd.evMultiplier_i,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]

        cd.aggGroup_i, cd.marketRuleIds = fields

        times = lastTimes.split()
        if len(times) > 0:
            cd.maturity = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]
        if len(times) > 2:
            cd.timeZoneId = times[2]

        contractDetails = ContractDetails(**cd.dict())
        contractDetails.contract = Contract(**c.dict())
        self.wrapper.bondContractDetails(int(reqId), contractDetails)

    def execDetails(self, fields):
        c = Parser()
        ex = Parser()
        (
            _,
            reqId,
            ex.orderId_i,
            c.conId_i,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike_f,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            ex.execId,
            ex.time,
            ex.acctNumber,
            ex.exchange,
            ex.side,
            ex.shares_f,
            ex.price_f,
            ex.permId_i,
            ex.clientId_i,
            ex.liquidation_i,
            ex.cumQty_f,
            ex.avgPrice_f,
            ex.orderRef,
            ex.evRule,
            ex.evMultiplier_f,
            ex.modelCode,
            ex.lastLiquidity_i) = fields

        contract = Contract(**c.dict())
        execution = Execution(**ex.dict())
        self.wrapper.execDetails(int(reqId), contract, execution)

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
                volume=int(get()),
                average=float(get()),
                barCount=int(get()))
            self.wrapper.historicalData(int(reqId), bar)

        self.wrapper.historicalDataEnd(int(reqId), startDateStr, endDateStr)

    def historicalDataUpdate(self, fields):
        _, reqId, *fields = fields
        get = iter(fields).__next__

        bar = BarData(
            barCount=int(get()),
            date=get(),
            open=float(get()),
            close=float(get()),
            high=float(get()),
            low=float(get()),
            average=float(get()),
            volume=int(get()))

        self.wrapper.historicalDataUpdate(int(reqId), bar)

    def scannerData(self, fields):
        _, _, reqId, n, *fields = fields

        for _ in range(int(n)):
            cd = Parser()
            c = Parser()
            (
                rank,
                c.conId_i,
                c.symbol,
                c.secType,
                c.lastTradeDateOrContractMonth,
                c.strike,
                c.right_f,
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

            contractDetails = ContractDetails(**cd.dict())
            contractDetails.contract = Contract(**c.dict())
            self.wrapper.scannerData(
                int(reqId), int(rank), contractDetails,
                distance, benchmark, projection, legsStr)

        self.wrapper.scannerDataEnd(int(reqId))

    def tickOptionComputation(self, fields):
        _, _, reqId, tickTypeInt, impliedVol, delta, optPrice, \
            pvDividend, gamma, vega, theta, undPrice = fields

        self.wrapper.tickOptionComputation(
            int(reqId), int(tickTypeInt),
            float(impliedVol) if impliedVol != '-1' else None,
            float(delta) if delta != '-2' else None,
            float(optPrice) if optPrice != '-1' else None,
            float(pvDividend) if pvDividend != '-1' else None,
            float(gamma) if gamma != '-2' else None,
            float(vega) if vega != '-2' else None,
            float(theta) if theta != '-2' else None,
            float(undPrice) if undPrice != '-1' else None)

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
        c = Parser()
        (
            _, _,
            account,
            c.conId_i,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike_f,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost) = fields

        contract = Contract(**c.dict())
        self.wrapper.position(
            account, contract, float(position or 0), float(avgCost or 0))

    def positionMulti(self, fields):
        c = Parser()
        (
            _, _,
            reqId,
            orderId,
            account,
            c.conId_i,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike_f,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost,
            modelCode) = fields

        contract = Contract(**c.dict())
        self.wrapper.positionMulti(
            int(reqId), account, modelCode, contract,
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
            size = int(get())
            ticks.append(
                HistoricalTick(time, price, size))

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
            sizeBid = int(get())
            sizeAsk = int(get())
            ticks.append(
                HistoricalTickBidAsk(
                    time, attrib, priceBid, priceAsk, sizeBid, sizeAsk))

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
            size = int(get())
            exchange = get()
            specialConditions = get()
            ticks.append(
                HistoricalTickLast(
                    time, attrib, price, size, exchange, specialConditions))

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
            attrib = TickAttribLast(
                pastLimit=bool(mask & 1),
                unreported=bool(mask & 2))

            self.wrapper.tickByTickAllLast(
                reqId, tickType, time, float(price), int(size),
                attrib, exchange, specialConditions)

        elif tickType == 3:
            bidPrice, askPrice, bidSize, askSize, mask = fields
            mask = int(mask)
            attrib = TickAttribBidAsk(
                bidPastLow=bool(mask & 1),
                askPastHigh=bool(mask & 2))

            self.wrapper.tickByTickBidAsk(
                reqId, time, float(bidPrice), float(askPrice),
                int(bidSize), int(askSize), attrib)

        elif tickType == 4:
            midPoint, = fields

            self.wrapper.tickByTickMidPoint(reqId, time, float(midPoint))

    def openOrder(self, fields):
        o = Parser()
        c = Parser()
        st = Parser()
        if self.serverVersion < 145:
            fields.pop(0)
        (
            _,
            o.orderId_i,
            c.conId_i,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike_f,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            o.action,
            o.totalQuantity_f,
            o.orderType,
            o.lmtPrice_fu,
            o.auxPrice_fu,
            o.tif,
            o.ocaGroup,
            o.account,
            o.openClose,
            o.origin_i,
            o.orderRef,
            o.clientId_i,
            o.permId_i,
            o.outsideRth_b,
            o.hidden_b,
            o.discretionaryAmt_f,
            o.goodAfterTime,
            _,
            o.faGroup,
            o.faMethod,
            o.faPercentage,
            o.faProfile,
            o.modelCode,
            o.goodTillDate,
            o.rule80A,
            o.percentOffset_fu,
            o.settlingFirm,
            o.shortSaleSlot_i,
            o.designatedLocation,
            o.exemptCode_i,
            o.auctionStrategy_i,
            o.startingPrice_fu,
            o.stockRefPrice_fu,
            o.delta_fu,
            o.stockRangeLower_fu,
            o.stockRangeUpper_fu,
            o.displaySize_i,
            o.blockOrder_b,
            o.sweepToFill_b,
            o.allOrNone_b,
            o.minQty_iu,
            o.ocaType_i,
            o.eTradeOnly_b,
            o.firmQuoteOnly_b,
            o.nbboPriceCap_fu,
            o.parentId_i,
            o.triggerMethod_i,
            o.volatility_fu,
            o.volatilityType_i,
            o.deltaNeutralOrderType,
            o.deltaNeutralAuxPrice_fu,
            *fields) = fields
        if o.deltaNeutralOrderType:
            (
                o.deltaNeutralConId_i,
                o.deltaNeutralSettlingFirm,
                o.deltaNeutralClearingAccount,
                o.deltaNeutralClearingIntent,
                o.deltaNeutralOpenClose,
                o.deltaNeutralShortSale_b,
                o.deltaNeutralShortSaleSlot_i,
                o.deltaNeutralDesignatedLocation,
                *fields) = fields
        (
            o.continuousUpdate_b,
            o.referencePriceType_i,
            o.trailStopPrice_fu,
            o.trailingPercent_fu,
            o.basisPoints_fu,
            o.basisPointsType_iu,
            c.comboLegsDescrip,
            numLegs,
            *fields) = fields

        c.comboLegs = []
        for _ in range(int(numLegs)):
            leg = Parser()
            (
                leg.conId_i,
                leg.ratio_i,
                leg.action,
                leg.exchange,
                leg.openClose_i,
                leg.shortSaleSlot_i,
                leg.designatedLocation,
                leg.exemptCode_i,
                *fields) = fields
            c.comboLegs.append(ComboLeg(**leg.dict()))

        numOrderLegs = int(fields.pop(0))
        o.orderComboLegs = []
        for _ in range(numOrderLegs):
            o.orderComboLegs.append(
                OrderComboLeg(price=float(fields.pop(0) or UNSET_DOUBLE)))

        numParams = int(fields.pop(0))
        if numParams > 0:
            o.smartComboRoutingParams = []
            for _ in range(numParams):
                tag, value, *fields = fields
                o.smartComboRoutingParams.append(
                    TagValue(tag, value))

        (
            o.scaleInitLevelSize_iu,
            o.scaleSubsLevelSize_iu,
            increment,
            *fields) = fields

        o.scalePriceIncrement = float(increment or UNSET_DOUBLE)
        if 0 < o.scalePriceIncrement < UNSET_DOUBLE:
            (
                o.scalePriceAdjustValue_fu,
                o.scalePriceAdjustInterval_iu,
                o.scaleProfitOffset_fu,
                o.scaleAutoReset_b,
                o.scaleInitPosition_iu,
                o.scaleInitFillQty_iu,
                o.scaleRandomPercent_b,
                *fields) = fields

        o.hedgeType = fields.pop(0)
        if o.hedgeType:
            o.hedgeParam = fields.pop(0)

        (
            o.optOutSmartRouting_b,
            o.clearingAccount,
            o.clearingIntent,
            o.notHeld_b,
            dncPresent,
            *fields) = fields

        if int(dncPresent):
            conId, delta, price, *fields = fields
            c.deltaNeutralContract = DeltaNeutralContract(
                int(price or 0), float(delta or 0), float(price or 0))

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
            o.solicited_b,
            o.whatIf_b,
            st.status,
            *fields) = fields

        if self.serverVersion >= 142:
            (
                st.initMarginBefore,
                st.maintMarginBefore,
                st.equityWithLoanBefore,
                st.initMarginChange,
                st.maintMarginChange,
                st.equityWithLoanChange,
                *fields) = fields
        (
            st.initMarginAfter,
            st.maintMarginAfter,
            st.equityWithLoanAfter,
            st.commission_fu,
            st.minCommission_fu,
            st.maxCommission_fu,
            st.commissionCurrency,
            st.warningText,
            o.randomizeSize_b,
            o.randomizePrice_b,
            *fields) = fields

        if o.orderType == 'PEG BENCH':
            (
                o.referenceContractId_i,
                o.isPeggedChangeAmountDecrease_b,
                o.peggedChangeAmount_f,
                o.referenceChangeAmount_f,
                o.referenceExchangeId,
                *fields) = fields

        numConditions = int(fields.pop(0))
        if numConditions > 0:
            o.conditions = []
            for _ in range(numConditions):
                condType = int(fields.pop(0))
                condition = OrderCondition.create(condType)
                n = len(condition.defaults) - 1
                condition.decode(condType, *fields[:n])
                fields = fields[n:]
                o.conditions.append(condition)
            (
                o.conditionsIgnoreRth_b,
                o.conditionsCancelOrder_b,
                *fields) = fields

        (
            o.adjustedOrderType,
            o.triggerPrice_f,
            o.trailStopPrice_f,
            o.lmtPriceOffset_f,
            o.adjustedStopPrice_f,
            o.adjustedStopLimitPrice_f,
            o.adjustedTrailingAmount_f,
            o.adjustableTrailingUnit_i,
            name,
            value,
            displayName,
            cashQty_f,
            *fields) = fields

        o.softDollarTier = SoftDollarTier(name, value, displayName)

        if self.serverVersion >= 141:
            o.dontUseAutoPriceForHedge_b = fields.pop(0)
        if self.serverVersion >= 145:
            o.isOmsContainer_b = fields.pop(0)
        if self.serverVersion >= 148:
            o.discretionaryUpToLimitPrice_b = fields.pop(0)
        if self.serverVersion >= 151:
            o.usePriceMgmtAlgo_b = fields.pop(0)

        contract = Contract(**c.dict())
        order = Order(**o.dict())
        orderState = OrderState(**st.dict())
        self.wrapper.openOrder(order.orderId, contract, order, orderState)

    def completedOrder(self, fields):
        ...
