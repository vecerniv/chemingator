"""Chemical components and the ordered component set of a flowsheet."""

from __future__ import annotations

from collections.abc import Sequence
import dataclasses


@dataclasses.dataclass(frozen=True)
class Component:
    """A chemical species.

    Attributes:
        name: Identifier used in specifications, e.g. "N2".
        molar_mass: Molar mass in kg/mol, supplied by the user. Only required
            for mass-basis specification or reports.
    """

    name: str
    molar_mass: float | None = None


class ComponentList:
    """An ordered, name-indexed set of components shared by a flowsheet."""

    def __init__(self, components: Sequence[str | Component]) -> None:
        """Initializes the list.

        Args:
            components: Names or Component objects, in reporting order.

        Raises:
            ValueError: If a name appears more than once.
        """
        raise NotImplementedError

    def names(self) -> list[str]:
        """Returns component names in order."""
        raise NotImplementedError
