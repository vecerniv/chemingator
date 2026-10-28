"""Tests for chemingator.units.splitter."""

import math
from typing import NamedTuple

import pytest

from chemingator.core.port import PortKind
from chemingator.core.stream import Stream
from chemingator.core.variable import current_value
from chemingator.exceptions import ChemingatorError
from chemingator.exceptions import ConnectivityError
from chemingator.flowsheet import Flowsheet
from chemingator.units.splitter import Splitter

# --- Fixtures ---------------------------------------------------------------


class SplitLine(NamedTuple):
    """One feed -> Splitter -> two products, all connected."""

    fs: Flowsheet
    splitter: Splitter
    feed: Stream
    product1: Stream
    product2: Stream


@pytest.fixture(name="line")
def fixture_line() -> SplitLine:
    """A 2-outlet splitter over components "A" and "B", fully connected.

    Free variables: 3 streams x 2 components + 2 splits = 8.
    Equations: 1 split sum + 2 outlets x 2 components = 5.
    """
    fs = Flowsheet(["A", "B"])
    splitter = fs.add_unit(Splitter("S1", n_outlets=2))
    feed = fs.add_stream("F")
    product1 = fs.add_stream("P1")
    product2 = fs.add_stream("P2")
    fs.connect(feed, splitter.inlet)
    fs.connect(splitter.outlet[0], product1)
    fs.connect(splitter.outlet[1], product2)
    return SplitLine(fs, splitter, feed, product1, product2)


# --- Construction -----------------------------------------------------------


def test_splitter_ports() -> None:
    """One inlet named in and n outlets named out0..out{n-1}."""
    splitter = Splitter("S1", n_outlets=3)

    assert splitter.inlet.name == "in"
    assert splitter.inlet.kind is PortKind.INLET
    assert [p.name for p in splitter.outlet] == ["out0", "out1", "out2"]
    assert all(p.kind is PortKind.OUTLET for p in splitter.outlet)
    assert splitter.ports() == [splitter.inlet, *splitter.outlet]


def test_splitter_default_two_outlets() -> None:
    """Without n_outlets, a splitter has two outlets."""
    assert len(Splitter("S1").outlet) == 2


def test_splitter_one_outlet_allowed() -> None:
    """A single-outlet splitter is a valid pass-through."""
    assert len(Splitter("S1", n_outlets=1).outlet) == 1


def test_splitter_no_outlets_raises() -> None:
    """A splitter needs at least one outlet."""
    with pytest.raises(ValueError, match="'S1'"):
        Splitter("S1", n_outlets=0)


def test_split_variables() -> None:
    """One unfixed split[i] per outlet, registered as internal, in [0, 1]."""
    splitter = Splitter("S1", n_outlets=3)

    assert splitter.internal_variables() == splitter.split
    assert [s.name for s in splitter.split] == [
        "S1.split[0]",
        "S1.split[1]",
        "S1.split[2]",
    ]
    for s in splitter.split:
        assert s.fixed is False
        assert s.lower == 0.0
        assert s.upper == 1.0
        assert s.units == "-"


def test_split_guess_equal_across_outlets() -> None:
    """Each split starts at the guess 1 / n_outlets."""
    splitter = Splitter("S1", n_outlets=4)

    values = [s.value for s in splitter.split]

    assert values == pytest.approx([0.25, 0.25, 0.25, 0.25])


# --- n_equations() ----------------------------------------------------------


@pytest.mark.parametrize(
    "n_outlets, components, expected",
    [(2, ["A", "B"], 5), (3, ["A"], 4), (1, ["A", "B", "C"], 4)],
    ids=["2x2", "3x1", "1x3"],
)
def test_n_equations_one_plus_n_times_components(
    n_outlets: int, components: list[str], expected: int
) -> None:
    """One plus n_outlets times components."""
    fs = Flowsheet(components)
    splitter = fs.add_unit(Splitter("S1", n_outlets=n_outlets))

    assert splitter.n_equations() == expected


def test_n_equations_outside_flowsheet_raises() -> None:
    """Without a flowsheet the component count is unknown."""
    with pytest.raises(ChemingatorError, match="'S1'"):
        Splitter("S1").n_equations()


# --- residuals() ------------------------------------------------------------


def test_residuals_zero_for_consistent_state(line: SplitLine) -> None:
    """Residuals vanish when each outlet is split[i] times the inlet."""
    line.splitter.split[0].fix(0.2)
    line.splitter.split[1].fix(0.8)
    line.feed.specify(A=5.0, B=10.0)
    line.product1.specify(A=1.0, B=2.0)
    line.product2.specify(A=4.0, B=8.0)

    residuals = line.splitter.residuals(current_value, math)

    assert residuals == pytest.approx([0.0, 0.0, 0.0, 0.0, 0.0])
    assert len(residuals) == line.splitter.n_equations()


