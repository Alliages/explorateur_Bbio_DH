"""Structures de projet : hiérarchie, plusieurs groupes par zone, contrôles de saisie."""

import pytest

from moteur.structures import Baie, Batiment, Groupe, Paroi, Projet, Zone


def projet_deux_groupes():
    """Immeuble collectif à deux groupes : logements traversants et non traversants."""
    traversant = Groupe("Traversants", surface_m2=600.0, traversant=True,
                        parois=[Paroi("Façade sud", "mur", 180.0, u=0.25, orientation_deg=0)],
                        baies=[Baie("Baies sud", 60.0, orientation_deg=0, uw=1.3, sw=0.45)])
    non_traversant = Groupe("Non traversants", surface_m2=400.0,
                            parois=[Paroi("Façade ouest", "mur", 120.0, u=0.25, orientation_deg=90),
                                    Paroi("Toiture", "toiture", 200.0, u=0.15, inclinaison_deg=0)],
                            baies=[Baie("Baies ouest", 40.0, orientation_deg=90)])
    zone = Zone("Logements", groupes=[traversant, non_traversant])
    return Projet("Essai", zone_climatique="H1a", altitude_m=120, batiments=[Batiment("A", zones=[zone])])


def test_batiment_a_deux_groupes():
    projet = projet_deux_groupes()
    batiment = projet.batiments[0]
    assert [g.nom for g in batiment.groupes] == ["Traversants", "Non traversants"]
    assert [g.traversant for g in batiment.groupes] == [True, False]


def test_surfaces_additionnees():
    batiment = projet_deux_groupes().batiments[0]
    assert batiment.zones[0].surface_m2 == pytest.approx(1000.0)
    assert batiment.surface_m2 == pytest.approx(sum(g.surface_m2 for g in batiment.groupes))
    assert batiment.groupes[1].surface_parois_m2 == pytest.approx(320.0)
    assert batiment.groupes[0].surface_baies_m2 == pytest.approx(60.0)


def test_listes_independantes():
    """Deux groupes créés sans parois ne partagent pas la même liste."""
    a, b = Groupe("A", 10.0), Groupe("B", 10.0)
    a.baies.append(Baie("Fenêtre", 2.0, orientation_deg=0))
    assert b.baies == []


@pytest.mark.parametrize("fabrique", [
    lambda: Projet("X", zone_climatique="H4"),
    lambda: Projet("X", zone_climatique="H1a", altitude_m=-5),
    lambda: Zone("X", usage="bureaux"),
    lambda: Groupe("X", surface_m2=0),
    lambda: Baie("X", surface_m2=-1, orientation_deg=0),
    lambda: Paroi("X", "cloison", 10.0),
    lambda: Paroi("X", "mur", 10.0, contact="voisin"),
])
def test_saisies_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()
