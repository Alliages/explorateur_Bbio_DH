"""Modèle thermique horaire du groupe (annexe III, fiche 5.21)."""

import math

import numpy as np
import pandas as pd
import pytest

from moteur.calendrier import construire_calendrier
from moteur.groupe import (TEMPERATURES, avancer_etat, etat_initial, inertie_groupe, matrice_groupe, pas_groupe,
                           preparer_modele, simuler_groupe, sollicitations_groupe)
from moteur.meteo import charger_meteo
from moteur.structures import Baie, Brasseur, Groupe, Paroi, PontThermique

FLUX_DU_BILAN = ["flux_ventilation", "flux_baies", "flux_parois", "flux_apports", "flux_inerties_longues"]


# ------------------------------------------------------------------
# Outils
# ------------------------------------------------------------------
def meteo_constante(te, heures=2000):
    """Météo sans soleil ni rayonnement froid, à température extérieure constante."""
    return pd.DataFrame({"dirN": 0.0, "diff": 0.0, "Gamma": 0.0, "Psi": 0.0, "Teciel": te, "te": te},
                        index=range(heures))


def groupe_test(**options):
    """Logement de 50 m² : 2 murs, 2 baies, des ponts thermiques, une ventilation."""
    options.setdefault("parois", [Paroi("Sud", "mur", 20.0, u=0.25, orientation_deg=0, alpha=0.6),
                                  Paroi("Nord", "mur", 20.0, u=0.25, orientation_deg=180, alpha=0.6)])
    options.setdefault("baies", [Baie("Sud", 6.0, 0, uw=1.3, sw_e=0.5),
                                 Baie("Nord", 3.0, 180, uw=1.3, sw_e=0.5)])
    options.setdefault("ponts_thermiques", [PontThermique("Planchers", 30.0, 0.3)])
    options.setdefault("debit_ventilation_m3h", 75.0)
    return Groupe("Logement", 50.0, volume_m3=125.0, **options)


def regime_permanent(modele, heures=3000, **sollicitations):
    """Répète la même heure jusqu'à l'équilibre et rend le dernier résultat."""
    etat = etat_initial()
    for _ in range(heures):
        resultat = pas_groupe(modele, etat, **sollicitations)
        avancer_etat(modele, etat, resultat)
    return resultat


# ------------------------------------------------------------------
# Paramètres du modèle (éq. 311 à 332, 349 à 352, 370)
# ------------------------------------------------------------------
def test_parametres_du_modele():
    modele = preparer_modele(groupe_test(), "th_bc")
    # his = 2,5 + 1,2 × 5,5 = 9,1 ; Atparois = 4,5 × 50 = 225 m² ; Amq = 2,5 × 50 = 125 m² (inertie moyenne)
    assert modele.h_is == pytest.approx(9.1)
    assert modele.a_tparois == pytest.approx(225.0)
    assert modele.hg_is == pytest.approx(225.0 / (1 / 2.5 - 1 / 9.1))             # éq. 323
    assert modele.hg_ms == pytest.approx(9.1 * 125.0)                              # éq. 326
    assert modele.c_mq == pytest.approx(165.0 * 50.0 / 3.6)                        # éq. 320, en Wh/K
    assert modele.p_trm == pytest.approx(1 + 2.5 / 6.6)                            # éq. 370
    # Baies : 9 × 1,3 ; parois et ponts : 40 × 0,25 + 30 × 0,3 = 19 W/K
    assert modele.hg_es == pytest.approx(11.7)
    assert modele.h_th == pytest.approx(19.0)
    assert 1 / modele.hg_em + 1 / modele.hg_ms == pytest.approx(1 / 19.0)          # éq. 339
    # Répartitions (éq. 349 à 352) : chaque flux est entièrement distribué
    assert modele.fr_l_baies == pytest.approx(9.0 / 225.0)
    assert modele.fr_m == pytest.approx(125.0 / 225.0)
    assert modele.fr_l_baies + modele.fr_m + modele.fr_s == pytest.approx(1.0)
    assert modele.fr_sd + modele.fr_md == pytest.approx(1.0)
    assert modele.fr_md == pytest.approx(125.0 / 216.0)


@pytest.mark.parametrize("classe, amq, cmq", [("tres_legere", 2.5, 80), ("legere", 2.5, 110), ("moyenne", 2.5, 165),
                                              ("lourde", 3.0, 260), ("tres_lourde", 3.5, 370)])
