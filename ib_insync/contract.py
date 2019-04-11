
from ib_insync.objects import Object

__all__ = (
    'Contract Stock Option Future ContFuture Forex Index CFD '
    'Commodity Bond FuturesOption MutualFund Warrant Bag').split()


class Contract(Object):
    """
    ``Contract(**kwargs)`` can create any contract using keyword
    arguments. To simplify working with contracts, there are also more
    specialized contracts that take optional positional arguments.
    Some examples::

        Contract(conId=270639)
        Stock('AMD', 'SMART', 'USD')
        Stock('INTC', 'SMART', 'USD', primaryExchange='NASDAQ')
        Forex('EURUSD')
        CFD('IBUS30')
        Future('ES', '20180921', 'GLOBEX')
        Option('SPY', '20170721', 240, 'C', 'SMART')
        Bond(secIdType='ISIN', secId='US03076KAA60')

    Args:
        conId (int): The unique IB contract identifier.
        symbol (str): The contract (or its underlying) symbol.
        secType (str): The security type:

            * 'STK' = Stock (or ETF)
            * 'OPT' = Option
            * 'FUT' = Future
            * 'IND' = Index
            * 'FOP' = Futures option
            * 'CASH' = Forex pair
            * 'CFD' = CFD
            * 'BAG' = Combo
            * 'WAR' = Warrant
            * 'BOND'= Bond
            * 'CMDTY'= Commodity
            * 'NEWS' = News
            * 'FUND'= Mutual fund
        lastTradeDateOrContractMonth (str): The contract's last trading
            day or contract month (for Options and Futures).
            Strings with format YYYYMM will be interpreted as the
            Contract Month whereas YYYYMMDD will be interpreted as
            Last Trading Day.
        strike (float): The option's strike price.
        right (str): Put or Call.
            Valid values are 'P', 'PUT', 'C', 'CALL', or '' for non-options.
        multiplier (str): he instrument's multiplier (i.e. options, futures).
        exchange (str): The destination exchange.
        currency (str): The underlying's currency.
        localSymbol (str): The contract's symbol within its primary exchange.
            For options, this will be the OCC symbol.
        primaryExchange (str): The contract's primary exchange.
            For smart routed contracts, used to define contract in case
            of ambiguity. Should be defined as native exchange of contract,
            e.g. ISLAND for MSFT. For exchanges which contain a period in name,
            will only be part of exchange name prior to period, i.e. ENEXT
            for ENEXT.BE.
        tradingClass (str): The trading class name for this contract.
            Available in TWS contract description window as well.
            For example, GBL Dec '13 future's trading class is "FGBL".
        includeExpired (bool): If set to true, contract details requests
            and historical data queries can be performed pertaining to
            expired futures contracts. Expired options or other instrument
            types are not available.
        secIdType (str): Security identifier type. Examples for Apple:

                * secIdType='ISIN', secId='US0378331005'
                * secIdType='CUSIP', secId='037833100'
        secId (str): Security identifier.
        comboLegsDescription (str): Description of the combo legs.
        comboLegs (List[ComboLeg]): The legs of a combined contract definition.
        deltaNeutralContract (DeltaNeutralContract): Delta and underlying
            price for Delta-Neutral combo orders.
    """
    defaults = dict(
        secType='',
        conId=0,
        symbol='',
        lastTradeDateOrContractMonth='',
        strike=0.0,
        right='',
        multiplier='',
        exchange='',
        primaryExchange='',
        currency='',
        localSymbol='',
        tradingClass='',
        includeExpired=False,
        secIdType='',
        secId='',
        comboLegsDescrip='',
        comboLegs=None,
        deltaNeutralContract=None
    )
    __slots__ = defaults.keys()

    @staticmethod
    def create(**kwargs):
        """
        Create and a return a specialized contract based on the given secType,
        or a general Contract if secType is not given.
        """
        secType = kwargs.get('secType', '')
        cls = {
            '': Contract,
            'STK': Stock,
            'OPT': Option,
            'FUT': Future,
            'CONTFUT': ContFuture,
            'CASH': Forex,
            'IND': Index,
            'CFD': CFD,
            'BOND': Bond,
            'CMDTY': Commodity,
            'FOP': FuturesOption,
            'FUND': MutualFund,
            'WAR': Warrant,
            'IOPT': Warrant,
            'BAG': Bag,
            'NEWS': Contract
        }.get(secType, Contract)
        if cls is not Contract:
            kwargs.pop('secType', '')
        return cls(**kwargs)

    def isHashable(self):
        """
        See if this contract can be hashed by conId.

        Note: Bag contracts always get conId=28812380 and ContFutures get the
        same conId as the front contract, so these contract types are
        not hashable.
        """
        return self.conId and self.conId != 28812380 and \
            self.secType not in ('BAG', 'CONTFUT')

    def __eq__(self, other):
        return self.isHashable() and isinstance(other, Contract) and \
                self.conId == other.conId \
                or Object.__eq__(self, other)

    def __hash__(self):
        if not self.isHashable():
            raise ValueError(f'Contract {self} can\'t be hashed')
        return self.conId

    def __repr__(self):
        attrs = self.nonDefaults()
        if self.__class__ is not Contract:
            attrs.pop('secType', '')
        clsName = self.__class__.__qualname__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__


