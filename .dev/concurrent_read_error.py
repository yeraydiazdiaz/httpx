import asyncio
import httpx

request_count = 0


async def print_content_from_url(url, client):
    global request_count
    res = await client.get(url)
    request_count += 1
    print(res, url, request_count)


async def main():
    urls = ["https://example.com", "https://google.com"] * 100
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(print_content_from_url(url, client) for url in urls))


asyncio.run(main())
