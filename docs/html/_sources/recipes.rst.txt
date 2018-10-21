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


Integration with PyQt5 or PySide2
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/qt-tickertable.png

`This example <https://github.com/erdewit/ib_insync/blob/master/examples/qt_ticker_table.py>`_
of a ticker table shows how to integrate both
realtime streaming and synchronous API requests in a single-threaded
Qt application.
The API requests in this example are ``connect`` and
``ib.qualifyContracts()``; The latter is used
to get the conId of a contract and use that as a unique key.

The Qt interface will not freeze when a request is ongoing and it is even
possible to have multiple outstanding requests at the same time.

This example depends on PyQt5:

``pip3 install -U PyQt5``.

It's also possible to use PySide2 instead; To do so uncomment the PySide2
import and ``util.useQt`` lines in the example and comment out their PyQt5
counterparts.


More to be added...