"""
Valeurs des 13 variables d'enveloppe (celles de donnees/typologies_logements.csv) pour quelques RSET,
une ligne par groupe, à partir de caracteristiques_rset.csv.

Usage : python -I valeurs_3_rset.py <csv_entree> <csv_sortie>

- Fichiers retenus : liste FICHIERS (par défaut, les 3 RSET « scénario 2 » à la racine de _sources).
- Inertie : classe Th-I, « personnalisée » convertie par Cmq et Amq (même règle que calcul_typologies_logements.py).
- Sortie : séparateur ;, virgule décimale, 3 décimales au plus, UTF-8 avec BOM (Excel FR).
"""
import os
import sys

import pandas as pd

# Fonctions et variables partagées avec le calcul des niveaux (même dossier ; -I n'ajoute pas ce dossier au chemin)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calcul_typologies_logements import VARIABLES, CLASSES_INERTIE, classe_inertie, en_nombre, fmt_nombre

# ---------------------------------------------------------------------------
# RÉGLAGES
# ---------------------------------------------------------------------------
# Valeurs de la colonne « fichier » de caracteristiques_rset.csv (chemins relatifs à la racine du dépôt)
FICHIERS = [os.path.join("_sources", f"{v}_scenario2_resultats_groupes_occ.xml") for v in ("nice", "paris", "sete")]
IDENTITE = ["fichier", "empreinte_entrees", "zone_climatique", "usage", "batiment", "zone", "groupe", "shab_m2"]
DECIMALES = 3


def main(chemin_entree, chemin_sortie):
    df = pd.read_csv(chemin_entree, sep=";", dtype=str, encoding="utf-8-sig")
    df = df[df["fichier"].isin(FICHIERS)].copy()
    absents = set(FICHIERS) - set(df["fichier"])
    if absents:
        print("ATTENTION : fichiers absents de", chemin_entree, ":", absents)

    # Conversion numérique, puis classe d'inertie (0..4 -> nom)
    for c in [c for c, *_ in VARIABLES] + ["shab_m2", "cmq_surf", "amq_surf"]:
        df[c] = en_nombre(df[c])
    df["classe_inertie"] = [CLASSES_INERTIE[int(i)] if pd.notna(i) else ""
                            for i in df.apply(classe_inertie, axis=1)]

    sortie = df[IDENTITE + [c for c, *_ in VARIABLES]
                + ["classe_inertie", "inertie_quotidienne", "cmq_surf", "amq_surf"]]
    sortie = sortie.rename(columns={"classe_inertie": "inertie_quotidienne_classe",
                                    "inertie_quotidienne": "inertie_quotidienne_saisie"})
    # Nombres écrits en texte : virgule décimale, sans zéros inutiles
    for c in sortie.columns:
        if pd.api.types.is_float_dtype(sortie[c]):
            sortie[c] = sortie[c].map(lambda x: "" if pd.isna(x) else fmt_nombre(round(x, DECIMALES)))
    sortie.to_csv(chemin_sortie, sep=";", index=False, encoding="utf-8-sig")
    print(f"{len(sortie)} groupes, {sortie['fichier'].nunique()} fichiers -> {chemin_sortie}")
    print(sortie.T.to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
