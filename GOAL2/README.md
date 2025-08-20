## REST Integration (Goal 2)

Με το **RESTSource** μπορείς να δηλώσεις REST APIs μέσα στο μοντέλο και να χρησιμοποιείς απευθείας τα δεδομένα τους στη λογική των automations μέσω `rest.<SourceName>.<field>`.

### Syntax

```smauto
RESTSource <Name>
    url: "https://api.example.com/v1/endpoint"
    method: GET | POST | PUT | DELETE
    headers: {"X-Api-Key": "KEY"}              # optional
    params:  {"q": "crete", "units": "metric"} # optional
    body:    {"foo": "bar"}                    # optional (dict ή JSON string)
    auth:
        # ένα από:
        #   ApiKey(header, value)
        #   Bearer(token)
        #   Basic(username, password)
    poll: 60                                   # προαιρετικό polling interval (sec)
    timeout: 10                                # προαιρετικό request timeout (sec)
    map: {
        field1: "$.path.to.value"   | number,  # types: number|string|bool|list|dict
        field2: "$.arr[0].name"     | string
    }
end
```

> Το `map` ορίζει **ονοματισμένα πεδία** με απλά JSON paths (π.χ. `$.a.b[0]`).  
> Αυτά τα πεδία είναι διαθέσιμα σε conditions/expressions ως `rest.<Source>.<field>`.

---

### Παράδειγμα (Open-Meteo)

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

Χρήση σε automation:

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

- **Warm-up fetch** στην εκκίνηση, ώστε τα mapped fields να έχουν άμεσα τιμές.
- **Polling loop** που ανανεώνει τις τιμές κάθε `poll` δευτερόλεπτα.
- Οι τιμές αποθηκεύονται σε in-memory store και είναι διαθέσιμες στην αξιολόγηση ως `rest.<Source>.<field>`.

---

### Running the Demo

```bash
python scripts/run_rest_demo.py examples/weather_rest.smauto
# Παράδειγμα εξόδου:
# [Weather] {'temp': 21.3, 'wind': 6.5}
```

### Tests

```bash
pytest -q
# Περιλαμβάνει:
# - tests/test_rest_mapping.py   (JSON-path & type casting)
# - tests/test_rest_client.py    (HTTP client behavior)
# - tests/test_rest_runtime.py   (poller ενημερώνει το store)
```

---

### File Map

- **Grammar**
  - `smauto/grammar/rest.tx` – ορισμός `RESTSource`
  - `smauto/grammar/smauto.tx` – προσθήκη `restSources*=RESTSource` στο μοντέλο
  - `smauto/grammar/condition.tx` – υποστήριξη `rest.Source.field` σε conditions
- **Backend**
  - `smauto/lib/rest_client.py` – async HTTP (httpx), auth, retries, μετατροπή DSL→native
  - `smauto/lib/rest_mapping.py` – JSON-path reader + type casting
  - `smauto/lib/rest_runtime.py` – warm-up + polling, in-memory value store
- **Demo/Tests**
  - `examples/weather_rest.smauto`, `scripts/run_rest_demo.py`
  - `tests/test_rest_*.py`

---

### Tips & Troubleshooting

- Αν στην αρχή δεις `None`, περίμενε έναν κύκλο polling (ή βεβαιώσου ότι το warm-up είναι ενεργό—είναι by default).
- Έλεγξε τα JSON paths πάνω στην **πραγματική** απόκριση του API· για arrays χρησιμοποίησε indices (π.χ. `...temperature_2m[0]`).
- Συνιστάται χρήση **virtualenv** για την εγκατάσταση εξαρτήσεων (`httpx` υπάρχει στο `requirements.txt`).
