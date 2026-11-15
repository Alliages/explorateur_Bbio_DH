r"""
============================================================
 DH — degrés-heures d'inconfort d'été et DH max
============================================================
 Sources :
   annexe III de l'arrêté du 4 août 2021, fiche 13.5
     (C_CALC_Indicateur de confort d'été), éq. 2542 à 2551 ;
   code de la construction et de l'habitation, annexe à
     l'article R. 172-4, chapitre II, IV et chapitre III, IV
     (version du décret n° 2026-200 du 18 mars 2026) : DH max.

 Le DH mesure à la fois la durée et l'intensité de l'inconfort
 chaud d'un groupe, sur une année à séquence caniculaire (jeu
 météo Th-D) :

     DH = Σ MAX(0 ; θop(h) − θconf(h))               (éq. 2551)

        θ (°C)
           |        .--.        θop : température opérative
           |      .'####'.            du groupe, en fin de pas
     θconf |-----'--------'------
           |   .'          '.   #### : degrés-heures comptés
           +-------------------------> heures

   - θconf est la température limite de confort chaud
     (moteur/confort.py) : 26 °C la nuit, 26 à 28 °C le jour
     selon la chaleur des jours précédents, relevée par l'effet
     des brasseurs d'air (éq. 2547) ;
   - seules comptent les heures d'OCCUPATION, en PÉRIODE DE
     CONFORT ADAPTATIF ;
   - la température vient du calcul Th-D du groupe
     (moteur.besoins.calculer_besoins, mode « th_d ») : sans
     climatisation, même pour un groupe climatisé.

 Indicateurs pédagogiques (éq. 2548 à 2550) : nombre d'heures où
 θop atteint θconf, θconf + 1 °C et θconf + 2 °C.

 DH max du logement collectif, en °C.h, selon la surface
 moyenne des logements Smoylgt (m²) :

                    catégorie 1    catégorie 1 climatisée    catégorie 2
                                   en H2d ou H3
   Smoylgt ≤ 20        1 250            1 600                  2 600
   20 à 60             1 250        1 700 − 5 × S          2 850 − 12,5 × S
   Smoylgt > 60        1 250            1 400                  2 100

 Hypothèse de l'outil (docs/audit.md, 0.8.16) : le chapitre V,
 qui définit les catégories de contraintes extérieures, manque
 aux sources. La règle retenue est celle observée sur des
 études : catégorie 2 si le groupe est climatisé ET exposé au
 bruit (BR2 ou BR3), catégorie 1 sinon.

 L'outil est pédagogique : la comparaison au DH max situe le
 projet, elle n'a aucune valeur réglementaire.
============================================================
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from moteur.bbio import controler_projet
from moteur.besoins import JEUX_DES_MODES, calculer_besoins
from moteur.calendrier import construire_calendrier
from moteur.hypotheses import hyp
from moteur.meteo import charger_meteo
from moteur.ouvertures import groupe_ouvrable
from moteur.protections import groupe_protege
from moteur.scenarios import charger_scenarios

MODE = "th_d"                       # confort d'été : jeu météo de l'année à séquence caniculaire
ZONES_CHAUDES = ("H2d", "H3")       # zones où une partie climatisée de catégorie 1 a son propre DH max
EXPOSITIONS_BRUYANTES = ("BR2", "BR3")
ECARTS_PEDAGOGIQUES = (0.0, 1.0, 2.0)   # °C au-dessus du seuil, pour les trois compteurs d'heures (éq. 2548 à 2550)


# ============================================================
# 1. DEGRÉS-HEURES (fiche 13.5, éq. 2548 à 2551)
# ============================================================
def degres_heures(theta_op, seuil, occupe, confort_adaptatif):
    """Degrés-heures d'inconfort chaud et indicateurs pédagogiques, à partir de séries horaires.

    theta_op            température opérative du groupe en fin de pas (°C)
    seuil               température limite de confort chaud, corrigée des brasseurs d'air (°C)
    occupe              occupation de la zone (0 ou 1, ou booléens)
    confort_adaptatif   indicateur de période de confort adaptatif (0 ou 1, ou booléens)
    Sortie : dictionnaire
        dh                  degrés-heures de l'année (°C.h)
        nb_h_inconfort      heures où θop ≥ seuil ; nb_h_inconfort_1 et _2 : seuil + 1 °C et + 2 °C
        dh_horaire          degrés-heures de chaque heure (tableau)
    """
    theta_op = np.asarray(theta_op, dtype=float)
    ecart = theta_op - np.asarray(seuil, dtype=float)
    retenue = np.asarray(occupe).astype(bool) & np.asarray(confort_adaptatif).astype(bool)
    dh_horaire = np.where(retenue, np.maximum(0.0, ecart), 0.0)                     # éq. 2551
    compteurs = [int((retenue & (ecart >= marge)).sum()) for marge in ECARTS_PEDAGOGIQUES]
    return {"dh": float(dh_horaire.sum()), "nb_h_inconfort": compteurs[0], "nb_h_inconfort_1": compteurs[1],
            "nb_h_inconfort_2": compteurs[2], "dh_horaire": dh_horaire}


def dh_groupe(heures):
    """Degrés-heures d'un groupe à partir du résultat horaire de calculer_besoins(mode="th_d")."""
    return degres_heures(heures["theta_op"], heures["seuil_confort_corrige"], heures["occupe"],
                         heures["confort_adaptatif"])


