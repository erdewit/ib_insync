|Group| |PyVersion| |Status| |PyPiVersion| |License|

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

`IB-insync home page. <http://rawgit.com/erdewit/ib_insync/master/docs/html/index.html>`_

Example
-------

This is a complete script to download historical data:

.. code-block:: python

    from ib_insync import *
      
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    
    contract = Stock('AMD', 'SMART', 'USD')
    bars = ib.reqHistoricalData(contract, endDateTime='', durationStr='30 D',
            barSizeSetting='1 hour', whatToShow='TRADES', useRTH=True)
    
    # convert to pandas dataframe:
    df = util.df(bars)
    print(df)
    
Output::

                       date   open   high    low  close  volume  barCount  average
    0   2017-06-23 15:30:00  14.14  14.35  13.90  14.24  190461     31287   14.187
    1   2017-06-23 16:00:00  14.23  14.65  14.16  14.62  266730     41320   14.461
    ...
    206 2017-08-04 21:00:00  13.13  13.15  13.08  13.12   88656     21886   13.113


Be sure to take a look at the
`example notebooks <http://rawgit.com/erdewit/ib_insync/master/docs/html/notebooks.html>`_ too.

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
   

