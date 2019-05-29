# -*- coding: utf-8 -*-
"""
Created on Mon May 27 11:05:27 2019

@author: basse
"""

#%% Change working directory from the workspace root to the ipynb file location. Turn this addition off with the DataScience.changeDirOnImportExport setting
import requests
from influxdb import DataFrameClient

import datetime
import pandas as pd

import os

try:
	os.chdir(os.path.join(os.getcwd(), '..\..\ib_insync'))
	print(os.getcwd())
except:
	pass

#%%
from ib_insync import *
util.startLoop()
ib = IB()
#%%
ib.connect('127.0.0.1', 7498, clientId=2)

#%%
df_ticks = pd.DataFrame(columns=['Timestamp','price','size'])
contracts = [Future(conId='333866981')]
contracts[0].includeExpired=True
#contracts[0].lastTradeDateOrContractMonth='20190318'
ib.qualifyContracts(*contracts)
dt_earliest_available=ib.reqHeadTimeStamp(contracts[0],"TRADES",False,1)
dt_earliest_available=dt_earliest_available.astimezone(tz=datetime.timezone.utc)
dt_earliest_available

table='USM19-5-28'
     
#%%
def GetInfluxdbPandasClient():
    """Instantiate the connection to the InfluxDB client."""
    user = 'root'
    password = 'root'
    dbname = 'demo'
    protocol = 'json'
    host='localhost'
    port=8086
    client = DataFrameClient(host, port, user, password, dbname)
    return client
#%%
'''
#pd.DatetimeIndex(df_result.index).strftime('%f')
dt=pd.DatetimeIndex(df_result.index).second*1000000000
dt=dt+pd.DatetimeIndex(df_result.index).microsecond*1000
dt=dt+pd.DatetimeIndex(df_result.index).nanosecond
df_result.index= pd.to_datetime(dt, unit='s')
'''
#%%
#df_ticks.index=pd.DatetimeIndex(df_ticks['time'])

client = GetInfluxdbPandasClient()

zb_ticker=ib.reqTickByTickData(contracts[0],'Last')
#%%
def onPendingTickers(tickers):
    df_ticks = pd.DataFrame(columns=['time','id','price','size', 'hist'])

    i=0
    for t in tickers:
        for tick in t.tickByTicks:
            new_entry = {'time': datetime.datetime.fromtimestamp (tick.time.timestamp()),
                         'id': i,'price': tick.price, 'size': float(tick.size), 'hist': '0'}

            df_ticks.loc[len(df_ticks)]= new_entry
            
            #df_ticks.loc[len(df_ticks)]=[ tick.time,i,tick.price,tick.size]
            i=i+1
        
    print(df_ticks.tail())
    #dt=datetime.datetime.now()

    if len(df_ticks)>=0:
        #df_ticks.set_index(['time','id'],inplace=True)
        df_ticks.set_index(['time'],inplace=True)
        #print(df_ticks)
        #print(df_ticks.index)
        result=client.write_points(df_ticks,table,tag_columns=['id'])
        #result=True
        #if result:
            #df_ticks.truncate()
           # df_ticks.reset_index(drop=True,inplace=True)
            
ib.pendingTickersEvent += onPendingTickers


#%%
ib.pendingTickersEvent -= onPendingTickers
#%%
ib.cancelTickByTickData(contracts[0], 'AllLast')

#%%
ib.disconnect()

#%%
result=client.query("select * from "+table) #+" order by time desc limit 10 ",
                    #epoch='ns')
result
df_result=pd.DataFrame(result[table])
df_result

df_result.to_csv(r'c:\test\IB-USM19-hist-data'+str(datetime.datetime.now().timestamp())+'.csv')
#df_ticks.to_csv(r'c:\test\IB-USM19-hist-data'+str(dt.timestamp())+'.csv')
print(df_result)
#%%
