"""
============================================================
 COMPARAISON — une variante face à une boîte de référence
============================================================
 L'outil sert à comprendre ce qui fait bouger le Bbio et le DH :
 on garde un calcul comme référence, on change une saisie, et on
 lit l'écart.

     référence (boîte gardée)  ─┐
                                ├─→  ce qui a changé dans la saisie
     variante (boîte calculée) ─┘    et l'écart sur chaque indicateur

 Deux fonctions, sans Streamlit (elles se testent seules) :
   differences(reference, variante)   les saisies qui diffèrent ;
   ecarts(resultats_ref, resultats)   les indicateurs côte à côte.
 afficher() les met en page.

 Ajouter une saisie à Boite : lui donner un libellé dans LIBELLES
 (un test le vérifie).
============================================================
"""

from dataclasses import fields

from interface.briques.graphiques import nombre
from interface.saisie import FACADES, point_cardinal

# ============================================================
# RÉGLAGES
# ============================================================
# Libellé de chaque champ de Boite : (nom affiché, unité, décimales) ; décimales None : texte ou oui / non
LIBELLES = {
    "zone_climatique": ("Zone climatique", "", None),
    "altitude_m": ("Altitude", "m", 0),
    "exposition_bruit": ("Exposition au bruit", "", None),
    "longueur_m": ("Longueur", "m", 0),
    "profondeur_m": ("Profondeur", "m", 0),
    "nb_niveaux": ("Niveaux", "", 0),
    "hauteur_etage_m": ("Hauteur d'étage", "m", 2),
    "hauteur_sous_plafond_m": ("Hauteur sous plafond", "m", 2),
    "orientation_deg": ("Orientation de la façade principale", "", None),
    "part_habitable": ("Part habitable", "%", 0),
    "nb_logements": ("Logements", "", 0),
    "traversant": ("Logements traversants", "", None),
    "part_vitree_principale": ("Part vitrée, façade principale", "%", 0),
    "part_vitree_pignon_a": ("Part vitrée, pignon A", "%", 0),
    "part_vitree_arriere": ("Part vitrée, façade arrière", "%", 0),
    "part_vitree_pignon_b": ("Part vitrée, pignon B", "%", 0),
    "uw": ("Uw des baies", "W/m².K", 2),          # deux décimales : les niveaux d'enveloppe ont 1,35 et 1,45
    "sw": ("Facteur solaire Sw", "", 2),
    "tl": ("Transmission lumineuse", "", 2),
    "protection": ("Protection mobile", "", None),
    "gestion_protection": ("Gestion de la protection", "", None),
    "uw_protege": ("Uw, protection baissée", "W/m².K", 2),
    "sw_protege": ("Facteur solaire, protection baissée", "", 2),
    "ouvrable": ("Baies ouvrables", "", None),
    "ratio_ouverture_max": ("Part ouvrante de la baie", "%", 0),
    "debord_m": ("Balcons ou casquettes", "m", 1),
    "facades_debord": ("Façades à balcons", "", None),
    "u_mur": ("U des murs", "W/m².K", 2),
    "u_toiture": ("U de la toiture", "W/m².K", 2),
    "u_plancher": ("U du plancher bas", "W/m².K", 2),
    "plancher_sur_sol": ("Plancher bas sur le sol", "", None),
    "teinte": ("Teinte des parois", "", None),
    "psi_planchers": ("Ponts thermiques des planchers", "W/m.K", 2),
    "inertie": ("Inertie", "", None),
    "debit_ventilation_m3h_m2": ("Ventilation", "m³/h.m²", 1),
    "permeabilite_q4pa": ("Perméabilité à l'air", "m³/h.m²", 1),
    "climatise": ("Logements climatisés", "", None),
    "brasseurs": ("Brasseurs d'air", "", None),
    "brasseurs_par_logement": ("Brasseurs par logement", "", 0),
    "brasseur_debit_m3h": ("Débit d'un brasseur", "m³/h", 0),
    "brasseur_puissance_w": ("Puissance d'un brasseur", "W", 0),
}
# Champs sans effet tant qu'une option est éteinte : champ → (option, valeur de l'option qui l'éteint)
SANS_EFFET = {"gestion_protection": ("protection", "aucune"), "uw_protege": ("protection", "aucune"),
              "sw_protege": ("protection", "aucune"), "ratio_ouverture_max": ("ouvrable", False),
              "facades_debord": ("debord_m", 0.0), "brasseurs_par_logement": ("brasseurs", False),
              "brasseur_debit_m3h": ("brasseurs", False), "brasseur_puissance_w": ("brasseurs", False)}
