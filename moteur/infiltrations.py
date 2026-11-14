r"""
============================================================
 INFILTRATIONS — air entrant par les défauts d'étanchéité
============================================================
 Source : annexe III de l'arrêté du 4 août 2021, fiche 5.6
   (C_VEN_Débits_d'air_Cep), éq. 131 à 172, tableaux 23, 24 et
   27 à 29 ; fiche 3.1 : correction locale du vent.

 L'enveloppe n'est jamais parfaitement étanche. Sa perméabilité
 se mesure par le débit de fuite sous 4 Pa, par m² de paroi
 (planchers bas exclus) : Q4Pa_surf, en m³/h/m².

 Le débit d'un défaut suit la différence de pression de part et
 d'autre de l'enveloppe :

     q = C × signe(ΔP) × |ΔP|^(2/3)        C = A × Q4Pa_surf / 4^(2/3)

     ΔP = Pext − Pint, avec
       Pext = ½ × Cp × ρext × V² − ρext × g × z      (vent, poids de l'air)
       Pint = Pib − ρint × g × z                     (Pib : pression au plancher)

 Les défauts sont répartis par convention, quelle que soit la
 direction du vent :

            toiture (tout C_toit)
          +-----------+
    1/4   |   haut    |   1/4        façade AU VENT : Cp > 0
          |- - - - - -|              façade SOUS LE VENT : Cp < 0
    1/4   |   bas     |   1/4
          +-----------+
    vent →

 Pib est l'inconnue : c'est la pression pour laquelle il entre
 autant d'air qu'il en sort (éq. 167), ventilation comprise.
 On la cherche chaque heure par dichotomie.

 Ventilation du Bbio : double flux à débits volumiques égaux ;
 l'air soufflé, plus froid que l'air repris en hiver, est plus
 dense : le groupe est mis en légère surpression (éq. 156-157).

 L'air qui entre par les défauts est à la température
 extérieure et ne passe pas par l'échangeur : c'est lui qui
 pèse sur le besoin de chauffage.

 Hypothèses de l'outil (docs/audit.md, 0.8.14) : un bilan par
 groupe (et non par zone) ; pas d'entrées d'air en mode Bbio ;
 humidité de l'air ignorée dans les masses volumiques.
============================================================
"""

import numpy as np

from moteur.hypotheses import hyp

KELVIN = 273.0
SECONDES_PAR_HEURE = 3600.0
PESANTEUR = 9.81                    # m/s²
EXPOSANT = 2.0 / 3.0                # loi de débit des défauts d'étanchéité (éq. 151)
INCLINAISON_FACADE_MIN_DEG = 60.0   # façade : à moins de 30° de la verticale (§ 5.6.3.1.4)
INCLINAISON_FACADE_MAX_DEG = 120.0  # au-delà : plancher bas, hors de la surface perméable
ITERATIONS = 60                     # dichotomie sur Pib : précision bien meilleure que 1e-6 Pa
MARGE_PRESSION = 1.0                # Pa ajoutés de part et d'autre de l'encadrement de Pib


# ============================================================
# 1. GRANDEURS DU GROUPE
# ============================================================
def masse_volumique(theta):
    """Masse volumique de l'air sec à la température theta (kg/m³) : éq. 131-132, sans l'humidité."""
    return hyp("air_masse_volumique_reference") * (KELVIN + hyp("ouv_temperature_reference")) / (KELVIN + theta)


def surfaces_permeables(groupe):
    """(surface de façade, surface de toiture) du groupe, baies comprises, planchers bas exclus (m²)."""
    facade = toit = 0.0
    for composant in list(groupe.parois) + list(groupe.baies):
        if getattr(composant, "type", None) == "plancher_bas":
            continue
        beta = composant.inclinaison_deg
        if INCLINAISON_FACADE_MIN_DEG <= beta <= INCLINAISON_FACADE_MAX_DEG:
            facade += composant.surface_m2
        elif beta < INCLINAISON_FACADE_MIN_DEG:
            toit += composant.surface_m2
    return facade, toit


def coefficients_pression(traversant, hauteur_moyenne_m):
    """(Cp au vent, Cp sous le vent, Cp de la toiture) : tableaux 23 (écrantage normal, toit plat) et 24."""
    if not traversant:
        return hyp("inf_cp_non_traversant_vent"), hyp("inf_cp_non_traversant_sous_vent"), 0.0
    haut = hauteur_moyenne_m is not None and hauteur_moyenne_m >= hyp("inf_hauteur_seuil_cp")
    au_vent = hyp("inf_cp_traversant_vent_haut") if haut else hyp("inf_cp_traversant_vent_bas")
    return au_vent, hyp("inf_cp_traversant_sous_vent"), hyp("inf_cp_traversant_toit")


def defauts_groupe(groupe, hauteur_zone_m=None, hauteur_moyenne_m=None):
    """Défauts d'étanchéité conventionnels du groupe : liste de (C en m³/h/Pa^(2/3), Cp, altitude z en m).

    Quatre défauts de façade (au vent et sous le vent, en bas et en haut, un quart chacun) et, s'il y a une
    toiture, un cinquième qui porte toute sa perméabilité (tableaux 28 et 29). En habitation, pas de tirage entre
    niveaux : les altitudes sont comptées sur 3 m au plus (éq. 138).
    """
    facade, toit = surfaces_permeables(groupe)
    par_pascal = groupe.permeabilite_q4pa / hyp("inf_pression_reference") ** EXPOSANT             # éq. 150
    hauteur = min(hauteur_zone_m if hauteur_zone_m is not None else hyp("inf_hauteur_tirage_max"),
                  hyp("inf_hauteur_tirage_max"))
    bas, haut = hyp("inf_part_altitude_basse") * hauteur, hyp("inf_part_altitude_haute") * hauteur
    cp_vent, cp_sous_vent, cp_toit = coefficients_pression(groupe.traversant, hauteur_moyenne_m)
    quart = 0.25 * facade * par_pascal
    defauts = [(quart, cp, z) for cp in (cp_vent, cp_sous_vent) for z in (bas, haut)]
    if toit > 0:
        defauts.append((toit * par_pascal, cp_toit, hauteur))
    return [d for d in defauts if d[0] > 0]


