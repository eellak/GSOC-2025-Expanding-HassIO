import httpx
import pytest
from smauto.lib.rest_client import RestClient


class DummyAsyncClient:
    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, headers=None, params=None, json=None, data=None):
        req = httpx.Request(method, url, headers=headers, params=params)
        if "text" in url:
            return httpx.Response(
                200,
                text="hello",
                headers={"content-type": "text/plain"},
                request=req,
            )
        return httpx.Response(
            200,
            json={"foo": "bar"},
            headers={"content-type": "application/json"},
            request=req,
        )


@pytest.mark.asyncio
async def test_fetch_json(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    class Src:
        url = "https://example.com/json"
        method = "GET"
        headers = {}
        params = {}
        auth = None
        body = None
        timeout = None

    rc = RestClient()
    data = await rc.fetch(Src)
    assert data == {"foo": "bar"}


@pytest.mark.asyncio
async def test_fetch_text(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    class Src:
        url = "https://example.com/text"
        method = "GET"
        headers = {}
        params = {}
        auth = None
        body = None
        timeout = None

    rc = RestClient()
    data = await rc.fetch(Src)
    assert data == {"_raw": "hello"}