# Indicateurs comparés : (nom, table des résultats, clé, unité, décimales)
INDICATEURS = (("Bbio", "bbio", "bbio", "points", 1),
               ("Chauffage", "bbio", "b_ch", "kWh/m²", 1),
               ("Refroidissement", "bbio", "b_fr", "kWh/m²", 1),
               ("Éclairage", "bbio", "b_ecl", "kWh/m²", 1),
               ("DH", "dh", "dh", "°C.h", 0),
               ("Heures d'inconfort", "dh", "nb_h_inconfort", "h", 0),
               ("Température la plus haute", "dh", "theta_op_max", "°C", 1))
NOMS_FACADES = {cle: libelle.lower() for cle, libelle, _, _ in FACADES}


# ============================================================
# 1. CE QUI A CHANGÉ DANS LA SAISIE
# ============================================================
def _ecrire(champ, valeur):
    """Valeur d'un champ de Boite, écrite pour être lue (unité, virgule décimale, oui / non)."""
    _, unite, decimales = LIBELLES[champ]
    if champ == "orientation_deg":
        return point_cardinal(valeur)
    if champ == "facades_debord":
        return ", ".join(NOMS_FACADES[cle] for cle in valeur) or "aucune"
    if isinstance(valeur, bool):
        return "oui" if valeur else "non"
    if decimales is None:
        return str(valeur).replace("_", " ")
    if unite == "%":
        return nombre(valeur * 100.0, decimales, "%")
    return nombre(valeur, decimales, unite)


def _eteint(boite, champ):
    """Vrai si le champ n'a aucun effet sur cette boîte (son option est éteinte)."""
    if champ not in SANS_EFFET:
        return False
    option, valeur_eteinte = SANS_EFFET[champ]
    return getattr(boite, option) == valeur_eteinte


def differences(reference, variante):
    """Saisies qui diffèrent : liste de (libellé, valeur de la référence, valeur de la variante), en clair.

    Un champ sans effet des deux côtés (réglage d'une protection absente, par exemple) n'est pas listé.
    """
    lignes = []
    for champ in fields(reference):
        avant, apres = getattr(reference, champ.name), getattr(variante, champ.name)
        if avant == apres or (_eteint(reference, champ.name) and _eteint(variante, champ.name)):
            continue
        lignes.append((LIBELLES[champ.name][0], _ecrire(champ.name, avant), _ecrire(champ.name, apres)))
    return lignes


# ============================================================
# 2. L'ÉCART SUR LES INDICATEURS
# ============================================================
def ecarts(resultats_reference, resultats):
    """Indicateurs côte à côte : liste de dictionnaires indicateur, unite, decimales, reference, variante,
    ecart (variante − référence) et ecart_pct (None si la référence est nulle).

    Seuls figurent les indicateurs des calculs lancés des deux côtés (Bbio, DH ou les deux).
    """
    lignes = []
    for nom, table, cle, unite, decimales in INDICATEURS:
        if getattr(resultats_reference, table) is None or getattr(resultats, table) is None:
            continue
        avant, apres = getattr(resultats_reference, table)[cle], getattr(resultats, table)[cle]
        lignes.append({"indicateur": nom, "unite": unite, "decimales": decimales, "reference": avant,
                       "variante": apres, "ecart": apres - avant,
                       "ecart_pct": (apres / avant - 1.0) * 100.0 if avant else None})
    return lignes


# ============================================================
# 3. MISE EN PAGE (Streamlit)
# ============================================================
def afficher(reference, resultats_reference, variante, resultats):
    """Tableau des indicateurs et liste des saisies changées. Streamlit n'est importé qu'ici."""
    import pandas as pd
    import streamlit as st

    colonne_indicateurs, colonne_saisies = st.columns([3, 2], gap="large")
    with colonne_indicateurs:
        lignes = []
        for e in ecarts(resultats_reference, resultats):
            signe = "+" if e["ecart"] > 0 else "−" if e["ecart"] < 0 else ""
            ecart = f"{signe}{nombre(abs(e['ecart']), e['decimales'])}"
            if e["ecart_pct"] is not None:
                ecart += f" ({signe}{nombre(abs(e['ecart_pct']), 0)} %)"
            lignes.append({"Indicateur": f"{e['indicateur']} ({e['unite']})",
                           "Référence": nombre(e["reference"], e["decimales"]),
                           "Variante": nombre(e["variante"], e["decimales"]), "Écart": ecart})
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")
    with colonne_saisies:
        changements = differences(reference, variante)
        st.markdown("**Ce qui a changé**\n" + "\n".join(f"- {libelle} : {avant} → **{apres}**"
                                                       for libelle, avant, apres in changements))
        if len(changements) > 1:
            st.caption("Plusieurs saisies ont changé : pour savoir laquelle agit, n'en changer qu'une à la fois.")
