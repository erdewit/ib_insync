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
ticks
#%%
contracts = [ContFuture('ZB')]
ib.qualifyContracts(*contracts)
contracts[0].includeExpired=True
ib.reqHeadTimeStamp(contracts[0],"TRADES",False,1)

dt=datetime.datetime(2019, 5, 20, 1, 31,0,0,datetime.timezone.utc)

dt=datetime.datetime(2019, 5, 19, 23, 52,33,0,datetime.timezone.utc)

dt.utctimetuple()
#ticks=ib.reqHistoricalTicks(contracts[0], '',datetime.datetime.now(),1000,"TRADES",False)
ticks=ib.reqHistoricalTicks(contracts[0],None,dt,1000,"TRADES",False)
ticks
#%%
import pandas as pd
df_ticks = pd.DataFrame(columns=['Timestamp','price','size'])
#%%
def insert_ticks(df_ticks):
    data = []
    i=0
    for tick in ticks:
        #df_ticks.loc[i] = [tick.time,tick.price,tick.size]
        data.insert(i, {'Timestamp': tick.time, 'price': tick.price, 'size': tick.size})
        #df_ticks.loc[len(ticks)] = [tick.time,tick.price,tick.size]  # adding a row
        #df_ticks.index = df_ticks.index + 1  # shifting index
        #df_ticks.sort_index(inplace=True) 
        i=i+1

    df_ticks=pd.concat([pd.DataFrame(data), df_ticks], ignore_index=True)
    return df_ticks

dt=datetime.datetime.now()

while True:
    ticks=ib.reqHistoricalTicks(contracts[0],None,dt,1000,"TRADES",False)

    if len(ticks)<1:
        break
    
    df_ticks=insert_ticks(df_ticks)
    dt=datetime.datetime.fromisoformat(str(ticks[0].time))
  
df_ticks
df_ticks.to_csv(r'c:\test\IB-data.csv')
#%%
ib.disconnect()

'''
put the first date in the ticks result array in a variable and use it as the end time for the next iteration 
in the loop. get the next date/second and start storing in DB till end of array
creaye a tick id as datetime field + a counter, to differentiate between ticks in the same second

for the calculations; drop all leading rows in bars dataframe until the last row where 
position was flat and number of remaining rows > largest number of rows required to calc studies, 35 for e.g.
- estimate how many ticks are needed to form a new bar, keep a counter, once it's formed, 
add a row to the dataframe and recalculate
