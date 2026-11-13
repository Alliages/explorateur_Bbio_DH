"""
============================================================
 BRASSEURS D'AIR — gestion, effet sur le ressenti, consommation
============================================================
 Source : annexe III de l'arrêté du 4 août 2021,
   fiche 8.32 (C_BAT_Fonctionnement/gestion/régulation des
   brasseurs d'air), éq. 1646 à 1666, tableaux 257 et 258 ;
   fiche 13.5 (C_CALC_Indicateur de confort d'été), éq. 2547.

 Rôle dans le DH : les brasseurs créent une vitesse d'air qui
 relève le seuil d'inconfort chaud du groupe :
     θop_conf_ch_corr(h) = θop_conf_ch(h) + ΔθopBA(h)  (éq. 2547)
 Ce module calcule ΔθopBA(h) ; l'addition se fera dans le
 module DH. Sans brasseur, ΔθopBA = 0.

 Chaîne de calcul, pour chaque type p de brasseurs :
   1. paramètres corrigés : débit maximal × 1 / 0,9 / 0,8 et
      puissance maximale × 1 / 1,1 / 1,2 (certifié / justifié /
      déclaré) ; vitesse intermédiaire = 0,6 × maximum ;
   2. ratio de surface brassée : Ratbr = min(15 Nbr / Agr ;
      surface desservie / Agr) ; test de cohérence avec RatUs
      (tableau 257) ;
   3. régime (arrêt, intermédiaire, maximal) par une hystérésis
      sur θop(h−1) : seuils arr < V1 < V2 (éq. 1646 à 1654) ;
      arrêt hors occupation, hors de la plage jour / nuit et
      hors période de confort adaptatif ; la nuit, en
      habitation, bridé à l'intermédiaire et, en gestion
      manuelle, bloqué sur sa position de 23h ;
   4. effet : Qtot = Q × Nbr ; τ = Qtot / (Vol × Ratbr) ;
      v = 0,0032 × τ ; si v > 0,2 m/s :
      Δθ = 1,8322 e^(0,0361 (θrm−θi)) ln v
           + 3,0498 e^(0,0368 (θrm−θi))    (θrm, θi à h−1)
                                           (éq. 1656 à 1659)
   5. effet du groupe : moyenne des Δθ pondérée par Ratbr / RatUs,
      calculée pour le jour et pour la nuit (éq. 1660-1661) ;
   6. consommation et chaleur dégagée dans le groupe
      (éq. 1662 à 1666).

 Convention d'heure : « hlég » est lu comme la case des
 scénarios (heure légale de FIN de pas, 1 à 24) ; « jour » =
 6 < case ≤ 22, soit le pas de 6h-7h au pas de 21h-22h.

 Couplage avec le modèle du groupe : le régime à l'heure h ne
 dépend que des températures de l'heure h−1, et la chaleur des
 brasseurs entre dans le bilan de l'heure h. Le modèle du groupe
 appellera donc pas_brasseurs() heure par heure. La fonction
 simuler_brasseurs() déroule l'année sur des températures déjà
 connues (tests, évolution libre sans retour de la chaleur).

 Hypothèses de l'outil : voir docs/audit.md (brasseurs d'air).
 Domaine de validité de la méthode : brasseurs de plafond,
 hauteur sous plafond inférieure à 3 m, groupe non climatisé.
============================================================
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.reglages import USAGES_HABITATION
from moteur.hypotheses import hyp

# Régimes d'un type de brasseurs : le débit ne prend que ces trois valeurs (fiche 8.32, § 8.32.1)
ARRET, INTERMEDIAIRE, MAXIMAL = 0, 1, 2

# Colonnes attendues par simuler_brasseurs(), une ligne par heure
COLONNES_ENTREES = (
    "case",                # heure légale de fin de pas (1-24), voir moteur/calendrier.py
    "actif",               # Is_confort_adaptatif(h) en Th-D (période d'utilisation possible), booléen
    "occupe",              # iocc_zone(h), booléen
    "theta_op",            # θop,fin(h) : température opérative du groupe en fin de pas (°C)
    "theta_i",             # θi(h) : température de l'air du groupe (°C)
    "theta_rm",            # θrm(h) : température radiante moyenne du groupe (°C)
    "theta_ifr",           # θiifr+(h) : consigne de refroidissement en occupation (°C)
    "ecart_conf_adapt",    # Δθconf_adapt(h) (fiche 13.5, éq. 2546) (°C)
)


@dataclass
class TypeBrasseur:
    """Un type p de brasseurs, avec ses paramètres corrigés et ses ratios de surface."""
    brasseur: object            # moteur.structures.Brasseur
    debits_m3h: tuple           # débit individuel par régime : (0, Qint, Qmax_corr)
    puissances_w: tuple         # puissance individuelle par régime : (0, Pint, Pmax_corr)
    ratio_brasse: float         # Ratbr_p, après plafonnement à 15 m² par brasseur
    ratio_usage: float          # RatUs_BA_p (tableau 257)


# ============================================================
# 1. PARAMÈTRES CORRIGÉS (fiche 8.32, § Paramètres d'intégration et intrinsèques)
# ============================================================
def parametres_corriges(brasseur):
    """Débits (m³/h) et puissances (W) individuels corrigés : (Qmax_corr, Qint, Pmax_corr, Pint)."""
    coef_debit = {"certifiee": 1.0,
                  "justifiee": hyp("brasseur_coef_debit_justifie"),
                  "declaree": hyp("brasseur_coef_debit_declare")}[brasseur.caractere_debit]
    coef_puissance = {"certifiee": 1.0,
                      "justifiee": hyp("brasseur_coef_puissance_justifiee"),
                      "declaree": hyp("brasseur_coef_puissance_declaree")}[brasseur.caractere_puissance]
    q_max = coef_debit * brasseur.debit_max_m3h
    p_max = coef_puissance * brasseur.puissance_max_w
    ratio = hyp("brasseur_ratio_intermediaire")
    return q_max, ratio * q_max, p_max, ratio * p_max


# ============================================================
# 2. RATIOS DE SURFACE (fiche 8.32, tableau 257 et § Ratio de surface brassée)
# ============================================================
def ratio_brasse(brasseur, surface_groupe_m2):
    """Ratbr_p = min(15 × Nbr_p / Agr ; surface desservie / Agr)."""
    plafond = hyp("brasseur_surface_max") * brasseur.nombre / surface_groupe_m2
    return min(plafond, brasseur.surface_desservie_m2 / surface_groupe_m2)


def ratio_usage(usage_brasseur, usage_zone):
    """RatUs_BA_p : part de la surface du groupe occupée pour l'usage jour ou nuit du brasseur."""
    if usage_brasseur == "jour_et_nuit":
        return hyp("brasseur_ratus_jour_et_nuit")
    return hyp(f"brasseur_ratus_{usage_zone}_{usage_brasseur}")


