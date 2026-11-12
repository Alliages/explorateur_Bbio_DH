"""
============================================================
 EXTRACTION DES DONNÉES — des classeurs officiels aux CSV
============================================================
 Régénère donnees/meteo/ et donnees/scenarios/ à partir des
 deux classeurs officiels, à placer dans _references/ (dossier
 local, hors du dépôt) :
   - 4_scenarios_meteorologiques_th-bc_th-d_re2020.xlsx
   - 2026-04-29_scenarios_conventionnels.xlsx

 Usage (PowerShell, depuis la racine du dépôt) :
     python -m outils.extraire_donnees

 Dépendance : openpyxl (outil seulement, pas le moteur).
 Format des CSV : séparateur « ; », virgule décimale, UTF-8.
============================================================
"""

import csv
import os

import openpyxl

from config.reglages import (CLASSEUR_METEO, CLASSEUR_SCENARIOS, COLONNES_METEO, DECIMALE_CSV, DOSSIER_METEO,
                             DOSSIER_SCENARIOS, ENCODAGE_CSV, JEUX_METEO, NB_HEURES_ANNEE, SEPARATEUR_CSV,
                             USAGES, ZONES_CLIMATIQUES)

# ============================================================
# PARAMÈTRES
# ============================================================
CHIFFRES_SIGNIFICATIFS = 12            # écriture des nombres (les valeurs du classeur en ont moins)

# --- Classeur des scénarios : repères de lecture --------------
ENTETE_HORAIRE = "jour V / heure >"    # ligne d'en-tête d'un tableau 7 jours × 24 heures
ENTETE_SEMAINE = "semaine V / mois >"  # ligne d'en-tête d'un tableau 5 semaines × 12 mois
COLONNE_REPERE = 1                     # colonne (comptée de 0) des en-têtes et des numéros de ligne
NB_JOURS, NB_CASES = 7, 24
NB_SEMAINES, NB_MOIS = 5, 12

# Nom donné à chaque tableau, dans l'ordre du classeur (onglet LC)
SCENARIOS_PAR_USAGE = {
    "logement_collectif": (
        "mobilite", "occupation", "chauffage", "refroidissement", "ventilation", "eclairage", "ecs",
        "logements_taux_occupation", "logements_apports_chaleur", "logements_apports_humidite",
        "circulation_taux_occupation", "circulation_apports_chaleur", "circulation_apports_humidite"),
}

# Valeurs isolées : cle → (ligne comptée de 1, colonne comptée de 0, unité)
PARAMETRES_PAR_USAGE = {
    "logement_collectif": {
        "consigne_chauffage_normal": (7, 3, "°C"),
        "consigne_chauffage_reduit_moins_48h": (8, 3, "°C"),
        "consigne_chauffage_reduit_plus_48h": (9, 3, "°C"),
        "consigne_refroidissement_normal": (7, 4, "°C"),
        "consigne_refroidissement_reduit_moins_48h": (8, 4, "°C"),
        "consigne_refroidissement_reduit_plus_48h": (9, 4, "°C"),
        "logements_ratio_surface": (144, 2, "-"),
        "logements_chaleur_occupant": (149, 2, "W/Nadeq"),
        "logements_humidite_occupant": (150, 2, "kg/h/Nadeq"),
        "logements_apports_chaleur": (173, 2, "W/m²"),
        "logements_apports_humidite": (196, 2, "kg/h/m²"),
        "circulation_ratio_surface": (220, 2, "-"),
        "circulation_occupants": (224, 2, "Nadeq"),
        "circulation_chaleur_occupant": (225, 2, "W/Nadeq"),
        "circulation_humidite_occupant": (226, 2, "kg/h/Nadeq"),
        "circulation_apports_chaleur": (249, 2, "W/m²"),
        "circulation_apports_humidite": (272, 2, "kg/h/m²"),
    },
}


def fr(x):
    """Nombre au format du dépôt (virgule décimale) ; cellule vide si None."""
    if x is None:
        return ""
    return f"{float(x):.{CHIFFRES_SIGNIFICATIFS}g}".replace(".", DECIMALE_CSV)


