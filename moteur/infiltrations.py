r"""
============================================================
 INFILTRATIONS — air entrant par les défauts d'étanchéité
============================================================
 Source : annexe III de l'arrêté du 4 août 2021, fiche 5.6
   (C_VEN_Débits_d'air_Cep), éq. 131 à 172, tableaux 23, 24 et
   27 à 29 ; fiche 3.2 (p. 40) : correction locale du vent.

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

 Entrées d'air du projet (éq. 141, tableau 25) : ouvertures de
 loi q = M × (|ΔP| / 20 Pa)^0,5, M étant leur module (m³/h sous
 20 Pa) : un quart au vent en haut, un en bas, de même sous le
 vent. En logement (pas de tirage entre niveaux), une seule
 altitude : 0,92 × MIN(h ; 3). Pour un même écart de pression,
 elles laissent entrer bien plus d'air que les défauts.

 Pib est l'inconnue : c'est la pression pour laquelle il entre
 autant d'air qu'il en sort (éq. 167), ventilation comprise.
 On la cherche chaque heure entre deux pressions qui l'encadrent,
 par fausse position (la corde entre les deux bornes), avec un
 pas de dichotomie quand l'encadrement se resserre mal : plusieurs
 fois moins d'évaluations du bilan qu'une dichotomie seule.

 Ventilation du Bbio : double flux à débits volumiques égaux ;
 l'air soufflé, plus froid que l'air repris en hiver, est plus
 dense : le groupe est mis en légère surpression (éq. 156-157).

 L'air qui entre par les défauts est à la température
 extérieure et ne passe pas par l'échangeur : c'est lui qui
 pèse sur le besoin de chauffage.

 Caractère traversant : celui de la zone au sens des conditions
 d'hiver (tableau 22, Groupe.traversant_hiver), à défaut celui
 du confort d'été. Hauteur moyenne inconnue : prise sous 15 m,
 avec un avertissement.

 Hypothèses de l'outil (docs/audit.md, 0.8.14 et 0.9.10) : un
 bilan par groupe (et non par zone) ; entrées d'air du projet
 gardées en mode Bbio, comme le moteur réglementaire
 (hypothèse 92, qui remplace la 67), en entrées fixes, sans
 autoréglage ni anti-retour ; humidité de l'air ignorée dans
 les masses volumiques.
============================================================
"""

import warnings

import numpy as np

from config.reglages import KELVIN, SECONDES_PAR_HEURE
from moteur.hypotheses import hyp

PESANTEUR = 9.81                    # m/s²
EXPOSANT = 2.0 / 3.0                # loi de débit des défauts d'étanchéité (éq. 151)
INCLINAISON_FACADE_MIN_DEG = 60.0   # façade : à moins de 30° de la verticale (§ 5.6.3.1.4)
INCLINAISON_FACADE_MAX_DEG = 120.0  # au-delà : plancher bas, hors de la surface perméable
ITERATIONS = 180                    # essais au plus ; jamais atteint : encadrement divisé par 2 tous les 3 essais
PRECISION_PRESSION = 1e-12          # Pa : la recherche de Pib s'arrête quand deux essais successifs sont plus proches
ESSAIS_PAR_CONTROLE = 3             # tous les 3 essais, l'encadrement doit avoir été divisé par 2 ; sinon dichotomie
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
    """Ouvertures conventionnelles du groupe : liste de (C, Cp, altitude z en m, exposant n), débit C × |ΔP|^n.

    Défauts d'étanchéité (n = 2/3, C en m³/h/Pa^(2/3)) : quatre de façade (au vent et sous le vent, en bas et en
    haut, un quart chacun) et, s'il y a une toiture, un cinquième qui porte toute sa perméabilité (tableaux 28 et
    29). Entrées d'air du projet (n = 0,5, C en m³/h/Pa^0,5, éq. 141) : un quart à chacune des quatre places de
    façade (tableau 25), toutes à l'altitude unique d'un logement. En habitation, pas de tirage entre niveaux :
    les altitudes sont comptées sur 3 m au plus (éq. 138).
    """
    hauteur = min(hauteur_zone_m if hauteur_zone_m is not None else hyp("inf_hauteur_tirage_max"),
                  hyp("inf_hauteur_tirage_max"))
    # Caractère traversant au sens des conditions d'hiver (tableau 22) : celui de la zone s'il est donné
    traversant = groupe.traversant if groupe.traversant_hiver is None else groupe.traversant_hiver
    if traversant and hauteur_moyenne_m is None:
        warnings.warn(f"Groupe « {groupe.nom} » : hauteur moyenne de la zone inconnue, prise sous 15 m "
                      "(Cp au vent 0,25 au lieu de 0,45, tableau 23)", stacklevel=2)
    cp_vent, cp_sous_vent, cp_toit = coefficients_pression(traversant, hauteur_moyenne_m)
    defauts = []
    if groupe.permeabilite_q4pa:
        facade, toit = surfaces_permeables(groupe)
        par_pascal = groupe.permeabilite_q4pa / hyp("inf_pression_reference") ** EXPOSANT         # éq. 150
        bas, haut = hyp("inf_part_altitude_basse") * hauteur, hyp("inf_part_altitude_haute") * hauteur
        quart = 0.25 * facade * par_pascal
        defauts += [(quart, cp, z, EXPOSANT) for cp in (cp_vent, cp_sous_vent) for z in (bas, haut)]
        if toit > 0:
            defauts.append((toit * par_pascal, cp_toit, hauteur, EXPOSANT))
    # Entrées d'air du projet, gardées en mode Bbio comme le fait le moteur réglementaire (hypothèse 92)
    if groupe.module_entrees_air_m3h:
        n = hyp("inf_ea_exposant")
        quart = 0.25 * groupe.module_entrees_air_m3h / hyp("inf_ea_pression_reference") ** n        # éq. 141
        z = hyp("inf_ea_position") * hauteur
        defauts += [(quart, cp, z, n) for cp in (cp_vent, cp_vent, cp_sous_vent, cp_sous_vent)]
    return [d for d in defauts if d[0] > 0]


