from textx import textx_isinstance, get_metamodel
import statistics
from smauto.lib.types import List, Dict, Time, Date

PRIMITIVES = (int, float, str, bool)

OPERATORS = {
    "~": lambda left, right: f"({left} in {right})",
    "!~": lambda left, right: f"({left} not in {right})",
    "has": lambda left, right: f"({right} in {left})",
    "has not": lambda left, right: f"({right} not in {left})",
    "==": lambda left, right: f"({left} == {right})",
    "!=": lambda left, right: f"({left} != {right})",
    "is": lambda left, right: f"({left} == {right})",
    "is not": lambda left, right: f"({left} != {right})",
    "in": lambda left, right: f"({left} in {right})",
    "not in": lambda left, right: f"({left} not in {right})",
    ">": lambda left, right: f"({left} > {right})",
    ">=": lambda left, right: f"({left} >= {right})",
    "<": lambda left, right: f"({left} < {right})",
    "<=": lambda left, right: f"({left} <= {right})",
    "AND": lambda left, right: f"({left} and {right})",
    "OR": lambda left, right: f"({left} or {right})",
    "NOT": lambda left, right: f"({left} is not {right})",
    "XOR": lambda left, right: f"({left} ^ {right})",
    "NOR": lambda left, right: f"(not ({left} or {right}))",
    "XNOR": lambda left, right: f"((({left}) and ({right})) or ((not {left}) and (not {right})))",
    "NAND": lambda left, right: f"(not ({left} and {right}))",
    "InRange": lambda attr, min, max: f"({attr} > {min} and {attr} < {max})",
}


