"""Rayonnement sur une paroi orientée (annexe III, fiche 3.2) et flux solaires transmis (fiches 5.10, 5.17).

Cas analytiques à 1 %, bilans à 0,1 %, ordres de grandeur sur les fichiers météo (plan de contrôle).
"""

import math

import numpy as np
import pandas as pd
import pytest

from config.reglages import ZONES_CLIMATIQUES
from moteur.hypotheses import hyp
from moteur.meteo import charger_meteo
from moteur.solaire import (eclairement_exterieur, environnement_proche, facteurs_solaires_paroi,
                            flux_solaires_baie, flux_solaires_paroi, jour_astro, sw_baie)
from moteur.structures import Baie, Paroi

ANALYTIQUE = 0.01       # plan de contrôle : 1 % sur les cas analytiques
BILAN = 0.001           # plan de contrôle : 0,1 % sur les bilans


def meteo_test(gamma, psi, dirn=800.0, diff=100.0, te=20.0, teciel=10.0):
    """Météo synthétique d'une ou plusieurs heures (mêmes colonnes que charger_meteo)."""
    gamma = np.atleast_1d(np.asarray(gamma, dtype=float))
    n = len(gamma)
    return pd.DataFrame({"dirN": np.full(n, dirn), "diff": np.full(n, diff), "Gamma": gamma,
                         "Psi": np.broadcast_to(np.asarray(psi, dtype=float), (n,)).copy(),
                         "Teciel": np.full(n, teciel), "te": np.full(n, te)})


def mur(orientation, **options):
    return Paroi("Mur", "mur", 10.0, u=0.25, orientation_deg=orientation, **options)


# ============================================================
# CAS ANALYTIQUES (fiche 3.2, éq. 7 à 11)
# ============================================================
def test_soleil_dans_l_axe_de_la_normale():
    """Paroi sud inclinée à 60°, soleil plein sud à 30° : la normale vise le soleil, Drp = IDn."""
    env = environnement_proche(meteo_test(30.0, 0.0), Paroi("Toit", "toiture", 1.0, orientation_deg=0,
                                                              inclinaison_deg=60))
    assert env["cos_theta"].iloc[0] == pytest.approx(1.0, rel=ANALYTIQUE)
    assert env["drp"].iloc[0] == pytest.approx(800.0, rel=ANALYTIQUE)


