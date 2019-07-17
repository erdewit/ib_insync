# In[37]:
from ib_insync import *
from influxdb import DataFrameClient
import requests
import datetime
import calendar
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.datasets import make_regression
from IPython.display import display, HTML
import pandas as pd
import pandas_datareader.wb as wb
import statsmodels.api as sm
from operator import mul
from functools import reduce
from bokeh.io import output_notebook
from plotly.tools import FigureFactory as FF
import plotly.tools
import plotly.graph_objs as go
import plotly.plotly as py
import hvplot.pandas
import holoviews as hv
from bokeh.plotting import figure, output_file, show
from bokeh.models import CustomJS, Slider
from bokeh.layouts import row, column, widgetbox
from bokeh.models.widgets import Select
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.io import curdoc
from pykalman import KalmanFilter
from scipy import interp
from matplotlib.dates import date2num
from matplotlib.dates import num2date
import numpy as np
import pandas as pds
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import warnings
warnings.filterwarnings('ignore')


hv.extension('bokeh')

output_notebook()
#from data_wrangling import get_df_from_table, add_bar_counter
#from db_connection import DBConnection
# %%
# Import Libraries


np.random.seed(42)

#from plotly.offline import plot
#import cufflinks as cf


pd.core.common.is_list_like = pd.api.types.is_list_like
# In[6]:

# function to create different sampling base data


def create_bar(dataframe, column_, units):
    _bars_ = dataframe  # .copy()
    # print(_bars_)
    if column_ == 'time_stamp':
        _bars_ = _bars_.resample(str(units) + 'T',
                                 label='left').agg({"Price": 'ohlc',
                                                    "volume": 'sum',
                                                    'transaction': 'sum'})
        # print(_bars_)
        _bars_.columns = _bars_.columns.droplevel()
        # print(_bars_)
        _bars_['vwap'] = _bars_['transaction'] / _bars_['volume']
        _bars_ = _bars_.set_index('time_stamp')
        # print(_bars_)
    else:
        if column_ == 'id':
            _bars_[column_] = 1
        print(_bars_)
        # _bars_
        _bars_['transaction'] = _bars_['Open'] * _bars_['Volume']

        _bars_['filter'] = _bars_[column_].cumsum()
        # print(_bars_)
        _bars_['group'] = 0
        # print(_bars_)
        _bars_['filter'] = _bars_['filter'] / units
        # print(_bars_)
        _bars_['filter'] = np.nan_to_num(_bars_['filter'])

        _bars_['filter'] = _bars_['filter'].astype(int)
        # print(_bars_)
        _bars_['group'] = _bars_['filter']
        # print(_bars_)
        # _bars_ =
        # _bars_.groupby('group').agg({"time_stamp":"last","Price":'ohlc',"volume":'sum','transaction':'sum'})
        # # original version for ML class project
        _bars_ = _bars_.groupby('group').agg(
            {"Date": "last", "Open": 'ohlc', "Volume": 'sum', 'transaction': 'sum'})
        # print(_bars_)

        _bars_.columns = _bars_.columns.droplevel()
        # print(_bars_)
        _bars_['vwap'] = _bars_['transaction'] / _bars_['Volume']
        # print(_bars_)

        # print(_bars_)

    return _bars_


# In[8]:

def split_time(x):
    x = x.astype('str')
    x = x.str.pad(4, side='left', fillchar='0')
    # print(x.str)
    # if len(x.all())==4:
    x = x.str[:2] + ':' + x.str[2:]

    return x

# In[15]:


def LinRegRollingWindow(df, window=0):

    df['a'] = None  # constant
    df['b1'] = None  # beta1
    df['RSI_LinReg'] = None  # beta2
    for i in range(window, len(df)):
        temp = df.iloc[i - window:i, :]
        print(np.asarray(temp.loc[:, 'RSI']))
        X = range(1, window + 1)
        X = sm.add_constant(X)
        print("X ", X)
        RollOLS = sm.OLS(np.asarray(temp.loc[:, 'RSI']), X).fit()
        print("rollOLS ", RollOLS.params)
        df.iloc[i, df.columns.get_loc('a')] = RollOLS.params[0]
        df.iloc[i, df.columns.get_loc('b1')] = RollOLS.params[1]
        df.iloc[i, df.columns.get_loc('RSI_LinReg')] = RollOLS.predict(
            sm.add_constant(i))

# The following line gives you predicted values in a row, given the PRIOR row's estimated parameters
# df['predicted']=df['a'].shift(1)+df['b1'].shift(1)*df['RSI']

# Exponential Moving Average


def EMA(df, n, name, column='close'):

    EMA = pd.Series(df[column].ewm(span=n).mean(), name='ema_' + name)
    df = df.join(EMA)
    return df

# Momentum


def MOM(df, n):
    M = pd.Series(df['close'].diff(n), name='momentum_' + str(n))
    df = df.join(M)
    return df

# Relative Strength Index


def RSI(df, n):
    i = 0
    UpI = [0]
    DoI = [0]
    while i < df['close'].count() - 1:
        UpMove = df['high'].iat[i + 1] - df['high'].iat[i]
        DoMove = df['low'].iat[i] - df['low'].iat[i + 1]
        if UpMove > DoMove and UpMove > 0:
            UpD = UpMove
        else:
            UpD = 0
        UpI.append(UpD)
        if DoMove > UpMove and DoMove > 0:
            DoD = DoMove
        else:
            DoD = 0
        DoI.append(DoD)
        i = i + 1
    UpI = pd.Series(UpI)
    DoI = pd.Series(DoI)

    PosDI = pd.Series(UpI.ewm(span=n, min_periods=n - 1).mean())
    NegDI = pd.Series(DoI.ewm(span=n, min_periods=n - 1).mean())
    RSI = pd.Series(PosDI / (PosDI + NegDI), name='rsi_' + str(n)) * 100
    df = df.assign(RSI=RSI.values)

    return df

