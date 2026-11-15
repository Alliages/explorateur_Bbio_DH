r"""
============================================================
 CONFORT ADAPTATIF — période et seuil d'inconfort chaud
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 3.1 (C_EEX_Climat extérieur), éq. 1 et 2 : moyenne
     glissante de la température extérieure et période de
     confort adaptatif ;
   fiche 13.5 (C_CALC_Indicateur de confort d'été), éq. 2543
     à 2546 : température limite de confort chaud.

 Le confort adaptatif part d'un constat : on supporte mieux la
 chaleur quand il fait chaud dehors depuis plusieurs jours.

 1. Moyenne glissante de la température extérieure, θrm(j)
    (theta_rm_ext dans le code : « theta_rm » y désigne déjà la
    température radiante moyenne du groupe), calculée une fois par jour (jours de 24 pas à partir de
    l'heure 0, donc en UTC) et valable toute la journée :

        θrm(1) = 0
        θrm(j) = 0,8 × θrm(j−1) + 0,2 × moyenne de la veille

 2. Période de confort adaptatif : du PREMIER au DERNIER jour
    de l'année où θrm(j) ≥ 16 °C, sans interruption.

 3. Température limite de confort chaud, en habitation :

        θ (°C)
        28 |            ___________   plafond : consigne + 2 °C
           |          /
        26 |________/                 plancher : consigne (26 °C)
           +--------|---|----------> θrm (°C)
                  15,8  21,8

      de jour (6 < hlég ≤ 22)  MIN(consigne + 2 ;
                                MAX(consigne ; 0,33 × θrm + 18,8 + 2))
      de nuit (sommeil)         la consigne de refroidissement

    hlég est l'heure légale de DÉBUT de pas : le jour va du
    pas de 7h-8h au pas de 22h-23h.

 Ces règles, vérifiées sur les sorties horaires d'un moteur
 Th-BCE, sont aussi celles du module dh_re2020.py de Météo et
 Chaleur (voir docs/audit.md, 0.8.16).
============================================================
"""

import numpy as np

from config.reglages import HEURES_PAR_JOUR
from moteur.hypotheses import hyp


def moyenne_glissante_exterieure(te):
    """θrm heure par heure (°C) : moyenne glissante de la température extérieure « te » (fiche 3.1, éq. 1).

    Une valeur par jour de 24 pas, répétée sur ses heures ; nulle le premier jour, comme l'écrit la fiche.
    """
    te = np.asarray(te, dtype=float)
    nb_jours = -(-len(te) // HEURES_PAR_JOUR)                # un dernier jour incomplet compte pour un jour
    poids_veille = hyp("confort_poids_veille")
    par_jour = np.zeros(nb_jours)
    for j in range(1, nb_jours):
        veille = te[(j - 1) * HEURES_PAR_JOUR:j * HEURES_PAR_JOUR].mean()
        par_jour[j] = poids_veille * par_jour[j - 1] + (1.0 - poids_veille) * veille
    return np.repeat(par_jour, HEURES_PAR_JOUR)[:len(te)]


def periode_confort_adaptatif(theta_rm_ext):
    """Isconf_adapt heure par heure (booléens) : du premier au dernier jour où θrm ≥ 16 °C (fiche 3.1, éq. 2).

    theta_rm_ext : moyenne glissante de la température extérieure, heure par heure (°C).
    Aucune heure n'est retenue si elle n'atteint jamais le seuil.
    """
    theta_rm_ext = np.asarray(theta_rm_ext, dtype=float)
    chaudes = np.flatnonzero(theta_rm_ext >= hyp("confort_theta_rm_seuil_periode"))
    periode = np.zeros(len(theta_rm_ext), dtype=bool)
    if chaudes.size:
        periode[chaudes[0]:chaudes[-1] + 1] = True
    return periode


def est_jour(hleg):
    """Vrai si 6 < hlég ≤ 22 (hlég : heure légale de début de pas) ; accepte un nombre ou un tableau."""
    hleg = np.asarray(hleg)
    return (hleg > hyp("heure_debut_jour")) & (hleg <= hyp("heure_fin_jour"))


def seuil_confort_chaud(theta_rm_ext, hleg, consigne_fr, habitation=True):
    """θop_conf_ch heure par heure (°C) : température limite de confort chaud (fiche 13.5, éq. 2543 à 2545).

    theta_rm_ext moyenne glissante de la température extérieure (°C)
    hleg         heure légale de début de pas (0 à 23)
    consigne_fr  θiifr+ : consigne de refroidissement en occupation (°C)
    habitation   la nuit, le seuil d'une habitation est la consigne (sommeil) ; ailleurs il suit θrm à toute heure
    """
    theta_rm_ext = np.asarray(theta_rm_ext, dtype=float)
    maximum = np.maximum(consigne_fr, hyp("confort_pente") * theta_rm_ext + hyp("confort_origine")
                         + hyp("confort_ecart_c1"))                                         # éq. 2543
    seuil = np.minimum(consigne_fr + hyp("confort_ecart_min_max"), maximum)                 # éq. 2544-2545
    if habitation:
        seuil = np.where(est_jour(hleg), seuil, consigne_fr)
    return seuil


def ecart_confort_adaptatif(seuil, consigne_fr):
    """Δθconf_adapt (°C) : écart entre le seuil de confort chaud et la consigne de refroidissement (éq. 2546)."""
    return np.maximum(0.0, np.asarray(seuil, dtype=float) - consigne_fr)