# ============================================================
# 2. ÉQUILIBRE AÉRAULIQUE D'UNE HEURE (fiche 5.6, éq. 135 à 137, 151, 161 et 167)
# ============================================================
def equilibre(defauts, vent, te, theta_i, debit_ventilation_m3h=0.0, theta_souffle=None):
    """Pression intérieure d'équilibre et débits par les défauts d'étanchéité.

    defauts                 liste de (C, Cp, z, n) de defauts_groupe() ; sans n, n = 2/3 (défaut d'étanchéité)
    vent                    vitesse du vent corrigée (m/s)
    te, theta_i             températures extérieure et intérieure (°C)
    debit_ventilation_m3h   débit de la double flux, soufflé et repris à volumes égaux
    theta_souffle           température de l'air soufflé (°C) ; par défaut te
    Sortie : dictionnaire pib (Pa), debit_entrant_kg_s, debit_sortant_kg_s (négatif) et
    debit_entrant_m3h (volume équivalent à la masse volumique de référence).
    """
    rho_ext, rho_int = masse_volumique(te), masse_volumique(theta_i)
    # Pression motrice de chaque défaut, hors Pib : vent et tirage thermique (éq. 135 à 137)
    motrices = [0.5 * d[1] * rho_ext * vent ** 2 + (rho_int - rho_ext) * PESANTEUR * d[2] for d in defauts]
    coefficients = [d[0] for d in defauts]
    exposants = [d[3] if len(d) > 3 else EXPOSANT for d in defauts]     # 2/3 défaut, 0,5 entrée d'air
    # Ventilation double flux : masses soufflée et reprise (éq. 156-157)
    rho_souffle = masse_volumique(theta_souffle if theta_souffle is not None else te)
    net_ventilation = (rho_souffle - rho_int) * debit_ventilation_m3h / SECONDES_PAR_HEURE

    defauts_du_bilan = list(zip(coefficients, motrices, exposants))
    secondes = SECONDES_PAR_HEURE

    def bilan(pib):
        """Somme des débits massiques entrant dans le groupe (kg/s) pour une pression Pib : décroît avec Pib.

        Appelé une dizaine de fois par heure : écrit au plus court (dp > 0 : |dp| = dp ; sinon |dp| = −dp)."""
        total = net_ventilation
        for c, motrice, n in defauts_du_bilan:
            dp = motrice - pib
            if dp > 0:
                total += rho_ext * c * dp ** n / secondes
            else:
                total += rho_int * c * -((-dp) ** n) / secondes
        return total

    # Encadrement : sous la plus petite pression motrice tout entre, au-dessus de la plus grande tout sort ;
    # élargi tant que la ventilation déséquilibrée l'exige
    bas, haut = min(motrices) - MARGE_PRESSION, max(motrices) + MARGE_PRESSION
    bilan_bas = bilan(bas)
    while bilan_bas < 0:
        bas -= 10.0 * (haut - bas)
        bilan_bas = bilan(bas)
    bilan_haut = bilan(haut)
    while bilan_haut > 0:
        haut += 10.0 * (haut - bas)
        bilan_haut = bilan(haut)
    # Recherche de Pib : le bilan décroît de bilan(bas) > 0 à bilan(haut) < 0.
    #   1. fausse position : on essaie le point où la corde entre les deux bornes coupe zéro ; si la même borne
    #      vient d'être déplacée deux fois de suite, le bilan de l'autre est divisé par deux (variante dite
    #      « Illinois »), ce qui force les deux bornes à se rapprocher de la solution ;
    #   2. garde-fou : si, en ESSAIS_PAR_CONTROLE essais, l'encadrement n'a pas été divisé par deux, l'essai
    #      suivant est le milieu (dichotomie) ;
    #   3. arrêt quand deux essais successifs sont à moins de PRECISION_PRESSION, ou sur un bilan nul.
    if bilan_bas == 0.0:
        pib = bas
    elif bilan_haut == 0.0:
        pib = haut
    else:
        pib = None
        dernier_cote = 0                # + 1 : borne basse déplacée à l'essai précédent ; − 1 : borne haute
        largeur_controle, au_milieu = haut - bas, False
        for essai_no in range(1, ITERATIONS + 1):
            if au_milieu:
                essai = 0.5 * (bas + haut)
            else:
                essai = (bas * bilan_haut - haut * bilan_bas) / (bilan_haut - bilan_bas)
                if not bas < essai < haut:          # arrondis : la corde sort de l'encadrement
                    essai = 0.5 * (bas + haut)
            bilan_essai = bilan(essai)
            if bilan_essai == 0.0 or (pib is not None and abs(essai - pib) <= PRECISION_PRESSION):
                pib = essai
                break
            pib = essai
            if bilan_essai > 0:
                bas, bilan_bas = essai, bilan_essai
                if dernier_cote == 1 and not au_milieu:
                    bilan_haut *= 0.5
                dernier_cote = 1
            else:
                haut, bilan_haut = essai, bilan_essai
                if dernier_cote == -1 and not au_milieu:
                    bilan_bas *= 0.5
                dernier_cote = -1
            if au_milieu:
                dernier_cote, au_milieu = 0, False
            if essai_no % ESSAIS_PAR_CONTROLE == 0:
                au_milieu = haut - bas > 0.5 * largeur_controle
                largeur_controle = haut - bas
            if haut - bas <= PRECISION_PRESSION:
                pib = 0.5 * (bas + haut)
                break

    entrant = sortant = 0.0
    for c, motrice, n in zip(coefficients, motrices, exposants):
        dp = motrice - pib
        if dp > 0:
            entrant += rho_ext * c * dp ** n / SECONDES_PAR_HEURE
        else:
            sortant -= rho_int * c * (-dp) ** n / SECONDES_PAR_HEURE
    return {"pib": pib, "debit_entrant_kg_s": entrant, "debit_sortant_kg_s": sortant,
            "debit_entrant_m3h": entrant * SECONDES_PAR_HEURE / hyp("air_masse_volumique_reference")}


