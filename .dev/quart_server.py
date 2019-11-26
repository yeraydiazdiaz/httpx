"""
Running this on Mac causes a quick "Too many open files" exception

Use docker:
docker build . --tag aiofiles2
docker run -p 5000:5000 aiofiles2

On a different terminal:
python client.py <num_requests>
"""

import os
from random import randint
from typing import NamedTuple, Optional as Opt

import click
from quart import Quart, make_response, request

app = Quart(__name__)


class Config(NamedTuple):
    size: Opt[int]
    min: Opt[int]
    max: Opt[int]


def get_size():
    config = app.config["CONFIG"]
    if config.size:
        return config.size
    return randint(config.min, config.max)


@app.route("/", methods=["POST"])
async def post():
    data = await request.get_data()
    return {"size": len(data)}


@app.route("/", methods=["GET"])
async def index():
    size = get_size()
    payload = os.urandom(size)
    response = await make_response(payload)
    response.content_type = "application/octet-stream"
    response.content_length = size
    return response


@app.cli.command("run")
@click.option("--min", "min_", default=1, help="Minimum size of payload")
@click.option("--max", "max_", default=(1024 ** 2), help="Maximum size of payload")
@click.option(
    "--size", default=None, help="Fixed size, if set range min and max will be ignored"
)
@click.option("--uvloop/--no-uvloop", default=False)
def run(min_, max_, size, uvloop=False):
    if size:
        config = Config(size=size, min=None, max=None)
    else:
        config = Config(size=None, min=min_, max=max_)
    if uvloop:
        import uvloop

        uvloop.install()
    app.config["CONFIG"] = config
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    run()
