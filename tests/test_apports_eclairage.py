"""Apports internes (annexe III, fiche 4.1) et éclairage (fiches 5.10 et 7.1)."""

import numpy as np
import pandas as pd
import pytest

from moteur.apports import apports_internes, nombre_adultes_equivalents
from moteur.calendrier import construire_calendrier
from moteur.eclairage import (coefficient_c2, coefficients_einat, eclairage_groupe, eclairement_naturel,
                              flux_lumineux_baie)
from moteur.meteo import charger_meteo
from moteur.scenarios import charger_scenarios
from moteur.solaire import environnement_proche
from moteur.structures import Baie, Groupe


def meteo_test(gamma, dirn=800.0, diff=100.0):
    """Météo synthétique : soleil au sud à la hauteur « gamma » (degrés), une ligne par valeur."""
    gamma = np.atleast_1d(np.asarray(gamma, dtype=float))
    n = len(gamma)
    return pd.DataFrame({"dirN": np.full(n, dirn), "diff": np.full(n, diff), "Gamma": gamma, "Psi": np.zeros(n),
                         "Teciel": np.full(n, 10.0), "te": np.full(n, 20.0)})


# ------------------------------------------------------------------
# Apports internes (fiche 4.1, éq. 33 à 42)
# ------------------------------------------------------------------
@pytest.mark.parametrize("surface_logement, attendu", [
    (8.0, 1.0),                                     # moins de 10 m² : Nmax = 1
    (30.0, 1.75 - 0.01875 * 20),                    # entre 10 et 50 m²
    (50.0, 1.75),                                   # raccord à 50 m²
    (65.0, 1.75 + 0.3 * (0.035 * 65 - 1.75)),       # au-delà : Nmax = 2,275, réduit au-dessus de 1,75
])
def test_adultes_equivalents(surface_logement, attendu):
    assert nombre_adultes_equivalents(surface_logement, 1) == pytest.approx(attendu)
    assert nombre_adultes_equivalents(4 * surface_logement, 4) == pytest.approx(4 * attendu)


def test_apports_internes_du_logement_collectif():
    groupe = Groupe("Immeuble", 650.0, nb_logements=10)
    calendrier = construire_calendrier()
    a = apports_internes(groupe, charger_scenarios(), calendrier)
    # Surface habitable 585 m², 58,5 m² par logement : Nmax = 2,0475, Nadeq = 10 × (1,75 + 0,3 × 0,2975)
    n_adeq = 10 * (1.75 + 0.3 * (0.035 * 58.5 - 1.75))
    assert a["n_occ"].max() == pytest.approx(n_adeq)
    assert a["phi_occupants"].max() == pytest.approx(n_adeq * 90.0)
    assert a["phi_usages"].max() == pytest.approx(585.0 * 5.7)             # 5,7 W/m² de logements
    # Veille : 20 % ; rien pendant la semaine de vacances du scénario
    assert sorted(a["phi_usages"].round(6).unique()) == pytest.approx([0.0, 0.2 * 585.0 * 5.7, 585.0 * 5.7])
    # Logement inoccupé : pas d'occupant ; 2 012 heures par an (voir docs/audit.md, 0.8.0)
    assert (a["occupe"] == 0).sum() == 2012
    assert (a.loc[a["occupe"] == 0, "n_occ"] == 0).all()
    # Nuit : 70 % des occupants ; moitié convectif, moitié radiatif
    assert sorted(a["n_occ"].round(6).unique()) == pytest.approx([0.0, 0.7 * n_adeq, n_adeq])
    total = a["phi_occupants"] + a["phi_usages"]
    assert (a["phi_conv"] - 0.5 * total).abs().max() < 1e-9 and (a["phi_rad"] - 0.5 * total).abs().max() < 1e-9
    with pytest.raises(ValueError, match="nb_logements"):
        apports_internes(Groupe("Sans logements", 650.0), charger_scenarios(), calendrier)


# ------------------------------------------------------------------
# Lumière naturelle (fiches 5.10 et 7.1)
# ------------------------------------------------------------------
def test_coefficients_einat():
    # Ro moyen = (0,2 + 2,5 × 0,5 + 0,7) / 4,5 ; interréflexions I = Ro / (1 − Ro) / 4,5
    ro = (0.2 + 2.5 * 0.5 + 0.7) / 4.5
    inter = ro / (1 - ro) / 4.5
    k1, k2, k3 = coefficients_einat()
    assert (k1, k2, k3) == pytest.approx((0.2 * inter, 0.4 + inter, 0.7 * 0.8 + 0.7 * inter))
    assert (k1, k2, k3) == pytest.approx((0.0407, 0.6033, 0.7023), abs=1e-4)


