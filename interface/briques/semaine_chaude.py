"""
============================================================
 BRIQUE « Semaine chaude » — l'inconfort heure par heure
============================================================
 Niveau 1 : sept jours de l'année caniculaire, heure par heure :
 la température dehors, la température ressentie dedans, le
 seuil de confort (26 °C la nuit, jusqu'à 28 °C le jour) et, en
 orange, les degrés-heures comptés. En dessous, ce que font les
 occupants : protections baissées, fenêtres ouvertes.
 Par défaut, la semaine montrée est celle qui compte le plus de
 degrés-heures ; un curseur la décale.
 Niveau 2 : éq. 2543 à 2545 de la fiche 13.5, moteur/confort.py.
============================================================
"""

import altair as alt
import pandas as pd
import streamlit as st

from config.reglages import HEURES_PAR_JOUR, JOURS_PAR_SEMAINE
from interface import charte
from interface.aides import aide
from interface.briques.base import Brique
from interface.briques.graphiques import (FORMAT_HEURE, FORMAT_JOUR, HAUTEUR, HAUTEUR_BANDE, echelle_couleurs,
                                          legende, nombre)
from moteur.confort import moyenne_glissante_exterieure, seuil_confort_chaud
from moteur.hypotheses import hyp

DECALAGE_MAX_JOURS = 45         # course du curseur, de part et d'autre de la semaine la plus chaude
TEMPERATURES = {"Extérieur": charte.COULEUR_EXTERIEUR, "Intérieur (opérative)": charte.COULEUR_INTERIEUR,
                "Seuil de confort": charte.COULEUR_LIMITE}
GESTES = {"Protections baissées": charte.COULEUR_PROTECTION, "Fenêtres ouvertes": charte.COULEUR_OUVERTURE}


def debut_semaine_la_plus_chaude(ete):
    """Rang de la première heure des sept jours consécutifs qui comptent le plus de degrés-heures."""
    par_jour = ete["dh_horaire"].to_numpy().reshape(-1, HEURES_PAR_JOUR).sum(axis=1)
    sur_sept_jours = pd.Series(par_jour).rolling(JOURS_PAR_SEMAINE).sum().shift(-(JOURS_PAR_SEMAINE - 1))
    return int(sur_sept_jours.fillna(0.0).idxmax()) * HEURES_PAR_JOUR


def extraire_semaine(ete, decalage_jours=0):
    """Les 168 heures de la semaine la plus chaude, décalée de decalage_jours et gardée dans l'année."""
    duree = JOURS_PAR_SEMAINE * HEURES_PAR_JOUR
    debut = debut_semaine_la_plus_chaude(ete) + decalage_jours * HEURES_PAR_JOUR
    debut = max(0, min(len(ete) - duree, debut))
    return ete.iloc[debut:debut + duree]


def _temperatures(semaine):
    axe_x = alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR, tickCount="day"))
    longue = semaine.rename(columns={"te": "Extérieur", "theta_op": "Intérieur (opérative)",
                                     "seuil_confort_corrige": "Seuil de confort"}).melt(
        id_vars="date", value_vars=list(TEMPERATURES), var_name="serie", value_name="temperature")
    base = alt.Chart(longue).encode(
        x=axe_x, y=alt.Y("temperature:Q", title="Température (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color("serie:N", scale=echelle_couleurs(TEMPERATURES), legend=legende()))
    lignes = base.mark_line(strokeWidth=2)
    survol = base.mark_circle(size=60, opacity=0).encode(
        tooltip=[alt.Tooltip("date:T", title="Heure", format=FORMAT_HEURE), alt.Tooltip("serie:N", title="Série"),
                 alt.Tooltip("temperature:Q", title="°C", format=".1f")])
    # Degrés-heures comptés : la surface entre le seuil et la température intérieure, aux heures retenues
    comptes = semaine.assign(haut=semaine["seuil_confort_corrige"] + semaine["dh_horaire"])
    surface = alt.Chart(comptes).mark_area(color=charte.COULEUR_INCONFORT, opacity=0.55, interpolate="step").encode(
        x=axe_x, y="seuil_confort_corrige:Q", y2="haut:Q")
    return (surface + lignes + survol).properties(height=HAUTEUR)


def _gestes(semaine):
    longue = semaine.assign(**{"Protections baissées": semaine["rprot_moyen"] * 100.0,
                               "Fenêtres ouvertes": semaine["rouv_moyen"] * 100.0}).melt(
        id_vars="date", value_vars=list(GESTES), var_name="serie", value_name="part")
    return alt.Chart(longue).mark_line(strokeWidth=2, interpolate="step-after").encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR, tickCount="day")),
        y=alt.Y("part:Q", title="Part (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("serie:N", scale=echelle_couleurs(GESTES), legend=legende()),
        tooltip=[alt.Tooltip("date:T", title="Heure", format=FORMAT_HEURE), alt.Tooltip("serie:N", title="Geste"),
                 alt.Tooltip("part:Q", title="%", format=".0f")]).properties(height=HAUTEUR_BANDE)


