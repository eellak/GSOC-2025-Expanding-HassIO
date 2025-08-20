import base64
import json
import asyncio
from typing import Any, Dict as TDict
import collections.abc as cabc
import httpx


def _seq_to_native(seq):
    seq = list(seq)
    if not seq:
        return []
    first = seq[0]
    if hasattr(first, "key") and hasattr(first, "value"):
        return {getattr(it, "key"): _to_native(getattr(it, "value")) for it in seq}
    if hasattr(first, "name") and hasattr(first, "value"):
        return {getattr(it, "name"): _to_native(getattr(it, "value")) for it in seq}
    return [_to_native(x) for x in seq]


def _to_native(v: Any) -> Any:
    if v is None or isinstance(v, (str, int, float, bool, bytes, bytearray)):
        return v

    items = getattr(v, "items", None)
    if isinstance(items, (list, tuple)):
        return _seq_to_native(items)

    values = getattr(v, "values", None)
    if isinstance(values, (list, tuple)):
        return _seq_to_native(values)

    # Κάποια textX αντικείμενα είναι iterable χωρίς να είναι list
    if isinstance(v, cabc.Mapping):
        return {k: _to_native(val) for k, val in v.items()}
    if isinstance(v, cabc.Sequence) and not isinstance(v, (str, bytes, bytearray)):
        return _seq_to_native(v)

    # Τελευταία προσπάθεια: αν έχει __iter__
    try:
        it = iter(v)
    except TypeError:
        return v
    else:
        return _seq_to_native(it)


class RestClient:
    def __init__(self, timeout: int = 10, max_retries: int = 3, backoff: float = 0.5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def _auth_headers(self, auth) -> TDict[str, str]:
        if auth is None:
            return {}
        t = type(auth).__name__
        if t == "RESTAuthNone":
            return {}
        if t == "RESTAuthApiKey":
            return {auth.header: auth.value}
        if t == "RESTAuthBearer":
            return {"Authorization": f"Bearer {auth.token}"}
        if t == "RESTAuthBasic":
            raw = f"{auth.username}:{auth.password}".encode("utf-8")
            return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}
        return {}

    async def fetch(self, source) -> TDict[str, Any]:
        url = source.url
        method = (getattr(source, "method", None) or "GET").upper()

        headers = _to_native(getattr(source, "headers", None)) or {}
        headers.update(self._auth_headers(getattr(source, "auth", None)))
        params = _to_native(getattr(source, "params", None)) or {}

        data = None
        json_body = None
        if hasattr(source, "body") and source.body is not None:
            body_native = _to_native(source.body)
            if isinstance(body_native, (dict, list)):
                json_body = body_native
            elif isinstance(body_native, (str, bytes, bytearray)):
                if isinstance(body_native, (bytes, bytearray)):
                    data = bytes(body_native)
                else:
                    try:
                        json_body = json.loads(body_native)
                    except Exception:
                        data = body_native.encode("utf-8")

        timeout = getattr(source, "timeout", None) or self.timeout
        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_body,
                        data=data,
                    )
                resp.raise_for_status()
                ctype = resp.headers.get("content-type", "")
                txt = resp.text or ""
                if "application/json" in ctype or txt.strip().startswith(("{", "[")):
                    return resp.json()
                return {"_raw": txt}
            except Exception:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                await asyncio.sleep(self.backoff * attempt)