def test_flux_lumineux_et_eclairement_naturel():
    m = meteo_test([30.0, 0.0], dirn=[800.0, 0.0][0])
    baie = Baie("Sud", 2.0, orientation_deg=0, uw=1.3, sw_e=0.5, tl=0.7)
    env = environnement_proche(m, baie)
    flux = flux_lumineux_baie(baie, m)
    assert flux["flt1"].iloc[0] == pytest.approx(2.0 * 0.7 * env["erp_m"].iloc[0])     # éq. 231
    assert flux["flt2"].iloc[0] == pytest.approx(2.0 * 0.7 * env["efp_m"].iloc[0])     # éq. 232
    assert flux["flt3"].iloc[0] == pytest.approx(2.0 * 0.7 * env["errp_m"].iloc[0])    # éq. 233
    k1, k2, k3 = coefficients_einat()
    groupe = Groupe("G", 20.0, baies=[baie])
    einat = eclairement_naturel(groupe, m)
    assert einat.iloc[0] == pytest.approx((k1 * flux["flt1"] + k2 * flux["flt2"] + k3 * flux["flt3"]).iloc[0] / 20.0)
    # Deux fois plus de baies : deux fois plus de lumière ; sans baie : aucune
    groupe.baies.append(Baie("Sud 2", 2.0, orientation_deg=0, uw=1.3, sw_e=0.5, tl=0.7))
    assert eclairement_naturel(groupe, m).iloc[0] == pytest.approx(2 * einat.iloc[0])
    assert (eclairement_naturel(Groupe("Aveugle", 20.0), m) == 0).all()
    with pytest.raises(ValueError, match="tl"):
        flux_lumineux_baie(Baie("Sans Tl", 2.0, orientation_deg=0), m)


@pytest.mark.parametrize("einat, attendu", [(0, 1.0), (100, 1.0), (150, 0.525), (200, 0.05),
                                            (1500, 0.05 * 1300 / 2600), (2800, 0.0), (5000, 0.0)])
def test_coefficient_c2(einat, attendu):
    assert coefficient_c2(einat) == pytest.approx(attendu)


def test_consommation_d_eclairage():
    # Nuit (pas de lumière naturelle) puis plein jour, éclairage autorisé puis non
    m = meteo_test([0.0, 0.0, 45.0], dirn=0.0, diff=0.0)
    m.loc[2, ["dirN", "diff"]] = [800.0, 150.0]
    groupe = Groupe("G", 50.0, baies=[Baie("Sud", 30.0, orientation_deg=0, uw=1.3, sw_e=0.5, tl=0.7)])
    e = eclairage_groupe(groupe, m, [1, 0, 1])
    assert e["cecl_wh"].iloc[0] == pytest.approx(1.0 * 0.9 * 1.0 * 50.0)       # éq. 789 : 1 W/m² × C1 × C2 × A
    assert e["cecl_wh"].iloc[1] == 0                                           # éclairage non autorisé
    assert e["einat"].iloc[2] > 2800 and e["cecl_wh"].iloc[2] == 0             # assez de lumière naturelle
    assert e["phi_conv"].iloc[0] == pytest.approx(22.5) and e["phi_rad"].iloc[0] == pytest.approx(22.5)
    with pytest.raises(ValueError, match="autorisation"):
        eclairage_groupe(groupe, m, [1, 0])


def test_eclairage_annuel():
    # Année entière : plus de baies, moins d'éclairage ; ordre de grandeur de 1 à 3 kWh/m².an
    meteo = charger_meteo("H1a", "th_bc", 100.0)
    autorisation = charger_scenarios().derouler("eclairage", construire_calendrier())

    def consommation(surface_baies):
        groupe = Groupe("G", 65.0, baies=[Baie("Sud", surface_baies, orientation_deg=0, uw=1.3, sw_e=0.5, tl=0.7)])
        return eclairage_groupe(groupe, meteo, autorisation)["cecl_wh"].sum() / 1000.0 / 65.0

    peu, beaucoup = consommation(4.0), consommation(12.0)
    assert 1.0 < beaucoup < peu < 3.0
    # Sans lumière naturelle : 1 W/m² × 0,9 pendant toutes les heures d'éclairage autorisé
    aveugle = eclairage_groupe(Groupe("G", 65.0), meteo, autorisation)["cecl_wh"].sum()
    assert aveugle == pytest.approx(0.9 * 65.0 * (autorisation > 0).sum())
