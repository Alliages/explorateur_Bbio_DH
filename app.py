"""
============================================================
 EXPLORATEUR Bbio / DH — point d'entrée Streamlit
============================================================
 Lancement local :  streamlit run app.py

 Deux pages : « Accueil », qui présente l'outil et ne calcule
 rien (interface/accueil.py, texte dans interface/textes/), et
 « Explorer », ouverte par le bouton de l'accueil ou par
 « Calculer ». La page « Explorer » tient en quatre gestes :
   1. partir d'un bâtiment (logement de 70 m² ou immeuble) et
      d'une enveloppe (performante, moyenne ou faible), puis les
      modifier dans le menu de gauche (interface/formulaire.py) ;
   2. le voir tourner et se vitrer aussitôt (interface/axonometrie.py) ;
   3. lancer le calcul (DH, Bbio ou les deux), puis lire les
      résultats brique par brique (interface/briques/) : le
      phénomène d'abord, l'équation, la référence et le code dans
      un volet ;
   4. garder des calculs en variantes (A à D, interface/variantes.py),
      changer une saisie et lire l'écart à la variante de référence
      (interface/comparaison.py), revenir à une variante d'un clic.
      Sans variante, les chiffres clés montrent l'écart avec le
      calcul précédent.

 Le dessin suit la saisie sans attendre ; le calcul (2 à 8 s
 chacun), lui, ne part qu'au bouton « Calculer ». Tant qu'il
 n'est pas relancé, les résultats affichés sont ceux de la saisie
 précédente, et la page le dit. Le Bbio et le DH sont gardés en
 mémoire séparément : ajouter l'un à l'autre ne relance que lui.

 Mise en page de « Explorer » (0.9.32), de haut en bas :
   barre des résultats   collée en haut quand la page défile : Bbio
                         et DH, écart, état périmé, « Calculer »,
                         pastilles des variantes (0.9.34) ;
   dessin | la boîte     le dessin à gauche ; à droite, sa surface,
                         la paroi examinée, sa fiche et ses saisies
                         (liées à celles du menu, 0.9.34) ;
   comparaison           le calcul affiché face à la référence ;
   synthèse              le Bbio et le DH côte à côte (0.9.34) ;
   briques               une à la fois, au choix.
 Dans le menu, « Calculer » reste collé en bas. Résultats périmés :
 la comparaison, la synthèse et les briques sont pâlies (STYLE_PERIME).

 Ce fichier ne fait qu'assembler : aucun calcul ici. Le moteur
 (moteur/) ne connaît pas l'interface.
============================================================
"""

import streamlit as st

from config.reglages import lire_version
from interface import (accueil, axonometrie, calcul, charte, comparaison, fiche_paroi, indicateurs, synthese,
                       variantes)
from interface.dessin_cliquable import dessin_cliquable, paroi_cliquee, vue_choisie
from interface.aides import aide
from interface.briques import BRIQUES
from interface.briques.base import montrer
from interface.briques.graphiques import nombre
from interface.formulaire import CHOIX_CALCULS, choisir_calculs, choisir_depart, remettre, saisir, saisir_dans_la_fiche
from interface.saisie import boite_de_depart, ecrire_batiment, point_cardinal

# ============================================================
# RÉGLAGES
# ============================================================
TITRE = "Explorateur Bbio / DH"
SOUS_TITRE = ("Recalculer, de façon approchée, le Bbio et les degrés-heures d'inconfort d'une boîte de logements, "
              "pour comprendre ce qui les fait bouger. Outil pédagogique, sans valeur réglementaire.")
