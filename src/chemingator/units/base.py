"""Base class for unit operations."""

from __future__ import annotations

import abc
from typing import Any

from chemingator.core import expression
from chemingator.core import port
from chemingator.core import variable


class Unit(abc.ABC):
    """A unit operation contributing residual equations.

    Subclasses create ports in __init__, declare internal variables and
    implement `residuals` and `n_equations`. Balances are written as
    'in - out + source - accumulation = 0'.

    Attributes:
        name: Unique unit name.
        inlets: Inlet ports in declaration order.
        outlets" Outlet ports in declaration order.
        flowsheet: Owning flowsheer, set by Flowsheet.add_unit().
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.inlets: list[port.Port] = []
        self.outlets: list[port.Port] = []
        self.flowsheet: Any = None
        self._internal: list[variable.Variable] = []

    def _add_inlet(self, name: str) -> port.Port:
        """Creates an inlet port, registers it and returns it."""
        inlet = port.Port(self, name, port.PortKind.INLET)
        self.inlets.append(inlet)
        return inlet

    def _add_outlet(self, name: str) -> port.Port:
        """Creates an outlet port, registers it and returns it."""
        outlet = port.Port(self, name, port.PortKind.OUTLET)
        self.outlets.append(outlet)
        return outlet

    def _add_variable(
        self, local_name: str, **kwargs: Any
    ) -> variable.Variable:
        """Creates a variable named f'{self.name}.{local_name}', registers it
        and returns it."""
        var = variable.Variable(f"{self.name}.{local_name}", **kwargs)
        self._internal.append(var)
        return var

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
            ops: Namespace providing operation like exp, log, ...
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
