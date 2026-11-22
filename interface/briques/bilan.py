"""
============================================================
 BRIQUE « Le bilan en coupe » — par où la chaleur entre et sort
============================================================
 Niveau 1 : la coupe de la boîte (interface/coupe.py), une
 flèche par poste, d'épaisseur proportionnelle à ses kWh, sur
 une période des calculs lancés (année moyenne du Bbio, été ou
 semaine la plus chaude du DH) ; le tableau du bilan, poste par
 poste ; avec le DH, la part de chaque poste dans la chaleur
 entrée aux heures qui comptent des DH. Un clic sur une paroi de
 la coupe l'ouvre dans la fiche sous l'axonométrie.
 Niveau 2 : fiche 5.21 (modèle du groupe), hypothèse 103 de
 docs/audit.md, moteur/bilan_paroi.py.

 Proposée dès qu'un calcul est lancé, Bbio ou DH (besoin vide).
============================================================
"""

import altair as alt
import pandas as pd
import streamlit as st

from interface import charte
from interface.aides import aide
from interface.briques.base import Brique
from interface.briques.graphiques import nombre
from interface.calcul import CUMUL, ECHANGE, PERIODES_PAROIS, POINTE, RESTE, SOLEIL
from interface.coupe import COULEURS, LIBELLES_POSTES, dessiner_coupe
from interface.dessin_cliquable import dessin_cliquable, paroi_cliquee
from interface.fiche_paroi import parois
from moteur.bilan_paroi import entrant, masse_gardee, postes_du_groupe

# ============================================================
# RÉGLAGES
# ============================================================
# Familles du tableau du bilan : (libellé, genre de flèche de la coupe, postes de moteur.bilan_paroi.POSTES ;
# les parois sont ajoutées selon la boîte)
FAMILLES = (("Soleil transmis", "soleil", ()), ("Parois : conduction et ciel", "paroi", ()),
            ("Ponts thermiques", "paroi", ("ponts_thermiques",)),
            ("Air : ventilation", "air", ("ventilation",)), ("Air : infiltrations", "air", ("infiltrations",)),
            ("Air : baies ouvertes", "air", ("ouvertures",)), ("Apports internes", "apports", ("apports_internes",)),
            ("Chauffage", "chauffage", ("chauffage",)), ("Froid", "froid", ("refroidissement",)))
PART_MIN = 0.005                # part dans le DH en dessous de laquelle un poste n'est pas montré
HAUTEUR_BARRE_POSTE = 26        # px par poste dans le graphique des parts
LARGEUR_ETIQUETTES = 320        # px laissés aux noms des postes, à gauche du graphique des parts
# Deux lectures de la coupe : le cumul sur la période, ou l'heure de pointe (interface/calcul.py)
LECTURES = {CUMUL: "Sur la période (kWh)", POINTE: "Heure de pointe (Wh)"}
UNITES = {CUMUL: "kWh", POINTE: "Wh"}


def _periodes(resultats):
    """Périodes des calculs lancés : {clé: (libellé, bilan en coupe de la période : cumul, pointe, heure…)}, dans
    l'ordre de PERIODES_PAROIS."""
    tables = {"dh": resultats.coupe_dh, "bbio": resultats.coupe_bbio}
    return {f"{calcul}.{periode}": (libelle, tables[calcul][periode]) for calcul, periode, libelle in PERIODES_PAROIS
            if tables[calcul] is not None and periode in tables[calcul]}


def tableau(bilan):
    """Bilan d'une période par famille : liste de (famille, kWh entrés, kWh sortis), puis la masse. Les parois
    comptent à part leur soleil (entré) et leur échange (le plus souvent sorti)."""
    lignes = []
    for libelle, _, postes in FAMILLES:
        if libelle == "Soleil transmis":
            valeurs = [v for poste, v in bilan.items() if poste.endswith(f".{SOLEIL}")]
        elif libelle.startswith("Parois"):
            valeurs = [v for poste, v in bilan.items() if poste.endswith(f".{ECHANGE}")]
        else:
            valeurs = [bilan.get(poste, 0.0) for poste in postes]
        entre = sum(v for v in valeurs if v > 0)
        sorti = -sum(v for v in valeurs if v < 0)
        if round(entre) or round(sorti):
            lignes.append((libelle, entre, sorti))
    reste = bilan.get(RESTE, 0.0)
    lignes.append(("Gardé (rendu) par la masse", max(0.0, -reste), max(0.0, reste)))
    return lignes


