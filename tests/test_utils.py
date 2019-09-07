import logging
import os

import pytest

import httpx
from httpx import utils
from httpx.utils import get_netrc_login, guess_json_utf, parse_header_links


@pytest.mark.parametrize(
    "encoding",
    (
        "utf-32",
        "utf-8-sig",
        "utf-16",
        "utf-8",
        "utf-16-be",
        "utf-16-le",
        "utf-32-be",
        "utf-32-le",
    ),
)
def test_encoded(encoding):
    data = "{}".encode(encoding)
    assert guess_json_utf(data) == encoding


def test_bad_utf_like_encoding():
    assert guess_json_utf(b"\x00\x00\x00\x00") is None


@pytest.mark.parametrize(
    ("encoding", "expected"),
    (
        ("utf-16-be", "utf-16"),
        ("utf-16-le", "utf-16"),
        ("utf-32-be", "utf-32"),
        ("utf-32-le", "utf-32"),
    ),
)
def test_guess_by_bom(encoding, expected):
    data = "\ufeff{}".encode(encoding)
    assert guess_json_utf(data) == expected


def test_bad_get_netrc_login():
    assert get_netrc_login("url") is None

    os.environ["NETRC"] = "tests/.netrc"
    assert get_netrc_login("url") is None

    os.environ["NETRC"] = "wrongpath"
    assert get_netrc_login("url") is None

    from httpx import utils

    utils.NETRC_STATIC_FILES = ()
    os.environ["NETRC"] = ""
    assert utils.get_netrc_login("url") is None


def test_get_netrc_login():
    os.environ["NETRC"] = "tests/.netrc"
    assert get_netrc_login("netrcexample.org") == (
        "example-username",
        None,
        "example-password",
    )


@pytest.mark.parametrize(
    "value, expected",
    (
        (
            '<http:/.../front.jpeg>; rel=front; type="image/jpeg"',
            [{"url": "http:/.../front.jpeg", "rel": "front", "type": "image/jpeg"}],
        ),
        ("<http:/.../front.jpeg>", [{"url": "http:/.../front.jpeg"}]),
        ("<http:/.../front.jpeg>;", [{"url": "http:/.../front.jpeg"}]),
        (
            '<http:/.../front.jpeg>; type="image/jpeg",<http://.../back.jpeg>;',
            [
                {"url": "http:/.../front.jpeg", "type": "image/jpeg"},
                {"url": "http://.../back.jpeg"},
            ],
        ),
        ("", []),
    ),
)
def test_parse_header_links(value, expected):
    assert parse_header_links(value) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_debug", ["0", "1", "True", "False"])
async def test_httpx_debug_enabled_stderr_logging(server, capsys, httpx_debug):
    os.environ["HTTPX_DEBUG"] = httpx_debug

    # Force a reload on the logging handlers
    utils._LOGGER_INITIALIZED = False
    utils.get_logger("httpx")

    async with httpx.AsyncClient() as client:
        await client.get(server.url)

    if httpx_debug in ("1", "True"):
        assert "httpx.dispatch.connection_pool" in capsys.readouterr().err
    else:
        assert "httpx.dispatch.connection_pool" not in capsys.readouterr().err

    # Reset the logger so we don't have verbose output in all unit tests
    logging.getLogger("httpx").handlers = []


def test_lru_dict() -> None:
    d = utils.LRUDict(max_size=2)
    d["a"] = 1
    d["b"] = 2
    d["c"] = 3

    assert d == {"b": 2, "c": 3}


def test_lru_dict_initialized_with_keywords() -> None:
    d = utils.LRUDict(max_size=2, a=1, b=2)
    d["c"] = 3

    assert d == {"b": 2, "c": 3}


def test_lru_dict_initialized_with_iterable() -> None:
    d = utils.LRUDict(2, (("a", 1), ("b", 2)))
    d["c"] = 3

    assert d == {"b": 2, "c": 3}


def test_lru_dict_initialized_with_both() -> None:
    d = utils.LRUDict(2, [("a", 1)], b=2)
    d["c"] = 3

    assert d == {"b": 2, "c": 3}


def test_lru_dict_initialized_with_more_items_than_max_size_raises() -> None:
    with pytest.raises(ValueError):
        utils.LRUDict(1, a=1, b=2)


def test_default_lru_dict() -> None:
    d = utils.DefaultLRUDict(2, lambda: 0, [("a", 1)], b=2)
    assert d["c"] == 0

    assert d == {"b": 2, "c": 0}
