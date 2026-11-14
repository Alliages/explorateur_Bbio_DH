"""Structures de projet : hiérarchie, plusieurs groupes par zone, contrôles de saisie."""

import pytest

from moteur.structures import Baie, Batiment, Groupe, Paroi, Projet, Zone


def projet_deux_groupes():
    """Immeuble collectif à deux groupes : logements traversants et non traversants."""
    traversant = Groupe("Traversants", surface_m2=600.0, traversant=True,
                        parois=[Paroi("Façade sud", "mur", 180.0, u=0.25, orientation_deg=0)],
                        baies=[Baie("Baies sud", 60.0, orientation_deg=0, uw=1.3, sw_e=0.45)])
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


# ------------------------------------------------------------------
# 0.8.4 : données du modèle thermique du groupe
# ------------------------------------------------------------------
def test_inclinaison_par_defaut_selon_le_type():
    assert Paroi("Mur", "mur", 10.0, orientation_deg=0).inclinaison_deg == 90
    assert Paroi("Toit", "toiture", 10.0).inclinaison_deg == 0
    assert Paroi("Plancher", "plancher_bas", 10.0).inclinaison_deg == 180
    assert Paroi("Rampant", "toiture", 10.0, orientation_deg=0, inclinaison_deg=35).inclinaison_deg == 35


def test_donnees_thermiques_du_groupe():
    from moteur.structures import PontThermique
    groupe = Groupe("G", 50.0, ponts_thermiques=[PontThermique("Plancher", 30.0, 0.3)],
                    debit_ventilation_m3h=75.0, inertie_quotidienne="lourde")
    assert groupe.ponts_thermiques[0].psi == 0.3
    assert (groupe.inertie_sequentielle, groupe.inertie_annuelle, groupe.climatise) == ("defaut", "defaut", False)


def _brasseur():
    from moteur.structures import Brasseur
    return Brasseur("B", nombre=1, surface_desservie_m2=15.0, debit_max_m3h=5000.0, puissance_max_w=40.0)


@pytest.mark.parametrize("fabrique", [
    lambda: __import__("moteur.structures", fromlist=["PontThermique"]).PontThermique("X", 0.0, 0.3),
    lambda: __import__("moteur.structures", fromlist=["PontThermique"]).PontThermique("X", 10.0, -0.1),
    lambda: Groupe("X", 50.0, debit_ventilation_m3h=-1.0),
    lambda: Groupe("X", 50.0, inertie_quotidienne="massive"),
    lambda: Groupe("X", 50.0, inertie_sequentielle="annuelle"),
    lambda: Groupe("X", 50.0, inertie_quotidienne="personnalisee", amq_surf=2.5),
    lambda: Groupe("X", 50.0, inertie_annuelle="personnalisee", cma_surf=6000.0),
    lambda: Groupe("X", 50.0, cmq_surf=-10.0),
    lambda: Groupe("X", 50.0, volume_m3=125.0, climatise=True, brasseurs=[_brasseur()]),
    lambda: Paroi("X", "mur", 10.0, b_therm=1.5),
    lambda: Baie("X", 2.0, orientation_deg=0, sw2_e=1.2),
    lambda: Baie("X", 2.0, orientation_deg=0, uw_horizontal=0.0),
])
def test_saisies_thermiques_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()


# ------------------------------------------------------------------
# 0.8.6 : logements, débit de pointe, transmission lumineuse
# ------------------------------------------------------------------
@pytest.mark.parametrize("fabrique", [
    lambda: Groupe("X", 50.0, nb_logements=0),
    lambda: Groupe("X", 50.0, nb_logements=2.5),
    lambda: Groupe("X", 50.0, debit_ventilation_m3h=90.0, debit_ventilation_pointe_m3h=60.0),
    lambda: Baie("X", 2.0, orientation_deg=0, tl=1.3),
])
def test_saisies_des_besoins_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()


# ------------------------------------------------------------------
# 0.8.8 : données du Bbio max (bruit, hauteur sous plafond, logements de la zone)
# ------------------------------------------------------------------
def test_donnees_du_bbio_max():
    zone = Zone("Z", groupes=[Groupe("A", 100.0, nb_logements=2), Groupe("B", 50.0, nb_logements=1)],
                hauteur_sous_plafond_m=2.7)
    assert zone.nb_logements == 3 and zone.groupes[0].exposition_bruit == "BR1"
    # Un groupe sans nombre de logements : celui de la zone est inconnu
    assert Zone("Z", groupes=[Groupe("A", 100.0, nb_logements=2), Groupe("B", 50.0)]).nb_logements is None
    assert Zone("Z").nb_logements is None


@pytest.mark.parametrize("fabrique", [
    lambda: Groupe("X", 50.0, exposition_bruit="BR4"),
    lambda: Zone("X", hauteur_sous_plafond_m=0.0),
])
def test_saisies_du_bbio_max_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()