class Condition(object):
    def __init__(self, parent):
        self.parent = parent
        self.cond_lambda = None
        self.cond_raw = None

    @staticmethod
    def transform_operand(node) -> str:
        if type(node) in PRIMITIVES:
            if type(node) is str:
                return f"'{node}'"
            else:
                return node
        elif type(node) == List:
            return node
        elif type(node) == Dict:
            return node
        elif type(node) == Time:
            return node.to_int()
        elif textx_isinstance(
            node, get_metamodel(node).namespaces["condition"]["AugmentedAttr"]
        ):
            return Condition.transform_augmented_attr(node)
        elif textx_isinstance(
            node, get_metamodel(node).namespaces["condition"]["SimpleTimeAttr"]
        ):
            val = (
                f"entities['{node.attribute.parent.name}']."
                + f"attributes_dict['{node.attribute.name}'].value.to_int()"
            )
            return val
        else:
            val = (
                f"entities['{node.parent.name}']."
                + f"attributes_dict['{node.name}'].value"
            )
            return val

    @staticmethod
    def transform_augmented_attr(aattr) -> str:
        parent = aattr.parent
        val: str = ""
        cname = aattr.__class__.__name__
        if cname == "SimpleNumericAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            if parent.__class__.__name__ in (
                "StdAttr",
                "MeanAttr",
                "VarAttr",
                "MinAttr",
                "MaxAttr",
            ):
                entity_ref.init_attr_buffer(attr_ref.name, parent.size)
                entity_ref.attr_buffs.append((attr_ref.name, parent.size))
                val = f"entities['{entity_ref.name}']." + f"get_buffer('{attr_ref.name}')"
            else:
                val = (
                    f"entities['{entity_ref.name}']."
                    + f"attributes_dict['{attr_ref.name}'].value"
                )
        elif cname == "SimpleBoolAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = (
                f"entities[''{entity_ref.name}'']."
                + f"attributes_dict['{attr_ref.name}'].value"
            )
            val = (
                f"entities['{entity_ref.name}']."
                + f"attributes_dict['{attr_ref.name}'].value"
            )
        elif cname == "SimpleStringAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = (
                f"entities['{entity_ref.name}']."
                + f"attributes_dict['{attr_ref.name}'].value"
            )
        elif cname == "SimpleDictAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = (
                f"entities['{entity_ref.name}']."
                + f"attributes_dict['{attr_ref.name}'].value"
            )
        elif cname == "SimpleListAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = (
                f"entities['{entity_ref.name}']."
                + f"attributes_dict['{attr_ref.name}'].value"
            )
        elif cname == "StdAttr":
            val = f"std({Condition.transform_augmented_attr(aattr.attribute)})"
        elif cname == "MeanAttr":
            val = f"mean({Condition.transform_augmented_attr(aattr.attribute)})"
        elif cname == "VarAttr":
            val = f"var({Condition.transform_augmented_attr(aattr.attribute)})"
        elif cname == "MaxAttr":
            val = f"max({Condition.transform_augmented_attr(aattr.attribute)})"
        elif cname == "MinAttr":
            val = f"min({Condition.transform_augmented_attr(aattr.attribute)})"
        elif cname == "RestNumericRef":
            val = f"rests['{aattr.source.name}']['{aattr.field}']"
        elif cname == "RestStringRef":
            val = f"rests['{aattr.source.name}'][''{aattr.field}'']"
            val = f"rests['{aattr.source.name}']['{aattr.field}']"
        elif cname == "RestBoolRef":
            val = f"rests['{aattr.source.name}']['{aattr.field}']"
        elif cname == "RestListRef":
            val = f"rests['{aattr.source.name}']['{aattr.field}']"
        elif cname == "RestDictRef":
            val = f"rests['{aattr.source.name}']['{aattr.field}']"
        return val

    def build(self):
        self.process_node_condition(self)
        return self.cond_lambda

    @staticmethod
    def process_node_condition(cond_node):
        metamodel = get_metamodel(cond_node.parent)
        if textx_isinstance(
            cond_node, metamodel.namespaces["condition"]["ConditionGroup"]
        ):
            Condition.process_node_condition(cond_node.r1)
            Condition.process_node_condition(cond_node.r2)
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(
                cond_node.r1.cond_lambda, cond_node.r2.cond_lambda
            )
        elif textx_isinstance(
            cond_node, metamodel.namespaces["condition"]["InRangeCondition"]
        ):
            cond_node.process_node_condition()
        else:
            operand1 = Condition.transform_operand(cond_node.operand1)
            operand2 = Condition.transform_operand(cond_node.operand2)
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(operand1, operand2)

    def evaluate(self):
        if self.cond_lambda not in (None, ""):
            try:
                entities = self.parent.parent.entities_dict
                model = self.parent.parent
                rests = {}
                for rs in getattr(model, "restSources", []):
                    if hasattr(rs, "data") and isinstance(rs.data, dict):
                        rests[rs.name] = rs.data
                    elif hasattr(rs, "value") and isinstance(rs.value, dict):
                        rests[rs.name] = rs.value
                    elif hasattr(rs, "fields") and isinstance(rs.fields, dict):
                        rests[rs.name] = rs.fields
                    else:
                        rests[rs.name] = {}
                if eval(
                    self.cond_lambda,
                    {"entities": entities, "rests": rests},
                    {
                        "std": statistics.stdev,
                        "var": statistics.variance,
                        "mean": statistics.mean,
                        "min": min,
                        "max": max,
                    },
                ):
                    return True, f"{self.parent.name}: triggered."
                else:
                    return False, f"{self.parent.name}: not triggered."
            except Exception as e:
                print(e)
                return False, f"{self.parent.name}: not triggered."
        else:
            return False, f"{self.parent.name}: condition not built."


class ConditionGroup(Condition):
    def __init__(self, parent, r1, operator, r2):
        self.r1 = r1
        self.r2 = r2
        self.operator = operator
        super().__init__(parent)


class PrimitiveCondition(Condition):
    def __init__(self, parent):
        super().__init__(parent)


class AdvancedCondition(Condition):
    def __init__(self, parent):
        super().__init__(parent)


class InRangeCondition(AdvancedCondition):
    def __init__(self, parent, attribute, min, max):
        self.attribute = attribute
        self.min = min
        self.max = max
        super().__init__(parent)

    def process_node_condition(self):
        operand1 = self.transform_operand(self.attribute)
        cond_lambda = (OPERATORS["InRange"])(operand1, self.min, self.max)
        self.cond_lambda = cond_lambda


class NumericCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class BoolCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class StringCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class ListCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class DictCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class TimeCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)
