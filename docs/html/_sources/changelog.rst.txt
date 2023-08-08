Changelog
=========

0.9
---


Version 0.9.86
^^^^^^^^^^^^^^

* Fixed: :issue:`588`: Fixed account summary tag.
* Fixed: :issue:`589`: Fixed more account summary tags.
* pull:`598`: Year updates

Version 0.9.85
^^^^^^^^^^^^^^
 * Fixed: :issue:`586`: Revert socket protocol back to version 176.

Version 0.9.84
^^^^^^^^^^^^^^
* Potential fix for ``reqWshEventData``.

Version 0.9.83
^^^^^^^^^^^^^^
* Added support for WSH (Wall Street Horizon) requests plus
  the (blocking) convenience methods ``getWshMetaData`` and ``getWshEventData``.
* Updated socket protocol to version 177.
* Added support for ``Event`` security type.

Version 0.9.82
^^^^^^^^^^^^^^

* Fixed: :issue:`534`: Session parsing for Forex contracts.
* Fixed: :issue:`536`: Handle empty session field.
* Fixed: :issue:`541`: Remove superfluous closing bracket.
* Fixed: :issue:`542`: Use float size for ``pnlSingle``.
* Fixed: :issue:`544`: Cancel head-time request after completion.
* Fixed: :issue:`545`: Return ``Trade`` instead of ``Order`` for
  ``reqOpenOrders`` and ``reqAllOpenOrders``.
* :pull:`553`: Volume bar added.
* :pull:`565`: Typo fix.

Version 0.9.81
^^^^^^^^^^^^^^

* Add ``ContractDetails.tradingSessions()`` and
  ``ContractDetails.liquidSessions()`` to parse session times.
* Fix ``IBC.on2fatimeout`` command line argument for Unix.

Version 0.9.80
^^^^^^^^^^^^^^

* Fix ``ib.reqMatchingSymbols`` to handle bond contracts.

Version 0.9.79
^^^^^^^^^^^^^^

* Fix datetime parsing.

Version 0.9.78
^^^^^^^^^^^^^^

* Added ``account`` parameter to ``ib.portfolio()``.
* Added ``IBC.on2fatimeout`` field.
* Removed obsolete ``IBController``.
* Fixed: :issue:`530`: Use explicit timezone in requests as per new API requirement.

Version 0.9.77
^^^^^^^^^^^^^^

* :pull:`528`: Fixes regression in ``client.py``.

Version 0.9.76
^^^^^^^^^^^^^^

* Fixed: :issue:`525`: For ``whatIf`` request treat error 110 as failure.

Version 0.9.75
^^^^^^^^^^^^^^

* Fixed: :issue:`524`: Use fix from Papakipos for issue with ``FlexReport`` downloading.

Version 0.9.74
^^^^^^^^^^^^^^

* Fix ``reqContractDetails`` bug in combination with latest TWS.
* Update the code to comply with stricter MyPy checks.

Version 0.9.73
^^^^^^^^^^^^^^

* :pull:`523`: Fix ``completedOrder`` parsing for new socket protocol.

Version 0.9.72
^^^^^^^^^^^^^^

* :pull:`507`: Fixes ``bondContractDetails`` request.
* Fixed: :issue:`502`: Treat error 110 as a warning.
* Added ``manualOrderTime`` and ``manualCancelOrderTime`` for audit trails.
* Added ``PEG MID`` and ``PEG BEST`` order types.
* Added contract fields ``description`` and ``issuerId``.
* Added ``IB.reqUserInfo()``.
* Support socket protocol version 176.

Version 0.9.71
^^^^^^^^^^^^^^

* :pull:`453`: Added support for ``bidExchange`` and ``askExchange`` fields to ``Ticker``.
* :pull:`489`: ``Watchdog.start()`` now returns a ``Future``.
* Fixed: :issue:`439`: Set ``marketDataType`` directly on ``Ticker``.
* Fixed: :issue:`441`: Add explicit timezone of None to accomodate pandas Timestamp.
* Fixed: :issue:`471`: Revised ``Ticker.marketPrice()`` calculation.
* Added ``minTick``, ``bboExchange`` and ``snapshotPermissions`` fields to ``Ticker``.
* Added ``minSize``, ``sizeIncrement`` and ``suggestedSizeIncrement`` fields to ``ContractDetails``.
* Added ``IB.reqHistoricalSchedule`` request.
* Added ``IB.reqSmartComponents`` request.
* Added ``Order.advancedErrorOverride`` field. Any advanced error message is made availble from
  ``Trade.advancedError``.
