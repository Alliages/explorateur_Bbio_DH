r"""
============================================================
 BBIO — besoin bioclimatique d'un projet et Bbio max
============================================================
 Sources :
   annexe III de l'arrêté du 4 août 2021, fiche 13.1
     (C_CALC_Sorties du mode Th-B), éq. 2375 à 2386 ;
   code de la construction et de l'habitation, annexe à
     l'article R. 172-4, chapitres I à III (version du décret
     n° 2026-200 du 18 mars 2026) : Bbio max.

 Bbio (en points) :

     Bbio = 2 × Bch + 2 × Bfr + 5 × Becl            (éq. 2385)

   Bch, Bfr, Becl : besoins annuels de chauffage, de
   refroidissement et d'éclairage, en kWh par m² de surface de
   référence (moteur/besoins.py). La surface de référence d'un
   logement est sa surface habitable.

 Trois niveaux de résultat (fiche 13.1) :

     groupe  →  zone  →  bâtiment

   Les besoins d'une zone ou d'un bâtiment sont ceux de ses
   groupes, pondérés par leur surface de référence : ce sont
   des kWh rapportés aux m² de l'ensemble.

 Bbio max (annexe à l'article R. 172-4, chapitre II, I) :

     Bbio_max = Bbio_maxmoyen × (1 + Mbgéo + Mbcombles
                + Mbsurf_moy + Mbsurf_tot + Mbbruit + MbHSP)

   Logements collectifs : Bbio_maxmoyen = 65 points ;
     Mbgéo       zone climatique et altitude ;
     Mbcombles   nul ;
     Mbsurf_moy  surface moyenne des logements de la zone,
                 Smoylgt = Sref / nombre de logements ;
     Mbsurf_tot  surface de référence du bâtiment (tous les
                 logements collectifs du bâtiment) ;
     Mbbruit     exposition au bruit (BR1, BR2, BR3) ;
     MbHSP       hauteur sous plafond moyenne des logements
                 collectifs du bâtiment, au-delà de 2,5 m.
   Le Bbio max d'une zone ou d'un bâtiment est la moyenne de
   ceux de ses parties, pondérée par leur surface de référence
   (chapitre II, V).

 L'outil est pédagogique : la comparaison au Bbio max situe le
 projet, elle n'a aucune valeur réglementaire. Tant que les
 protections mobiles et l'ouverture des baies ne sont pas
 modélisées (0.9.4), le besoin de froid, donc le Bbio, est
 surestimé (voir docs/audit.md).
============================================================
"""

from dataclasses import dataclass

import pandas as pd

from moteur.besoins import JEU, bilan_besoins, calculer_besoins
from moteur.calendrier import construire_calendrier
from moteur.hypotheses import hyp
from moteur.meteo import charger_meteo
from moteur.scenarios import charger_scenarios

BESOINS = ["b_ch", "b_fr", "b_ecl"]                                     # kWh/m² de surface de référence
MODULATIONS = ["mb_geo", "mb_combles", "mb_surf_moy", "mb_surf_tot", "mb_bruit", "mb_hsp"]
EXPOSITION_SANS_BRUIT = "BR1"
POURCENT = 100.0


# ============================================================
# 1. BBIO (fiche 13.1, éq. 2385)
# ============================================================
def points_bbio(b_ch, b_fr, b_ecl):
    """Bbio en points à partir des besoins en kWh/m² : 2 × Bch + 2 × Bfr + 5 × Becl (éq. 2385).

    Accepte des nombres ou des colonnes : la formule vaut pour un mois comme pour l'année.
    """
    return (hyp("bbio_coef_chauffage") * b_ch + hyp("bbio_coef_refroidissement") * b_fr
            + hyp("bbio_coef_eclairage") * b_ecl)


# ============================================================
# 2. BBIO MAX (annexe à l'article R. 172-4, chapitres II et III)
# ============================================================
def classe_altitude(altitude_m):
    """Ligne du tableau Mbgéo : « basse » (< 400 m), « moyenne » (400 à 800 m) ou « haute » (> 800 m)."""
    if altitude_m < hyp("bbio_altitude_seuil_bas"):
        return "basse"
    if altitude_m <= hyp("bbio_altitude_seuil_haut"):
        return "moyenne"
    return "haute"


