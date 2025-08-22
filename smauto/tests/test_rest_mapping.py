from smauto.lib.rest_mapping import json_path, map_fields


class Mapping:
    def __init__(self, name, jpath, type=None):
        self.name = name
        self.jpath = jpath
        self.type = type


def test_json_path_basic():
    obj = {"a": {"b": [10, {"c": 42}]}}
    assert json_path("$.a.b[0]", obj) == 10
    assert json_path("$.a.b[1].c", obj) == 42
    assert json_path("$.x.y", obj) is None


def test_map_fields_casting():
    raw = {"current": {"temperature": "21.5", "ok": "true"}}
    src = type(
        "S",
        (),
        {
            "mappings": [
                Mapping("temp", "$.current.temperature", "number"),
                Mapping("flag", "$.current.ok", "bool"),
                Mapping("missing", "$.current.missing", "string"),
            ]
        },
    )
    mapped = map_fields(src, raw)
    assert mapped["temp"] == 21.5
    assert mapped["flag"] is True
    assert mapped["missing"] is None or mapped["missing"] == ""
