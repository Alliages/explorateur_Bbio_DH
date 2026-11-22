"""
============================================================
 VARIANTES — jusqu'à quatre calculs gardés, A à D (0.9.34)
============================================================
 Remplace la référence unique (« Garder comme référence ») :

   « Garder »    range le calcul affiché sous la première lettre
                 libre (A, puis B…) ; quatre au plus ;
   pastille      un clic remet sa saisie dans le menu, et son
                 calcul (en mémoire) s'affiche aussitôt ;
   référence     la première gardée, ou celle choisie dans
                 « Variantes » : les écarts se lisent face à elle ;
   retirer       dans « Variantes » ; la référence retirée passe
                 à la première qui reste.

 Une variante : {"lettre", "boite", "batiment", "niveau"} ; le
 bâtiment de départ et le niveau d'enveloppe donnent les champs
 non saisis (part habitable), pour retrouver la même boîte.
 Session : « variantes » (liste, par lettre) et « lettre_reference ».

 Les fonctions de la partie 1 n'utilisent pas Streamlit : elles
 se testent seules. afficher() met la bande en page.
============================================================
"""

from interface.briques.graphiques import nombre

# ============================================================
# RÉGLAGES
# ============================================================
LETTRES = "ABCD"                # au plus quatre variantes ; leur calcul reste en mémoire (app.CALCULS_GARDES)


# ============================================================
# 1. LA LISTE DES VARIANTES (sans Streamlit)
# ============================================================
def garder(variantes, boite, batiment, niveau):
    """Liste avec cette boîte gardée sous la première lettre libre ; inchangée si elle y est déjà ou si les quatre
    lettres sont prises. Rend (liste, lettre de la boîte ou None)."""
    deja = trouver(variantes, boite)
    if deja is not None:
        return variantes, deja
    libres = [lettre for lettre in LETTRES if lettre not in {v["lettre"] for v in variantes}]
    if not libres:
        return variantes, None
    nouvelle = {"lettre": libres[0], "boite": boite, "batiment": batiment, "niveau": niveau}
    return sorted(variantes + [nouvelle], key=lambda v: v["lettre"]), libres[0]


def retirer(variantes, lettre):
    """Liste sans la variante de cette lettre."""
    return [v for v in variantes if v["lettre"] != lettre]


def trouver(variantes, boite):
    """Lettre de la variante qui a cette boîte, ou None."""
    return next((v["lettre"] for v in variantes if v["boite"] == boite), None)


def variante(variantes, lettre):
    """La variante de cette lettre, ou None."""
    return next((v for v in variantes if v["lettre"] == lettre), None)


def reference(variantes, lettre_reference):
    """Lettre de la référence : celle choisie si elle est encore gardée, sinon la première ; None sans variante."""
    lettres = [v["lettre"] for v in variantes]
    if lettre_reference in lettres:
        return lettre_reference
    return lettres[0] if lettres else None


def libelle(v, chiffres, est_reference):
    """Texte d'une pastille : « A · 119,8 · 732 °C.h », avec un signet pour la référence.

    chiffres : {"bbio": …, "dh": …} des calculs lancés (les absents ne sont pas écrits).
    """
    morceaux = [v["lettre"]]
    if "bbio" in chiffres:
        morceaux.append(nombre(chiffres["bbio"], 1))
    if "dh" in chiffres:
        morceaux.append(nombre(chiffres["dh"], 0, "°C.h"))
    texte = " · ".join(morceaux)
    return f":material/bookmark: {texte}" if est_reference else texte


# ============================================================
# 2. LA BANDE (Streamlit)
# ============================================================
def afficher(variantes, lettre_ref, chiffres, active, remettre):
    """Pastilles des variantes et menu « Variantes » (référence, retirer). Streamlit n'est importé qu'ici.

    chiffres : lettre → {"bbio", "dh"} ; active : lettre de la variante dont la saisie est affichée, ou None ;
    remettre : fonction(variante) qui remet sa saisie et son calcul (rappel d'un clic sur une pastille).
    """
    import streamlit as st

    if not variantes:
        return
    lettres = [v["lettre"] for v in variantes]

    def _clic():
        lettre = st.session_state.get("pastilles")
        if lettre is not None:                              # un clic sur la pastille active la désélectionne
            remettre(variante(variantes, lettre))

    # La pastille active suit la saisie : posée avant le widget (pas de « default » : la session la donne)
    st.session_state["pastilles"] = active
    ligne = st.container(horizontal=True, vertical_alignment="center", gap="small")    # le menu juste après
    ligne.pills("Variantes gardées", lettres, key="pastilles", on_change=_clic, label_visibility="collapsed",
                format_func=lambda l: libelle(variante(variantes, l), chiffres.get(l, {}), l == lettre_ref))
    with ligne.popover("", icon=":material/tune:", help="Choisir la référence, retirer une variante"):
        st.session_state["choix_reference"] = lettre_ref    # suit la référence, même retirée entre-temps
        st.segmented_control("Référence", lettres, required=True, key="choix_reference",
                             on_change=lambda: st.session_state.update(
                                 lettre_reference=st.session_state["choix_reference"]))
        for lettre in lettres:
            st.button(f"Retirer {lettre}", icon=":material/delete:", key=f"retirer_{lettre}",
                      on_click=lambda l=lettre: st.session_state.update(
                          variantes=retirer(st.session_state["variantes"], l)))