def test_paroi_horizontale():
    """Toiture : Drp = IDn.sin(gamma), tout le diffus, aucun réfléchi, orientation inutile."""
    env = environnement_proche(meteo_test(40.0, 30.0), Paroi("Toit", "toiture", 1.0, inclinaison_deg=0))
    assert env["drp"].iloc[0] == pytest.approx(800.0 * math.sin(math.radians(40)), rel=ANALYTIQUE)
    assert env["dfp"].iloc[0] == pytest.approx(100.0, rel=ANALYTIQUE)
    assert env["rrp"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_mur_vertical_sud():
    """Mur sud, soleil plein sud à 30° : Drp = IDn.cos(30°), Dfp = Idi/2, Rrp = alb/2 × global horizontal."""
    env = environnement_proche(meteo_test(30.0, 0.0), mur(0))
    assert env["drp"].iloc[0] == pytest.approx(800.0 * math.cos(math.radians(30)), rel=ANALYTIQUE)
    assert env["dfp"].iloc[0] == pytest.approx(50.0, rel=ANALYTIQUE)
    global_horizontal = 800.0 * 0.5 + 100.0
    assert env["rrp"].iloc[0] == pytest.approx(0.2 * 0.5 * global_horizontal, rel=ANALYTIQUE)


def test_mur_nord_a_midi_sans_direct():
    env = environnement_proche(meteo_test(30.0, 0.0), mur(180))
    assert env["drp"].iloc[0] == 0.0
    assert env["dfp"].iloc[0] > 0


def test_symetrie_est_ouest():
    """Soleil à 45° à l'est du sud puis à 45° à l'ouest : mêmes apports sur le mur est puis le mur ouest."""
    est = environnement_proche(meteo_test(25.0, -45.0), mur(-90))
    ouest = environnement_proche(meteo_test(25.0, 45.0), mur(90))
    assert est["isr"].iloc[0] == pytest.approx(ouest["isr"].iloc[0], rel=1e-12)
    assert est["drp"].iloc[0] == pytest.approx(800.0 * math.cos(math.radians(25)) * math.cos(math.radians(45)),
                                               rel=ANALYTIQUE)


def test_orientation_270_egale_moins_90():
    """La fiche 3.2 note l'est 270° ; structures.py le ramène à −90°, sans changer le résultat."""
    assert mur(270).orientation_deg == -90.0
    m = meteo_test([10.0, 30.0, 50.0], [-100.0, -60.0, -10.0])
    assert environnement_proche(m, mur(270))["isr"].tolist() == environnement_proche(m, mur(-90))["isr"].tolist()


def test_plancher_vers_le_bas():
    """Inclinaison 180° : ni diffus ni réfléchi (1 − |cos beta| = 0), ni direct tant que le soleil est levé."""
    env = environnement_proche(meteo_test(30.0, 0.0), Paroi("Plancher", "plancher_bas", 1.0, inclinaison_deg=180))
    assert env["isr"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_direct_avec_soleil_a_l_horizon():
    """Hypothèse 0.8.2 (docs/audit.md) : formule telle quelle, direct non nul sur un mur vertical à gamma = 0."""
    env = environnement_proche(meteo_test(0.0, -90.0, dirn=75.0), mur(-90))
    assert env["drp"].iloc[0] == pytest.approx(75.0, rel=ANALYTIQUE)
    assert jour_astro(meteo_test(0.0, -90.0)).iloc[0] == 0


def test_jour_astro():
    assert jour_astro(meteo_test([0.0, 0.001, 0.01, 20.0], 0.0)).tolist() == [0, 0, 1, 1]


# ============================================================
# RAYONNEMENT FROID ET ÉCLAIREMENT
# ============================================================
def test_rayonnement_froid():
    """Éq. 17 : Qer = hre.(Teciel − Te).Max(cos beta ; 0) : plein sur une toiture, nul sur un mur."""
    m = meteo_test(30.0, 0.0, te=20.0, teciel=10.0)
    toit = environnement_proche(m, Paroi("Toit", "toiture", 1.0, inclinaison_deg=0))
    assert toit["qer"].iloc[0] == pytest.approx(5.5 * (10.0 - 20.0), rel=ANALYTIQUE)
    assert environnement_proche(m, mur(0))["qer"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_efficacite_lumineuse():
    """Fiche 3.1 : environ 104 lm/W à 30° de hauteur ; efficacité positive et < 130 lm/W de 0 à 90°."""
    ecl = eclairement_exterieur(meteo_test(30.0, 0.0, dirn=1.0, diff=0.0))
    assert ecl["edn"].iloc[0] == pytest.approx(103.7, rel=ANALYTIQUE)
    efficacites = eclairement_exterieur(meteo_test(np.arange(0.0, 90.5, 0.5), 0.0, dirn=1.0))["edn"]
    assert (efficacites > 0).all() and (efficacites < 130).all()


@pytest.mark.parametrize("dirn, efficacite", [(0.0, 124), (0.5, 124), (1.0, 116), (120.0, 116), (121.0, 128)])
def test_efficacite_diffuse(dirn, efficacite):
    assert eclairement_exterieur(meteo_test(20.0, 0.0, dirn=dirn, diff=10.0))["edi"].iloc[0] == 10.0 * efficacite


# ============================================================
# BILANS ET ORDRES DE GRANDEUR SUR LA MÉTÉO RÉELLE
# ============================================================
@pytest.mark.parametrize("zone", ZONES_CLIMATIQUES)
def test_bilan_horizontal(zone):
    """Sur une toiture, direct + diffus reçus = global horizontal du fichier (IDn.sin(gamma) + Idi)."""
    m = charger_meteo(zone, "th_bc")
    env = environnement_proche(m, Paroi("Toit", "toiture", 1.0, inclinaison_deg=0))
    attendu = (m["dirN"] * np.sin(np.radians(m["Gamma"])) + m["diff"]).sum()
    assert env["isr"].sum() == pytest.approx(attendu, rel=BILAN)


@pytest.mark.parametrize("zone", ZONES_CLIMATIQUES)
def test_ordres_de_grandeur(zone):
    """Irradiation annuelle (kWh/m²) : horizontale entre 1 000 et 1 800, sud > est, ouest > nord."""
    m = charger_meteo(zone, "th_bc")
    annuel = {nom: environnement_proche(m, composant)["isr"].sum() / 1000.0 for nom, composant in {
        "horizontal": Paroi("Toit", "toiture", 1.0, inclinaison_deg=0),
        "sud": mur(0), "ouest": mur(90), "nord": mur(180), "est": mur(-90)}.items()}
    assert 1000 < annuel["horizontal"] < 1800
    assert annuel["sud"] > annuel["est"] > annuel["nord"]
    assert annuel["sud"] > annuel["ouest"] > annuel["nord"]


def test_mediterranee_plus_ensoleillee_que_le_nord():
    def horizontal(zone):
        m = charger_meteo(zone, "th_bc")
        return environnement_proche(m, Paroi("Toit", "toiture", 1.0, inclinaison_deg=0))["isr"].sum()
    assert horizontal("H3") > horizontal("H1a")


# ============================================================
# FACTEURS SOLAIRES ET FLUX TRANSMIS
# ============================================================
def test_sw_par_jeu():
    baie = Baie("Fenêtre", 2.0, orientation_deg=0, uw=1.3, sw_e=0.45)
    assert sw_baie(baie, "th_d") == 0.45
    assert sw_baie(baie, "th_bc") == pytest.approx(0.35)          # éq. 215 : Sw-e − 0,1
    baie.sw_c = 0.40
    assert sw_baie(baie, "th_bc") == 0.40


def test_facteurs_solaires_paroi_th_bat():
    """Formules 259-260 : alpha = 0,6, Up-C = 0,25 → Sf-c = 0,006 ; Up-E = 1/(4 + 0,03) → Sf-e ≈ 0,01042."""
    sf_c, sf_e = facteurs_solaires_paroi(mur(0, alpha=0.6))
    assert sf_c == pytest.approx(0.6 * 0.25 * 0.04, rel=ANALYTIQUE)
    assert sf_e == pytest.approx(0.6 / 4.03 * 0.07, rel=ANALYTIQUE)
    assert facteurs_solaires_paroi(mur(0, sf_c=0.02, sf_e=0.03)) == (0.02, 0.03)
    with pytest.raises(ValueError):
        facteurs_solaires_paroi(Paroi("Mur", "mur", 10.0, orientation_deg=0))


def test_flux_baie():
    m = meteo_test(30.0, 0.0)
    baie = Baie("Fenêtre", 2.0, orientation_deg=0, uw=1.3, sw_e=0.45)
    flux = flux_solaires_baie(baie, m, "th_bc")
    assert flux["fs"].iloc[0] == pytest.approx(2.0 * 0.35 * environnement_proche(m, baie)["isr"].iloc[0])
    assert flux["ftvc"].iloc[0] == pytest.approx(0.0, abs=1e-9)    # baie verticale : pas de voûte céleste


def test_flux_paroi_th_bc_et_th_d():
    m = meteo_test([30.0, 30.0], 0.0)
    toit = Paroi("Toit", "toiture", 100.0, u=0.2, inclinaison_deg=0, sf_c=0.01, sf_e=0.02)
    isr = environnement_proche(m, toit)["isr"]
    th_bc = flux_solaires_paroi(toit, m, "th_bc")
    assert th_bc["phi_s"].tolist() == pytest.approx((100.0 * 0.01 * isr).tolist())
    assert th_bc["phi_vc"].iloc[0] == pytest.approx(100.0 * 5.5 * (10.0 - 20.0) * 0.2 / 25.0)
    th_d = flux_solaires_paroi(toit, m, "th_d", confort_adaptatif=[0, 1])   # Sf-c puis Sf-e
    assert th_d["phi_s"].tolist() == pytest.approx([100.0 * 0.01 * isr.iloc[0], 100.0 * 0.02 * isr.iloc[1]])
    with pytest.raises(ValueError):
        flux_solaires_paroi(toit, m, "th_d")


def test_paroi_non_exterieure_sans_soleil():
    m = meteo_test(30.0, 0.0)
    plancher = Paroi("Plancher", "plancher_bas", 50.0, u=0.2, inclinaison_deg=180, contact="sol")
    assert (flux_solaires_paroi(plancher, m, "th_bc") == 0).all().all()


def test_hypotheses_solaires_sourcees():
    for cle in ("albedo_sol", "hre", "he", "rse_c", "rse_e", "ecart_sw_c_e", "seuil_entree_soleil"):
        assert hyp(cle) >= 0


# ============================================================
# 0.8.4 : DÉCOMPOSITION Sw1 / Sw2 / Sw3 ET U SELON L'INCLINAISON
# ============================================================
def test_decomposition_du_flux_des_baies():
    """Fs = Fs1 + Fs2 + Fs3 (fiche 5.10, éq. 219 à 221) ; Sw2 nul par défaut, Sw3 nul sans protection."""
    from moteur.solaire import sw2_baie
    m = meteo_test(30.0, 0.0)
    baie = Baie("Fenêtre", 2.0, orientation_deg=0, uw=1.3, sw_e=0.45)
    flux = flux_solaires_baie(baie, m, "th_d")
    assert sw2_baie(baie, "th_d") == pytest.approx(hyp("sw2_part_defaut") * 0.45)
    assert flux["fs1"].iloc[0] == pytest.approx(flux["fs"].iloc[0]) and flux["fs2"].iloc[0] == 0
    assert flux["fs3"].iloc[0] == 0
    # Sw2 saisi : Sw1 = Sw − Sw2, par jeu
    baie = Baie("Fenêtre", 2.0, orientation_deg=0, uw=1.3, sw_e=0.45, sw2_e=0.05, sw_c=0.40, sw2_c=0.08)
    isr = environnement_proche(m, baie)["isr"].iloc[0]
    th_d, th_bc = flux_solaires_baie(baie, m, "th_d"), flux_solaires_baie(baie, m, "th_bc")
    assert th_d["fs1"].iloc[0] == pytest.approx(2.0 * 0.40 * isr)
    assert th_d["fs2"].iloc[0] == pytest.approx(2.0 * 0.05 * isr)
    assert th_bc["fs1"].iloc[0] == pytest.approx(2.0 * 0.32 * isr)
    assert th_bc["fs2"].iloc[0] == pytest.approx(2.0 * 0.08 * isr)
    for flux in (th_d, th_bc):
        assert (flux["fs1"] + flux["fs2"] + flux["fs3"]).iloc[0] == pytest.approx(flux["fs"].iloc[0])
    with pytest.raises(ValueError, match="Sw2"):
        flux_solaires_baie(Baie("Fenêtre", 2.0, orientation_deg=0, uw=1.3, sw_e=0.45, sw2_e=0.6), m, "th_d")


def test_rayonnement_froid_avec_u_incline():
    """Le rayonnement froid utilise le U de la position réelle (fiches 5.10, éq. 207, et 5.17, éq. 294)."""
    m = meteo_test(30.0, 0.0)
    # Fenêtre de toit horizontale : Uw horizontal
    baie = Baie("Toit", 2.0, orientation_deg=0, inclinaison_deg=0, uw=1.3, uw_horizontal=1.8, sw_e=0.45)
    assert flux_solaires_baie(baie, m, "th_bc")["ftvc"].iloc[0] == pytest.approx(
        2.0 * 1.8 * 5.5 * (10.0 - 20.0) / 25.0)
    # Mur de U = 0,25 couché en toiture : U = 1 / (1/0,25 − 0,17 + 0,14)
    couche = Paroi("Mur", "mur", 100.0, u=0.25, inclinaison_deg=0, sf_c=0.01, sf_e=0.02)
    assert flux_solaires_paroi(couche, m, "th_bc")["phi_vc"].iloc[0] == pytest.approx(
        100.0 * 5.5 * (10.0 - 20.0) / (1 / 0.25 - 0.17 + 0.14) / 25.0)
