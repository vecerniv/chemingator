"""Tests for chemingator.flowsheet."""

from collections.abc import Sequence
import math
from typing import NamedTuple

import pytest

from chemingator.core import expression
from chemingator.core.stream import Stream
from chemingator.core.variable import current_value
from chemingator.exceptions import ChemingatorError
from chemingator.exceptions import ConnectivityError
from chemingator.exceptions import DegreesOfFreedomError
from chemingator.flowsheet import DofReport
from chemingator.flowsheet import Flowsheet
from chemingator.units.base import Unit

# --- Test doubles and fixtures ----------------------------------------------


class StubUnit(Unit):
    """Unit with chosen ports, internal variables and constant residuals.

    Ports are named in0, in1, ... and out0, out1, ...
    """

    def __init__(
        self,
        name: str,
        n_inlets: int = 1,
        n_outlets: int = 1,
        residual_values: Sequence[float] = (),
        declared_equations: int | None = None,
        internal: Sequence[str] = (),
    ) -> None:
        """Initializes the stub.

        Args:
            name: Unit name.
            n_inlets: Number of inlet ports.
            n_outlets: Number of outlet ports.
            residual_values: What residuals() returns.
            declared_equations: What n_equations() returns; defaults to
                len(residual_values). Set it differently to fake a bug.
            internal: Local names of internal variables to create.
        """
        super().__init__(name)
        for i in range(n_inlets):
            self._add_inlet(f"in{i}")
        for j in range(n_outlets):
            self._add_outlet(f"out{j}")
        for local_name in internal:
            self._add_variable(local_name)
        self._residual_values = list(residual_values)
        self._declared = (
            len(self._residual_values)
            if declared_equations is None
            else declared_equations
        )

    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del val, ops  # Unused: the residuals are constants.
        return list(self._residual_values)

    def n_equations(self) -> int:
        return self._declared


class Line(NamedTuple):
    """Feed -> unit -> product, all connected."""

    fs: Flowsheet
    unit: Unit
    feed: Stream
    product: Stream


@pytest.fixture(name="fs")
def fixture_fs() -> Flowsheet:
    """An empty flowsheet with components "A" and "B"."""
    return Flowsheet(["A", "B"])


@pytest.fixture(name="line")
def fixture_line(fs: Flowsheet) -> Line:
    """A connected feed -> M1 -> product line; M1 declares 2 equations.

    Free variables: 2 feed flows + 2 product flows = 4. Equations: 2.
    So it needs 2 specifications for DOF = 0.
    """
    unit = fs.add_unit(StubUnit("M1", residual_values=[0.0, 0.0]))
    feed = fs.add_stream("F")
    product = fs.add_stream("P")
    fs.connect(feed, unit.inlets[0])
    fs.connect(unit.outlets[0], product)
    return Line(fs, unit, feed, product)


# --- DofReport --------------------------------------------------------------


@pytest.mark.parametrize(
    "n_unknowns, n_equations, dof",
    [(4, 4, 0), (5, 4, 1), (3, 4, -1)],
    ids=["exact", "under", "over"],
)
def test_dof_report(n_unknowns: int, n_equations: int, dof: int) -> None:
    """DOF is unknowns minus equations."""
    assert DofReport(n_unknowns, n_equations).dof == dof


# --- Construction and registration ------------------------------------------


def test_flowsheet_init(fs: Flowsheet) -> None:
    """A new flowsheet has its components and nothing else."""
    assert fs.components.names() == ["A", "B"]
    assert fs.property_package is None
    assert not fs.units
    assert not fs.streams
    assert not fs.constraints


def test_add_unit(fs: Flowsheet) -> None:
    """add_unit registers the unit, sets its owner and returns it."""
    unit = StubUnit("M1")

    returned = fs.add_unit(unit)

    assert returned is unit
    assert fs.units == {"M1": unit}
    assert unit.flowsheet is fs


def test_add_unit_duplicate_name_raises(fs: Flowsheet) -> None:
    """A second unit with the same name is rejected, the first stays."""
    first = fs.add_unit(StubUnit("M1"))
    second = StubUnit("M1")

    with pytest.raises(ValueError, match="'M1'"):
        fs.add_unit(second)

    assert fs.units["M1"] is first
    assert second.flowsheet is None


