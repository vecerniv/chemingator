"""ComponentSeparator unit."""

from __future__ import annotations

from typing import override

from chemingator.core import expression
from chemingator.core import port
from chemingator.core import variable
from chemingator.units import base as cg_base


class ComponentSeparator(cg_base.Unit):
    """
    Splits one inlet into top and bottom by component recovery.

    Internal variables:
        recovery[c]: Fraction of component c sent to top (-), in [0, 1].

    Residuals:

        recovery[c] * top[c] - in[c] = 0
        in[c] - top[c] + bottom[c] = 0

    Attributes:
        inlet: Inlet port "in".
        top: Outlet port "top".
        bottom: Outlet port "bottom".
        recovery: Recovery fraction variables, one per component.
    """

    def __init__(self, name: str) -> None:
        """Initializes the separator.

        Recovery variables depend on the flowsheet's components, so they
        are created when the unit is added to a flowsheet.

        Args:
            name: Unique unit name.
        """
        super().__init__(name)

        self.inlet: port.Port = self._add_inlet("in")
        self.top: port.Port = self._add_outlet("top")
        self.bottom: port.Port = self._add_outlet("bottom")
        self.recovery: dict[str, variable.Variable] = {}

    @override
    def _build(self) -> None:
        """Creates one recovery variable per component, guess 0.5."""
        self.recovery = {
            c: self._add_variable(
                f"recovery[{c}]", value=0.5, lower=0.0, upper=1.0, units="-"
            )
            for c in self._component_names()
        }

    @override
    def residuals(
        self, val: expression.Resolver, ops: expression.MathOps
    ) -> list[expression.Scalar]:
        del ops  # Unused: no nonlinear functions.

        inlet = self._stream(self.inlet)
        top = self._stream(self.top)
        bottom = self._stream(self.bottom)
        names = self._component_names()

        res: list[expression.Scalar] = [
            val(self.recovery[c]) * val(inlet.flow[c]) - val(top.flow[c])
            for c in names
        ]
        res.extend(
            val(inlet.flow[c]) - val(top.flow[c]) - val(bottom.flow[c])
            for c in names
        )

        return res

    @override
    def n_equations(self) -> int:
        return 2 * len(self._component_names())

    @override
    def initialize(self) -> None:
        """Guesses each unfixed outlet flows from recoveries.

        Skips a component if its inlet flow or recovery has no value yet.
        """
        inlet = self._stream(self.inlet)
        top = self._stream(self.top)
        bottom = self._stream(self.bottom)

        for c in self._component_names():
            in_value = inlet.flow[c].value
            rec_value = self.recovery[c].value

            if in_value is None or rec_value is None:
                continue

            top_value = rec_value * in_value
            if not top.flow[c].fixed:
                top.flow[c].value = top_value
            if not bottom.flow[c].fixed:
                bottom.flow[c].value = in_value - top_value