def test_classes_d_inertie_quotidienne(classe, amq, cmq):
    inertie = inertie_groupe(Groupe("G", 50.0, inertie_quotidienne=classe))
    assert (inertie["amq"], inertie["cmq"]) == (amq, cmq)
    # Séquentielle et annuelle par défaut : mêmes valeurs que la quotidienne
    assert (inertie["ams"], inertie["cms"], inertie["ama"], inertie["cma"]) == (amq, cmq, amq, cmq)


def test_inerties_sequentielle_et_annuelle():
    inertie = inertie_groupe(Groupe("G", 50.0, inertie_quotidienne="tres_lourde", inertie_sequentielle="lourde"))
    assert (inertie["ams"], inertie["cms"]) == (3.0, 850)                # tableau 54 et Th-Bât, tableau 89
    assert (inertie["ama"], inertie["cma"]) == (3.0, 850)                # éq. 316
    perso = inertie_groupe(Groupe("G", 50.0, inertie_quotidienne="personnalisee", amq_surf=2.0, cmq_surf=100.0,
                                  inertie_sequentielle="personnalisee", ams_surf=1.5, cms_surf=400.0,
                                  inertie_annuelle="personnalisee", ama_surf=1.0, cma_surf=6000.0))
    assert perso == {"amq": 2.0, "cmq": 100.0, "ams": 1.5, "cms": 400.0, "ama": 1.0, "cma": 6000.0}


def test_inerties_longues_seulement_en_th_d():
    groupe = groupe_test(inertie_quotidienne="tres_lourde", inertie_sequentielle="lourde",
                         inertie_annuelle="personnalisee", ama_surf=1.0, cma_surf=6000.0)
    th_bc, th_d = preparer_modele(groupe, "th_bc"), preparer_modele(groupe, "th_d")
    assert (th_bc.dhg_seq, th_bc.dhg_ann) == (0.0, 0.0)
    # ΔHg = 1 / (1/(his.Ams) − 1/(his.Amq)), Ams = 150 m², Amq = 175 m² (éq. 327 à 329)
    assert th_d.dhg_seq == pytest.approx(1 / (1 / (9.1 * 150) - 1 / (9.1 * 175)))
    assert th_d.dc_seq == pytest.approx((850 - 370) * 50 / 3.6)          # éq. 331
    assert th_d.dhg_ann == pytest.approx(1 / (1 / (9.1 * 50) - 1 / (9.1 * 175)))
    assert th_d.dc_ann == pytest.approx((6000 - 850) * 50 / 3.6)         # éq. 332
    # Surfaces d'échange égales : résistances égales, donc pas de couplage (note sous l'éq. 329)
    assert preparer_modele(groupe_test(inertie_sequentielle="moyenne"), "th_d").dhg_seq == 0.0


def test_modele_inapplicable():
    with pytest.raises(ValueError, match="inapplicable"):
        preparer_modele(Groupe("Passoire", 10.0, parois=[Paroi("Mur", "mur", 100.0, u=3.0, orientation_deg=0)]),
                        "th_bc")
    with pytest.raises(ValueError, match="dépassent"):
        preparer_modele(Groupe("Serre", 10.0, inertie_quotidienne="tres_lourde",
                               baies=[Baie("B", 20.0, 0, uw=1.3, sw_e=0.5)]), "th_bc")


# ------------------------------------------------------------------
# Régime permanent : cas analytiques (à 1 %)
# ------------------------------------------------------------------
def test_regime_permanent_parois_et_ventilation():
    # Sans baie : un apport convectif Φ s'évacue par la ventilation (Hv) et par les parois, en série avec
    # l'échange interne Hg_is : θi = te + Φ / (Hv + 1 / (1/Hg_is + 1/H_TH))
    modele = preparer_modele(groupe_test(baies=[]), "th_bc")
    hv, phi = 0.34 * 75.0, 500.0
    r = regime_permanent(modele, te=5.0, hg_ei=hv, phi_conv=phi)
    attendu = 5.0 + phi / (hv + 1 / (1 / modele.hg_is + 1 / modele.h_th))
    assert r["theta_i"] == pytest.approx(attendu, rel=1e-6)
    assert r["theta_i_moy"] == pytest.approx(r["theta_i"], abs=1e-6)
    assert r["stockage"] == pytest.approx(0.0, abs=1e-6)
    # Sans apport, tout le groupe est à la température extérieure
    r = regime_permanent(modele, te=5.0, hg_ei=hv)
    assert [r[nom] for nom in TEMPERATURES] == pytest.approx([5.0] * 5)


