"""Splitter unit."""

from __future__ import annotations

from typing import override

from chemingator.core import expression
from chemingator.core import port
from chemingator.core import variable
from chemingator.units import base


class Splitter(base.Unit):
    """Divides one inlet into n outlets of identical composition.

    Internal variables:
        split[i]: Fraction of the inlet sent to out{i} (-), in [0, 1].

    Residuals:

        sum_i split[i] - 1 = 0
        split[i] * in[c] - out_j[c] = 0

    Attributes:
        inlet: Inlet port "in".
        outlet: Outlet ports "out0".."out{n-1}".
        split: Split fraction variables, one per outlet
    """

    def __init__(self, name: str, n_outlets: int = 2) -> None:
        """Initializes the splitter.

        Args:
            name: Unique unit name.
            n_outlets: Number of outlets, at least one.

        Raises:
            ValueError: If `n_outlets` is less than 1.
        """
        if n_outlets < 1:
            raise ValueError(
                f"Splitter {name!r} needs at least 1 outlet, received "
                f"{n_outlets}."
            )

        super().__init__(name)

        self.inlet: port.Port = self._add_inlet("in")
        self.outlet: list[port.Port] = [
            self._add_outlet(f"out{i}") for i in range(n_outlets)
        ]
        self.split: list[variable.Variable] = [
            self._add_variable(
                f"split[{i}]",
                value=1.0 / n_outlets,
                lower=0.0,
                upper=1.0,
                units="-",
            )
            for i in range(n_outlets)
        ]

    @override
    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del ops  # Unused: no nonlinear functions.

        inlet = self._stream(self.inlet)
        outlets = [self._stream(p) for p in self.outlet]

        split_sum: expression.Scalar = 0.0
        for s in self.split:
            split_sum += val(s)

        res: list[expression.Scalar] = [split_sum - 1.0]
        for frac, out in zip(self.split, outlets, strict=True):
            for c in self._component_names():
                res.append(val(frac) * val(inlet.flow[c]) - val(out.flow[c]))
        return res

    @override
    def n_equations(self) -> int:
        return 1 + len(self.outlet) * len(self._component_names())

    @override
    def initialize(self) -> None:
        """Guesses each unfixed outlet flow as split[i] * inlet flow.

        Skips a component if the inlet flow has no value yet.
        """
        inlet = self._stream(self.inlet)
        outlets = [self._stream(p) for p in self.outlet]

        for frac, out in zip(self.split, outlets, strict=True):
            if frac.value is None:
                continue
            for c in self._component_names():
                in_value = inlet.flow[c].value
                out_var = out.flow[c]
                if out_var.fixed or in_value is None:
                    continue
                out_var.value = frac.value * in_value
