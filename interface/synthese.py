"""
============================================================
 SYNTHÈSE — le Bbio et le DH côte à côte (0.9.34)
============================================================
 Affichée quand les deux calculs sont lancés, avant les briques
 (qui restent une à la fois). Le même geste (une saisie changée)
 fait bouger les deux indicateurs, souvent en sens contraires :
 la synthèse les montre ensemble, face à la référence.

   gauche   les trois besoins pondérés du Bbio, en une barre ;
            la référence dessous, en pâle ;
   droite   les degrés-heures de chaque jour de l'été ; la
            référence en trait noir ;
   dessous  une phrase : l'écart de chaque poste et du DH.

 Pas une brique : pas d'équation propre (celles du Bbio et du DH
 sont dans leurs briques).
============================================================
"""

import altair as alt
import pandas as pd

from interface import charte
from interface.briques.bbio import COULEURS, POSTES
from interface.briques.dh import par_jour
from interface.briques.graphiques import FORMAT_JOUR, HAUTEUR_BANDE, HAUTEUR_BARRE, echelle_couleurs, legende, nombre
from moteur.hypotheses import hyp

# ============================================================
# RÉGLAGES
# ============================================================
OPACITE_REFERENCE = 0.35        # la référence, en pâle sous le calcul affiché
HAUTEUR_REFERENCE = 60          # hauteur ajoutée par la barre de la référence (px)


# ============================================================
# 1. LES DONNÉES (sans Streamlit)
# ============================================================
def points_par_poste(resultats, nom):
    """Lignes (nom, poste, ordre, besoin, points) des trois besoins pondérés d'un calcul."""
    return [{"calcul": nom, "poste": poste, "ordre": rang, "besoin": resultats.bbio[colonne],
             "points": hyp(cle) * resultats.bbio[colonne]}
            for rang, (colonne, poste, cle) in enumerate(POSTES)]


def lecture(resultats, resultats_reference, lettre_reference):
    """Phrase des écarts face à la référence : chaque besoin en kWh/m², puis le DH ; None sans référence."""
    if resultats_reference is None:
        return None
    morceaux = []
    for colonne, poste, _ in POSTES:
        ecart = resultats.bbio[colonne] - resultats_reference.bbio[colonne]
        morceaux.append(f"{poste.lower()} {_signe(ecart, 1)}")
    ecart_dh = resultats.dh["dh"] - resultats_reference.dh["dh"]
    return (f"Face à {lettre_reference}, en kWh/m² : {', '.join(morceaux)} ; "
            f"DH {_signe(ecart_dh, 0)} °C.h.")


def _signe(ecart, decimales):
    """« + 0,5 », « − 2,2 », « ± 0 » (nul à l'arrondi)."""
    if round(ecart, decimales) == 0:
        return "± 0"
    return f"{'+' if ecart > 0 else '−'} {nombre(abs(ecart), decimales)}"


# ============================================================
# 2. LES GRAPHIQUES
# ============================================================
def _barres_bbio(resultats, resultats_reference, lettre_reference, nom_affiche):
    """Une barre par calcul (affiché, puis la référence en pâle), les trois postes bout à bout, et le Bbio max."""
    lignes = points_par_poste(resultats, nom_affiche)
    ordre = [nom_affiche]
    if resultats_reference is not None:
        nom_reference = f"Référence {lettre_reference}"
        lignes += points_par_poste(resultats_reference, nom_reference)
        ordre.append(nom_reference)
    table = pd.DataFrame(lignes)
    table["opacite"] = [1.0 if c == nom_affiche else OPACITE_REFERENCE for c in table["calcul"]]
    barres = alt.Chart(table).mark_bar(stroke="white", strokeWidth=2).encode(
        x=alt.X("points:Q", title="Points de Bbio", stack="zero"),
        y=alt.Y("calcul:N", sort=ordre, title=None),
        color=alt.Color("poste:N", scale=echelle_couleurs(COULEURS), legend=legende()),
        opacity=alt.Opacity("opacite:Q", legend=None, scale=None),
        order=alt.Order("ordre:Q"),
        tooltip=[alt.Tooltip("calcul:N", title="Calcul"), alt.Tooltip("poste:N", title="Poste"),
                 alt.Tooltip("besoin:Q", title="Besoin (kWh/m²)", format=".1f"),
                 alt.Tooltip("points:Q", title="Points", format=".1f")])
    trait = alt.Chart(pd.DataFrame({"points": [resultats.bbio["bbio_max"]]})).mark_rule(
        color=charte.COULEUR_LIMITE, strokeWidth=2, strokeDash=[5, 4]).encode(x="points:Q")
    return (barres + trait).properties(height=HAUTEUR_BARRE + HAUTEUR_REFERENCE * (len(ordre) - 1))


def _jours_dh(resultats, resultats_reference, lettre_reference):
    """Degrés-heures de chaque jour : barres orange du calcul affiché, trait noir en escalier de la référence."""
    jours = par_jour(resultats.ete)
    axe_x = alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR))
    barres = alt.Chart(jours).mark_bar(color=charte.COULEUR_INCONFORT).encode(
        x=axe_x, y=alt.Y("dh:Q", title="°C.h par jour"),
        tooltip=[alt.Tooltip("date:T", title="Jour", format=FORMAT_JOUR),
                 alt.Tooltip("dh:Q", title="DH du jour", format=".0f")])
    graphique = barres
    if resultats_reference is not None:
        reference = par_jour(resultats_reference.ete)
        graphique += alt.Chart(reference).mark_line(color=charte.COULEUR_LIMITE, strokeWidth=1.5,
                                                    interpolate="step").encode(
            x=axe_x, y="dh:Q",
            tooltip=[alt.Tooltip("date:T", title="Jour", format=FORMAT_JOUR),
                     alt.Tooltip("dh:Q", title=f"DH du jour, {lettre_reference}", format=".0f")])
    return graphique.properties(height=HAUTEUR_BANDE)


# ============================================================
# 3. MISE EN PAGE (Streamlit)
# ============================================================
def afficher(resultats, resultats_reference, lettre_reference, lettre_affichee=None):
    """La synthèse, si le Bbio et le DH sont calculés ; rien sinon. lettre_affichee : celle du calcul affiché, s'il
    est gardé en variante (nom de sa barre)."""
    import streamlit as st

    if resultats.bbio is None or resultats.dh is None:
        return
    st.subheader("Bbio et DH ensemble")
    gauche, droite = st.columns(2, gap="large")
    with gauche:
        st.markdown("**Bbio** : les trois besoins pondérés")
        st.altair_chart(_barres_bbio(resultats, resultats_reference, lettre_reference,
                                     lettre_affichee or "Calcul affiché"),
                        alt="Besoins pondérés du Bbio, calcul affiché et référence")
    with droite:
        st.markdown("**DH** : les degrés-heures de chaque jour")
        st.altair_chart(_jours_dh(resultats, resultats_reference, lettre_reference),
                        alt="Degrés-heures de chaque jour de l'été, calcul affiché et référence")
    phrase = lecture(resultats, resultats_reference, lettre_reference)
    st.caption(phrase or "Garder une variante pour lire ici l'écart de chaque besoin et du DH.")
