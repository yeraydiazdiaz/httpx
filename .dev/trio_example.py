# example.py
import trio
import httpx
from httpx.concurrency.trio import TrioBackend


async def main(url):
    async with httpx.AsyncClient(backend=TrioBackend()) as client:
        print(await client.get(url))


trio.run(main, "https://google.com")
