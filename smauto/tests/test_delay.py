import smauto.lib.automation as auto

def test_delay_calls_sleep(monkeypatch, entities, model_builder, automation_builder, steps_runtime):
    calls = []
    def fake_sleep(s):
        calls.append(s)
    monkeypatch.setattr(auto.time, "sleep", fake_sleep)

    model = model_builder(entities, rest_temp=30.0)
    aut = automation_builder(model, steps=[
        steps_runtime["Delay"](0.5),
        steps_runtime["Delay"](0.05),
    ])

    ctx = {}
    for s in aut.steps:
        s.run(ctx, aut)

    assert calls == [0.5, 0.05]
    assert entities["fan"].publisher.sent == []
    assert entities["ac"].publisher.sent == []
