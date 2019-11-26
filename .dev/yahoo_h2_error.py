import asyncio
import logging
import sys

import httpx

logging.basicConfig(
    format="[%(levelname)s %(asctime)s] (%(name)s) %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger("httpx")
log.setLevel(logging.DEBUG)


async def do_request(url):
    cl = httpx.AsyncClient()
    resp = await cl.get(url)
    print("Success:", resp)


if __name__ == "__main__":
    try:
        url = sys.argv[1]
    except:
        url = "https://yahoo.com"

    asyncio.run(do_request(url))
