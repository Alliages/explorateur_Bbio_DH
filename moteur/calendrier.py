"""
============================================================
 CALENDRIER CONVENTIONNEL — de l'heure de simulation à la
 case des scénarios
============================================================
 Source : annexe III de l'arrêté du 4 août 2021,
   - fiche 3.1 (C_Clim) : Hleg = IHJ + EHLO ;
   - fiche 4.1 (C_EIN_Scénarios conventionnels) : calendrier
     et tableau de correspondance des heures.

 Conventions de la méthode :
   - la simulation compte 8 760 heures, de 0 à 8 759 ; l'heure
     h couvre l'intervalle UTC [h ; h+1[ ;
   - les fichiers météo sont en UTC, les scénarios en heure
     légale : légale = UTC + 1 en hiver, UTC + 2 en été ;
   - l'été va de l'heure 1 896 à l'heure 7 031 incluse ;
   - l'année commence un lundi et compte 52 semaines réparties
     par mois : 4-4-5-4-5-4-4-5-4-4-5-4 ;
   - la « case » d'un scénario (1 à 24) est l'heure légale de
     FIN du pas de temps : la case 2 couvre [1h ; 2h[ légal.

 Exemples du tableau de la fiche 4.1, retrouvés par ce module :
     heure 0     → UTC 0h-1h   → légal 1h-2h → case 2
     heure 1 895 → UTC 23h-0h  → légal 0h-1h → case 1
     heure 1 896 → UTC 0h-1h   → légal 2h-3h → case 3 (passage à l'été)
     heure 7 031 → UTC 23h-0h  → légal 1h-2h → case 2
     heure 7 032 → UTC 0h-1h   → légal 1h-2h → case 2 (retour à l'hiver)

 Deux cas ne sont pas décrits par le texte (voir docs/audit.md) :
   - le jour 365, hors des 52 semaines : c'est un lundi, et il
     reprend les valeurs hebdomadaires d'une semaine fixée dans
     donnees/hypotheses.csv (jour_365_mois, jour_365_semaine) ;
   - la dernière heure de l'année (8 759), dont l'heure légale
     tombe après le 31 décembre : elle est reportée sur le
     1er janvier (l'année est traitée comme un cycle).
============================================================
"""

import numpy as np
import pandas as pd

from config.reglages import HEURES_PAR_JOUR, JOURS_PAR_SEMAINE, NB_HEURES_ANNEE, SEMAINES_PAR_MOIS
from moteur.hypotheses import hyp


def decalage_legal():
    """EHLO : décalage (h) entre l'heure légale et l'heure UTC, pour chaque heure de l'année."""
    heures = np.arange(NB_HEURES_ANNEE)
    ete = (heures >= hyp("iteration_debut_ete")) & (heures < hyp("iteration_fin_ete"))
    return np.where(ete, hyp("decalage_legal_ete"), hyp("decalage_legal_hiver")).astype(int)


def mois_et_semaine(jour_annee):
    """Mois (1-12) et semaine du mois (1-5) de chaque jour de l'année (1-365).

    Les 364 premiers jours suivent la répartition conventionnelle des semaines ; le jour 365
    reçoit le mois et la semaine fixés par hypothèse.
    """
    # Mois et rang dans le mois de chacune des 52 semaines
    mois_des_semaines = np.repeat(np.arange(1, 13), SEMAINES_PAR_MOIS)
    rang_des_semaines = np.concatenate([np.arange(1, n + 1) for n in SEMAINES_PAR_MOIS])
    # Semaine de l'année (0-51) ; le jour 365 tomberait en semaine 52, hors tableau
    semaine_annee = (np.asarray(jour_annee) - 1) // JOURS_PAR_SEMAINE
    hors_tableau = semaine_annee >= len(mois_des_semaines)
    indice = np.where(hors_tableau, 0, semaine_annee)
    mois = np.where(hors_tableau, int(hyp("jour_365_mois")), mois_des_semaines[indice])
    semaine = np.where(hors_tableau, int(hyp("jour_365_semaine")), rang_des_semaines[indice])
    return mois, semaine


def construire_calendrier():
    """Calendrier des 8 760 heures de simulation.

    Colonnes :
        h             heure de simulation (0-8759), début du pas de temps en UTC
        heure_utc     heure du jour UTC de début de pas (0-23)
        ehlo          décalage légal − UTC (1 en hiver, 2 en été)
        case          case des scénarios = heure légale de fin de pas (1-24)
        jour_annee    jour légal de l'année (1-365)
        jour_semaine  jour légal de la semaine (1 = lundi … 7 = dimanche)
        mois          mois conventionnel (1-12)
        semaine_mois  semaine du mois (1-5)
    """
    h = np.arange(NB_HEURES_ANNEE)
    ehlo = decalage_legal()
    # Heure légale de début de pas, comptée depuis le début de l'année ; l'année est un cycle
    h_legale = (h + ehlo) % NB_HEURES_ANNEE
    jour_annee = h_legale // HEURES_PAR_JOUR + 1
    mois, semaine_mois = mois_et_semaine(jour_annee)
    return pd.DataFrame({
        "h": h,
        "heure_utc": h % HEURES_PAR_JOUR,
        "ehlo": ehlo,
        "case": h_legale % HEURES_PAR_JOUR + 1,
        "jour_annee": jour_annee,
        "jour_semaine": (jour_annee - 1) % JOURS_PAR_SEMAINE + 1,
        "mois": mois,
        "semaine_mois": semaine_mois,
    })
