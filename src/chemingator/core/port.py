"""Units ports: named inlets and outlets on units."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chemingator.core import stream as cg_stream
    from chemingator.units import base as cg_units

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

    def __init__(self, unit: cg_units.Unit, name: str, kind: PortKind) -> None:
        self.unit = unit
        self.name = name
        self.kind = kind
        self.stream: cg_stream.Stream | None = None

    @property
    def connected(self) -> bool:
        """Whether a stream is connected to this port."""
        return self.stream is not None

    @property
    def label(self) -> str:
        """Unit-qualified port name, e.g. "M1.in0"."""
        return f"{self.unit.name}.{self.name}"

    def attach(self, stream: cg_stream.Stream) -> None:
        """Links a this port and a stream in both directions.

        Sets `self.stream`, plus `stream.source` or `stream.destination`.

        Args:
            stream: The stream to attach.

        Raises:
            ConnectivityError: If the port is already connected.
        """
        if self.stream is not None:
            raise ConnectivityError(
                f"Port {self.label!r} is already connected to "
                f"{self.stream.name!r}"
            )
        self.stream = stream
        if self.kind is PortKind.OUTLET:
            stream.source = self
        else:
            stream.destination = self