def test_add_stream(fs: Flowsheet) -> None:
    """add_stream creates an unconnected stream over the components."""
    stream = fs.add_stream("F")

    assert fs.streams == {"F": stream}
    assert list(stream.flow) == ["A", "B"]
    assert stream.source is None
    assert stream.destination is None


def test_add_stream_duplicate_name_raises(fs: Flowsheet) -> None:
    """A second stream with the same name is rejected, the first stays."""
    first = fs.add_stream("F")

    with pytest.raises(ValueError, match="'F'"):
        fs.add_stream("F")

    assert fs.streams["F"] is first


def test_add_constraint(fs: Flowsheet) -> None:
    """add_constraint stores the callable under its name."""

    def spec(val: expression.Resolver, ops: expression.MathOps) -> float:
        del val, ops
        return 0.0

    fs.add_constraint("spec", spec)

    assert fs.constraints == {"spec": spec}


def test_add_constraint_not_callable_raises(fs: Flowsheet) -> None:
    """A constraint must be a function, not e.g. a number."""
    with pytest.raises(TypeError, match="'spec'"):
        fs.add_constraint("spec", 0.8)

    assert not fs.constraints


def test_add_constraint_duplicate_name_raises(fs: Flowsheet) -> None:
    """A second constraint with the same name is rejected."""
    fs.add_constraint("spec", lambda val, ops: 0.0)

    with pytest.raises(ValueError, match="'spec'"):
        fs.add_constraint("spec", lambda val, ops: 1.0)


# --- connect(): accepted forms ----------------------------------------------


def test_connect_feed(fs: Flowsheet) -> None:
    """(stream, inlet) makes the stream feed the inlet."""
    unit = fs.add_unit(StubUnit("M1"))
    feed = fs.add_stream("F")

    returned = fs.connect(feed, unit.inlets[0])

    assert returned is feed
    assert feed.destination is unit.inlets[0]
    assert unit.inlets[0].stream is feed


def test_connect_product(fs: Flowsheet) -> None:
    """(outlet, stream) makes the outlet feed the stream."""
    unit = fs.add_unit(StubUnit("M1"))
    product = fs.add_stream("P")

    returned = fs.connect(unit.outlets[0], product)

    assert returned is product
    assert product.source is unit.outlets[0]
    assert unit.outlets[0].stream is product


def test_connect_internal_default_name(fs: Flowsheet) -> None:
    """(outlet, inlet) creates and registers a stream named after both."""
    up = fs.add_unit(StubUnit("M1"))
    down = fs.add_unit(StubUnit("M2"))

    stream = fs.connect(up.outlets[0], down.inlets[0])

    assert stream.name == "M1.out0->M2.in0"
    assert fs.streams[stream.name] is stream
    assert stream.source is up.outlets[0]
    assert stream.destination is down.inlets[0]


def test_connect_internal_custom_name(fs: Flowsheet) -> None:
    """An explicit name is used for the internal stream."""
    up = fs.add_unit(StubUnit("M1"))
    down = fs.add_unit(StubUnit("M2"))

    stream = fs.connect(up.outlets[0], down.inlets[0], name="S3")

    assert stream.name == "S3"
    assert fs.streams["S3"] is stream


# --- connect(): rejected forms ----------------------------------------------


def test_connect_wrong_port_kinds_raise(fs: Flowsheet) -> None:
    """Inlet->inlet, outlet->outlet and inlet->outlet are rejected."""
    a = fs.add_unit(StubUnit("M1"))
    b = fs.add_unit(StubUnit("M2"))
    pairs = [
        (a.inlets[0], b.inlets[0]),
        (a.outlets[0], b.outlets[0]),
        (a.inlets[0], b.outlets[0]),
    ]

    for start, end in pairs:
        with pytest.raises(ConnectivityError):
            fs.connect(start, end)

    assert not any(p.connected for p in [*a.ports(), *b.ports()])
    assert not fs.streams


