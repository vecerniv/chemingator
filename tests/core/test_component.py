"""Tests for chemingator.core.component."""

import pytest

from chemingator.core.component import Component
from chemingator.core.component import ComponentList

# --- Component construction -------------------------------------------------


def test_component_defaults() -> None:
    """A component created with only a name and no properties."""
    comp = Component("N2")

    assert comp.name == "N2"
    assert comp.molar_mass is None


def test_component_with_molar_mass() -> None:
    """A component created with a name and molar mass."""
    comp = Component("N2", molar_mass=0.028)

    assert comp.name == "N2"
    assert comp.molar_mass == 0.028


# --- ComponentList construction ---------------------------------------------


def test_comp_list_from_components() -> None:
    """A component list created from a sequence of Components."""
    n2 = Component("N2", molar_mass=0.028)
    o2 = Component("O2", molar_mass=0.032)

    clist = ComponentList([n2, o2])

    assert len(clist) == 2
    assert clist["N2"] is n2
    assert clist["O2"] is o2


def test_comp_list_from_names() -> None:
    """A component list created from a sequence of names."""
    clist = ComponentList(["N2", "O2"])

    assert clist["N2"] == Component("N2")
    assert clist["O2"].molar_mass is None


def test_comp_list_from_mixed() -> None:
    """A component list created from a sequence of Components and names."""
    n2 = Component("N2", molar_mass=0.032)

    clist = ComponentList([n2, "O2"])

    assert clist["N2"] is n2
    assert clist["O2"] == Component("O2")


def test_comp_list_empty() -> None:
    """A component list created from an empty sequence is empty."""
    clist = ComponentList([])

    assert len(clist) == 0
    assert clist.names() == []


def test_comp_list_keeps_order() -> None:
    """Components keep input order, not alphabetical order."""
    clist = ComponentList(["N2", "O2", "Ar"])

    assert clist.names() == ["N2", "O2", "Ar"]
    assert [comp.name for comp in clist] == ["N2", "O2", "Ar"]


@pytest.mark.parametrize(
    "components",
    [
        ["N2", "N2"],
        [Component("N2"), Component("N2")],
        [Component("N2", molar_mass=0.028), "N2"],
    ],
    ids=["names", "components", "mixed"],
)
def test_comp_list_duplicate_raises(components: list[str | Component]) -> None:
    """The same component name given twice is rejected."""
    with pytest.raises(ValueError, match="N2"):
        ComponentList(components)