def test_residuals_values_and_order(line: SplitLine) -> None:
    """Split sum first, then split[i] * in[c] - out_i[c] per outlet."""
    line.splitter.split[0].fix(0.2)
    line.splitter.split[1].fix(0.8)
    line.feed.specify(A=5.0, B=10.0)
    line.product1.specify(A=2.0, B=4.0)
    line.product2.specify(A=4.0, B=8.0)

    residuals = line.splitter.residuals(current_value, math)

    assert residuals == pytest.approx([0.0, -1.0, -2.0, 0.0, 0.0])


def test_residuals_split_sum(line: SplitLine) -> None:
    """The first residual is sum(split) - 1."""
    line.splitter.split[0].fix(0.3)
    line.splitter.split[1].fix(0.3)
    line.feed.specify(A=0.0, B=0.0)
    line.product1.specify(A=0.0, B=0.0)
    line.product2.specify(A=0.0, B=0.0)

    residuals = line.splitter.residuals(current_value, math)

    assert residuals[0] == pytest.approx(-0.4)


def test_residuals_unconnected_port_raises() -> None:
    """A splitter with a dangling port cannot write its balances."""
    fs = Flowsheet(["A"])
    splitter = fs.add_unit(Splitter("S1", n_outlets=2))
    fs.connect(fs.add_stream("F"), splitter.inlet)
    fs.connect(splitter.outlet[0], fs.add_stream("P"))

    with pytest.raises(ConnectivityError, match="S1.out1"):
        splitter.residuals(current_value, math)


# --- initialize() -----------------------------------------------------------


def test_initialize_guesses_outlets(line: SplitLine) -> None:
    """Each unfixed outlet flow is guessed as split[i] times inlet flows."""
    line.splitter.split[0].value = 0.2
    line.splitter.split[1].value = 0.8
    line.feed.specify(A=5.0, B=10.0)

    line.splitter.initialize()

    assert line.product1.flow["A"].value == pytest.approx(1.0)
    assert line.product1.flow["B"].value == pytest.approx(2.0)
    assert line.product2.flow["A"].value == pytest.approx(4.0)
    assert line.product2.flow["B"].value == pytest.approx(8.0)
    assert not any(v.fixed for v in line.product1.variables())


def test_initialize_keeps_fixed_outlet(line: SplitLine) -> None:
    """A specified outlet flow is never overwritten."""
    line.feed.specify(A=1.0, B=2.0)
    line.product1.specify(A=9.0)

    line.splitter.initialize()

    assert line.product1.flow["A"].value == 9.0
    assert line.product1.flow["B"].value == pytest.approx(1.0)


def test_initialize_skips_component_with_unset_inlet(
    line: SplitLine,
) -> None:
    """A component is skipped if any of its inlet flows is unknown."""
    line.feed.specify(A=1.0)

    line.splitter.initialize()

    assert line.product1.flow["A"].value == pytest.approx(0.5)
    assert line.product1.flow["B"].value is None
    assert line.product2.flow["B"].value is None


def test_initialize_skips_outlet_with_unset_split(line: SplitLine) -> None:
    """An outlet is skipped if its split fraction is unknown."""
    line.splitter.split[1].value = None
    line.feed.specify(A=1.0, B=2.0)

    line.splitter.initialize()

    assert line.product1.flow["A"].value == pytest.approx(0.5)
    assert line.product2.flow["A"].value is None


# --- In a flowsheet ---------------------------------------------------------


def test_dof_feed_only_is_under_specified(line: SplitLine) -> None:
    """Feed alone leaves the split open: 8 - 2 specs - 5 eqs = +1."""
    line.feed.specify(A=1.0, B=2.0)

    assert line.fs.check_dof(raise_on_error=False).dof == 1


def test_dof_feed_and_one_split(line: SplitLine) -> None:
    """With n outlets, n - 1 splits are free, the sum fixes the last."""
    line.feed.specify(A=1.0, B=2.0)
    line.splitter.split[0].fix(0.2)

    assert line.fs.check_dof().dof == 0


def test_dof_feed_and_one_product_flow(line: SplitLine) -> None:
    """A product flow can replace the split specification."""
    line.feed.specify(A=1.0, B=2.0)
    line.product1.specify(A=0.2)

    assert line.fs.check_dof().dof == 0


def test_dof_all_splits_fixed_is_over_specified(line: SplitLine) -> None:
    """Fixing every split over-specifies, even if they sum to 1."""
    line.feed.specify(A=1.0, B=2.0)
    line.splitter.split[0].fix(0.2)
    line.splitter.split[1].fix(0.8)

    assert line.fs.check_dof(raise_on_error=False).dof == -1


def test_flowsheet_residuals_include_splitter(line: SplitLine) -> None:
    """The flowsheet collects the splitter's balances."""
    line.feed.specify(A=1.0, B=2.0)
    line.product1.specify(A=0.5, B=1.0)
    line.product2.specify(A=0.5, B=1.0)

    assert line.fs.residuals(current_value, math) == pytest.approx(
        [0.0, 0.0, 0.0, 0.0, 0.0]
    )