# MACD, MACD Signal and MACD difference


def MACD(df, n_fast, n_slow):
    EMAfast = pd.Series(
        df['close'].ewm(
            span=n_fast,
            min_periods=n_slow -
            1).mean())
    EMAslow = pd.Series(
        df['close'].ewm(
            span=n_slow,
            min_periods=n_slow -
            1).mean())
    MACD = pd.Series(
        EMAfast -
        EMAslow,
        name='MACD_' +
        str(n_fast) +
        '_' +
        str(n_slow))
    MACDsign = pd.Series(
        MACD.ewm(
            span=9,
            min_periods=8).mean(),
        name='MACDsign_' +
        str(n_fast) +
        '_' +
        str(n_slow))
    MACDdiff = pd.Series(
        MACD -
        MACDsign,
        name='MACDdiff_' +
        str(n_fast) +
        '_' +
        str(n_slow))
    df = df.join(MACD)
    df = df.join(MACDsign)
    df = df.join(MACDdiff)
    return df

# Commodity Channel Index


def CCI(df, n):

    PP = (df['high'] + df['low'] + df['close']) / 3

    r = PP.rolling(window=n)
    CCI = pd.Series((PP - r.mean()) / r.std(), name='CCI_' + str(n))
    df = df.join(CCI)
    return df

# In[12]:


def CalculateBarMaxProfit(df, returnsCol='dollar_returns', window=1):
    df = df.dropna()
    df.head()
    prev_return = df.iloc[0, df.columns.get_loc(returnsCol)]
    cum_sum_return = prev_return
    df['Target'] = None  # constant
    df['a'] = None
    df['BarStrength'] = None
    bars_strength = 1
    for i in range(window, len(df) - 1):

        curr_return = df.iloc[i, df.columns.get_loc(returnsCol)]
        if((prev_return < 0 and curr_return < 0) or ((prev_return > 0 and curr_return > 0))):
            bars_strength = bars_strength + 1

            if(bars_strength == 2):  # reset cum sum the first time
                cum_sum_return = prev_return + curr_return
            else:
                cum_sum_return = cum_sum_return + curr_return

            df.iloc[i - 1,
                    df.columns.get_loc('a')] = cum_sum_return - curr_return
            df.iloc[i, df.columns.get_loc('a')] = cum_sum_return
            df.iloc[i - bars_strength + 1,
                    df.columns.get_loc('Target')] = cum_sum_return

            for j in range(0, bars_strength - 1):
                if(j == 0):  # reset cum sum the first time
                    cum_sum_return_backwards = 0
                cum_sum_return_backwards = cum_sum_return_backwards + \
                    df.iloc[i - j, df.columns.get_loc(returnsCol)]
                df.iloc[i - j,
                        df.columns.get_loc('Target')] = cum_sum_return_backwards

        else:

            bars_strength = 1
            cum_sum_return = 0
            df.iloc[i - 1, df.columns.get_loc('a')] = prev_return
            df.iloc[i - bars_strength,
                    df.columns.get_loc('Target')] = prev_return

        df.iloc[i, df.columns.get_loc('BarStrength')] = bars_strength

        prev_return = curr_return

    return df


def CalculateBarStrength(df, returnsCol='dollar_returns', window=1):
    df = df.dropna()
    df['b'] = None
    df['BarStrength'] = None
    prev_return = df.iloc[0, df.columns.get_loc(returnsCol)]
    bars_strength = 1
    for i in range(window, len(df) - 1):

        curr_return = df.iloc[i, df.columns.get_loc(returnsCol)]

        if((prev_return < 0 and curr_return < 0) or ((prev_return > 0 and curr_return > 0))):
            bars_strength = bars_strength + 1
            df.iloc[i - bars_strength + 1,
                    df.columns.get_loc('BarStrength')] = bars_strength

            for j in range(0, bars_strength - 1):
                # if(j==0): #reset cum sum the first time
                    # bars_strength=1

                df.iloc[i - j, df.columns.get_loc('BarStrength')] = j + 1

        else:
            bars_strength = 1
            df.iloc[i, df.columns.get_loc('BarStrength')] = bars_strength

        df.iloc[i, df.columns.get_loc('b')] = bars_strength

        prev_return = curr_return

    return df

# function to replace nan or null with median


def impute_nan_with_median(table):
    for col in table.columns:
        table[col] = table[col].fillna(0)
    return table


def CalcRollingVAR(df, rolling_window=5, returnsCol='dollar_returns'):
    df = df.assign(periodVAR=df[returnsCol].rolling(5, center=True).var())
    return df


def CalcRollingCORR(df, rolling_window=5, returnsCol='dollar_returns'):
    df = df.assign(periodCORR=df[returnsCol].rolling(5, center=True).corr())
    return df


def CalcRollingCOV(df, rolling_window=5, returnsCol='dollar_returns'):
    df = df.assign(periodCOV=df[returnsCol].rolling(5, center=True).cov())
    return df


