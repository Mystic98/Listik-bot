import pytest
from utils import (
    parse_quantity,
    format_item,
    extract_quantity_parts,
    extract_unit,
    combine_quantities,
    get_unit_group,
    normalize_to_base,
    format_quantity,
)


class TestParseQuantity:
    def test_parse_quantity_with_liters(self):
        name, quantity = parse_quantity("молоко 2л")
        assert name == "молоко"
        assert quantity == "2л"

    def test_parse_quantity_with_milliliters(self):
        name, quantity = parse_quantity("сок 500мл")
        assert name == "сок"
        assert quantity == "500мл"

    def test_parse_quantity_with_kilograms(self):
        name, quantity = parse_quantity("картошка 2кг")
        assert name == "картошка"
        assert quantity == "2кг"

    def test_parse_quantity_with_grams(self):
        name, quantity = parse_quantity("сыр 500г")
        assert name == "сыр"
        assert quantity == "500г"

    def test_parse_quantity_with_pieces(self):
        name, quantity = parse_quantity("яйца 10 шт")
        assert name == "яйца"
        assert quantity == "10 шт"

    def test_parse_quantity_with_packs(self):
        name, quantity = parse_quantity("макароны 2 уп")
        assert name == "макароны"
        assert quantity == "2 уп"

    def test_parse_quantity_without_unit(self):
        name, quantity = parse_quantity("хлеб")
        assert name == "хлеб"
        assert quantity is None

    def test_parse_quantity_empty_string(self):
        name, quantity = parse_quantity("")
        assert name is None
        assert quantity is None

    def test_parse_quantity_whitespace_only(self):
        name, quantity = parse_quantity("   ")
        assert name is None
        assert quantity is None

    def test_parse_quantity_with_decimal(self):
        name, quantity = parse_quantity("вода 1.5л")
        assert name == "вода"
        assert quantity == "1.5л"

    def test_parse_quantity_with_comma_decimal(self):
        name, quantity = parse_quantity("молоко 2,5л")
        assert name == "молоко"
        assert quantity == "2.5л"

    def test_parse_quantity_case_insensitive_units(self):
        name, quantity = parse_quantity("молоко 2Л")
        assert name == "молоко"
        assert quantity == "2Л"

    def test_parse_quantity_with_multiple_words(self):
        name, quantity = parse_quantity("белый хлеб 2 шт")
        assert name == "белый хлеб"
        assert quantity == "2 шт"

    def test_parse_quantity_none_input(self):
        name, quantity = parse_quantity(None)
        assert name is None
        assert quantity is None


class TestFormatItem:
    def test_format_item_with_quantity(self):
        result = format_item("молоко", "2л")
        assert result == "молоко 2л"

    def test_format_item_without_quantity(self):
        result = format_item("хлеб", None)
        assert result == "хлеб"

    def test_format_item_empty_quantity(self):
        result = format_item("сыр", "")
        assert result == "сыр"


class TestExtractQuantityParts:
    def test_extract_parts_liters(self):
        value, unit = extract_quantity_parts("2л")
        assert value == 2
        assert unit == "л"

    def test_extract_parts_with_space(self):
        value, unit = extract_quantity_parts("10 шт")
        assert value == 10
        assert unit == "шт"

    def test_extract_parts_decimal(self):
        value, unit = extract_quantity_parts("1.5кг")
        assert value == 1.5
        assert unit == "кг"

    def test_extract_parts_grams(self):
        value, unit = extract_quantity_parts("500г")
        assert value == 500
        assert unit == "г"

    def test_extract_parts_none(self):
        value, unit = extract_quantity_parts(None)
        assert value is None
        assert unit == ""

    def test_extract_parts_empty(self):
        value, unit = extract_quantity_parts("")
        assert value is None
        assert unit == ""

    def test_extract_parts_no_unit(self):
        value, unit = extract_quantity_parts("2")
        assert value is None
        assert unit == ""


class TestExtractUnit:
    def test_extract_unit_liters(self):
        assert extract_unit("2л") == "л"

    def test_extract_unit_pieces(self):
        assert extract_unit("10 шт") == "шт"

    def test_extract_unit_none(self):
        assert extract_unit(None) == ""

    def test_extract_unit_empty(self):
        assert extract_unit("") == ""


