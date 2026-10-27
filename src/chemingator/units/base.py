"""Base class for unit operations."""

from __future__ import annotations

import abc
from typing import Any

from chemingator import exceptions
from chemingator.core import expression
from chemingator.core import port
from chemingator.core import stream as cg_stream
from chemingator.core import variable


class Unit(abc.ABC):
    """A unit operation contributing residual equations.

    Subclasses create ports in __init__, declare internal variables and
    implement `residuals` and `n_equations`. Balances are written as
    'in - out + source - accumulation = 0'.

    Attributes:
        name: Unique unit name.
        inlets: Inlet ports in declaration order.
        outlets: Outlet ports in declaration order.
        flowsheet: Owning flowsheet, set by Flowsheet.add_unit().
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.inlets: list[port.Port] = []
        self.outlets: list[port.Port] = []
        self.flowsheet: Any = None
        self._internal: list[variable.Variable] = []

    def _add_inlet(self, name: str) -> port.Port:
        """Creates an inlet port, registers it and returns it.

        Raises:
            ValueError: If the unit already has a port callen `name`.
        """
        self._check_port_names(name)
        inlet = port.Port(self, name, port.PortKind.INLET)
        self.inlets.append(inlet)
        return inlet

    def _add_outlet(self, name: str) -> port.Port:
        """Creates an outlet port, registers it and returns it.

        Raises:
            ValueError: If the unit already has a port callen `name`.
        """
        self._check_port_names(name)
        outlet = port.Port(self, name, port.PortKind.OUTLET)
        self.outlets.append(outlet)
        return outlet

    def _check_port_names(self, name: str) -> None:
        if any(p.name == name for p in self.ports()):
            raise ValueError(f"Unit {self.name!r} already has a port {name!r}.")

    def _add_variable(
        self, local_name: str, **kwargs: Any
    ) -> variable.Variable:
        """Creates a variable, registers it and returns it."""
        var = variable.Variable(f"{self.name}.{local_name}", **kwargs)
        self._internal.append(var)
        return var

    def _component_names(self) -> list[str]:
        """Returns the flowsheet's component names in order.

        Raises:
            ChemingatorError: If the unit is not in a flowsheet yet.
        """
        if self.flowsheet is None:
            raise exceptions.ChemingatorError(
                f"Unit {self.name!r} is not in a flowsheet. "
                "Call Flowsheet.add_unit() first."
            )
        names: list[str] = self.flowsheet.components.names()
        return names

    def _stream(self, p: port.Port) -> cg_stream.Stream:
        """Returns the stream attached to one of this unit's ports.

        Raises:
            ConnectivityError: If no stream is attached.
        """
        if p.stream is None:
            raise exceptions.ConnectivityError(
                f"Port {p.label!r} is not connected."
            )
        return p.stream

    def internal_variables(self) -> list[variable.Variable]:
        """Returns variables owned by the unit."""
        return [*self._internal]

    def ports(self) -> list[port.Port]:
        """Returns all ports, inlets first."""
        return [*self.inlets, *self.outlets]

    @abc.abstractmethod
    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        """Return residuals, each zero at the solution.

        Uses only arithmetic operators and 'ops' functions.

        Args:
            val: Maps each variable to a float, symbol, etc.
            ops: Namespace providing operations like exp, log, ...
        """

    @abc.abstractmethod
    def n_equations(self) -> int:
        """Returns the number of residual equations.

        Stated as a formula per unit, so the DOF check needs no expression.
        """

    def initialize(self) -> None:
        """Sets initial guesses for outlet/internal from inlets.

        Default does nothing, subclasses may override.
        """
