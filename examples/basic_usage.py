"""
Basic symbol search and ticker streaming example.
"""
import asyncio
import time
import traceback

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

        start = time.time()

        # search for all contracts matching `SPY`
        contracts = await searchForContracts(ib, 'SPY')

        print(f"Found contracts in {time.time() - start}:\n{contracts}")

        # request streaming market data for first contract
        for contract in contracts:
            if contract.primaryExchange == 'ARCA':
                break

        ib.reqMktData(contract)

        count = 0
        # print quotes to console
        async for tickers in ib.pendingTickersEvent:
            print(tickers)
            count += 1
            if count > 2:
                break


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        traceback.print_exc()