def CalcRollingKURT(df, rolling_window=5, returnsCol='dollar_returns'):
    df = df.assign(periodKURT=df[returnsCol].rolling(5, center=True).kurt())
    return df


def CalcRollingSKEW(df, rolling_window=5, returnsCol='dollar_returns'):
    df = df.assign(periodSKEW=df[returnsCol].rolling(5, center=True).skew())
    return df


def CalcEWMAC(df, FastEMA='ema_fast', SlowEMA='ema_slow'):
    df['EWMAC'] = df[FastEMA] - df[SlowEMA]
    return df


def LabelLongBars(df, returnsCol='dollar_returns'):
    df['Target'] = np.where(df[returnsCol] > 0, 1, 0)
    return df


def LabelShortBars(df, returnsCol='dollar_returns'):
    df['Target'] = np.where(df[returnsCol] > 0, -1, 0)
    return df


def CalcKalmanFilter(df):
    kf = KalmanFilter(transition_matrices=[1],
                      observation_matrices=[1],
                      initial_state_mean=0,
                      initial_state_covariance=1,
                      observation_covariance=1,
                      transition_covariance=.01)

    # Use the observed values of the price to get a rolling mean
    state_means, _ = kf.filter(df['close'].values)
    state_means_returns_log, _ = kf.filter(df['dollar_returns_log'] * 1000)
    state_means = pd.Series(state_means.flatten(), index=df.index)
    state_means_returns_log = pd.Series(
        state_means_returns_log.flatten(), index=df.index)
    df['state_means'] = state_means
    df['state_means_returns_log'] = state_means_returns_log
    return df


def CalculateLabels(
        df,
        returnsCol='dollar_returns',
        voltCol='periodVolDiff',
        window=1,
        short_entries=True,
        long_entries=True):
    #dollar_bars2=CalculateLabels(dollar_bars2, long_entries=False)
    df = df.dropna()
    df.head()
    df['prev_return'] = df[[returnsCol]].shift(1)
    df['prev_volt'] = df[[voltCol]].shift(1)
    # prev_return
    df['PL'] = 0
    df['Position'] = np.nan  # constant
    df['DirectionChange'] = 0
    df['VoltChange'] = 0

    df['curr_position'] = 0

    df = df.reset_index(drop=True)
    df.loc[(((df['prev_return'] < 0) & (df[returnsCol] > 0)) | (
        (df['prev_return'] > 0) & (df[returnsCol] < 0))), 'DirectionChange'] = 1
    df.loc[(((df['prev_volt'] < -0.00001) & (df['periodVolDiff'] > 0.00001)) |
            ((df['prev_volt'] > 0.00001) & (df['periodVolDiff'] < -0.00001))), 'VoltChange'] = 1

    return df


def CreateDollarBars(_bars_, units):

    ##df2.loc[: , "2005"]
    _bars_['transaction'] = _bars_['Price'] * _bars_['Vol']
    column_ = 'transaction'
    # units=75000
    _bars_[column_] = pd.to_numeric(_bars_[column_])
    # _bars_[column_].dropna()
    _bars_ = _bars_[~_bars_.isin([np.nan, np.inf, -np.inf]).any(1)]
    _bars_['filter'] = _bars_[column_].cumsum()
    # print(_bars_)
    _bars_['group'] = 0
    # print(_bars_)
    _bars_['filter'] = _bars_['filter'] / units
    # print(_bars_)
    _bars_['filter'] = np.nan_to_num(_bars_['filter'])

    _bars_['filter'] = _bars_['filter'].astype(int)
    # print(_bars_)
    _bars_['group'] = _bars_['filter']
    # print(_bars_)
    # _bars_ =
    # _bars_.groupby('group').agg({"time_stamp":"last","Price":'ohlc',"volume":'sum','transaction':'sum'})
    # # original version for ML class project
    _bars_ = _bars_.groupby('group').agg(
        {
            "Date": "last",
            "Time": "last",
            "Price": 'ohlc',
            "Vol": 'sum',
            'transaction': 'sum'})  # used for Tradestation tick files

    # print(_bars_)
    #
    _bars_.columns = _bars_.columns.droplevel()
    # print(_bars_)
    _bars_['vwap'] = _bars_['transaction'] / _bars_['Vol']
    #    #print(_bars_)
    #
    _bars_ = _bars_.rename(columns={"Vol": "vol"})
    print(_bars_.columns)
    print(_bars_)
    return _bars_
#


# In[54]:

def get_df_from_table(instrument, db_connection):
    """Given an instrument, returns a pandas dataframe from the relevant table in the database."""

    query = f"""
        SELECT *
        FROM {instrument}
    """
    return pd.read_sql(query, db_connection)


def add_bar_counter(df):
    """Adds a 'bar' count column based on the index which is automatically generating when querying the db."""
    df['bar'] = df.index


def get_display_range(slider, bars_to_display):
    """Set the range of bars to display, based on slider value and desired zoom level. Return (start, end)
    tuple of indices."""
    end = slider.value
    start = max(0, (end - bars_to_display))
    return start, end


def fetch_data(name):
    """Retrieve data from the db based on table name. Return a pandas dataframe."""
    dataframe = get_df_from_table(
        name, conn)[['date', 'open', 'high', 'low', 'close']][:]
    add_bar_counter(dataframe)
    return dataframe


