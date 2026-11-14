"""Bbio et Bbio max (annexe III, fiche 13.1 ; annexe à l'article R. 172-4 du code de la construction)."""

import pytest

from moteur.bbio import (bbio_max, calculer_bbio, classe_altitude, hauteur_sous_plafond_moyenne, mb_bruit, mb_geo,
                         mb_hsp, mb_surf_moy, mb_surf_tot, points_bbio, ponderer)
from moteur.besoins import bilan_besoins, calculer_besoins
from moteur.meteo import charger_meteo
from moteur.structures import Baie, Batiment, Groupe, Paroi, Projet, Zone

MOYEN = 65.0        # Bbio_maxmoyen des logements collectifs (points)


def groupe(nom, surface, nb_logements, orientation_baies=0, **options):
    """Groupe de logements simple : deux façades, une toiture, des baies sur une façade."""
    return Groupe(nom, surface, nb_logements=nb_logements, debit_ventilation_m3h=0.9 * surface,
                  parois=[Paroi("Sud", "mur", 0.3 * surface, u=0.25, orientation_deg=0, alpha=0.6),
                          Paroi("Nord", "mur", 0.3 * surface, u=0.25, orientation_deg=180, alpha=0.6),
                          Paroi("Toit", "toiture", 0.3 * surface, u=0.15, alpha=0.6)],
                  baies=[Baie("Baies", 0.17 * surface, orientation_baies, uw=1.3, sw_e=0.5, tl=0.7)], **options)


def projet_essai():
    """Un bâtiment de deux zones : logements traversants (deux groupes) et non traversants (un groupe)."""
    traversants = Zone("Traversants", groupes=[groupe("Sud", 600.0, 9), groupe("Nord", 300.0, 6, 180)],
                       hauteur_sous_plafond_m=2.5)
    non_traversants = Zone("Non traversants", groupes=[groupe("Est", 200.0, 5, -90, exposition_bruit="BR2")],
                           hauteur_sous_plafond_m=2.7)
    return Projet("Essai", zone_climatique="H2c", altitude_m=150.0,
                  batiments=[Batiment("A", zones=[traversants, non_traversants])])


@pytest.fixture(scope="module")
def resultat():
    return calculer_bbio(projet_essai())


# ------------------------------------------------------------------
# Bbio (fiche 13.1, éq. 2385)
# ------------------------------------------------------------------
def test_points_bbio():
    assert points_bbio(10.0, 0.0, 0.0) == pytest.approx(20.0)
    assert points_bbio(0.0, 10.0, 0.0) == pytest.approx(20.0)
    assert points_bbio(0.0, 0.0, 10.0) == pytest.approx(50.0)
    # Ordre de grandeur d'une étude de logements collectifs : 2 × 15,9 + 2 × 1,7 + 5 × 1,8 = 44,2 points
    assert points_bbio(15.9, 1.7, 1.8) == pytest.approx(44.2)


# ------------------------------------------------------------------
# Bbio max (annexe à l'article R. 172-4, chapitre III, logements collectifs)
# ------------------------------------------------------------------
def test_mb_geo():
    assert [classe_altitude(a) for a in (0, 399.9, 400, 800, 800.1)] == ["basse", "basse", "moyenne", "moyenne",
                                                                         "haute"]
    assert (mb_geo("H1a", 100), mb_geo("H1b", 100), mb_geo("H2a", 0), mb_geo("H3", 399)) == (0.1, 0.2, -0.1, -0.1)
    assert (mb_geo("H1c", 600), mb_geo("H3", 600), mb_geo("H2b", 900), mb_geo("H3", 1200)) == (0.45, -0.05, 0.65,
                                                                                               0.15)


def test_mb_surf_moy():
    assert mb_surf_moy(30.0, MOYEN) == pytest.approx(-3.0 / MOYEN)      # −6 + 0,1 × 30
    assert mb_surf_moy(60.0, MOYEN) == pytest.approx(0.0)               # −6 + 0,1 × 60
    assert mb_surf_moy(100.0, MOYEN) == pytest.approx(3.0 / MOYEN)      # −2 + 0,05 × 100
    assert mb_surf_moy(200.0, MOYEN) == pytest.approx(4.0 / MOYEN)
    # Les trois tranches se raccordent à 80 et à 120 m²
    assert mb_surf_moy(80.0, MOYEN) == pytest.approx(mb_surf_moy(80.0001, MOYEN), abs=1e-6)
    assert mb_surf_moy(120.0, MOYEN) == pytest.approx(mb_surf_moy(120.0001, MOYEN), abs=1e-6)


