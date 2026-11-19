"""
============================================================
 BRIQUE — l'unité pédagogique de l'interface
============================================================
 Une brique explique UN phénomène, sur deux niveaux de lecture :

   niveau 1 (toujours visible)   le phénomène en une ou deux
                                 phrases, un schéma ou un
                                 graphique, des ordres de grandeur,
                                 l'équation et ce qu'elle dit ;
   niveau 2 (dans un volet)      sa référence dans les textes, et
                                 le code du moteur qui la calcule.

 Les textes (phénomène, lecture de l'équation) peuvent citer le
 glossaire du confort : [[terme]] devient un lien vers sa page
 (interface/aides.py). Les termes de « glossaire » s'affichent
 en fin de brique, sous « Pour aller plus loin ».

 Écrire une brique : un fichier dans interface/briques/ qui
 définit BRIQUE = Brique(...), puis une ligne dans la liste
 BRIQUES de interface/briques/__init__.py. Rien d'autre à
 toucher : la page (app.py) parcourt la liste.

 Le code montré dans le volet est lu dans le moteur au moment de
 l'affichage (inspect.getsource) : il ne peut pas être périmé.
============================================================
"""

import inspect
from dataclasses import dataclass

import streamlit as st

from interface.aides import NOM_GLOSSAIRE, adresse_glossaire, lier

TITRE_VOLET = "Référence et code du moteur"


@dataclass(frozen=True)
class Brique:
    """Une brique pédagogique.

    cle         identifiant court, unique (clé des widgets de la brique)
    titre       nom affiché dans le choix des briques
    icone       icône Material Symbols (« :material/nom: »)
    phenomene   ce qui se passe, en une ou deux phrases, sans équation
    afficher    fonction afficher(resultats, boite) : schéma, chiffres et graphiques du niveau 1
    reperes     fonction sans argument rendant les ordres de grandeur (liste de phrases) ; une fonction, pour
                lire les valeurs dans donnees/hypotheses.csv au lieu de les recopier
    equation    équation principale, en LaTeX
    lecture     ce que désignent les symboles de l'équation et ce qu'elle dit
    reference   où la trouver dans les textes (annexe, fiche, équation)
    code        fonctions du moteur montrées dans le volet
    besoin      calcul dont la brique lit les résultats : « bbio » ou « dh » (interface/calcul.py) ; la page
                ne propose la brique que si ce calcul a été lancé
    glossaire   termes du glossaire du confort, pour aller plus loin (noms de interface/textes/glossaire.csv)
    """
    cle: str
    titre: str
    icone: str
    phenomene: str
    afficher: callable
    reperes: callable
    equation: str
    lecture: str
    reference: str
    code: tuple = ()
    besoin: str = ""
    glossaire: tuple = ()


def montrer(brique, resultats, boite):
    """Affiche une brique : niveau 1 (phénomène, graphiques, repères, équation), puis le volet du niveau 2."""
    st.subheader(brique.titre)
    st.markdown(lier(brique.phenomene))
    brique.afficher(resultats, boite)
    reperes = brique.reperes()
    if reperes:
        st.markdown("**Ordres de grandeur**\n" + "\n".join(f"- {repere}" for repere in reperes))
    # L'équation, montrée sans avoir à ouvrir le volet, avec ce qu'elle dit
    with st.container(border=True):
        st.markdown("**L'équation**")
        st.latex(brique.equation)
        st.markdown(lier(brique.lecture))
    if brique.glossaire:
        liens = " · ".join(lier(f"[[{terme}]]") for terme in brique.glossaire)
        st.markdown(f"**Pour aller plus loin**, dans le [{NOM_GLOSSAIRE}]({adresse_glossaire()}) : {liens}")
    with st.expander(TITRE_VOLET, icon=":material/functions:"):
        st.caption(f"Référence : {brique.reference}")
        for fonction in brique.code:
            st.caption(f"Code du moteur : `{fonction.__module__.replace('.', '/')}.py`, `{fonction.__name__}`")
            st.code(inspect.getsource(fonction), language="python")
