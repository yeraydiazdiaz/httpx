import asyncio

import httpx

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
        print("FAILED!" if response.status_code != 200 else "", algorithm, response)

    print("\nThis should fail...")
    print(await client.get(URL.format(password="bar", algorithm=ALGORITHMS[0])))


if __name__ == "__main__":
    asyncio.run(main())
