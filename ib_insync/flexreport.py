import time
import logging
from contextlib import suppress
from urllib.request import urlopen
import xml.etree.ElementTree as et

from ib_insync.objects import DynamicObject
from ib_insync import util

__all__ = ('FlexReport', 'FlexError')

_logger = logging.getLogger('ib_insync.flexreport')


class FlexError(Exception):
    pass


class FlexReport:
    """
    Download and parse IB account statements via the Flex Web Service.
    https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm

    To obtain a ``token`` in account management, go to
    Reports -> Settings -> Flex Web Service.
    Tip: choose a 1 year expiry.

    To obtain a ``queryId``: Create and save a query with
    Report -> Activity -> Flex Queries or
    Report -> Trade Confirmations -> Flex Queries.
    Find the query ID (not the query name).

    A large query can take a few minutes. In the weekends the query servers
    can be down.
    """

    def __init__(self, token=None, queryId=None, path=None):
        """
        Download a report by giving a valid ``token`` and ``queryId``,
        or load from file by giving a valid ``path``.
        """
        self.data = None
        self.root = None
        if token and queryId:
            self.download(token, queryId)
        elif path:
            self.load(path)

    def topics(self):
        """
        Get the set of topics that can be extracted from this report.
        """
        return set(node.tag for node in self.root.iter() if node.attrib)

    def extract(self, topic: str, parseNumbers=True) -> list:
        """
        Extract items of given topic and return as list of objects.

        The topic is a string like TradeConfirm, ChangeInDividendAccrual,
        Order, etc.
        """
        cls = type(topic, (DynamicObject,), {})
        results = [cls(**node.attrib) for node in self.root.iter(topic)]
        if parseNumbers:
            for obj in results:
                d = obj.__dict__
                for k, v in d.items():
                    with suppress(ValueError):
                        d[k] = float(v)
                        d[k] = int(v)
        return results

    def df(self, topic: str, parseNumbers=True):
        """
        Same as extract but return the result as a pandas DataFrame.
        """
        return util.df(self.extract(topic, parseNumbers))

    def download(self, token, queryId):
        """
        Download report for the given ``token`` and ``queryId``.
        """
        url = (
                'https://gdcdyn.interactivebrokers.com'
                f'/Universal/servlet/FlexStatementService.SendRequest?'
                f't={token}&q={queryId}&v=3')
        resp = urlopen(url)
        data = resp.read()

        root = et.fromstring(data)
        if root.find('Status').text == 'Success':
            code = root.find('ReferenceCode').text
            baseUrl = root.find('Url').text
            _logger.info('Statement is being prepared...')
        else:
            errorCode = root.find('ErrorCode').text
            errorMsg = root.find('ErrorMessage').text
            raise FlexError(f'{errorCode}: {errorMsg}')

        while True:
            time.sleep(1)
            url = f'{baseUrl}?q={code}&t={token}'
            resp = urlopen(url)
            self.data = resp.read()
            self.root = et.fromstring(self.data)
            if self.root[0].tag == 'code':
                msg = self.root[0].text
                if msg.startswith('Statement generation in progress'):
                    _logger.info('still working...')
                    continue
                else:
                    raise FlexError(msg)
            break
        _logger.info('Statement retrieved.')

    def load(self, path):
        """
        Load report from XML file.
        """
        with open(path, 'rb') as f:
            self.data = f.read()
            self.root = et.fromstring(self.data)

    def save(self, path):
        """
        Save report to XML file.
        """
        with open(path, 'wb') as f:
            f.write(self.data)


if __name__ == '__main__':
    util.logToConsole()
    report = FlexReport('945692423458902392892687', '272555')
    print(report.topics())
    trades = report.extract('Trade')
    print(trades)