def test_mb_surf_tot():
    assert mb_surf_tot(410.0, MOYEN) == pytest.approx((19.5 - 0.015 * 410.0) / MOYEN)     # 0,205
    assert mb_surf_tot(1300.0, MOYEN) == pytest.approx(0.0)
    assert mb_surf_tot(5000.0, MOYEN) == 0.0


def test_mb_bruit_et_hsp():
    assert all(mb_bruit(zone, "BR1") == 0.0 for zone in ("H1a", "H2d", "H3"))
    assert (mb_bruit("H1a", "BR2"), mb_bruit("H1c", "BR2"), mb_bruit("H2c", "BR3"), mb_bruit("H3", "BR3")) \
        == (0.0, 0.1, 0.1, 0.2)
    assert mb_hsp(None) == 0.0 and mb_hsp(2.5) == 0.0
    assert mb_hsp(2.7) == pytest.approx((2.7 / 2.5 - 1.0) / 1.5)
    assert mb_hsp(3.5) == pytest.approx(mb_hsp(2.9)) == pytest.approx(0.16 / 1.5)


def test_bbio_max_a_la_main():
    # H1a sous 400 m, 24 logements pour 717 m² (29,9 m² par logement), bâtiment de 4 809 m², sans bruit :
    # 65 × (1 + 0,1 + (−6 + 2,9875) / 65) = 65 × 1,1 − 3,0125 = 68,49 points
    detail = bbio_max("H1a", 50.0, 717.0 / 24, 4809.0)
    assert detail["bbio_max"] == pytest.approx(68.4875)
    assert detail["mb_combles"] == 0.0 and detail["mb_surf_tot"] == 0.0
    # H3, 16 logements pour 1 468,5 m², bâtiment de 2 076,9 m², BR3 : 65 × (1 − 0,1 + 0,2) + (−2 + 4,589) = 74,09
    assert bbio_max("H3", 0.0, 1468.5 / 16, 2076.9, "BR3")["bbio_max"] == pytest.approx(74.089, abs=1e-3)
    # H2a, 3 logements pour 223 m², petit bâtiment de 410 m² : 65 × 0,9 + (−6 + 7,433) + (19,5 − 6,15) = 73,28
    assert bbio_max("H2a", 0.0, 223.0 / 3, 410.0, "BR2")["bbio_max"] == pytest.approx(73.283, abs=1e-3)


# ------------------------------------------------------------------
# Projet : groupes, zones, bâtiment
# ------------------------------------------------------------------
def test_ponderer():
    import pandas as pd
    table = pd.DataFrame({"zone": ["a", "a", "b"], "sref_m2": [100.0, 300.0, 50.0], "b_ch": [10.0, 20.0, 4.0]})
    zones = ponderer(table, ["zone"], ["b_ch"])
    assert zones["sref_m2"].tolist() == [400.0, 50.0]
    assert zones["b_ch"].tolist() == pytest.approx([17.5, 4.0])         # (100 × 10 + 300 × 20) / 400


def test_bbio_des_groupes(resultat):
    g = resultat.groupes
    assert g["groupe"].tolist() == ["Sud", "Nord", "Est"] and not g.isna().any().any()
    assert g["bbio"].tolist() == pytest.approx((2 * g["b_ch"] + 2 * g["b_fr"] + 5 * g["b_ecl"]).tolist())
    # Le groupe « Sud » seul donne les mêmes besoins que le calcul direct
    sud = projet_essai().batiments[0].zones[0].groupes[0]
    _, annuel = bilan_besoins(calculer_besoins(sud, charger_meteo("H2c", "th_bc", 150.0)), sud.surface_m2)
    assert g.loc[0, ["b_ch", "b_fr", "b_ecl"]].tolist() == pytest.approx(annuel.tolist())
    # Baies au nord : plus de chauffage et moins de froid que baies au sud
    assert g.loc[1, "b_ch"] > g.loc[0, "b_ch"] and g.loc[1, "b_fr"] < g.loc[0, "b_fr"]
    assert set(resultat.horaire) == {("A", "Traversants", "Sud"), ("A", "Traversants", "Nord"),
                                     ("A", "Non traversants", "Est")}
    assert len(resultat.horaire[("A", "Traversants", "Sud")]) == 8760


def test_bbio_mensuel(resultat):
    m, g = resultat.mensuel, resultat.groupes
    assert len(m) == 3 * 12
    # Éq. 2386 : le Bbio annuel est la somme des Bbio mensuels
    annuel = m.groupby("groupe", sort=False)[["b_ch", "bbio"]].sum()
    assert annuel["bbio"].tolist() == pytest.approx(g["bbio"].tolist())
    assert annuel["b_ch"].tolist() == pytest.approx(g["b_ch"].tolist())


