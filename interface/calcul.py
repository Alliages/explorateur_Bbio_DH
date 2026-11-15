"""
============================================================
 CALCUL — de la boîte aux résultats que montrent les briques
============================================================
 Enchaîne les deux calculs du moteur sur la boîte saisie :

     boîte → projet → Bbio (climat moyen, mode Th-B)
                    → DH   (année caniculaire, mode Th-D)

 et n'en garde que ce que l'interface affiche : le moteur rend
 8 760 heures de 40 à 50 colonnes par calcul, trop lourd à garder
 en mémoire pour chaque essai de l'utilisateur.

 Ce fichier ne dépend pas de Streamlit ; app.py met calculer()
 en cache. Une brique qui a besoin d'une autre grandeur horaire
 l'ajoute à COLONNES_ETE ou à COLONNES_HIVER.
============================================================
"""

from dataclasses import dataclass

import pandas as pd

from interface.saisie import CLE_GROUPE, construire_projet
from moteur.bbio import calculer_bbio
from moteur.besoins import JEUX_DES_MODES
from moteur.calendrier import construire_calendrier
from moteur.dh import MODE as MODE_DH
from moteur.dh import calculer_dh
from moteur.meteo import charger_meteo

# ============================================================
# RÉGLAGES
# ============================================================
# Colonnes horaires gardées du calcul Th-D (voir moteur.besoins.calculer_besoins et moteur.dh.calculer_dh)
COLONNES_ETE = ["theta_op", "seuil_confort_corrige", "occupe", "confort_adaptatif", "dh_horaire", "rprot_moyen",
                "rouv_moyen", "ecart_ba"]
ANNEE_AFFICHEE = 2023           # année sans 29 février, pour dater les heures sur les graphiques (heure légale)


@dataclass
class Resultats:
    """Ce que les briques reçoivent.

    bbio      ligne du groupe de moteur.bbio.calculer_bbio (b_ch, b_fr, b_ecl, bbio, bbio_max, modulations…)
    mensuel   une ligne par mois conventionnel : mois, b_ch, b_fr, b_ecl, bbio
    dh        ligne du groupe de moteur.dh.calculer_dh (dh, dh_max, heures d'inconfort, avertissement…)
    ete       les 8 760 heures de l'année caniculaire : date (heure légale), te (extérieur, °C) et COLONNES_ETE
    """
    bbio: dict
    mensuel: pd.DataFrame
    dh: dict
    ete: pd.DataFrame


def dates_legales(calendrier):
    """Date et heure légales du début de chaque pas de temps, pour l'axe des graphiques.

    Heure UTC plus le décalage légal (1 h en hiver, 2 h en été) : la série saute une heure au passage à l'heure
    d'été et en répète une au retour à l'heure d'hiver, comme une horloge.
    """
    debut = pd.Timestamp(year=ANNEE_AFFICHEE, month=1, day=1)
    return debut + pd.to_timedelta(calendrier["h"] + calendrier["ehlo"], unit="h")


def calculer(boite):
    """Bbio et DH de la boîte (2 à 4 s) ; lève une ValueError au message clair si la saisie est incohérente."""
    projet = construire_projet(boite)
    calendrier = construire_calendrier()
    bbio = calculer_bbio(projet, calendrier=calendrier)
    dh = calculer_dh(projet, calendrier=calendrier)

    meteo = charger_meteo(boite.zone_climatique, JEUX_DES_MODES[MODE_DH], boite.altitude_m)
    ete = dh.horaire[CLE_GROUPE][COLONNES_ETE].reset_index(drop=True)
    ete.insert(0, "te", meteo["te"].to_numpy())
    ete.insert(0, "date", dates_legales(calendrier).to_numpy())
    return Resultats(bbio=bbio.groupes.iloc[0].to_dict(),
                     mensuel=bbio.mensuel[["mois", "b_ch", "b_fr", "b_ecl", "bbio"]].reset_index(drop=True),
                     dh=dh.groupes.iloc[0].to_dict(), ete=ete)