def preparer_brasseurs(groupe, usage_zone="logement_collectif"):
    """Liste des TypeBrasseur du groupe, après le test de cohérence des surfaces.

    Erreurs (fiche 8.32, § Ratio de surface brassée et remarque sous le tableau 257) :
      - un brasseur « jour et nuit » ne peut pas côtoyer un brasseur d'un autre usage ;
      - pour chaque usage, la somme des Ratbr ne peut dépasser RatUs (lecture « ≤ », voir docs/audit.md).
    """
    if not groupe.brasseurs:
        return []
    usages = {b.usage for b in groupe.brasseurs}
    if "jour_et_nuit" in usages and len(usages) > 1:
        raise ValueError(f"Groupe « {groupe.nom} » : un brasseur « jour et nuit » exclut tout brasseur d'un "
                         "autre usage (fiche 8.32, remarque sous le tableau 257)")
    types = []
    for b in groupe.brasseurs:
        q_max, q_int, p_max, p_int = parametres_corriges(b)
        types.append(TypeBrasseur(b, (0.0, q_int, q_max), (0.0, p_int, p_max),
                                  ratio_brasse(b, groupe.surface_m2), ratio_usage(b.usage, usage_zone)))
    for usage in usages:
        somme = sum(t.ratio_brasse for t in types if t.brasseur.usage == usage)
        limite = ratio_usage(usage, usage_zone)
        if somme > limite + 1e-12:
            raise ValueError(f"Groupe « {groupe.nom} » : brasseurs d'usage « {usage} », surface brassée "
                             f"{somme:.0%} du groupe, au-delà de la surface occupée pour cet usage ({limite:.0%})")
    return types


# ============================================================
# 3. GESTION — RÉGULATION (fiche 8.32, éq. 1646 à 1654)
# ============================================================
def est_jour(case):
    """Vrai si 6 < hlég ≤ 22, hlég étant l'heure légale de fin de pas (case des scénarios)."""
    return hyp("heure_debut_jour") < case <= hyp("heure_fin_jour")


