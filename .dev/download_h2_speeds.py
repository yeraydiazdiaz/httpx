import httpx
import time
import requests
import logging

logging.basicConfig(
    format="[%(levelname)s %(asctime)s] (%(name)s) %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger("httpx")
log.setLevel(logging.DEBUG)


url = "https://quic.aiortc.org/50000000"

# start = time.time()
# r = requests.get(url)
# print("requests %.1f s" % (time.time() - start))

for http_version in ["HTTP/2"]:
    client = httpx.Client(http_versions=http_version)

    start = time.time()
    _ = client.get(url)
    print("httpx %s %.1f s" % (http_version, time.time() - start))