# ============================================================
# 2. ÉQUILIBRE AÉRAULIQUE D'UNE HEURE (fiche 5.6, éq. 135 à 137, 151, 161 et 167)
# ============================================================
def equilibre(defauts, vent, te, theta_i, debit_ventilation_m3h=0.0, theta_souffle=None):
    """Pression intérieure d'équilibre et débits par les défauts d'étanchéité.

    defauts                 liste de (C, Cp, z) de defauts_groupe()
    vent                    vitesse du vent corrigée (m/s)
    te, theta_i             températures extérieure et intérieure (°C)
    debit_ventilation_m3h   débit de la double flux, soufflé et repris à volumes égaux
    theta_souffle           température de l'air soufflé (°C) ; par défaut te
    Sortie : dictionnaire pib (Pa), debit_entrant_kg_s, debit_sortant_kg_s (négatif) et
    debit_entrant_m3h (volume équivalent à la masse volumique de référence).
    """
    rho_ext, rho_int = masse_volumique(te), masse_volumique(theta_i)
    # Pression motrice de chaque défaut, hors Pib : vent et tirage thermique (éq. 135 à 137)
    motrices = [0.5 * cp * rho_ext * vent ** 2 + (rho_int - rho_ext) * PESANTEUR * z for _, cp, z in defauts]
    coefficients = [c for c, _, _ in defauts]
    # Ventilation double flux : masses soufflée et reprise (éq. 156-157)
    rho_souffle = masse_volumique(theta_souffle if theta_souffle is not None else te)
    net_ventilation = (rho_souffle - rho_int) * debit_ventilation_m3h / SECONDES_PAR_HEURE

    def bilan(pib):
        """Somme des débits massiques entrant dans le groupe (kg/s) pour une pression Pib : décroît avec Pib."""
        total = net_ventilation
        for c, motrice in zip(coefficients, motrices):
            dp = motrice - pib
            total += (rho_ext if dp > 0 else rho_int) * c * (abs(dp) ** EXPOSANT if dp > 0 else -abs(dp) ** EXPOSANT) \
                / SECONDES_PAR_HEURE
        return total

    # Encadrement : sous la plus petite pression motrice tout entre, au-dessus de la plus grande tout sort ;
    # élargi tant que la ventilation déséquilibrée l'exige
    bas, haut = min(motrices) - MARGE_PRESSION, max(motrices) + MARGE_PRESSION
    while bilan(bas) < 0:
        bas -= 10.0 * (haut - bas)
    while bilan(haut) > 0:
        haut += 10.0 * (haut - bas)
    for _ in range(ITERATIONS):
        milieu = 0.5 * (bas + haut)
        if bilan(milieu) > 0:
            bas = milieu
        else:
            haut = milieu
    pib = 0.5 * (bas + haut)

    entrant = sortant = 0.0
    for c, motrice in zip(coefficients, motrices):
        dp = motrice - pib
        if dp > 0:
            entrant += rho_ext * c * dp ** EXPOSANT / SECONDES_PAR_HEURE
        else:
            sortant -= rho_int * c * (-dp) ** EXPOSANT / SECONDES_PAR_HEURE
    return {"pib": pib, "debit_entrant_kg_s": entrant, "debit_sortant_kg_s": sortant,
            "debit_entrant_m3h": entrant * SECONDES_PAR_HEURE / hyp("air_masse_volumique_reference")}


# ============================================================
# 3. LE GROUPE, HEURE PAR HEURE
# ============================================================
def groupe_permeable(groupe):
    """Vrai si une perméabilité à l'air est renseignée pour le groupe."""
    return groupe.permeabilite_q4pa is not None and groupe.permeabilite_q4pa > 0


class InfiltrationsGroupe:
    """Infiltrations d'un groupe en mode Bbio : équilibre aéraulique de chaque heure."""

    def __init__(self, groupe, meteo, debit_ventilation_m3h, hauteur_zone_m=None, hauteur_moyenne_m=None):
        self.defauts = defauts_groupe(groupe, hauteur_zone_m, hauteur_moyenne_m)
        self.debit_ventilation = debit_ventilation_m3h
        self.vent = hyp("vent_correction_locale") * meteo["Vent"].to_numpy(float)       # fiche 3.1 : Ventc
        self.te = meteo["te"].to_numpy(float)

    def pas(self, h, theta_i_prec, theta_souffle):
        """Débit entrant par les défauts à l'heure h et son coefficient d'échange (W/K, air à te)."""
        if not self.defauts:
            return {"debit_m3h": 0.0, "hg": 0.0, "pib": 0.0}
        r = equilibre(self.defauts, self.vent[h], self.te[h], theta_i_prec, self.debit_ventilation, theta_souffle)
        return {"debit_m3h": r["debit_entrant_m3h"], "pib": r["pib"],
                "hg": hyp("chaleur_volumique_air") * r["debit_entrant_m3h"]}
