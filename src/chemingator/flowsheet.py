"""Flowsheet: owns units and streams, assembles the problem."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
import dataclasses

from chemingator import exceptions
from chemingator.core import component
from chemingator.core import expression
from chemingator.core import port
from chemingator.core import stream as cg_stream
from chemingator.core import variable
from chemingator.properties import base as cg_properties
from chemingator.units import base as cg_units


@dataclasses.dataclass
class DofReport:
    """Result of a degrees of freedom analysis.

    Attributes:
        n_unknowns: Number of unfixed variables.
        n_equations: Number of residual equations.
    """

    n_unknowns: int
    n_equations: int

    @property
    def dof(self) -> int:
        """Degrees of freedom: unknowns minus equations."""
        return self.n_unknowns - self.n_equations


class Flowsheet:
    """A block flow diagram: units connected by streams.

    Attributes:
        components: Components shared by all streams.
        property_package: Property package or None.
        units: Unit name -> unit.
        streams: Stream name -> stream.
        constraints: Constraint name -> user specification equation.
    """

    def __init__(
        self,
        components: Sequence[str | component.Component],
        property_package: cg_properties.PropertyPackage | None = None,
    ) -> None:
        self.components = component.ComponentList(components)
        self.property_package = property_package
        self.units: dict[str, cg_units.Unit] = {}
        self.streams: dict[str, cg_stream.Stream] = {}
        self.constraints: dict[str, expression.Constraint] = {}

    def add_unit[UnitT: cg_units.Unit](self, unit: UnitT) -> UnitT:
        """Registers a unit and sets its `flowsheet`.

        Raises:
            ValueError: If the name is already used.
        """
        if unit.name in self.units:
            raise ValueError(f"Duplicate unit name: {unit.name!r}")
        unit.attach(self)
        self.units[unit.name] = unit
        return unit

    def add_stream(self, name: str) -> cg_stream.Stream:
        """Creates and returns a stream with unfixed flows.

        Raises:
            ValueError: If the name is already used.
        """
        if name in self.streams:
            raise ValueError(f"Duplicate stream name: {name!r}")
        stream = cg_stream.Stream(name, self.components)
        self.streams[name] = stream
        return stream

    def connect(
        self,
        start: cg_stream.Stream | port.Port,
        end: port.Port | cg_stream.Stream,
        name: str | None = None,
    ) -> cg_stream.Stream:
        """Connects a stream or outlet port to an inlet port or stream.

        Accepted forms:
            (stream, inlet) for feed,
            (outlet, inlet) for an internal stream,
            (outlet, stream) for a product.

        Args:
            start: Upstream stream or outlet port.
            end: Downstream inlet port or stream.
            name: Name for a newly created internal stream.

        Returns:
            The stream joining both ends.

        Raises:
            ConnectivityError: If port has the wrong kind, a port or stream
                end is taken, or an object belongs to another flowsheet.
            ValueError: If the internal stream's name is already used.
        """
        match start, end:
            case cg_stream.Stream() as feed, port.Port() as inlet:
                self._check_stream(feed, free_end="destination")
                self._check_port(inlet, port.PortKind.INLET)
                stream, ports = feed, [inlet]
            case port.Port() as outlet, cg_stream.Stream() as product:
                self._check_port(outlet, port.PortKind.OUTLET)
                self._check_stream(product, free_end="source")
                stream, ports = product, [outlet]
            case port.Port() as outlet, port.Port() as inlet:
                self._check_port(outlet, port.PortKind.OUTLET)
                self._check_port(inlet, port.PortKind.INLET)
                stream = self.add_stream(
                    name or f"{outlet.label}->{inlet.label}"
                )
                ports = [outlet, inlet]
            case _:
                raise exceptions.ConnectivityError(
                    f"Cannot connect {start!r} to {end!r}: at least one end "
                    "must be a port."
                )

        for p in ports:
            p.attach(stream)

        return stream

    def _check_port(self, p: port.Port, kind: port.PortKind) -> None:
        if p.unit.flowsheet is not self:
            raise exceptions.ConnectivityError(
                f"Port {p.label!r} belongs to a unit not in this flowsheet."
            )
        if p.kind is not kind:
            raise exceptions.ConnectivityError(
                f"Port {p.label!r} is an {p.kind.value}. "
                f"Expected an {kind.value}."
            )
        if p.connected:
            raise exceptions.ConnectivityError(
                f"Port {p.label!r} is already connected."
            )

    def _check_stream(self, s: cg_stream.Stream, free_end: str) -> None:
        if self.streams.get(s.name) is not s:
            raise exceptions.ConnectivityError(
                f"Stream {s.name!r} is not in this flowsheet."
            )
        if getattr(s, free_end) is not None:
            raise exceptions.ConnectivityError(
                f"Stream {s.name!r} already has a {free_end} port."
            )

    def add_constraint(
        self, name: str, constraint: expression.Constraint
    ) -> None:
        """Adds a user specification equation, zero at the solution.

        Use to specify derived quantities that are not variables, e.g.
        a product mole fraction or a total flow. Each constraint adds one
        equation, so one more variable must be left unfixed.

        Example:
        Require x_A = 0.8 in product stream S3. `val` and `ops` are supplied
        by the caller of `residuals()`, not by the user.
        Define a residual equation which equals zero, such as:

            s3 = fs.add_stream("S3")
            ...
            def x_a_spec(val, ops):
                return val(s3.flow["A"]) - 0.8 * s3.total_flow(val)
            fs.add_constraint("S3.x[A]", x_a_spec)

        Args:
            name: Unique name, shown in DOF and solver reports.
            constraint: Callable (val, ops) -> Scalar, written like
                Unit.residuals but returning a single residual.

        Raises:
            TypeError: If `constraint` is not callable.
            ValueError: If the name is already used.
        """
        if not callable(constraint):
            raise TypeError(
                f"Constraint {name!r} must be callable (val, ops) -> Scalar, "
                f"got {type(constraint).__name__}."
            )
        if name in self.constraints:
            raise ValueError(f"Duplicate constraint name: {name!r}")
        self.constraints[name] = constraint

    def validate(self) -> None:
        """Checks that every port and stream is connected.

        Raises:
            ConnectivityError: If a port or a stream is dangling.
        """
        dangling_ports = [p.label for p in self._ports() if not p.connected]
        orphan_streams = [
            s.name
            for s in self.streams.values()
            if s.source is None and s.destination is None
        ]
        problems = []
        if dangling_ports:
            problems.append(f"unconnected ports {dangling_ports!r}")
        if orphan_streams:
            problems.append(f"streams attached to nothing {orphan_streams!r}")
        if problems:
            raise exceptions.ConnectivityError(
                f"Invalid flowsheet: {"; ".join(problems)}."
            )

    def _ports(self) -> Iterator[port.Port]:
        for unit in self.units.values():
            yield from unit.ports()

    def variables(self) -> list[variable.Variable]:
        """Returns stream and unit variables in deterministic order."""
        variables = []
        for stream in self.streams.values():
            variables.extend(stream.variables())
        for unit in self.units.values():
            variables.extend(unit.internal_variables())

        return variables

    def free_variables(self) -> list[variable.Variable]:
        """Returns the unfixed variables."""
        return [v for v in self.variables() if not v.fixed]

    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        """Returns unit residuals, then constraints, in deterministic order.

        Order: units in insertion order, each unit's residuals in its own
        order, then constraints in insertion order.

        Args:
            val: Maps each variable to a float, symbol, etc.
            ops: Namespace providing operations like exp, log, ...

        Returns:
            One residual per equation, sum(Unit.n_equations) +
            len(constraints) in total.

        Raises:
            ChemingatorError: If a unit returns a number of residuals
                different from its `n_equations()`.
        """
        res: list[expression.Scalar] = []
        for unit in self.units.values():
            unit_res = unit.residuals(val, ops)
            if len(unit_res) != unit.n_equations():
                raise exceptions.ChemingatorError(
                    f"Unit {unit.name!r} returned {len(unit_res)} residuals "
                    f"but declares {unit.n_equations()} equations."
                )
            res.extend(unit_res)

        for constraint in self.constraints.values():
            res.append(constraint(val, ops))

        return res

    def check_dof(self, raise_on_error: bool = True) -> DofReport:
        """Runs the degree of freedom analysis.

        Counts equations with Unit.n_equations plus one per constraint.

        Args:
            raise_on_error: Raise instead of returning when DOF != 0.

        Raises:
            DegreesOfFreedomError: If DOF != 0 and `raise_on_error`.
        """
        variables = len(self.free_variables())
        eqs: int = 0
        for unit in self.units.values():
            eqs += unit.n_equations()
        eqs += len(self.constraints)

        dof_rep = DofReport(variables, eqs)
        dof = dof_rep.dof
        if dof != 0 and raise_on_error:
            raise exceptions.DegreesOfFreedomError(
                f"Flowsheet has non-zero degrees of freedom: {dof}."
            )

        return dof_rep

    def feeds(self) -> list[cg_stream.Stream]:
        """Returns system feed streams."""
        return [s for s in self.streams.values() if s.source is None]

    def products(self) -> list[cg_stream.Stream]:
        """Returns system product streams."""
        return [p for p in self.streams.values() if p.destination is None]
