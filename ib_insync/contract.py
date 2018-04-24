import  ibapi.contract

from ib_insync.objects import Object

__all__ = (
    'Contract Stock Option Future ContFuture Forex Index CFD '
    'Commodity Bond FuturesOption MutualFund Warrant').split()


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
    """
    defaults = {'secType': '', **ibapi.contract.Contract().__dict__}
    __slots__ = list(defaults.keys()) + \
            ['comboLegsCount', 'underCompPresent', 'deltaNeutralContractPresent',
                'secIdListCount']  # bug in decoder.py

    @staticmethod
    def create(**kwargs):
        """
        Create and a return a specialized contract based on the given secType,
        or a general Contract if secType is not given.
        """
        secType = kwargs.pop('secType', '')
        cls = {
            '': Contract,
            'STK': Stock,
            'OPT': Option,
            'FUT': Future,
            'CASH': Forex,
            'IND': Index,
            'CFD': CFD,
            'BOND': Bond,
            'CMDTY': Commodity,
            'FOP': FuturesOption,
            'FUND': MutualFund,
            'IOPT': Warrant
        }[secType]
        return cls(**kwargs)

    def __eq__(self, other):
        return (self.conId and isinstance(other, Contract) and
                (self.conId == other.conId) or
                Object.__eq__(self, other))

    def __hash__(self):
        return self.conId

    def __repr__(self):
        attrs = self.nonDefaults()
        if self.__class__ is not Contract:
            attrs.pop('secType', '')
        clsName = self.__class__.__name__
        kwargs = ', '.join(f'{k}={v!r}' for k, v in attrs.items())
        return f'{clsName}({kwargs})'

    __str__ = __repr__


class Stock(Contract):
    __slots__ = ()

    def __init__(self, symbol='', exchange='', currency='', **kwargs):
        Contract.__init__(self, secType='STK', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class Option(Contract):
    __slots__ = ()

    def __init__(self, symbol='', lastTradeDateOrContractMonth='',
            strike='', right='', exchange='', multiplier='',
            currency='', **kwargs):
        Contract.__init__(self, 'OPT', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                strike=strike, right=right, exchange=exchange,
                multiplier=multiplier, currency=currency, **kwargs)


class Future(Contract):
    __slots__ = ()

    def __init__(self, symbol='', lastTradeDateOrContractMonth='',
            exchange='', localSymbol='', multiplier='',
            currency='', **kwargs):
        Contract.__init__(self, 'FUT', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                exchange=exchange, localSymbol=localSymbol,
                multiplier=multiplier, currency=currency, **kwargs)


class ContFuture(Contract):
    __slots__ = ()

    def __init__(self, symbol='', exchange='', localSymbol='', multiplier='',
            currency='', **kwargs):
        Contract.__init__(self, 'CONTFUT', symbol=symbol,
                exchange=exchange, localSymbol=localSymbol,
                multiplier=multiplier, currency=currency, **kwargs)


class Forex(Contract):
    __slots__ = ()

    def __init__(self, pair='', exchange='IDEALPRO',
            symbol='', currency='', **kwargs):
        if pair:
            assert len(pair) == 6
            symbol = symbol or pair[:3]
            currency = currency or pair[3:]
        Contract.__init__(self, 'CASH', symbol=symbol,
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

    def pair(self):
        return self.symbol + self.currency


class Index(Contract):
    __slots__ = ()

    def __init__(self, symbol='', exchange='', currency='', **kwargs):
        Contract.__init__(self, 'IND', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class CFD(Contract):
    __slots__ = ()

    def __init__(self, symbol='', exchange='', currency='', **kwargs):
        Contract.__init__(self, 'CFD', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class Commodity(Contract):
    __slots__ = ()

    def __init__(self, symbol='', exchange='', currency='', **kwargs):
        Contract.__init__(self, 'CMDTY', symbol=symbol,
                exchange=exchange, currency=currency, **kwargs)


class Bond(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        Contract.__init__(self, 'BOND', **kwargs)


class FuturesOption(Contract):
    __slots__ = ()

    def __init__(self, symbol='', lastTradeDateOrContractMonth='',
            strike='', right='', exchange='', multiplier='',
            currency='', **kwargs):
        Contract.__init__(self, 'FOP', symbol=symbol,
                lastTradeDateOrContractMonth=lastTradeDateOrContractMonth,
                strike=strike, right=right, exchange=exchange,
                multiplier=multiplier, currency=currency, **kwargs)


class MutualFund(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        Contract.__init__(self, 'FUND', **kwargs)


class Warrant(Contract):
    __slots__ = ()

    def __init__(self, **kwargs):
        Contract.__init__(self, 'IOPT', **kwargs)