* Added a `recipe for integration with PyGame <https://ib-insync.readthedocs.io/recipes.html#integration-with-pygame>`_.
* Minimum required TWSAPI client protocol version is 157 now.

Version 0.9.70
^^^^^^^^^^^^^^

* Fixed: :issue:`413`: Set the appropriate events as done on disconnect.
* Exported symbols are now static so that the VSCode/PyLance code analyzer can understand it.

Version 0.9.69
^^^^^^^^^^^^^^

* Fixed: :issue:`403`: Change validity test for whatIfOrder response.

Version 0.9.68
^^^^^^^^^^^^^^

* Fixed: :issue:`402`: Downloading historical ticks for crypto currencies.

Version 0.9.67
^^^^^^^^^^^^^^

* ``Crypto`` security class added. To accommodate fractional crypto currency sizes,
  all the various ``size`` and ``volume`` fields that were of type ``int`` are now of type ``float``.
* :pull:`385`: Get day trades remaining for next four days in ``IB.accountSummary``.
* Fixed: :issue:`361`: Prevent ``util.logToConsole`` and ``util.logToFile`` from messing with the root logger.
* Fixed: :issue:`370`: Catch ``asyncio.CancelledError`` during connect.
* Fixed: :issue:`371`: Fix type annotation for ``reqMarketRuleAsync``.
* Fixed: :issue:`380`: Reject bogus ``whatIf`` order response.
* Fixed: :issue:`389`: Add ``TradeLogEntry.errorCode`` field.

Version 0.9.66
^^^^^^^^^^^^^^

* Fixed: :issue:`360`: Improved disconnect.
* Fixed issue with duplicate orderId.
* Update ``Order`` default values to work with the latest beta TWS/gateway.
* :pull:`348`: Added PySide6 support.

Version 0.9.65
^^^^^^^^^^^^^^

* Fixed: :issue:`337`.
* :pull:`317`: Update and order's ``totalQuantity``, ``lmtPrice``, ``auxPrice`` and ``orderType``
  when the order is modified externally.
* :pull:`332`: Typo.

Version 0.9.64
^^^^^^^^^^^^^^

* Fixed: :issue:`309`: Aggregate past fills into the ``Trade`` they belong to upon connect.
* ``ContFut`` objects are now hashable (:issue:`310`).
* Added ``Watchdog.probeTimeout`` parameter (:issue:`307`).

Version 0.9.63
^^^^^^^^^^^^^^

* Fixed :issue:`282`: ``util.Qt()`` also works with the ProactorEventLoop
  (default on Windows) now.
* Fixed :issue:`303`: A regression in TWS 480.4l+ is bypassed now to avoid
  ``IB.connect()`` timeouts. Request timeouts during syncing are logged as errors but will let
  the connect proceed.

Version 0.9.62
^^^^^^^^^^^^^^

* ``IB.TimezoneTWS`` field added, for when the TWS timezone differs from the
  local system timezone (:issue:`287`).
* ``IB.RaiseRequestErrors`` field added, can be set to ``True`` to raise
  ``RequestError`` when certain requests fail, instead of returning
  empty data (:pull:`296`).
* ``IB.accountSummaryAsync()`` method added (:issue:`267`).
* ``Watchdog.probeContract`` field added, to use a contract other then EURUSD
  for probing the data connection (:issue:`298`).
* ``Ticker.rtTime`` added (:issue:`274`, :pull:`275`). Please note that this
  timestamp appears to be mostly bogus.
* Fixed :issue:`270`: Clear ticker depth data when canceling market
  depth subscription.
* Fixed issue with duplicate order IDs.

Version 0.9.61
^^^^^^^^^^^^^^
* ``Ticker.marketDataType`` added to indicate the delayed/frozen status of
  the ``reqMktData`` ticks.

Version 0.9.60
^^^^^^^^^^^^^^

* ``IB.reqHistoricalData()`` has a new ``timeout`` parameter that automatically
  cancels the request after timing out.