def update_source(df, slider, bars_to_display):
    """Update the data source to be displayed.
    This is called once when the plot initiates, and then every time the slider moves, or a different instrument is
    selected from the dropdown.
    """
    start, end = get_display_range(slider, bars_to_display)

    # create new view from dataframe
    df_view = df.iloc[start:end]

    # create new source
    new_source = df_view.to_dict(orient='list')

    # add colors to be used for plotting bull and bear candles
    colors = ['green' if cl >= op else 'red' for (cl, op)
              in zip(df_view.close, df_view.open)]
    new_source['colors'] = colors

    # source.data.update(new_source)
    source.data = new_source


def make_subplot(src):

    #    newSrc = pd.DataFrame(src)
    #    newSrc = newSrc.rename(columns={0:"shortFCs",1:"longFCs"})
    #    newSrc['bar'] = newSrc.index
    #
    #    print(newSrc.columns)
    p = figure(title="forecast position", plot_width=1800, plot_height=200)

    #p.line('bar', 'shortFCs', source=src, line_color='red' )
    p.line('bar', 'FCs', source=src, line_color='green')
    p.line('bar', source=src, y=0, line_color='red')
    hover = HoverTool(tooltips=[
        ('bar', '@bar'),
        ('FCs', '@FCs{0.0f}'),
        ('close', '@close{0.0000f}')
    ]  # ,formatters={'date': 'datetime'}
    )
    p.add_tools(hover)

    return p


def make_PL_plot(src):
    p = figure(title="PL", plot_width=1800, plot_height=200)
    p.line('bar', 'commission', source=src, line_color='orange')
    p.line('bar', 'CumPL', source=src, line_color='grey')
    return p


def make_vol_plot(src):
    p = figure(title="vol bars", plot_width=1800, plot_height=200)
   # p.line('bar', 'periodVol', source=src, line_color='orange' )
    #p.line('bar', 'periodVol', source=src, line_color='grey' )
    p.line('bar', 'sine', source=src, line_color='red')
    p.line('bar', 'leadsine', source=src, line_color='darkviolet')
   # p.line('bar', 'volBBlower', source=src, line_color='red' )
    return p


def make_plot(src):
    """Draw the plot using the ColumnDataSource"""

    p = figure(title="Dollar bars", plot_width=1800, plot_height=800)
    p.segment(
        'bar',
        'high',
        'bar',
        'low',
        source=src,
        line_width=1,
        color='black')  # plot the wicks
    p.vbar(
        'bar',
        0.7,
        'close',
        'open',
        source=src,
        line_color='black',
        fill_color='colors',
    )  # plot the body
    #p.line('bar', 'ema_6', source=src, line_color='lightblue' )
    #p.line('bar', 'ema_16', source=src, line_color='darksalmon' )
    p.line('bar', 'state_means', source=src, line_color='green')
    #p.line('bar', 'KF_returns_log', source=src, line_color='red' )
    p.line('bar', 'KAMA16', source=src, line_color='blue')
    p.line('bar', 'KAMA64', source=src, line_color='black')

    #p.line('bar', 'FAMA', source=src, line_color='darkviolet' )
    #p.line('bar', 'KF_returns_log', source=src, line_color='red' )

    p.line('bar', 'BBupper', source=src, line_color='red')
    p.line('bar', 'BBmiddle', source=src, line_color='darkviolet')
    p.line('bar', 'BBlower', source=src, line_color='red')

    hover = HoverTool(tooltips=[
        ('bar', '@bar'),
        ('open', '@open{0.0000f}'),
        ('high', '@high{0.0000f}'),
        ('low', '@low{0.0000f}'),
        ('close', '@close{0.0000f}')
    ]  # ,formatters={'date': 'datetime'}
    )
    p.add_tools(hover)

   # p.line("bar", "ema_6")

    return p


def slider_handler(attr, old, new):
    """Handler function for the slider. Updates the ColumnDataSource to a new range given by the slider's position."""
    update_source(dollar_bars, slider, bars_to_display)


def Get_Dollar_Bar_Size(dollar_bars):

    dollar_bars['Price'] = pd.to_numeric(dollar_bars['Price'], errors='coerce')
    dollar_bars = dollar_bars.dropna()
    dollar_bars['VWAP'] = dollar_bars['Vol'] * dollar_bars['Price']
    dollar_bars['VWAP'] = pd.to_numeric(dollar_bars['VWAP'], errors='coerce')
    dollar_bars = dollar_bars.dropna()

    dollar_bars['daily_vwap'] = dollar_bars.groupby(['Date'])['VWAP'].cumsum()
    dvwap = dollar_bars.groupby(['Date'])['daily_vwap'].max()
    # dvwap.plot()
    avg_dvwap = dvwap.mean()
    # avg_dvwap
    # 8 hours of main trading session a day, 10 just looks legit
    bar_size = avg_dvwap / 10 / 8
    return bar_size


# In[48]:

# dollar_bars=pd.read_csv(r'e:\gdrive\code\USH19_12-2_dollar_bars_labelled_bars.csv')
# dollar_bars['Date']=dollar_bars['DayTime']

#dollar_bars=dollar_bars.loc[dollar_bars['dollar_returns_log'] > 0]


# In[3123]
# dollar_bars=pd.read_csv(r'e:\gdrive\code\USH19_11-30_dollar_bars_labelled_bars.csv')
# dollar_bars['Date']=dollar_bars['DateTime']
#dollar_bars=dollar_bars.loc[dollar_bars['dollar_returns_log'] > 0]
# dollar_bars=pd.read_csv(r'e:\gdrive\code\dollar_bars_labelled_bars.csv')
# dollar_bars['dollar_returns_log']*1000

