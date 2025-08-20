import asyncio
import pytest
from smauto.lib.rest_runtime import RestPoller
from smauto.lib.rest_client import RestClient


class Mapping:
    def __init__(self, name, jpath, type=None):
        self.name = name
        self.jpath = jpath
        self.type = type


class FakeSource:
    def __init__(self):
        self.name = "Weather"
        self.url = "https://example.com/weather"
        self.method = "GET"
        self.headers = {}
        self.params = {}
        self.auth = None
        self.body = None
        self.timeout = None
        self.poll = 0.1
        self.mappings = [
            Mapping("temp", "$.t", "number"),
            Mapping("wind", "$.w", "number"),
        ]


@pytest.mark.asyncio
async def test_poller_updates_store(monkeypatch):
    async def fake_fetch(self, source):
        return {"t": 29.5, "w": 3.4}

    monkeypatch.setattr(RestClient, "fetch", fake_fetch)

    model = type("M", (), {"restSources": [FakeSource()]})
    poller = RestPoller(model, default_poll=0.1)
    await poller.start()
    try:
        await asyncio.sleep(0.25)
        assert poller.store.get("Weather", "temp") == 29.5
        assert poller.store.get("Weather", "wind") == 3.4
    finally:
        await poller.stop()