def test_zones_et_batiment(resultat):
    g, z, b = resultat.groupes, resultat.zones, resultat.batiments
    assert z["zone"].tolist() == ["Traversants", "Non traversants"]
    assert z["sref_m2"].tolist() == [900.0, 200.0] and b["sref_m2"].tolist() == [1100.0]
    assert z["nb_logements"].tolist() == [15, 5]
    assert z["surface_moyenne_logement_m2"].tolist() == pytest.approx([60.0, 40.0])
    # Zone : kWh des groupes rapportés aux m² de la zone
    for colonne in ("b_ch", "b_fr", "b_ecl", "bbio", "bbio_max"):
        attendu = (600.0 * g.loc[0, colonne] + 300.0 * g.loc[1, colonne]) / 900.0
        assert z.loc[0, colonne] == pytest.approx(attendu), colonne
        attendu = (900.0 * z.loc[0, colonne] + 200.0 * z.loc[1, colonne]) / 1100.0
        assert b.loc[0, colonne] == pytest.approx(attendu), colonne
    # Le Bbio du bâtiment suit aussi la formule appliquée à ses besoins
    assert b.loc[0, "bbio"] == pytest.approx(2 * b.loc[0, "b_ch"] + 2 * b.loc[0, "b_fr"] + 5 * b.loc[0, "b_ecl"])
    assert b.loc[0, "ecart_pct"] == pytest.approx((b.loc[0, "bbio"] / b.loc[0, "bbio_max"] - 1.0) * 100.0)
    assert bool(b.loc[0, "respecte"]) == (b.loc[0, "bbio"] <= b.loc[0, "bbio_max"])


def test_bbio_max_du_projet(resultat):
    g = resultat.groupes
    # H2c à 150 m : Mbgéo = −0,1 ; bâtiment de 1 100 m² : Mbsurf_tot = (19,5 − 16,5) / 65
    assert (g["mb_geo"] == -0.1).all() and (g["bbio_max_moyen"] == MOYEN).all()
    assert g["mb_surf_tot"].tolist() == pytest.approx([3.0 / MOYEN] * 3)
    # Traversants : 60 m² par logement (0) ; non traversants : 40 m² (−2 / 65), BR2 en H2c (0,1)
    assert g["mb_surf_moy"].tolist() == pytest.approx([0.0, 0.0, -2.0 / MOYEN])
    assert g["mb_bruit"].tolist() == [0.0, 0.0, 0.1]
    # Hauteur sous plafond moyenne du bâtiment : (900 × 2,5 + 200 × 2,7) / 1 100 = 2,536 m, pour tous les groupes
    hsp = (900.0 * 2.5 + 200.0 * 2.7) / 1100.0
    assert hauteur_sous_plafond_moyenne(projet_essai().batiments[0], "logement_collectif") == pytest.approx(hsp)
    mb = (hsp / 2.5 - 1.0) / 1.5
    assert g["mb_hsp"].tolist() == pytest.approx([mb] * 3)
    assert g.loc[0, "bbio_max"] == pytest.approx(MOYEN * (0.9 + mb) + 3.0)
    assert g.loc[2, "bbio_max"] == pytest.approx(MOYEN * (1.0 + mb) + 1.0)                  # 65 × (1 + mb) + 3 − 2


def test_sans_refroidissement():
    projet = projet_essai()
    projet.batiments[0].zones = projet.batiments[0].zones[1:]       # un seul groupe : calcul court
    sans_froid = calculer_bbio(projet, refroidissement=False)
    assert sans_froid.groupes.loc[0, "b_fr"] == 0.0
    assert sans_froid.groupes.loc[0, "bbio"] == pytest.approx(
        2 * sans_froid.groupes.loc[0, "b_ch"] + 5 * sans_froid.groupes.loc[0, "b_ecl"])
    # Bâtiment réduit à 200 m² : Mbsurf_tot = (19,5 − 3) / 65
    assert sans_froid.groupes.loc[0, "mb_surf_tot"] == pytest.approx(16.5 / MOYEN)


def test_projets_refuses():
    with pytest.raises(ValueError, match="aucun groupe"):
        calculer_bbio(Projet("Vide", zone_climatique="H1a", batiments=[Batiment("A", zones=[Zone("Z")])]))
    doublon = Zone("Z", groupes=[groupe("G", 100.0, 2), groupe("G", 100.0, 2)])
    with pytest.raises(ValueError, match="en double"):
        calculer_bbio(Projet("Double", zone_climatique="H1a", batiments=[Batiment("A", zones=[doublon])]))
    sans_logements = Zone("Z", groupes=[groupe("G", 100.0, None)])
    with pytest.raises(ValueError, match="nombre de logements"):
        calculer_bbio(Projet("X", zone_climatique="H1a", batiments=[Batiment("A", zones=[sans_logements])]))
