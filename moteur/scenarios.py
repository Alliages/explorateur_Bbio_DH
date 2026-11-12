"""
============================================================
 SCÉNARIOS CONVENTIONNELS — occupation, consignes, apports
============================================================
 Source : classeur « scénarios conventionnels » de la RE2020
 (version du 29/04/2026), extrait par outils/extraire_donnees.py
 vers donnees/scenarios/<usage>_{horaire,semaine,parametres}.csv.
 Méthode : annexe III, fiche 4.1 (C_EIN_Scénarios conventionnels).

 Un scénario est décrit par deux tableaux :
   - horaire  : 7 jours (lundi → dimanche) × 24 cases (heures
                légales de fin de pas, 1 à 24) ;
   - semaine  : 5 semaines × 12 mois (cases vides quand le mois
                n'a que 4 semaines).

 Déroulé sur l'année, heure par heure :
   - cas général : valeur = horaire × semaine
     (semaine à 0 = vacances : inoccupation, arrêt) ;
   - chauffage et refroidissement : l'état vaut 1 (consigne
     normale), 0 (réduit de moins de 48 h) ou −1 (réduit de
     plus de 48 h). Une semaine à −1 impose −1 à toutes ses
     heures ; sinon l'état est celui du tableau horaire.

 Scénarios du logement collectif :
   mobilite, occupation, chauffage, refroidissement,
   ventilation, eclairage, ecs,
   logements_taux_occupation, logements_apports_chaleur,
   logements_apports_humidite, circulation_taux_occupation,
   circulation_apports_chaleur, circulation_apports_humidite.
============================================================
"""

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.reglages import (DECIMALE_CSV, DOSSIER_SCENARIOS, ENCODAGE_CSV, SCENARIOS_CONSIGNE,
                             SEPARATEUR_CSV, USAGES)

# États de consigne du classeur
ETAT_NORMAL = 1
ETAT_REDUIT_COURT = 0       # réduit de moins de 48 h
ETAT_REDUIT_LONG = -1       # réduit de plus de 48 h


@dataclass
class Scenarios:
    """Scénarios conventionnels d'un usage."""
    usage: str
    horaire: dict          # nom → tableau (7 jours, 24 cases)
    semaine: dict          # nom → tableau (5 semaines, 12 mois), NaN si la semaine n'existe pas
    parametres: dict       # cle → valeur (consignes, apports nominaux…)

    @property
    def noms(self):
        return list(self.horaire)

    def derouler(self, nom, calendrier):
        """Valeur du scénario `nom` pour chacune des 8 760 heures du calendrier."""
        if nom not in self.horaire:
            raise KeyError(f"Scénario inconnu : « {nom} » (disponibles : {', '.join(self.noms)})")
        valeur_horaire = self.horaire[nom][calendrier["jour_semaine"].to_numpy() - 1,
                                          calendrier["case"].to_numpy() - 1]
        valeur_semaine = self.semaine[nom][calendrier["semaine_mois"].to_numpy() - 1,
                                           calendrier["mois"].to_numpy() - 1]
        if np.isnan(valeur_semaine).any():
            raise ValueError(f"Scénario « {nom} » : semaine absente du tableau hebdomadaire")
        if nom in SCENARIOS_CONSIGNE:
            return np.where(valeur_semaine == ETAT_REDUIT_LONG, ETAT_REDUIT_LONG, valeur_horaire)
        return valeur_horaire * valeur_semaine

    def consigne(self, nom, calendrier):
        """Température de consigne (°C) heure par heure, pour « chauffage » ou « refroidissement »."""
        if nom not in SCENARIOS_CONSIGNE:
            raise KeyError(f"« {nom} » n'est pas un scénario de consigne ({', '.join(SCENARIOS_CONSIGNE)})")
        etat = self.derouler(nom, calendrier)
        temperatures = {ETAT_NORMAL: self.parametres[f"consigne_{nom}_normal"],
                        ETAT_REDUIT_COURT: self.parametres[f"consigne_{nom}_reduit_moins_48h"],
                        ETAT_REDUIT_LONG: self.parametres[f"consigne_{nom}_reduit_plus_48h"]}
        consigne = np.full(len(etat), np.nan)
        for valeur_etat, temperature in temperatures.items():
            consigne[etat == valeur_etat] = temperature
        if np.isnan(consigne).any():
            raise ValueError(f"Scénario « {nom} » : état de consigne inattendu")
        return consigne


def _lire_tableaux(chemin, colonne_ligne):
    """Lit un CSV de tableaux empilés : {scenario: tableau numpy}, lignes dans l'ordre de `colonne_ligne`."""
    table = pd.read_csv(chemin, sep=SEPARATEUR_CSV, decimal=DECIMALE_CSV, encoding=ENCODAGE_CSV)
    tableaux = {}
    for nom, bloc in table.groupby("scenario", sort=False):
        bloc = bloc.sort_values(colonne_ligne)
        tableaux[nom] = bloc.drop(columns=["scenario", colonne_ligne]).to_numpy(dtype=float)
    return tableaux


def charger_scenarios(usage="logement_collectif"):
    """Scénarios conventionnels d'un usage, lus dans donnees/scenarios/ et contrôlés."""
    if usage not in USAGES:
        raise ValueError(f"Usage inconnu : « {usage} » (disponibles : {', '.join(USAGES)})")
    base = os.path.join(DOSSIER_SCENARIOS, usage)
    horaire = _lire_tableaux(f"{base}_horaire.csv", "jour")
    semaine = _lire_tableaux(f"{base}_semaine.csv", "semaine")
    parametres = pd.read_csv(f"{base}_parametres.csv", sep=SEPARATEUR_CSV, decimal=DECIMALE_CSV,
                             encoding=ENCODAGE_CSV)
    # Contrôles de forme : mêmes scénarios dans les deux fichiers, 7 × 24 et 5 × 12
    if list(horaire) != list(semaine):
        raise ValueError(f"Scénarios {usage} : tableaux horaires et hebdomadaires différents")
    for nom in horaire:
        if horaire[nom].shape != (7, 24) or semaine[nom].shape != (5, 12):
            raise ValueError(f"Scénario « {nom} » : dimensions inattendues")
    return Scenarios(usage=usage, horaire=horaire, semaine=semaine,
                     parametres=dict(zip(parametres["cle"], parametres["valeur"].astype(float))))
