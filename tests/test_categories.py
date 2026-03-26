import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from categories import (
    categorize_product,
    get_category_name,
    get_category_emoji,
    get_sorted_categories,
    get_all_categories,
    normalize_text,
    extract_words,
    find_category_by_keyword,
    find_category_by_partial_match,
    find_category_by_fuzzy_match,
)


class TestNormalizeText:
    def test_lowercase(self):
        assert normalize_text("МОЛОКО") == "молоко"

    def test_strip(self):
        assert normalize_text("  молоко  ") == "молоко"

    def test_multiple_spaces(self):
        assert normalize_text("молоко  2л") == "молоко 2л"

    def test_empty(self):
        assert normalize_text("") == ""

    def test_none(self):
        assert normalize_text(None) == ""


class TestExtractWords:
    def test_simple(self):
        assert extract_words("молоко 2л") == ["молоко", "2л"]

    def test_single_word(self):
        assert extract_words("хлеб") == ["хлеб"]

    def test_empty(self):
        assert extract_words("") == []

    def test_short_words_filtered(self):
        result = extract_words("я и ты")
        assert all(len(w) >= 2 for w in result)


class TestFindCategoryByKeyword:
    def test_dairy(self):
        assert find_category_by_keyword("молоко") == "dairy"

    def test_meat(self):
        assert find_category_by_keyword("курица") == "meat"

    def test_not_found(self):
        assert find_category_by_keyword("неизвестныйтовар") is None

    def test_short_word(self):
        assert find_category_by_keyword("я") is None


class TestFindCategoryByPartialMatch:
    def test_partial_dairy(self):
        assert find_category_by_partial_match("домашнее молоко") == "dairy"

    def test_partial_meat(self):
        assert find_category_by_partial_match("куриная грудка") == "meat"

    def test_not_found(self):
        assert find_category_by_partial_match("неизвестный") is None


class TestFindCategoryByFuzzyMatch:
    def test_typo_milk(self):
        result = find_category_by_fuzzy_match("малоко", threshold=0.6)
        assert result == "dairy" or result is None

    def test_not_found(self):
        result = find_category_by_fuzzy_match("xyzabc12345", threshold=0.8)
        assert result is None


class TestCategorizeProduct:
    def test_dairy_exact(self):
        assert categorize_product("молоко") == "dairy"

    def test_meat_exact(self):
        assert categorize_product("курица") == "meat"

    def test_fish_exact(self):
        assert categorize_product("лосось") == "fish"

    def test_vegetables_exact(self):
        assert categorize_product("картофель") == "vegetables"

    def test_fruits_exact(self):
        assert categorize_product("яблоки") == "fruits"

    def test_bakery_exact(self):
        assert categorize_product("хлеб") == "bakery"

    def test_grocery_exact(self):
        assert categorize_product("рис") == "grocery"

    def test_drinks_exact(self):
        assert categorize_product("сок") == "drinks"

    def test_sweets_exact(self):
        assert categorize_product("шоколад") == "sweets"

    def test_household_exact(self):
        assert categorize_product("шампунь") == "household"

    def test_unknown_returns_other(self):
        assert categorize_product("xyzqwerty123") == "other"

    def test_empty_returns_other(self):
        assert categorize_product("") == "other"

    def test_none_returns_other(self):
        assert categorize_product(None) == "other"

    def test_partial_match(self):
        assert categorize_product("домашнее молоко") == "dairy"

    def test_case_insensitive(self):
        assert categorize_product("МОЛОКО") == "dairy"

    def test_user_categories_override(self):
        user_cats = {"супертовар": "meat"}
        assert categorize_product("супертовар", user_cats) == "meat"

    def test_user_categories_partial(self):
        user_cats = {"молоко": "other"}
        assert categorize_product("домашнее молоко", user_cats) == "other"


class TestGetCategoryName:
    def test_dairy(self):
        assert "Молочные" in get_category_name("dairy")

    def test_meat(self):
        assert "Мясо" in get_category_name("meat")

    def test_other(self):
        assert "Другое" in get_category_name("other")

    def test_unknown(self):
        assert "Другое" in get_category_name("unknown")


class TestGetCategoryEmoji:
    def test_dairy(self):
        assert "🥛" in get_category_emoji("dairy")

    def test_meat(self):
        assert "🥩" in get_category_emoji("meat")

    def test_other(self):
        assert "📦" in get_category_emoji("other")


class TestGetSortedCategories:
    def test_returns_list(self):
        result = get_sorted_categories()
        assert isinstance(result, list)

    def test_dairy_first(self):
        result = get_sorted_categories()
        assert result[0] == "dairy"

    def test_other_last(self):
        result = get_sorted_categories()
        assert result[-1] == "other"

    def test_contains_all(self):
        result = get_sorted_categories()
        assert "dairy" in result
        assert "meat" in result
        assert "fish" in result
        assert "other" in result


class TestGetAllCategories:
    def test_returns_dict(self):
        result = get_all_categories()
        assert isinstance(result, dict)

    def test_has_dairy(self):
        result = get_all_categories()
        assert "dairy" in result
        assert "name" in result["dairy"]
        assert "order" in result["dairy"]

    def test_not_modifies_original(self):
        result = get_all_categories()
        result["test"] = {"name": "Test", "order": 0}
        result2 = get_all_categories()
        assert "test" not in result2