# In[38]:
"""
#import pandas as pd
#dollar_bars=pd.read_csv(r'e:\gdrive\code\@USM19price 9_2018-3_2019.csv')
li = []
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2003-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2004-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2004-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2005-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2005-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2006-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2006-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2007-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2007-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2008-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2008-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2009-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.us2009-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2010-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2010-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2011-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2011-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2012-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2012-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2013-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2013-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2014-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2014-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2015-Jan-Jul.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2015-Jul-Dec.csv')
li.append(dollar_bars)
dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US2016-Jan-Jul.csv')
li.append(dollar_bars)

frame = pd.concat(li, axis=0, ignore_index=True)
dollar_bars=frame

dollar_bars["Date"]=pd.to_datetime(dollar_bars["Date"]).astype('datetime64[ns]')
dollar_bars.to_csv(r'e:\onedrive\data\TickData.US.csv')
"""

# %%


def AddStudies(dollar_bars):
    import numpy as np

    ##dollar_bars = create_bar(dollar_bars , 'transaction', 75000)
    # dollar_bars=pd.read_csv(r'G:\backups\data\USUS01_16.csv')
    dollar_bars

    dollar_bars = dollar_bars.assign(
        dollar_returns=dollar_bars['close'].diff())
    dollar_returns_log = np.log(dollar_bars['close']).diff()
    dollar_bars = dollar_bars.assign(
        dollar_returns_log=dollar_returns_log.values)

    dollar_bars.columns

    # dollar_bars=LinRegRollingWindow(dollar_bars)
    dollar_bars = RSI(dollar_bars, 21)
    dollar_bars = MOM(dollar_bars, 21)
    dollar_bars = CCI(dollar_bars, 14)
    dollar_bars = EMA(dollar_bars, 8, 'fast')
    dollar_bars = EMA(dollar_bars, 64, 'slow')
    dollar_bars = CalcEWMAC(dollar_bars, 'ema_fast', 'ema_slow')
    dollar_bars = MACD(dollar_bars, 21, 35)
    dollar_bars = CalcRollingCORR(dollar_bars)
    dollar_bars = CalcRollingCOV(dollar_bars)
    dollar_bars = CalcRollingKURT(dollar_bars)
    dollar_bars = CalcRollingSKEW(dollar_bars)
    dollar_bars = CalcRollingVAR(dollar_bars)
    # dollar_bars = CalculateLabels(dollar_bars) #direction change and volatility diff change
    #dollar_bars = CalcKalmanFilter(dollar_bars)
    #dollar_bars = LabelLongBars(dollar_bars)
    dollar_bars = LabelShortBars(dollar_bars)
    # dollar_bars["date"]=dollar_bars["DateTime"]

    dollar_bars["bar"] = dollar_bars.index

    #dollar_bars['KF_returns_log']= dollar_bars['close']-dollar_bars['state_means_returns_log']

    from talib import abstract
    from numpy import mean
    KAMA = abstract.KAMA
    KAMA = abstract.Function('KAMA')
    # print(KAMA.info)
    output1 = KAMA(dollar_bars, timeperiod=15)
    output2 = KAMA(dollar_bars, timeperiod=45)
    dollar_bars = dollar_bars.assign(KAMA16=output1)
    dollar_bars = dollar_bars.assign(KAMA64=output2)

    FAMA = abstract.KAMA
    FAMA = abstract.Function('KAMA')
    # print(FAMA.info)
    output1 = FAMA(dollar_bars, fastlimit=0, slowlimit=0)
    dollar_bars = dollar_bars.assign(FAMA=output1)

    MAVP = abstract.MAVP
    MAVP = abstract.Function('MAVP')
    # print(MAVP.info)
    #output1 = MAVP(dollar_bars)
    #dollar_bars=dollar_bars.assign(MAVP =output1)
    BBANDS = abstract.BBANDS
    BBANDS = abstract.Function('BBANDS')

    # print(BBANDS.info)
    df = abstract.BBANDS(
        dollar_bars,
        timeperiod=15,
        nbdevup=2,
        nbdevdn=2,
        matype=1)
    dollar_bars = dollar_bars.assign(BBupper=df['upperband'])
    dollar_bars = dollar_bars.assign(BBmiddle=df['middleband'])
    dollar_bars = dollar_bars.assign(BBlower=df['lowerband'])

    # ht=abstract.Function('HT_TRENDLINE')
    # ht=abstract.Function('HT_TRENDMODE')
    ht = abstract.Function('HT_SINE')
    # ht=abstract.Function('HT_PHASOR')

    ht_result = ht(dollar_bars)
    # dollar_bars=dollar_bars.assign(sine=ht_result)
    dollar_bars = dollar_bars.assign(sine=ht_result['sine'])
    dollar_bars = dollar_bars.assign(leadsine=ht_result['leadsine'])
    # dollar_bars=dollar_bars.assign(HT_DCPERIOD=ht_result['inphase'])
    # dollar_bars=dollar_bars.assign(ema_10=ht_result['quadrature'])

    #dollar_bars=EMA(dollar_bars, 10, column='sine')

    # parameters to be optimized are EMAs=6/16, RollingWindow=5, BarSize
    # factor=80, HT_SINE params, StopLoss=1000, +0.5/-0.5 in FCs
    dollar_bars = dollar_bars.assign(
        periodVolStd=dollar_bars['dollar_returns'].rolling(
            5, center=True).std())
    dollar_bars['periodVolStd']
    dollar_bars['VolAdjEMA'] = (
        dollar_bars['ema_fast'] - dollar_bars['ema_slow']) / dollar_bars['periodVolStd'] * 10
    dollar_bars['VolAdjEMA']

    import numpy as np
    dollar_bars['longs'] = dollar_bars['VolAdjEMA'].loc[(
        dollar_bars['VolAdjEMA'] >= 0)]
    dollar_bars['shorts'] = dollar_bars['VolAdjEMA'].loc[(
        dollar_bars['VolAdjEMA'] <= 0)]
    longs = dollar_bars['longs']
    shorts = dollar_bars['shorts']
    longs = np.nan_to_num(longs)
    shorts = np.nan_to_num(shorts)
    print('long Vol Adj EMAC', np.mean(longs))
    print('short Vol Adj EMAC', np.mean(shorts))

    dollar_bars['longs'] = np.where(longs > 20, 20, longs)  # longs#
    dollar_bars['shorts'] = np.where(shorts < -20, -20, shorts)  # shorts#
    return dollar_bars


