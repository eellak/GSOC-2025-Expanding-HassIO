from smauto.lib.condition import Condition

class AutoStub:
    def __init__(self, model, name="test_auto"):
        self.parent = model
        self.name = name  # Needed for Condition.evaluate message formatting

class ModelStub:
    def __init__(self, entities_dict, rest_sources):
        self.entities_dict = entities_dict
        self.restSources = rest_sources

def test_condition_evaluate_uses_rests(entities):
    rs = type("RS", (), {"name": "OpenWeather", "data": {"temp": 29.5}})()
    model = ModelStub(entities, [rs])
    aut_stub = AutoStub(model)
    cond = Condition(parent=aut_stub)
    cond.cond_lambda = "rests['OpenWeather']['temp'] >= 28"
    ok, _ = cond.evaluate()
    assert ok

def test_condition_evaluate_false_branch(entities):
    rs = type("RS", (), {"name": "OpenWeather", "data": {"temp": 20.0}})()
    model = ModelStub(entities, [rs])
    aut_stub = AutoStub(model)
    cond = Condition(parent=aut_stub)
    cond.cond_lambda = "rests['OpenWeather']['temp'] >= 28"
    ok, _ = cond.evaluate()
    assert not ok
