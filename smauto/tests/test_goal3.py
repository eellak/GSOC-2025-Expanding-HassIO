import smauto.lib.automation as auto

class FakePublisher:
    def __init__(self):
        self.sent = []
    def publish(self, message):
        self.sent.append(message)

class Attr:
    def __init__(self, parent, name, value=None):
        self.parent = parent
        self.name = name
        self.value = value

class Entity:
    def __init__(self, name):
        self.name = name
        self.publisher = FakePublisher()
        self.attributes_dict = {}

class ModelStub:
    def __init__(self, entities_dict, rest_sources):
        self.entities_dict = entities_dict
        self.restSources = rest_sources

class TrueCondition:
    def __init__(self, parent):
        self.parent = parent
        self.cond_lambda = "True"
    def build(self):
        self.cond_lambda = "True"
        return self.cond_lambda
    def evaluate(self):
        return True, "triggered"

class DemoAutomation(auto.Automation):
    def _eval_math(self, node, ctx):
        sensor_temp = float(self.parent.entities_dict["sensor"].attributes_dict["temp"].value)
        # Read REST directly from model to avoid depending on private helpers
        ow = next((rs for rs in self.parent.restSources if rs.name == "OpenWeather"), None)
        rest_temp = float((getattr(ow, "data", {}) or getattr(ow, "value", {}) or {}).get("temp", 0.0))
        return (sensor_temp + rest_temp) / 2.0

def build_demo_context(rest_temp: float, sensor_temp: float = 29.0):
    sensor = Entity("sensor")
    sensor.attributes_dict["temp"] = Attr(sensor, "temp", sensor_temp)
    fan = Entity("fan")
    fan.attributes_dict["speed"] = Attr(fan, "speed", 0)
    ac = Entity("ac")
    ac.attributes_dict["power"] = Attr(ac, "power", False)

    entities = {"sensor": sensor, "fan": fan, "ac": ac}
    rest_source = type("RS", (), {"name": "OpenWeather", "data": {"temp": rest_temp}})()
    model = ModelStub(entities, [rest_source])

    aut = DemoAutomation(
        parent=model,
        name="goal3_demo",
        condition=TrueCondition(None),
        actions=[],
        freq=1,
        enabled=True,
        continuous=True,
        checkOnce=True,
        delay=0.0,
        after=[],
        starts=[],
        stops=[],
        description="",
        steps=[],
    )

    DelayStepRt = getattr(auto.Automation, "DelayStepRt")
    ComputeStepRt = getattr(auto.Automation, "ComputeStepRt")
    StepActionRt = getattr(auto.Automation, "StepActionRt")
    SwitchStepRt = getattr(auto.Automation, "SwitchStepRt")

    steps = [
        DelayStepRt(0.05),
        ComputeStepRt("avg", None),
        SwitchStepRt(
            cases=[
                ("ctx['avg'] >= 30", [
                    StepActionRt(aut.parent.entities_dict["fan"].attributes_dict["speed"], 3),
                    StepActionRt(aut.parent.entities_dict["ac"].attributes_dict["power"], True),
                ]),
                ("ctx['avg'] >= 28", [
                    StepActionRt(aut.parent.entities_dict["fan"].attributes_dict["speed"], 2),
                ]),
            ],
            default_steps=[
                StepActionRt(aut.parent.entities_dict["fan"].attributes_dict["speed"], 1),
            ],
        ),
    ]
    return aut, steps, entities

def run_steps(aut, steps):
    ctx = {}  # simple dict works as ExecutionContext substitute
    for s in steps:
        s.run(ctx, aut)
    return ctx

def test_high_avg_triggers_ac_and_fan3():
    aut, steps, ents = build_demo_context(rest_temp=31.0, sensor_temp=29.0)  # avg = 30.0
    ctx = run_steps(aut, steps)
    assert abs(ctx["avg"] - 30.0) < 1e-9
    assert ents["fan"].publisher.sent[-1] == {"speed": 3}
    assert ents["ac"].publisher.sent[-1] == {"power": True}

def test_mid_avg_triggers_fan2_only():
    aut, steps, ents = build_demo_context(rest_temp=27.0, sensor_temp=29.0)  # avg = 28.0
    ctx = run_steps(aut, steps)
    assert abs(ctx["avg"] - 28.0) < 1e-9
    assert ents["fan"].publisher.sent[-1] == {"speed": 2}
    assert not ents["ac"].publisher.sent or ents["ac"].publisher.sent[-1] != {"power": True}

def test_low_avg_triggers_default_fan1():
    aut, steps, ents = build_demo_context(rest_temp=25.0, sensor_temp=27.0)  # avg = 26.0
    ctx = run_steps(aut, steps)
    assert abs(ctx["avg"] - 26.0) < 1e-9
    assert ents["fan"].publisher.sent[-1] == {"speed": 1}
    assert not ents["ac"].publisher.sent or ents["ac"].publisher.sent[-1] != {"power": True}
