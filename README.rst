|Group| |PyVersion| |Status| |PyPiVersion| |License|

Introduction
============

The ``ib_insync`` package is build on top of the Python API
from Interactive Brokers. The objective is to make it as
easy as possible to use the API, without sacrificing any
functionality.

The main features are:

* An ``IB`` component that automatically keeps its state
  in sync with the world;
* A sequential style of programming that is easy to understand 
  for novice users (no more callbacks);
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
* A running TWS or IB gateway application (version 963 or higher) with the 
  `API port enabled <https://interactivebrokers.github.io/tws-api/initial_setup.html>`_.
  
To install packages needed for the notebooks::

    pip3 install -U PyQt5 quamash jupyter numpy pandas

`IB-insync home page. <http://rawgit.com/erdewit/ib_insync/master/docs/html/index.html>`_

Example
-------

This is a complete script to download historical data:

.. code-block:: python

    from ib_insync import *

    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    bars = ib.reqHistoricalData(
            contract=Stock('TSLA', 'SMART', 'USD'),
            endDateTime='',
            durationStr='30 D',
            barSizeSetting='1 hour',
            whatToShow='TRADES',
            useRTH=True)

    print(bars)

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
   

