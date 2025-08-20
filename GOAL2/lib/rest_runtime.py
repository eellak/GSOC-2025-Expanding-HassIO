import asyncio
import time
from typing import Any, Dict, Tuple, Optional

from .rest_client import RestClient
from .rest_mapping import map_fields


class RestValueStore:
    def __init__(self):
        self._values: Dict[Tuple[str, str], Any] = {}
        self._stamp: Dict[Tuple[str, str], float] = {}

    def set(self, source_name: str, field: str, value: Any):
        k = (source_name, field)
        self._values[k] = value
        self._stamp[k] = time.time()

    def get(self, source_name: str, field: str) -> Any:
        return self._values.get((source_name, field))

    def age(self, source_name: str, field: str) -> Optional[float]:
        k = (source_name, field)
        if k not in self._stamp:
            return None
        return time.time() - self._stamp[k]


class RestPoller:
    def __init__(self, model, default_poll: int = 300):
        self.model = model
        self.client = RestClient()
        self.store = RestValueStore()
        self.default_poll = default_poll
        self._tasks = []
        self._stop = asyncio.Event()

    async def _run_source(self, source):
        interval = getattr(source, "poll", None) or self.default_poll
        while not self._stop.is_set():
            try:
                raw = await self.client.fetch(source)
                mapped = map_fields(source, raw)
                for k, v in mapped.items():
                    self.store.set(source.name, k, v)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    async def start(self):
        self._stop.clear()
        # warm-up: κάνε ένα άμεσο fetch για κάθε source ώστε να υπάρχουν τιμές από την αρχή
        for s in getattr(self.model, "restSources", []):
            try:
                raw = await self.client.fetch(s)
                mapped = map_fields(s, raw)
                for k, v in mapped.items():
                    self.store.set(s.name, k, v)
            except Exception:
                pass
        # ξεκίνα το περιοδικό polling
        self._tasks = [asyncio.create_task(self._run_source(s)) for s in getattr(self.model, "restSources", [])]

    async def stop(self):
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        self._tasks = []


_global_poller: Optional[RestPoller] = None


async def start_rest_runtime(model):
    global _global_poller
    _global_poller = RestPoller(model)
    await _global_poller.start()


async def stop_rest_runtime():
    global _global_poller
    if _global_poller:
        await _global_poller.stop()
        _global_poller = None


def get_rest_value(source_name: str, field: str):
    if not _global_poller:
        return None
    return _global_poller.store.get(source_name, field)
