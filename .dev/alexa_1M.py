import asyncio
import logging
import sys
from pathlib import Path

import trio

import httpx
from httpx.concurrency.trio import TrioBackend

logging.basicConfig(
    format="[%(levelname)s %(asctime)s] (%(name)s) %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger("httpx")
log.setLevel(logging.DEBUG)


async def do_request(url: str) -> None:
    cl = httpx.AsyncClient()
    resp = await cl.get(url)
    print("Success:", resp)


async def do_trio_request(url: str) -> None:
    async with httpx.AsyncClient(backend=TrioBackend()) as client:
        resp = await client.get(url)
        print("Success:", resp)


def do_run(backend, url):
    if backend == "asyncio":
        asyncio.run(do_request(url))
    else:
        trio.run(do_trio_request, url)


if __name__ == "__main__":
    limit = 1_000
    try:
        limit = int(sys.argv[1])
    except:
        pass

    backend = "asyncio"
    try:
        backend = sys.argv[2]
    except:
        pass

    print(f"Limiting to {limit} requests...")

    with open(Path(__file__).parent / "alexa-1m.txt") as fd:
        for i, url in enumerate(fd.readlines(), 1):
            url = url.strip()
            if input(f"\n\nAbout to fetch {url}, is that ok? [Y/n]: ").lower() in (
                "n",
                "no",
            ):
                break
            try:
                do_run(backend, url)
            except httpx.exceptions.HTTPError as e:
                log.exception(e)
                print("\n\n\n ERROR \n\n\n")
                pass

            if i == limit:
                break
