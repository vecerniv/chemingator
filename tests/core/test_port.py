"""Tests for chemingator.core.port."""

import pytest

from chemingator.core.component import ComponentList
from chemingator.core.port import Port
from chemingator.core.port import PortKind
from chemingator.core.stream import Stream
from chemingator.exceptions import ConnectivityError
from chemingator.units.base import Unit

# --- Construction -----------------------------------------------------------


def test_port_init(unit: Unit) -> None:
    """A new port stores its owner, name and kind, and has no stream."""
    port = Port(unit, "in0", PortKind.INLET)

    assert port.unit is unit
    assert port.name == "in0"
    assert port.kind is PortKind.INLET
    assert port.stream is None
    assert port.connected is False


def test_port_label(unit: Unit) -> None:
    """The label qualifies the port name with the unit name."""
    port = Port(unit, "in0", PortKind.INLET)

    assert port.label == "M1.in0"


# --- attach() ---------------------------------------------------------------


def test_attach_inlet(unit: Unit, stream: Stream) -> None:
    """An inlet becomes the stream's destination, not its source."""
    port = Port(unit, "in0", PortKind.INLET)

    port.attach(stream)

    assert port.stream is stream
    assert port.connected is True
    assert stream.destination is port
    assert stream.source is None


def test_attach_outlet(unit: Unit, stream: Stream) -> None:
    """An outlet becomes the stream's source, not its destination."""
    port = Port(unit, "out0", PortKind.OUTLET)

    port.attach(stream)

    assert port.stream is stream
    assert port.connected is True
    assert stream.source is port
    assert stream.destination is None


def test_attach_to_connected_port_raises(
    unit: Unit, stream: Stream, components: ComponentList
) -> None:
    """A second stream is rejected and nothing is relinked."""
    port = Port(unit, "in0", PortKind.INLET)
    port.attach(stream)
    other = Stream("S2", components)

    with pytest.raises(ConnectivityError, match="M1.in0"):
        port.attach(other)

    assert port.stream is stream
    assert other.destination is None


def test_attach_stream_to_outlet_and_inlet(unit: Unit, stream: Stream) -> None:
    """One stream connects one outlet to one inlet."""
    outlet = Port(unit, "out0", PortKind.OUTLET)
    inlet = Port(unit, "in0", PortKind.INLET)

    outlet.attach(stream)
    inlet.attach(stream)

    assert stream.source is outlet
    assert stream.destination is inlet


@pytest.mark.parametrize(
    "kind", [PortKind.INLET, PortKind.OUTLET], ids=["inlet", "outlet"]
)
def test_attach_stream_with_taken_end_raises(
    unit: Unit, stream: Stream, kind: PortKind
) -> None:
    """A stream whose matching end is taken is rejected and nothing is
    relinked.
    """
    port1 = Port(unit, "p0", kind)
    port2 = Port(unit, "p1", kind)
    port1.attach(stream)

    with pytest.raises(ConnectivityError, match="S1"):
        port2.attach(stream)

    taken_end = stream.destination if kind is PortKind.INLET else stream.source
    assert taken_end is port1
    assert port1.stream is stream
    assert port2.stream is None
