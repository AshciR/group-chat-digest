import pytest

from chat_nuff_bot.utils import str_to_bool


@pytest.mark.parametrize("test_input,expected", [
    ('true', True),
    ('t', True),
    ('1', True),
    ('yes', True),
    ('Y', True),
    ('TRUE', True),
    ('TrUe', True)
])
def test_str_to_bool_true_values(test_input, expected):
    assert str_to_bool(test_input) == expected


@pytest.mark.parametrize("test_input,expected", [
    ('false', False),
    ('f', False),
    ('0', False),
    ('no', False),
    ('N', False),
    ('FALSE', False),
    ('FaLsE', False)
])
def test_str_to_bool_false_values(test_input, expected):
    assert str_to_bool(test_input) == expected


@pytest.mark.parametrize("test_input", [
    'not_a_boolean',
    '123',
    '',
    'TrueFalse',
    'yesno'
])
def test_str_to_bool_invalid_values(test_input):
    with pytest.raises(ValueError):
        str_to_bool(test_input)


@pytest.mark.parametrize("test_input", [
    None,
    100,
    [],
    {}
])
def test_str_to_bool_non_string_input(test_input):
    with pytest.raises(AttributeError):
        str_to_bool(test_input)
