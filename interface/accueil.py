"""
============================================================
 ACCUEIL — la page qui présente l'outil (comme Météo et Chaleur)
============================================================
 Texte dans interface/textes/accueil.md (Markdown, modifiable
 sans toucher au code). Le repère <!-- bouton_explorer --> y
 place le bouton qui ouvre la page « Explorer » ; l'adresse
 (GLOSSAIRE) y devient celle du glossaire Notion, et [[terme]]
 un lien vers la page du terme (interface/aides.py).
 L'accueil ne lance aucun calcul.
============================================================
"""

import streamlit as st

from interface import charte
from interface.aides import adresse_glossaire, lire_texte

# ============================================================
# RÉGLAGES
# ============================================================
FICHIER = "accueil.md"
REPERE_BOUTON = "<!-- bouton_explorer -->"
LIBELLE_BOUTON = "Explorer la boîte ›"
# Mise en forme du texte : titres sur fond coloré, notions encadrées (palette de interface/charte.py)
STYLE = f"""<style>
.st-key-accueil {{ max-width: 920px; margin: 0 auto; }}
.st-key-accueil p, .st-key-accueil li {{ font-size: 1.02rem; line-height: 1.6; }}
.st-key-accueil h1 {{ background: {charte.BLEU_NUIT}; color: white; border-radius: 12px; padding: 14px 20px;
                      font-size: 1.7rem; margin-bottom: 14px; }}
.st-key-accueil h2 {{ background: {charte.FOND_SCHEMA}; color: {charte.BLEU_NUIT}; border-radius: 10px;
                      padding: 7px 14px; font-size: 1.18rem; margin: 22px 0 8px; }}
.st-key-accueil h2.alerte {{ background: {charte.ORANGE}; color: white; }}
.st-key-accueil h2.liens {{ background: {charte.PRUNE}; color: white; }}
.st-key-accueil [data-testid="stHeaderActionElements"] {{ display: none; }}
.st-key-accueil blockquote {{ border-left: 5px solid {charte.JAUNE}; background: {charte.FOND_SCHEMA};
                              border-radius: 0 10px 10px 0; padding: 8px 16px; margin: 10px 0; opacity: 1; }}
.st-key-accueil blockquote p {{ margin: 0; color: {charte.NOIR}; }}    /* Streamlit grise les citations */
.st-key-accueil a {{ font-weight: 600; }}
</style>"""


def _texte():
    """Texte de l'accueil, coupé en deux autour du repère du bouton."""
    texte = lire_texte(FICHIER).replace("](GLOSSAIRE)", f"]({adresse_glossaire()})")
    avant, _, apres = texte.partition(REPERE_BOUTON)
    return avant, apres


def afficher(aller_explorer):
    """Page d'accueil : le texte, et le bouton qui ouvre la page « Explorer » (fonction aller_explorer)."""
    avant, apres = _texte()
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.container(key="accueil"):
        st.markdown(avant, unsafe_allow_html=True)
        st.button(LIBELLE_BOUTON, on_click=aller_explorer, type="primary", key="accueil_explorer",
                  icon=":material/deployed_code:")
        if apres.strip():
            st.markdown(apres, unsafe_allow_html=True)
