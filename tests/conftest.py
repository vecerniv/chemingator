"""Shared pytest fixtures and test doubles."""

import pytest

from chemingator.core import expression
from chemingator.core.component import ComponentList
from chemingator.core.stream import Stream
from chemingator.units.base import Unit


class DummyUnit(Unit):
    """Minimal concrete Unit for tests that only need an owner with a name."""

    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del val, ops  # Unused.
        return []

    def n_equations(self) -> int:
        return 0


@pytest.fixture
def unit() -> Unit:
    """A unit named "M1" to own ports."""
    return DummyUnit("M1")


@pytest.fixture
def components() -> ComponentList:
    """Components "A" and "B"."""
    return ComponentList(["A", "B"])


@pytest.fixture
def stream(components: ComponentList) -> Stream:  # pylint: disable=redefined-outer-name
    """A stream "S1" not yet attached to any port."""
    return Stream("S1", components)