DEPOT = "https://github.com/Alliages/explorateur_Bbio_DH"
CALCULS_GARDES = 24             # nombre de saisies dont chaque calcul reste en mémoire (0,7 Mo pour le DH)
LIBELLES_CALCULS = {"bbio": "du Bbio", "dh": "du DH"}
PAGE_ACCUEIL, PAGE_EXPLORER = "Accueil", "Explorer"
PAGES = {PAGE_ACCUEIL: ":material/home:", PAGE_EXPLORER: ":material/deployed_code:"}   # page → icône
DEPUIS = "depuis le calcul précédent"
FACE_REFERENCE = "face à {lettre}"    # écart à la variante de référence
FICHIER_BATIMENT = "03_mon_batiment.csv"    # nom proposé au téléchargement : se range après les deux fournis
# Styles de la page (clés des conteneurs : classe « st-key-<clé> ») :
#   - la barre des résultats reste sous l'en-tête de Streamlit (3,75 rem) quand la page défile ;
#   - « Calculer » reste en bas du menu de gauche, quel que soit le volet ouvert ;
#   - moins de marge au-dessus du titre (6 rem par défaut) : la hauteur va aux résultats.
# Streamlit enveloppe chaque conteneur d'un « stLayoutWrapper » de même hauteur : « sticky » se pose sur l'enveloppe.
STYLE = f"""<style>
[data-testid="stLayoutWrapper"]:has(> .st-key-barre_resultats) {{ position: sticky; top: 3.75rem; z-index: 100; }}
.st-key-barre_resultats {{ background: #FFFFFF; padding: 0.5rem 0 0.75rem;
    border-bottom: 1px solid {charte.BORDURE}; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-zone_calculer) {{ position: sticky; bottom: 0; z-index: 100; }}
.st-key-zone_calculer {{ background: {charte.FOND_SCHEMA}; padding: 0.75rem 0 1rem;
    border-top: 1px solid {charte.BORDURE}; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 3.5rem; }}
</style>"""
# Résultats périmés (la saisie a changé) : chiffres, comparaison, synthèse et briques pâlis, encore lisibles (contraste 5:1)
STYLE_PERIME = """<style>
[class*="st-key-chiffre_"], .st-key-comparaison, .st-key-synthese, .st-key-briques { opacity: 0.55; }
</style>"""

st.set_page_config(page_title=TITRE, page_icon=":material/deployed_code:", layout="wide")


# Un cache par calcul : revenir à une saisie déjà calculée est immédiat, et demander le Bbio en plus du DH ne
# relance pas le DH. Les fonctions sont lues dans le module calcul à chaque appel (les tests les remplacent).
@st.cache_data(max_entries=CALCULS_GARDES, show_spinner=False)
def _bbio(boite):
    return calcul.resultats_bbio(boite)


@st.cache_data(max_entries=CALCULS_GARDES, show_spinner=False)
def _dh(boite):
    return calcul.resultats_dh(boite)


@st.cache_data(max_entries=CALCULS_GARDES, show_spinner=False)
def _effet(boite, cle, calculs):
    """DH et Bbio sans la paroi « cle » (bouton « Mesurer l'effet de cette paroi » de la fiche)."""
    return calcul.effet_paroi(boite, cle, calculs)


def _calculer(boite, calculs):
    """Résultats des calculs demandés pour une boîte, chacun pris dans son cache."""
    parties = {"bbio": _bbio, "dh": _dh}
    champs = {}
    for nom in calculs:
        champs.update(parties[nom](boite))
    return calcul.Resultats(**champs)


def _retenir_calcul(boite, chiffres):
    """Garde les chiffres clés du calcul affiché et ceux du calcul d'avant, pour montrer l'écart entre eux.

    Un « calcul » est une boîte calculée : ajouter le Bbio au DH de la même boîte complète ses chiffres sans en
    faire un nouveau calcul. Rend les chiffres du calcul précédent ({} s'il n'y en a pas).
    """
    dernier = st.session_state.get("dernier_calcul")
    if dernier is None or dernier["boite"] != boite:
        st.session_state["calcul_precedent"] = dernier
        dernier = st.session_state["dernier_calcul"] = {"boite": boite, "chiffres": {}}
    dernier["chiffres"].update(chiffres)
    precedent = st.session_state.get("calcul_precedent")
    return precedent["chiffres"] if precedent else {}


def _ecart(valeur, avant, decimales, unite="", depuis=DEPUIS):
    """Texte de l'écart avec un autre calcul (le précédent, ou la référence : depuis=FACE_REFERENCE), pour le delta
    d'un st.metric ; None sans autre calcul.

    Le signe « - » en tête donne la flèche vers le bas ; un écart nul à l'arrondi s'écrit « inchangé ».
    """
    if avant is None:
        return None
    ecart = round(valeur - avant, decimales)
    if ecart == 0:
        return f"inchangé {depuis}"
    return f"{'-' if ecart < 0 else '+'}{nombre(abs(ecart), decimales, unite)} {depuis}"


