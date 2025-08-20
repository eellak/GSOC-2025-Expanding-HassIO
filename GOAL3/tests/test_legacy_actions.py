import smauto.lib.automation as auto

class DummyAction(auto.Action):
    def __init__(self, attribute, value):
        # parent not used by trigger_actions
        super().__init__(parent=None, attribute=attribute, value=value)

def test_legacy_actions_batching(entities, model_builder, automation_builder):
    model = model_builder(entities, rest_temp=30.0)
    actions = [
        DummyAction(entities["fan"].attributes_dict["speed"], 2),
        DummyAction(entities["fan"].attributes_dict["speed"], 3),  # same entity, same attr -> last wins in publish dict
        DummyAction(entities["ac"].attributes_dict["power"], True),
    ]
    aut = automation_builder(model, steps=[], actions=actions)
    aut.trigger_actions()

    # fan receives one combined message with latest value 3
    assert entities["fan"].publisher.sent[-1] == {"speed": 3}
    # ac receives its own message
    assert entities["ac"].publisher.sent[-1] == {"power": True}

def test_steps_do_not_use_legacy_batching(entities, model_builder, automation_builder, steps_runtime):
    model = model_builder(entities, rest_temp=30.0)
    steps = [
        steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 1),
        steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 2),
    ]
    aut = automation_builder(model, steps=steps, actions=[])
    ctx = {}
    for s in aut.steps:
        s.run(ctx, aut)

    # two separate publishes in order
    assert entities["fan"].publisher.sent[0] == {"speed": 1}
    assert entities["fan"].publisher.sent[1] == {"speed": 2}