# ============================================================
# 2. DH MAX (annexe à l'article R. 172-4, chapitre III, IV)
# ============================================================
def categorie_contraintes(climatise, exposition_bruit):
    """Catégorie de contraintes extérieures (1 ou 2) : 2 si le groupe est climatisé et exposé au bruit.

    Règle observée sur des études, faute du chapitre V dans les sources (hypothèse de l'outil).
    """
    return 2 if climatise and exposition_bruit in EXPOSITIONS_BRUYANTES else 1


def _selon_surface(prefixe, surface_moyenne_logement_m2):
    """Valeur d'une colonne à trois tranches de surface moyenne des logements."""
    s = surface_moyenne_logement_m2
    if s <= hyp("dh_max_lc_surface_seuil_1"):
        return hyp(f"{prefixe}_petit")
    if s <= hyp("dh_max_lc_surface_seuil_2"):
        return hyp(f"{prefixe}_origine") - hyp(f"{prefixe}_pente") * s
    return hyp(f"{prefixe}_grand")


def dh_max(zone_climatique, surface_moyenne_logement_m2, climatise=False, exposition_bruit="BR1",
           usage="logement_collectif"):
    """DH max d'une partie de bâtiment (°C.h) et catégorie de contraintes extérieures retenue.

    surface_moyenne_logement_m2   Smoylgt de la zone : surface de référence / nombre de logements
    Sortie : dictionnaire categorie (1 ou 2) et dh_max.
    """
    if usage != "logement_collectif":
        raise ValueError(f"DH max : usage « {usage} » non traité (logement collectif seulement)")
    categorie = categorie_contraintes(climatise, exposition_bruit)
    if categorie == 2:
        valeur = _selon_surface("dh_max_lc_categorie_2", surface_moyenne_logement_m2)
    elif climatise and zone_climatique in ZONES_CHAUDES:
        valeur = _selon_surface("dh_max_lc_categorie_1_clim", surface_moyenne_logement_m2)
    else:
        valeur = hyp("dh_max_lc_categorie_1")
    return {"categorie": categorie, "dh_max": valeur}


# ============================================================
# 3. DH D'UN PROJET, GROUPE PAR GROUPE
# ============================================================
def avertissements_confort(groupe):
    """Ce qui manque à la description d'un groupe pour que son DH ait un sens, en clair (texte vide si rien).

    Sans protection mobile ni baie ouvrable, rien ne limite la chaleur de l'année caniculaire : la température
    calculée dépasse facilement 40 °C et le DH n'est plus comparable à celui d'une étude.
    """
    manques = []
    if not groupe_protege(groupe):
        manques.append("aucune protection mobile")
    if not groupe_ouvrable(groupe):
        manques.append("aucune baie ouvrable")
    return ", ".join(manques)


