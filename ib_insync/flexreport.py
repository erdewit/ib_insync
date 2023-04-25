"""Access to account statement webservice."""

import logging
import time
import xml.etree.ElementTree as et
from contextlib import suppress
from urllib.request import urlopen

from ib_insync import util
from ib_insync.objects import DynamicObject

_logger = logging.getLogger('ib_insync.flexreport')


class FlexError(Exception):
    pass


class FlexReport:
    """
    To obtain a token:

    * Login to web portal
    * Go to Settings
    * Click on "Configure Flex Web Service"
    * Generate token
    """

    data: bytes
    root: et.Element

    def __init__(self, token=None, queryId=None, path=None):
        """
        Download a report by giving a valid ``token`` and ``queryId``,
        or load from file by giving a valid ``path``.
        """
        if token and queryId:
            self.download(token, queryId)
        elif path:
            self.load(path)

    def topics(self):
        """Get the set of topics that can be extracted from this report."""
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
        """Same as extract but return the result as a pandas DataFrame."""
        return util.df(self.extract(topic, parseNumbers))

    def download(self, token, queryId):
        """Download report for the given ``token`` and ``queryId``."""
        url = (
            'https://gdcdyn.interactivebrokers.com'
            f'/Universal/servlet/FlexStatementService.SendRequest?'
            f't={token}&q={queryId}&v=3')
        resp = urlopen(url)
        data = resp.read()

        root = et.fromstring(data)
        elem = root.find('Status')
        if elem is not None and elem.text == 'Success':
            elem = root.find('ReferenceCode')
            assert elem is not None
            code = elem.text
            elem = root.find('Url')
            assert elem is not None
            baseUrl = elem.text
            _logger.info('Statement is being prepared...')
        else:
            elem = root.find('ErrorCode')
            errorCode = elem.text if elem is not None else ''
            elem = root.find('ErrorMessage')
            errorMsg = elem.text if elem is not None else ''
            raise FlexError(f'{errorCode}: {errorMsg}')

        while True:
            time.sleep(1)
            url = f'{baseUrl}?q={code}&t={token}'
            resp = urlopen(url)
            self.data = resp.read()
            self.root = et.fromstring(self.data)
            if self.root[0].tag == 'code':
                msg = self.root[0].text
                if msg and msg.startswith('Statement generation in progress'):
                    _logger.info('still working...')
                    continue
                else:
                    raise FlexError(msg)
            break
        _logger.info('Statement retrieved.')

    def load(self, path):
        """Load report from XML file."""
        with open(path, 'rb') as f:
            self.data = f.read()
            self.root = et.fromstring(self.data)

    def save(self, path):
        """Save report to XML file."""
        with open(path, 'wb') as f:
            f.write(self.data)


if __name__ == '__main__':
    util.logToConsole()
    report = FlexReport('945692423458902392892687', '272555')
    print(report.topics())
    trades = report.extract('Trade')
    print(trades)
