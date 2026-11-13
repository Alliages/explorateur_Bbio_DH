"""
============================================================
 RÉGLAGES — chemins, formats et listes de l'outil
============================================================
 Ce fichier ne contient AUCUNE constante physique ou
 réglementaire : celles-ci sont dans donnees/hypotheses.csv,
 chacune avec sa source (annexe, fiche, équation).
============================================================
"""

import os

# ============================================================
# CHEMINS
# ============================================================
RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOSSIER_DONNEES = os.path.join(RACINE, "donnees")
DOSSIER_METEO = os.path.join(DOSSIER_DONNEES, "meteo")
DOSSIER_SCENARIOS = os.path.join(DOSSIER_DONNEES, "scenarios")
CHEMIN_HYPOTHESES = os.path.join(DOSSIER_DONNEES, "hypotheses.csv")
CHEMIN_VERSION = os.path.join(RACINE, "VERSION")

# Classeurs officiels : gardés en local, hors du dépôt (voir .gitignore)
DOSSIER_REFERENCES = os.path.join(RACINE, "_references")
CLASSEUR_METEO = os.path.join(DOSSIER_REFERENCES, "4_scenarios_meteorologiques_th-bc_th-d_re2020.xlsx")
CLASSEUR_SCENARIOS = os.path.join(DOSSIER_REFERENCES, "2026-04-29_scenarios_conventionnels.xlsx")

# ============================================================
# FORMAT DES CSV DU DÉPÔT
# ============================================================
SEPARATEUR_CSV = ";"
DECIMALE_CSV = ","
ENCODAGE_CSV = "utf-8"

# ============================================================
# MÉTÉO
# ============================================================
ZONES_CLIMATIQUES = ("H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3")
# jeu de données → suffixe de l'onglet du classeur officiel
JEUX_METEO = {"th_bc": "Th-BC",      # climat moyen : Bbio, besoins, consommations
              "th_d": "Th-D"}        # séquence caniculaire : confort d'été (DH)
# Colonnes des fichiers météo (noms du classeur officiel, sans les unités)
COLONNES_METEO = ("h", "te0", "we0", "dirN", "diff", "Teciel", "Vent", "Teau", "Gamma", "Psi")

# ============================================================
# CALENDRIER CONVENTIONNEL (annexe III, fiche 4.1)
# ============================================================
NB_HEURES_ANNEE = 8760
HEURES_PAR_JOUR = 24
JOURS_PAR_SEMAINE = 7
# Nombre de semaines de chaque mois (janvier → décembre) : 52 semaines, 364 jours
SEMAINES_PAR_MOIS = (4, 4, 5, 4, 5, 4, 4, 5, 4, 4, 5, 4)

# ============================================================
# USAGES ET SCÉNARIOS
# ============================================================
# usage → onglet du classeur des scénarios conventionnels
USAGES = {"logement_collectif": "LC"}
# Usages « habitation / hébergement » : seuil d'inconfort de nuit sans confort adaptatif (fiche 13.5, éq. 2544),
# brasseurs d'air bridés la nuit (fiche 8.32, § 8.32.3.3.3.2)
USAGES_HABITATION = ("logement_collectif",)
# Scénarios dont la semaine porte un état de consigne (1 normal, −1 réduit de plus de 48 h)
SCENARIOS_CONSIGNE = ("chauffage", "refroidissement")


def lire_version():
    """Numéro de version de l'outil (fichier VERSION à la racine)."""
    with open(CHEMIN_VERSION, encoding="utf-8") as f:
        return f.read().strip()
