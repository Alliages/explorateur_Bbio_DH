r"""
============================================================
 VALIDER — l'outil face à toutes les études d'un dossier
============================================================
 Passe chaque RSET ou RSEE (XML) des dossiers donnés dans
 outils/comparer_reference.py et réunit, groupe par groupe :

     besoins (Bch, Bfr, Becl), Bbio et Bbio max : outil et étude,
     écart du Bbio en pour cent, dans la cible ou non ;
     avec --dh : DH de l'outil et de l'étude.

 Puis un résumé : nombre d'études et de groupes, écart médian,
 part des groupes dans la cible (± CIBLE_BBIO_PCT sur le Bbio).

 Les fichiers sans zone de logement collectif (bureaux : usage
 3 ; maison individuelle : usage 1) sont écartés et listés ; un
 fichier présent deux fois (même contenu) n'est compté qu'une
 fois.

 Usage (PowerShell) :
     python -m outils.valider
     python -m outils.valider "..\_RSEE" "_sources" --dh
     python -m outils.valider --sortie "_resultats\validation.csv"

 Les études restent hors du dépôt ; la table écrite aussi (dossier
 _resultats/, séparateur « ; », virgule décimale).
============================================================
"""

import argparse
import glob
import hashlib
import os
import sys
import time

import pandas as pd

from config.reglages import RACINE
from outils.comparer_reference import comparer, comparer_dh
from outils.lire_rset import lire_rset

# ============================================================
# RÉGLAGES
# ============================================================
DOSSIERS_PAR_DEFAUT = (os.path.join(RACINE, "..", "_RSEE"), os.path.join(RACINE, "_sources"))
SORTIE_PAR_DEFAUT = os.path.join(RACINE, "_resultats", "validation.csv")
CIBLE_BBIO_PCT = 10.0           # cible de la 0.9.8 : Bbio de l'outil à ± 10 % de celui de l'étude
GRANDEURS = ("b_ch", "b_fr", "b_ecl", "bbio", "bbio_max")


def lister_etudes(dossiers):
    """Fichiers XML des dossiers (sous-dossiers compris), sans doublon de contenu (même empreinte SHA-1) : liste
    des chemins."""
    vus, etudes = set(), []
    for dossier in dossiers:
        for chemin in sorted(glob.glob(os.path.join(dossier, "**", "*.xml"), recursive=True)):
            with open(chemin, "rb") as fichier:
                empreinte = hashlib.sha1(fichier.read()).hexdigest()
            if empreinte not in vus:
                vus.add(empreinte)
                etudes.append(chemin)
    return etudes


def nb_groupes_logement(chemin):
    """Nombre de groupes de logement collectif que l'outil lit dans un fichier (0 : fichier écarté)."""
    projet, _ = lire_rset(chemin)
    return sum(len(zone.groupes) for batiment in projet.batiments for zone in batiment.zones)


def valider_etude(chemin, avec_dh=False):
    """Une ligne par groupe d'une étude : grandeurs de l'outil et de l'étude, écarts."""
    c = comparer(chemin)
    groupes = c.annuel[c.annuel["niveau"] == "groupe"].copy()
    groupes.insert(0, "etude", os.path.basename(chemin))
    groupes.insert(1, "zone_climatique", c.reference.infos["zone_climatique"])
    groupes.insert(2, "logiciel", c.reference.infos.get("fichier_logiciel"))
    for grandeur in GRANDEURS:
        groupes[f"{grandeur}_ecart_pct"] = (groupes[f"{grandeur}_outil"] / groupes[f"{grandeur}_etude"] - 1.0) * 100.0
    groupes["dans_la_cible"] = groupes["bbio_ecart_pct"].abs() <= CIBLE_BBIO_PCT
    groupes["non_repris"] = "; ".join(f"{cle} : {n}" for cle, n in c.reference.infos["non_repris"].items())
    if avec_dh:
        dh = comparer_dh(c.projet, c.reference)[["batiment", "zone", "groupe", "dh_outil", "dh_etude", "dh_ecart_pct",
                                                "dh_max_outil"]]
        # Appariement par bâtiment, zone et groupe : un même nom de groupe peut revenir dans plusieurs zones
        groupes = groupes.merge(dh, on=["batiment", "zone", "groupe"], how="left")
    return groupes.drop(columns=["niveau"])


def resumer(table):
    """Résumé de la validation : études, groupes, écarts médians, part dans la cible."""
    return {"etudes": table["etude"].nunique(), "groupes": len(table),
            "dans_la_cible": int(table["dans_la_cible"].sum()),
            "ecart_bbio_median_pct": float(table["bbio_ecart_pct"].median()),
            "ecart_bch_median_pct": float(table["b_ch_ecart_pct"].median()),
            "rapport_bfr_median": float((table["b_fr_outil"] / table["b_fr_etude"]).median())}


def ecrire(table, chemin):
    """Table au format du projet : séparateur « ; », virgule décimale, UTF-8."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    table.to_csv(chemin, sep=";", decimal=",", index=False, encoding="utf-8", float_format="%.3f")


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description="Compare l'outil à toutes les études d'un ou plusieurs dossiers.")
    analyseur.add_argument("dossiers", nargs="*", default=DOSSIERS_PAR_DEFAUT, help="dossiers des RSET et RSEE")
    analyseur.add_argument("--dh", action="store_true", help="ajoute les degrés-heures (calcul Th-D, plus long)")
    analyseur.add_argument("--sortie", default=SORTIE_PAR_DEFAUT, help="table écrite (CSV)")
    options = analyseur.parse_args(arguments)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)

    tables, ecartees = [], []
    for chemin in lister_etudes(options.dossiers):
        nom = os.path.relpath(chemin)
        try:
            if nb_groupes_logement(chemin) == 0:
                ecartees.append(f"{nom} : aucune zone de logement collectif")
                continue
            debut = time.time()
            tables.append(valider_etude(chemin, options.dh))
            print(f"{nom} : {len(tables[-1])} groupes, {time.time() - debut:.0f} s", flush=True)
        except Exception as erreur:          # une étude illisible n'arrête pas les autres ; elle est listée
            ecartees.append(f"{nom} : {type(erreur).__name__} : {erreur}")
    print("\nÉcartées :")
    for ligne in ecartees:
        print(f"  - {ligne}")
    if not tables:
        print("Aucune étude de logement collectif.")
        return
    table = pd.concat(tables, ignore_index=True)
    colonnes = ["etude", "zone_climatique", "groupe", "sref_m2"] + [
        f"{g}_{s}" for g in GRANDEURS for s in ("outil", "etude")] + ["bbio_ecart_pct", "dans_la_cible"]
    if options.dh:
        colonnes += ["dh_outil", "dh_etude", "dh_ecart_pct"]
    print("\n" + table[colonnes].round(1).to_string(index=False))
    print("\nRésumé :", {cle: round(v, 1) if isinstance(v, float) else v for cle, v in resumer(table).items()})
    ecrire(table, options.sortie)
    print(f"Table écrite : {options.sortie}")


if __name__ == "__main__":
    main()
