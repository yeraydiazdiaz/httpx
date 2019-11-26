import asyncio
import contextvars

import httpx
import requests
from devtools import debug


URL = "https://httpbin.org/digest-auth/auth/yeray/{password}/MD5"


def just_one():
    password = "foo"
    auth = requests.auth.DigestAuth("yeray", password)
    debug(requests.get(URL.format(password=password), auth=auth))


if __name__ == "__main__":
    just_one()
