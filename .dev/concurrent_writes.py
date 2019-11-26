import asyncio
import os
import random
from typing import NamedTuple, Optional as Opt

import click
import httpx


class Config(NamedTuple):
    requests: Opt[int]
    min: Opt[int]
    max: Opt[int]


async def send_requests(config):
    requests = []
    async with httpx.AsyncClient(
            timeout=httpx.TimeoutConfig(timeout=60),
            base_url="http://localhost:5000/") as client:
        for _ in range(config.requests):
            requests.append(_send_to_server(client, config))

        results = await asyncio.gather(*requests)

    return results

async def _send_to_server(client, config):
    size = random.randint(config.min, config.max)
    payload = os.urandom(size)
    headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(size)
    }
    response = await client.post('/', headers=headers, data=payload)
    print(response.content)
    return response


@click.command()
@click.option("--min", "min_", default=1, help="Minimum size of payload")
@click.option("--max", "max_", default=(1024 ** 2), help="Maximum size of payload")
@click.option("--requests", default=1000, help="Number of requests")
def run(min_, max_, requests):
    config = Config(requests=requests, min=min_, max=max_)
    asyncio.run(send_requests(config))


if __name__ == "__main__":
    run()
