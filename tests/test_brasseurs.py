"""Brasseurs d'air (annexe III, fiche 8.32) : paramètres, ratios, hystérésis, effet, agrégation, consommation."""

import math

import numpy as np
import pandas as pd
import pytest

from moteur.brasseurs import (ARRET, INTERMEDIAIRE, MAXIMAL, COLONNES_ENTREES, consignes, ecart_operatif, est_jour,
                              parametres_corriges, pas_brasseurs, preparer_brasseurs, ratio_brasse, regime_suivant,
                              simuler_brasseurs, vitesse_air)
from moteur.hypotheses import lire_hypotheses
from moteur.structures import Brasseur, Groupe

ANALYTIQUE = 0.01


def brasseur(nom="B", **options):
    valeurs = dict(nombre=1, surface_desservie_m2=20.0, debit_max_m3h=5000.0, puissance_max_w=50.0,
                   caractere_debit="certifiee", caractere_puissance="certifiee")
    valeurs.update(options)
    return Brasseur(nom, **valeurs)


def groupe(*brasseurs, surface=60.0, volume=150.0):
    return Groupe("Logements", surface, volume_m3=volume, brasseurs=list(brasseurs))


def regime(b, theta_op_prec, regime_prec=ARRET, case=12, actif=True, occupe=True, habitation=True,
           theta_ifr=26.0, ecart_conf_adapt=0.0):
    return regime_suivant(b, regime_prec, theta_op_prec, case, actif, occupe, theta_ifr, ecart_conf_adapt,
                          habitation)


# ============================================================
# EFFET SUR LE RESSENTI (éq. 1658-1659)
# ============================================================
def test_effet_a_un_metre_par_seconde():
    """v = 1 m/s, θrm = θi : ln v = 0, Δθ = 3,0498 °C."""
    assert ecart_operatif(1.0, 27.0, 27.0) == pytest.approx(3.0498, rel=ANALYTIQUE)


def test_effet_avec_ecart_radiant():
    """v = e m/s (ln v = 1), θrm − θi = 2 °C : Δθ = 1,8322 e^0,0722 + 3,0498 e^0,0736."""
    attendu = 1.8322 * math.exp(0.0722) + 3.0498 * math.exp(0.0736)
    assert ecart_operatif(math.e, 29.0, 27.0) == pytest.approx(attendu, rel=ANALYTIQUE)


def test_seuil_de_vitesse():
    """Nul jusqu'à 0,2 m/s inclus ; juste au-dessus, la formule donne déjà ≈ 0,10 °C (saut, voir audit)."""
    assert ecart_operatif(0.2, 27.0, 27.0) == 0.0
    assert ecart_operatif(0.2001, 27.0, 27.0) == pytest.approx(1.8322 * math.log(0.2001) + 3.0498, rel=ANALYTIQUE)


# ============================================================
# PARAMÈTRES ET RATIOS
# ============================================================
@pytest.mark.parametrize("caractere, coef_q, coef_p", [("certifiee", 1.0, 1.0), ("justifiee", 0.9, 1.1),
                                                        ("declaree", 0.8, 1.2)])
def test_parametres_corriges(caractere, coef_q, coef_p):
    b = brasseur(debit_max_m3h=10000.0, puissance_max_w=50.0, caractere_debit=caractere,
                 caractere_puissance=caractere)
    q_max, q_int, p_max, p_int = parametres_corriges(b)
    assert (q_max, q_int) == pytest.approx((10000 * coef_q, 6000 * coef_q))
    assert (p_max, p_int) == pytest.approx((50 * coef_p, 30 * coef_p))


def test_ratio_brasse_plafonne_a_15_m2_par_brasseur():
    assert ratio_brasse(brasseur(surface_desservie_m2=20.0), 60.0) == pytest.approx(15 / 60)
    assert ratio_brasse(brasseur(nombre=2, surface_desservie_m2=20.0), 60.0) == pytest.approx(20 / 60)


