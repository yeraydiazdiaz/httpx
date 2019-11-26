# Notes related to HTTPX

## HTTP/2

Addresses problems with HTTP 1.1 like:

- It's not optimized for reusing TCP connections.
- Since webpages have increased in the number of single files to be downloaded this causes delays on the time to render.
- Latency is a big problem since the size of the files is small but there are many of them. Having to create multiple connections with a high latency increases the delay.
- HTTP pipelining (sending requests while waiting for other responses) is supposed to help but it has problems since it depends on the previous requests.

This limitations have produced common workarounds in the industry:

- Spriting, creating a big image containing smaller ones and cutting them via CSS. This transfers more data than is needed and invalidates the cache for all subelements unnecessarily.
- Inlining images in CSS which causes again caching problems.
- Concatenation of JavaScript files.
- Sharding, since HTTP 1.1 limited the number of connections to a host developers split the content in many different hosts to allow for a larger number of TCP connections. A side benefit is having the browser not send the cookie data for content-only requests.

### Concepts:

- HTTP2 uses the same schemas as HTTP 1.1, i.e. `http://` and `https://`.
- HTTP2 is practically TLS only, some CLI clients support clear text HTTP2 but all browsers require TLS.
- HTTP2 is negotiated through HTTP 1.1 using an `Upgrade` header which the server responds with `101 Switching`. This is called ALPN (Application Layer Protocol Negotiation) and it requires a round-trip but it was deemed worth the advantages since HTTP2 connections are typically held for longer times.
- HTTP2 is binary, which means requests can no longer be handcrafted in telnet and the use of a tool is necessary for debugging. This is less important in practice since it's all over TLS.
- HTTP2 frame format is:
    1. Length
    2. Type
    3. Flags
    4. Stream Identifier
    5. Frame payload
- The two most fundamental types are DATA and HEADERS which map to HTTP 1.1

### Streams

HTTP2 introduces the concept of streams. Streams are an independent, bi-directional sequence of frames exchanged between the server and the client through the same HTTP2 connection.

A single HTTP2 connection can contain multiple concurrent streams, interleaving frames from various streams in the same transport.

Streams can be established and used unilaterraly and closed by either endpoint.

The order of the frames within a stream is important as recipients will process them in order.

Streams have a priority or "weight" to allow the server to prioritize in high load situations. Additionally the PRIORITY frame allows a client to define dependencies between streams. These two techniques allow the creation of stream trees which browser can take advantage of to prioritise loading of elements in sections.

### Header compression

HTTP 1.1 requires sending headers repeatedly for related requests to a host. The increased size of the headers through cookie data is also a factor. HTTP2 introduces compression on headers.

The compression is done via HPACK, a compression format specific for HTTP2 headers.

### Reset

In HTTP 1.1 it is difficult to stop a request after a Content-Length has been sent without closing the TCP connection. HTTP2 introduces this with the RST_STREAM frame.

### Server push

In HTTP2 a server can preemptively send resources to the client by putting it in the cache so when requested it will be promptly served. The client must explicitly allow the server to do so and can always use RST_STREAM to abort.

### Flow control

Each HTTP2 stream has its own advertised flow window that the other end is allowed to send data for. Both ends have to tell the peer it has enough room to handle incoming data, the other end is only allowed to send that much data until the window is extended. Only DATA frames are flow controlled - all other frame types must be accepted.

The default flow-control window is 65K and it cannot be disabled.
