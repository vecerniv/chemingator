"""Tests for chemingator.units.base."""

from typing import Any

import pytest

from chemingator.core import expression
from chemingator.core.port import Port
from chemingator.core.port import PortKind
from chemingator.core.variable import Variable
from chemingator.units.base import Unit

# --- Test doubles -----------------------------------------------------------


class OpenUnit(Unit):
    """Concrete Unit that exposes the protected builders to tests."""

    def add_inlet(self, name: str) -> Port:
        """Public wrapper around _add_inlet."""
        return self._add_inlet(name)

    def add_outlet(self, name: str) -> Port:
        """Public wrapper around _add_outlet."""
        return self._add_outlet(name)

    def add_variable(self, local_name: str, **kwargs: Any) -> Variable:
        """Public wrapper around _add_variable."""
        return self._add_variable(local_name, **kwargs)

    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del val, ops
        return []

    def n_equations(self) -> int:
        return 0


# --- Abstract interface -----------------------------------------------------


def test_unit_is_abstract() -> None:
    """Unit itself cannot be instantiated."""
    with pytest.raises(TypeError):
        Unit("M1")  # pylint: disable=abstract-class-instantiated


def test_subclass_must_implement_residuals() -> None:
    """A subclass missing an abstract method cannot be instantiated."""

    class Incomplete(Unit):

        def n_equations(self) -> int:
            return 0

    with pytest.raises(TypeError):
        Incomplete("M1")  # pylint: disable=abstract-class-instantiated


# --- Construction -----------------------------------------------------------


def test_unit_init() -> None:
    """A new unit has a name and nothing else yet."""
    unit = OpenUnit("M1")

    assert unit.name == "M1"
    assert not unit.inlets
    assert not unit.outlets
    assert not unit.ports()
    assert not unit.internal_variables()
    assert unit.flowsheet is None


# --- Ports ------------------------------------------------------------------


def test_add_inlet() -> None:
    """An inlet is created for this unit, registered and returned."""
    unit = OpenUnit("M1")

    inlet = unit.add_inlet("in0")

    assert inlet.unit is unit
    assert inlet.name == "in0"
    assert inlet.kind is PortKind.INLET
    assert unit.inlets == [inlet]
    assert not unit.outlets


def test_add_outlet() -> None:
    """An outlet is created for this unit, registered and returned."""
    unit = OpenUnit("M1")

    outlet = unit.add_outlet("out")

    assert outlet.unit is unit
    assert outlet.name == "out"
    assert outlet.kind is PortKind.OUTLET
    assert unit.outlets == [outlet]
    assert not unit.inlets


def test_ports_inlets_first() -> None:
    """ports() lists inlets, then outlets, each in declaration order."""
    unit = OpenUnit("M1")
    out = unit.add_outlet("out")
    in0 = unit.add_inlet("in0")
    in1 = unit.add_inlet("in1")

    assert unit.ports() == [in0, in1, out]


@pytest.mark.parametrize(
    "first, second",
    [("inlet", "inlet"), ("outlet", "outlet"), ("inlet", "outlet")],
    ids=["inlet-inlet", "outlet-outlet", "inlet-outlet"],
)
def test_duplicate_port_name_raises(first: str, second: str) -> None:
    """Port names are unique within a unit, across inlets and outlets."""
    unit = OpenUnit("M1")
    add = {"inlet": unit.add_inlet, "outlet": unit.add_outlet}
    add[first]("p")

    with pytest.raises(ValueError, match="'p'"):
        add[second]("p")

    assert len(unit.ports()) == 1


# --- Internal variables -----------------------------------------------------


def test_add_variable() -> None:
    """A variable is named after the unit, registered and returned."""
    unit = OpenUnit("M1")

    var = unit.add_variable("split[0]")

    assert var.name == "M1.split[0]"
    assert unit.internal_variables() == [var]


def test_add_variable_passes_kwargs() -> None:
    """Keyword arguments reach the Variable constructor."""
    unit = OpenUnit("M1")

    var = unit.add_variable("split[0]", value=0.5, fixed=True, units="-")

    assert var.value == 0.5
    assert var.fixed is True
    assert var.units == "-"


def test_internal_variables_returns_copy() -> None:
    """Changing the returned list does not change the unit."""
    unit = OpenUnit("M1")
    unit.add_variable("split[0]")

    unit.internal_variables().clear()

    assert len(unit.internal_variables()) == 1


# --- initialize() -----------------------------------------------------------


def test_initialize_default_changes_nothing() -> None:
    """The default initialize() leaves every value as it was."""
    unit = OpenUnit("M1")
    var = unit.add_variable("split[0]", value=0.5)

    unit.initialize()

    assert var.value == 0.5