def test_connect_stream_to_outlet_raises(fs: Flowsheet) -> None:
    """A feed stream must enter through an inlet."""
    unit = fs.add_unit(StubUnit("M1"))
    feed = fs.add_stream("F")

    with pytest.raises(ConnectivityError, match="M1.out0"):
        fs.connect(feed, unit.outlets[0])

    assert feed.destination is None


def test_connect_inlet_to_stream_raises(fs: Flowsheet) -> None:
    """A product stream must leave through an outlet."""
    unit = fs.add_unit(StubUnit("M1"))
    product = fs.add_stream("P")

    with pytest.raises(ConnectivityError, match="M1.in0"):
        fs.connect(unit.inlets[0], product)

    assert product.source is None


def test_connect_stream_to_stream_raises(fs: Flowsheet) -> None:
    """At least one end must be a port."""
    feed = fs.add_stream("F")
    product = fs.add_stream("P")

    with pytest.raises(ConnectivityError):
        fs.connect(feed, product)


def test_connect_connected_port_raises(line: Line) -> None:
    """A port that already has a stream is rejected, nothing changes."""
    other = line.fs.add_stream("F2")

    with pytest.raises(ConnectivityError, match="M1.in0"):
        line.fs.connect(other, line.unit.inlets[0])

    assert line.unit.inlets[0].stream is line.feed
    assert other.destination is None


def test_connect_one_stream_to_two_inlets_raises(fs: Flowsheet) -> None:
    """Splitting a stream needs a Splitter, nothing changes."""
    unit = fs.add_unit(StubUnit("M1", n_inlets=2))
    feed = fs.add_stream("F")
    fs.connect(feed, unit.inlets[0])

    with pytest.raises(ConnectivityError, match="'F'"):
        fs.connect(feed, unit.inlets[1])

    assert feed.destination is unit.inlets[0]
    assert unit.inlets[1].stream is None


def test_connect_two_outlets_to_one_stream_raises(fs: Flowsheet) -> None:
    """Merging into a stream needs a Mixer; nothing changes."""
    unit = fs.add_unit(StubUnit("M1", n_outlets=2))
    product = fs.add_stream("P")
    fs.connect(unit.outlets[0], product)

    with pytest.raises(ConnectivityError, match="'P'"):
        fs.connect(unit.outlets[1], product)

    assert product.source is unit.outlets[0]
    assert unit.outlets[1].stream is None


def test_connect_unregistered_unit_raises(fs: Flowsheet) -> None:
    """Ports of a unit not added to this flowsheet are rejected."""
    stray = StubUnit("X1")
    feed = fs.add_stream("F")

    with pytest.raises(ConnectivityError, match="X1.in0"):
        fs.connect(feed, stray.inlets[0])

    assert stray.inlets[0].stream is None


def test_connect_foreign_stream_raises(fs: Flowsheet) -> None:
    """A stream from another flowsheet is rejected, even with a free name."""
    unit = fs.add_unit(StubUnit("M1"))
    foreign = Flowsheet(["A", "B"]).add_stream("F")

    with pytest.raises(ConnectivityError, match="'F'"):
        fs.connect(foreign, unit.inlets[0])

    assert unit.inlets[0].stream is None


def test_connect_internal_duplicate_name_raises(fs: Flowsheet) -> None:
    """A taken stream name fails before any port is attached."""
    up = fs.add_unit(StubUnit("M1"))
    down = fs.add_unit(StubUnit("M2"))
    fs.add_stream("S3")

    with pytest.raises(ValueError, match="'S3'"):
        fs.connect(up.outlets[0], down.inlets[0], name="S3")

    assert up.outlets[0].stream is None
    assert down.inlets[0].stream is None


# --- validate() -------------------------------------------------------------


def test_validate_connected_flowsheet(line: Line) -> None:
    """A fully connected flowsheet passes."""
    line.fs.validate()


def test_validate_reports_all_problems(fs: Flowsheet) -> None:
    """Every dangling port and orphan stream is named in one error."""
    fs.add_unit(StubUnit("M1"))
    fs.add_stream("F")

    with pytest.raises(ConnectivityError) as excinfo:
        fs.validate()

    message = str(excinfo.value)
    assert "M1.in0" in message
    assert "M1.out0" in message
    assert "'F'" in message


