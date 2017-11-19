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
    
    
More to be added...