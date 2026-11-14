"""Infiltrations par les défauts d'étanchéité (annexe III, fiche 5.6)."""

import pytest

from moteur.besoins import bilan_besoins, calculer_besoins
from moteur.infiltrations import (InfiltrationsGroupe, coefficients_pression, defauts_groupe, equilibre,
                                  masse_volumique, surfaces_permeables)
from moteur.meteo import charger_meteo
from moteur.structures import Baie, Groupe, Paroi, Zone

FLUX_DU_BILAN = ["flux_ventilation", "flux_baies", "flux_parois", "flux_apports", "flux_inerties_longues"]
SURFACE = 300.0
PAR_PASCAL = 1.0 / 4.0 ** (2.0 / 3.0)       # débit sous 1 Pa d'un défaut de 1 m³/h sous 4 Pa


def groupe(traversant=False, toiture=True, **options):
    """80 m² de murs, 20 m² de baies, 50 m² de toiture (facultative), 100 m² de plancher bas."""
    parois = [Paroi("Mur", "mur", 80.0, u=0.25, orientation_deg=0, alpha=0.6),
              Paroi("Plancher", "plancher_bas", 100.0, u=0.3, contact="local_non_chauffe", b_therm=0.8)]
    if toiture:
        parois.append(Paroi("Toit", "toiture", 50.0, u=0.15, alpha=0.6))
    return Groupe("G", SURFACE, nb_logements=5, debit_ventilation_m3h=300.0, traversant=traversant, parois=parois,
                  baies=[Baie("Sud", 20.0, 0, uw=1.4, sw_e=0.5, tl=0.6)], **options)


# ------------------------------------------------------------------
# Description conventionnelle des défauts (tableaux 23, 24, 28 et 29)
# ------------------------------------------------------------------
def test_surfaces_et_coefficients_de_pression():
    # Façade : murs et baies ; toiture à part ; le plancher bas ne compte pas
    assert surfaces_permeables(groupe()) == (100.0, 50.0)
    assert surfaces_permeables(groupe(toiture=False)) == (100.0, 0.0)
    assert coefficients_pression(False, 30.0) == (0.05, -0.05, 0.0)
    assert coefficients_pression(True, None) == (0.25, -0.5, -0.6)
    assert coefficients_pression(True, 10.0)[0] == 0.25 and coefficients_pression(True, 17.0)[0] == 0.45


def test_defauts_d_un_groupe():
    defauts = defauts_groupe(groupe(permeabilite_q4pa=1.0))
    # Quatre quarts de façade (100 m² × 1 m³/h/m² sous 4 Pa) et la toiture entière ; hauteurs 0,75, 2,25 et 3 m
    assert [d[0] for d in defauts] == pytest.approx([25.0 * PAR_PASCAL] * 4 + [50.0 * PAR_PASCAL])
    assert [(d[1], d[2]) for d in defauts] == [(0.05, 0.75), (0.05, 2.25), (-0.05, 0.75), (-0.05, 2.25), (0.0, 3.0)]
    # Zone basse de 2 m : altitudes comptées sur 2 m ; sans toiture : quatre défauts
    assert [d[2] for d in defauts_groupe(groupe(permeabilite_q4pa=1.0), hauteur_zone_m=2.0)] \
        == [0.5, 1.5, 0.5, 1.5, 2.0]
    assert len(defauts_groupe(groupe(toiture=False, permeabilite_q4pa=1.0))) == 4
    assert defauts_groupe(groupe(permeabilite_q4pa=0.0)) == []


# ------------------------------------------------------------------
# Équilibre aéraulique (éq. 135 à 137, 151 et 167)
# ------------------------------------------------------------------
def test_vent_seul():
    # Même température dedans et dehors (19 °C, 1,2 kg/m³) : pas de tirage. Vent de 4 m/s, Cp = ± 0,05 :
    # pression motrice ± ½ × 0,05 × 1,2 × 16 = ± 0,48 Pa ; par symétrie Pib = 0 ; il entre par les deux défauts au
    # vent : 2 × 25 × 0,48^(2/3) / 4^(2/3) m³/h
    defauts = defauts_groupe(groupe(toiture=False, permeabilite_q4pa=1.0))
    r = equilibre(defauts, 4.0, 19.0, 19.0)
    assert r["pib"] == pytest.approx(0.0, abs=1e-6)
    assert r["debit_entrant_m3h"] == pytest.approx(2 * 25.0 * PAR_PASCAL * 0.48 ** (2.0 / 3.0))
    assert r["debit_entrant_kg_s"] == pytest.approx(-r["debit_sortant_kg_s"])
    # Sans vent ni écart de température : rien ne bouge
    assert equilibre(defauts, 0.0, 19.0, 19.0)["debit_entrant_m3h"] == pytest.approx(0.0, abs=1e-6)


