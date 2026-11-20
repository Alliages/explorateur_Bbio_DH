"""
============================================================
 BRIQUE « DH » — durée et intensité de l'inconfort d'été
============================================================
 Niveau 1 : le DH face à son maximum, puis, jour par jour sur la
 période de confort adaptatif, la température la plus haute
 dehors et dedans face au seuil de confort, et les degrés-heures
 que chaque jour ajoute.
 Niveau 2 : éq. 2551 de la fiche 13.5, moteur/dh.py.
============================================================
"""

import altair as alt
import streamlit as st

from interface import charte
from interface.briques.base import Brique
from interface.briques.graphiques import FORMAT_JOUR, HAUTEUR, HAUTEUR_BANDE, echelle_couleurs, legende, nombre
from moteur.dh import degres_heures, dh_max
from moteur.hypotheses import hyp

SERIES = {"Extérieur": charte.COULEUR_EXTERIEUR, "Intérieur (opérative)": charte.COULEUR_INTERIEUR,
          "Seuil de confort": charte.COULEUR_LIMITE}


def par_jour(ete):
    """Une ligne par jour de la période de confort adaptatif : maximums du jour et degrés-heures du jour."""
    periode = ete[ete["confort_adaptatif"] > 0]
    return periode.groupby(periode["date"].dt.normalize()).agg(
        exterieur=("te", "max"), interieur=("theta_op", "max"), seuil=("seuil_confort_corrige", "max"),
        dh=("dh_horaire", "sum")).reset_index()


def _temperatures(jours):
    """Maximum du jour, dehors et dedans, et seuil de confort de jour."""
    longue = jours.rename(columns={"exterieur": "Extérieur", "interieur": "Intérieur (opérative)",
                                   "seuil": "Seuil de confort"}).melt(
        id_vars="date", value_vars=list(SERIES), var_name="serie", value_name="temperature")
    base = alt.Chart(longue).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR)),
        y=alt.Y("temperature:Q", title="Maximum du jour (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color("serie:N", scale=echelle_couleurs(SERIES), legend=legende()))
    lignes = base.mark_line(strokeWidth=2, interpolate="step-after")
    survol = base.mark_circle(size=70, opacity=0).encode(
        tooltip=[alt.Tooltip("date:T", title="Jour", format=FORMAT_JOUR), alt.Tooltip("serie:N", title="Série"),
                 alt.Tooltip("temperature:Q", title="Maximum (°C)", format=".1f")])
    return (lignes + survol).properties(height=HAUTEUR)


def _dh_par_jour(jours):
    return alt.Chart(jours).mark_bar(color=charte.COULEUR_INCONFORT).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR)),
        y=alt.Y("dh:Q", title="DH du jour (°C.h)"),
        tooltip=[alt.Tooltip("date:T", title="Jour", format=FORMAT_JOUR),
                 alt.Tooltip("dh:Q", title="Degrés-heures (°C.h)", format=".1f")]).properties(height=HAUTEUR_BANDE)


def afficher(r, boite):
    if r.dh["avertissement"]:
        st.warning(f"Ce bâtiment n'a {r.dh['avertissement']} : rien ne limite la chaleur de l'année caniculaire "
                   "et le DH n'est plus comparable à celui d'une étude.", icon=":material/warning:")
    colonnes = st.columns(4)
    colonnes[0].metric("DH", nombre(r.dh["dh"], 0, "°C.h"), f"{r.dh['ecart_pct']:+.0f} % du DH max",
                       delta_color="inverse")
    colonnes[1].metric("DH max", nombre(r.dh["dh_max"], 0, "°C.h"))
    colonnes[2].metric("Heures d'inconfort", nombre(r.dh["nb_h_inconfort"], 0, "h"))
    colonnes[3].metric("Température la plus haute", nombre(r.dh["theta_op_max"], 1, "°C"))
    jours = par_jour(r.ete)
    if jours.empty:
        st.info("Ce climat n'a pas de période de confort adaptatif : aucun degré-heure n'est compté.")
        return
    st.caption("Chaque jour de la période de confort adaptatif : la température la plus haute dehors et "
               "dedans, et le seuil de confort de la journée. En dessous, les degrés-heures que le jour ajoute.")
    st.altair_chart(_temperatures(jours), alt="Températures maximales du jour, dehors et dedans, et seuil de confort")
    st.altair_chart(_dh_par_jour(jours), alt="Degrés-heures d'inconfort de chaque jour")


def reperes():
    return [f"DH max du logement collectif sans contrainte extérieure : "
            f"{nombre(hyp('dh_max_lc_categorie_1'), 0, '°C.h')}.",
            "1 °C au-dessus du seuil pendant 100 heures occupées, ou 2 °C pendant 50 heures : 100 °C.h.",
            "Le calcul se fait sur une année à séquence caniculaire, sans climatisation, même si le logement "
            "est climatisé.",
            "Fiabilité de l'outil : sur 23 groupes de 10 études, le DH va de 37 % sous l'étude à 30 % au-dessus."]


BRIQUE = Brique(
    cle="dh",
    titre="DH : l'inconfort d'été",
    icone=":material/sunny:",
    phenomene=("Les degrés-heures mesurent à la fois **combien de temps** et **de combien** la "
               "[[Température opérative|température ressentie]] dépasse le seuil de confort, quand le logement "
               "est occupé. Protections solaires, ouverture des fenêtres la nuit, [[Inertie|inertie]] et "
               "[[Brasseur d’air (ventilateur de plafond)|brasseurs d'air]] les font baisser."),
    afficher=afficher,
    reperes=reperes,
    equation=r"DH = \sum_{h} \max\left(0 \;;\; \theta_{op}(h) - \theta_{conf}(h)\right)",
    lecture=("$\\theta_{op}$ : température opérative du logement (moyenne de l'air et des parois), en fin "
             "d'heure. $\\theta_{conf}$ : température limite de confort chaud, relevée par l'effet des "
             "brasseurs d'air. La somme porte sur les heures occupées de la période de confort adaptatif.\n\n"
             "Ce qu'elle dit : seul compte l'écart au-dessus du seuil. Une heure à 2 °C de trop compte autant que "
             "deux heures à 1 °C de trop ; une heure sous le seuil ne rattrape rien."),
    reference=("arrêté du 4 août 2021, annexe III, fiche 13.5, éq. 2542 à 2551 ; DH max : code de la "
               "construction et de l'habitation, annexe à l'article R. 172-4, chapitres II et III."),
    code=(degres_heures, dh_max),
    besoin="dh",
    glossaire=("DH", "Température opérative", "Confort adaptatif", "Canicule"))
