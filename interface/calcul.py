"""
============================================================
 CALCUL — de la boîte aux résultats que montrent les briques
============================================================
 Lance sur la boîte saisie l'un des deux calculs du moteur, ou
 les deux :

     boîte → projet → Bbio (climat moyen, mode Th-B)   resultats_bbio()
                    → DH   (année caniculaire, mode Th-D) resultats_dh()

 et n'en garde que ce que l'interface affiche : le moteur rend
 8 760 heures de 40 à 50 colonnes par calcul, trop lourd à garder
 en mémoire pour chaque essai de l'utilisateur.

 Les deux calculs pèsent à peu près autant et ne dépendent pas
 l'un de l'autre : l'interface ne lance que celui qu'on lui
 demande, et les garde en mémoire séparément (passer du DH seul
 au Bbio et au DH ne lance que le Bbio).

 Ce fichier ne dépend pas de Streamlit ; app.py met
 resultats_bbio() et resultats_dh() en cache. Une brique qui a
 besoin d'une autre grandeur horaire l'ajoute à COLONNES_ETE.
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
CALCULS = ("bbio", "dh")        # les deux calculs, dans l'ordre d'affichage


@dataclass
class Resultats:
    """Ce que les briques reçoivent ; les champs d'un calcul non lancé valent None.

    bbio      ligne du groupe de moteur.bbio.calculer_bbio (b_ch, b_fr, b_ecl, bbio, bbio_max, modulations…)
    mensuel   une ligne par mois conventionnel : mois, b_ch, b_fr, b_ecl, bbio
    dh        ligne du groupe de moteur.dh.calculer_dh (dh, dh_max, heures d'inconfort, avertissement…)
    ete       les 8 760 heures de l'année caniculaire : date (heure légale), te (extérieur, °C) et COLONNES_ETE
    """
    bbio: dict = None
    mensuel: pd.DataFrame = None
    dh: dict = None
    ete: pd.DataFrame = None

    def calculs(self):
        """Les calculs présents, parmi CALCULS."""
        return tuple(nom for nom in CALCULS if getattr(self, nom) is not None)


def dates_legales(calendrier):
    """Date et heure légales du début de chaque pas de temps, pour l'axe des graphiques.

    Heure UTC plus le décalage légal (1 h en hiver, 2 h en été) : la série saute une heure au passage à l'heure
    d'été et en répète une au retour à l'heure d'hiver, comme une horloge.
    """
    debut = pd.Timestamp(year=ANNEE_AFFICHEE, month=1, day=1)
    return debut + pd.to_timedelta(calendrier["h"] + calendrier["ehlo"], unit="h")


def resultats_bbio(boite):
    """Champs bbio et mensuel de Resultats ; lève une ValueError au message clair si la saisie est incohérente."""
    bbio = calculer_bbio(construire_projet(boite), calendrier=construire_calendrier())
    return {"bbio": bbio.groupes.iloc[0].to_dict(),
            "mensuel": bbio.mensuel[["mois", "b_ch", "b_fr", "b_ecl", "bbio"]].reset_index(drop=True)}


def resultats_dh(boite):
    """Champs dh et ete de Resultats ; lève une ValueError au message clair si la saisie est incohérente."""
    calendrier = construire_calendrier()
    dh = calculer_dh(construire_projet(boite), calendrier=calendrier)
    meteo = charger_meteo(boite.zone_climatique, JEUX_DES_MODES[MODE_DH], boite.altitude_m)
    ete = dh.horaire[CLE_GROUPE][COLONNES_ETE].reset_index(drop=True)
    ete.insert(0, "te", meteo["te"].to_numpy())
    ete.insert(0, "date", dates_legales(calendrier).to_numpy())
    return {"dh": dh.groupes.iloc[0].to_dict(), "ete": ete}


def calculer(boite, calculs=CALCULS):
    """Résultats des calculs demandés (« bbio », « dh » ou les deux), sans mémoire : app.py garde les siens."""
    fonctions = {"bbio": resultats_bbio, "dh": resultats_dh}
    champs = {}
    for nom in calculs:
        champs.update(fonctions[nom](boite))
    return Resultats(**champs)
