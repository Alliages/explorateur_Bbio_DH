"""
============================================================
 BRIQUE « DH » — durée et intensité de l'inconfort d'été
============================================================
 Niveau 1 : le DH face à son maximum, puis, heure par heure sur
 la période de confort adaptatif, la température dehors et
 dedans face au seuil de confort, avec les degrés-heures comptés.
 En dessous, les degrés-heures de chaque jour : on y trace un
 cadre à la souris pour zoomer sur ces jours (comme le curseur de
 zoom de l'onglet Analyse de Météo et Chaleur) ; trois boutons
 ouvrent l'été entier, la semaine la plus chaude ou le jour le
 plus chaud ; la molette zoome aussi sur le graphique du dessus.
 Niveau 2 : éq. 2551 de la fiche 13.5, moteur/dh.py.
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
                                          etiquettes_heures, legende, nombre, traits)
from interface.briques.semaine_chaude import debut_semaine_la_plus_chaude
from moteur.dh import degres_heures, dh_max
from moteur.hypotheses import hyp

SERIES = {"Extérieur": charte.COULEUR_EXTERIEUR, "Intérieur (opérative)": charte.COULEUR_INTERIEUR,
          "Seuil de confort": charte.COULEUR_SEUIL}
# Fenêtres proposées au-dessus du graphique ; la première est celle de l'ouverture
ETE_ENTIER, SEMAINE, JOUR = "Été entier", "Semaine la plus chaude", "Jour le plus chaud"
FENETRES = (ETE_ENTIER, SEMAINE, JOUR)
ZOOM = "zoom"                   # nom de la sélection tracée sur la bande des DH de chaque jour


def par_jour(ete):
    """Une ligne par jour de la période de confort adaptatif : maximums du jour et degrés-heures du jour."""
    periode = ete[ete["confort_adaptatif"] > 0]
    return periode.groupby(periode["date"].dt.normalize()).agg(
        exterieur=("te", "max"), interieur=("theta_op", "max"), seuil=("seuil_confort_corrige", "max"),
        dh=("dh_horaire", "sum")).reset_index()


def _ms(instant):
    """Instant en millisecondes depuis 1970, comme Vega lit les dates des données (heure lue sans fuseau)."""
    return int(pd.Timestamp(instant).value // 1_000_000)


def fenetre(ete, choix):
    """Bornes (première et dernière heure, en millisecondes) de la fenêtre choisie, ou None pour l'été entier.

    Semaine la plus chaude : les sept jours qui comptent le plus de degrés-heures (comme la brique « Semaine
    chaude ») ; jour le plus chaud : le jour qui en compte le plus.
    """
    if choix == SEMAINE:
        debut = debut_semaine_la_plus_chaude(ete)
        heures = ete["date"].iloc[debut:debut + JOURS_PAR_SEMAINE * HEURES_PAR_JOUR]
    elif choix == JOUR:
        jours = par_jour(ete)
        jour = jours.loc[jours["dh"].idxmax(), "date"]
        heures = ete["date"][ete["date"].dt.normalize() == jour]
    else:
        return None
    return _ms(heures.iloc[0]), _ms(heures.iloc[-1])


def bornes_selectionnees(evenement):
    """Bornes (en millisecondes) du cadre tracé sur la bande des DH de chaque jour, ou None s'il n'y en a pas.

    evenement : ce que rend st.altair_chart(…, on_select="rerun") ; la sélection « zoom » porte sur « date ».
    """
    try:
        valeurs = evenement["selection"][ZOOM]["date"]
    except (KeyError, TypeError):
        return None
    if not valeurs or len(valeurs) != 2:
        return None
    return tuple(v if isinstance(v, (int, float)) else _ms(v) for v in valeurs)


def temperatures(ete, bornes=None):
    """Heure par heure : température dehors et dedans, seuil de confort, et en orange les degrés-heures comptés
    (la surface entre le seuil et la température intérieure, aux heures retenues).

    bornes : jours montrés (millisecondes), None pour l'été entier. Seules ces heures sont envoyées à la page (un
    domaine imposé à l'axe du temps n'est pas suivi par Streamlit). La molette zoome encore, le glisser déplace,
    le double-clic revient aux bornes.
    """
    periode = ete[ete["confort_adaptatif"] > 0]
    if bornes:
        debut, fin = (pd.to_datetime(b, unit="ms") for b in bornes)
        periode = periode[(periode["date"] >= debut) & (periode["date"] <= fin)]
    axe_x = alt.X("date:T", title=None, axis=etiquettes_heures())
    longue = periode.rename(columns={"te": "Extérieur", "theta_op": "Intérieur (opérative)",
                                     "seuil_confort_corrige": "Seuil de confort"}).melt(
        id_vars="date", value_vars=list(SERIES), var_name="serie", value_name="temperature")
    longue["temperature"] = longue["temperature"].round(1)          # page plus légère, même lecture
    base = alt.Chart(longue).encode(
        x=axe_x, y=alt.Y("temperature:Q", title="Température (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color("serie:N", scale=echelle_couleurs(SERIES), legend=legende()),
        strokeDash=traits(SERIES, pointilles=("Seuil de confort",)))
    lignes = base.mark_line(strokeWidth=2, clip=True).add_params(
        alt.selection_interval(bind="scales", encodings=["x"]))
    survol = base.mark_circle(size=50, opacity=0, clip=True).encode(
        tooltip=[alt.Tooltip("date:T", title="Heure", format=FORMAT_HEURE), alt.Tooltip("serie:N", title="Série"),
                 alt.Tooltip("temperature:Q", title="°C", format=".1f")])
    comptes = periode[["date"]].assign(seuil_confort_corrige=periode["seuil_confort_corrige"].round(2),
                                       haut=(periode["seuil_confort_corrige"] + periode["dh_horaire"]).round(2))
    surface = alt.Chart(comptes).mark_area(color=charte.COULEUR_INCONFORT, opacity=0.45, interpolate="step",
                                           clip=True).encode(x=axe_x, y="seuil_confort_corrige:Q", y2="haut:Q")
    return (surface + lignes + survol).properties(height=HAUTEUR)


def apercu(ete, bornes=None):
    """Degrés-heures de chaque jour, avec la sélection « zoom » : un cadre (celui des bornes au départ) que l'on
    trace ou déplace à la souris pour choisir les jours montrés au-dessus."""
    zoom = alt.selection_interval(encodings=["x"], name=ZOOM, **({"value": {"x": list(bornes)}} if bornes else {}))
    return alt.Chart(par_jour(ete)).mark_bar(color=charte.COULEUR_INCONFORT).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format=FORMAT_JOUR)),
        y=alt.Y("dh:Q", title="DH du jour (°C.h)"),
        tooltip=[alt.Tooltip("date:T", title="Jour", format=FORMAT_JOUR),
                 alt.Tooltip("dh:Q", title="Degrés-heures (°C.h)", format=".1f")]).add_params(
        zoom).properties(height=HAUTEUR_BANDE)


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
    if par_jour(r.ete).empty:
        st.info("Ce climat n'a pas de période de confort adaptatif : aucun degré-heure n'est compté.")
        return
    choix = st.segmented_control("Montrer", FENETRES, default=ETE_ENTIER, required=True, key="dh_fenetre",
                                 help=aide("dh_fenetre"))
    st.caption("Heure par heure sur la période de confort adaptatif : la température dehors (noir) et dedans "
               "(jaune), le seuil de confort (orange, en pointillé) et, en orange, les degrés-heures comptés. "
               "En dessous, les degrés-heures de chaque jour : y tracer un cadre à la souris montre ces jours-là, "
               "le déplacer fait avancer ; la molette zoome sur le graphique du dessus. Heure légale.")
    bornes = fenetre(r.ete, choix)
    haut = st.container()       # le graphique du dessus attend le cadre tracé sur celui du dessous
    # Deux graphiques séparés, liés par Streamlit (on_select) : réunis dans un alt.vconcat de couches, ils
    # s'élargissent sans fin dans la page. La clé suit le bouton choisi : changer de bouton efface le cadre tracé.
    evenement = st.altair_chart(apercu(r.ete, bornes), on_select="rerun", selection_mode=ZOOM,
                                key=f"dh_apercu_{FENETRES.index(choix)}",
                                alt="Degrés-heures de chaque jour de la période de confort adaptatif")
    with haut:
        st.altair_chart(temperatures(r.ete, bornes_selectionnees(evenement) or bornes),
                        alt="Températures dehors et dedans et seuil de confort, heure par heure")


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
