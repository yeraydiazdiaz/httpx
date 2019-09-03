import hashlib
import os
import time
import typing
from base64 import b64encode

from ..exceptions import ProtocolError
from ..models import AsyncRequest, AsyncResponse, StatusCode
from ..utils import to_bytes, to_str
from .base import BaseMiddleware


class BasicAuthMiddleware(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        if isinstance(username, str):
            username = username.encode("latin1")

        if isinstance(password, str):
            password = password.encode("latin1")

        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()

        self.authorization_header = f"Basic {token}"

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.authorization_header
        return await get_response(request)


class CustomAuthMiddleware(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[AsyncRequest], AsyncRequest]):
        self.auth = auth

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request = self.auth(request)
        return await get_response(request)


class HTTPDigestAuthMiddleware(BaseMiddleware):

    ALGORITHM_TO_HASH_FUNCTION: typing.Dict[str, typing.Callable] = {
        "MD5": hashlib.md5,
        "MD5-SESS": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA-SESS": hashlib.sha1,
        "SHA-256": hashlib.sha256,
        "SHA-256-SESS": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA-512-SESS": hashlib.sha512,
    }

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = username
        self.password = password
        self._previous_nonce: typing.Optional[bytes] = None
        self._nonce_count = 0

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        response = await get_response(request)

        if self._should_return_digest_auth(response):
            request.headers["Authorization"] = self._build_auth_header(
                request, response
            )
            return await self(request, get_response)

        return response

    def _should_return_digest_auth(self, response: AsyncResponse) -> bool:
        auth_header = response.headers.get("www-authenticate")
        return StatusCode.is_client_error(response.status_code) and (
            auth_header is None or "digest" in auth_header.lower()
        )

    def _build_auth_header(self, request: AsyncRequest, response: AsyncResponse) -> str:
        # Retrieve challenge from response header
        header = response.headers.get("www-authenticate")
        assert header.lower().startswith("digest")
        challenge = DigestAuthChallenge.from_header_dict(self._parse_header(header))

        username = to_bytes(self.username)
        password = to_bytes(self.password)

        # Assemble parts depending on hash algorithms
        hash_func = self.ALGORITHM_TO_HASH_FUNCTION[challenge.algorithm]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode()

        A1 = b":".join((username, challenge.realm, password))
        HA1 = digest(A1)

        path = request.url.full_path.encode("utf-8")
        A2 = b":".join((request.method.encode(), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        # Construct Authenticate header string
        if challenge.nonce != self._previous_nonce:
            self._nonce_count = 1
        else:
            self._nonce_count += 1
        self._previous_nonce = challenge.nonce
        nc_value = b"%08x" % self._nonce_count

        s = str(self._nonce_count).encode()
        s += challenge.nonce
        s += time.ctime().encode()
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16].encode()
        if challenge.algorithm.lower().endswith("-sess"):
            A1 += b":".join((challenge.nonce, cnonce))

        if challenge.algorithm == "MD5-SESS":
            HA1 = digest(b":".join((HA1, challenge.nonce, cnonce)))

        qop = challenge.qop
        if not qop:
            to_key_digest = [HA1, challenge.nonce, HA2]
        elif qop == b"auth" or b"auth" in qop.split(b",") or b"auth" in qop.split(b" "):
            to_key_digest = [challenge.nonce, nc_value, cnonce, b"auth", HA2]
        elif qop == b"auth-int":
            raise NotImplementedError("Digest auth-int support is not yet implemented")
        else:
            raise ProtocolError('Unexpected qop value "{}" in digest auth'.format(qop))

        key_digest = b":".join(to_key_digest)

        format_args = {
            "username": username,
            "realm": challenge.realm,
            "nonce": challenge.nonce,
            "uri": path,
            "response": digest(b":".join((HA1, key_digest))),
            "algorithm": challenge.algorithm.encode(),
        }
        if challenge.opaque:
            format_args["opaque"] = challenge.opaque
        if qop:
            format_args["qop"] = b"auth"
            format_args["nc"] = nc_value
            format_args["cnonce"] = cnonce

        header_value = ", ".join(
            ['{}="{}"'.format(key, to_str(value)) for key, value in format_args.items()]
        )
        return "Digest " + header_value

    def _parse_header(self, header: str) -> dict:
        result = {}
        for item in header[7:].split(","):
            key, value = item.strip().split("=")
            value = value[1:-1] if value[0] == value[-1] == '"' else value
            result[key] = value

        return result


class DigestAuthChallenge:
    def __init__(
        self,
        realm: bytes,
        nonce: bytes,
        algorithm: str = None,
        opaque: typing.Optional[bytes] = None,
        qop: typing.Optional[bytes] = None,
    ) -> None:
        self.realm = realm
        self.nonce = nonce
        self.algorithm = algorithm or "MD5"
        self.opaque = opaque
        self.qop = qop

    @classmethod
    def from_header_dict(cls, header_dict: dict) -> "DigestAuthChallenge":
        realm = header_dict["realm"].encode()
        nonce = header_dict["nonce"].encode()
        qop = header_dict["qop"].encode() if "qop" in header_dict else None
        opaque = header_dict["opaque"].encode() if "opaque" in header_dict else None
        algorithm = header_dict.get("algorithm")
        return cls(
            realm=realm, nonce=nonce, qop=qop, opaque=opaque, algorithm=algorithm
        )
