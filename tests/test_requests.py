import pytest

import ib_insync as ibi


@pytest.mark.asyncio
async def test_request_error_raised(ib):
    contract = ibi.Stock('MMM', 'SMART', 'USD')
    order = ibi.MarketOrder('BUY', 100)
    orderState = await ib.whatIfOrderAsync(contract, order)
    assert orderState.commission > 0

    ib.RaiseRequestErrors = True
    badContract = ibi.Stock('XXX')
    with pytest.raises(ibi.RequestError) as exc_info:
        await ib.whatIfOrderAsync(badContract, order)
    assert exc_info.value.code == 321