@dataclass
class ResultatDH:
    """Résultats du confort d'été d'un projet.

    groupes     une ligne par groupe : batiment, zone, groupe, sref_m2, climatise, exposition_bruit,
                surface_moyenne_logement_m2, dh (°C.h), nb_h_inconfort, nb_h_inconfort_1, nb_h_inconfort_2,
                debut_confort_adaptatif et fin_confort_adaptatif (heures de simulation), theta_op_max (°C),
                categorie, dh_max (°C.h), ecart_pct, respecte et avertissement (voir avertissements_confort)
    horaire     {(batiment, zone, groupe): résultat horaire de calculer_besoins(mode="th_d"), avec dh_horaire}
    """
    groupes: pd.DataFrame
    horaire: dict


def calculer_dh(projet, scenarios=None, calendrier=None):
    """Degrés-heures et DH max d'un projet, groupe par groupe (mode Th-D, jeu météo Th-D).

    scenarios    scénarios à appliquer à toutes les zones ; par défaut ceux de l'usage de chaque zone
    calendrier   calendrier conventionnel ; par défaut moteur.calendrier.construire_calendrier()
    Le DH se lit par groupe : le texte ne prévoit pas de moyenne par zone ou par bâtiment.
    """
    controler_projet(projet)
    calendrier = calendrier if calendrier is not None else construire_calendrier()
    meteo = charger_meteo(projet.zone_climatique, JEUX_DES_MODES[MODE], projet.altitude_m)

    lignes, horaire = [], {}
    for batiment in projet.batiments:
        for zone in batiment.zones:
            if not zone.groupes:
                continue
            scenarios_zone = scenarios if scenarios is not None else charger_scenarios(zone.usage)
            surface_moyenne = zone.surface_m2 / zone.nb_logements
            for groupe in zone.groupes:
                cle = {"batiment": batiment.nom, "zone": zone.nom, "groupe": groupe.nom}
                # Températures de l'année caniculaire, puis degrés-heures
                heures = calculer_besoins(groupe, meteo, scenarios_zone, calendrier, mode=MODE,
                                          hauteur_zone_m=zone.hauteur_m, hauteur_moyenne_m=zone.hauteur_moyenne_m)
                r = dh_groupe(heures)
                heures["dh_horaire"] = r.pop("dh_horaire")
                horaire[tuple(cle.values())] = heures
                # Période de confort adaptatif : première et dernière heures de simulation
                periode = np.flatnonzero(heures["confort_adaptatif"].to_numpy())
                debut, fin = (int(periode[0]), int(periode[-1])) if periode.size else (None, None)
                maxi = dh_max(projet.zone_climatique, surface_moyenne, groupe.climatise, groupe.exposition_bruit,
                              zone.usage)
                lignes.append({**cle, "sref_m2": groupe.surface_m2, "climatise": groupe.climatise,
                               "exposition_bruit": groupe.exposition_bruit,
                               "surface_moyenne_logement_m2": surface_moyenne, **r,
                               "debut_confort_adaptatif": debut, "fin_confort_adaptatif": fin,
                               "theta_op_max": float(heures["theta_op"].max()), **maxi,
                               "avertissement": avertissements_confort(groupe)})

    groupes = pd.DataFrame(lignes)
    groupes["ecart_pct"] = (groupes["dh"] / groupes["dh_max"] - 1.0) * 100.0
    groupes["respecte"] = groupes["dh"] <= groupes["dh_max"]
    # L'avertissement se lit en dernier, après les résultats
    groupes = groupes[[c for c in groupes.columns if c != "avertissement"] + ["avertissement"]]
    return ResultatDH(groupes=groupes, horaire=horaire)
