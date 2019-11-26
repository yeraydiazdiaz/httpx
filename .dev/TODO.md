# httpx

- heavily supported by h11 and h2
- remember to use the scripts directory, particularly lint
- some http2 tests use a pytest fixture http server using uvicorn

Make sure things work in Linux using Docker containers: `docker run --rm -it -v`pwd`:/root/ python:3.6.5-stretch bash`

## Components

1. Client, handles cookies, redirects, proxies, etc
2. Dispatcher, handles connection creation, pooling, keepalive, etc

On a standard flow:

- Client is a sync version of AsyncClient, simply wrapping it with `run_until_complete`. It can be used as a context manager which calls `close` on exit.
  + A `Dispatch` implementer, usually a ConnectionPool is passed or created on init.
  + After creating and preparing a request `send` is called + Auth and potentially other pre-request features are handled and calls `send_handling_redirects`
  + `self.dispatch.send` is called with the request, ssl, and timeout
    * `ConnectionPool.aquire_connection` creates a `HTTPConnection` object which is also an implementer of Dispatch and uses a `ConcurrencyBackend` and a `HTTPXConnection` object which wrap `h11` or `h2` objects. Note a default kwarg parameter passed to `HTTPXConnection` is `release_func=self.release_connection`
    * `HTTPConnection.send` is called, if no `HTTPXConnections` exist `connection.connect` will be called, using the concurrency backend's `backend.connect` to create a `reader, writer, protocol` tuple and the hX connection as an instance variables, note the `HTTPXConnection` objects hold references to the reader and writer, there's also an `on_release` callback.
        * `connection.send` then proceeds to call the `HTTPXConnection.send` methods which create a `h11` or `h2` requests, and send events and data and recieve responses
            * `HTTPXConnection.send` will then create a `Response` object and if the request was not set to stream will close the response (which apparently does not release the connection itself), returning the response. *Note the response includes an `on_close` callback which by default calls `ConnectionPool.release_connection` as mentioned above.*
        * The `HTTPXConnection` object returns the response
    * The ConnectionPool returns the response, but if any errors occur the connection is removed from the lists
  - `Client.send_handling_redirects` takes the response and handles redirection by creating new requests and calling itself, eventually returning a response
- The API method returns the response and the user manipulates it
  + Note at this point the client's `dispatch` (ConnectionPool) has stored the connection referring to the response in in the pool, these are saved by origin in `keepalive` or `active` `ConnectionStore` objects.
  + Upon `ConnectionPool.release_connection`:
    * If the connection is closed, we discard it from the active connections
    * If there is no space in the pool we discard it and close it
    * Otherwise we move the connection from active to keepalive
  - This process happens for non-streaming responses, after the response is closed, which is after it's body is read deep in `HTTPXConnection.send`
- On Client context manager exit, the dispatch `ConnectionPool.close` is called.
  + ConnectionPool.close calls `HTTPConnection.close` on each stored connection
  + `HTTPConnection.close` calls `HTTPXConnection.close` for either one
  + `HTTPXConnection.close` created a `h11` or `h2` connection closed and closes the writer.

## ISSUES

- MitmProxy errors https://github.com/encode/httpx/issues/376
  + The OP is using `verify` on `client.get` which is not passed through to the dispatcher which only happens on `Client.init`.
  + Moving `verify` to init doesn't help

