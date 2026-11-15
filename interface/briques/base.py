"""
============================================================
 BRIQUE — l'unité pédagogique de l'interface
============================================================
 Une brique explique UN phénomène, sur deux niveaux de lecture :

   niveau 1 (toujours visible)   le phénomène en une ou deux
                                 phrases, un schéma ou un
                                 graphique, des ordres de grandeur ;
   niveau 2 (dans un volet)      l'équation, sa référence dans les
                                 textes, et le code du moteur qui
                                 la calcule.

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

TITRE_VOLET = "Équation, référence et code"


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
    lecture     ce que désignent les symboles de l'équation
    reference   où la trouver dans les textes (annexe, fiche, équation)
    code        fonctions du moteur montrées dans le volet
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


def montrer(brique, resultats, boite):
    """Affiche une brique : niveau 1, puis le volet du niveau 2."""
    st.subheader(brique.titre)
    st.markdown(brique.phenomene)
    brique.afficher(resultats, boite)
    reperes = brique.reperes()
    if reperes:
        st.markdown("**Ordres de grandeur**\n" + "\n".join(f"- {repere}" for repere in reperes))
    with st.expander(TITRE_VOLET, icon=":material/functions:"):
        st.latex(brique.equation)
        st.markdown(brique.lecture)
        st.caption(f"Référence : {brique.reference}")
        for fonction in brique.code:
            st.caption(f"Code du moteur : `{fonction.__module__.replace('.', '/')}.py`, `{fonction.__name__}`")
            st.code(inspect.getsource(fonction), language="python")