def consignes(brasseur, theta_ifr, ecart_conf_adapt):
    """Seuils de l'hystérésis (arr, V1, V2) en °C, à l'heure h (éq. 1646 à 1650).

    Manuelle et thermostat : le déclenchement suit le seuil d'inconfort,
        θop_dec = θiifr+ + Δθconf_adapt + Δθop_3 ; V1 = θop_dec ; V2 = V1 + Δθop_2 ; arr = V1 − Δθop_1.
    Automatique : θop_dec est fixe, saisi ; V1 = θop_dec + Δθop_3 ; mêmes écarts ensuite.
    """
    if brasseur.gestion == "manuelle":
        ecart_arret, ecart_max = hyp("brasseur_man_arret"), hyp("brasseur_man_max")
        v1 = theta_ifr + ecart_conf_adapt + hyp("brasseur_man_declenchement")
    elif brasseur.gestion == "thermostat":
        ecart_arret, ecart_max = brasseur.ecart_arret, brasseur.ecart_max
        v1 = theta_ifr + ecart_conf_adapt + brasseur.ecart_declenchement
    else:
        ecart_arret, ecart_max = brasseur.ecart_arret, brasseur.ecart_max
        decalage = (brasseur.ecart_declenchement if brasseur.ecart_declenchement is not None
                    else hyp("brasseur_auto_declenchement"))
        v1 = brasseur.temperature_declenchement + decalage
    return v1 - ecart_arret, v1, v1 + ecart_max


def regime_suivant(brasseur, regime_prec, theta_op_prec, case, actif, occupe, theta_ifr, ecart_conf_adapt,
                   habitation):
    """Régime (ARRET, INTERMEDIAIRE, MAXIMAL) d'un type de brasseurs à l'heure h.

    regime_prec et theta_op_prec sont ceux de l'heure h−1.
    """
    # Hors période d'utilisation, hors occupation ou hors de la plage jour / nuit : arrêt (éq. 1651 à 1653)
    jour = est_jour(case)
    if not (actif and occupe):
        return ARRET
    if (brasseur.usage == "jour" and not jour) or (brasseur.usage == "nuit" and jour):
        return ARRET

    # Hystérésis à deux paliers sur la température opérative de fin de l'heure précédente (éq. 1654)
    arr, v1, v2 = consignes(brasseur, theta_ifr, ecart_conf_adapt)
    if theta_op_prec < arr:
        regime = ARRET
    elif theta_op_prec < v1:
        regime = regime_prec
    elif theta_op_prec < v2:
        regime = max(INTERMEDIAIRE, regime_prec)
    else:
        regime = MAXIMAL

    # Nuit en habitation : pas de vitesse maximale (acoustique) ; en gestion manuelle, position de 23h gardée
    if habitation and brasseur.usage in ("nuit", "jour_et_nuit") and not jour:
        regime = min(regime, INTERMEDIAIRE)
        if brasseur.gestion == "manuelle" and (case > hyp("brasseur_heure_blocage")
                                               or case <= hyp("heure_debut_jour")):
            regime = regime_prec
    return regime


# ============================================================
# 4. EFFET SUR LA TEMPÉRATURE OPÉRATIVE RESSENTIE (fiche 8.32, éq. 1656 à 1659)
# ============================================================
def ecart_operatif(vitesse, theta_rm, theta_i):
    """Δθop (°C) dû à une vitesse d'air moyenne (m/s) ; nul si la vitesse ne dépasse pas 0,2 m/s (éq. 1659)."""
    if vitesse <= hyp("brasseur_vitesse_seuil"):
        return 0.0
    ecart_radiant = theta_rm - theta_i
    return (hyp("brasseur_a") * math.exp(hyp("brasseur_ka") * ecart_radiant) * math.log(vitesse)
            + hyp("brasseur_b") * math.exp(hyp("brasseur_kb") * ecart_radiant))


def vitesse_air(type_brasseur, regime, volume_m3):
    """Vitesse moyenne de l'air dans la zone brassée (m/s) : v = 0,0032 × Q × Nbr / (Vol × Ratbr)."""
    debit_total = type_brasseur.debits_m3h[regime] * type_brasseur.brasseur.nombre          # éq. 1656
    taux_brassage = debit_total / (volume_m3 * type_brasseur.ratio_brasse)                  # éq. 1657 (vol/h)
    return hyp("brasseur_coef_vitesse") * taux_brassage                                     # éq. 1658


