import httpcore
http = httpcore.SyncConnectionPool()
response = http.request(
    'GET', 'http://httpbin.org/stream-bytes/1024?chunk_size=8', stream=True,
    headers=[(b"Connection", b"close")])

buffer = b''
for data in response.raw():
    print(len(data), end=" ")
    buffer += data

print("\n", len(buffer))
