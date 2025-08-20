import time
from smauto.lib.automation import Automation, ExecutionContext

class FakePublisher:
    def __init__(self):
        self.sent = []
    def publish(self, message):
        self.sent.append(message)
        print(f"[publish] {message}")

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

class DemoAutomation(Automation):
    def _eval_math(self, node, ctx):
        sensor_temp = float(self.parent.entities_dict["sensor"].attributes_dict["temp"].value)
        rest_temp = float(self._get_rest_value("OpenWeather", "temp"))
        return (sensor_temp + rest_temp) / 2.0

def build_demo(rest_temp: float, sensor_temp: float):
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

    DelayStepRt = Automation.DelayStepRt
    ComputeStepRt = Automation.ComputeStepRt
    StepActionRt = Automation.StepActionRt
    SwitchStepRt = Automation.SwitchStepRt

    steps = [
        DelayStepRt(0.2),
        ComputeStepRt("avg", None),
        SwitchStepRt(
            cases=[
                ("ctx['avg'] >= 30", [
                    StepActionRt(model.entities_dict["fan"].attributes_dict["speed"], 3),
                    StepActionRt(model.entities_dict["ac"].attributes_dict["power"], True),
                ]),
                ("ctx['avg'] >= 28", [
                    StepActionRt(model.entities_dict["fan"].attributes_dict["speed"], 2),
                ]),
            ],
            default_steps=[
                StepActionRt(model.entities_dict["fan"].attributes_dict["speed"], 1),
            ],
        ),
    ]
    return aut, steps, entities

def run_once(aut, steps):
    ctx = ExecutionContext()
    for s in steps:
        s.run(ctx, aut)
    return ctx

if __name__ == "__main__":
    print("=== Scenario A: rest=31, sensor=29 -> avg=30 => fan=3, ac=true ===")
    aut, steps, ents = build_demo(rest_temp=31.0, sensor_temp=29.0)
    ctx = run_once(aut, steps)
    print(f"ctx: {dict(ctx)}")
    print(f"fan sent: {ents['fan'].publisher.sent}")
    print(f"ac sent: {ents['ac'].publisher.sent}")

    print("\n=== Scenario B: rest=27, sensor=29 -> avg=28 => fan=2 ===")
    aut, steps, ents = build_demo(rest_temp=27.0, sensor_temp=29.0)
    ctx = run_once(aut, steps)
    print(f"ctx: {dict(ctx)}")
    print(f"fan sent: {ents['fan'].publisher.sent}")
    print(f"ac sent: {ents['ac'].publisher.sent}")

    print("\n=== Scenario C: rest=25, sensor=27 -> avg=26 => fan=1 (default) ===")
    aut, steps, ents = build_demo(rest_temp=25.0, sensor_temp=27.0)
    ctx = run_once(aut, steps)
    print(f"ctx: {dict(ctx)}")
    print(f"fan sent: {ents['fan'].publisher.sent}")
    print(f"ac sent: {ents['ac'].publisher.sent}")
