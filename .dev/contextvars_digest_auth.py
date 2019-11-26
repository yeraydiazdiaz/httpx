import sys
import asyncio

import httpx
from devtools import debug

URL = "https://httpbin.org/digest-auth/auth/yeray/{password}/{algorithm}"

ALGORITHMS = [
    "MD5",
    "MD5-SESS",
    "SHA",
    "SHA-SESS",
    "SHA-256",
    "SHA-256-SESS",
    "SHA-512",
    "SHA-512-SESS",
]


async def main():
    password = "foo"
    client = httpx.AsyncClient(auth=httpx.DigestAuth("yeray", password))
    fs = [
        client.get(URL.format(password=password, algorithm=algorithm))
        for algorithm in ALGORITHMS
    ]
    responses = await asyncio.gather(*fs)
    for algorithm, response in zip(ALGORITHMS, responses):
        debug(algorithm, response)
        if response.status_code != 200:
            print("The above request FAILED!!")

    print("\nThis should fail...")
    debug(await client.get(URL.format(password="bar", algorithm=ALGORITHMS[0])))


async def just_one(algorithm=None):
    algorithm = algorithm or ALGORITHMS[0]
    client = httpx.AsyncClient()
    password = "foo"
    auth = httpx.DigestAuth("yeray", password)
    debug(
        algorithm,
        await client.get(URL.format(password=password, algorithm=algorithm), auth=auth),
    )


if __name__ == "__main__":
    try:
        if sys.argv[1] == "all":
            asyncio.run(main())
        else:
            idx = int(sys.argv[1])
            asyncio.run(just_one(ALGORITHMS[idx]))
    except (IndexError, ValueError):
        for algorithm in ALGORITHMS:
            asyncio.run(just_one(algorithm))
