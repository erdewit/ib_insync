|Group| |PyVersion| |Status| |PyPiVersion| |License| |Docs|

Introduction
============

The ``ib_insync`` package is build on top of the Python API
from Interactive Brokers. The objective is to make it as
easy as possible to use the API to its fullest extent.

The main features are:

* An ``IB`` component that automatically keeps in sync;
* An easy to use linear style of programming (no more callbacks);
* A fully asynchonous framework based on
  `asyncio <https://docs.python.org/3.6/library/asyncio.html>`_
  for advanced users;
* Interactive operation with live data in Jupyter notebooks.

Installation
------------

::

    pip3 install -U ib_insync

Requirements:

* Python_ version 3.6 or higher;
* The `Interactive Brokers Python API`_ version 9.73.03 or higher;
* A running TWS or IB gateway application (version 967 or higher).
  Make sure the
  `API port is enabled <https://interactivebrokers.github.io/tws-api/initial_setup.html>`_
  and 'Download open orders on connection' is checked.
  
To install packages needed for the examples and notebooks::

    pip3 install -U jupyter numpy pandas

Example
-------

This is a complete script to download historical data:

.. code-block:: python

    from ib_insync import *
      
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    
    contract = Forex('EURUSD')
    bars = ib.reqHistoricalData(contract, endDateTime='', durationStr='30 D',
            barSizeSetting='1 hour', whatToShow='MIDPOINT', useRTH=True)
    
    # convert to pandas dataframe:
    df = util.df(bars)
    print(df[['date', 'open', 'high', 'low', 'close']])
        
Output::
    
                       date      open      high       low     close
    0   2017-08-13 23:15:00  1.182850  1.183100  1.182100  1.182400
    1   2017-08-14 00:00:00  1.182400  1.182450  1.181875  1.182175
    2   2017-08-14 01:00:00  1.182175  1.182675  1.181900  1.182525
    ...
    719 2017-09-22 22:00:00  1.194425  1.195425  1.194225  1.195050


Be sure to take a look at the
`notebooks <http://rawgit.com/erdewit/ib_insync/master/docs/html/notebooks.html>`_
and the
`recipes <http://rawgit.com/erdewit/ib_insync/master/docs/html/recipes.html>`_
too.

Documentation
-------------

`API docs <http://rawgit.com/erdewit/ib_insync/master/docs/html/api.html>`_

Discussion
----------

The `insync user group <https://groups.io/g/insync>`_ is the place to discuss
IB-insync and anything related to it.

Disclaimer
----------

The software is provided on the conditions of the simplified BSD license.

This project is not affiliated with Interactive Brokers Group, Inc.'s.

Changelog
---------

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

Version 0.6.1
^^^^^^^^^^^^^

* Added UTC timezone to some timestamps
* Fixed issue #1

Version 0.6.0
^^^^^^^^^^^^^

* Initial release


Good luck and enjoy,

:author: Ewald de Wit <ewald.de.wit@gmail.com>

.. _Python: http://www.python.org
.. _`Interactive Brokers Python API`: http://interactivebrokers.github.io

.. |Group| image:: https://img.shields.io/badge/groups.io-insync-green.svg
   :alt: Join the user group
   :target: https://groups.io/g/insync

.. |PyPiVersion| image:: https://img.shields.io/pypi/v/ib_insync.svg
   :alt: PyPi
   :target: https://pypi.python.org/pypi/ib_insync

.. |PyVersion| image:: https://img.shields.io/badge/python-3.6+-blue.svg
   :alt:

.. |Status| image:: https://img.shields.io/badge/status-beta-green.svg
   :alt:

.. |License| image:: https://img.shields.io/badge/license-BSD-blue.svg
   :alt:
   
 .. |Docs| image:: https://readthedocs.org/projects/ib-insync/badge/?version=latest
   :alt: Documentation Status
   :target: http://ib-insync.readthedocs.io