def test_coherence_surface_brassee():
    """Jour : RatUs = 0,54 en logement collectif ; 2 × 15 m² sur 50 m² = 0,6 > 0,54 → erreur."""
    with pytest.raises(ValueError, match="surface occupée"):
        preparer_brasseurs(groupe(brasseur("A"), brasseur("B"), surface=50.0))
    assert len(preparer_brasseurs(groupe(brasseur("A"), brasseur("B"), surface=60.0))) == 2   # 0,5 ≤ 0,54


def test_jour_et_nuit_exclusif():
    with pytest.raises(ValueError, match="jour et nuit"):
        preparer_brasseurs(groupe(brasseur("A", usage="jour_et_nuit"), brasseur("B", usage="nuit")))


# ============================================================
# GESTION — RÉGULATION (éq. 1646 à 1654)
# ============================================================
def test_consignes():
    """Manuelle : V1 = 26 + 1,5 + 1 ; thermostat : saisi ; automatique : θop_dec fixe + Δθop_3 (0 par défaut)."""
    assert consignes(brasseur(), 26.0, 1.5) == pytest.approx((26.5, 28.5, 32.5))
    thermo = brasseur(gestion="thermostat", ecart_arret=1.0, ecart_max=3.0, ecart_declenchement=0.5)
    assert consignes(thermo, 26.0, 1.5) == pytest.approx((27.0, 28.0, 31.0))
    auto = brasseur(gestion="automatique", ecart_arret=1.0, ecart_max=2.0, temperature_declenchement=27.0)
    assert consignes(auto, 26.0, 1.5) == pytest.approx((26.0, 27.0, 29.0))


def test_hysteresis_manuelle():
    """arr = 25, V1 = 27, V2 = 31 : montée, maintien, palier maximal, retour à l'arrêt."""
    b = brasseur()
    suite = [(26.0, ARRET), (27.0, INTERMEDIAIRE), (26.0, INTERMEDIAIRE), (31.0, MAXIMAL), (28.0, MAXIMAL),
             (25.0, MAXIMAL), (24.9, ARRET), (26.0, ARRET)]
    r = ARRET
    for theta, attendu in suite:
        r = regime(b, theta, r)
        assert r == attendu, f"θop(h−1) = {theta}"


def test_arret_hors_periode_occupation_ou_plage():
    jour, nuit = brasseur(), brasseur(usage="nuit")
    assert regime(jour, 35.0, actif=False) == ARRET
    assert regime(jour, 35.0, occupe=False) == ARRET
    assert regime(jour, 35.0, case=23) == ARRET        # 22h-23h : nuit
    assert regime(jour, 35.0, case=7) == MAXIMAL       # 6h-7h : jour
    assert regime(nuit, 35.0, case=12) == ARRET


def test_nuit_en_habitation_bridee():
    nuit = brasseur(usage="nuit")
    assert regime(nuit, 35.0, case=23) == INTERMEDIAIRE
    assert regime(nuit, 35.0, case=23, habitation=False) == MAXIMAL


def test_blocage_manuel_apres_23h():
    """Gestion manuelle, de 23h à 6h : position de l'heure précédente gardée ; pas en gestion par thermostat."""
    nuit = brasseur(usage="nuit")
    assert regime(nuit, 20.0, INTERMEDIAIRE, case=24) == INTERMEDIAIRE
    assert regime(nuit, 35.0, ARRET, case=3) == ARRET
    thermo = brasseur(usage="nuit", gestion="thermostat", ecart_arret=2.0, ecart_max=4.0, ecart_declenchement=1.0)
    assert regime(thermo, 20.0, INTERMEDIAIRE, case=24) == ARRET


def test_est_jour():
    assert [c for c in range(1, 25) if est_jour(c)] == list(range(7, 23))


