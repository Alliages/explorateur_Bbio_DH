"""
============================================================
 BRIQUE « Bbio » — les trois besoins et leur poids
============================================================
 Niveau 1 : le Bbio face à son maximum, la part de chacun des
 trois besoins une fois pondérés, et leur répartition dans
 l'année (le chauffage en hiver, le froid en été, l'éclairage
 toute l'année).
 Niveau 2 : éq. 2385 de la fiche 13.1, moteur/bbio.py.
============================================================
"""

import altair as alt
import pandas as pd
import streamlit as st

from interface import charte
from interface.briques.base import Brique
from interface.briques.graphiques import HAUTEUR, HAUTEUR_BARRE, MOIS, echelle_couleurs, legende, nombre
from moteur.bbio import bbio_max, points_bbio
from moteur.hypotheses import hyp

# Les trois postes : (colonne du moteur, nom affiché, clé du coefficient dans donnees/hypotheses.csv)
POSTES = (("b_ch", "Chauffage", "bbio_coef_chauffage"),
          ("b_fr", "Refroidissement", "bbio_coef_refroidissement"),
          ("b_ecl", "Éclairage", "bbio_coef_eclairage"))
COULEURS = {"Chauffage": charte.COULEUR_CHAUFFAGE, "Refroidissement": charte.COULEUR_FROID,
            "Éclairage": charte.COULEUR_ECLAIRAGE}


def _points_par_poste(besoins):
    """Table poste, besoin (kWh/m²), coefficient et points, à partir d'une ligne ou d'un mois de besoins."""
    lignes = [{"poste": nom, "ordre": rang, "besoin": besoins[colonne], "coefficient": hyp(cle),
               "points": hyp(cle) * besoins[colonne]}
              for rang, (colonne, nom, cle) in enumerate(POSTES)]
    return pd.DataFrame(lignes)


def _barre_annuelle(r):
    """Une barre : les trois besoins pondérés bout à bout, et le trait du Bbio max."""
    table = _points_par_poste(r.bbio)
    barre = alt.Chart(table).mark_bar(size=46, stroke="white", strokeWidth=2).encode(
        x=alt.X("points:Q", title="Points de Bbio", stack="zero"),
        color=alt.Color("poste:N", scale=echelle_couleurs(COULEURS), legend=legende()),
        order=alt.Order("ordre:Q"),
        tooltip=[alt.Tooltip("poste:N", title="Poste"),
                 alt.Tooltip("besoin:Q", title="Besoin (kWh/m²)", format=".1f"),
                 alt.Tooltip("coefficient:Q", title="Coefficient"),
                 alt.Tooltip("points:Q", title="Points", format=".1f")])
    limite = pd.DataFrame({"points": [r.bbio["bbio_max"]],
                           "texte": [f"Bbio max {nombre(r.bbio['bbio_max'], 1)}"]})
    trait = alt.Chart(limite).mark_rule(color=charte.COULEUR_LIMITE, strokeWidth=2, strokeDash=[5, 4]).encode(
        x="points:Q")
    etiquette = alt.Chart(limite).mark_text(align="left", dx=6, dy=-34, color=charte.COULEUR_LIMITE).encode(
        x="points:Q", text="texte:N")
    return (barre + trait + etiquette).properties(height=HAUTEUR_BARRE)


def _barres_mensuelles(r):
    """Points de Bbio de chaque mois conventionnel, par poste."""
    tables = []
    for _, mois in r.mensuel.iterrows():
        table = _points_par_poste(mois)
        table["rang_mois"] = int(mois["mois"])
        table["mois"] = MOIS[int(mois["mois"]) - 1]
        tables.append(table)
    return alt.Chart(pd.concat(tables, ignore_index=True)).mark_bar(stroke="white", strokeWidth=2).encode(
        x=alt.X("mois:N", sort=MOIS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("points:Q", title="Points de Bbio", stack="zero"),
        color=alt.Color("poste:N", scale=echelle_couleurs(COULEURS), legend=legende()),
        order=alt.Order("ordre:Q"),
        tooltip=[alt.Tooltip("mois:N", title="Mois"), alt.Tooltip("poste:N", title="Poste"),
                 alt.Tooltip("besoin:Q", title="Besoin (kWh/m²)", format=".2f"),
                 alt.Tooltip("points:Q", title="Points", format=".1f")]).properties(height=HAUTEUR)


def afficher(r, boite):
    ecart = (r.bbio["bbio"] / r.bbio["bbio_max"] - 1.0) * 100.0
    colonnes = st.columns(4)
    colonnes[0].metric("Bbio", nombre(r.bbio["bbio"], 1, "points"), f"{ecart:+.0f} % du Bbio max",
                       delta_color="inverse")
    for colonne, (cle, nom, _) in zip(colonnes[1:], POSTES):
        colonne.metric(nom, nombre(r.bbio[cle], 1, "kWh/m²"))
    st.altair_chart(_barre_annuelle(r), alt="Les trois besoins pondérés, comparés au Bbio max")
    st.caption("Répartition dans l'année, par mois conventionnel de quatre ou cinq semaines.")
    st.altair_chart(_barres_mensuelles(r), alt="Points de Bbio par mois et par poste")


def reperes():
    return [f"Un kWh/m² de chauffage ou de froid pèse {nombre(hyp('bbio_coef_chauffage'))} points, un kWh/m² "
            f"d'éclairage {nombre(hyp('bbio_coef_eclairage'))} points.",
            f"Bbio max moyen du logement collectif : {nombre(hyp('bbio_max_moyen_logement_collectif'))} points, "
            "avant modulation par le climat, l'altitude, la surface, le bruit et la hauteur sous plafond.",
            "Fiabilité de l'outil : sur 46 groupes de 16 études, Bbio à ± 10 % de l'étude dans 30 groupes, écart "
            "médian nul ; le chauffage est parfois beaucoup trop fort (jusqu'à + 50 % environ)."]


BRIQUE = Brique(
    cle="bbio",
    titre="Bbio : les trois besoins",
    icone=":material/thermostat:",
    phenomene=("Le Bbio note le bâtiment **avant tout équipement** : ce qu'il faut de chaleur, de froid et de "
               "lumière artificielle pour le tenir à température et l'éclairer ([[Besoins (thermiques)|ses "
               "besoins]]), selon sa forme, son enveloppe, ses baies et son climat. Plus il est bas, moins le "
               "bâtiment demande."),
    afficher=afficher,
    reperes=reperes,
    equation=r"B_{bio} = 2 \times B_{ch} + 2 \times B_{fr} + 5 \times B_{ecl}",
    lecture=("$B_{ch}$, $B_{fr}$ et $B_{ecl}$ : besoins annuels de chauffage, de refroidissement et d'éclairage, "
             "en kWh par m² de surface de référence (la surface habitable en logement). Le Bbio se compare à "
             "$B_{bio,max} = B_{bio,max\\,moyen} \\times (1 + \\sum M_b)$.\n\n"
             "Ce qu'elle dit : un kWh/m² d'éclairage pèse deux fois et demie plus qu'un kWh/m² de chauffage ou "
             "de froid. Des baies qui font entrer la lumière du jour peuvent donc faire baisser le Bbio, même si "
             "elles ajoutent un peu de chauffage ou de froid."),
    reference=("arrêté du 4 août 2021, annexe III, fiche 13.1, éq. 2385 ; Bbio max : code de la construction et "
               "de l'habitation, annexe à l'article R. 172-4, chapitres II et III."),
    code=(points_bbio, bbio_max),
    besoin="bbio",
    glossaire=("Besoins (thermiques)", "Bioclimatique", "RE2020"))
