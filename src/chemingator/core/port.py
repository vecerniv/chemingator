"""Units ports: named inlets and outlets on units."""

from __future__ import annotations

import enum
from typing import Any

from chemingator.exceptions import ConnectivityError


class PortKind(enum.Enum):
    """Direction of a port."""

    INLET = "inlet"
    OUTLET = "outlet"


class Port:
    """A named inlet or outlet on a unit connected to at most one stream.

    Attributes:
        unit: The port owner unit.
        name: A unit-wise unique name.
        kind: Inlet or outlet.
        stream: The attached stream or None.
    """

    def __init__(self, unit: Any, name: str, kind: PortKind) -> None:
        self.unit = unit
        self.name = name
        self.kind = kind
        self.stream: Any | None = None

    @property
    def connected(self) -> bool:
        """Whether a stream is connected to this port."""
        return self.stream is not None

    def attach(self, stream: Any) -> None:
        """Attaches a stream to this port.

        Args:
            stream: The stream to attach.

        Raises:
            ConnectivityError: If a stream is already attached.
        """
        if self.connected:
            raise ConnectivityError(
                f"A stream is already attached to port {self.name} "
                f"in unit {self.unit.name}."
            )

        self.stream = stream