# ============================================================
# EFFET DU GROUPE ET CONSOMMATION (éq. 1656 à 1666)
# ============================================================
def test_vitesse_et_effet_du_groupe():
    """60 m², 150 m³, 1 brasseur de 5 000 m³/h : Ratbr = 0,25, τ = 133,3 vol/h, v = 0,4267 m/s ;
    Δθ_p = 1,8322 ln 0,4267 + 3,0498 = 1,489 °C ; groupe, jour : 0,25 / 0,54 × 1,489 = 0,689 °C."""
    types = preparer_brasseurs(groupe(brasseur()))
    assert vitesse_air(types[0], MAXIMAL, 150.0) == pytest.approx(0.0032 * 5000 / (150 * 0.25), rel=ANALYTIQUE)
    res = pas_brasseurs(types, [MAXIMAL], 150.0, case=12, actif=True, occupe=True, theta_op_prec=35.0,
                        theta_i_prec=30.0, theta_rm_prec=30.0, theta_ifr=26.0, ecart_conf_adapt=0.0)
    ecart_p = 1.8322 * math.log(0.0032 * 5000 / 37.5) + 3.0498
    assert res["ecarts_types"][0] == pytest.approx(ecart_p, rel=ANALYTIQUE)
    assert res["ecart"] == pytest.approx(0.25 / 0.54 * ecart_p, rel=ANALYTIQUE)
    assert res["ecart_nuit"] == 0.0
    assert res["energie_wh"] == pytest.approx(50.0) and res["chaleur_wh"] == res["energie_wh"]


def test_jour_et_nuit_et_consommation_par_nombre():
    """Brasseur « jour et nuit » (RatUs = 1), 2 unités déclarées de 40 W au régime intermédiaire, la nuit."""
    b = brasseur(usage="jour_et_nuit", nombre=2, caractere_puissance="declaree", puissance_max_w=40.0)
    types = preparer_brasseurs(groupe(b))
    res = pas_brasseurs(types, [INTERMEDIAIRE], 150.0, case=2, actif=True, occupe=True, theta_op_prec=35.0,
                        theta_i_prec=30.0, theta_rm_prec=30.0, theta_ifr=26.0, ecart_conf_adapt=0.0)
    assert res["regimes"] == [INTERMEDIAIRE]
    assert res["ecart"] == res["ecart_nuit"] == res["ecart_jour"] == pytest.approx(
        types[0].ratio_brasse * res["ecarts_types"][0])
    assert res["energie_wh"] == pytest.approx(2 * 0.6 * 1.2 * 40.0)


# ============================================================
# DÉROULÉ HORAIRE
# ============================================================
def entrees(n=4, theta_op=32.0, case=12):
    return pd.DataFrame({"case": np.full(n, case), "actif": True, "occupe": True, "theta_op": theta_op,
                         "theta_i": 30.0, "theta_rm": 30.0, "theta_ifr": 26.0, "ecart_conf_adapt": 0.0})


def test_simulation():
    """Première heure à l'arrêt, puis vitesse maximale (θop = 32 ≥ V2 = 31)."""
    res = simuler_brasseurs(groupe(brasseur("salon")), entrees())
    assert list(res["regime_salon"]) == [ARRET, MAXIMAL, MAXIMAL, MAXIMAL]
    assert res["ecart_ba"].iloc[0] == 0.0 and res["ecart_ba"].iloc[1] > 0.5
    assert list(res["energie_wh"]) == pytest.approx([0.0, 50.0, 50.0, 50.0])


def test_simulation_sans_brasseur_et_colonnes():
    res = simuler_brasseurs(Groupe("Sans", 60.0), entrees())
    assert (res[["ecart_ba", "energie_wh"]].to_numpy() == 0).all()
    with pytest.raises(ValueError, match="Colonnes manquantes"):
        simuler_brasseurs(groupe(brasseur()), entrees().drop(columns="theta_rm"))
    assert set(COLONNES_ENTREES) == set(entrees().columns)


# ============================================================
# STRUCTURES ET HYPOTHÈSES
# ============================================================
def test_saisie_controlee():
    with pytest.raises(ValueError, match="volume"):
        Groupe("G", 60.0, brasseurs=[brasseur()])
    with pytest.raises(ValueError, match="réglages à saisir"):
        brasseur(gestion="thermostat")
    with pytest.raises(ValueError, match="usage"):
        brasseur(usage="soir")
    with pytest.raises(ValueError, match="entier"):
        brasseur(nombre=1.5)


def test_hypotheses_brasseurs_sourcees():
    table = lire_hypotheses()
    cles = [c for c in table if c.startswith("brasseur_")]
    assert len(cles) >= 19
    assert all("fiche 8.32" in table[c]["source"] for c in cles)