class Stock(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', exchange: str = '', currency: str = '',
            **kwargs):
        """
        Stock contract.

        Args:
            symbol: Symbol name.
            exchange: Destination exchange.
            currency: Underlying currency.
        """
        Contract.__init__(
            self, secType='STK', symbol=symbol,
            exchange=exchange, currency=currency, **kwargs)


class Option(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', lastTradeDateOrContractMonth: str = '',
            strike: float = 0.0, right: str = '', exchange: str = '',
            multiplier: str = '', currency: str = '', **kwargs):
        """
        Option contract.

        Args:
            symbol: Symbol name.
            lastTradeDateOrContractMonth: The option's last trading day
                or contract month.

                * YYYYMM format: To specify last month
                * YYYYMMDD format: To specify last trading day
            strike: The option's strike price.
            right: Put or call option.
                Valid values are 'P', 'PUT', 'C' or 'CALL'.
            exchange: Destination exchange.
            multiplier: The contract multiplier.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'OPT', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                strike=strike, right=right, exchange=exchange,
                multiplier=multiplier, currency=currency, **kwargs)


class Future(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', lastTradeDateOrContractMonth: str = '',
            exchange: str = '', localSymbol: str = '', multiplier: str = '',
            currency: str = '', **kwargs):
        """
        Future contract.

        Args:
            symbol: Symbol name.
            lastTradeDateOrContractMonth: The option's last trading day
                or contract month.

                * YYYYMM format: To specify last month
                * YYYYMMDD format: To specify last trading day
            exchange: Destination exchange.
            localSymbol: The contract's symbol within its primary exchange.
            multiplier: The contract multiplier.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'FUT', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                exchange=exchange, localSymbol=localSymbol,
                multiplier=multiplier, currency=currency, **kwargs)


class ContFuture(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', exchange: str = '', localSymbol: str = '',
            multiplier: str = '', currency: str = '', **kwargs):
        """
        Continuous future contract.

        Args:
            symbol: Symbol name.
            exchange: Destination exchange.
            localSymbol: The contract's symbol within its primary exchange.
            multiplier: The contract multiplier.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'CONTFUT', symbol=symbol,
                exchange=exchange, localSymbol=localSymbol,
                multiplier=multiplier, currency=currency, **kwargs)


class Forex(Contract):
    __slots__ = ()

    def __init__(
            self, pair: str = '', exchange: str = 'IDEALPRO',
            symbol: str = '', currency: str = '', **kwargs):
        """
        Foreign exchange currency pair.

        Args:
            pair: Shortcut for specifying symbol and currency, like 'EURUSD'.
            exchange: Destination exchange.
            symbol: Base currency.
            currency: Quote currency.
        """
        if pair:
            assert len(pair) == 6
            symbol = symbol or pair[:3]
            currency = currency or pair[3:]
        Contract.__init__(
                self, 'CASH', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)

    def __repr__(self):
        attrs = self.nonDefaults()
        attrs.pop('secType')
        s = 'Forex('
        if 'symbol' in attrs and 'currency' in attrs:
            pair = attrs.pop('symbol')
            pair += attrs.pop('currency')
            s += "'" + pair + "'" + (", " if attrs else "")
        s += ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        s += ')'
        return s

    __str__ = __repr__

    def pair(self) -> str:
        '''
        Short name of pair.
        '''
        return self.symbol + self.currency


class Index(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', exchange: str = '', currency: str = '',
            **kwargs):
        """
        Index.

        Args:
            symbol: Symbol name.
            exchange: Destination exchange.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'IND', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class CFD(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', exchange: str = '', currency: str = '',
            **kwargs):
        """
        Contract For Difference.

        Args:
            symbol: Symbol name.
            exchange: Destination exchange.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'CFD', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class Commodity(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', exchange: str = '', currency: str = '',
            **kwargs):
        """
        Commodity.

        Args:
            symbol: Symbol name.
            exchange: Destination exchange.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'CMDTY', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class Bond(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        """
        Bond.
        """
        Contract.__init__(self, 'BOND', **kwargs)


class FuturesOption(Contract):
    __slots__ = ()

    def __init__(
            self, symbol: str = '', lastTradeDateOrContractMonth: str = '',
            strike: float = 0.0, right: str = '', exchange: str = '',
            multiplier: str = '', currency: str = '', **kwargs):
        """
        Option on a futures contract.

        Args:
            symbol: Symbol name.
            lastTradeDateOrContractMonth: The option's last trading day
                or contract month.

                * YYYYMM format: To specify last month
                * YYYYMMDD format: To specify last trading day
            strike: The option's strike price.
            right: Put or call option.
                Valid values are 'P', 'PUT', 'C' or 'CALL'.
            exchange: Destination exchange.
            multiplier: The contract multiplier.
            currency: Underlying currency.
        """
        Contract.__init__(
                self, 'FOP', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                strike=strike, right=right, exchange=exchange,
                multiplier=multiplier, currency=currency, **kwargs)


class MutualFund(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        """
        Mutual fund.
        """
        Contract.__init__(self, 'FUND', **kwargs)


class Warrant(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        """
        Warrant option.
        """
        Contract.__init__(self, 'WAR', **kwargs)


class Bag(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        """
        Bag contract.
        """
        Contract.__init__(self, 'BAG', **kwargs)
