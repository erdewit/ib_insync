|Build| |Group| |PyVersion| |Status| |PyPiVersion| |CondaVersion| |License| |Downloads| |Docs|

Introduction
============

The goal of the IB-insync library is to make working with the
`Trader Workstation API <http://interactivebrokers.github.io/tws-api/>`_
from Interactive Brokers as easy as possible.

The main features are:

* An easy to use linear style of programming;
* An `IB component <https://ib-insync.readthedocs.io/api.html#module-ib_insync.ib>`_
  that automatically keeps in sync with the TWS or IB Gateway application;
* A fully asynchonous framework based on
  `asyncio <https://docs.python.org/3/library/asyncio.html>`_
  and
  `eventkit <https://github.com/erdewit/eventkit>`_
  for advanced users;
* Interactive operation with live data in Jupyter notebooks.

Be sure to take a look at the
`notebooks <https://ib-insync.readthedocs.io/notebooks.html>`_,
the `recipes <https://ib-insync.readthedocs.io/recipes.html>`_
and the `API docs <https://ib-insync.readthedocs.io/api.html>`_.


Installation
------------

::

    pip install ib_insync

For Python 3.6 install the ``dataclasses`` package as well
(newer Python versions already have it)::

    pip install dataclasses

Requirements:

* Python 3.6 or higher;
* A running TWS or IB Gateway application (version 972 or higher).
  Make sure the
  `API port is enabled <https://interactivebrokers.github.io/tws-api/initial_setup.html>`_
  and 'Download open orders on connection' is checked.

The ibapi package from IB is not needed.

Example
-------

This is a complete script to download historical data:

.. code-block:: python

    from ib_insync import *
    # util.startLoop()  # uncomment this line when in a notebook

    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    contract = Forex('EURUSD')
    bars = ib.reqHistoricalData(
        contract, endDateTime='', durationStr='30 D',
        barSizeSetting='1 hour', whatToShow='MIDPOINT', useRTH=True)

    # convert to pandas dataframe:
    df = util.df(bars)
    print(df)

Output::

                       date      open      high       low     close  volume  \
    0   2019-11-19 23:15:00  1.107875  1.108050  1.107725  1.107825      -1
    1   2019-11-20 00:00:00  1.107825  1.107925  1.107675  1.107825      -1
    2   2019-11-20 01:00:00  1.107825  1.107975  1.107675  1.107875      -1
    3   2019-11-20 02:00:00  1.107875  1.107975  1.107025  1.107225      -1
    4   2019-11-20 03:00:00  1.107225  1.107725  1.107025  1.107525      -1
    ..                  ...       ...       ...       ...       ...     ...
    705 2020-01-02 14:00:00  1.119325  1.119675  1.119075  1.119225      -1


Documentation
-------------

The complete `API documentation <https://ib-insync.readthedocs.io/api.html>`_.

`Changelog <https://ib-insync.readthedocs.io/changelog.html>`_.

Discussion
----------

The `insync user group <https://groups.io/g/insync>`_ is the place to discuss
IB-insync and anything related to it.

Consultancy & Development
-------------------------

IB-insync offers an easy entry into building automated trading systems
for both individual traders and fintech companies. However, to get the most out
of it is not a trivial matter and is beyond the reach of most developers.

If you need expert help, you can contact me. This can be for a small project,
such as fixing something in your own code, or it can be creating an entire new
trading infrastructure.
Please provide enough details so that I can assess both the feasibility and
the scope. Many folks worry about having to provide their 'secret sauce',
but that is never necessary (although you're perfectly welcome
to send that as well!)


Disclaimer
----------

The software is provided on the conditions of the simplified BSD license.

This project is not affiliated with Interactive Brokers Group, Inc.'s.

Good luck and enjoy,

:author: Ewald de Wit <ewald.de.wit@gmail.com>

.. _`Interactive Brokers Python API`: http://interactivebrokers.github.io

.. |Group| image:: https://img.shields.io/badge/groups.io-insync-green.svg
   :alt: Join the user group
   :target: https://groups.io/g/insync

.. |PyPiVersion| image:: https://img.shields.io/pypi/v/ib_insync.svg
   :alt: PyPi
   :target: https://pypi.python.org/pypi/ib_insync

.. |CondaVersion| image:: https://img.shields.io/conda/vn/conda-forge/ib-insync.svg
   :alt: Conda
   :target: https://anaconda.org/conda-forge/ib-insync

.. |PyVersion| image:: https://img.shields.io/badge/python-3.6+-blue.svg
   :alt:

.. |Status| image:: https://img.shields.io/badge/status-beta-green.svg
   :alt:

.. |License| image:: https://img.shields.io/badge/license-BSD-blue.svg
   :alt:

.. |Docs| image:: https://img.shields.io/badge/Documentation-green.svg
   :alt: Documentation
   :target: https://ib-insync.readthedocs.io/api.html

.. |Downloads| image:: https://pepy.tech/badge/ib-insync
   :alt: Number of downloads
   :target: https://pepy.tech/project/ib-insync

.. |Build| image:: https://github.com/erdewit/ib_insync/actions/workflows/test.yml/badge.svg?branch=master
   :target: https://github.com/erdewit/ib_insync/actions
