import asyncio

import httpx


async def auth():
    url = "https://httpbin.org/basic-auth/foo/bar"
    cl = httpx.AsyncClient()
    resp = await cl.get(url, auth=("foo", "bar"))
    print("Basic auth:", resp)


async def redirect():
    url = "https://httpbin.org/redirect-to?url=https://news.ycombinator.com"
    cl = httpx.AsyncClient()
    resp = await cl.get(url)
    print("Redirect:", resp)


# async def digest():
#     url = "https://httpbin.org/digest-auth/auth/yeray/{password}/SHA-256"
#     client = httpx.AsyncClient()
#     password = "foo"
#     auth = httpx.DigestAuth("yeray", password)
#     resp = await client.get(url.format(password=password), auth=auth)
#     print("Digest:", resp)


async def main():
    coros = [
        auth(),
        redirect(),
        # digest(),
    ]
    await asyncio.gather(*coros)


if __name__ == "__main__":
    asyncio.run(main())
