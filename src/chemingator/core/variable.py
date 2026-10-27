"""Scalar variables: unknowns and specifications of a flowsheet"""

from __future__ import annotations


class Variable:
    """A scalar unknown or specification.

    Specifications are made by fixing a variable to a value. Bounds are
    enforced only when fixing.

    Attributes:
        name: Globally unique name, e.g. "S1.flow[A]".
        lower: Lower bound, or None.
        upper: Upper bound, or None.
        units: SI unit string, informational only.
    """

    def __init__(
        self,
        name: str,
        *,
        value: float | None = None,
        lower: float | None = None,
        upper: float | None = None,
        fixed: bool = False,
        units: str = "",
    ) -> None:
        """Initializes the variable.

        Args:
            name: Globally unique name, e.g. "S1.flow[A]".
            value: Initial value or guess. None means unset.
            lower: Lower bound, or None.
            upper: Upper bound, or None.
            fixed: Whether to fix the variable as a specification.
            units: SI unit string, informational only.

        Raises:
            ValueError: If `lower` > `upper`, or if `fixed` is True and
                `value` is None or outside the bounds.
        """
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(
                f"Variable {name!r} has lower bound {lower} > upper bound "
                f"{upper}."
            )

        self.name = name
        self.units = units
        self._value = value
        self.lower = lower
        self.upper = upper
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

    def within_bounds(self, tol: float = 0.0) -> bool:
        """Whether the value lies in [lower - tol, upper + tol].

        True if the value is None or a bound is None.

        Args:
            tol: Absolute tolerance on both bounds.
        """
        return self._in_bounds(self._value, tol)

    def fix(self, value: float | None = None) -> None:
        """Marks the variable as a specification.

        Args:
            value: New value. If None, the current value is kept.

        Raises:
            ValueError: If both `value` and the current value are None, or
                the resulting value is outside the bounds.
        """
        new_value = self._value if value is None else value

        if new_value is None:
            raise ValueError(
                f"Unable to fix variable {self.name!r} with `value` None."
            )

        if not self._in_bounds(new_value):
            raise ValueError(
                f"Unable to fix variable {self.name!r} to {new_value}:"
                f"outside of bounds [{self.lower}, {self.upper}]."
            )

        self._value = new_value
        self._fixed = True

    def unfix(self) -> None:
        """Marks the variable as an unknown, keeping its value as a guess."""
        self._fixed = False

    def _in_bounds(self, value: float | None, tol: float = 0.0) -> bool:
        if value is None:
            return True
        if self.lower is not None and value < self.lower - tol:
            return False
        if self.upper is not None and value > self.upper + tol:
            return False
        return True


def current_value(var: Variable) -> float:
    """Returns a variable's value.

    Acts as a numeric resolver.

    Raises:
        ValueError: If the variable has no value yet.
    """
    if var.value is None:
        raise ValueError(f"Variable {var.name!r} has no value.")
    return var.value