def mb_geo(zone_climatique, altitude_m):
    """Mbgéo : modulation selon la zone climatique et l'altitude."""
    return hyp(f"bbio_mbgeo_{zone_climatique}_{classe_altitude(altitude_m)}")


def mb_surf_moy(surface_moyenne_logement_m2, bbio_max_moyen):
    """Mbsurf_moy : modulation selon la surface moyenne des logements (Smoylgt = Sref / nombre de logements).

    Le texte donne des points, à diviser par Bbio_maxmoyen : de petits logements abaissent le Bbio max.
    """
    s = surface_moyenne_logement_m2
    if s <= hyp("bbio_mbsurf_moy_seuil_1"):
        points = hyp("bbio_mbsurf_moy_origine_1") + hyp("bbio_mbsurf_moy_pente_1") * s
    elif s <= hyp("bbio_mbsurf_moy_seuil_2"):
        points = hyp("bbio_mbsurf_moy_origine_2") + hyp("bbio_mbsurf_moy_pente_2") * s
    else:
        points = hyp("bbio_mbsurf_moy_plafond")
    return points / bbio_max_moyen


def mb_surf_tot(sref_batiment_m2, bbio_max_moyen):
    """Mbsurf_tot : modulation selon la surface de référence du bâtiment (petits bâtiments : Bbio max relevé)."""
    if sref_batiment_m2 > hyp("bbio_mbsurf_tot_seuil"):
        return 0.0
    return (hyp("bbio_mbsurf_tot_origine") - hyp("bbio_mbsurf_tot_pente") * sref_batiment_m2) / bbio_max_moyen


def mb_bruit(zone_climatique, exposition_bruit):
    """Mbbruit : modulation selon l'exposition au bruit ; nulle en BR1, selon la zone climatique en BR2 et BR3."""
    if exposition_bruit == EXPOSITION_SANS_BRUIT:
        return 0.0
    return hyp(f"bbio_mbbruit_{zone_climatique}")


def mb_hsp(hauteur_sous_plafond_m):
    """MbHSP : modulation selon la hauteur sous plafond moyenne, (MIN(HSPmoy ; 2,9) / 2,5 − 1) / 1,5.

    Nulle jusqu'à 2,5 m, ou si la hauteur n'est pas renseignée.
    """
    seuil = hyp("bbio_mbhsp_seuil")
    if hauteur_sous_plafond_m is None or hauteur_sous_plafond_m <= seuil:
        return 0.0
    return (min(hauteur_sous_plafond_m, hyp("bbio_mbhsp_plafond")) / seuil - 1.0) / hyp("bbio_mbhsp_diviseur")


def bbio_max(zone_climatique, altitude_m, surface_moyenne_logement_m2, sref_batiment_m2,
             exposition_bruit=EXPOSITION_SANS_BRUIT, hauteur_sous_plafond_m=None, usage="logement_collectif"):
    """Bbio max d'une partie de bâtiment et détail de ses modulations.

    surface_moyenne_logement_m2   Smoylgt de la zone : surface de référence / nombre de logements
    sref_batiment_m2              surface de référence de tous les logements collectifs du bâtiment
    Sortie : dictionnaire bbio_max_moyen, mb_geo, mb_combles, mb_surf_moy, mb_surf_tot, mb_bruit, mb_hsp
    et bbio_max (points).
    """
    moyen = hyp(f"bbio_max_moyen_{usage}")
    detail = {"bbio_max_moyen": moyen,
              "mb_geo": mb_geo(zone_climatique, altitude_m),
              "mb_combles": 0.0,                                        # nul en logement collectif
              "mb_surf_moy": mb_surf_moy(surface_moyenne_logement_m2, moyen),
              "mb_surf_tot": mb_surf_tot(sref_batiment_m2, moyen),
              "mb_bruit": mb_bruit(zone_climatique, exposition_bruit),
              "mb_hsp": mb_hsp(hauteur_sous_plafond_m)}
    detail["bbio_max"] = moyen * (1.0 + sum(detail[nom] for nom in MODULATIONS))
    return detail


