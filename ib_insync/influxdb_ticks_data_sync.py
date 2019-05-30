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
ib.connect('127.0.0.1', 7498, clientId=15)
table='USM190529'

#%%
data_ready=False
df_ticks = pd.DataFrame(columns=['Timestamp','price','size'])
contracts = [Future(conId='333866981')]
#contracts = [ContFuture('ZB')]
contracts[0].includeExpired=True

#contracts[0].lastTradeDateOrContractMonth='20190318'
ib.qualifyContracts(*contracts)
dt_earliest_available=ib.reqHeadTimeStamp(contracts[0],"TRADES",False,1)
dt_earliest_available=dt_earliest_available.astimezone(tz=datetime.timezone.utc)
dt_earliest_available

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
client = GetInfluxdbPandasClient()

#%% download historical ticks from a current moment to a past date then exit
def Get_last_hist_tick_time_in_db():
    #id>=1000 is only true when historical ticks are retrieved, also time precision is second only
    result=client.query("select * from "+table+" where hist=1 order by time desc limit 1")

    try:
        df_result=pd.DataFrame(result[table.replace('"','')])
        dt_latest_hist_in_db=df_result.index[0]#,tz=datetime.timezone.utc)
        dt_latest_hist_in_db=dt_latest_hist_in_db+datetime.timedelta(seconds=1)
        #dt_latest_hist_in_db=dt_latest_hist_in_db.astimezone(tz=datetime.timezone.utc)
        return dt_latest_hist_in_db
    except:
        return 0
#%%
#to stop at a certain tick in db
#result=client.query("select * from "+table +" order by time desc limit 1")
#df_result=pd.DataFrame(result['demo_tbl'])
#df_result.index[0]
#dt_earliest_available=datetime.datetime.fromtimestamp(int(str(df_result.index[0])),tz=datetime.timezone.utc)


#%%
def Delete_existing_live_ticks():
    #assumes the db has only one patch of live ticks, i.e. historical tick has to overwrite live ticks everyday before market opens, and after a system crash
    result=client.query("select * from "+table+" where hist=0 order by time asc limit 1")#epoch='ns')
    result
    
    try:
        df_result=pd.DataFrame(result[table.replace('"','')])
        dt_earliest_live_tick_in_db=df_result.index[0]#,tz=datetime.timezone.utc)
        
        dt_earliest_live_tick_in_db = pd.datetime.timestamp(dt_earliest_live_tick_in_db)
        dt_earliest_live_tick_in_db = datetime.datetime.fromtimestamp(dt_earliest_live_tick_in_db)
        result=client.query("delete from "+table+" where time>="+str(dt_earliest_live_tick_in_db.timestamp()))#epoch='ns')
        return result
    except:
        return 0
    #%% download historical ticks from a current moment to a past date then exit
def Get_earliest_live_tick_time_in_db():
    #assumes the db has only one patch of live ticks, i.e. historical tick has to overwrite live ticks everyday before market opens, and after a system crash
    result=client.query("select * from "+table+" where hist=0 order by time asc limit 1")#epoch='ns')
    result
    
    try:
        df_result=pd.DataFrame(result[table.replace('"','')])
        dt_earliest_live_tick_in_db=df_result.index[0]#,tz=datetime.timezone.utc)
        dt_earliest_live_tick_in_db=dt_earliest_live_tick_in_db-datetime.timedelta(microseconds=1)
        #dt_earliest_live_tick_in_db=dt_earliest_live_tick_in_db.astimezone(tz=datetime.timezone.utc)
        return dt_earliest_live_tick_in_db
        
    except:
        return 0#datetime.datetime.now().astimezone(tz=datetime.timezone.utc)
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
        req_data=req_data+table.replace('"','')+','+'id='+ str(i) +' price='+str(tick.price)+',size='+str(tick.size)+',hist=1 '+str(tick_time)[:-2]+'000000000\n'
        last_tick_time=tick_time
        #print(req_data)
    #"http://localhost:8086/write?db=mydb" --data-binary 'mymeas,mytag=1 myfield=90 1463683075000000000'
    if len(req_data)>0:
        req_data=str(req_data).encode('utf-8')
        #"http://localhost:8086/write?db=mydb" --data-binary 'mymeas,mytag=1 myfield=90 1463683075000000000'
        r = requests.post('http://localhost:8086/write?db=demo&u=root&p=root', data=req_data)
        print('inserted data ', req_data,' ',r)
        return r.status_code
    else:
        print('no more data to insert')
        return 'no points to insert'    