* ``BracketOrder`` is iterable again.
* ``IB.waitOnUpdate()`` returns ``False`` on timeout now.
* :pull:`210`: Fix decoding of execDetails time.
* :pull:`215`: New scanner notebook added, courtesy of C. Valcarcel.
* :pull:`220`: Added ``readonly`` option for Watchdog.
* Fixed :issue:`221`: Delayed close ticks handling by ``Ticker``.
* Fixed :issue:`224`: Added timeout for ``completedOrders`` request during connect.
* Fixed :issue:`227`: ``IB.MaxSyncedSubAccounts`` added.
* Fixed :issue:`230`: Fixed ``IB.reqHistogramData`` method.
* Fixed :issue:`235`: ``Order.discretionaryAmt`` is now of type ``float`` (was ``int``).
* Fixed :issue:`236`: ``ticker.updateEvent`` is now fired for any change made to the ticker.
* Fixed :issue:`245`: Emit ``trade.statusEvent`` when order is implicitly canceled by a problem.
* You can now `sponsor the development of IB-insync! <https://github.com/sponsors/erdewit>`_

Version 0.9.59
^^^^^^^^^^^^^^

* PR #205 adds more typing annotations.
* ``dataclasses`` are now used for objects (instead of inheriting from a base
  ``Object``). For Python 3.6.* install it with ``pip install dataclasses``

Version 0.9.58
^^^^^^^^^^^^^^

* PR #196 treats error 492 as a warning so that scanner results can still
  be used.

Version 0.9.57
^^^^^^^^^^^^^^

* PR #184, #185 and #186 add the new Ticker fields
  ``rtTradeVolume``, ``auctionVolume``, ``auctionPrice`` and
  ``auctionImbalance``.
* PR #191 lets ``util.schedule`` return a handle that can be canceled.
* PR #192 adds ``throttleStart`` and ``throttleEnd`` events to the ``Client``.
* PR #194 adds better JSON support for ``namedtuple`` objects.

Version 0.9.56
^^^^^^^^^^^^^^

* Fix bug #178: ``Order.totalQuantity`` is now float.

Version 0.9.55
^^^^^^^^^^^^^^

* Sphinx update for documentation.

Version 0.9.54
^^^^^^^^^^^^^^

* ``ContractDetails.stockType`` added.
* Fixed ``Trade.filled()`` for combo (BAG) contracts.
* Server version check added to make sure TWS/gateway version is at least 972.

Version 0.9.53
^^^^^^^^^^^^^^

* Fix bug #155 (IB.commissionReportEvent not firing).
* Help editors with the code completion for Events.

Version 0.9.52
^^^^^^^^^^^^^^

