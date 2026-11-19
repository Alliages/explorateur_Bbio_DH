"""
============================================================
 AIDES — les textes de l'interface, tenus hors du code
============================================================
 Trois fichiers du dossier interface/textes/, modifiables sans
 toucher au code :

   aides.csv       l'aide de chaque saisie (la bulle « ? ») :
                   cle;aide, la clé étant celle du widget ;
   glossaire.csv   les termes du « Glossaire du confort dans le
                   bâtiment » (Notion) : terme;page ;
   accueil.md      le texte de la page d'accueil.

 Lien vers le glossaire : dans tout texte, [[terme]] devient un
 lien vers la page du terme, et [[terme|texte montré]] un lien
 sous un autre texte. Le terme s'écrit comme dans glossaire.csv
 (un test vérifie que chaque terme cité existe).

 Ce fichier ne dépend pas de Streamlit.
============================================================
"""

import csv
import os
import re
from functools import lru_cache

# ============================================================
# RÉGLAGES
# ============================================================
DOSSIER_TEXTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textes")
SITE_GLOSSAIRE = "https://guillaume-meunier.notion.site/"      # site public des pages Notion
PAGE_GLOSSAIRE = "2446562e29cd80a99195f07beeade7c3"             # la base « Glossaire du confort dans le bâtiment »
NOM_GLOSSAIRE = "Glossaire du confort dans le bâtiment"
LIEN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")          # [[terme]] ou [[terme|texte montré]]


def _lire_csv(nom):
    """Lignes d'un CSV du dossier des textes (séparateur « ; », UTF-8), en dictionnaires."""
    with open(os.path.join(DOSSIER_TEXTES, nom), encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier, delimiter=";"))


@lru_cache(maxsize=1)
def glossaire():
    """Terme → adresse de sa page dans le glossaire."""
    return {ligne["terme"]: SITE_GLOSSAIRE + ligne["page"] for ligne in _lire_csv("glossaire.csv")}


@lru_cache(maxsize=1)
def aides():
    """Clé du widget → texte de l'aide, tel qu'écrit (liens [[…]] non remplacés)."""
    return {ligne["cle"]: ligne["aide"] for ligne in _lire_csv("aides.csv")}


def adresse_glossaire():
    """Adresse de la base entière du glossaire."""
    return SITE_GLOSSAIRE + PAGE_GLOSSAIRE


def termes_cites(texte):
    """Termes du glossaire cités dans un texte par [[…]]."""
    return [terme.strip() for terme, _ in LIEN.findall(texte)]


def lier(texte):
    """Remplace chaque [[terme]] ou [[terme|texte montré]] par un lien Markdown vers sa page du glossaire.

    Un terme absent du glossaire reste en texte simple : la page s'affiche, le test signale l'oubli.
    """
    pages = glossaire()

    def lien(trouve):
        terme, montre = trouve.group(1).strip(), (trouve.group(2) or trouve.group(1)).strip()
        return f"[{montre}]({pages[terme]})" if terme in pages else montre

    return LIEN.sub(lien, texte)


def aide(cle):
    """Aide du widget de clé donnée, liens compris ; None s'il n'en a pas (Streamlit n'affiche alors rien)."""
    texte = aides().get(cle)
    return lier(texte) if texte else None


def lire_texte(nom):
    """Texte d'un fichier du dossier des textes (accueil.md…), liens du glossaire remplacés."""
    with open(os.path.join(DOSSIER_TEXTES, nom), encoding="utf-8") as fichier:
        return lier(fichier.read())
