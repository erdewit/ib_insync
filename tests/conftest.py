import asyncio

import pytest

import ib_insync as ibi


@pytest.fixture(scope='session')
def event_loop():
    loop = ibi.util.getLoop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
async def ib():
    ib = ibi.IB()
    await ib.connectAsync()
    yield ib
    ib.disconnect()