class TestCombineQuantities:
    def test_combine_same_units(self):
        result = combine_quantities("2л", "3л")
        assert result == "5л"

    def test_combine_decimal_result(self):
        result = combine_quantities("1.5кг", "0.5кг")
        assert result == "2кг"

    def test_combine_different_units(self):
        result = combine_quantities("2л", "3кг")
        assert result is None

    def test_combine_with_none_first(self):
        result = combine_quantities(None, "2л")
        assert result is None

    def test_combine_with_none_second(self):
        result = combine_quantities("2л", None)
        assert result is None

    def test_combine_pieces(self):
        result = combine_quantities("5 шт", "3 шт")
        assert result == "8шт"

    def test_combine_grams(self):
        result = combine_quantities("200г", "300г")
        assert result == "500г"


class TestGetUnitGroup:
    def test_kilograms(self):
        assert get_unit_group("кг") == "weight"

    def test_grams(self):
        assert get_unit_group("г") == "weight"

    def test_liters(self):
        assert get_unit_group("л") == "volume"

    def test_milliliters(self):
        assert get_unit_group("мл") == "volume"

    def test_pieces(self):
        assert get_unit_group("шт") == "pieces"

    def test_packs(self):
        assert get_unit_group("уп") == "pieces"

    def test_none(self):
        assert get_unit_group(None) == "pieces"

    def test_empty(self):
        assert get_unit_group("") == "pieces"


class TestNormalizeToBase:
    def test_kg_to_grams(self):
        value, group = normalize_to_base("2кг")
        assert value == 2000
        assert group == "weight"

    def test_grams_stays_grams(self):
        value, group = normalize_to_base("500г")
        assert value == 500
        assert group == "weight"

    def test_liters_to_ml(self):
        value, group = normalize_to_base("1.5л")
        assert value == 1500
        assert group == "volume"

    def test_ml_stays_ml(self):
        value, group = normalize_to_base("300мл")
        assert value == 300
        assert group == "volume"

    def test_pieces(self):
        value, group = normalize_to_base("5шт")
        assert value == 5
        assert group == "pieces"

    def test_packs(self):
        value, group = normalize_to_base("2уп")
        assert value == 2
        assert group == "pieces"

    def test_none_becomes_1_piece(self):
        value, group = normalize_to_base(None)
        assert value == 1
        assert group == "pieces"


class TestFormatQuantity:
    def test_grams_under_1000(self):
        assert format_quantity(500, "weight") == "500г"

    def test_grams_exactly_1000(self):
        assert format_quantity(1000, "weight") == "1кг"

    def test_grams_over_1000(self):
        assert format_quantity(1200, "weight") == "1.2кг"

    def test_grams_decimal_kg(self):
        assert format_quantity(1500, "weight") == "1.5кг"

    def test_ml_under_1000(self):
        assert format_quantity(500, "volume") == "500мл"

    def test_ml_exactly_1000(self):
        assert format_quantity(1000, "volume") == "1л"

    def test_ml_over_1000(self):
        assert format_quantity(1500, "volume") == "1.5л"

    def test_pieces(self):
        assert format_quantity(5, "pieces") == "5шт"

    def test_pieces_decimal(self):
        assert format_quantity(5.5, "pieces") == "5.5шт"


class TestCombineQuantitiesNew:
    def test_combine_kg_and_grams(self):
        result = combine_quantities("1кг", "200г")
        assert result == "1.2кг"

    def test_combine_grams_to_kg(self):
        result = combine_quantities("700г", "300г")
        assert result == "1кг"

    def test_combine_grams_under_1000(self):
        result = combine_quantities("200г", "300г")
        assert result == "500г"

    def test_combine_liters_and_ml(self):
        result = combine_quantities("1л", "500мл")
        assert result == "1.5л"

    def test_combine_ml_to_liters(self):
        result = combine_quantities("700мл", "300мл")
        assert result == "1л"

    def test_combine_ml_under_1000(self):
        result = combine_quantities("200мл", "300мл")
        assert result == "500мл"

    def test_combine_none_none(self):
        result = combine_quantities(None, None)
        assert result == "2шт"

    def test_combine_none_with_pieces(self):
        result = combine_quantities(None, "2шт")
        assert result == "3шт"

    def test_combine_pieces_with_none(self):
        result = combine_quantities("2шт", None)
        assert result == "3шт"

    def test_combine_packs(self):
        result = combine_quantities("1уп", "2уп")
        assert result == "3шт"

    def test_combine_pack_with_none(self):
        result = combine_quantities("1уп", None)
        assert result == "2шт"

    def test_combine_different_groups_kg_pieces(self):
        result = combine_quantities("1кг", "1шт")
        assert result is None

    def test_combine_different_groups_l_kg(self):
        result = combine_quantities("1л", "1кг")
        assert result is None
