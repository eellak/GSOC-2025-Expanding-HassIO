def run_pipeline(aut):
    ctx = {}
    for s in aut.steps:
        s.run(ctx, aut)
    return ctx

def build_switch(entities, steps_runtime):
    # Build Switch using entities directly to avoid needing 'aut' during construction
    return steps_runtime["Switch"](
        cases=[
            ("ctx['avg'] >= 30", [
                steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 3),
                steps_runtime["Action"](entities["ac"].attributes_dict["power"], True),
            ]),
            ("avg >= 28", [
                steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 2),
            ]),
        ],
        default_steps=[
            steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 1),
        ],
    )

def test_switch_high_triggers_ac_and_fan3(auto_mod, entities, model_builder, automation_builder, steps_runtime):
    entities["sensor"].attributes_dict["temp"].value = 29.0
    model = model_builder(entities, rest_temp=31.0)  # avg=30
    aut = automation_builder(model, steps=[
        steps_runtime["Compute"]("avg", None),
        build_switch(entities, steps_runtime),
    ])
    ctx = run_pipeline(aut)
    assert abs(ctx["avg"] - 30.0) < 1e-9
    assert entities["fan"].publisher.sent[-1] == {"speed": 3}
    assert entities["ac"].publisher.sent[-1] == {"power": True}

def test_switch_mid_triggers_fan2(auto_mod, entities, model_builder, automation_builder, steps_runtime):
    entities["sensor"].attributes_dict["temp"].value = 29.0
    model = model_builder(entities, rest_temp=27.0)  # avg=28
    aut = automation_builder(model, steps=[
        steps_runtime["Compute"]("avg", None),
        build_switch(entities, steps_runtime),
    ])
    ctx = run_pipeline(aut)
    assert abs(ctx["avg"] - 28.0) < 1e-9
    assert entities["fan"].publisher.sent[-1] == {"speed": 2}
    assert not entities["ac"].publisher.sent or entities["ac"].publisher.sent[-1] != {"power": True}

def test_switch_default_when_no_case(auto_mod, entities, model_builder, automation_builder, steps_runtime):
    entities["sensor"].attributes_dict["temp"].value = 20.0
    model = model_builder(entities, rest_temp=22.0)  # avg=21
    aut = automation_builder(model, steps=[
        steps_runtime["Compute"]("avg", None),
        build_switch(entities, steps_runtime),
    ])
    ctx = run_pipeline(aut)
    assert abs(ctx["avg"] - 21.0) < 1e-9
    assert entities["fan"].publisher.sent[-1] == {"speed": 1}