* Fix Client.exerciseOptions (bug #152).

Version 0.9.51
^^^^^^^^^^^^^^

* Fix ``ib.placeOrder`` for older TWS/gateway versions.
* Better handling of unclean disconnects.

Version 0.9.50
^^^^^^^^^^^^^^

* Fix ``execDetailsEvent`` regression.
* Added ``readonly`` argument to ``ib.connect`` method. Set this to ``True``
  when the API is in read-only mode.

Version 0.9.49
^^^^^^^^^^^^^^

* ``ib.reqCompletedOrders()`` request added (requires TWS/gateway >= 976).
  Completed orders are automatically synced on connect and are available from
  ``ib.trades()``, complete with fills and commission info.
* Fixed bug #144.

Version 0.9.48
^^^^^^^^^^^^^^

* ``Ticker.halted`` field added.
* ``Client.reqFundamentalData`` fixed.

Version 0.9.47
^^^^^^^^^^^^^^

* ``ibapi`` package from IB is no longer needed, ib_insync handles its own
  socket protocol encoding and decoding now.
* Documentation moved to `readthedocs <https://ib-insync.readthedocs.io>`_ as
  rawgit will cease operation later this year.
* Blocking requests will now raise ``ConnectionError`` on a connection failure.
  This also goes for ``util.run``, ``util.timeRange``, etc.

Version 0.9.46
^^^^^^^^^^^^^^

* ``Event`` class has been replaced with the one from
  `eventkit <https://github.com/erdewit/eventkit>`_.
* Event-driven bar construction from ticks added (via ``Ticker.updateEvent``)
* Fixed bug #136.
* Default request throttling is now 45 requests/s for compatibility with
  TWS/gateway 974 and higher.

Version 0.9.45
^^^^^^^^^^^^^^

* ``Event.merge()`` added.
* ``TagValue`` serialization fixed.

Version 0.9.44
^^^^^^^^^^^^^^

* ``Event.any()`` and ``Event.all()`` added.
* Ticker fields added: ``tradeCount``, ``tradeRate``, ``volumeRate``,
  ``avOptionVolume``, ``markPrice``, ``histVolatility``,
  ``impliedVolatility``, ``rtHistVolatility`` and ``indexFuturePremium``.
* Parse ``ticker.fundamentalRatios`` into ``FundamentalRatios`` object.
* ``util.timeRangeAsync()`` and ``waitUntilAsync()`` added.
* ``ib.pendingTickersEvent`` now emits a ``set`` of Tickers
  instead of a ``list``.
* Tick handling has been streamlined.
* For harvesting tick data, an imperative code style with a
  ``waitOnUpdate`` loop should not be used anymore!

Version 0.9.43
^^^^^^^^^^^^^^

* Fixed issue #132.
* ``Event.aiter()`` added, all events can now be used
  as asynchronous iterators.
* ``Event.wait()`` added, all events are now also awaitable.
* Decreased default throttling to 95 requests per 2 sec.

Version 0.9.42
^^^^^^^^^^^^^^

* ``Ticker.shortableShares`` added (for use with generic tick 236).
* ``ib.reqAllOpenOrders()`` request added.
* tickByTick subscription will update ticker's bid, ask, last, etc.
* Drop redundant bid/ask ticks from ``reqMktData``.
* Fixed occasional "Group name cannot be null" error message on connect.
* ``Watchdog`` code rewritten to not need ``util.patchAsyncio``.
* ``Watchdog.start()`` is no longer blocking.

Version 0.9.41
^^^^^^^^^^^^^^

* Fixed bug #117.
* Fixed order modifications with TWS/gateway 974.

Version 0.9.40
^^^^^^^^^^^^^^

* ``Ticker.fundamentalRatios`` added (for use with generic tick 258).
* Fixed ``reqHistoricalTicks`` with MIDPOINT.

Version 0.9.39
^^^^^^^^^^^^^^

* Handle partially filled dividend data.
* Use ``secType='WAR'`` for warrants.

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
* ``Client.setConnectOptions()`` added (for PACEAPI).

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
* ``IB.scannerDataEvent`` now emits the full list of ScanData.
* ``ScanDataList`` added.

Version 0.9.32
^^^^^^^^^^^^^^

* Autocompletion with Jedi plugin as used in Spyder and VS Code working again.

Version 0.9.31
^^^^^^^^^^^^^^

* Request results will return specialized contract types (like ``Stock``)
  instead of generic ``Contract``.
* ``IB.scannerDataEvent`` added.
* ``ContractDetails`` field ``summary`` renamed to ``contract``.
* ``isSmartDepth`` parameter added for ``reqMktDepth``.
* Event loop nesting is now handled by the
  `nest_asyncio project <https://github.com/erdewit/nest_asyncio>`_.
* ``util.useQt`` is rewritten so that it can be used with any asyncio
  event loop, with support for both PyQt5 and PySide2.
  It does not use quamash anymore.
* Various fixes, extensive documentation overhaul and
  flake8-compliant code formatting.

Version 0.9.30
^^^^^^^^^^^^^^

* ``Watchdog.stop()`` will not trigger restart now.
* Fixed bug #93.

Version 0.9.29
^^^^^^^^^^^^^^
* ``util.patchAsyncio()`` updated for Python 3.7.

Version 0.9.28
^^^^^^^^^^^^^^

* ``IB.RequestTimeout`` added.
* ``util.schedule()`` accepts tz-aware datetimes now.
* Let ``client.disconnect()`` complete when no event loop is running.

Version 0.9.27
^^^^^^^^^^^^^^

* Fixed bug #77.

Version 0.9.26
^^^^^^^^^^^^^^

* PR #74 merged (``ib.reqCurrentTime()`` method added).
* Fixed bug with order error handling.

Version 0.9.25
^^^^^^^^^^^^^^

* Default throttling rate now compatible with reqTickers.
* Fixed issue with ``ib.waitOnUpdate()`` in combination.
  with ``ib.pendingTickersEvent``.
* Added timeout parameter for ``ib.waitOnUpdate()``.

Version 0.9.24
^^^^^^^^^^^^^^

* ``ticker.futuresOpenInterest`` added.
* ``execution.time`` was string, is now parsed to UTC datetime.
* ``ib.reqMarketRule()`` request added.

Version 0.9.23
^^^^^^^^^^^^^^

* Compatability with Tornado 5 as used in new Jupyter notebook server.

Version 0.9.22
^^^^^^^^^^^^^^

* updated ``ib.reqNewsArticle`` and ``ib.reqHistoricalNews`` to ibapi v9.73.07.

Version 0.9.21
^^^^^^^^^^^^^^

* updated ``ib.reqTickByTickData()`` signature to ibapi v9.73.07 while keeping
  backward compatibility.

Version 0.9.20
^^^^^^^^^^^^^^

* Fixed watchdog bug.

Version 0.9.19
^^^^^^^^^^^^^^

* Don't overwrite ``exchange='SMART'`` in qualifyContracts.

Version 0.9.18
^^^^^^^^^^^^^^

* Merged PR #65 (Fix misnamed event).


Version 0.9.17
^^^^^^^^^^^^^^

* New IB events ``disconnectedEvent``, ``newOrderEvent``, ``orderModifyEvent``
  and ``cancelOrderEvent``.
* ``Watchdog`` improvements.


Version 0.9.16
^^^^^^^^^^^^^^

* New event system that will supersede ``IB.setCallback()``.
* Notebooks updated to use events.
* ``Watchdog`` must now be given an ``IB`` instance.

Version 0.9.15
^^^^^^^^^^^^^^

* Fixed bug in default order conditions.
* Fixed regression from v0.9.13 in ``placeOrder``.

Version 0.9.14
^^^^^^^^^^^^^^

* Fixed ``orderStatus`` callback regression.

Version 0.9.13
^^^^^^^^^^^^^^

* Log handling improvements.
* ``Client`` with ``clientId=0`` can now manage manual TWS orders.
* ``Client`` with master clientId can now monitor manual TWS orders.


Version 0.9.12
^^^^^^^^^^^^^^

* Run ``IBC`` and ``IBController`` directly instead of via shell.

Version 0.9.11
^^^^^^^^^^^^^^

* Fixed bug when collecting ticks using ``ib.waitOnUpdate()``.
* Added ``ContFuture`` class (continuous futures).
* Added ``Ticker.midpoint()``.

Version 0.9.10
^^^^^^^^^^^^^^

* ``ib.accountValues()`` fixed for use with multiple accounts.

Version 0.9.9
^^^^^^^^^^^^^

* Fixed issue #57

Version 0.9.8
^^^^^^^^^^^^^

* Fix for ``ib.reqPnLSingle()``.

Version 0.9.7
^^^^^^^^^^^^^

* Profit and Loss (PnL) funcionality added.

Version 0.9.6
^^^^^^^^^^^^^

* ``IBC`` added.
* PR #53 (delayed greeks) merged.
* ``Ticker.futuresOpenInterest`` field removed.

Version 0.9.5
^^^^^^^^^^^^^

* Fixed canceling bar and tick subscriptions.

Version 0.9.4
^^^^^^^^^^^^^

* Fixed issue #49.

Version 0.9.3
^^^^^^^^^^^^^

* ``Watchdog`` class added.
* ``ib.setTimeout()`` added.
* ``Ticker.dividends`` added for use with ``genericTickList`` 456.
* Errors and warnings will now log the contract they apply to.
* ``IB`` ``error()`` callback signature changed to include contract.
* Fix for issue #44.

Version 0.9.2
^^^^^^^^^^^^^

* Historical ticks and realtime bars now return time in UTC.

Version 0.9.1
^^^^^^^^^^^^^

* ``IBController`` added.
* ``openOrder`` callback added.
* default arguments for ``ib.connect()`` and ``ib.reqMktData()``.

Version 0.9.0
^^^^^^^^^^^^^

* minimum API version is v9.73.06.
* ``tickByTick`` support.
* automatic request throttling.
* ``ib.accountValues()`` now works for multiple accounts.
* ``AccountValue.modelCode`` added.
* ``Ticker.rtVolume`` added.

0.8
---

Version 0.8.17
^^^^^^^^^^^^^^

* workaround for IBAPI v9.73.06 for ``Contract.lastTradeDateOrContractMonth``
  format.

Version 0.8.16
^^^^^^^^^^^^^^

* ``util.tree()`` method added.
* ``error`` callback signature changed to
  ``(reqId, errorCode, errorString)``.
* ``accountValue`` and ``accountSummary`` callbacks added.

Version 0.8.15
^^^^^^^^^^^^^^

* ``util.useQt()`` fixed for use with Windows.

Version 0.8.14
^^^^^^^^^^^^^^

* Fix for ``ib.schedule()``.

Version 0.8.13
^^^^^^^^^^^^^^

* Import order conditions into ib_insync namespace.
* ``util.useQtAlt()`` added for using nested event loops on Windows with Qtl
* ``ib.schedule()`` added.

Version 0.8.12
^^^^^^^^^^^^^^

* Fixed conditional orders.

Version 0.8.11
^^^^^^^^^^^^^^

* ``FlexReport`` added.

Version 0.8.10
^^^^^^^^^^^^^^

* Fixed issue #22.

Version 0.8.9
^^^^^^^^^^^^^

* ``Ticker.vwap`` field added (for use with generic tick 233).
* Client with master clientId can now monitor orders and trades of
  other clients.

Version 0.8.8
^^^^^^^^^^^^^

* ``barUpdate`` event now used also for ``reqRealTimeBars`` responses
* ``reqRealTimeBars`` will return ``RealTimeBarList`` instead of list.
* realtime bars example added to bar data notebook.
* fixed event handling bug in ``Wrapper.execDetails``.

Version 0.8.7
^^^^^^^^^^^^^

* ``BarDataList`` now used with ``reqHistoricalData``; it also stores
  the request parameters.
* updated the typing annotations.
* added ``barUpdate`` event to ``IB``.
* bar- and tick-data notebooks updated to use callbacks for realtime data.

Version 0.8.6
^^^^^^^^^^^^^

* ``ticker.marketPrice`` adjusted to ignore price of -1.
* ``ticker.avVolume`` handling fixed.

Version 0.8.5
^^^^^^^^^^^^^

* ``realtimeBar`` wrapper fix.
* context manager for ``IB`` and ``IB.connect()``.

Version 0.8.4
^^^^^^^^^^^^^

* compatibility with upcoming ibapi changes.
* added ``error`` event to ``IB``.
* notebooks updated to use ``loopUntil``.
* small fixes and performance improvements.

Version 0.8.3
^^^^^^^^^^^^^

* new ``IB.reqHistoricalTicks()`` API method.
* new ``IB.loopUntil()`` method.
* fixed issues #4, #6, #7.

Version 0.8.2
^^^^^^^^^^^^^

* fixed swapped ``ticker.putOpenInterest`` vs ``ticker.callOpenInterest``.

Version 0.8.1
^^^^^^^^^^^^^

* fixed ``wrapper.tickSize`` regression.

Version 0.8.0
^^^^^^^^^^^^^

* support for realtime bars and ``keepUpToDate`` for historical bars
* added option greeks to ``Ticker``.
* new ``IB.waitUntil()`` and ``IB.timeRange()`` scheduling methods.
* notebooks no longer depend on PyQt5 for live updates.
* notebooks can be run in one go ('run all').
* tick handling bypasses ibapi decoder for more efficiency.

0.7
---

Version 0.7.3
^^^^^^^^^^^^^

* ``IB.whatIfOrder()`` added.
* Added detection and warning about common setup problems.

Version 0.7.2
^^^^^^^^^^^^^

* Removed import from ipykernel.

Version 0.7.1
^^^^^^^^^^^^^

* Removed dependencies for installing via pip.

Version 0.7.0
^^^^^^^^^^^^^

* added lots of request methods.
* order book (DOM) added.
* notebooks updated.

0.6
---

Version 0.6.1
^^^^^^^^^^^^^

* Added UTC timezone to some timestamps.
* Fixed issue #1.

Version 0.6.0
^^^^^^^^^^^^^

* Initial release.