def test_regime_permanent_avec_baies():
    # À l'équilibre, les déperditions égalent les apports ; l'air, source de chaleur, est le plus chaud
    modele = preparer_modele(groupe_test(), "th_bc")
    r = regime_permanent(modele, te=0.0, hg_ei=25.5, phi_conv=600.0)
    assert -(r["flux_ventilation"] + r["flux_baies"] + r["flux_parois"]) == pytest.approx(600.0, rel=1e-6)
    assert r["theta_i"] > r["theta_s"] > r["theta_mq"] > 0.0
    # Ordre de grandeur : 600 W pour environ 25,5 + 11,7 + 19 = 56 W/K, soit près de 11 °C
    assert r["theta_i"] == pytest.approx(600.0 / (25.5 + 11.7 + 19.0), rel=0.03)


def test_apport_radiatif_perdu_par_les_baies():
    # Un apport radiatif va aux baies pour Abaies / Atparois ; la part Uw / his en repart aussitôt (éq. 361)
    modele = preparer_modele(groupe_test(), "th_bc")
    r = pas_groupe(modele, etat_initial(), te=18.0, phi_rad=1000.0)
    perte = 1000.0 * (9.0 / 225.0) * (1.3 / 9.1)
    assert r["flux_apports"] == pytest.approx(1000.0 - perte)
    # Le soleil de courte longueur d'onde, lui, est entièrement réparti : 10 % à l'air, le reste aux parois
    r = pas_groupe(modele, etat_initial(), te=18.0, fs1=1000.0)
    assert r["flux_apports"] == pytest.approx(1000.0)


def test_temperatures_radiante_et_operative():
    modele = preparer_modele(groupe_test(), "th_bc")
    r = pas_groupe(modele, etat_initial(), te=0.0, hg_ei=25.5, phi_conv=800.0)
    theta_rm = modele.p_trm * r["theta_s"] + (1 - modele.p_trm) * r["theta_i"]         # éq. 369
    assert r["theta_rm"] == pytest.approx(theta_rm)
    assert r["theta_op"] == pytest.approx((r["theta_rm"] + r["theta_i"]) / 2)          # éq. 371
    # θs = (hci.θi + hrs.θrm) / (hci + hrs) : le nœud θs est bien la moyenne pondérée de l'air et du radiant
    assert r["theta_s"] == pytest.approx((2.5 * r["theta_i"] + 6.6 * r["theta_rm"]) / 9.1)


# ------------------------------------------------------------------
# Régime variable
# ------------------------------------------------------------------
def test_constante_de_temps():
    # Sans baie ni ventilation, la masse seule se refroidit vers l'extérieur : θ(t) = te + Δθ.exp(−t.Hg_em/Cmq)
    modele = preparer_modele(groupe_test(baies=[], debit_ventilation_m3h=0.0), "th_bc")
    etat = etat_initial()                                   # 18 °C
    heures = 100
    for _ in range(heures):
        avancer_etat(modele, etat, pas_groupe(modele, etat, te=0.0))
    assert etat.theta_mq == pytest.approx(18.0 * math.exp(-heures * modele.hg_em / modele.c_mq), rel=0.01)


def test_inertie_lourde_amortit():
    # Créneau d'apports : la température monte moins vite dans un groupe lourd
    def temperature_apres(classe):
        modele = preparer_modele(groupe_test(inertie_quotidienne=classe), "th_bc")
        etat = etat_initial()
        for _ in range(6):
            avancer_etat(modele, etat, pas_groupe(modele, etat, te=18.0, phi_conv=2000.0))
        return etat.theta_op
    assert temperature_apres("tres_legere") > temperature_apres("moyenne") > temperature_apres("tres_lourde") > 18.0


def test_moyenne_et_fin_de_pas():
    modele = preparer_modele(groupe_test(), "th_bc")
    etat = etat_initial()
    r = pas_groupe(modele, etat, te=18.0, phi_conv=2000.0)
    assert r["theta_mq_moy"] == pytest.approx((18.0 + r["theta_mq"]) / 2)
    assert r["theta_i_moy"] < r["theta_i"]                  # le groupe chauffe : la moyenne est sous la fin de pas
    assert etat.theta_mq == 18.0                            # pas_groupe ne modifie pas l'état


