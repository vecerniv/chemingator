"""Scalar variables: unknowns and specifications of a flowsheet"""

from __future__ import annotations


class Variable:
    """A scalar unknown or specification.

    Specifications are made by fixing a variable to a value.
    Residuals are written in terms of `symbol`.

    Attributes:
        name: Globally unique name, e.g. "S1.flow[A]"
        value: Current value or initial guess while unsolved.
        fixed: True if value is a specification.
        units: SI unit string.
    """

    def __init__(
        self,
        name: str,
        value: float | None = None,
        fixed: bool = False,
        units: str = "",
    ) -> None:
        self.name = name
        self.units = units
        self._value = value
        self._fixed = False
        if fixed:
            self.fix()

    def __repr__(self) -> str:
        return self.name

    @property
    def value(self) -> float | None:
        """Current value or initial guess."""
        return self._value

    @value.setter
    def value(self, new_value: float | None) -> None:
        if new_value is None and self._fixed:
            raise ValueError(
                "Unable to set `value` of a fixed variable to None."
            )
        self._value = new_value

    @property
    def fixed(self) -> bool:
        """True if value is a specification."""
        return self._fixed

    def fix(self, value: float | None = None) -> None:
        """Marks the variable as a specification.

        Args:
            value: New value. If None, the current value is kept.

        Raises:
            ValueError: If both `value` and the current value are None.
        """
        if value is not None:
            self._value = value

        if self._value is None:
            raise ValueError(
                f"Unable to fix variable {self.name} with `value` None."
            )

        self._fixed = True

    def unfix(self) -> None:
        """Marks the variable as an unknown, keeping it's value as a guess."""
        self._fixed = False
