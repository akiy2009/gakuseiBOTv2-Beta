import pytest

from cogs.normal.utilities import calculate_expression, parse_choices


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("(12 + 8) * 3 / 2", 30),
        ("-5 + 2", -3),
        ("2 ** 3", 8),
        ("7 // 2", 3),
        ("7 % 2", 1),
    ],
)
def test_calculate_expression_supports_basic_arithmetic(expression, expected):
    assert calculate_expression(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo unsafe')",
        "1 / 0",
        "2 ** 11",
        "",
        "1" * 101,
        "True",
        "[1, 2]",
    ],
)
def test_calculate_expression_rejects_unsafe_or_invalid_input(expression):
    with pytest.raises(ValueError):
        calculate_expression(expression)


def test_parse_choices_trims_values_and_preserves_order():
    assert parse_choices(" A, B , C ") == ["A", "B", "C"]


@pytest.mark.parametrize("value", ["one", "a, b, a", "a, b, c" + ", d" * 18])
def test_parse_choices_rejects_invalid_choice_sets(value):
    with pytest.raises(ValueError):
        parse_choices(value)


def test_parse_choices_rejects_long_options():
    with pytest.raises(ValueError):
        parse_choices("short, " + "x" * 81)