# ------------------------------------------------------------------
# Matrice du groupe (éq. 373)
# ------------------------------------------------------------------
def test_matrice_du_groupe():
    modele = preparer_modele(groupe_test(), "th_bc")
    etat = etat_initial()
    froid = matrice_groupe(modele, etat, te=-5.0, hg_ei=25.5)
    chaud = matrice_groupe(modele, etat, te=30.0, hg_ei=25.5, fs1=800.0, phi_conv=300.0, phi_rad=200.0)
    assert froid.shape == (5, 6)
    # Colonnes (moyenne, fin) du cas sans puissance : celles de pas_groupe
    libre = pas_groupe(modele, etat, te=-5.0, hg_ei=25.5)
    assert froid[:, 0] == pytest.approx([libre[f"{nom}_moy"] for nom in TEMPERATURES])
    assert froid[:, 1] == pytest.approx([libre[nom] for nom in TEMPERATURES])
    # Modèle linéaire : l'effet de 10 W/m² ne dépend ni de la météo ni des apports
    for colonne in (2, 3, 4, 5):
        assert froid[:, colonne] - froid[:, colonne % 2] == pytest.approx(chaud[:, colonne] - chaud[:, colonne % 2])
    effet_conv, effet_rad = froid[:, 3] - froid[:, 1], froid[:, 5] - froid[:, 1]
    assert (effet_conv > 0).all() and (effet_rad > 0).all()
    i, rm = TEMPERATURES.index("theta_i"), TEMPERATURES.index("theta_rm")
    assert effet_conv[i] > effet_rad[i]                     # l'émission convective chauffe d'abord l'air
    assert effet_rad[rm] > effet_conv[rm]                   # l'émission radiative chauffe d'abord les parois


