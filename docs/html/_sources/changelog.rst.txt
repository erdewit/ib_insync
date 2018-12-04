Changelog
=========

0.9
---

Version 0.9.39
^^^^^^^^^^^^^^

* Handle partially filled dividend data.
* Use secType='WAR' for warrants.

Version 0.9.38
^^^^^^^^^^^^^^

* ibapi v97.4 is now required.
* fixed tickByTick wrappers.

Version 0.9.37
^^^^^^^^^^^^^^

* Backward compatibility with older ibapi restored.

Version 0.9.36
^^^^^^^^^^^^^^

* Compatibility with ibapi v974.
* Client.setConnectOptions() added (for PACEAPI).

Version 0.9.35
^^^^^^^^^^^^^^

* ``Ticker.hasBidAsk()`` added.
* ``IB.newsBulletinEvent`` added.
* Various small fixes.

Version 0.9.34
^^^^^^^^^^^^^^

* Old event system (ib.setCallback) removed.
* Compatibility fix with previous ibapi version.

Version 0.9.33
^^^^^^^^^^^^^^

* Market scanner subscription improved.
* IB.scannerDataEvent now emits the full list of ScanData.
* ScanDataList added.

Version 0.9.32
^^^^^^^^^^^^^^

* Autocompletion with Jedi plugin as used in Spyder and VS Code working again.

Version 0.9.31
^^^^^^^^^^^^^^

* Requst results will return specialized contract types (like Stock)
  instead of generic Contract.
* ``IB.scannerDataEvent`` added.
* ContractDetails field ``summary`` renamed to ``contract``.
* ``isSmartDepth`` parameter added for ``reqMktDepth``.
* Event loop nesting is now handled by the
  `nest_asyncio project <https://github.com/erdewit/nest_asyncio>`_.
* ``util.useQt`` is rewritten so that it can be used with any asyncio
  event loop, with support for both PyQt5 and PySide2.
  It does not use quamash any more.
* Various fixes, extensive documentation overhaul and
  flake8-compliant code formatting.

Version 0.9.30
^^^^^^^^^^^^^^

* Watchdog.stop() will not trigger restart now
* Fixed bug #93

Version 0.9.29
^^^^^^^^^^^^^^
* util.patchAsyncio() updated for Python 3.7

Version 0.9.28
^^^^^^^^^^^^^^

* IB.RequestTimeout added
* util.schedule() accepts tz-aware datetimes now
* Let client.disconnect() complete when no event loop is running

Version 0.9.27
^^^^^^^^^^^^^^
* Fixed bug #77

Version 0.9.26
^^^^^^^^^^^^^^
* PR #74 merged (ib.reqCurrentTime method added)
* Fixed bug with order error handling

Version 0.9.25
^^^^^^^^^^^^^^
* Default throttling rate now compatible with reqTickers
* Fixed issue with ib.waitOnUpdate in combination with ib.pendingTickersEvent
* Added timeout parameter for ib.waitOnUpdate

Version 0.9.24
^^^^^^^^^^^^^^
* ``ticker.futuresOpenInterest`` added
* ``execution.time`` was string, is now parsed to UTC datetime
* ``ib.reqMarketRule`` request added

Version 0.9.23
^^^^^^^^^^^^^^
* Compatability with Tornado 5 as used in new Jupyter notebook server

Version 0.9.22
^^^^^^^^^^^^^^
* updated ib.reqNewsArticle and ib.reqHistoricalNews to ibapi v9.73.07

Version 0.9.21
^^^^^^^^^^^^^^

* updated ib.reqTickByTickData signature to ibapi v9.73.07 while keeping backward compatibility

Version 0.9.20
^^^^^^^^^^^^^^

* Fixed watchdog bug

Version 0.9.19
^^^^^^^^^^^^^^
* Don't overwrite exchange='SMART' in qualifyContracts

Version 0.9.18
^^^^^^^^^^^^^^
* Merged PR #65 (Fix misnamed event)


Version 0.9.17
^^^^^^^^^^^^^^
* New IB events disconnectedEvent, newOrderEvent, orderModifyEvent and cancelOrderEvent
* Watchdog improvements


Version 0.9.16
^^^^^^^^^^^^^^
* New event system that will supersede IB.setCallback
* Notebooks updated to use events
* Watchdog must now be given an IB instance

Version 0.9.15
^^^^^^^^^^^^^^

* Fixed bug in default order conditions
* Fixed regression from v0.9.13 in ``placeOrder``

Version 0.9.14
^^^^^^^^^^^^^^

* Fixed ``orderStatus`` callback regression

Version 0.9.13
^^^^^^^^^^^^^^

* Log handling improvements
* Client with clientId=0 can now manage manual TWS orders
* Client with master clientId can now monitor manual TWS orders


Version 0.9.12
^^^^^^^^^^^^^^

* Run IBC and IBController directly instead of via shell

Version 0.9.11
^^^^^^^^^^^^^^

* Fixed bug when collecting ticks using ib.waitOnUpdate()
* Added ContFuture class (continuous futures)
* Added Ticker.midpoint()

Version 0.9.10
^^^^^^^^^^^^^^