#%%
        
def insert_mid_ticks_to_db(ticks, first_live_tick_time_in_db,prev_req_data_live):
    i=0
    last_tick_time=0
    req_data_live=''

    for tick in ticks:
        #print(tick.time)
        tick_time=tick.time.timestamp()
        if tick_time<=first_live_tick_time_in_db.timestamp(): #last_hist_tick_time_in_db already has 1 second added, hence the >= condition
        
            if tick_time!=last_tick_time:
                i=0
            else:
                i=i+1            #this adds i as a column regardless of the tick timestamp being unique or not
            #this will require to completely purge and re-import historical data every time 
            #unless "seconds" in timestamp is used as a merker to not write to db anymore history
            req_data_live=req_data_live+table.replace('"','')+','+'id='+ str(i) +' price='+str(tick.price)+',size='+str(tick.size)+',hist=1 '+(str(tick_time))[:-2]+'000000000\n'
            last_tick_time=tick_time
            #print(len(req_data_live))
            
    if (len(req_data_live)>0) & (prev_req_data_live!=last_tick_time):
        req_data_live=str(req_data_live).encode('utf-8')
        #"http://localhost:8086/write?db=mydb" --data-binary 'mymeas,mytag=1 myfield=90 1463683075000000000'
        r = requests.post('http://localhost:8086/write?db=demo&u=root&p=root', data=req_data_live)
        print(req_data_live,' ',r)
        prev_req_data_live=last_tick_time
        return r.status_code, prev_req_data_live
    else:
        return 'no points to insert' ,prev_req_data_live
    #%%
result=Delete_existing_live_ticks()

zb_ticker=ib.reqTickByTickData(contracts[0],'Last')
#%% start storing live ticks
def onPendingTickers(tickers):
    df_ticks = pd.DataFrame(columns=['time','id','price','size', 'hist'])
    
    i=0
    for t in tickers:
        for tick in t.tickByTicks:
            new_entry = {'time': datetime.datetime.fromtimestamp (tick.time.timestamp()),
                         'id': i,'price': tick.price, 'size': float(tick.size), 'hist': float(0)}
    
            df_ticks.loc[len(df_ticks)]= new_entry
            
            #df_ticks.loc[len(df_ticks)]=[ tick.time,i,tick.price,tick.size]
            i=i+1
        
    print(df_ticks.tail())
    #dt=datetime.datetime.now()
    
    #if data_ready:
        #call function to calc bars & studies on new data
    
    if len(df_ticks)>=0:
        #df_ticks.set_index(['time','id'],inplace=True)
        df_ticks.set_index(['time'],inplace=True)
        #print(df_ticks)
        #print(df_ticks.index)
        
        result=client.write_points(df_ticks,table.replace('"',''),tag_columns=['id'])
        
        #result=True
        #if result:
            #df_ticks.truncate()
           # df_ticks.reset_index(drop=True,inplace=True)
        
ib.pendingTickersEvent += onPendingTickers

#%% store missing hist ticks till current moment
try:
    last_hist_tick_time_in_db = Get_last_hist_tick_time_in_db()
    last_hist_tick_time_in_db = pd.datetime.timestamp(last_hist_tick_time_in_db)
    last_hist_tick_time_in_db = datetime.datetime.fromtimestamp(last_hist_tick_time_in_db)
    last_hist_tick_time_in_db  = last_hist_tick_time_in_db.astimezone(tz=datetime.timezone.utc)
except:
    last_hist_tick_time_in_db = datetime.datetime.fromtimestamp(last_hist_tick_time_in_db,tz=datetime.timezone.utc)
    
