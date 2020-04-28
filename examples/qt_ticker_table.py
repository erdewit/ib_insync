import asyncio

import PyQt5.QtWidgets as qt
# import PySide2.QtWidgets as qt

from ib_insync import IB, util
from ib_insync.contract import *  # noqa


class TickerTable(qt.QTableWidget):

    headers = [
        'symbol', 'bidSize', 'bid', 'ask', 'askSize',
        'last', 'lastSize', 'close']

    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.conId2Row = {}
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setAlternatingRowColors(True)

    def __contains__(self, contract):
        assert contract.conId
        return contract.conId in self.conId2Row

    def addTicker(self, ticker):
        row = self.rowCount()
        self.insertRow(row)
        self.conId2Row[ticker.contract.conId] = row
        for col in range(len(self.headers)):
            item = qt.QTableWidgetItem('-')
            self.setItem(row, col, item)
        item = self.item(row, 0)
        item.setText(ticker.contract.symbol + (
            ticker.contract.currency if ticker.contract.secType == 'CASH'
            else ''))
        self.resizeColumnsToContents()

    def clearTickers(self):
        self.setRowCount(0)
        self.conId2Row.clear()

    def onPendingTickers(self, tickers):
        for ticker in tickers:
            row = self.conId2Row[ticker.contract.conId]
            for col, header in enumerate(self.headers):
                if col == 0:
                    continue
                item = self.item(row, col)
                val = getattr(ticker, header)
                item.setText(str(val))


class Window(qt.QWidget):

    def __init__(self, host, port, clientId):
        qt.QWidget.__init__(self)
        self.edit = qt.QLineEdit('', self)
        self.edit.editingFinished.connect(self.add)
        self.table = TickerTable()
        self.connectButton = qt.QPushButton('Connect')
        self.connectButton.clicked.connect(self.onConnectButtonClicked)
        layout = qt.QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.table)
        layout.addWidget(self.connectButton)

        self.connectInfo = (host, port, clientId)
        self.ib = IB()
        self.ib.pendingTickersEvent += self.table.onPendingTickers

    def add(self, text=''):
        text = text or self.edit.text()
        if text:
            contract = eval(text)
            if (contract and self.ib.qualifyContracts(contract)
                    and contract not in self.table):
                ticker = self.ib.reqMktData(contract, '', False, False, None)
                self.table.addTicker(ticker)
            self.edit.setText(text)

    def onConnectButtonClicked(self, _):
        if self.ib.isConnected():
            self.ib.disconnect()
            self.table.clearTickers()
            self.connectButton.setText('Connect')
        else:
            self.ib.connect(*self.connectInfo)
            self.connectButton.setText('Disonnect')
            for symbol in (
                    'EURUSD', 'USDJPY', 'EURGBP', 'USDCAD',
                    'EURCHF', 'AUDUSD', 'NZDUSD'):
                self.add(f"Forex('{symbol}')")
            self.add("Stock('TSLA', 'SMART', 'USD')")

    def closeEvent(self, ev):
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    util.patchAsyncio()
    util.useQt()
    # util.useQt('PySide2')
    window = Window('127.0.0.1', 7497, 1)
    window.resize(600, 400)
    window.show()
    IB.run()
