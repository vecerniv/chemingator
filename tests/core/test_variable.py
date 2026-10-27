"""Tests for chemingator.core.variable."""

import pytest

from chemingator.core.variable import current_value
from chemingator.core.variable import Variable

# --- Construction -----------------------------------------------------------


def test_defaults() -> None:
    """A variable created with only a name is an unknown with no value."""
    var = Variable("T")

    assert var.name == "T"
    assert var.value is None
    assert var.lower is None
    assert var.upper is None
    assert var.fixed is False
    assert var.units == ""


def test_create_fixed_with_value() -> None:
    """A variable can be created already fixed if it has a value."""
    var = Variable(
        "T", value=300.0, lower=0.0, upper=500.0, fixed=True, units="K"
    )

    assert var.value == 300.0
    assert var.lower == 0.0
    assert var.upper == 500.0
    assert var.fixed is True
    assert var.units == "K"


def test_create_lower_bound() -> None:
    """A variable can be created with a lower bound only."""
    var = Variable("T", value=300.0, lower=100.0)

    assert var.value == 300.0
    assert var.lower == 100.0
    assert var.upper is None


def test_create_upper_bound() -> None:
    """A variable can be created with an upper bound only."""
    var = Variable("T", value=300.0, upper=500.0)

    assert var.value == 300.0
    assert var.lower is None
    assert var.upper == 500.0


def test_create_fixed_below_lower_raises() -> None:
    """A specification below lower bound is rejected."""
    with pytest.raises(ValueError, match="outside"):
        Variable("T", value=300.0, lower=500.0, fixed=True)


def test_create_fixed_above_upper_raises() -> None:
    """A specification above upper bound is rejected."""
    with pytest.raises(ValueError, match="outside"):
        Variable("T", value=300.0, upper=200.0, fixed=True)


def test_create_lower_bigger_than_upper_raises() -> None:
    """A variable with lower bound higher than upper bound is rejected."""
    with pytest.raises(ValueError, match="lower bound"):
        Variable("T", lower=100.0, upper=10.0)


def test_create_fixed_without_value_raises() -> None:
    """A specification without value is rejected."""
    with pytest.raises(ValueError, match="None"):
        Variable("T", fixed=True)


def test_positional_after_name_raises() -> None:
    """Arguments after name are keyword only."""
    with pytest.raises(TypeError):
        Variable("T", 300.0)  # pylint: disable=too-many-function-args


# --- Properties -------------------------------------------------------------


def test_fixed_var_cannot_lose_value() -> None:
    """A fixed variable cannot have None assigned to `value`."""
    var = Variable("T", value=300.0, fixed=True)

    with pytest.raises(ValueError):
        var.value = None

    assert var.value == 300.0


def test_unfix_var_can_be_none() -> None:
    """An unfixed variable can have None assigned to `value`."""
    var = Variable("T", value=300.0)

    var.value = None

    assert var.value is None


def test_fixed_is_read_only() -> None:
    """`fixed` attribute can only be changed with fix() and unfix()."""
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


def test_fix_value_equal_to_bounds() -> None:
    """fix() with value == lower == upper is a valid specification."""
    var = Variable("T", lower=100.0, upper=100.0)

    var.fix(100.0)

    assert var.value == 100.0
    assert var.fixed is True


def test_fix_without_value_raises() -> None:
    """fix() on a variable without value fails."""
    var = Variable("T")

    with pytest.raises(ValueError):
        var.fix()

    assert var.fixed is False


def test_failed_fix_keeps_value() -> None:
    """Failed fix() keeps the variable's original state."""
    var = Variable("T", value=300.0, lower=100.0)

    with pytest.raises(ValueError):
        var.fix(50.0)

    assert var.value == 300.0
    assert var.fixed is False


# --- unfix() ----------------------------------------------------------------


def test_unfix_keeps_value() -> None:
    """unfix() turns a specification into a guess, keeping its value."""
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


# --- current_value() --------------------------------------------------------


def test_current_value() -> None:
    """The numeric resolver returns the variable's value."""
    var = Variable("T", value=300.0)

    assert current_value(var) == 300.0


def test_current_value_unset_raises() -> None:
    """A variable without a value cannot be resolved to a number."""
    var = Variable("T")

    with pytest.raises(ValueError, match="'T'"):
        current_value(var)


# --- within_bounds() --------------------------------------------------------


def test_bounds_without_tol() -> None:
    """A variable lies in bounds with no tolerance."""
    var = Variable("T", value=300.0, lower=100.0, upper=500.0)

    assert var.within_bounds() is True


def test_bounds_with_tol() -> None:
    """`tol` widens the bounds."""
    var = Variable("T", value=99.0, lower=100.0)

    assert var.within_bounds() is False
    assert var.within_bounds(tol=2.0) is True


def test_none_value_in_bounds() -> None:
    """A variable with no value is in bounds."""
    var = Variable("T")

    assert var.within_bounds() is True


def test_value_in_no_bounds() -> None:
    """A variable with no bounds is in bounds."""
    var = Variable("T", value=300.0)

    assert var.within_bounds() is True


def test_value_not_in_bounds_lower() -> None:
    """A variable below lower returns False."""
    var = Variable("T", value=100.0, lower=200.0)

    assert var.within_bounds() is False


def test_value_not_in_bounds_upper() -> None:
    """A variable above upper returns False."""
    var = Variable("T", value=100.0, upper=50.0)

    assert var.within_bounds() is False


def test_value_at_bound() -> None:
    """A value exactly on bounds returns True."""
    var = Variable("T", value=100.0, lower=100.0, upper=100.0)

    assert var.within_bounds() is True
