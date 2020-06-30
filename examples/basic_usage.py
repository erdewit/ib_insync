"""
Basic symbol search and ticker streaming example.
"""
import traceback
import asyncio

import ib_insync as ibi


async def searchForContracts(ib, pattern):
    """Search for multiple symbols concurrently using ``asyncio`` tasks.
    """
    descriptions = await ib.reqMatchingSymbolsAsync(pattern)
    results = await asyncio.gather(
        *[
            ib.reqContractDetailsAsync(descr.contract)
            for descr in descriptions
        ]
    )
    return [cd.contract for cds in results for cd in cds]


async def main():
    """Entry point for our main ``asyncio`` task.
    """
    ib = ibi.IB()
    with await ib.connectAsync(clientId=2):

        # search for all contracts matching `SPY`
        contracts = await searchForContracts(ib, 'SPY')

        tickers = {}
        # request streaming market data for all matches
        for contract in contracts:
            tickers[contract.symbol] = ib.reqMktData(contract)

        # print quotes to console
        async for tickers in ib.pendingTickersEvent:
            print(tickers)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        traceback.print_exc()