# ============================================================
# 5-6. PAS DE TEMPS : effet du groupe et consommation (éq. 1660 à 1666)
# ============================================================
def pas_brasseurs(types, regimes_prec, volume_m3, *, case, actif, occupe, theta_op_prec, theta_i_prec,
                  theta_rm_prec, theta_ifr, ecart_conf_adapt, habitation=True):
    """Calcul d'une heure h pour tous les types de brasseurs d'un groupe.

    Entrées : types (preparer_brasseurs), régimes et températures de l'heure h−1, données de l'heure h.
    Sortie : dictionnaire
        regimes          régime de chaque type à l'heure h (à repasser à l'heure suivante)
        ecarts_types     ΔθopBA_p de chaque type (°C)
        ecart_jour       ΔθopBA_jour (°C)
        ecart_nuit       ΔθopBA_nuit (°C)
        ecart            ΔθopBA retenu selon l'heure (°C), à ajouter au seuil d'inconfort (éq. 2547)
        energie_wh       Wabs-BAgr : consommation des brasseurs du groupe sur l'heure (Wh)
        chaleur_wh       Φth-BA-vcgr : chaleur dégagée dans le groupe (Wh), égale à la consommation
    """
    regimes, ecarts = [], []
    ecart_jour = ecart_nuit = energie = 0.0
    for t, regime_prec in zip(types, regimes_prec):
        regime = regime_suivant(t.brasseur, regime_prec, theta_op_prec, case, actif, occupe, theta_ifr,
                                ecart_conf_adapt, habitation)
        ecart = ecart_operatif(vitesse_air(t, regime, volume_m3), theta_rm_prec, theta_i_prec)
        # Moyenne pondérée par les surfaces : Ratbr_p / RatUs (éq. 1660)
        part = t.ratio_brasse * ecart / t.ratio_usage
        if t.brasseur.usage in ("jour", "jour_et_nuit"):
            ecart_jour += part
        if t.brasseur.usage in ("nuit", "jour_et_nuit"):
            ecart_nuit += part
        # Consommation de l'ensemble des brasseurs du type (éq. 1662-1663, × Nbr : voir docs/audit.md)
        energie += t.puissances_w[regime] * t.brasseur.nombre
        regimes.append(regime)
        ecarts.append(ecart)
    return {"regimes": regimes, "ecarts_types": ecarts, "ecart_jour": ecart_jour, "ecart_nuit": ecart_nuit,
            "ecart": ecart_jour if est_jour(case) else ecart_nuit,                         # éq. 1661
            "energie_wh": energie, "chaleur_wh": energie}                                   # éq. 1664-1666


def simuler_brasseurs(groupe, entrees, usage_zone="logement_collectif"):
    """Déroule les brasseurs du groupe sur toutes les heures de « entrees » (colonnes COLONNES_ENTREES).

    Les températures de l'heure h−1 pilotent l'heure h ; à la première heure, les brasseurs sont à l'arrêt
    (hypothèse de l'outil). Sans brasseur, toutes les sorties sont nulles.
    Sortie : DataFrame avec ecart_ba, ecart_ba_jour, ecart_ba_nuit, energie_wh, chaleur_wh, puis
    regime_<nom> et ecart_<nom> pour chaque type de brasseurs.
    """
    manquantes = [c for c in COLONNES_ENTREES if c not in entrees.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes pour les brasseurs : {', '.join(manquantes)}")
    types = preparer_brasseurs(groupe, usage_zone)
    habitation = usage_zone in USAGES_HABITATION
    n = len(entrees)
    sorties = {nom: np.zeros(n) for nom in ("ecart_ba", "ecart_ba_jour", "ecart_ba_nuit", "energie_wh",
                                            "chaleur_wh")}
    regimes_types = np.zeros((n, len(types)), dtype=int)
    ecarts_types = np.zeros((n, len(types)))

    # Colonnes en tableaux numpy : boucle horaire plus rapide qu'avec pandas
    e = {c: entrees[c].to_numpy() for c in COLONNES_ENTREES}
    regimes = [ARRET] * len(types)
    for h in range(1, n):
        res = pas_brasseurs(types, regimes, groupe.volume_m3, case=int(e["case"][h]), actif=bool(e["actif"][h]),
                            occupe=bool(e["occupe"][h]), theta_op_prec=e["theta_op"][h - 1],
                            theta_i_prec=e["theta_i"][h - 1], theta_rm_prec=e["theta_rm"][h - 1],
                            theta_ifr=e["theta_ifr"][h], ecart_conf_adapt=e["ecart_conf_adapt"][h],
                            habitation=habitation)
        regimes = res["regimes"]
        sorties["ecart_ba"][h] = res["ecart"]
        sorties["ecart_ba_jour"][h] = res["ecart_jour"]
        sorties["ecart_ba_nuit"][h] = res["ecart_nuit"]
        sorties["energie_wh"][h] = res["energie_wh"]
        sorties["chaleur_wh"][h] = res["chaleur_wh"]
        regimes_types[h] = regimes
        ecarts_types[h] = res["ecarts_types"]

    resultat = pd.DataFrame(sorties, index=entrees.index)
    for i, t in enumerate(types):
        resultat[f"regime_{t.brasseur.nom}"] = regimes_types[:, i]
        resultat[f"ecart_{t.brasseur.nom}"] = ecarts_types[:, i]
    return resultat
