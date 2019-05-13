#%% Change working directory from the workspace root to the ipynb file location. Turn this addition off with the DataScience.changeDirOnImportExport setting
import os
try:
	os.chdir(os.path.join(os.getcwd(), '..\..\ib_insync'))
	print(os.getcwd())
except:
	pass
#%% [markdown]
# # Tick data
# 
# For optimum results this notebook should be run during the Forex trading session.

#%%
from ib_insync import *
util.startLoop()

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=15)

#%% [markdown]
# ### Streaming tick data
# 
# Create some Forex contracts:

#%%
contracts = [Forex(pair) for pair in ('EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'USDCAD', 'AUDUSD')]
ib.qualifyContracts(*contracts)

eurusd = contracts[0]

#%% [markdown]
# Request streaming ticks for them:

#%%
for contract in contracts:
    ib.reqMktData(contract, '', False, False)

#%% [markdown]
# Wait a few seconds for the tickers to get filled.

#%%
ticker = ib.ticker(eurusd)
ib.sleep(2)

ticker

#%% [markdown]
# The price of Forex ticks is always nan. To get a midpoint price use ``midpoint()`` or ``marketPrice()``.
# 
# The tickers are kept live updated, try this a few times to see if the price changes:

#%%
ticker.marketPrice()

#%% [markdown]
# The following cell will start a 30 second loop that prints a live updated ticker table.
# It is updated on every ticker change.

#%%
from IPython.display import display, clear_output
import pandas as pd

df = pd.DataFrame(
    index=[c.pair() for c in contracts],
    columns=['bidSize', 'bid', 'ask', 'askSize', 'high', 'low', 'close'])

def onPendingTickers(tickers):
    for t in tickers:
        df.loc[t.contract.pair()] = (
            t.bidSize, t.bid, t.ask, t.askSize, t.high, t.low, t.close)
        clear_output(wait=True)
    display(df)        

ib.pendingTickersEvent += onPendingTickers
ib.sleep(30)
ib.pendingTickersEvent -= onPendingTickers

#%% [markdown]
# New tick data is available in the 'ticks' attribute of the pending tickers.
# The tick data will be cleared before the next update.
#%% [markdown]
# To stop the live tick subscriptions:

#%%
for contract in contracts:
    ib.cancelMktData(contract)

#%% [markdown]
# ### Tick by Tick data ###
# 
# The ticks in the previous section are time-sampled by IB in order to cut on bandwidth. So with ``reqMktdData`` not every tick from the exchanges is sent. 
# The promise of ``reqTickByTickData`` is to send every tick, just how it appears in the TWS Time & Sales window. This functionality is severly nerfed by a total of
#  just three simultaneous subscriptions, where bid-ask ticks and sale ticks also use up a subscription each.
# 
# The tick-by-tick updates are available from ``ticker.tickByTicks`` and are signalled by ``ib.pendingTickersEvent`` or ``ticker.updateEvent``.

#%%
ticker = ib.reqTickByTickData(eurusd, 'BidAsk')
ib.sleep(2)
print(ticker)

ib.cancelTickByTickData(ticker.contract, 'BidAsk')

#%% [markdown]
# ### Historical tick data
# 
# Historical tick data can be fetched with a maximum of 1000 ticks at a time. Either the start time or the end time must be given, and one of them must remain empty:

#%%
import datetime

start = ''
end = datetime.datetime.now()
ticks = ib.reqHistoricalTicks(eurusd, start, end, 1000, 'BID_ASK', useRth=False)

contracts = [ContFuture('ZB')]
ib.qualifyContracts(*contracts)
contracts[0].includeExpired=True
ib.reqHeadTimeStamp(contracts[0],"TRADES",False,1)
dt=datetime.datetime(2016, 11, 13, 23, 0)
ib.reqHistoricalTicks(contracts[0], dt,'',1000,"TRADES",False)




ticks[-1]


#%%
ib.disconnect()