def _part_du_max(nom, valeur, maximum, decimales, unite=""):
    """« 26 % au-dessus du Bbio max (91,0) », en rouge au-dessus du max, en vert en dessous."""
    ecart = (valeur / maximum - 1.0) * 100.0
    sens, couleur = ("au-dessus du", "red") if ecart > 0 else ("sous le", "green")
    return f":{couleur}[{nombre(abs(ecart), 0)} % {sens} {nom} max] ({nombre(maximum, decimales, unite)})"


# ============================================================
# 1. SAISIE (menu de gauche)
# ============================================================
if "boite_calculee" not in st.session_state:    # premier affichage : premier bâtiment, enveloppe moyenne, déjà calculé
    st.session_state["boite_calculee"] = boite_de_depart()
    st.session_state["calculs_lances"] = next(iter(CHOIX_CALCULS.values()))

st.html(STYLE)                                              # style seul : st.html ne prend aucune place
with st.sidebar:
    st.header("La boîte")
    depart = choisir_depart()
    calculs = choisir_calculs()
    boite = saisir(depart)
    # Bâtiment de départ et niveau d'enveloppe de la saisie : gardés avec le calcul, pour qu'une variante gardée
    # retrouve exactement sa boîte (ils donnent les champs non saisis)
    origine = (st.session_state["batiment_depart"], st.session_state["niveau_enveloppe"])
    st.session_state.setdefault("depart_calcule", origine)  # premier affichage : la boîte de départ
    # Calculer ouvre la page « Explorer » (le choix de page n'est pas encore affiché : on peut l'écrire)
    demande = {"boite_calculee": boite, "calculs_lances": calculs, "page": PAGE_EXPLORER, "depart_calcule": origine}
    deja_fait = boite == st.session_state["boite_calculee"] and calculs == st.session_state["calculs_lances"]
    # Sous les volets, collé en bas du menu (STYLE) : visible quel que soit le volet ouvert ou la saisie modifiée
    with st.container(key="zone_calculer"):
        if st.button("Calculer", type="primary", icon=":material/play_arrow:", width="stretch", key="calculer",
                     disabled=deja_fait):
            st.session_state.update(demande)
            st.rerun()                                      # le bouton se grise aussitôt : la saisie est à jour
        st.caption("Résultats à jour." if deja_fait else "Saisie modifiée : 2 à 8 s par calcul.")
    # La saisie en CSV de bâtiment, à déposer dans donnees/batiments/ (BOM : Excel l'ouvre avec ses accents)
    nom_variante = f"{st.session_state['batiment_depart']} (variante)"
    st.download_button("Télécharger ce bâtiment", ("﻿" + ecrire_batiment(boite, nom_variante)).encode("utf-8"),
                       file_name=FICHIER_BATIMENT, mime="text/csv", icon=":material/download:", width="stretch",
                       on_click="ignore", key="telecharger_batiment", help=aide("telecharger_batiment"))
    st.caption(f"Outil pédagogique, sans valeur réglementaire. Version {lire_version()} · licence GPL 3 · "
               f"[code source]({DEPOT})")

boite_calculee = st.session_state["boite_calculee"]
calculs_lances = st.session_state["calculs_lances"]
a_jour = boite == boite_calculee and calculs == calculs_lances

# ============================================================
# 2. EN-TÊTE ET CHOIX DE LA PAGE
# ============================================================
st.title(TITRE)
st.session_state.setdefault("page", PAGE_ACCUEIL)          # l'accueil à l'ouverture, comme Météo et Chaleur
page = st.segmented_control("Page", list(PAGES), key="page", required=True, label_visibility="collapsed",
                            format_func=lambda nom: f"{PAGES[nom]} {nom}")
if page == PAGE_ACCUEIL:                                    # l'accueil ne lance aucun calcul
    st.caption(SOUS_TITRE)                                  # « Explorer » garde la hauteur pour les résultats
    accueil.afficher(lambda: st.session_state.update(page=PAGE_EXPLORER))
    st.stop()

