"""Masques solaires (annexe III, fiche 3.2) : cas analytiques à 1 %, cas limites et combinaison."""

import math

import numpy as np
import pandas as pd
import pytest

from moteur.solaire import environnement_proche
from moteur.structures import (Baie, MasqueLointainVertical, MasqueProcheHorizontal, MasqueProcheVertical,
                               MasqueTranches, Paroi)

ANALYTIQUE = 0.01


def meteo_test(gamma, psi):
    gamma = np.atleast_1d(np.asarray(gamma, dtype=float))
    n = len(gamma)
    return pd.DataFrame({"dirN": np.full(n, 800.0), "diff": np.full(n, 100.0), "Gamma": gamma,
                         "Psi": np.broadcast_to(np.asarray(psi, dtype=float), (n,)).copy(),
                         "Teciel": np.full(n, 10.0), "te": np.full(n, 20.0)})


def baie_sud(*masques, largeur=2.0, hauteur=2.0, inclinaison=90.0):
    return Baie("Baie", largeur * hauteur, orientation_deg=0, inclinaison_deg=inclinaison, sw_e=0.5,
                largeur_m=largeur, hauteur_m=hauteur, masques=list(masques))


def facteurs(baie, gamma, psi):
    env = environnement_proche(meteo_test(gamma, psi), baie)
    return env["f_dir"].to_numpy(), env["f_dif"].to_numpy()


# ============================================================
# MASQUE PROCHE HORIZONTAL (éq. 20 et 21)
# ============================================================
def test_debord_moitie_a_l_ombre():
    """Soleil plein sud à 45°, débord de 1 m au ras d'une baie de 2 m : ombre de 1 m, F = 0,5."""
    f_dir, _ = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=1.0)), 45.0, 0.0)
    assert f_dir[0] == pytest.approx(0.5, rel=ANALYTIQUE)


def test_debord_angle_de_profil():
    """Soleil à 60° de la normale : ombre = dhm.tan(gamma)/cos(phi) = 1 × 1 / 0,5 = 2 m : baie entière à l'ombre."""
    f_dir, _ = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=1.0)), 45.0, 60.0)
    assert f_dir[0] == pytest.approx(0.0, abs=1e-9)


def test_debord_distant():
    """Débord à 0,5 m au-dessus de la baie : ombre utile 1 − 0,5 = 0,5 m sur 2 m, F = 0,75."""
    f_dir, _ = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=1.0, distance_m=0.5)), 45.0, 0.0)
    assert f_dir[0] == pytest.approx(0.75, rel=ANALYTIQUE)


def test_debord_diffus():
    """Éq. 21 : theta_g = arctan((0 + 2/2) / 1) = 45° → F = 0,5 ; débord très court → F proche de 1."""
    _, f_dif = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=1.0)), 45.0, 0.0)
    assert f_dif[0] == pytest.approx(0.5, rel=ANALYTIQUE)
    _, f_dif = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=1e-6)), 45.0, 0.0)
    assert f_dif[0] == pytest.approx(1.0, rel=ANALYTIQUE)


def test_debord_nul_sans_effet():
    f_dir, f_dif = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=0.0)), 45.0, 0.0)
    assert f_dir[0] == 1.0 and f_dif[0] == 1.0


def test_masque_proche_ignore_si_non_vertical():
    """Fiche 3.2 : masques proches réservés aux composants verticaux."""
    f_dir, f_dif = facteurs(baie_sud(MasqueProcheHorizontal(debord_m=5.0), inclinaison=60.0), 45.0, 0.0)
    assert f_dir[0] == 1.0 and f_dif[0] == 1.0


# ============================================================
# MASQUES PROCHES VERTICAUX (éq. 19)
# ============================================================
def test_joue_gauche_soleil_a_l_ouest():
    """Soleil à 45° à l'ouest d'une baie sud : la joue gauche (côté ouest, vue de dehors) ombre 1 m sur 2."""
    f_dir, _ = facteurs(baie_sud(MasqueProcheVertical("gauche", debord_m=1.0)), 30.0, 45.0)
    assert f_dir[0] == pytest.approx(0.5, rel=ANALYTIQUE)


def test_joue_droite_soleil_a_l_ouest_sans_effet():
    f_dir, _ = facteurs(baie_sud(MasqueProcheVertical("droite", debord_m=1.0)), 30.0, 45.0)
    assert f_dir[0] == 1.0


def test_joue_droite_soleil_a_l_est():
    f_dir, _ = facteurs(baie_sud(MasqueProcheVertical("droite", debord_m=1.0, distance_m=0.5)), 30.0, -45.0)
    assert f_dir[0] == pytest.approx(0.75, rel=ANALYTIQUE)


