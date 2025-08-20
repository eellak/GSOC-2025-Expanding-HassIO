from textx import textx_isinstance, get_metamodel
import time
import math
from rich import print, pretty
from concurrent.futures import ThreadPoolExecutor
from smauto.lib.types import List, Dict

pretty.install()


class AutomationState:
    IDLE = 0
    RUNNING = 1
    EXITED_SUCCESS = 2
    EXITED_FAILURE = 3


class ExecutionContext(dict):
    """Holds intermediate values for Compute steps."""
    pass


class Automation(object):
    def __init__(
        self,
        parent,
        name,
        condition,
        actions,
        freq,
        enabled,
        continuous,
        checkOnce,
        delay,
        after,
        starts,
        stops,
        description="",
        steps=None,
    ):
        enabled = True if enabled is None else enabled
        continuous = True if continuous is None else continuous
        checkOnce = False if checkOnce is None else checkOnce
        freq = 1 if freq in (None, 0) else freq
        delay = 0 if not delay else delay
        self.parent = parent
        self.name = name
        self.condition = condition
        self.enabled = enabled
        self.continuous = continuous
        self.checkOnce = checkOnce
        self.freq = freq
        self.actions = actions
        self.steps = steps or []
        self.after = after
        self.starts = starts
        self.stops = stops
        self.time_between_activations = 5
        self.state = AutomationState.IDLE
        self.description = description
        self.delay = delay
        self._rests_cache = None

    def evaluate_condition(self):
        if self.enabled:
            return self.condition.evaluate()
        else:
            return False, f"{self.name}: Automation disabled."

    def trigger_actions(self):
        """Legacy batch action execution (kept for backward compatibility)."""
        if not self.continuous:
            self.enabled = False
        messages = {}
        for action in self.actions:
            value = action.value
            if type(value) is Dict:
                value = value.to_dict()
            elif type(value) is List:
                value = value.print_item(value)
            if action.attribute.parent in messages.keys():
                messages[action.attribute.parent].update({action.attribute.name: value})
            else:
                messages[action.attribute.parent] = {action.attribute.name: value}
        for entity, message in messages.items():
            entity.publisher.publish(message)

    def build_condition(self):
        self.condition.build()

    def print(self):
        after = f"\n".join([f"      - {dep.name}" for dep in self.after])
        starts = f"\n".join([f"      - {dep.name}" for dep in self.starts])
        stops = f"\n".join([f"      - {dep.name}" for dep in self.stops])
        print(
            f"[*] Automation <{self.name}>\n"
            f"    Condition: {self.condition.cond_lambda}\n"
            f"    Frequency: {self.freq} Hz\n"
            f"    Continuoues: {self.continuous}\n"
            f"    CheckOnce: {self.checkOnce}\n"
            f"    Starts:\n"
            f"      {starts}\n"
            f"    Stops:\n"
            f"      {stops}\n"
            f"    After:\n"
            f"      {after}\n"
        )

    # --- Steps runtime ---

    def _duration_to_seconds(self, d):
        millis = getattr(d, "millis", None)
        if millis is not None:
            return float(millis) / 1000.0
        seconds = getattr(d, "seconds", 0)
        return float(seconds)

    def _build_rests_mapping(self):
        """Build a mapping name -> dict of fields for REST sources."""
        if self._rests_cache is not None:
            return self._rests_cache
        rests = {}
        model = self.parent
        for rs in getattr(model, "restSources", []):
            if hasattr(rs, "data") and isinstance(rs.data, dict):
                rests[rs.name] = rs.data
            elif hasattr(rs, "value") and isinstance(rs.value, dict):
                rests[rs.name] = rs.value
            elif hasattr(rs, "fields") and isinstance(rs.fields, dict):
                rests[rs.name] = rs.fields
            else:
                rests[rs.name] = {}
        self._rests_cache = rests
        return rests

    def _get_rest_value(self, source_name, field_name):
        rests = self._build_rests_mapping()
        return rests.get(source_name, {}).get(field_name, None)

    def _eval_math(self, node, ctx):
        """Evaluate MathExpression to a number (supports REST and entity numeric attributes)."""
        mm = get_metamodel(self.parent)
        ns = mm.namespaces["condition"]

        def eval_expression(expr):
            parts = getattr(expr, "op", None)
            parts = parts if isinstance(parts, list) else [parts]
            val = eval_term(parts[0])
            i = 1
            while i < len(parts):
                op = parts[i]
                rhs = eval_term(parts[i + 1])
                if op == "+":
                    val += rhs
                else:
                    val -= rhs
                i += 2
            return val

        def eval_term(term):
            parts = getattr(term, "op", None)
            parts = parts if isinstance(parts, list) else [parts]
            val = eval_factor(parts[0])
            i = 1
            while i < len(parts):
                op = parts[i]
                rhs = eval_factor(parts[i + 1])
                if op == "*":
                    val *= rhs
                else:
                    val /= rhs
                i += 2
            return val

        def eval_factor(factor):
            sign = getattr(factor, "sign", None)
            v = eval_operand(getattr(factor, "op"))
            return -v if sign == "-" else v

        def eval_operand(operand):
            if isinstance(operand, (int, float)):
                return float(operand)
            if textx_isinstance(operand, ns["MathExpression"]):
                return eval_expression(operand)
            if textx_isinstance(operand, ns["MathOperand"]):
                return eval_operand(getattr(operand, "op"))
            if textx_isinstance(operand, ns["RestNumericRef"]):
                return float(self._get_rest_value(operand.source.name, operand.field))
            if hasattr(operand, "parent") and hasattr(operand, "name"):
                ent_name = operand.parent.name
                attr_name = operand.name
                return float(self.parent.entities_dict[ent_name].attributes_dict[attr_name].value)
            raise NotImplementedError("Unsupported operand in Compute expression.")

        return eval_expression(node)

    class DelayStepRt:
        def __init__(self, duration_sec):
            self.duration_sec = duration_sec

        def run(self, ctx, automation):
            time.sleep(self.duration_sec)

    class ComputeStepRt:
        def __init__(self, var_name, expr_node):
            self.var_name = var_name
            self.expr_node = expr_node

        def run(self, ctx, automation):
            try:
                val = automation._eval_math(self.expr_node, ctx)
                ctx[self.var_name] = val
            except Exception as e:
                print(f"[ERROR][Compute {self.var_name}] {e}")

    class StepActionRt:
        def __init__(self, attribute, value):
            self.attribute = attribute
            self.value = value

        def run(self, ctx, automation):
            value = self.value
            if type(value) is Dict:
                value = value.to_dict()
            elif type(value) is List:
                value = value.print_item(value)
            entity = self.attribute.parent
            entity.publisher.publish({self.attribute.name: value})

    class SwitchStepRt:
        def __init__(self, cases, default_steps):
            self.cases = cases
            self.default_steps = default_steps or []

        def run(self, ctx, automation):
            entities = automation.parent.entities_dict
            rests = automation._build_rests_mapping()
            locals_map = {"min": min, "max": max, "ctx": ctx}
            locals_map.update(ctx)
            for cond_code, steps in self.cases:
                try:
                    ok = eval(
                        cond_code,
                        {"entities": entities, "rests": rests},
                        locals_map,
                    )
                except Exception as e:
                    print(f"[ERROR][Switch case] {e}")
                    ok = False
                if ok:
                    for s in steps:
                        s.run(ctx, automation)
                    return
            for s in self.default_steps:
                s.run(ctx, automation)

    def _compile_steps(self):
        """Compile model steps (Delay/Compute/Switch/Action) to runtime objects."""
        mm = get_metamodel(self.parent)
        compiled = []

        def compile_step(s):
            cname = s.__class__.__name__
            if cname == "DelayStep":
                secs = self._duration_to_seconds(s.duration)
                return Automation.DelayStepRt(secs)
            if cname == "ComputeStep":
                return Automation.ComputeStepRt(s.var, s.expr)
            if cname == "StepAction":
                a = s
                return Automation.StepActionRt(a.attribute, a.value)
            if cname == "SwitchStep":
                cases = []
                for c in s.cases:
                    cond = c.cond
                    cond.parent = self
                    cond.build()
                    steps_rt = [compile_step(x) for x in c.steps]
                    cases.append((cond.cond_lambda, steps_rt))
                default_rt = (
                    [compile_step(x) for x in getattr(s, "default_steps", [])]
                    if hasattr(s, "default_steps")
                    else []
                )
                return Automation.SwitchStepRt(cases, default_rt)
            if hasattr(s, "attribute") and hasattr(s, "value"):
                return Automation.StepActionRt(s.attribute, s.value)
            raise NotImplementedError(f"Unsupported step: {cname}")

        for s in self.steps:
            compiled.append(compile_step(s))
        return compiled

    def start(self):
        self.state = AutomationState.IDLE
        self.build_condition()
        self.print()
        print(f"[bold yellow][*] Executing Automation: {self.name}[/bold yellow]")

        compiled_steps = self._compile_steps() if len(self.steps) > 0 else []
        while True:
            if len(self.after) == 0:
                self.state = AutomationState.RUNNING
            while self.state == AutomationState.IDLE:
                wait_for = [
                    dep.name
                    for dep in self.after
                    if dep.state == AutomationState.RUNNING
                ]
                if len(wait_for) == 0:
                    self.state = AutomationState.RUNNING
                print(
                    fr"[bold magenta]\[{self.name}] Waiting for dependent automations to finish:[/bold magenta] {wait_for}"
                )
                time.sleep(1)
            while self.state == AutomationState.RUNNING:
                try:
                    triggered, msg = self.evaluate_condition()
                    if triggered:
                        print(
                            f"[bold yellow][*] Automation <{self.name}> "
                            f"Triggered![/bold yellow]"
                        )
                        print(
                            f"[bold blue][*] Condition met: "
                            f"{self.condition.cond_lambda}"
                        )
                        if compiled_steps:
                            ctx = ExecutionContext()
                            for s in compiled_steps:
                                s.run(ctx, self)
                        else:
                            self.trigger_actions()

                        self.state = AutomationState.EXITED_SUCCESS
                        for automation in self.starts:
                            automation.enable()
                        for automation in self.stops:
                            automation.disable()
                    if self.checkOnce:
                        self.disable()
                        self.state = AutomationState.EXITED_SUCCESS
                    time.sleep(1 / self.freq)
                except Exception as e:
                    print(f"[ERROR] {e}")
                    return
            self.state = AutomationState.IDLE

    def enable(self):
        self.enabled = True
        print(f"[bold yellow][*] Enabled Automation: {self.name}[/bold yellow]")

    def disable(self):
        self.enabled = False
        print(f"[bold yellow][*] Disabled Automation: {self.name}[/bold yellow]")


class Action:
    def __init__(self, parent, attribute, value):
        self.parent = parent
        self.attribute = attribute
        self.value = value


class IntAction(Action):
    def __init__(self, parent, attribute, value):
        super(IntAction, self).__init__(parent, attribute, value)


class FloatAction(Action):
    def __init__(self, parent, attribute, value):
        super(FloatAction, self).__init__(parent, attribute, value)


class StringAction(Action):
    def __init__(self, parent, attribute, value):
        super(StringAction, self).__init__(parent, attribute, value)


class BoolAction(Action):
    def __init__(self, parent, attribute, value):
        super(BoolAction, self).__init__(parent, attribute, value)