def _bilan_paroi(paroi, boite, boite_calculee, calculs_lances):
    """Ce que fait la paroi examinée, d'après le dernier calcul (lu en mémoire : aucun calcul de plus), et
    seulement si la saisie n'a pas changé depuis : sinon le bilan serait celui d'une autre boîte."""
    if boite != boite_calculee:
        st.caption("Cliquer sur « Calculer » pour lire ce que fait cette paroi.")
        return
    try:
        resultats = _calculer(boite_calculee, calculs_lances)
    except ValueError:                                      # message affiché plus bas, avec les résultats
        return
    periodes, lignes = fiche_paroi.bilan(resultats, paroi)
    if not periodes:                                        # paroi hors du groupe
        if paroi in boite.parois_adiabatiques:
            st.caption("Paroi adiabatique : elle n'échange rien avec l'extérieur.")
        return
    st.markdown("**Ce qu'elle fait**, d'après le calcul\n\n"
                f"| | {' | '.join(periodes)} |\n|---|{'---|' * len(periodes)}\n"
                + "\n".join(f"| {grandeur} | {' | '.join(valeurs)} |" for grandeur, valeurs in lignes),
                help=aide("bilan_paroi"))
    _effet_paroi(paroi, boite_calculee, calculs_lances, resultats)


def _effet_paroi(paroi, boite, calculs_lances, resultats):
    """Bouton « Mesurer l'effet de cette paroi » : DH et Bbio relancés sans elle (un calcul par indicateur, gardé en
    mémoire), comparés au calcul affiché. La demande est retenue tant que la paroi et la boîte ne changent pas."""
    demande = (boite, paroi, tuple(calculs_lances))
    if st.button("Mesurer l'effet de cette paroi", icon=":material/science:", key="effet_paroi",
                 help=aide("effet_paroi")):
        st.session_state["effet_demande"] = demande
    if st.session_state.get("effet_demande") != demande:
        return
    with st.spinner("Calcul sans cette paroi…"):
        effets = _effet(*demande)
    sans = ("baies remplacées par du mur" if paroi.startswith(axonometrie.PREFIXE_BAIES)
            else "paroi retirée, comme si elle était adiabatique")
    lignes = []
    if "dh" in effets and resultats.dh is not None:
        avec = resultats.dh["dh"]
        lignes.append(f"DH : {nombre(effets['dh'], 0, '°C.h')} au lieu de {nombre(avec, 0, '°C.h')} "
                      f"({_signe(effets['dh'] - avec, 0)})")
    if "bbio" in effets and resultats.bbio is not None:
        avec = resultats.bbio["bbio"]
        lignes.append(f"Bbio : {nombre(effets['bbio'], 1)} au lieu de {nombre(avec, 1)} "
                      f"({_signe(effets['bbio'] - avec, 1)})")
    st.markdown(f"**Sans cette paroi** ({sans}) :\n" + "\n".join(f"- {ligne}" for ligne in lignes))
    if (paroi.startswith(axonometrie.PREFIXE_BAIES) and resultats.dh is not None
            and effets.get("dh", 0.0) > resultats.dh["dh"]):
        st.caption("Le DH monte sans ces baies : elles font entrer le soleil, mais on les ouvre aussi pour "
                   "rafraîchir le logement, la nuit surtout. Le bilan en coupe montre ce que l'air des baies "
                   "ouvertes emporte.")


def _signe(ecart, decimales):
    """Écart signé, à la française (« + 12 », « − 3,5 »)."""
    return f"{'+' if ecart >= 0 else '−'} {nombre(abs(ecart), decimales)}"


def _choisir_indicateurs():
    """Boîte « Indicateurs » (au-dessus du dessin, elle s'ouvre par-dessus) : une case par indicateur du registre
    (interface/indicateurs.py) ; « Valider » change le cartouche du dessin. Rend les clés retenues."""
    retenus = st.session_state.setdefault("indicateurs", list(indicateurs.COCHES_D_OFFICE))
    with st.popover("Indicateurs", icon=":material/tune:", help=aide("indicateurs")):
        with st.form("choix_indicateurs", border=False):
            coches = {indicateur.cle: st.checkbox(indicateur.libelle, value=indicateur.cle in retenus,
                                                  key=f"case_{indicateur.cle}",
                                                  help=aide(indicateurs.PREFIXE_AIDE + indicateur.cle))
                      for indicateur in indicateurs.INDICATEURS}
            if st.form_submit_button("Valider", type="primary", key="valider_indicateurs"):
                retenus = [cle for cle, coche in coches.items() if coche]
                st.session_state["indicateurs"] = retenus
    return retenus


