import smauto.lib.automation as auto
import pytest

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
    def __init__(self, parent=None):
        self.parent = parent
        self.cond_lambda = "True"
    def build(self):
        self.cond_lambda = "True"
        return self.cond_lambda
    def evaluate(self):
        return True, "triggered"

class DemoAutomation(auto.Automation):
    # Compute avg of entity sensor.temp and REST OpenWeather.temp
    def _eval_math(self, node, ctx):
        sensor_temp = float(self.parent.entities_dict["sensor"].attributes_dict["temp"].value)
        ow = next((rs for rs in self.parent.restSources if rs.name == "OpenWeather"), None)
        rest_temp = float((getattr(ow, "data", {}) or getattr(ow, "value", {}) or {}).get("temp", 0.0))
        return (sensor_temp + rest_temp) / 2.0

@pytest.fixture
def auto_mod():
    return auto

@pytest.fixture
def entities():
    sensor = Entity("sensor")
    sensor.attributes_dict["temp"] = Attr(sensor, "temp", 0.0)

    fan = Entity("fan")
    fan.attributes_dict["speed"] = Attr(fan, "speed", 0)

    ac = Entity("ac")
    ac.attributes_dict["power"] = Attr(ac, "power", False)

    return {"sensor": sensor, "fan": fan, "ac": ac}

@pytest.fixture
def model_builder():
    def _build(entities, rest_temp):
        rs = type("RS", (), {"name": "OpenWeather", "data": {"temp": rest_temp}})()
        return ModelStub(entities, [rs])
    return _build

@pytest.fixture
def automation_builder():
    def _build(model, steps=None, actions=None, cls=DemoAutomation):
        return cls(
            parent=model,
            name="goal3_test",
            condition=TrueCondition(None),
            actions=actions or [],
            freq=1,
            enabled=True,
            continuous=True,
            checkOnce=True,
            delay=0.0,
            after=[],
            starts=[],
            stops=[],
            description="",
            steps=steps or [],
        )
    return _build

@pytest.fixture
def steps_runtime(auto_mod):
    return {
        "Delay": getattr(auto_mod.Automation, "DelayStepRt"),
        "Compute": getattr(auto_mod.Automation, "ComputeStepRt"),
        "Action": getattr(auto_mod.Automation, "StepActionRt"),
        "Switch": getattr(auto_mod.Automation, "SwitchStepRt"),
    }