# ============================================================
# 3. BBIO D'UN PROJET : GROUPES, ZONES, BÂTIMENTS
# ============================================================
@dataclass
class ResultatBbio:
    """Résultats du Bbio d'un projet.

    groupes     une ligne par groupe : batiment, zone, groupe, sref_m2, b_ch, b_fr, b_ecl (kWh/m²), bbio
                (points), modulations (mb_...) et bbio_max (points)
    zones       une ligne par zone : les mêmes grandeurs, plus nb_logements et surface_moyenne_logement_m2
    batiments   une ligne par bâtiment, plus ecart_pct (écart du Bbio au Bbio max, en %) et respecte
    mensuel     une ligne par groupe et par mois conventionnel : b_ch, b_fr, b_ecl et bbio
    horaire     {(batiment, zone, groupe): résultat horaire de moteur.besoins.calculer_besoins()}
    """
    groupes: pd.DataFrame
    zones: pd.DataFrame
    batiments: pd.DataFrame
    mensuel: pd.DataFrame
    horaire: dict


def ponderer(table, cles, colonnes):
    """Moyennes pondérées par la surface de référence (sref_m2), par ensemble « cles » (fiche 13.1).

    Une zone (un bâtiment) a pour besoin la somme des kWh de ses groupes, rapportée à la somme de leurs m².
    Sortie : cles, sref_m2 (somme) et les colonnes pondérées.
    """
    produits = table[colonnes].multiply(table["sref_m2"], axis=0)
    produits[cles] = table[cles]
    produits["sref_m2"] = table["sref_m2"]
    sommes = produits.groupby(cles, sort=False).sum()
    sommes[colonnes] = sommes[colonnes].div(sommes["sref_m2"], axis=0)
    return sommes[["sref_m2"] + colonnes].reset_index()


def _controler_projet(projet):
    """Erreurs claires avant un calcul long : projet vide, noms en double, nombre de logements manquant."""
    cles = [(batiment.nom, zone.nom, groupe.nom)
            for batiment in projet.batiments for zone in batiment.zones for groupe in zone.groupes]
    if not cles:
        raise ValueError(f"Projet « {projet.nom} » : aucun groupe à calculer")
    doubles = sorted({cle for cle in cles if cles.count(cle) > 1})
    if doubles:
        raise ValueError(f"Projet « {projet.nom} » : noms en double (bâtiment, zone, groupe) : {doubles}")
    for batiment in projet.batiments:
        for zone in batiment.zones:
            if zone.groupes and zone.nb_logements is None:
                raise ValueError(f"Zone « {zone.nom} » : nombre de logements à renseigner sur chaque groupe "
                                 "(apports internes et Bbio max)")


def hauteur_sous_plafond_moyenne(batiment, usage):
    """HSPmoy des zones d'un usage du bâtiment : moyenne des hauteurs saisies, pondérée par la surface de référence.

    Les zones sans hauteur saisie ne comptent pas ; None si aucune n'en a. Les études appliquent bien la même
    hauteur moyenne à toutes les zones de logements d'un bâtiment (voir docs/audit.md, 0.8.10).
    """
    zones = [z for z in batiment.zones if z.usage == usage and z.hauteur_sous_plafond_m is not None
             and z.surface_m2 > 0]
    if not zones:
        return None
    return sum(z.hauteur_sous_plafond_m * z.surface_m2 for z in zones) / sum(z.surface_m2 for z in zones)