@st.fragment
def _dessin(boite, boite_calculee, calculs_lances):
    """Le dessin à gauche (heure du soleil et indicateurs au-dessus ; boussole des vues et cartouche des indicateurs
    dans ses coins) ; à droite, la boîte : sa surface, la paroi examinée et sa fiche ; dessous, sur toute la largeur,
    ce que fait la paroi (la boîte calculée). Un clic sur une paroi du dessin la choisit dans la liste, un clic sur
    la boussole change de vue. Fragment : changer de vue, d'heure ou de paroi ne redessine que lui, sans repasser
    par le calcul ni par les graphiques ; les deux colonnes sont dans le fragment, pour que la fiche suive le clic
    sur le dessin.
    Une saisie changée dans la fiche est recopiée dans le menu (formulaire.saisir_dans_la_fiche) : la page entière
    est alors relancée, pour que la boîte, le dessin et le menu la suivent."""
    if st.session_state.pop("saisie_par_la_fiche", False):
        st.rerun()                                          # portée « app » : tout repasse, menu compris
    colonne_dessin, colonne_boite = st.columns([3, 2], gap="large")
    with colonne_dessin:
        # Au-dessus du dessin : l'heure du soleil, et la boîte des indicateurs du cartouche. La vue se choisit
        # dans la boussole du dessin (session « vue », changée au clic)
        vue = st.session_state.setdefault("vue", "sud-ouest")
        colonne_heure, colonne_indicateurs = st.columns([4, 1], vertical_alignment="bottom")
        with colonne_heure:
            heure = st.select_slider("Heure du soleil, le 21 juin (heure légale)",
                                     options=axonometrie.HEURES_SOLEIL, value=int(axonometrie.SOLEIL_HEURE),
                                     key="heure_soleil", format_func=lambda h: f"{h} h", help=aide("heure_soleil"))
        with colonne_indicateurs:
            retenus = _choisir_indicateurs()
        dessin = st.container()
        plancher = " Plancher bas adiabatique, non visible." if "plancher_bas" in boite.parois_adiabatiques else ""
        # Légende courte ; la course du soleil et l'ombre sont dites dans l'aide « vue »
        st.caption("Dessin à l'échelle. En prune, la protection mobile ; en gris, les parois adiabatiques ; en "
                   "pointillé, la course du soleil le 21 juin. Survoler une paroi affiche ses valeurs, cliquer "
                   "dessus ouvre sa fiche ; cliquer sur un quart de la boussole change de vue." + plancher,
                   help=aide("vue"))

    # Paroi examinée : surlignée dans le dessin, avec sa fiche ; une paroi disparue de la boîte (baies d'une façade
    # passée à 0 % ou adiabatique) est oubliée avant d'afficher la liste
    choix = fiche_paroi.parois(boite)
    if st.session_state.get("paroi_examinee") not in choix:
        st.session_state.pop("paroi_examinee", None)
    with colonne_boite:
        surface_baies = sum(facade["baies_m2"] for facade in boite.facades())
        st.markdown(f"Surface habitable **{nombre(boite.surface_habitable_m2, 0, 'm²')}** · baies "
                    f"**{nombre(100 * surface_baies / boite.surface_habitable_m2, 0, '%')}** de la surface "
                    "habitable")
        paroi = st.selectbox("Paroi examinée", list(choix), index=None, format_func=choix.get,
                             key="paroi_examinee",
                             placeholder="Cliquer sur le dessin, ou choisir une façade, ses baies, la toiture ou "
                                         "le plancher bas",
                             help=aide("paroi_examinee"))
        if paroi is not None:
            projection = axonometrie.Projection(axonometrie.VUES[vue])
            cachee = "" if axonometrie.paroi_visible(boite, paroi, projection) else \
                " Cachée dans cette vue : son contour est en pointillé."
            # La fiche : d'abord ce que l'on peut changer ici, puis ce qui se lit
            st.markdown(f"**{choix[paroi]}**.{cachee}")
            saisir_dans_la_fiche(boite, paroi)
            st.markdown("| Grandeur | Valeur |\n|---|---|\n"
                        + "\n".join(f"| {grandeur} | {valeur} |"
                                    for grandeur, valeur in fiche_paroi.fiche(boite, paroi)))
    # Ce que fait la paroi : un tableau par période calculée, trop large pour la colonne de droite
    if paroi is not None:
        _bilan_paroi(paroi, boite, boite_calculee, calculs_lances)

    # SVG écrit dans la page par un composant (interface/dessin_cliquable.py) : infobulle de chaque paroi au
    # survol, clé de la paroi renvoyée au clic. Le rappel tourne avant le passage suivant du fragment : la paroi
    # cliquée est mise dans la liste avant qu'elle ne s'affiche
    def _clic():
        vue_cliquee = vue_choisie(st.session_state.get("dessin_axonometrie"))
        if vue_cliquee is not None:
            st.session_state["vue"] = vue_cliquee
            return
        cle = paroi_cliquee(st.session_state.get("dessin_axonometrie"), choix)
        if cle is not None:
            st.session_state["paroi_examinee"] = cle

    svg = axonometrie.dessiner(boite, axonometrie.VUES[vue], heure, surlignee=paroi,
                               infobulles=fiche_paroi.infobulles(boite),
                               cartouche=indicateurs.valeurs(boite, retenus))
    description = (f"Axonométrie de la boîte vue depuis le {vue}, façade principale au "
                   f"{point_cardinal(boite.orientation_deg)}, soleil du 21 juin à {heure} h ; cliquer sur une paroi "
                   "ouvre sa fiche, sur un quart de la boussole change de vue")
    with dessin:
        dessin_cliquable(svg, description, key="dessin_axonometrie", on_clic=_clic)


