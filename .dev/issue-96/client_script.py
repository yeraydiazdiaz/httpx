import asyncio
import sys

import httpx

http_client = httpx.AsyncClient()


async def request(port, client=None):
    print("Performing request")
    cl = client or http_client
    resp = await cl.get(f"http://localhost:{port}")
    if resp.status_code != 200:
        raise Exception("Unexpected non-200 response")
    print("Got response", resp.content, "\n")
    await resp.close()


async def main2(port, timeout=5):
    # Closing the connections works fine
    async with httpx.AsyncClient() as c:
        await request(port, c)
    await asyncio.sleep(timeout)
    async with httpx.AsyncClient() as c:
        await request(port, c)


async def main(port, timeout=2):
    await request(port)

    conn = list(http_client.dispatch.keepalive_connections.all.keys())[0]
    print(conn.h11_connection.h11_state.our_state)
    print(conn.h11_connection.h11_state.their_state)
    if timeout is not None:
        print(f"Waiting {timeout} seconds...")
        await asyncio.sleep(timeout)
    await request(port)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify a port number to connect to")
    else:
        port = sys.argv[1]
        timeout = None if len(sys.argv) < 3 else int(sys.argv[2])
        asyncio.run(main(port, timeout), debug=True)
