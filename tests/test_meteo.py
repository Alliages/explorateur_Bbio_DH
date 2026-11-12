"""Fichiers météo : intégrité des 16 fichiers, valeurs du classeur officiel, correction d'altitude."""

import os

import pytest

from config.reglages import CLASSEUR_METEO, COLONNES_METEO, JEUX_METEO, ZONES_CLIMATIQUES
from moteur.meteo import altitude_corrigee, charger_meteo, lire_meteo

# Premières lignes du classeur officiel, relevées à la main (onglets H1a_Th-BC et H1c_Th-D)
H1A_TH_BC_HEURE_0 = {"te0": 5.835, "we0": 5.4565, "dirN": 0, "diff": 0, "Teciel": 0, "Vent": 1, "Teau": 9.4,
                     "Gamma": 0, "Psi": 166.81}
HEURES_DIRECT_SOLEIL_COUCHE_MAX = 30     # constat sur le classeur officiel, pas une règle
H1C_TH_D_HEURE_6 = {"te0": 0.6, "we0": 4.4915, "Teciel": -3.3, "Vent": 0.8, "Teau": 6.5, "Psi": -75.96}


@pytest.mark.parametrize("zone", ZONES_CLIMATIQUES)
@pytest.mark.parametrize("jeu", JEUX_METEO)
def test_fichier_complet_et_plausible(zone, jeu):
    meteo = lire_meteo(zone, jeu)                       # contrôle déjà : colonnes, 8 760 heures, pas de vide
    assert tuple(meteo.columns) == COLONNES_METEO
    assert len(meteo) == 8760
    assert meteo["te0"].between(-30, 50).all()
    assert (meteo[["we0", "dirN", "diff", "Vent"]] >= 0).all().all()
    assert meteo["Gamma"].between(0, 90).all()
    assert meteo["Psi"].between(-180, 180).all()
    # Rayonnement direct avec un soleil noté couché (Gamma = 0) : quelques heures du classeur officiel
    # sont dans ce cas (28 en H1a, 30 en H2d, voir docs/audit.md) ; on borne leur nombre
    assert ((meteo["Gamma"] == 0) & (meteo["dirN"] > 0)).sum() <= HEURES_DIRECT_SOLEIL_COUCHE_MAX


def test_valeurs_du_classeur():
    ligne = lire_meteo("H1a", "th_bc").iloc[0]
    for colonne, valeur in H1A_TH_BC_HEURE_0.items():
        assert ligne[colonne] == pytest.approx(valeur, abs=1e-9), colonne
    ligne = lire_meteo("H1c", "th_d").iloc[6]
    for colonne, valeur in H1C_TH_D_HEURE_6.items():
        assert ligne[colonne] == pytest.approx(valeur, abs=1e-9), colonne


@pytest.mark.parametrize("zone", ZONES_CLIMATIQUES)
def test_th_d_au_moins_aussi_chaud_que_th_bc(zone):
    """Le jeu Th-D porte une séquence caniculaire : il diffère de Th-BC et son maximum n'est jamais plus bas.

    En H2c, les deux maximums sont égaux (40,89 °C) : l'égalité est donc admise.
    """
    th_bc, th_d = lire_meteo(zone, "th_bc")["te0"], lire_meteo(zone, "th_d")["te0"]
    assert th_d.max() >= th_bc.max()
    assert (th_d != th_bc).sum() > 800                 # au moins un mois d'heures différentes


@pytest.mark.parametrize("altitude, attendu", [(0, 100), (400, 100), (400.1, 500), (800, 500), (801, 900), (1500, 900)])
def test_paliers_d_altitude(altitude, attendu):
    assert altitude_corrigee(altitude) == attendu


def test_correction_d_altitude_a_la_main():
    """H1a Th-BC, heure 0 : te0 = 5,835 °C, we0 = 5,4565 g/kg, Teau0 = 9,4 °C."""
    # Site à 650 m → altcorr = 500 m
    ligne = charger_meteo("H1a", "th_bc", altitude=650).iloc[0]
    assert ligne["te"] == pytest.approx(5.835 - 0.005 * 500)             # 3,335 °C
    assert ligne["we"] == pytest.approx((5.4565 - 0.0025 * 500) / 1000)  # 0,0042065 kg/kg
    assert ligne["teau"] == pytest.approx(9.4 - 0.005 * 500)             # 6,9 °C
    # Au niveau de la mer, la méthode retient quand même 100 m : −0,5 °C
    assert charger_meteo("H1a", "th_bc", altitude=0).iloc[0]["te"] == pytest.approx(5.335)
    # Les colonnes d'origine ne sont pas modifiées
    assert ligne["te0"] == pytest.approx(5.835)


def test_zone_ou_jeu_inconnu():
    with pytest.raises(ValueError):
        lire_meteo("H4", "th_bc")
    with pytest.raises(ValueError):
        lire_meteo("H1a", "th_c")


@pytest.mark.skipif(not os.path.exists(CLASSEUR_METEO), reason="classeur officiel absent de _references/")
def test_identique_au_classeur_officiel():
    """Comparaison complète d'un onglet au CSV (seulement si le classeur est présent en local)."""
    import openpyxl
    classeur = openpyxl.load_workbook(CLASSEUR_METEO, read_only=True, data_only=True)
    for zone, jeu in (("H2d", "th_d"), ("H3", "th_bc")):
        lignes = [l[:10] for l in classeur[f"{zone}_{JEUX_METEO[jeu]}"].iter_rows(min_row=2, values_only=True)
                  if l[0] is not None]
        meteo = lire_meteo(zone, jeu).to_numpy()
        assert meteo.shape == (8760, 10)
        assert abs(meteo - [[float(v) for v in l] for l in lignes]).max() < 1e-9