def calculer_bbio(projet, scenarios=None, calendrier=None, refroidissement=True):
    """Bbio et Bbio max d'un projet, par groupe, par zone et par bâtiment (mode Th-B, climat Th-BC).

    scenarios        scénarios à appliquer à toutes les zones ; par défaut ceux de l'usage de chaque zone
    calendrier       calendrier conventionnel ; par défaut moteur.calendrier.construire_calendrier()
    refroidissement  False pour ne pas compter de besoin de froid (voir moteur.besoins.calculer_besoins)
    Sortie : ResultatBbio. Durée : environ une seconde par groupe.
    """
    _controler_projet(projet)
    calendrier = calendrier if calendrier is not None else construire_calendrier()
    meteo = charger_meteo(projet.zone_climatique, JEU, projet.altitude_m)

    lignes, mensuels, horaire = [], [], {}
    for batiment in projet.batiments:
        # Mbsurf_tot : surface de référence de toutes les zones de même usage du bâtiment (chapitre II, I)
        sref_par_usage = {}
        for zone in batiment.zones:
            sref_par_usage[zone.usage] = sref_par_usage.get(zone.usage, 0.0) + zone.surface_m2
        hsp_par_usage = {usage: hauteur_sous_plafond_moyenne(batiment, usage) for usage in sref_par_usage}
        for zone in batiment.zones:
            if not zone.groupes:
                continue
            scenarios_zone = scenarios if scenarios is not None else charger_scenarios(zone.usage)
            surface_moyenne = zone.surface_m2 / zone.nb_logements
            for groupe in zone.groupes:
                cle = {"batiment": batiment.nom, "zone": zone.nom, "groupe": groupe.nom}
                # Besoins du groupe, heure par heure, puis par mois et par an (kWh/m²)
                heures = calculer_besoins(groupe, meteo, scenarios_zone, calendrier, refroidissement)
                mensuel, annuel = bilan_besoins(heures, groupe.surface_m2, calendrier)
                horaire[tuple(cle.values())] = heures
                mensuels.append(mensuel.reset_index().assign(sref_m2=groupe.surface_m2, **cle))
                # Bbio max de la partie de bâtiment que forme le groupe
                maxi = bbio_max(projet.zone_climatique, projet.altitude_m, surface_moyenne,
                                sref_par_usage[zone.usage], groupe.exposition_bruit,
                                hsp_par_usage[zone.usage], zone.usage)
                lignes.append({**cle, "usage": zone.usage, "sref_m2": groupe.surface_m2,
                               "nb_logements": groupe.nb_logements, **annuel.to_dict(), **maxi})

    # --- Groupes : Bbio annuel et mensuel (éq. 2385 et 2386) ---
    groupes = pd.DataFrame(lignes)
    groupes["bbio"] = points_bbio(groupes["b_ch"], groupes["b_fr"], groupes["b_ecl"])
    mensuel = pd.concat(mensuels, ignore_index=True)
    mensuel["bbio"] = points_bbio(mensuel["b_ch"], mensuel["b_fr"], mensuel["b_ecl"])
    mensuel = mensuel[["batiment", "zone", "groupe", "mois", "sref_m2"] + BESOINS + ["bbio"]]

    # --- Zones et bâtiments : moyennes pondérées par la surface de référence ---
    a_ponderer = BESOINS + ["bbio"] + MODULATIONS + ["bbio_max"]
    zones = ponderer(groupes, ["batiment", "zone"], a_ponderer)
    logements = groupes.groupby(["batiment", "zone"], sort=False)["nb_logements"].sum().to_numpy()
    zones.insert(3, "nb_logements", logements)
    zones.insert(4, "surface_moyenne_logement_m2", zones["sref_m2"] / logements)
    batiments = ponderer(groupes, ["batiment"], a_ponderer)
    batiments["ecart_pct"] = (batiments["bbio"] / batiments["bbio_max"] - 1.0) * POURCENT
    batiments["respecte"] = batiments["bbio"] <= batiments["bbio_max"]

    colonnes = ["batiment", "zone", "groupe", "usage", "sref_m2", "nb_logements"] + BESOINS + ["bbio"] \
        + ["bbio_max_moyen"] + MODULATIONS + ["bbio_max"]
    return ResultatBbio(groupes=groupes[colonnes], zones=zones, batiments=batiments, mensuel=mensuel,
                        horaire=horaire)