# %%
# AddStudies(62500)
scaler = StandardScaler()
forecasts_S = pd.DataFrame()
forecasts_L = pd.DataFrame()
# %% comment to test second wave of data after train (fit) was done


def AddForecasts(dollar_bars, Train=True):

    # toggle between fit and transform for training and testing data sets
    # forecasts=scaler.fit_transform(dollar_bars[['shorts','longs']])

    if Train:
        forecasts_S = scaler.fit_transform(dollar_bars[['shorts']])
        print("forecasts_S - ", forecasts_S)
        forecasts_L = scaler.fit_transform(dollar_bars[['longs']])
        print("forecasts_L - ", forecasts_L)

    else:
        forecasts_S = scaler.fit_transform(dollar_bars[['shorts']])
        forecasts_L = scaler.fit_transform(dollar_bars[['longs']])

    dollar_bars['shortFCs'] = pd.DataFrame(forecasts_S[:, 0])
    dollar_bars['longFCs'] = pd.DataFrame(forecasts_L[:, 0])
    dollar_bars['shortFCs'] = dollar_bars['shortFCs'] - .5

    dollar_bars['longFCs'] = dollar_bars['longFCs'] + .5

    dollar_bars['FCs'] = dollar_bars['longFCs'] + dollar_bars['shortFCs']
    dollar_bars['FCs'] = np.around(dollar_bars['FCs'].values)
    #
    #dollar_bars['FCs']=dollar_bars['FCs'].replace(3, 35)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace(1, 15)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace(2, 25)
    #
    #dollar_bars['FCs']=dollar_bars['FCs'].replace(-3, -35)
    # dollar_bars['FCs']=dollar_bars['FCs'].replace(-1,-15)
    # dollar_bars['FCs']=dollar_bars['FCs'].replace(-2,-25)
    #
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( -25,2)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( 25,-2)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( -35,1)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( 35,-1)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( -15,3)
    #dollar_bars['FCs']=dollar_bars['FCs'].replace( 15,-3)

   # if HT_sine is trending, use trend following EWMAC, else, use reverse trend following EWMAC, i.e. mean reversal
    # shift down 1, since position will be entered on bar close
    trend_following = (dollar_bars['sine'] - dollar_bars['leadsine'])
    dollar_bars['shifted_leadsine'] = dollar_bars['leadsine'].shift(-1)
    dollar_bars['diff_leadsine'] = dollar_bars['shifted_leadsine'] - \
        dollar_bars['leadsine']
    #dollar_bars['position']=dollar_bars['FCs'].shift(1)*(np.where( trend_following  > 0 ,1,-1))
    dollar_bars['position'] = dollar_bars['FCs'].shift(
        1) * (np.where(trend_following > 0, 1, -1))

    dollar_bars['trend_following'] = np.where(trend_following > 0, 1, -1)
    dollar_bars['trend_following'] = dollar_bars['trend_following'].shift(1)
    # dollar_bars=dollar_bars.dropna()
    # new system
    dollar_bars['position'] = np.where(
        dollar_bars['trend_following'] == -1, np.where(
            dollar_bars['diff_leadsine'] > 0, abs(
                dollar_bars['position']), -1 * abs(
                dollar_bars['position'])), dollar_bars['position'])

    dollar_bars['prev_position'] = dollar_bars['position'].shift(1)

    # calculate trade number and whether this is a new trade or not, to be
    # used in stop loss actioning
    dollar_bars['new_trade'] = np.where(
        (((dollar_bars['position'] > 0) & (
            dollar_bars['prev_position'] <= 0)) | (
            (dollar_bars['position'] < 0) & (
                dollar_bars['prev_position'] >= 0))), 1, 0)
    dollar_bars['new_trade'] = dollar_bars['new_trade'].shift(1)
    dollar_bars['trade_number'] = dollar_bars['new_trade'].cumsum()
    return dollar_bars
# %%

# AddForecasts()

# %%


