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
ib.connect('127.0.0.1', 7498, clientId=1)

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
last_tick_time=0
#%%
def insert_ticks(df_ticks, ticks):
    data = []
    i=0
    for tick in ticks:
        data.insert(i, {'Timestamp': tick.time, 'price': tick.price, 'size': tick.size})
        i=i+1

    df_ticks=pd.concat([pd.DataFrame(data), df_ticks], ignore_index=True)
    return df_ticks

#%%
def insert_ticks_to_db(ticks):
    i=0
    last_tick_time=0

    req_data=''
    for tick in ticks:
        tick_time=tick.time.timestamp()
        
        if tick_time!=last_tick_time:
            i=0
        else:
            i=i+1
        #this adds i as a column regardless of the tick timestamp being unique or not
        #this will require to completely purge and re-import historical data every time 
        #unless "seconds" in timestamp is used as a merker to not write to db anymore history
        req_data=req_data+table+','+'id='+ str(i) +' price='+str(tick.price)+',size='+str(tick.size)+',hist=1 '+str(tick_time)[:-2]+'000000000\n'
        last_tick_time=tick_time
        #print(req_data)
    req_data=req_data.encode('utf-8')
    #"http://localhost:8086/write?db=mydb" --data-binary 'mymeas,mytag=1 myfield=90 1463683075000000000'
    r = requests.post('http://localhost:8086/write?db=demo&u=root&p=root', data=req_data)
    print(req_data,' ',r)
    return r.status_code  
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
#%% download historical ticks from a current moment to a past date then exit
#dt_earliest_available=datetime.datetime.now()-datetime.timedelta(days=3)
#dt_earliest_available=dt_earliest_available.astimezone(tz=datetime.timezone.utc)
#%%

client = GetInfluxdbPandasClient()

dt=datetime.datetime.now()
dt=dt.astimezone(tz=datetime.timezone.utc)
dt
#%%
#result=client.query("delete from "+table)
#%%
while True:
    print ('Getting tick data for ', dt)
    ticks=ib.reqHistoricalTicks(contracts[0],None,dt,1000,"TRADES",False)

    if dt<=dt_earliest_available:
        break

    if len(ticks)<2:
        dt=dt-datetime.timedelta(days=1)
    else:
        #df_ticks=insert_ticks(df_ticks, ticks)
        print ('Writing tick data to db for ', dt)
        result=insert_ticks_to_db(ticks)
        dt=ticks[0].time
        
#%%
'''
#pd.DatetimeIndex(df_result.index).strftime('%f')
dt=pd.DatetimeIndex(df_result.index).second*1000000000
dt=dt+pd.DatetimeIndex(df_result.index).microsecond*1000
dt=dt+pd.DatetimeIndex(df_result.index).nanosecond
df_result.index= pd.to_datetime(dt, unit='s')
'''
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
ib.disconnect()