dt_now=datetime.datetime.now()
#dt_now=datetime.datetime.fromtimestamp(1557150177)
dt_now=dt_now.astimezone(tz=datetime.timezone.utc)
#%%
while True:
    print ('First Loop: Getting tick data for ', dt_now)
    ticks=ib.reqHistoricalTicks(contracts[0],None,dt_now,1000,"TRADES",False)

    if dt_now<=last_hist_tick_time_in_db:
        break

    if len(ticks)<2:
        dt_now=dt_now-datetime.timedelta(days=1)
    else:
        #df_ticks=insert_ticks(df_ticks, ticks)
        print ('First Loop: Writing tick data to db for ', dt_now)
        result=insert_ticks_to_db(ticks)
        dt_now=ticks[0].time#earliest time in result set
        # since every historical tick has time and id as primary key, duplicate ticks will not be inserted more than once to the db
        #this code assumes that not more than 1000 ticks can be returned per 10 second, which is safe for ZB
 
        #once adding to db stops, get out of this while loop
        if str(result)!='204':
            break
#%% keep getting new historical data every 10 seconds until earliest live tick is hit
# since every historical tick has time and id as primary key, duplicate historical ticks will not be inserted more than once to the db
#this code assumes that not more than 1000 ticks can be returned per 10 second, which is safe for ZB
            
from time import sleep
sleep(60) #give some time for the live ticks to start

prev_req_data_live=0
    
dt_earliest_live_tick_in_db = Get_earliest_live_tick_time_in_db()
dt_earliest_live_tick_in_db = pd.datetime.timestamp(dt_earliest_live_tick_in_db)
dt_earliest_live_tick_in_db = datetime.datetime.fromtimestamp(dt_earliest_live_tick_in_db)
# get any additional missing hist ticks between the time last hist ticks were saved and live ticks started
while True:
        
    dt=datetime.datetime.now()
    dt=dt.astimezone(tz=datetime.timezone.utc)
    
    print ('Second Loop: Getting tick data for ', dt)
    ticks=ib.reqHistoricalTicks(contracts[0],None,dt,1000,"TRADES",False)

    if len(ticks)>2:
        #df_ticks=insert_ticks(df_ticks, ticks)
        print ('Second Loop: Writing tick data to db for ', dt)
        
        #switch the 2 lines of code below if trying to to reconcile with live ticks
        #result=insert_ticks_to_db(ticks)
        result,prev_req_data_live=insert_mid_ticks_to_db(ticks,dt_earliest_live_tick_in_db,prev_req_data_live)
        print(str(result))
        if str(result)!='204':
            break
        sleep(10)
#%% has to be done when market data is very slow to give time for initial calculations without missing new live ticks
#call function to calc bars & studies
#get last time for hist tick in dataframe, use that as condition below
result=client.query("select * from "+table+" order by time asc where time> "+ df_last_hist,epoch='ns')
df_result=pd.DataFrame(result[table])
#concatdf_result with existing df
data_ready=True

#%%
'''
#pd.DatetimeIndex(df_result.index).strftime('%f')
dt=pd.DatetimeIndex(df_result.index).second*1000000000
dt=dt+pd.DatetimeIndex(df_result.index).microsecond*1000
dt=dt+pd.DatetimeIndex(df_result.index).nanosecond
df_result.index= pd.to_datetime(dt, unit='s')
#%%
result=client.query("select * from "+table) #+" order by time desc limit 10 ",
                    #epoch='ns')
result
df_result=pd.DataFrame(result[table])
df_result

df_result.to_csv(r'c:\test\IB-USM19-hist-data'+str(datetime.datetime.now().timestamp())+'.csv')
#df_ticks.to_csv(r'c:\test\IB-USM19-hist-data'+str(dt.timestamp())+'.csv')
print(df_result)

'''
#%%
ib.pendingTickersEvent -= onPendingTickers
#%%
ib.cancelTickByTickData(contracts[0], 'AllLast')

#%%
ib.disconnect()

#%%
ib.disconnect()