def AddStopLoss(dollar_bars):

    # if it is a new trade, keep adding PL, else, put 0
    stop_loss = -500
    # dollar_bars['IntraTrade_P_DD']=dollar_bars['PL'].copy()
    dollar_bars['IntraTrade_P_DD'] = dollar_bars.groupby(
        ['trade_number'])['dollar_returns'].cumsum() * 1000
    #dollar_bars['IntraTrade_P_DD'] = np.where((dollar_bars['new_trade'] == 0),dollar_bars['IntraTrade_P_DD'].rolling(2).sum(),dollar_bars['PL'])
    # (dollar_bars['position_stoploss_start']>0) &
    dollar_bars['IntraTrade_P_DD']
    dollar_bars['position_stoploss_start'] = np.where(
        (dollar_bars['IntraTrade_P_DD'].shift(1) <= stop_loss), 1, 0)  # sys.maxsize)
    #dollar_bars['position_stoploss_seq'] = np.where(( (dollar_bars['trade_number'].shift(1)==dollar_bars['trade_number'])) ,1,0)
    #print (dollar_bars[['position_stoploss_start', 'position_stoploss_seq','trade_number']])
    dollar_bars['stop_loss'] = dollar_bars.groupby(
        ['trade_number'])['position_stoploss_start'].cumsum()
    print(
        dollar_bars[['stop_loss', 'position_stoploss_start', 'trade_number']])
    #dollar_bars['temp'] = np.where((dollar_bars['position_stoploss_start']==dollar_bars.index),dollar_bars['position'])
    # |((dollar_bars['trade_number'].shift(1)==dollar_bars['trade_number']) &
    # (np.min(dollar_bars.groupby(['trade_number'])['IntraTrade_P_DD']) <= stop_loss))
    #dollar_bars['position_stoploss'] =dollar_bars['position_stoploss_start'] *dollar_bars['position_stoploss_seq']
    dollar_bars['position_with_stoploss'] = np.where(
        (dollar_bars['stop_loss'] > 0), 0, dollar_bars['position'])
    # dollar_bars['position_with_stoploss'].cumsum()
    # dollar_bars['position'].cumsum()
    return dollar_bars
# %%

# AddStopLoss()
# %%


def AddPL(dollar_bars):
    dollar_bars['PL'] = dollar_bars['position_with_stoploss'] * \
        dollar_bars['dollar_returns'] * 1000
    # dollar_bars['PL']=dollar_bars['position']*dollar_bars['dollar_returns']*1000
    dollar_bars['CumPL'] = dollar_bars['PL'].cumsum()
    dollar_bars['Signals'] = (dollar_bars['FCs'].diff())
    # dollar_bars['Trades']=abs(dollar_bars['position'].diff())
    dollar_bars['Trades'] = abs(dollar_bars['position_with_stoploss'].diff())
    dollar_bars['commission'] = dollar_bars['Trades'].cumsum() * 2.5
    dollar_bars['NetCumPL'] = dollar_bars['CumPL'] - dollar_bars['commission']
    dollar_bars['NetPL'] = dollar_bars['PL'] - dollar_bars['Trades'] * 2.5
    dollar_bars['MaxEquity'] = dollar_bars['NetPL'].rolling(2).max()
    return dollar_bars


def sharpe(y, num_days):
    # 21 days per month X 6 months = 126
    return np.sqrt(num_days) * (np.mean(y) / np.std(y))
#    return (np.mean(y) / np.std(y)) # 21 days per month X 6 months = 126
    # %%


def CalcAnalytics(dollar_bars):
    # dollar_bars.Date=pd.to_datetime(dollar_bars.Date)
    # Calculate rolling Sharpe ratio
    #SharpeRatio = sharpe(dollar_bars['NetPL'],len(dollar_bars['Date']))
    # expected profitability percentage per risked dollar
    MySharpeRatio = np.mean(
        dollar_bars['NetPL']) / dollar_bars['NetPL'].std() * 100
    #dollar_bars['rs'] = [my_rolling_sharpe(dollar_bars.loc[d - pd.offsets.DateOffset(months=6):d, 'NetPL']) for d in dollar_bars.Date]
    print('SR:              ', MySharpeRatio)

    AvgProfitPerTrade = dollar_bars.loc[dollar_bars['NetPL'] > 0, 'NetPL'].sum(
    ) / dollar_bars['Trades'].sum()
    AvgLossPerTrade = dollar_bars.loc[dollar_bars['NetPL'] < 0, 'NetPL'].sum(
    ) / dollar_bars['Trades'].sum()
    print('AvgProfitPerTrade', AvgProfitPerTrade)
    print('AvgLossPerTrade  ', AvgLossPerTrade)
    print('AvgTradePL       ', AvgProfitPerTrade + AvgLossPerTrade)
    print('Total Trades     ', dollar_bars['Trades'].sum())
    print('Bars in the black', len(dollar_bars.loc[dollar_bars['NetPL'] < 0]))
    print('Bars in the red  ', len(dollar_bars.loc[dollar_bars['NetPL'] > 0]))

    plt.hist(dollar_bars['FCs'], normed=True, bins=5)
    plt.ylabel('Probability')

    # dollar_bars['BBmiddle'].values
    print(dollar_bars['NetCumPL'])
    print('max Eq ', np.max(dollar_bars['NetCumPL']))


# %%
# AddPL()


def get_thursday(cal, year, month, thursday_number):
    '''
    For example, get_thursday(cal, 2017,8,0) returns (2017,8,3)
    because the first thursday of August 2017 is 2017-08-03
    '''
    monthcal = cal.monthdatescalendar(year, month)
    selected_thursday = [day for week in monthcal for day in week if
                         day.weekday() == calendar.THURSDAY and
                         day.month == month][thursday_number]
    return selected_thursday


def get_tuesday(cal, year, month, tuesday_number):

    monthcal = cal.monthdatescalendar(year, month)
    selected_tuesday = [day for week in monthcal for day in week if
                        day.weekday() == calendar.TUESDAY and
                        day.month == month][tuesday_number]
    return selected_tuesday