* ib.accountValues() fixed for use with multiple accounts

Version 0.9.9
^^^^^^^^^^^^^

* Fixed issue #57

Version 0.9.8
^^^^^^^^^^^^^

* Fix for ib.reqPnLSingle

Version 0.9.7
^^^^^^^^^^^^^

* Profit and Loss (PnL) funcionality added

Version 0.9.6
^^^^^^^^^^^^^

* IBC added
* PR #53 (delayed greeks) merged
* Ticker.futuresOpenInterest field removed

Version 0.9.5
^^^^^^^^^^^^^

* Fixed canceling bar and tick subscriptions

Version 0.9.4
^^^^^^^^^^^^^

* Fixed issue #49

Version 0.9.3
^^^^^^^^^^^^^

* Watchdog class added
* ib.setTimeout() added
* Ticker.dividends added for use with genericTickList 456
* Errors and warnings will now log the contract they apply to
* IB error() callback signature changed to include contract
* Fix for issue #44

Version 0.9.2
^^^^^^^^^^^^^

* historical ticks and realtime bars now return time in UTC

Version 0.9.1
^^^^^^^^^^^^^

* IBController added
* openOrder callback added
* default arguments for ib.connect() and ib.reqMktData()

Version 0.9.0
^^^^^^^^^^^^^

* minimum API version is v9.73.06
* tickByTick support
* automatic request throttling
* ib.accountValues() now works for multiple accounts
* AccountValue.modelCode added
* Ticker.rtVolume added

0.8
---

Version 0.8.17
^^^^^^^^^^^^^^

* workaround for IBAPI v9.73.06 for Contract.lastTradeDateOrContractMonth format

Version 0.8.16
^^^^^^^^^^^^^^

* util.tree() method added
* ``error`` callback signature changed to (reqId, errorCode, errorString)
* ``accountValue`` and ``accountSummary`` callbacks added

Version 0.8.15
^^^^^^^^^^^^^^

* util.useQt fixed for use with Windows

Version 0.8.14
^^^^^^^^^^^^^^

* Fix for ib.schedule()

Version 0.8.13
^^^^^^^^^^^^^^

* Import order conditions into ib_insync namespace
* util.useQtAlt() added for using nested event loops on Windows with Qt
* ib.schedule() added

Version 0.8.12
^^^^^^^^^^^^^^

* Fixed conditional orders

Version 0.8.11
^^^^^^^^^^^^^^

* FlexReport added

Version 0.8.10
^^^^^^^^^^^^^^

* Fixed issue #22

Version 0.8.9
^^^^^^^^^^^^^
* Ticker.vwap field added (for use with generic tick 233)
* Client with master clientId can now monitor orders and trades of other clients

Version 0.8.8
^^^^^^^^^^^^^
* ``barUpdate`` event now used also for reqRealTimeBars responses
* ``reqRealTimeBars`` will return RealTimeBarList instead of list
* realtime bars example added to bar data notebook
* fixed event handling bug in Wrapper.execDetails

Version 0.8.7
^^^^^^^^^^^^^
* BarDataList now used with reqHistoricalData; it also stores the request parameters
* updated the typing annotations
* added ``barUpdate`` event to ``IB``
* bar- and tick-data notebooks updated to use callbacks for realtime data

Version 0.8.6
^^^^^^^^^^^^^
* ticker.marketPrice adjusted to ignore price of -1
* ticker.avVolume handling fixed

Version 0.8.5
^^^^^^^^^^^^^
* realtimeBar wrapper fix
* context manager for IB and IB.connect()

Version 0.8.4
^^^^^^^^^^^^^
* compatibility with upcoming ibapi changes
* added ``error`` event to ``IB``
* notebooks updated to use ``loopUntil``
* small fixes and performance improvements

Version 0.8.3
^^^^^^^^^^^^^
* new IB.reqHistoricalTicks API method
* new IB.loopUntil method
* fixed issues #4, #6, #7

Version 0.8.2
^^^^^^^^^^^^^
* fixed swapped ticker.putOpenInterest vs ticker.callOpenInterest

Version 0.8.1
^^^^^^^^^^^^^

* fixed wrapper.tickSize regression

Version 0.8.0
^^^^^^^^^^^^^

* support for realtime bars and keepUpToDate for historical bars
* added option greeks to Ticker
* new IB.waitUntil and IB.timeRange scheduling methods
* notebooks no longer depend on PyQt5 for live updates
* notebooks can be run in one go ('run all')
* tick handling bypasses ibapi decoder for more efficiency

0.7
---

Version 0.7.3
^^^^^^^^^^^^^

* IB.whatIfOrder() added
* Added detection and warning about common setup problems

Version 0.7.2
^^^^^^^^^^^^^

* Removed import from ipykernel

Version 0.7.1
^^^^^^^^^^^^^

* Removed dependencies for installing via pip

Version 0.7.0
^^^^^^^^^^^^^

* added lots of request methods
* order book (DOM) added
* notebooks updated

0.6
---

Version 0.6.1
^^^^^^^^^^^^^

* Added UTC timezone to some timestamps
* Fixed issue #1

Version 0.6.0
^^^^^^^^^^^^^

* Initial release