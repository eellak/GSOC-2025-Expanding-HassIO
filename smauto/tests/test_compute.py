def run_pipeline(aut):
    ctx = {}
    for s in aut.steps:
        s.run(ctx, aut)
    return ctx

def test_compute_sets_ctx_avg_high(entities, model_builder, automation_builder, steps_runtime):
    entities["sensor"].attributes_dict["temp"].value = 29.0
    model = model_builder(entities, rest_temp=31.0)  # avg=30
    aut = automation_builder(model, steps=[
        steps_runtime["Compute"]("avg", None),
    ])
    ctx = run_pipeline(aut)
    assert abs(ctx["avg"] - 30.0) < 1e-9

def test_compute_nested_then_use_in_actions(entities, model_builder, automation_builder, steps_runtime):
    entities["sensor"].attributes_dict["temp"].value = 27.0
    model = model_builder(entities, rest_temp=25.0)  # avg=26
    aut = automation_builder(model, steps=[
        steps_runtime["Compute"]("avg", None),
        steps_runtime["Action"](entities["fan"].attributes_dict["speed"], 1 if 26 < 28 else 2),
    ])
    ctx = run_pipeline(aut)
    assert abs(ctx["avg"] - 26.0) < 1e-9
    assert entities["fan"].publisher.sent[-1] == {"speed": 1}