# Show the use of get_thursday()
cal = calendar.Calendar(firstweekday=calendar.MONDAY)
today = datetime.datetime.today()
year = today.year
month = today.month
# -1 because we want the last Thursday
date = get_thursday(cal, year, month, -1)
print('date: {0}'.format(date))  # date: 2017-08-31

# %%
util.startLoop()


def GetInfluxdbPandasClient():
    """Instantiate the connection to the InfluxDB client."""
    user = 'root'
    password = 'root'
    dbname = 'tick_data'
    protocol = 'json'
    host = 'localhost'
    port = 8086
    client = DataFrameClient(host, port, user, password, dbname)
    return client


# %%
client = GetInfluxdbPandasClient()


def GetAllTicksInDB(table):

    result = client.query(
        "select * from " +
        table +
        " order by time asc")  # epoch='ns')
    result

    try:
        df_result = pd.DataFrame(result[table.replace('"', '')])

        return df_result

    except BaseException:
        return 'no ticks'  # d


def GetHistoricalTicksInDB(table):

    result = client.query(
        "select * from " +
        table +
        " where hist=1 order by time asc")  # epoch='ns')
    result

    try:
        df_result = pd.DataFrame(result[table.replace('"', '')])

        return df_result

    except BaseException:
        return 'no ticks'  # d


def GetLiveTicksInDB(table):

    result = client.query(
        "select * from " +
        table +
        " where hist=0 order by time asc")  # epoch='ns')
    result

    try:
        df_result = pd.DataFrame(result[table.replace('"', '')])

        return df_result

    except BaseException:
        return 'no ticks'  # d


# %%
cont_id = "1906"
cont_symbol = 'US'
table = cont_symbol + '20' + cont_id
dollar_bars = GetAllTicksInDB(table)
dollar_bars.index
dollar_bars
# dollar_bars=pd.read_csv(r'e:\onedrive\data\IB-USM19-notCont-data.csv')
# dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.US.csv')
# dollar_bars=pd.read_csv(r'e:\onedrive\data\@USM19price.csv')
# dollar_bars=pd.read_csv(r'e:\onedrive\data\@USZ18Trades.csv')
#dollar_bars=pd.read_csv(r'e:\gdrive\code\@USM19price 9_2018-3_2019.csv')
# dollar_bars=pd.read_csv(r'E:\OneDrive\data\TickData.US2016-Jul-Dec.csv')
# dollar_bars=pd.read_csv(r'E:\OneDrive\data\TickData.US2016-Jan-Jul.csv')
#dollar_bars['Date'] = dollar_bars['Date'].str.replace(" 0","")
#dollar_bars['Date'] = dollar_bars['Date'].str.strip()
dollar_bars['Timestamp'] = dollar_bars.index.astype('datetime64[ns]')
dollar_bars = dollar_bars.set_index(dollar_bars['Timestamp'])
dollar_bars = dollar_bars.sort_index()
dollar_bars['Time'] = [d.time() for d in dollar_bars['Timestamp']]
dollar_bars['Date'] = [d.date() for d in dollar_bars['Timestamp']]
dollar_bars.columns
dollar_bars = dollar_bars.rename(
    columns={
        "price": "Price",
        "size": "Vol"})  # used for tickdata exported files
# %%
dollar_bars = dollar_bars.drop(dollar_bars[(dollar_bars['Date'].astype(
    'datetime64[ns]') <= datetime.datetime(2019, 3, 20))].index)
dollar_bars = dollar_bars.drop(dollar_bars[(dollar_bars['Date'].astype(
    'datetime64[ns]') >= datetime.datetime(2019, 5, 31))].index)
#dollar_bars = dollar_bars.drop(dollar_bars[(dollar_bars['Date'].astype('datetime64[ns]')<=datetime.datetime(2018,12,20))].index)
#dollar_bars = dollar_bars.drop(dollar_bars[(dollar_bars['Date'].astype('datetime64[ns]')>=datetime.datetime(2019,2,28))].index)

AllData = dollar_bars.copy()

dollar_bars['Vol'] = 1
# dollar_bars=AllData
# %% execute this block in train, skip in test
# calculate bar size to the nearest smaller 32 multiple
'''
bar_size=Get_Dollar_Bar_Size(dollar_bars)
bar_size
bar_size=bar_size//32
bar_size=bar_size*32
bar_size
'''
# select the bar size that is closest to the output from Get_dollar_bar_size
# %%
dollar_bars = CreateDollarBars(dollar_bars, bar_size)
# dollar_bars.to_csv(r'e:\onedrive\data\TickData.'+file_name+'bars.csv')
# dollar_bars.to_csv(r'e:\onedrive\data\\'+table+'_bars.csv')
#
# dollar_bars=pd.read_csv(r'e:\onedrive\data\TickData.@US-16-mbars.csv')
# dollar_bars=pd.read_csv(r'e:\onedrive\data\USM19dollarbars.csv')
# dollar_bars=pd.read_csv(r'e:\onedrive\data\@us18'+'bars.csv')

dollar_bars = AddStudies(dollar_bars)
dollar_bars = AddForecasts(dollar_bars, Train=False)
dollar_bars = AddStopLoss(dollar_bars)
dollar_bars = AddPL(dollar_bars)
CalcAnalytics(dollar_bars)

dollar_bars.to_csv(r'c:\test\ewmac-ib-influx-' + table + '.csv')