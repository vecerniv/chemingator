"""Tests for chemingator.core.variable."""

import pytest

from chemingator.core.variable import Variable

# --- Construction -----------------------------------------------------------


def test_defaults() -> None:
    """A variable created with only a name is an unknown with no value."""
    var = Variable("T")

    assert var.name == "T"
    assert var.value is None
    assert var.fixed is False
    assert var.units == ""


def test_create_fixed_with_value() -> None:
    """A variable can be created already fixed if it has a value."""
    var = Variable("T", value=300.0, fixed=True, units="K")

    assert var.value == 300.0
    assert var.fixed is True
    assert var.units == "K"


def test_create_fixed_without_value_raises() -> None:
    """A specification without value is rejected."""
    with pytest.raises(ValueError):
        Variable("T", fixed=True)


# --- Properties -------------------------------------------------------------


def test_fixed_var_cannot_lose_value() -> None:
    """A fixed variable cannot have None assigned to `value`."""
    var = Variable("T", value=300.0, fixed=True)

    with pytest.raises(ValueError):
        var.value = None

    assert var.value == 300.0


def test_unfix_var_can_be_none() -> None:
    """An unfix variable can have None assigned to `value`."""
    var = Variable("T", value=300.0)

    var.value = None

    assert var.value is None


def test_fixed_is_read_only() -> None:
    """`fixes` attribute can only be changed with fix() and unfix()."""
    var = Variable("T")

    with pytest.raises(AttributeError):
        var.fixed = True

    assert var.fixed is False


# --- fix() ------------------------------------------------------------------


def test_fix_with_new_value() -> None:
    """fix(value) fixes the variable and sets a new value."""
    var = Variable("T", value=250.0)

    var.fix(300.0)

    assert var.value == 300.0
    assert var.fixed is True


def test_fix_keeps_value() -> None:
    """fix() fixes the variable and keeps the old value."""
    var = Variable("T", value=250.0)

    var.fix()

    assert var.value == 250.0
    assert var.fixed is True


def test_fix_to_zero() -> None:
    """fix(0.0) is a valid specification, not a missing value."""
    var = Variable("T")

    var.fix(0.0)

    assert var.value == 0.0
    assert var.fixed is True


def test_fix_without_value_raises() -> None:
    """fix() on a variable without value fails."""
    var = Variable("T")

    with pytest.raises(ValueError):
        var.fix()

    assert var.fixed is False


# --- unfix() ----------------------------------------------------------------


def test_unfix_keeps_value() -> None:
    """unfix() turns a specification into a guess, keeping it's value."""
    var = Variable("T", value=300.0, fixed=True)

    var.unfix()

    assert var.value == 300.0
    assert var.fixed is False


# --- Identity ---------------------------------------------------------------


def test_equality_is_identity() -> None:
    """Two variables with equal values are still different variables."""
    var_a = Variable("T", value=300.0)
    var_b = Variable("T", value=300.0)

    assert var_a != var_b
    assert var_a == var_a


def test_variable_hashable() -> None:
    """Variables are hashable, so they can index dicts and sets."""
    var = Variable("T")

    lookup = {var: 0}

    assert lookup[var] == 0
