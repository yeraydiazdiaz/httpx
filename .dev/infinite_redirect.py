import asyncio

import httpx


async def success():
    url = "https://www.howsmyssl.com/a/check"  # Completes successfully
    cl = httpx.AsyncClient()
    resp = await cl.get(url)
    print("Success:", resp)


async def infinite():
    url = (
        "https://howsmyssl.com/a/check"
    )  # Sends a redirect to 'www.howsmyssl.com' but then errors?
    client = httpx.AsyncClient()
    resp = await client.get(url)
    print("Infinite:", resp)


async def main():
    coros = [infinite()]
    await asyncio.gather(*coros)


if __name__ == "__main__":
    asyncio.run(main())