- Connection pooling doesn't quite work https://github.com/encode/httpx/issues/514
  + I've noticed this myself when doing some test for other stuff:
    1. The client creates a ConnectionPool for the backend
    2. The ConnectionPool creates ConnectionStore's for active and keep alive connections.
    3. It also creates a BoundedSemaphore `max_connections` object with a max limit of, by default 100
    4. Upon `send` the connection pool (remember it's a dispatch) acquires from `max_connection`
  + I think since the bounded semaphore is at 100 there will be 100 connections created before it blocks.
  + All 100 connections are created and placed in the `active_connections` ConnectionStores, all of them sharing the same origin
  + On further requests `pop_connection` returns the first connection
  + The solution would be to create a semaphore of 1 *per origin*.
  + TC commented that in H1 you do need multiple connections, but that's clearly not working
    * He also mentions you don't know if you're in H2 until _after_ the first connection is returned and established, at which time we can reuse the connection as we know it can be shared.

### DONE/CLOSED

- Mentioned in the README but not an issue - Digest authentication (https://tools.ietf.org/html/rfc7616)
  + Authentication is passed as a parameter to the client API `auth`
  + Testing done simply by returning the auth header and asserting it's correct
  + The flow is:
    * Client requests a protected resource
    * Server responds with a 401 with a `WWW-Authenticate` header with:
      - `type`: optional, in our case `Digest` but can also be Basic and others
      - `realm`: a string describing the site so the user can identify the credentials, usually the host but usually is in the form of `users@example.com`
      - `domain`: a space separated ilst of URIs defining the resources protected, usually the canonical domain
      - `opaque`: a string of data specified by the server that should be returned
      - `nonce`: a string refreshed on each 401 as a hash of the current time and a secret string. This string is used to recalculate the hash in the response to see if it matches the secret portion and authenticate. The actual generation and usage of the nonce is completely dependent on the server.
      - `qop`: a required string defining "the quality of protection", values are `auth` for authentication, and `auth-int` for authentication with integrity protection.
      - `algorithm`: an optional string indicating the algorithm, if not present MD5 is assumed. When used with Digest there will be a non-session variant and a session variant prefixed with `-sess`
      <!-- - `stale`: a flag indicating the previous request was refected because the nonce value was stale, indicating the client should retry the request with the new nonce. -->
    * Client retries the request adding a `Authorization` header including:
      - `username` as quoted plaintext or hashed if the `userhash` response parameter is true, if it includes characters not in the ABNF the `username*` must be used
      - `username*` username using extended notation https://tools.ietf.org/html/rfc5987
      - `userhash`: a flag indicating the username has been hashed as specified by the response
      - `realm` copied from the response
      - `uri` the effective request URI copied to allow proxies to change the request target
      - `qop` the quality of protection used, one of the alternatives defined by the server's response
      - `cnonce` an opaque string provided by the client and used by both the client and server for authentication and integrity.
      - `nc` an hex count of requests including the present one of the number of times a nonce has been sent, technically must be present but Firefox does not show it
    - Requests implements Digest by using thread locals to store the values for the servers auth challenges thus transparently handling the 401 response.
      + This will not work in asyncio, however it might be a good opportunity to use contextvars
    - The flow is quite different from that of Basic auth since we need the returned parameters from the response. It does mimic however the handling of the redirects:
      + In requests a `register_hook` is added to the request to process the response and handle redirects and 401s
      + In httpx the `request.send` method delegates to a `send_handling_redirects` which enters a redirection loop. This method is already fairly complicated and adding to it is a bit odd.

    - Implementation:
      + The design of auth classes has a `__call__` method which is instantiated with the user and password at the start of `send` and then called *only with the request*. This makes it really hard to adapt to Digest since it's dependent on the response.

    - TC suggested implementing this as a separate package but we'd need to tweak the architecture to be able to plug this neatly.

    - Rough design:
      + The Client needs a class to be able to plug middlewares
      + Middlewares should be able to modify the request before its sent and modify the response
      + If a request is needed after processing a response iterate with that request

    - After initial PR:
      + TC mentions correctly that it's a bit awkward to setup the middlewares per requests.
      + He also mentions having the middlewares be Dispatchers which is interesting though I worry the dispatch abstraction is doing too much:
        * The Dispatcher has three main methods: `request`, `send` and `close`, along context manager enter and exit, the latter calling `close`.
          - Does that fit our requirement? Probably though it means passing all the arguments to all the middlewares even though they probably don't use it, biggest example is redirection
          - `send` is the key, `request`'s purpose is to create the request itself, there's actually an implementation on the base class and none of the implementers actually override it.
          - On a redirection `send` would check for the history and call `send` on the "next dispatcher" that would need to be passed by argument, potentially breaking the Dispatcher constructor or `send` signature.
          - `send` returns a response which is convenient, if we need to create a new request we can do so using its own `request` method and call `send` again.
        * An option would be to derive the middlewares from the arguments to client, it currently builds the dispatch class out of ConnectionPool, A/WSGIDispatch and Threaded Dispatcher, optionally you can pass the instance of the dispatcher yourself.

    - Many moons later: The implementation in ready as a middleware, it works fine but there's an issue with the state. Digest auth expects the client to internally have a counter for each nonce value sent by the server.
      + In request they simply hold the last nonce value sent by the server, but I feel that's incorrect, there should be an internal count for *all* nonce values, however this can get unwieldy quickly as storing all possible nonce can take up a fair amount of memory.
      + How do we store know the auth failed? The flow is:
        * Client sends request with no auth header
        * Server returns 401 with new nonce
        * Client computes the auth header and sends it
        * Server returns 401 with a new nonce
      + The solution-ish is to keep track of the 401 responses and give up
      + Storing the nonce counters globally is a pain because the user can create a DigestAuth instance at any point. DigestAuth needs to be a class with a call, so I ended up making a class variable storing them.
    - There's a separate problem where the RFC states the client should preemptively send the same authorization header if present
      + The RFC says an authentication session (username, password, nonce, nonce count,
   and opaque values) is started upon sending the Authorization header for that "protection space" defined by the "domain" response header and should be active until the next 401 in that protection space.
      + We have no concept of session but we do have a global state, we could refactor so that an authorization header can be created from the session data


- h11 RemoteProtocolError bug (https://github.com/encode/httpx/issues/96)
  + Fairly obscure error around handling of keep-alive connections
  + The issue is that when the server closes the connection after a timeout httpx reads EOF and passes it to h11 which raises the RemoteProtocolError that is unhandled
  + The only real option is to catch the exception and reestablish the connection
  + As suggested by njsmith the best way is to check for the readability of the socket before reusing a connection. Learned quite a bit about socket connections in general and how asyncio works
  + MERGED-ish! (https://github.com/encode/httpx/pull/145)

- <https://github.com/encode/httpcore/issues/5> -- Check connection aliveness on acquiry from pool Aside: Probably a whole bunch of robustness testing would be good, for lost-connection cases in general.

  - Not sure what "connection aliveness" means, it can be simply checking `is_closed` on the connection
  - Googling it seems we can detect dropped connections by receiving (or sending?) data
  - How do we test the other side hanging up?

    - A server that accepts and disconnects? We'd need low level control over the socket which is in the HTTPConnection as reader, writer, even so I don't know how to model a disconnection

  - CLOSED via h11 RemoteProtocolError above

- <https://github.com/encode/http3/issues/74> -- Finesse `response.json`
  + Detect encoding from initial bytes, rather than just using "utf-8".
  + Allow additional arguments to `response.json()` and review any subtle API diffs to requests.
  + Analysis:
    * requests asserts there's content and it's > 3
    * if the response has an encoding, it delegates to `response.text` for decoding and passes it to `json.loads`
    * if there is no encoding, uses an util function `guess_json_utf` and uses it to decode and pass the content to `json` (aliased to complexjson from compat, not sure if this is applicable)
    * if the function returns None or attempting to decode the content raises UnicodeDecodeError, it falls back to passing `response.text` to `json.loads` and hope for the best?
      * It does mean there's a duplication of content detection
      * I guess this is to optimize the reading of a potentially large json content?
    * The workflow would be:
      1. Attempt decoding using the response's encoding, present in `response.charset_encoding`
      2. If response does not have encoding, guess it using `guess_json_utf` (which would need tests) and attempt to return that
      3. On UnicodeDecodeError fall back to 1
  + MERGED! https://github.com/encode/httpx/pull/116
- Bug when GET https://www.google.com
  + Seems to be triggered by a double closing of the connection which `del`s the connection twice in the connection pool.
  + Happens only on https
  + There's a readtimeout error as well that seems unrleated?
```
[13]   /Users/yeray/code/personal/_forks/httpcore/httpcore/client.py(349)send()
-> allow_redirects=allow_redirects,
[14]   /Users/yeray/code/personal/_forks/httpcore/httpcore/client.py(376)send_handling_redirects()
-> request, stream=stream, verify=verify, cert=cert, timeout=timeout
[15]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection_pool.py(120)send()
-> request, stream=stream, verify=verify, cert=cert, timeout=timeout
[16]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection.py(58)send()
-> request, stream=stream, timeout=timeout
[17]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/http2.py(74)send()
-> await response.close()
[18]   /Users/yeray/code/personal/_forks/httpcore/httpcore/models.py(733)close()
-> await self.on_close()
[19]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/http2.py(143)response_closed()
-> await self.on_release()
[20]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection_pool.py(160)release_connection()
-> self.active_connections.remove(connection)
[21] > /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection_pool.py(67)remove()
```
```
[13]   /Users/yeray/code/personal/_forks/httpcore/httpcore/client.py(349)send()
-> allow_redirects=allow_redirects,
[14]   /Users/yeray/code/personal/_forks/httpcore/httpcore/client.py(376)send_handling_redirects()
-> request, stream=stream, verify=verify, cert=cert, timeout=timeout
[15]   /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection_pool.py(123)send()
-> self.active_connections.remove(connection)
[16] > /Users/yeray/code/personal/_forks/httpcore/httpcore/dispatch/connection_pool.py(67)remove()
-> del self.all[connection]
```
  - Looks like google is sending back a 400 event, followed by a protocol error:
```
  <ResponseReceived stream_id:1, headers:[(b':status', b'400'), (b'content-type', b'text/html; charset=UTF-8'), (b'referrer-policy', b'no-referrer'), (b'content-length', b'1555'), (b'date', b'Sat, 25 May 2019 10:25:58 GMT')]>
  <StreamReset stream_id:1, error_code:ErrorCodes.PROTOCOL_ERROR, remote_reset:True>
```
 - `self.body_iter` returns StopIteration with the first ResponseReceived
  + TC fixed: apparently the user-agent needs to be defined... or something


- <https://github.com/encode/httpcore/issues/26> -- 100% test coverage:

  - httpcore/backends/default.py 81 6 93% 70, 84-85, 140-142

    - `write_no_block`
    - `asyncio.Timeout` draining the stream_writer

      - This is difficult because it's a timeout on writing to a local socket

    - `stream_writer.get_extra_info("ssl_object") is not None

      - Possibly requires https and thus self-signed cerificates for uvicorn?
      - Created a `https_server` fixture

  - httpcore/backends/sync.py 83 10 88% 42, 46, 76, 79-80, 157, 178, 223, 246, 269

    - 42, `protocol` was not being checked
    - 46, `headers` was not being checked
    - 76, `close` not called
    - 79-80, repr
    - 156, options, head, put, patch and delete

  - httpcore/client.py 50 7 86% 106, 128, 175, 199, 223, 253, 255

    - options, head, put, patch, delete
    - 253, ssl is not None (specified on the request call)
    - 255, timeout is not None (timeouts can be specified on the client or per request call)

  - httpcore/config.py 88 8 91% 64-67, 93-94, 97-100

    - 64-67, verify may be a path or a bool, if neither raises
    - 93-94, ca_bundle_path is a dir
    - 97-100, self.cert is not None, it can be an str or a tuple?

      - Single certificate raises SSLError with self-signed certs

  - httpcore/decoders.py 69 6 91% 56-57, 79-80, 106-107

    - all try..except on flush calls which I don't know how to simulate without mocking

      - I guess mock?

  - httpcore/dispatch/connection.py 60 4 93% 48, 72, 80, 91

    - 48, there's already an h2 connection and 72 protocol is H2... all of them are because H2

      - uvicorn does not support H2 :(

  - httpcore/dispatch/connection_pool.py 97 3 97% 78-80

    - `getitem` ???

      - ConnectionStore[connection] should return... the same connection if it's in all???

  - httpcore/dispatch/http11.py 78 4 95% 48, 74, 105-108

    - 48, http11 prepare_request is not called

      - This is a bit strange, H1, H2 and their higher level abstraction HTTPConnection all implement `prepare_request` the same way: calling request.prepare, I assume we want the higher level one to do it?

    - 74, if event is h11.InformationalResponse

      - I tried sending a 100 back but h11 fails with `h11._util.RemoteProtocolError: can't handle event type ConnectionClosed when role=SERVER and state=SEND_RESPONSE`

  - httpcore/dispatch/http2.py 96 2 98% 151, 155

    - 151 no more events and `on_release` is defined
    - 155, is_closed property, why is it always False?

  - +++ <https://github.com/encode/httpcore/pull/54> (WIP, I guess...)

    - Some of them are fine, others no-cover

  - httpcore/dispatch/http11.py 73 3 96% 69, 100-103

    - 69 informational response
    - 100-103: close with protocol error

  - httpcore/concurrency.py 90 3 97% 79, 93-94

    - 79 Writer.write_no_block
    - 93-94 stream_Writer.drain exception handling raising WriteTimeout

  - httpcore/dispatch/connection_pool.py 96 3 97% 78-80

    - 78-80 `ConnectionStore.__getitem__`

- <https://github.com/encode/httpcore/issues/14> -- Wait for connection close

  - Sync support for `raw()`, which allows the user to retrieve the body as a non-decoded binary
  - Should be a case of `await self._writer.wait_closed()` on `HTTP11Connection.close`, but TC is changing these files so best to delay it
  - <https://github.com/encode/httpcore/pull/21> -- MERGED!!

- <https://github.com/encode/httpcore/issues/10> -- Exceptions for decoding errors

  - The decoding is part of the Response class, `decoders.py` imports the 3rd party libs and defines SUPPORTED_DECODERS
  - <https://github.com/encode/httpcore/pull/20> -- MERGED!!!

- <https://github.com/encode/httpcore/issues/8> --Streaming requests/responses

  - `rq-async` uses h11+asyncio.open_connection for transport, but then uses urllib3 to create a response. `requests`:
  - `requests.Response.iter_lines` > `iter_content` which returns a generator from `raw` which is a `urllib3.HTTPResponse`
  - `urllib3.HTTPResponse.stream(chunk_size)` which calls `read` or `read_chunked` which reads from the file descriptor with some hardcore error checking and decoding
  - A possible way forward would be to expose an `async def iter_lines` on `async_requests.Response` which would perform the necessary steps for the async streamed download.
  - We should have our own Response subclass anyway since there are methods that call `.raw` that will fail. Most of `requests.Response` is convenience wrappers for set values like content, cookies, etc.
  - TC fixed this, turns out streaming responses are just responses whose body you read asynchronously initially no having a body. Streaming requests just means the body of the request is an async generator

- <https://github.com/encode/httpcore/issues/12> -- response.body is not binary, we shouldn't encode

  - It is actually a binary if you pass it in?
  - <https://github.com/encode/requests-async/pull/23> -- MERGED!

- <https://github.com/encode/httpcore/issues/9> -- request.next on allow_redirects=False

  - Request's `Response.next` property which reads `Response._next`
  - Which is populated on `Session.send` by calling `next(Session.resolve_redirects)` which:

    - Takes response and request
    - Solves the redirect target from the response into a URL
    - while there's a URL:

      - consumes the response
      - copies elements from the request onto a new one
      - calls `Session.send` with the URL and gets a response (or yields the new request, which is what happens if `allow_redirects` is False)
      - yields the response

  - <https://github.com/encode/requests-async/pull/22> -- MERGED!
