#!/usr/bin/env python
# coding: utf-8

# # Ordering
# 
# 
# ## Warning: This notebook will place live orders
# 
# Use a paper trading account (during market hours).
# 

# In[1]:


from ib_insync import *
util.startLoop()

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=13)


# Create a contract and a market order:

# In[2]:


contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

order = MarketOrder('BUY', 100)


# placeOrder will place the order order and return a ``Trade`` object right away (non-blocking):

# In[3]:


trade = ib.placeOrder(contract, order)

trade


# ``trade`` contains the order and everything related to it, such as order status, fills and a log.
# It will be live updated with every status change or fill of the order.

# In[4]:


ib.sleep(1)
trade.log


# ``trade`` will also available from ``ib.trades()``:

# In[5]:


assert trade in ib.trades()


# Likewise for ``order``:

# In[6]:


assert order in ib.orders()


# Now let's create a limit order with an unrealistic limit:

# In[7]:


limitOrder = LimitOrder('BUY', 100, 0.05)
limitTrade = ib.placeOrder(contract, limitOrder)

limitTrade


# ``status`` will change from "PendingSubmit" to "Submitted":

# In[8]:


ib.sleep(1)
assert limitTrade.orderStatus.status == 'Submitted'


# In[9]:


assert limitTrade in ib.openTrades()


# Let's modify the limit price and resubmit:

# In[10]:


limitOrder.lmtPrice = 0.10

ib.placeOrder(contract, limitOrder)


# And now cancel it:

# In[11]:


ib.cancelOrder(limitOrder)


# In[12]:


limitTrade.log


# placeOrder is not blocking and will not wait on what happens with the order.
# To make the order placement blocking, that is to wait until the order is either
# filled or canceled, consider the following:

# In[13]:


get_ipython().run_cell_magic('time', '', "order = MarketOrder('BUY', 100)\n\ntrade = ib.placeOrder(contract, order)\nwhile not trade.isDone():\n    ib.waitOnUpdate()")


# What are our positions?

# In[14]:


ib.positions()


# What's the total of commissions paid today?

# In[15]:


sum(fill.commissionReport.commission for fill in ib.fills())


# whatIfOrder can be used to see the commission and the margin impact of an order without actually sending the order:

# In[16]:


order = MarketOrder('SELL', 200)
ib.whatIfOrder(contract, order)


# In[17]:


ib.disconnect()


# In[ ]:




