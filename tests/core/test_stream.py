"""Tests for chemingator.core.stream."""

import pytest

from chemingator.core.component import Component
from chemingator.core.component import ComponentList
from chemingator.core.stream import Stream
from chemingator.exceptions import BasisError

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture(name="mass_stream")
def fixture_mass_stream() -> Stream:
    """A stream whose component "A" has a molar mass and "B" has none.

    The molar mass is an arbitrary test number, not physical data.
    """
    components = ComponentList([Component("A", molar_mass=0.5), "B"])
    return Stream("S2", components)


# --- Construction -----------------------------------------------------------


def test_stream_init(stream: Stream) -> None:
    """A new stream has one unknown molar flow per component, no ports."""
    assert stream.name == "S1"
    assert list(stream.flow) == ["A", "B"]
    assert stream.source is None
    assert stream.destination is None


def test_stream_flow_variables(stream: Stream) -> None:
    """Flow variables are named per stream and component, in mol/s."""
    var = stream.flow["A"]

    assert var.name == "S1.flow[A]"
    assert var.units == "mol/s"
    assert var.value is None
    assert var.fixed is False


def test_variables_in_component_order(stream: Stream) -> None:
    """variables() returns the flow variables themselves, in order."""
    assert stream.variables() == [stream.flow["A"], stream.flow["B"]]


# --- total_flow() and molar_fraction() --------------------------------------


def test_total_flow(stream: Stream) -> None:
    """Total flow is the sum of component flows given by the resolver."""
    values = {stream.flow["A"]: 3.0, stream.flow["B"]: 1.0}

    assert stream.total_flow(lambda var: values[var]) == pytest.approx(4.0)


def test_molar_fraction(stream: Stream) -> None:
    """Molar fraction is component flow over total flow."""
    values = {stream.flow["A"]: 3.0, stream.flow["B"]: 1.0}

    fraction = stream.molar_fraction("A", lambda var: values[var])

    assert fraction == pytest.approx(0.75)


# --- specify() --------------------------------------------------------------


def test_specify_kwargs(stream: Stream) -> None:
    """specify(A=...) fixes only the named components."""
    stream.specify(A=2.0)

    assert stream.flow["A"].fixed is True
    assert stream.flow["A"].value == 2.0
    assert stream.flow["B"].fixed is False


def test_specify_mapping(stream: Stream) -> None:
    """specify({...}) fixes every name in the mapping."""
    stream.specify({"A": 2.0, "B": 1.0})

    assert stream.flow["A"].value == 2.0
    assert stream.flow["A"].fixed is True
    assert stream.flow["B"].value == 1.0
    assert stream.flow["B"].fixed is True


def test_specify_kwargs_override_mapping(stream: Stream) -> None:
    """A name given both ways takes the keyword value."""
    stream.specify({"A": 2.0}, A=5.0)

    assert stream.flow["A"].value == 5.0


def test_specify_unknown_name_raises(stream: Stream) -> None:
    """An unknown name is rejected before anything is fixed."""
    with pytest.raises(KeyError, match="'C'"):
        stream.specify(A=2.0, C=1.0)

    assert stream.flow["A"].fixed is False


# --- specify_mass() ---------------------------------------------------------


def test_specify_mass_converts_molar(mass_stream: Stream) -> None:
    """Mass flow is divided by molar mass: 1.0 kg/s / 0.5 kg/mol."""
    mass_stream.specify_mass(A=1.0)

    assert mass_stream.flow["A"].fixed is True
    assert mass_stream.flow["A"].value == pytest.approx(2.0)


def test_specify_mass_without_molar_mass_raises(mass_stream: Stream) -> None:
    """A component without molar mass cannot be given on mass basis."""
    with pytest.raises(BasisError, match="'B'"):
        mass_stream.specify_mass(A=1.0, B=1.0)

    assert mass_stream.flow["A"].fixed is False


def test_specify_mass_matching_molar_spec(mass_stream: Stream) -> None:
    """A mass spec equal to the existing molar spec is accepted."""
    mass_stream.specify(A=2.0)

    mass_stream.specify_mass(A=1.0)

    assert mass_stream.flow["A"].value == pytest.approx(2.0)


def test_specify_mass_conflicting_molar_spec_raises(
    mass_stream: Stream,
) -> None:
    """A mass spec contradicting the existing molar spec is rejected."""
    mass_stream.specify(A=3.0)

    with pytest.raises(BasisError):
        mass_stream.specify_mass(A=1.0)

    assert mass_stream.flow["A"].value == 3.0


def test_specify_mass_unknown_name_raises(mass_stream: Stream) -> None:
    """An unknown name is rejected before anything is fixed."""
    with pytest.raises(KeyError, match="'C'"):
        mass_stream.specify_mass(A=1.0, C=1.0)

    assert mass_stream.flow["A"].fixed is False


# --- unspecify() ------------------------------------------------------------


def test_unspecify_named(stream: Stream) -> None:
    """unspecify("A") unfixes only A and keeps its value as a guess."""
    stream.specify(A=2.0, B=1.0)

    stream.unspecify("A")

    assert stream.flow["A"].fixed is False
    assert stream.flow["A"].value == 2.0
    assert stream.flow["B"].fixed is True


def test_unspecify_all(stream: Stream) -> None:
    """unspecify() without names unfixes every component."""
    stream.specify(A=2.0, B=1.0)

    stream.unspecify()

    assert not any(var.fixed for var in stream.variables())


def test_unspecify_unknown_name_raises(stream: Stream) -> None:
    """An unknown name is rejected before anything is unfixed."""
    stream.specify(A=2.0)

    with pytest.raises(KeyError, match="'C'"):
        stream.unspecify("A", "C")

    assert stream.flow["A"].fixed is True
