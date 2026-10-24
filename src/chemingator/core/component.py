"""Chemical components and the ordered component set of a flowsheet."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
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
        self.components: dict[str, Component] = {}
        for item in components:
            comp = item if isinstance(item, Component) else Component(item)
            if comp.name in self.components:
                raise ValueError(f"Duplicate component name: {comp.name!r}")
            self.components[comp.name] = comp

    def __iter__(self) -> Iterator[Component]:
        for _, comp in self.components.items():
            yield comp

    def __len__(self) -> int:
        return len(self.components)

    def __contains__(self, name: object) -> bool:
        if name in self.names():
            return True
        else:
            return False

    def __getitem__(self, name: str) -> Component:
        return self.components[name]

    def names(self) -> list[str]:
        """Returns component names in order."""
        return [*self.components]