def test_tirage_thermique_seul():
    # 0 °C dehors, 20 °C dedans, sans vent : l'air entre en bas et sort en haut ; la masse se conserve
    assert masse_volumique(0.0) == pytest.approx(1.2 * 292.0 / 273.0)
    defauts = defauts_groupe(groupe(permeabilite_q4pa=1.0))
    r = equilibre(defauts, 0.0, 0.0, 20.0)
    assert r["debit_entrant_kg_s"] > 0 and r["debit_entrant_kg_s"] == pytest.approx(-r["debit_sortant_kg_s"])
    # Plus il fait froid, plus il entre d'air ; une enveloppe deux fois plus perméable en laisse passer le double
    assert equilibre(defauts, 0.0, -10.0, 20.0)["debit_entrant_m3h"] > r["debit_entrant_m3h"]
    double = defauts_groupe(groupe(permeabilite_q4pa=2.0))
    assert equilibre(double, 0.0, 0.0, 20.0)["debit_entrant_m3h"] == pytest.approx(2 * r["debit_entrant_m3h"])


def test_ventilation_double_flux():
    # Air soufflé à 10 °C, repris à 20 °C, mêmes volumes : il entre plus de masse qu'il n'en sort par la
    # ventilation ; le surplus sort par les défauts (éq. 156, 157 et 167)
    defauts = defauts_groupe(groupe(permeabilite_q4pa=1.0))
    r = equilibre(defauts, 3.0, 0.0, 20.0, debit_ventilation_m3h=300.0, theta_souffle=10.0)
    net = (masse_volumique(10.0) - masse_volumique(20.0)) * 300.0 / 3600.0
    assert r["debit_entrant_kg_s"] + r["debit_sortant_kg_s"] + net == pytest.approx(0.0, abs=1e-9)
    sans = equilibre(defauts, 3.0, 0.0, 20.0)
    assert r["pib"] > sans["pib"] and r["debit_entrant_m3h"] < sans["debit_entrant_m3h"]


def test_traversant_plus_expose_au_vent():
    non_traversant = equilibre(defauts_groupe(groupe(False, permeabilite_q4pa=1.0)), 5.0, 10.0, 20.0)
    traversant = equilibre(defauts_groupe(groupe(True, permeabilite_q4pa=1.0)), 5.0, 10.0, 20.0)
    assert traversant["debit_entrant_m3h"] > 2 * non_traversant["debit_entrant_m3h"]


# ------------------------------------------------------------------
# Effet sur les besoins
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def meteo():
    return charger_meteo("H1a", "th_bc", 100.0)


def test_vent_corrige(meteo):
    infiltrations = InfiltrationsGroupe(groupe(permeabilite_q4pa=1.0), meteo, 300.0)
    assert infiltrations.vent[:100].tolist() == pytest.approx((0.9 * meteo["Vent"].to_numpy()[:100]).tolist())
    r = infiltrations.pas(10, 20.0, 12.0)
    assert r["hg"] == pytest.approx(0.34 * r["debit_m3h"]) and r["debit_m3h"] > 0


def test_plus_de_chauffage_avec_infiltrations(meteo):
    etanche = calculer_besoins(groupe(True), meteo)
    permeable = calculer_besoins(groupe(True, permeabilite_q4pa=1.0), meteo)
    assert (etanche["hg_infiltrations"] == 0).all() and (permeable["hg_infiltrations"] >= 0).all()
    assert permeable["debit_infiltrations_m3h"].mean() > 5.0
    b_etanche, b_permeable = bilan_besoins(etanche, SURFACE)[1], bilan_besoins(permeable, SURFACE)[1]
    assert b_permeable["b_ch"] > 1.05 * b_etanche["b_ch"]
    # Bilan d'énergie de chaque heure, infiltrations comprises
    assert (permeable["stockage"] - permeable[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6


@pytest.mark.parametrize("fabrique", [
    lambda: groupe(permeabilite_q4pa=-0.5),
    lambda: Zone("Z", hauteur_m=0.0),
])
def test_saisies_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()