# ============================================================
# 3. LE GROUPE, HEURE PAR HEURE
# ============================================================
def groupe_permeable(groupe):
    """Vrai si une perméabilité à l'air ou des entrées d'air sont renseignées pour le groupe."""
    return bool(groupe.permeabilite_q4pa) or bool(groupe.module_entrees_air_m3h)


class InfiltrationsGroupe:
    """Infiltrations d'un groupe en mode Bbio : équilibre aéraulique de chaque heure."""

    def __init__(self, groupe, meteo, debit_ventilation_m3h, hauteur_zone_m=None, hauteur_moyenne_m=None):
        self.defauts = defauts_groupe(groupe, hauteur_zone_m, hauteur_moyenne_m)
        self.debit_ventilation = debit_ventilation_m3h
        self.vent = hyp("vent_correction_locale") * meteo["Vent"].to_numpy(float)       # fiche 3.2 : Ventc
        self.te = meteo["te"].to_numpy(float)
        self.chaleur_volumique = hyp("chaleur_volumique_air")

    def pas(self, h, theta_i_prec, theta_souffle):
        """Débit entrant par les défauts à l'heure h et son coefficient d'échange (W/K, air à te)."""
        if not self.defauts:
            return {"debit_m3h": 0.0, "hg": 0.0, "pib": 0.0}
        r = equilibre(self.defauts, self.vent[h], self.te[h], theta_i_prec, self.debit_ventilation, theta_souffle)
        return {"debit_m3h": r["debit_entrant_m3h"], "pib": r["pib"],
                "hg": self.chaleur_volumique * r["debit_entrant_m3h"]}
