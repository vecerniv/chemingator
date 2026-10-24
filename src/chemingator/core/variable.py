"""Scalar variables: unknowns and specification of a flowsheet"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(eq=False)
class Variable:
    """A scalar unknown or specification.

    Specifications are made by fixing a variable to a value. Residuals are
    written in terms of `symbol`.

    Attributes:
        name: Globally unique name, e.g. "S1.flow[A]"
        value: Current value or initial guess while unsolved.
        fixed: True if value if a specification.
        units: SI unit string.
    """

    name: str
    value: float | None = None
    fixed: bool = False
    units: str = ""

    def __post_init__(self) -> None:
        if self.fixed and self.value is None:
            raise ValueError("Unable to fix a variable with `value` None.")

    def fix(self, value: float | None = None) -> None:
        """Marks the variable as a specification.

        Args:
            value: New value. If None, the current value is kept.

        Raises:
            ValueError: If both `value` and the current value are None.
        """
        if value is not None:
            self.value = value

        if self.value is None:
            raise ValueError("Unable to fix a variable with `value` None.")

        self.fixed = True

    def unfix(self) -> None:
        """Marks the variable as an unknown, keeping it's value as a guess."""
        self.fixed = False
