import asyncio
from json import loads
from multiprocessing.dummy import Pool
from os.path import exists
from random import choice
from sys import stderr

import aiofiles
import aiohttp
from aiohttp.client import ClientSession
from aiohttp_proxy import ProxyConnector
from eth_account import Account
from loguru import logger
from pyuseragents import random as random_useragent

logger.remove()
logger.add(stderr,
           format="<white>{time:HH:mm:ss}</white> | "
                  "<level>{level: <8}</level> | "
                  "<cyan>{line}</cyan> - "
                  "<white>{message}</white>")

headers = {
    'accept': '*/*',
    'accept-language': 'ru,en;q=0.9',
    'origin': 'https://debank.com',
    'referer': 'https://debank.com/',
    'source': 'web',
}


async def get_connector():
    if proxies:
        connector = ProxyConnector.from_url(choice(proxies))

    else:
        connector = None

    return connector


class App:
    @staticmethod
    async def get_usd_value(local_address: str,
                            session: ClientSession) -> int:
        while True:
            r = await session.get('https://api.debank.com/user/addr',
                                  params={'addr': local_address})

            if '<title>429 Too Many Requests</title>' in await r.text():
                continue

            if not loads(await r.text())['data'].get('usd_value'):
                usd_value = 0

            else:
                usd_value = loads(await r.text())['data']['usd_value']

            return usd_value

    async def get_wallet_price(self,
                               local_address: str,
                               original_data: str) -> None:
        async with aiohttp.ClientSession(headers={**headers,
                                                  'user-agent': random_useragent()},
                                         connector=await get_connector()) as session:
            usd_value = await self.get_usd_value(local_address=local_address.lower(),
                                                 session=session)
        if usd_value > 0:
            async with aiofiles.open('with_balance.txt', 'a', encoding='utf-8-sig') as f:
                await f.write(f'{original_data} | {usd_value}')
            logger.success(f'{original_data} | {usd_value} $')

        else:
            async with aiofiles.open('without_balance.txt', 'a', encoding='utf-8-sig') as f:
                await f.write(f'{original_data} | {usd_value}')
            logger.error(f'{original_data} | {usd_value} $')


def wrapper(current_data) -> None:
    asyncio.run(App().get_wallet_price(local_address=current_data,
                                       original_data=current_data))


if __name__ == '__main__':
    Account.enable_unaudited_hdwallet_features()

    with open('source.txt', 'r', encoding='utf-8-sig') as file:
        source_data = [row.strip() for row in file]

    if exists('proxies.txt'):
        with open('proxies.txt', 'r', encoding='utf-8-sig') as file:
            proxies = [row.strip() for row in file]

    else:
        proxies = None

    threads = int(input('Threads: '))
    print()

    with Pool(processes=threads) as executor:
        executor.map(wrapper, source_data)

    logger.success(f'Работа успешно завершена')
    print()