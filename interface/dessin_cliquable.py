"""
============================================================
 DESSIN CLIQUABLE — l'axonométrie affichée dans la page, qui
 renvoie la paroi cliquée
============================================================
 Petit composant Streamlit (st.components.v2, écrit ici en
 entier : HTML, CSS et JavaScript, sans outil de construction).

     SVG de interface/axonometrie.py, chaque mur, baie,
     protection et toiture portant sa clé (attribut data-cle)
                  │
                  ▼
     affiché tel quel dans la page (infobulles au survol, main
     et éclaircissement sur ce qui se clique)
                  │  clic sur une forme qui porte une clé
                  ▼
     événement « clic » (setTriggerValue) : sa valeur est la clé
     de la paroi ; app.py la recopie dans la liste « Paroi
     examinée », qui reste le moyen de choisir au clavier et de
     choisir une paroi cachée dans la vue (façade de dos,
     plancher bas) ; un quart de la boussole porte la clé
     « vue:<nom> » : app.py change alors de vue (vue_choisie)

 Le dessin ne passe plus par st.markdown(unsafe_allow_html=True)
 (0.9.18) : le composant écrit le SVG lui-même, sans filtre, et
 le JavaScript reçoit les clics.

 Seul fichier de l'interface à contenir du JavaScript.
============================================================
"""

import streamlit as st

from interface.axonometrie import PREFIXE_VUE, VUES

# ============================================================
# RÉGLAGES
# ============================================================
NOM_COMPOSANT = "explorateur_bbio_dh.dessin_cliquable"
ECLAIRCISSEMENT_SURVOL = 1.12       # luminosité d'une forme cliquable sous la souris (1 = inchangée)

# ============================================================
# LE COMPOSANT (HTML, CSS, JavaScript)
# ============================================================
_HTML = """
<div class="dessin" role="group"></div>
"""

_CSS = f"""
.dessin svg {{
  display: block;
  width: 100%;
  height: auto;
}}
.dessin [data-cle] {{
  cursor: pointer;
}}
.dessin [data-cle]:hover {{
  filter: brightness({ECLAIRCISSEMENT_SURVOL});
}}
"""

# Le JavaScript est relancé à chaque passage de la page : il ne réécrit le SVG que s'il a changé (WeakMap, une
# entrée par instance), et remplace le gestionnaire de clic au lieu d'en empiler un de plus.
_JS = """
const dernierSvg = new WeakMap()

export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const cadre = parentElement.querySelector(".dessin")
  if (!cadre || !data) return

  if (dernierSvg.get(cadre) !== data.svg) {
    cadre.innerHTML = data.svg
    dernierSvg.set(cadre, data.svg)
  }
  cadre.setAttribute("aria-label", data.description || "")

  // Clic : la forme cliquée, ou celle qui la contient, porte la clé de sa paroi
  cadre.onclick = (evenement) => {
    const forme = evenement.target.closest("[data-cle]")
    if (forme) setTriggerValue("clic", forme.getAttribute("data-cle"))
  }
}
"""

_DESSIN = st.components.v2.component(NOM_COMPOSANT, html=_HTML, css=_CSS, js=_JS)


# ============================================================
# APPEL DEPUIS LA PAGE
# ============================================================
def dessin_cliquable(svg, description, *, key, on_clic):
    """Affiche le SVG ; on_clic (sans argument) est appelé au clic sur une paroi, avant le reste du passage de la
    page : la clé cliquée est alors dans st.session_state[key].clic (voir paroi_cliquee)."""
    return _DESSIN(data={"svg": svg, "description": description}, key=key, on_clic_change=on_clic)


def _cle_cliquee(etat):
    """Clé de la forme cliquée, lue dans l'état du composant (st.session_state[key]) ; None sans clic."""
    cle = getattr(etat, "clic", None) if etat is not None else None
    if cle is None and isinstance(etat, dict):
        cle = etat.get("clic")
    return cle


def paroi_cliquee(etat, choix):
    """Clé de la paroi cliquée, si elle est dans la liste des parois que l'on peut examiner (choix) ; None sinon."""
    cle = _cle_cliquee(etat)
    return cle if cle in choix else None


def vue_choisie(etat):
    """Vue choisie d'un clic sur un quart de la boussole (clé « vue:sud-ouest » → « sud-ouest ») ; None sinon."""
    cle = _cle_cliquee(etat)
    if isinstance(cle, str) and cle.startswith(PREFIXE_VUE) and cle[len(PREFIXE_VUE):] in VUES:
        return cle[len(PREFIXE_VUE):]
    return None