# ------------------------------------------------------------------
# Année entière : bilan d'énergie (à 0,1 %)
# ------------------------------------------------------------------
@pytest.mark.parametrize("zone, jeu", [("H1a", "th_bc"), ("H3", "th_bc"), ("H2d", "th_d")])
def test_bilan_energie_annuel(zone, jeu):
    groupe = groupe_test(inertie_quotidienne="tres_lourde", inertie_sequentielle="lourde",
                         inertie_annuelle="personnalisee", ama_surf=1.0, cma_surf=6000.0)
    meteo = charger_meteo(zone, jeu, 100.0)
    apports = pd.DataFrame({"phi_conv": np.full(len(meteo), 150.0), "phi_rad": np.full(len(meteo), 130.0)})
    r = simuler_groupe(groupe, meteo, jeu, apports=apports, confort_adaptatif=np.zeros(len(meteo)))
    assert len(r) == len(meteo) and not r.isna().any().any()
    # Chaque heure : chaleur prise par la masse = somme des flux
    assert (r["stockage"] - r[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6
    # Sur l'année : la somme des flux égale la variation de chaleur de la masse, à 0,1 % des apports près
    modele = preparer_modele(groupe, jeu)
    variation = modele.c_mq * (r["theta_mq"].iloc[-1] - 18.0)
    assert r[FLUX_DU_BILAN].sum().sum() == pytest.approx(variation, abs=0.001 * r["flux_apports"].sum())
    # Les inerties séquentielle et annuelle ne jouent qu'en Th-D
    assert (r["flux_inerties_longues"].abs().max() > 0) == (jeu == "th_d")
    # Températures plausibles en évolution libre
    assert -10.0 < r["theta_op"].min() and r["theta_op"].max() < 60.0


def test_inerties_longues_amortissent_l_ete():
    meteo = charger_meteo("H2d", "th_d", 100.0)
    options = {"confort_adaptatif": np.zeros(len(meteo))}
    sans = simuler_groupe(groupe_test(inertie_quotidienne="tres_lourde"), meteo, "th_d", **options)
    avec = simuler_groupe(groupe_test(inertie_quotidienne="tres_lourde", inertie_sequentielle="lourde"), meteo,
                          "th_d", **options)
    assert avec["theta_op"].max() < sans["theta_op"].max()
    # Initialisation : pendant les 24 premières heures, la masse séquentielle suit une moyenne fixée à 18 °C
    assert avec["theta_ms"].iloc[0] == pytest.approx(18.0)


def test_sollicitations_du_groupe():
    groupe = groupe_test()
    meteo = charger_meteo("H1a", "th_bc", 100.0)
    sol = sollicitations_groupe(groupe, meteo, "th_bc")
    # Sw2 nul par défaut : tout le flux des baies est de courte longueur d'onde ; baies verticales : pas de
    # rayonnement froid
    assert sol["fs2"].abs().max() == 0 and sol["ftvc"].abs().max() < 1e-9
    assert sol["fs1"].sum() > 0 and sol["phi_sh_s"].sum() > 0
    assert (sol["phi_sl"] == sol["fs2"] + sol["ftvc"]).all()
    # Avec une toiture, le rayonnement froid refroidit le groupe
    groupe.parois.append(Paroi("Toit", "toiture", 50.0, u=0.15, alpha=0.6))
    assert sollicitations_groupe(groupe, meteo, "th_bc")["phi_sh_vc"].sum() < 0


# ------------------------------------------------------------------
# Ventilation (fiche 6.1)
# ------------------------------------------------------------------
def test_echangeur_de_ventilation():
    # À l'équilibre, un échangeur d'efficacité ε réduit la déperdition par l'air à (1 − ε).Hv (éq. 382)
    groupe = groupe_test(baies=[])
    modele = preparer_modele(groupe, "th_bc")
    hv = 0.34 * 75.0
    paroi = 1 / (1 / modele.hg_is + 1 / modele.h_th)
    apports = pd.DataFrame({"phi_conv": np.full(2000, 500.0)})
    for efficacite, attendu in ((None, 5.0 + 500.0 / (0.5 * hv + paroi)), (0.0, 5.0 + 500.0 / (hv + paroi))):
        r = simuler_groupe(groupe, meteo_constante(5.0), "th_bc", apports=apports,
                           efficacite_echangeur=efficacite)
        assert r["theta_i"].iloc[-1] == pytest.approx(attendu, rel=1e-4)
    with pytest.raises(ValueError, match="Efficacité"):
        simuler_groupe(groupe, meteo_constante(5.0, 10), "th_bc", efficacite_echangeur=1.5)


def test_apports_mal_formes():
    with pytest.raises(ValueError, match="apports"):
        simuler_groupe(groupe_test(), meteo_constante(5.0, 10), "th_bc", apports=pd.DataFrame({"inconnu": [0.0] * 10}))
    with pytest.raises(ValueError, match="apports"):
        simuler_groupe(groupe_test(), meteo_constante(5.0, 10), "th_bc", apports=pd.DataFrame({"phi_conv": [0.0]}))


# ------------------------------------------------------------------
# Brasseurs d'air (fiche 8.32) branchés sur le groupe
# ------------------------------------------------------------------
def test_brasseurs_dans_le_groupe():
    brasseur = Brasseur("Séjour", nombre=1, surface_desservie_m2=15.0, debit_max_m3h=5000.0, puissance_max_w=40.0,
                        usage="jour_et_nuit")
    avec, sans = groupe_test(brasseurs=[brasseur]), groupe_test()
    meteo = charger_meteo("H2d", "th_d", 100.0)
    n = len(meteo)
    entrees = pd.DataFrame({"case": construire_calendrier()["case"], "actif": True, "occupe": True,
                            "theta_ifr": 26.0, "ecart_conf_adapt": 0.0})
    options = {"confort_adaptatif": np.zeros(n)}
    r_avec = simuler_groupe(avec, meteo, "th_d", entrees_brasseurs=entrees, **options)
    r_sans = simuler_groupe(sans, meteo, "th_d", **options)
    # Les brasseurs tournent quand il fait chaud, relèvent le seuil d'inconfort et chauffent un peu le groupe
    assert r_avec["energie_brasseurs_wh"].sum() > 0 and r_avec["ecart_ba"].max() > 0
    assert (r_avec["chaleur_brasseurs_w"] == r_avec["energie_brasseurs_wh"]).all()
    assert r_avec["theta_i"].mean() > r_sans["theta_i"].mean()
    assert r_avec["chaleur_brasseurs_w"].iloc[0] == 0                  # arrêt à la première heure
    assert r_sans["energie_brasseurs_wh"].sum() == 0
    # Bilan d'énergie toujours respecté, chaleur des brasseurs comprise
    assert (r_avec["stockage"] - r_avec[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6
    with pytest.raises(ValueError, match="entrees_brasseurs"):
        simuler_groupe(avec, meteo, "th_d", **options)


def test_debit_de_ventilation_moyen():
    """Fiche 6.2 : grand débit 14 heures par semaine pour le Bbio."""
    from moteur.groupe import debit_ventilation
    assert debit_ventilation(Groupe("G", 50.0, debit_ventilation_m3h=75.0)) == 75.0
    avec_pointe = Groupe("G", 650.0, debit_ventilation_m3h=600.0, debit_ventilation_pointe_m3h=1350.0)
    assert debit_ventilation(avec_pointe) == pytest.approx(600.0 + 750.0 * 14 / 168)
