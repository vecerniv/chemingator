"""Tests for chemingator.units.mixer."""

import math
from typing import NamedTuple

import pytest

from chemingator.core.port import PortKind
from chemingator.core.stream import Stream
from chemingator.core.variable import current_value
from chemingator.exceptions import ChemingatorError
from chemingator.exceptions import ConnectivityError
from chemingator.flowsheet import Flowsheet
from chemingator.units.mixer import Mixer

# --- Fixtures ---------------------------------------------------------------


class MixedLine(NamedTuple):
    """Two feeds -> Mixer -> product, all connected."""

    fs: Flowsheet
    mixer: Mixer
    feed1: Stream
    feed2: Stream
    product: Stream


@pytest.fixture(name="line")
def fixture_line() -> MixedLine:
    """A 2-inlet mixer over components "A" and "B", fully connected.

    Free variables: 3 streams x 2 components = 6. Equations: 2.
    """
    fs = Flowsheet(["A", "B"])
    mixer = fs.add_unit(Mixer("M1", n_inlets=2))
    feed1 = fs.add_stream("F1")
    feed2 = fs.add_stream("F2")
    product = fs.add_stream("P")
    fs.connect(feed1, mixer.inlet[0])
    fs.connect(feed2, mixer.inlet[1])
    fs.connect(mixer.outlet, product)
    return MixedLine(fs, mixer, feed1, feed2, product)


# --- Construction -----------------------------------------------------------


def test_mixer_ports() -> None:
    """n inlets named in0..in{n-1} and one outlet named out."""
    mixer = Mixer("M1", n_inlets=3)

    assert [p.name for p in mixer.inlet] == ["in0", "in1", "in2"]
    assert all(p.kind is PortKind.INLET for p in mixer.inlet)
    assert mixer.outlet.name == "out"
    assert mixer.outlet.kind is PortKind.OUTLET
    assert mixer.ports() == [*mixer.inlet, mixer.outlet]


def test_mixer_default_two_inlets() -> None:
    """Without n_inlets, a mixer has two inlets."""
    assert len(Mixer("M1").inlet) == 2


def test_mixer_one_inlet_allowed() -> None:
    """A single-inlet mixer is a valid pass-through."""
    assert len(Mixer("M1", n_inlets=1).inlet) == 1


def test_mixer_no_inlets_raises() -> None:
    """A mixer needs at least one inlet."""
    with pytest.raises(ValueError, match="'M1'"):
        Mixer("M1", n_inlets=0)


def test_mixer_has_no_internal_variables() -> None:
    """A mixer is described by its streams alone."""
    assert not Mixer("M1").internal_variables()


# --- n_equations() ----------------------------------------------------------


def test_n_equations_one_per_component(line: MixedLine) -> None:
    """One component balance per component."""
    assert line.mixer.n_equations() == 2


def test_n_equations_outside_flowsheet_raises() -> None:
    """Without a flowsheet the component count is unknown."""
    with pytest.raises(ChemingatorError, match="'M1'"):
        Mixer("M1").n_equations()


# --- residuals() ------------------------------------------------------------


def test_residuals_zero_for_consistent_state(line: MixedLine) -> None:
    """Residuals vanish when the outlet is the sum of the inlets."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)
    line.product.specify(A=4.0, B=6.0)

    residuals = line.mixer.residuals(current_value, math)

    assert residuals == pytest.approx([0.0, 0.0])
    assert len(residuals) == line.mixer.n_equations()


def test_residuals_are_in_minus_out(line: MixedLine) -> None:
    """Each residual is sum(in[c]) - out[c], in component order."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)
    line.product.specify(A=3.0, B=7.0)

    residuals = line.mixer.residuals(current_value, math)

    assert residuals == pytest.approx([1.0, -1.0])


def test_residuals_unconnected_port_raises() -> None:
    """A mixer with a dangling port cannot write its balances."""
    fs = Flowsheet(["A"])
    mixer = fs.add_unit(Mixer("M1", n_inlets=2))
    fs.connect(fs.add_stream("F1"), mixer.inlet[0])
    fs.connect(mixer.outlet, fs.add_stream("P"))

    with pytest.raises(ConnectivityError, match="M1.in1"):
        mixer.residuals(current_value, math)


# --- initialize() -----------------------------------------------------------


def test_initialize_guesses_outlet(line: MixedLine) -> None:
    """Each unfixed outlet flow is guessed as the sum of inlet flows."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)

    line.mixer.initialize()

    assert line.product.flow["A"].value == pytest.approx(4.0)
    assert line.product.flow["B"].value == pytest.approx(6.0)
    assert line.product.flow["A"].fixed is False


def test_initialize_keeps_fixed_outlet(line: MixedLine) -> None:
    """A specified outlet flow is never overwritten."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)
    line.product.specify(A=9.0)

    line.mixer.initialize()

    assert line.product.flow["A"].value == 9.0
    assert line.product.flow["B"].value == pytest.approx(6.0)


def test_initialize_skips_component_with_unset_inlet(
    line: MixedLine,
) -> None:
    """A component is skipped if any of its inlet flows is unknown."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0)

    line.mixer.initialize()

    assert line.product.flow["A"].value == pytest.approx(4.0)
    assert line.product.flow["B"].value is None


# --- In a flowsheet ---------------------------------------------------------


def test_dof_with_both_feeds_specified(line: MixedLine) -> None:
    """6 unknowns - 2 balances: specifying both feeds gives DOF = 0."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)

    assert line.fs.check_dof().dof == 0


def test_flowsheet_residuals_include_mixer(line: MixedLine) -> None:
    """The flowsheet collects the mixer's balances."""
    line.feed1.specify(A=1.0, B=2.0)
    line.feed2.specify(A=3.0, B=4.0)
    line.product.specify(A=4.0, B=6.0)

    assert line.fs.residuals(current_value, math) == pytest.approx([0.0, 0.0])