def afficher(r, boite):
    decalage = st.slider("Décaler la semaine (jours)", -DECALAGE_MAX_JOURS, DECALAGE_MAX_JOURS, 0,
                         key="semaine_chaude_decalage", help=aide("semaine_chaude_decalage"))
    semaine = extraire_semaine(r.ete, decalage)
    colonnes = st.columns(3)
    colonnes[0].metric("DH de la semaine", nombre(semaine["dh_horaire"].sum(), 0, "°C.h"))
    colonnes[1].metric("Maximum dehors", nombre(semaine["te"].max(), 1, "°C"))
    colonnes[2].metric("Maximum dedans", nombre(semaine["theta_op"].max(), 1, "°C"))
    st.caption("En orange : les degrés-heures comptés, quand le logement est occupé et que la température "
               "ressentie dépasse le seuil. Heure légale.")
    st.altair_chart(_temperatures(semaine),
                    alt="Températures extérieure et intérieure et seuil de confort, heure par heure sur sept jours")
    st.caption("Ce que font les occupants, selon les règles conventionnelles : part des protections mobiles "
               "baissées et part ouverte des fenêtres.")
    st.altair_chart(_gestes(semaine), alt="Part des protections baissées et des fenêtres ouvertes, heure par heure")


def reperes():
    return [f"Seuil de confort : la consigne de refroidissement la nuit, jusqu'à "
            f"{nombre(hyp('confort_ecart_min_max'))} °C de plus le jour quand il fait chaud depuis plusieurs jours.",
            f"La chaleur des jours passés compte : chaque jour garde "
            f"{nombre(hyp('confort_poids_veille') * 100)} % de la moyenne glissante de la veille.",
            "Un logement qui se rafraîchit la nuit repart plus bas le matin : regarder l'écart entre dedans et "
            "dehors en fin de nuit."]


BRIQUE = Brique(
    cle="semaine_chaude",
    titre="Une semaine chaude",
    icone=":material/timeline:",
    phenomene=("Pendant une [[Canicule|canicule]], la température du logement **suit celle du dehors avec "
               "retard** : les murs et les planchers stockent la chaleur le jour et la rendent la nuit "
               "([[Inertie|inertie]]). Baisser les [[Occultation|protections]] le jour et ouvrir la nuit, quand "
               "l'air est plus frais ([[Rafraichissement|rafraîchissement]]), décide du résultat."),
    afficher=afficher,
    reperes=reperes,
    equation=(r"\theta_{conf} = \min\left(\theta_{fr} + 2 \;;\; \max\left(\theta_{fr} \;;\; "
              r"0{,}33 \times \theta_{rm} + 18{,}8 + 2\right)\right)"),
    lecture=("$\\theta_{conf}$ : température limite de confort chaud, de jour. $\\theta_{fr}$ : consigne de "
             "refroidissement en occupation. $\\theta_{rm}$ : moyenne glissante de la température extérieure, "
             "$\\theta_{rm}(j) = 0{,}8 \\times \\theta_{rm}(j-1) + 0{,}2 \\times$ moyenne de la veille. La nuit, "
             "en habitation, le seuil est la consigne.\n\n"
             "Ce qu'elle dit : le seuil de jour suit la chaleur des jours passés. Après plusieurs jours chauds, "
             "on s'y est fait et l'on supporte jusqu'à 2 °C de plus ([[Confort adaptatif|confort adaptatif]])."),
    reference="arrêté du 4 août 2021, annexe III, fiche 3.1, éq. 1 et 2, et fiche 13.5, éq. 2543 à 2545.",
    code=(seuil_confort_chaud, moyenne_glissante_exterieure),
    besoin="dh",
    glossaire=("Confort adaptatif", "Inertie", "Constante de temps", "Rafraichissement", "Occultation"))