def parts_dh(part_dh, boite):
    """Part de chaque paroi et de chaque poste dans la chaleur entrée aux heures qui comptent des DH : DataFrame
    (poste, part, genre), du plus grand au plus petit, sans les parts sous PART_MIN."""
    noms = parois(boite)
    total = sum(part_dh.values())
    if total <= 0:
        return pd.DataFrame(columns=["poste", "part", "genre"])
    lignes = []
    for cle, valeur in part_dh.items():
        if cle in LIBELLES_POSTES:
            nom, genre = LIBELLES_POSTES[cle], {"ponts_thermiques": "paroi", "apports_internes": "apports",
                                                "chauffage": "chauffage", "refroidissement": "froid"}.get(cle, "air")
        else:
            nom, genre = noms.get(cle, cle), ("soleil" if cle.startswith("baies_") else "paroi")
        lignes.append((nom, valeur / total, genre))
    table = pd.DataFrame(lignes, columns=["poste", "part", "genre"])
    return table[table["part"] >= PART_MIN].sort_values("part", ascending=False).reset_index(drop=True)


def _valeur(valeur, unite):
    """Valeur du tableau du bilan, en kWh ou en Wh ; un tiret pour rien."""
    return nombre(valeur, 0, unite) if round(valeur) else "—"


def _graphique_parts(table):
    genres = {genre: COULEURS[genre] for genre in COULEURS if genre in set(table["genre"])}
    return alt.Chart(table).mark_bar().encode(
        x=alt.X("part:Q", title="Part de la chaleur entrée aux heures d'inconfort", axis=alt.Axis(format="%")),
        y=alt.Y("poste:N", title=None, sort=list(table["poste"]), axis=alt.Axis(labelLimit=LARGEUR_ETIQUETTES)),
        color=alt.Color("genre:N", scale=alt.Scale(domain=list(genres), range=list(genres.values())), legend=None),
        tooltip=[alt.Tooltip("poste:N", title="Poste"), alt.Tooltip("part:Q", title="Part", format=".0%")],
    ).properties(height=HAUTEUR_BARRE_POSTE * len(table) + 40)


def afficher(resultats, boite):
    periodes = _periodes(resultats)
    if not periodes:
        st.info("Relancer le calcul pour lire le bilan en coupe.")
        return
    colonnes = st.columns(2)
    cle = colonnes[0].segmented_control("Période", list(periodes), default=next(iter(periodes)), required=True,
                                        format_func=lambda c: periodes[c][0], key="periode_coupe",
                                        help=aide("periode_coupe"))
    lecture = colonnes[1].segmented_control("Lecture", list(LECTURES), default=CUMUL, required=True,
                                            format_func=LECTURES.get, key="lecture_coupe", help=aide("lecture_coupe"))
    libelle, coupe = periodes[cle]
    bilan, unite = coupe[lecture], UNITES[lecture]
    titre = libelle if lecture == CUMUL else f"{libelle}, heure de pointe le {coupe['heure']}"
    choix = parois(boite)

    def _clic():
        paroi = paroi_cliquee(st.session_state.get("dessin_coupe"), choix)
        if paroi is not None:
            st.session_state["paroi_examinee"] = paroi

    svg = dessiner_coupe(boite, bilan, titre, surlignee=st.session_state.get("paroi_examinee"), unite=unite)
    dessin_cliquable(svg, f"Coupe schématique du bilan de chaleur ({titre}) ; cliquer sur une paroi ouvre sa "
                     "fiche sous l'axonométrie", key="dessin_coupe", on_clic=_clic)
    if lecture == POINTE:
        st.caption(f"Heure de pointe : l'heure de la période où le soleil transmis au logement est le plus fort, le "
                   f"{coupe['heure']} ({nombre(coupe['te'], 1, '°C')} dehors, {nombre(coupe['theta_i'], 1, '°C')} "
                   "dans l'air du logement). Chaque flèche donne les Wh passés pendant cette heure, soit sa "
                   "puissance moyenne en W. Ce qui n'est pas ressorti dans l'heure est gardé par la masse : il "
                   "ressortira plus tard, ou fera monter la température.")
    st.caption("Coupe hors échelle, perpendiculaire à la façade principale. Chaque flèche a l'épaisseur de sa "
               "valeur et pointe dans le sens où la chaleur passe ; les deux pignons, devant et derrière la coupe, "
               "sont le cercle du milieu (⊙ : la chaleur sort ; ⊗ : elle entre). Survoler une flèche donne son "
               "détail ; cliquer sur une paroi ouvre sa fiche sous l'axonométrie.")
    st.markdown(f"**Bilan — {titre}**\n\n| Poste | Entré | Sorti |\n|---|---:|---:|\n"
                + "\n".join(f"| {nom} | {_valeur(entre, unite)} | {_valeur(sorti, unite)} |"
                            for nom, entre, sorti in tableau(bilan)),
                help=aide("bilan_coupe"))
    if resultats.part_dh is not None:
        table = parts_dh(resultats.part_dh, boite)
        if len(table):
            st.markdown("**Ce qui chauffe le logement aux heures d'inconfort**", help=aide("part_dh"))
            st.altair_chart(_graphique_parts(table), use_container_width=True)
            st.caption("En jaune, les baies (soleil surtout) ; en bleu nuit, les parois opaques et les ponts "
                       "thermiques ; en gris, l'air ; en orange, les apports internes. Pour l'effet exact d'une "
                       "paroi sur le DH, la choisir et cliquer sur « Mesurer l'effet de cette paroi ».")


