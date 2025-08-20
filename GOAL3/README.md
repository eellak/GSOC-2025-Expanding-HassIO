## New (Goal 3): Control-flow steps & REST

SmAuto now supports **step-based automations** with control-flow nodes and REST references.

### Overview
- A new optional block **`steps:`** can be added to an `Automation`.
- When **`steps:`** exists, the engine executes a **pipeline of steps** (in order).
- Legacy **`actions:`** remain supported and are **backwards compatible**:
  - With **`actions:`** only → values are **batched per entity** and published once.
  - With **`steps:`** → each `- entity.attr: value` inside steps is an **immediate step action** (no batching).

### Available Steps
- **Delay** — pause execution
- **Compute** — compute a numeric expression (entities + REST) and store the result in the step context
- **Switch** — branch to a list of steps based on **DSL `Condition`** cases

#### Syntax
```smauto
// Steps block
Automation <name>
    condition: (<Condition>)
    steps:
        Delay <Duration>
        Compute <id> = math(<expr>)
        Switch {
            case ( <Condition> ): <steps...>
            ...
            default: <steps...>
        }
    // other fields (freq, enabled, etc.)
end
```

- **Duration** supports: `500ms`, `2s`, `1.5`
- **Compute**
  - Stores the result to a **shared runtime context variable** named `<id>`
  - Expression `<expr>` supports numbers, `+ - * /`, parentheses, **numeric entity attributes**, and **REST numeric fields**
  - Grammar: `Compute <id> = math(<expr>)`
- **Switch**
  - `case` uses full **DSL `Condition`** (entities + REST)
  - Executes the first matching `case`, otherwise the `default` block (if present)

> Note: Case conditions are DSL Conditions. Values computed via `Compute` live in runtime context (e.g., `avg`) and are available to subsequent **step** evaluations; they are not yet part of the DSL condition grammar itself.

### REST in Conditions & Compute
- Reference REST data: `rest.<SourceName>.<field>`
- Usable anywhere a value is expected by the grammar:
  - In **Conditions** (e.g., `rest.Weather.temp >= 28`)
  - In **Compute** expressions (inside `math(...)`)

### Example
```smauto
Broker<MQTT> home_broker
    host: "localhost"
    port: 1883
end

Entity weather_station
    type: sensor
    topic: "porch.weather"
    broker: home_broker
    attributes:
        - temperature: float
end

Entity aircondition
    type: actuator
    topic: "bedroom.ac"
    broker: home_broker
    attributes:
        - mode: str
        - on: bool
        - fan: int
end

REST OpenWeather
    // exposes numeric field 'temp'
end

Automation cool_when_hot
    condition: ( weather_station.temperature > 28 )
    steps:
        Delay 500ms
        Compute avg = math( (weather_station.temperature + rest.OpenWeather.temp) / 2 )
        Switch {
            case ( weather_station.temperature >= 30 ):
                - aircondition.mode: "cool"
                - aircondition.on: true
                - aircondition.fan: 3
            case ( weather_station.temperature >= 28 ):
                - aircondition.mode: "fan"
                - aircondition.fan: 2
            default:
                - aircondition.on: false
        }
    freq: 1
    enabled: true
    continuous: true
end
```

### Quick Reference
- **Add steps:**  
  `steps:` inside `Automation`
- **Delay:**  
  `Delay 2s` | `Delay 500ms` | `Delay 1.25`
- **Compute (numeric):**  
  `Compute avg = math( (sensor.temp + rest.OpenWeather.temp) / 2 )`
- **Switch (DSL Condition cases):**
  ```smauto
  Switch {
      case ( rest.OpenWeather.temp >= 30 ):  - fan.speed: 3
      case ( rest.OpenWeather.temp >= 28 ):  - fan.speed: 2
      default:                               - fan.speed: 1
  }
  ```
- **Behavior:**  
  With `steps:` → actions publish immediately.  
  With `actions:` only → actions are batched per entity.
