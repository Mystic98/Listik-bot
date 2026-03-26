import re
from typing import Optional, Tuple, Union

UNITS = ["л", "мл", "кг", "г", "шт", "уп"]
UNITS_PATTERN = "|".join(UNITS)


def parse_quantity(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not text or not text.strip():
        return None, None

    text = text.strip()

    pattern = rf"^(.+?)\s+(\d+(?:[.,]\d+)?\s*({UNITS_PATTERN}))$"
    match = re.match(pattern, text, re.IGNORECASE)

    if match:
        name = match.group(1).strip()
        quantity = match.group(2).strip()
        quantity = quantity.replace(",", ".")
        return name if name else None, quantity

    return text if text else None, None


def format_item(name: str, quantity: Optional[str] = None) -> str:
    if quantity:
        return f"{name} {quantity}"
    return name


def extract_quantity_parts(
    quantity: Optional[str],
) -> Tuple[Union[int, float, None], str]:
    if not quantity:
        return None, ""

    quantity = quantity.strip()

    pattern = rf"^(\d+(?:[.,]\d+)?)\s*({UNITS_PATTERN})$"
    match = re.match(pattern, quantity, re.IGNORECASE)

    if match:
        value_str = match.group(1).replace(",", ".")
        value = float(value_str) if "." in value_str else int(value_str)
        unit = match.group(2).lower()
        return value, unit

    return None, ""


def extract_unit(quantity: Optional[str]) -> str:
    _, unit = extract_quantity_parts(quantity)
    return unit


def get_unit_group(unit: Optional[str]) -> Optional[str]:
    if unit in ("кг", "г"):
        return "weight"
    if unit in ("л", "мл"):
        return "volume"
    if unit in ("шт", "уп") or unit is None or unit == "":
        return "pieces"
    return None


def normalize_to_base(quantity: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if quantity is None:
        return 1.0, "pieces"

    val, unit = extract_quantity_parts(quantity)
    if val is None:
        return 1.0, "pieces"

    group = get_unit_group(unit)
    if group == "weight":
        if unit == "кг":
            return val * 1000, "weight"
        return float(val), "weight"
    elif group == "volume":
        if unit == "л":
            return val * 1000, "volume"
        return float(val), "volume"
    elif group == "pieces":
        return float(val), "pieces"

    return None, None


def format_quantity(base_value: float, group: str) -> Optional[str]:
    if group == "weight":
        if base_value >= 1000:
            kg = base_value / 1000
            if kg == int(kg):
                kg = int(kg)
            return f"{kg}кг"
        else:
            g = int(base_value) if base_value == int(base_value) else base_value
            return f"{g}г"
    elif group == "volume":
        if base_value >= 1000:
            l = base_value / 1000
            if l == int(l):
                l = int(l)
            return f"{l}л"
        else:
            ml = int(base_value) if base_value == int(base_value) else base_value
            return f"{ml}мл"
    elif group == "pieces":
        p = int(base_value) if base_value == int(base_value) else base_value
        return f"{p}шт"

    return None


def combine_quantities(q1: Optional[str], q2: Optional[str]) -> Optional[str]:
    base1, group1 = normalize_to_base(q1)
    base2, group2 = normalize_to_base(q2)

    if base1 is None or base2 is None or group1 is None or group2 is None:
        return None

    if group1 != group2:
        return None

    total = base1 + base2
    return format_quantity(total, group1)