def reperes():
    return ["Le bilan ferme exactement : ce qui entre et ne ressort pas est gardé par la masse du logement. Sur une "
            "année, la masse rend presque tout ce qu'elle a pris.",
            "Logement de 70 m² de départ, enveloppe faible, sans protection, semaine la plus chaude : à l'heure de "
            "pointe, les baies sud (4,9 m², Sw 0,45) font entrer près de 1 000 Wh en une heure, presque deux fois "
            "les apports internes (530 Wh) ; sur toute la semaine, 59 kWh seulement, car la nuit et les heures "
            "voilées comptent aussi.",
            "En canicule, la nuit n'est que de quelques degrés plus fraîche que le logement : même grandes "
            "ouvertes, les baies n'évacuent qu'une partie de ce que le soleil a fait entrer dans la journée."]


BRIQUE = Brique(
    cle="bilan",
    titre="Le bilan en coupe",
    icone=":material/compare_arrows:",
    phenomene=("Sur une période, toute la chaleur qui entre dans le logement en ressort ou reste dans sa "
               "[[Inertie|masse]]. Elle entre par le soleil, les apports internes et le chauffage ; elle sort par "
               "[[Conduction|conduction]] à travers les parois, par l'air renouvelé ([[Ventilation|ventilation]], "
               "infiltrations, fenêtres ouvertes) et par les ponts thermiques. La coupe montre la taille de chaque "
               "passage."),
    afficher=afficher,
    reperes=reperes,
    equation=(r"\underbrace{\Phi_{sol} + \Phi_{int} + \Phi_{ch}}_{\text{entre}} - \underbrace{\sum_k H_k "
              r"(\theta_{k} - \theta_e) + \Phi_{ciel} + H_{g,ei}(\theta_i - \theta_{ei,eq}) + \Phi_{fr}}"
              r"_{\text{sort}} = \Delta Q_{masse}"),
    lecture=("$\\Phi_{sol}$ : soleil transmis par les baies, les murs et la toiture. $\\Phi_{int}$ : occupants, "
             "appareils, éclairage. $\\Phi_{ch}$, $\\Phi_{fr}$ : chauffage et froid de l'émetteur conventionnel. "
             "$H_k (\\theta_k - \\theta_e)$ : chaleur qui traverse la paroi $k$ ou un pont thermique, vers "
             "la masse du logement pour les parois opaques et les ponts ($\\theta_k$ : température de la masse), "
             "vers les surfaces intérieures pour les baies ; "
             "$\\Phi_{ciel}$ : rayonnement froid vers la voûte céleste (toiture surtout). "
             "$H_{g,ei}(\\theta_i - \\theta_{ei,eq})$ : air renouvelé, de la ventilation, des infiltrations et des "
             "baies ouvertes. $\\Delta Q_{masse}$ : chaleur gardée par la masse sur la période, exacte : le "
             "bilan ferme.\n\n"
             "Ce qu'elle dit : réduire une sortie (mieux isoler) ou une entrée (protéger du soleil) déplace "
             "l'équilibre. En été, ce qui entre doit ressortir : la nuit, par les fenêtres ouvertes, ou rester "
             "dans la masse et faire monter la température."),
    reference=("arrêté du 4 août 2021, annexe III, fiche 5.21 (modèle du groupe) ; flux solaires, éq. 209 à 222, "
               "289 et 297 ; ponts thermiques, éq. 305 ; air, fiches 5.6, 5.13 et 6.1. Lecture du calcul : "
               "hypothèse 103 de docs/audit.md."),
    code=(postes_du_groupe, entrant, masse_gardee),
    besoin="",
    glossaire=("Inertie", "Conduction", "Ventilation", "Rayonnement"))