def _garder_variante(boite_calculee):
    """Rappel de « Garder » : le calcul affiché devient une variante (première lettre libre), avec le bâtiment de
    départ et le niveau d'enveloppe de ce calcul ; la première gardée devient la référence."""
    batiment, niveau = st.session_state["depart_calcule"]
    liste, _ = variantes.garder(st.session_state.get("variantes", []), boite_calculee, batiment, niveau)
    st.session_state["variantes"] = liste


def _remettre_variante(variante):
    """Rappel d'un clic sur une pastille : sa saisie revient dans le menu et son calcul (en mémoire) s'affiche."""
    remettre(variante["boite"], variante["batiment"], variante["niveau"])
    st.session_state.update(boite_calculee=variante["boite"], depart_calcule=(variante["batiment"],
                                                                                variante["niveau"]))


def _barre_resultats(resultats, resultats_reference, boite_calculee, liste, lettre_ref, chiffres_variantes):
    """Barre des résultats, collée en haut de la page (STYLE) : un chiffre clé par calcul lancé, avec l'écart à la
    variante de référence (ou, sans variante, au calcul précédent) et la part du max ; à droite, l'état, les
    boutons et les pastilles des variantes (interface/variantes.py).

    Chaque chiffre est dans un conteneur « chiffre_<nom> », pâli quand la saisie a changé (STYLE_PERIME).
    """
    chiffres = {}
    if resultats.bbio is not None:
        chiffres["bbio"] = resultats.bbio["bbio"]
    if resultats.dh is not None:
        chiffres["dh"] = resultats.dh["dh"]
    avant = _retenir_calcul(boite_calculee, chiffres)
    depuis = DEPUIS
    if resultats_reference is not None:                     # l'écart qui compte : celui avec la référence
        avant = {nom: getattr(resultats_reference, nom)[nom] for nom in chiffres}
        depuis = FACE_REFERENCE.format(lettre=lettre_ref)
    # (libellé, nom, clé, max, décimales, unité) ; l'unité du Bbio au libellé : 114,7 tient sur la ligne
    indicateurs = []
    if resultats.bbio is not None:
        indicateurs.append(("Bbio (points)", "Bbio", "bbio", resultats.bbio["bbio_max"], 1, ""))
    if resultats.dh is not None:
        indicateurs.append(("DH", "DH", "dh", resultats.dh["dh_max"], 0, "°C.h"))
    colonnes = st.columns([1] * len(indicateurs) + [1.6], gap="medium")
    for colonne, (libelle, nom, cle, maximum, decimales, unite) in zip(colonnes, indicateurs):
        with colonne, st.container(key=f"chiffre_{cle}"):
            st.metric(libelle, nombre(chiffres[cle], decimales, unite),
                      _ecart(chiffres[cle], avant.get(cle), decimales, unite, depuis), delta_color="inverse")
            st.markdown(_part_du_max(nom, chiffres[cle], maximum, decimales, unite))
    with colonnes[-1]:
        if not a_jour:
            st.warning("La saisie a changé : ces chiffres sont ceux du calcul précédent.", icon=":material/update:")
        boutons = st.container(horizontal=True)
        if not a_jour:
            # Second bouton, sous les yeux où que l'on soit dans la page (celui du menu est en bas du menu)
            boutons.button("Calculer", type="primary", icon=":material/play_arrow:", key="calculer_ici",
                           on_click=st.session_state.update, kwargs=demande)
        lettre_affichee = variantes.trouver(liste, boite_calculee)
        libres = [lettre for lettre in variantes.LETTRES if variantes.variante(liste, lettre) is None]
        if lettre_affichee is None and libres:
            # Saisie modifiée : le bouton garde le calcul affiché, celui d'avant la saisie, et le dit
            boutons.button(f"Garder en {libres[0]}" if a_jour else f"Garder le calcul affiché en {libres[0]}",
                           icon=":material/bookmark_add:", key="garder_variante", on_click=_garder_variante,
                           args=(boite_calculee,), help=aide("garder_variante"))
        variantes.afficher(liste, lettre_ref, chiffres_variantes, active=variantes.trouver(liste, boite),
                           remettre=_remettre_variante)
        if lettre_affichee is not None and lettre_affichee == lettre_ref:
            st.caption(f"Ce calcul est la référence {lettre_ref} : changer une saisie et calculer pour lire l'écart.")
        elif lettre_affichee is None and not libres:
            st.caption("Quatre variantes gardées : en retirer une (bouton à droite des pastilles) pour garder "
                       "celle-ci.")


