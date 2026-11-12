"""
============================================================
 MÉTÉO — fichiers conventionnels et correction d'altitude
============================================================
 Source des données : classeur officiel « scénarios
 météorologiques Th-BC / Th-D » (DHUP, données Météo-France
 2000-2018), extrait par outils/extraire_donnees.py vers
 donnees/meteo/meteo_<zone>_<jeu>.csv.

 Deux jeux par zone climatique (8 zones) :
   th_bc  climat moyen, pour le Bbio ;
   th_d   année à séquence caniculaire, pour le confort d'été.

 Colonnes (une ligne par heure, 0 à 8 759, en UTC) :
   h       heure de l'année
   te0     température extérieure à l'altitude 0 (°C)
   we0     humidité spécifique à l'altitude 0 (g/kg d'air sec)
   dirN    rayonnement direct normal (W/m²)
   diff    rayonnement diffus horizontal (W/m²)
   Teciel  température du ciel (°C)
   Vent    vitesse du vent (m/s)
   Teau    température d'eau froide à l'altitude 0 (°C)
   Gamma   hauteur du soleil (°)
   Psi     azimut du soleil (°)

 Correction d'altitude — annexe III, fiche 3.1 (C_Clim) :
   Te   = Te0   − 0,005  × altcorr
   we   = (we0  − 0,0025 × altcorr) / 1000      (kg/kg)
   Teau = Teau0 − 0,005  × altcorr
   altcorr = 100 m si altitude ≤ 400 m ; 500 m si ≤ 800 m ;
             900 m au-delà.
 Remarque : la correction s'applique même au niveau de la mer
 (altcorr = 100 m, soit −0,5 °C).
============================================================
"""

import os

import pandas as pd

from config.reglages import (COLONNES_METEO, DECIMALE_CSV, DOSSIER_METEO, ENCODAGE_CSV, JEUX_METEO,
                             NB_HEURES_ANNEE, SEPARATEUR_CSV, ZONES_CLIMATIQUES)
from moteur.hypotheses import hyp


def chemin_meteo(zone, jeu):
    """Chemin du fichier météo d'une zone climatique et d'un jeu (th_bc ou th_d)."""
    if zone not in ZONES_CLIMATIQUES:
        raise ValueError(f"Zone climatique inconnue : « {zone} » (attendu : {', '.join(ZONES_CLIMATIQUES)})")
    if jeu not in JEUX_METEO:
        raise ValueError(f"Jeu météo inconnu : « {jeu} » (attendu : {', '.join(JEUX_METEO)})")
    return os.path.join(DOSSIER_METEO, f"meteo_{zone}_{jeu}.csv")


def lire_meteo(zone, jeu):
    """Fichier météo brut (altitude 0), contrôlé : colonnes attendues, 8 760 heures, aucune valeur vide."""
    meteo = pd.read_csv(chemin_meteo(zone, jeu), sep=SEPARATEUR_CSV, decimal=DECIMALE_CSV, encoding=ENCODAGE_CSV)
    if tuple(meteo.columns) != COLONNES_METEO:
        raise ValueError(f"Météo {zone} {jeu} : colonnes inattendues {list(meteo.columns)}")
    if list(meteo["h"]) != list(range(NB_HEURES_ANNEE)):
        raise ValueError(f"Météo {zone} {jeu} : {len(meteo)} lignes, {NB_HEURES_ANNEE} heures attendues dans l'ordre")
    if meteo.isna().any().any():
        raise ValueError(f"Météo {zone} {jeu} : valeurs manquantes")
    return meteo


def altitude_corrigee(altitude):
    """altcorr (m) : altitude conventionnelle retenue pour la correction (100, 500 ou 900 m)."""
    if altitude <= hyp("altitude_seuil_bas"):
        return hyp("altitude_corrigee_basse")
    if altitude <= hyp("altitude_seuil_haut"):
        return hyp("altitude_corrigee_moyenne")
    return hyp("altitude_corrigee_haute")


def corriger_altitude(meteo, altitude):
    """Ajoute les colonnes corrigées de l'altitude : te (°C), we (kg/kg) et teau (°C)."""
    altcorr = altitude_corrigee(altitude)
    meteo = meteo.copy()
    meteo["te"] = meteo["te0"] - hyp("gradient_te") * altcorr
    meteo["we"] = (meteo["we0"] - hyp("gradient_we") * altcorr) / 1000.0
    meteo["teau"] = meteo["Teau"] - hyp("gradient_teau") * altcorr
    return meteo


def charger_meteo(zone, jeu, altitude=0.0):
    """Météo d'un projet : fichier de la zone et du jeu, corrigé de l'altitude du site."""
    return corriger_altitude(lire_meteo(zone, jeu), altitude)
