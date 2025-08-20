from typing import Any, Dict, List, Tuple, Optional
import re


def _split_path(p: str) -> List[str]:
    p = p.strip()
    if p.startswith("$."):
        p = p[2:]
    elif p.startswith("$"):
        p = p[1:]
    toks = []
    i = 0
    cur = ""
    while i < len(p):
        c = p[i]
        if c == ".":
            if cur:
                toks.append(cur)
                cur = ""
            i += 1
            continue
        if c == "[":
            if cur:
                toks.append(cur)
                cur = ""
            j = p.find("]", i)
            toks.append(p[i : j + 1])
            i = j + 1
            continue
        cur += c
        i += 1
    if cur:
        toks.append(cur)
    return toks


_idx_re = re.compile(r"\[(\d+)\]")


def _get(obj: Any, token: str) -> Any:
    if token.startswith("[") and token.endswith("]"):
        m = _idx_re.match(token)
        if not m:
            return None
        idx = int(m.group(1))
        if isinstance(obj, list) and 0 <= idx < len(obj):
            return obj[idx]
        return None
    if isinstance(obj, dict):
        return obj.get(token)
    return None


def json_path(path: str, obj: Any) -> Any:
    cur = obj
    for t in _split_path(path):
        cur = _get(cur, t)
        if cur is None:
            return None
    return cur


def _cast(v: Any, t: Optional[str]) -> Any:
    if t is None:
        return v
    if t == "number":
        try:
            return float(v)
        except Exception:
            return None
    if t == "string":
        return "" if v is None else str(v)
    if t == "bool":
        if isinstance(v, bool):
            return v
        if str(v).lower() in ("true", "1", "yes"):
            return True
        if str(v).lower() in ("false", "0", "no"):
            return False
        return None
    if t == "list":
        return v if isinstance(v, list) else None
    if t == "dict":
        return v if isinstance(v, dict) else None
    return v


def map_fields(source, raw_json: Any) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    for m in getattr(source, "mappings", []):
        val = json_path(m.jpath, raw_json)
        typ = getattr(m, "type", None)
        casted = _cast(val, typ)
        res[m.name] = casted
    return res