def test_loggia_combinaison():
    """Loggia : débord + deux joues, facteurs multipliés (éq. 23) ; diffus du seul débord."""
    baie = baie_sud(MasqueProcheHorizontal(debord_m=1.0), MasqueProcheVertical("gauche", debord_m=1.0),
                    MasqueProcheVertical("droite", debord_m=1.0))
    f_dir, f_dif = facteurs(baie, 45.0, 45.0)
    # débord : ombre = tan(45°)/cos(45°) = 1,414 m → 1 − 0,707 ; joue gauche : 0,5 ; joue droite : 1
    assert f_dir[0] == pytest.approx((1.0 - math.sqrt(2.0) / 2.0) * 0.5, rel=ANALYTIQUE)
    assert f_dif[0] == pytest.approx(0.5, rel=ANALYTIQUE)


def test_soleil_derriere_le_plan():
    """cos(phi) < 1e-5 : le soleil n'entre pas dans le plan, les masques sont sans effet."""
    baie = baie_sud(MasqueProcheHorizontal(debord_m=1.0), MasqueProcheVertical("gauche", debord_m=1.0),
                    MasqueLointainVertical(distance_m=10.0, hauteur_m=50.0))
    f_dir, _ = facteurs(baie, 20.0, 120.0)
    assert f_dir[0] == 1.0


# ============================================================
# MASQUES LOINTAINS (éq. 22 et tranches azimutales)
# ============================================================
@pytest.mark.parametrize("hauteur, attendu", [(5.0, 1.0), (15.0, 0.0), (0.0, 1.0)])
def test_plan_vertical_lointain(hauteur, attendu):
    """Immeuble à 10 m, soleil plein sud à 45° : le rayon passe à 10 m de haut au droit du masque."""
    f_dir, f_dif = facteurs(baie_sud(MasqueLointainVertical(distance_m=10.0, hauteur_m=hauteur)), 45.0, 0.0)
    assert f_dir[0] == attendu
    assert f_dif[0] == 1.0


def test_plan_vertical_lointain_sur_toiture():
    """Composant horizontal : l'orientation du masque est requise et sert de référence."""
    toit = Paroi("Toit", "toiture", 10.0, inclinaison_deg=0,
                 masques=[MasqueLointainVertical(distance_m=10.0, hauteur_m=15.0, orientation_deg=0)])
    env = environnement_proche(meteo_test([45.0, 60.0], 0.0), toit)
    assert env["f_dir"].tolist() == [0.0, 1.0]       # tan(60°) × 10 = 17,3 m > 15 m
    sans_orientation = Paroi("Toit", "toiture", 10.0, inclinaison_deg=0,
                             masques=[MasqueLointainVertical(distance_m=10.0, hauteur_m=15.0)])
    with pytest.raises(ValueError):
        environnement_proche(meteo_test(45.0, 0.0), sans_orientation)


def test_tranches_azimutales():
    """Horizon à 20° partout sauf la tranche [0° ; 10°[ (19e) à 50°."""
    hauteurs = [20.0] * 36
    hauteurs[18] = 50.0
    baie = baie_sud(MasqueTranches(hauteurs))
    f_dir, f_dif = facteurs(baie, [30.0, 10.0, 30.0, 60.0], [-5.0, -5.0, 5.0, 5.0])
    assert f_dir.tolist() == [1.0, 0.0, 0.0, 1.0]
    assert f_dif.tolist() == [1.0] * 4


def test_isr_avec_masque_total():
    """Masque lointain infranchissable : il ne reste que le diffus et le réfléchi."""
    baie = baie_sud(MasqueLointainVertical(distance_m=1.0, hauteur_m=1000.0))
    env = environnement_proche(meteo_test(30.0, 0.0), baie)
    assert env["drp_m"].iloc[0] == 0.0
    assert env["isr"].iloc[0] == pytest.approx(env["dfp"].iloc[0] + env["rrp"].iloc[0])
    assert env["erp_m"].iloc[0] == 0.0


# ============================================================
# SAISIE
# ============================================================
@pytest.mark.parametrize("fabrique", [
    lambda: MasqueProcheVertical("haut", debord_m=1.0),
    lambda: MasqueProcheHorizontal(debord_m=-1.0),
    lambda: MasqueLointainVertical(distance_m=0.0, hauteur_m=5.0),
    lambda: MasqueTranches([10.0] * 35),
    lambda: MasqueTranches([95.0] * 36),
    lambda: Baie("B", 2.0, orientation_deg=0, masques=[MasqueProcheHorizontal(debord_m=1.0)]),
    lambda: Baie("B", 2.0, orientation_deg=0, masques=["balcon"]),
])
def test_masques_refuses(fabrique):
    with pytest.raises(ValueError):
        fabrique()
