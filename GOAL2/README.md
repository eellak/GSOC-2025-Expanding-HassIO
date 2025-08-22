## REST Integration (Goal 2)

With **RESTSource** you can declare REST APIs directly in the model and use their data inside automation logic through `rest.<SourceName>.<field>`.

### Syntax

```smauto
RESTSource <Name>
    url: "https://api.example.com/v1/endpoint"
    method: GET | POST | PUT | DELETE
    headers: {"X-Api-Key": "KEY"}              # optional
    params:  {"q": "crete", "units": "metric"} # optional
    body:    {"foo": "bar"}                    # optional (dict or JSON string)
    auth:
        # one of:
        #   ApiKey(header, value)
        #   Bearer(token)
        #   Basic(username, password)
    poll: 60                                   # optional polling interval (sec)
    timeout: 10                                # optional request timeout (sec)
    map: {
        field1: "$.path.to.value"   | number,  # types: number|string|bool|list|dict
        field2: "$.arr[0].name"     | string
    }
end
```

> The `map` defines **named fields** using simple JSON paths (e.g. `$.a.b[0]`).  
> These fields are then available in conditions/expressions as `rest.<Source>.<field>`.

---

### Example (Open-Meteo)

```smauto
Metadata
    name: WeatherDemo
    version: "0.1.0"
end

RESTSource Weather
    url: "https://api.open-meteo.com/v1/forecast"
    method: GET
    params: {
        "latitude": 35.34,
        "longitude": 25.13,
        "hourly": "temperature_2m,wind_speed_10m",
        "forecast_hours": 1,
        "timezone": "auto"
    }
    poll: 10
    map: {
        temp: "$.hourly.temperature_2m[0]" | number,
        wind: "$.hourly.wind_speed_10m[0]" | number
    }
end
```

Usage in automation:

```smauto
Automation cool_when_hot
    condition:
        (rest.Weather.temp > 28)
    actions:
        - aircondition.on: true
        - aircondition.mode: "cool"
end
```

---

### Runtime Behavior

- **Warm-up fetch** at startup, so mapped fields have values immediately.
- **Polling loop** refreshes values every `poll` seconds.
- Values are stored in an in-memory store and can be accessed in expressions as `rest.<Source>.<field>`.

---

### Running the Demo

```bash
python scripts/run_rest_demo.py examples/weather_rest.smauto
# Example output:
# [Weather] {'temp': 21.3, 'wind': 6.5}
```

### Tests

```bash
pytest -q
# Includes:
# - tests/test_rest_mapping.py   (JSON-path & type casting)
# - tests/test_rest_client.py    (HTTP client behavior)
# - tests/test_rest_runtime.py   (poller updates the store)
```

---

### File Map

- **Grammar**
  - `smauto/grammar/rest.tx` – definition of `RESTSource`
  - `smauto/grammar/smauto.tx` – adds `restSources*=RESTSource` to the model
  - `smauto/grammar/condition.tx` – supports `rest.Source.field` in conditions
- **Backend**
  - `smauto/lib/rest_client.py` – async HTTP (httpx), auth, retries, DSL→native translation
  - `smauto/lib/rest_mapping.py` – JSON-path reader + type casting
  - `smauto/lib/rest_runtime.py` – warm-up + polling, in-memory value store
- **Demo/Tests**
  - `examples/weather_rest.smauto`, `scripts/run_rest_demo.py`
  - `tests/test_rest_*.py`

---

### Tips & Troubleshooting

- If you see `None` at first, wait for a polling cycle (or ensure warm-up is enabled—it is by default).
- Double-check JSON paths against the **actual API response**; for arrays use indices (e.g. `...temperature_2m[0]`).
- It is recommended to use a **virtualenv** for dependency installation (`httpx` is already included in `requirements.txt`).