def ecrire_csv(chemin, entete, lignes):
    """Écrit un CSV au format du dépôt."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding=ENCODAGE_CSV, newline="") as f:
        sortie = csv.writer(f, delimiter=SEPARATEUR_CSV, lineterminator="\n")
        sortie.writerow(entete)
        sortie.writerows(lignes)


# ============================================================
# MÉTÉO : 16 onglets « <zone>_<jeu> » → 16 CSV
# ============================================================

def extraire_meteo():
    """Un CSV par zone climatique et par jeu, avec toutes les colonnes du classeur."""
    classeur = openpyxl.load_workbook(CLASSEUR_METEO, read_only=True, data_only=True)
    for zone in ZONES_CLIMATIQUES:
        for jeu, suffixe in JEUX_METEO.items():
            lignes = [l[:len(COLONNES_METEO)] for l in classeur[f"{zone}_{suffixe}"].iter_rows(min_row=2, values_only=True)
                      if l[0] is not None]
            # Contrôle : 8 760 heures dans l'ordre, aucune cellule vide
            if [int(l[0]) for l in lignes] != list(range(NB_HEURES_ANNEE)):
                raise SystemExit(f"{zone}_{suffixe} : heures inattendues ({len(lignes)} lignes)")
            if any(v is None for l in lignes for v in l):
                raise SystemExit(f"{zone}_{suffixe} : cellule vide")
            ecrire_csv(os.path.join(DOSSIER_METEO, f"meteo_{zone}_{jeu}.csv"), COLONNES_METEO,
                       [[int(l[0]), *(fr(v) for v in l[1:])] for l in lignes])
            print(f"météo {zone} {jeu} : {len(lignes)} heures")


# ============================================================
# SCÉNARIOS : un onglet par usage → 3 CSV
# ============================================================

def _tableau(lignes, debut, nb_lignes, nb_colonnes):
    """Tableau placé sous une ligne d'en-tête : numéros de ligne contrôlés, valeurs à droite du repère."""
    tableau = []
    for rang in range(1, nb_lignes + 1):
        ligne = lignes[debut + rang]
        if ligne[COLONNE_REPERE] != rang:
            raise SystemExit(f"Ligne {debut + rang + 1} : numéro {rang} attendu, « {ligne[COLONNE_REPERE]} » lu")
        tableau.append(list(ligne[COLONNE_REPERE + 1:COLONNE_REPERE + 1 + nb_colonnes]))
    return tableau


def extraire_scenarios(usage):
    """Tableaux horaires, tableaux hebdomadaires et paramètres d'un usage."""
    classeur = openpyxl.load_workbook(CLASSEUR_SCENARIOS, read_only=True, data_only=True)
    lignes = [list(l) for l in classeur[USAGES[usage]].iter_rows(values_only=True)]
    noms = SCENARIOS_PAR_USAGE[usage]

    # Les tableaux se suivent dans le classeur : horaire puis hebdomadaire, pour chaque scénario
    debuts_horaire = [i for i, l in enumerate(lignes) if l[COLONNE_REPERE] == ENTETE_HORAIRE]
    debuts_semaine = [i for i, l in enumerate(lignes) if l[COLONNE_REPERE] == ENTETE_SEMAINE]
    if not len(debuts_horaire) == len(debuts_semaine) == len(noms):
        raise SystemExit(f"{usage} : {len(debuts_horaire)} tableaux horaires et {len(debuts_semaine)} hebdomadaires "
                         f"trouvés, {len(noms)} attendus")

    horaire, semaine = [], []
    for nom, debut_h, debut_s in zip(noms, debuts_horaire, debuts_semaine):
        if debut_s < debut_h:
            raise SystemExit(f"{usage} / {nom} : ordre des tableaux inattendu")
        for jour, valeurs in enumerate(_tableau(lignes, debut_h, NB_JOURS, NB_CASES), 1):
            if any(v is None for v in valeurs):
                raise SystemExit(f"{usage} / {nom} : cellule vide dans le tableau horaire")
            horaire.append([nom, jour, *(fr(v) for v in valeurs)])
        for rang, valeurs in enumerate(_tableau(lignes, debut_s, NB_SEMAINES, NB_MOIS), 1):
            semaine.append([nom, rang, *(fr(v) for v in valeurs)])

    parametres = []
    for cle, (ligne, colonne, unite) in PARAMETRES_PAR_USAGE[usage].items():
        valeur = lignes[ligne - 1][colonne]
        if not isinstance(valeur, (int, float)):
            raise SystemExit(f"{usage} / {cle} : nombre attendu ligne {ligne}, « {valeur} » lu")
        parametres.append([cle, fr(valeur), unite])

    base = os.path.join(DOSSIER_SCENARIOS, usage)
    ecrire_csv(f"{base}_horaire.csv", ["scenario", "jour", *range(1, NB_CASES + 1)], horaire)
    ecrire_csv(f"{base}_semaine.csv", ["scenario", "semaine", *range(1, NB_MOIS + 1)], semaine)
    ecrire_csv(f"{base}_parametres.csv", ["cle", "valeur", "unite"], parametres)
    print(f"scénarios {usage} : {len(noms)} scénarios, {len(parametres)} paramètres")


def main():
    extraire_meteo()
    for usage in USAGES:
        extraire_scenarios(usage)


if __name__ == "__main__":
    main()
