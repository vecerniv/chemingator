"""Mixer unit."""

from __future__ import annotations

from typing import override

from chemingator.core import expression
from chemingator.core import port
from chemingator.units import base


class Mixer(base.Unit):
    """Combines n inlets into one outlet.

    Residuals, per component `c`:

        sum_i in_i[c] - out[c] = 0

    Attributes:
        inlet: Inlet ports "in0".."in{n-1}".
        outlet: Outlet port "out".
    """

    def __init__(self, name: str, n_inlets: int = 2) -> None:
        """Initializes the mixer.

        Args:
            name: Unique unit name.
            n_inlets: Number of inlets, at least 1.

        Raises:
            ValueError: If `n_inlets` is less than 1.
        """
        if n_inlets < 1:
            raise ValueError(
                f"Mixer {name!r} needs at least 1 inlet, received {n_inlets}."
            )
        super().__init__(name)

        self.inlet: list[port.Port] = [
            self._add_inlet(f"in{i}") for i in range(n_inlets)
        ]
        self.outlet: port.Port = self._add_outlet("out")

    @override
    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del ops  # Unused: mass balances are linear.

        inlets = [self._stream(p) for p in self.inlet]
        outlet = self._stream(self.outlet)
        res: list[expression.Scalar] = []

        for c in self._component_names():
            total_in: expression.Scalar = 0.0
            for s in inlets:
                total_in += val(s.flow[c])
            res.append(total_in - val(outlet.flow[c]))
        return res

    @override
    def n_equations(self) -> int:
        return len(self._component_names())

    @override
    def initialize(self) -> None:
        """Guesses each unfixed outlet flow as the sum of the inlet flows.

        Skips a component if any inlet flow has no value yet.
        """
        inlets = [self._stream(p) for p in self.inlet]
        outlet = self._stream(self.outlet)

        for c in self._component_names():
            values = [s.flow[c].value for s in inlets]
            out_var = outlet.flow[c]
            if out_var.fixed or any(v is None for v in values):
                continue
            out_var.value = sum(v for v in values if v is not None)