# ============================================================
# 3. LA BARRE DES RÉSULTATS, LE DESSIN ET LA BOÎTE
# ============================================================
barre = st.container(key="barre_resultats")                 # remplie après le calcul, affichée en haut
_dessin(boite, boite_calculee, calculs_lances)

# ============================================================
# 4. CALCUL (le dessin est déjà affiché) ET CHIFFRES CLÉS
# ============================================================
liste_variantes = st.session_state.get("variantes", [])
lettre_ref = variantes.reference(liste_variantes, st.session_state.get("lettre_reference"))
st.session_state["lettre_reference"] = lettre_ref
reference = variantes.variante(liste_variantes, lettre_ref)["boite"] if lettre_ref else None
with barre:
    try:
        with st.spinner(f"Calcul {' et '.join(LIBELLES_CALCULS[nom] for nom in calculs_lances)}, heure par heure "
                        "sur une année…"):
            resultats = _calculer(boite_calculee, calculs_lances)
            # Les variantes passent par les mêmes calculs que la boîte affichée : immédiat s'ils sont en mémoire
            # (ajouter le Bbio au DH le calcule pour chacune)
            resultats_variantes = {v["lettre"]: _calculer(v["boite"], calculs_lances) for v in liste_variantes}
    except ValueError as erreur:                            # saisie incohérente : message du moteur, en clair
        st.error(str(erreur), title="Saisie à corriger", icon=":material/error:")
        st.stop()
    resultats_reference = resultats_variantes[lettre_ref] if reference not in (None, boite_calculee) else None
    chiffres_variantes = {lettre: {nom: getattr(r, nom)[nom] for nom in r.calculs()}
                          for lettre, r in resultats_variantes.items()}
    _barre_resultats(resultats, resultats_reference, boite_calculee, liste_variantes, lettre_ref, chiffres_variantes)
if not a_jour:
    st.html(STYLE_PERIME)

# ============================================================
# 5. COMPARAISON : la boîte calculée face à la variante de référence
# ============================================================
if resultats_reference is not None:
    with st.container(border=True, key="comparaison"):
        lettre_affichee = variantes.trouver(liste_variantes, boite_calculee)
        st.subheader(f"{lettre_affichee or 'Calcul affiché'} face à la référence {lettre_ref}")
        comparaison.afficher(reference, resultats_reference, boite_calculee, resultats)

# ============================================================
# 6. SYNTHÈSE ET BRIQUES : la synthèse avec le Bbio et le DH ; une brique à la fois, parmi celles des calculs lancés
# ============================================================
with st.container(key="synthese"):
    synthese.afficher(resultats, resultats_reference, lettre_ref,
                      variantes.trouver(liste_variantes, boite_calculee))
st.divider()
with st.container(key="briques"):
    briques = [brique for brique in BRIQUES if not brique.besoin or brique.besoin in calculs_lances]
    titres = {brique.cle: f"{brique.icone} {brique.titre}" for brique in briques}
    if st.session_state.get("brique") not in titres:        # brique d'un calcul qui n'est plus lancé
        st.session_state.pop("brique", None)
    choix = st.segmented_control("Comprendre", list(titres), default=briques[0].cle, format_func=titres.get,
                                 required=True, key="brique")
    montrer(next(brique for brique in briques if brique.cle == choix), resultats, boite_calculee)