# --- variables() and free_variables() ---------------------------------------


def test_variables_order(fs: Flowsheet) -> None:
    """Stream variables come first, then unit internals, in insert order."""
    unit = fs.add_unit(StubUnit("M1", internal=["split[0]"]))
    feed = fs.add_stream("F")
    product = fs.add_stream("P")

    assert fs.variables() == [
        *feed.variables(),
        *product.variables(),
        *unit.internal_variables(),
    ]


def test_free_variables_excludes_fixed(line: Line) -> None:
    """Fixed variables are specifications, not unknowns."""
    line.feed.specify(A=1.0)

    free = line.fs.free_variables()

    assert line.feed.flow["A"] not in free
    assert len(free) == 3


# --- residuals() ------------------------------------------------------------


def test_residuals_order(fs: Flowsheet) -> None:
    """Units in insertion order, then constraints in insertion order."""
    fs.add_unit(StubUnit("M1", residual_values=[1.0, 2.0]))
    fs.add_unit(StubUnit("M2", residual_values=[3.0]))
    fs.add_constraint("c1", lambda val, ops: 4.0)
    fs.add_constraint("c2", lambda val, ops: 5.0)

    assert fs.residuals(current_value, math) == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_residuals_passes_val_and_ops_to_constraints(fs: Flowsheet) -> None:
    """Constraints receive the caller's resolver and ops namespace."""
    received = []

    def spec(val: expression.Resolver, ops: expression.MathOps) -> float:
        received.append((val, ops))
        return 0.0

    fs.add_constraint("spec", spec)

    fs.residuals(current_value, math)

    assert received == [(current_value, math)]


def test_residuals_count_mismatch_raises(fs: Flowsheet) -> None:
    """A unit returning a different count than it declares is a bug."""
    fs.add_unit(StubUnit("M1", residual_values=[0.0], declared_equations=2))

    with pytest.raises(ChemingatorError, match="'M1'"):
        fs.residuals(current_value, math)


# --- check_dof() ------------------------------------------------------------


def test_check_dof_exactly_specified(line: Line) -> None:
    """2 specs for 4 unknowns and 2 equations give DOF = 0."""
    line.feed.specify(A=1.0, B=2.0)

    report = line.fs.check_dof()

    assert report == DofReport(n_unknowns=2, n_equations=2)
    assert report.dof == 0


def test_check_dof_under_specified(line: Line) -> None:
    """One spec missing gives DOF = +1."""
    line.feed.specify(A=1.0)

    assert line.fs.check_dof(raise_on_error=False).dof == 1


def test_check_dof_over_specified(line: Line) -> None:
    """One extra spec gives DOF = -1."""
    line.feed.specify(A=1.0, B=2.0)
    line.product.specify(A=1.0)

    assert line.fs.check_dof(raise_on_error=False).dof == -1


def test_check_dof_raises_when_not_zero(line: Line) -> None:
    """By default a non-zero DOF is an error."""
    with pytest.raises(DegreesOfFreedomError, match="2"):
        line.fs.check_dof()


def test_check_dof_counts_constraints(line: Line) -> None:
    """Each constraint adds one equation, replacing one fixed variable."""
    line.feed.specify(A=1.0)
    line.fs.add_constraint(
        "P.x[A]",
        lambda val, ops: line.product.fraction_residual("A", 0.5, val),
    )

    assert line.fs.check_dof().dof == 0


# --- feeds() and products() -------------------------------------------------


def test_feeds_and_products(fs: Flowsheet) -> None:
    """Feeds have no source, products no destination, internals neither."""
    up = fs.add_unit(StubUnit("M1"))
    down = fs.add_unit(StubUnit("M2"))
    feed = fs.add_stream("F")
    product = fs.add_stream("P")
    fs.connect(feed, up.inlets[0])
    internal = fs.connect(up.outlets[0], down.inlets[0])
    fs.connect(down.outlets[0], product)

    assert fs.feeds() == [feed]
    assert fs.products() == [product]
    assert internal not in fs.feeds() + fs.products()
