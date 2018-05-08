.. _recipes:


Code recipes
============

Collection of useful patterns, snippets and recipes.

Fetching consecutive historical data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Suppose we want to get the 1 min bar data of Tesla since the very beginning 
up until now. The best way is to start with now and keep requesting further
and further back in time until there is no more data returned.

.. code-block:: python

    import datetime
    from ib_insync import *
    
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    
    contract = Stock('TSLA', 'SMART', 'USD')
    
    dt = ''
    barsList = []
    while True:
        bars = ib.reqHistoricalData(
                contract,
                endDateTime=dt,
                durationStr='10 D',
                barSizeSetting='1 min',
                whatToShow='MIDPOINT',
                useRTH=True,
                formatDate=1)
        if not bars:
            break
        barsList.append(bars)
        dt = bars[0].date
        print(dt)
    
    allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(allBars)
    df.to_csv(contract.symbol + '.csv')
    

Integration with PyQt5
^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/qt-tickertable.png

Here is an recipe of a ticker table that shows how to integrate both
realtime streaming and synchronous API requests in a single-threaded
Qt application.
The API requests in this example are ``connect`` and 
``ib.qualifyContracts()``; The latter is used
to get the conId of a contract and use that as a unique key.

The Qt interface will not freeze when a request is ongoing and it is even
possible to have multiple outstanding requests at the same time.

This example depends on PyQt5 and quamash:
``pip3 install -U PyQt5 quamash``.

.. code-block:: python

    import sys
    import traceback
    import PyQt5.Qt as qt
    from ib_insync import *
    
    
    class TickerTable(qt.QTableWidget):
    
        headers = ['symbol', 'bidSize', 'bid', 'ask', 'askSize',
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
            item.setText(ticker.contract.symbol + (ticker.contract.currency
                    if ticker.contract.secType == 'CASH' else ''))
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
                for symbol in 'EURUSD USDJPY EURGBP USDCAD EURCHF AUDUSD NZDUSD'.split():
                    self.add(f"Forex('{symbol}')")
                self.add("Stock('TSLA', 'SMART', 'USD')")
    
    
    if __name__ == '__main__':
        sys.excepthook = traceback.print_exception
        util.useQt()
        util.allowCtrlC()
        window = Window('127.0.0.1', 7497, 1)
        window.resize(600, 400)
        window.show()
        IB.run()

    
More to be added...