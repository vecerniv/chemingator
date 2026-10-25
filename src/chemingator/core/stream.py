"""Material stream. Connects to unit ports and system input/output."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import math

from chemingator import exceptions
from chemingator.core import component
from chemingator.core import expression
from chemingator.core import port
from chemingator.core import variable


class Stream:
    """A material stream holding per-component molar flows.

    Internal state is always molar. Allows user to specify mass-basis input,
    which is internally converted into molar flow.

    Attributes:
        name: Unique stream name.
        flow: Component name -> molar flow variable (mol/s)
        source: Outlet port feeding this stream. None for system input.
        destination: Inlet port recieveing this stream. None for system output.
    """

    def __init__(self, name: str, components: component.ComponentList) -> None:
        self.name = name
        self._components = components
        self.flow: dict[str, variable.Variable] = {
            c: variable.Variable(f"{name}.flow[{c}]", units="mol/s")
            for c in components.names()
        }
        self.source: port.Port | None = None
        self.destination: port.Port | None = None

    def variables(self) -> list[variable.Variable]:
        """Returns all variables of the stream in component order."""
        return [*self.flow.values()]

    def total_flow(self, val: expression.Resolver) -> expression.Scalar:
        """Return the total molar flow in the resolver's representation.

        Args:
            val: Maps each variable to a float, symbol, etc.
        """
        total: expression.Scalar = 0.0
        for var in self.flow.values():
            total += val(var)
        return total

    def molar_fraction(
        self, name: str, val: expression.Resolver
    ) -> expression.Scalar:
        """Returns flow[name] / total flow.

        Args:
            name: Component name.
            val: Maps each variable to a float, symbol, etc.
        """
        return val(self.flow[name]) / self.total_flow(val)

    def specify(
        self, flows: Mapping[str, float] | None = None, /, **kwargs: float
    ) -> None:
        """Fixes component molar flows.

        Usage: specify(A=10.0, B=5.0) or specify({"N2": 3.0}).

        Args:
            flows: Component name -> molar flow in mol/s.
            **kwargs: Same, for names that are valied identifiers.

        Raises:
            KeyError: If a name is not a component of the flowsheet.
        """
        molar_flows = {**(flows or {}), **kwargs}
        self._check_names(molar_flows)
        for name, molar_flow in molar_flows.items():
            self.flow[name].fix(molar_flow)

    def specify_mass(
        self, flows: Mapping[str, float] | None = None, /, **kwargs: float
    ) -> None:
        """Fixes component flows on a given mass basis.

        Each mass flow in converted with the component's molar mass.

        Usage: specify(A=10.0, B=5.0) or specify({"N2": 3.0}).

        Args:
            flows: Component name -> mass flow in kg/s.
            **kwargs: Same, for names that are valied identifiers.

        Raises:
            KeyError: If a name is not a component of the stream.
            BasisError: If a component has no molar mass, or it's molar flow
                is already fixed to an different value.
        """
        mass_flows = {**(flows or {}), **kwargs}
        self._check_names(mass_flows)
        molar_flows: dict[str, float] = {}
        for name, mass_flow in mass_flows.items():
            molar_mass = self._components[name].molar_mass

            if molar_mass is None:
                raise exceptions.BasisError(
                    f"Component {name!r} has no `molar_mass` assigned."
                )
            molar_flow = mass_flow / molar_mass
            var = self.flow[name]
            if (
                var.fixed
                and var.value is not None
                and not math.isclose(molar_flow, var.value)
            ):
                raise exceptions.BasisError(
                    f"Mass flow of {name!r} gives {molar_flow!r} mol/s, but "
                    f"the molar flow is already fixed to {var.value!r} mol/s."
                )
            molar_flows[name] = molar_flow
        self.specify(molar_flows)

    def unspecify(self, *names: str) -> None:
        """Unfixes component flows, keeping their values as guesses.

        Args:
            *names: Component names, none unfixes all components.

        Raises:
            KeyError: If a name is not a component of the stream.
        """
        targets = names or tuple(self.flow)
        self._check_names(targets)
        for name in targets:
            self.flow[name].unfix()

    def _check_names(self, flows: Iterable[str]) -> None:
        unknown = [name for name in flows if name not in self.flow]
        if unknown:
            raise KeyError(f"Not a components of {self.name!r}: {unknown!r}.")
