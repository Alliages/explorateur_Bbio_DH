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
   4. garder un calcul comme référence, changer une saisie et lire
      l'écart (interface/comparaison.py). Sans référence, les
      chiffres clés montrent déjà l'écart avec le calcul précédent.

 Le dessin suit la saisie sans attendre ; le calcul (2 à 8 s
 chacun), lui, ne part qu'au bouton « Calculer ». Tant qu'il
 n'est pas relancé, les résultats affichés sont ceux de la saisie
 précédente, et la page le dit. Le Bbio et le DH sont gardés en
 mémoire séparément : ajouter l'un à l'autre ne relance que lui.

 Ce fichier ne fait qu'assembler : aucun calcul ici. Le moteur
 (moteur/) ne connaît pas l'interface.
============================================================
"""

import streamlit as st

from config.reglages import lire_version
from interface import accueil, axonometrie, calcul, comparaison, fiche_paroi
from interface.dessin_cliquable import dessin_cliquable, paroi_cliquee
from interface.aides import aide
from interface.briques import BRIQUES
from interface.briques.base import montrer
from interface.briques.graphiques import nombre
from interface.formulaire import CHOIX_CALCULS, choisir_calculs, choisir_depart, saisir
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
FICHIER_BATIMENT = "03_mon_batiment.csv"    # nom proposé au téléchargement : se range après les deux fournis

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


def _ecart_precedent(valeur, avant, decimales, unite=""):
    """Texte de l'écart avec le calcul précédent, pour le delta d'un st.metric ; None sans calcul précédent.

    Le signe « - » en tête donne la flèche vers le bas ; un écart nul à l'arrondi s'écrit « inchangé ».
    """
    if avant is None:
        return None
    ecart = round(valeur - avant, decimales)
    if ecart == 0:
        return f"inchangé {DEPUIS}"
    return f"{'-' if ecart < 0 else '+'}{nombre(abs(ecart), decimales, unite)} {DEPUIS}"


def _part_du_max(nom, valeur, maximum, decimales, unite=""):
    """« Bbio : 26 % au-dessus du max (91,0) », en rouge au-dessus du max, en vert en dessous."""
    ecart = (valeur / maximum - 1.0) * 100.0
    sens, couleur = ("au-dessus du", "red") if ecart > 0 else ("sous le", "green")
    return f"{nom} : :{couleur}[{nombre(abs(ecart), 0)} % {sens} {nom} max] ({nombre(maximum, decimales, unite)})"


# ============================================================
# 1. SAISIE (menu de gauche)
# ============================================================
if "boite_calculee" not in st.session_state:    # premier affichage : premier bâtiment, enveloppe moyenne, déjà calculé
    st.session_state["boite_calculee"] = boite_de_depart()
    st.session_state["calculs_lances"] = next(iter(CHOIX_CALCULS.values()))

with st.sidebar:
    st.header("La boîte")
    depart = choisir_depart()
    calculs = choisir_calculs()
    zone_bouton = st.container()                            # le bouton reste en haut, au-dessus des volets
    boite = saisir(depart)
    # Calculer ouvre la page « Explorer » (le choix de page n'est pas encore affiché : on peut l'écrire)
    demande = {"boite_calculee": boite, "calculs_lances": calculs, "page": PAGE_EXPLORER}
    deja_fait = boite == st.session_state["boite_calculee"] and calculs == st.session_state["calculs_lances"]
    if zone_bouton.button("Calculer", type="primary", icon=":material/play_arrow:", width="stretch",
                          key="calculer", disabled=deja_fait):
        st.session_state.update(demande)
        st.rerun()                                          # le bouton se grise aussitôt : la saisie est à jour
    # La saisie en CSV de bâtiment, à déposer dans donnees/batiments/ (BOM : Excel l'ouvre avec ses accents)
    nom_variante = f"{st.session_state['batiment_depart']} (variante)"
    st.download_button("Télécharger ce bâtiment", ("﻿" + ecrire_batiment(boite, nom_variante)).encode("utf-8"),
                       file_name=FICHIER_BATIMENT, mime="text/csv", icon=":material/download:", width="stretch",
                       on_click="ignore", key="telecharger_batiment", help=aide("telecharger_batiment"))
    st.caption(f"Version {lire_version()} · licence GPL 3 · [code source]({DEPOT})")

boite_calculee = st.session_state["boite_calculee"]
calculs_lances = st.session_state["calculs_lances"]
a_jour = boite == boite_calculee and calculs == calculs_lances

# ============================================================
# 2. LA BOÎTE DESSINÉE ET SES CHIFFRES
# ============================================================
st.title(TITRE)
st.caption(SOUS_TITRE)
st.session_state.setdefault("page", PAGE_ACCUEIL)          # l'accueil à l'ouverture, comme Météo et Chaleur
page = st.segmented_control("Page", list(PAGES), key="page", required=True, label_visibility="collapsed",
                            format_func=lambda nom: f"{PAGES[nom]} {nom}")
if page == PAGE_ACCUEIL:                                    # l'accueil ne lance aucun calcul
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


@st.fragment
def _dessin(boite, boite_calculee, calculs_lances):
    """Axonométrie, avec le choix de la vue au-dessus, l'heure du soleil et la paroi examinée (sa fiche et, la
    boîte calculée, ce qu'elle fait) au-dessous ; un clic sur une paroi du dessin la choisit dans la liste.
    Fragment : changer de vue, d'heure ou de paroi ne redessine que lui, sans repasser par le calcul ni par les
    graphiques."""
    vue = st.segmented_control("Vue depuis le", list(axonometrie.VUES), default="sud-ouest", required=True,
                               key="vue")
    dessin = st.container()                                 # le dessin au-dessus du curseur qui le règle
    heure = st.select_slider("Heure du soleil, le 21 juin (heure légale)", options=axonometrie.HEURES_SOLEIL,
                             value=int(axonometrie.SOLEIL_HEURE), key="heure_soleil",
                             format_func=lambda h: f"{h} h", help=aide("heure_soleil"))
    plancher = " Le plancher bas, adiabatique, n'est pas visible." if "plancher_bas" in boite.parois_adiabatiques \
        else ""
    st.caption("Dessin à l'échelle : les baies ont la surface saisie. En prune, la protection mobile ; en gris, "
               "les parois adiabatiques. En pointillé, la course du soleil le 21 juin, du lever au nord-est au "
               "coucher au nord-ouest (un point toutes les deux heures), dans le ciel et portée au bord du sol ; "
               "le soleil de l'heure choisie est à sa hauteur, avec l'ombre de la boîte et ses façades à "
               "l'ombre, plus sombres. Survoler un mur, une baie ou la toiture affiche ses valeurs ; cliquer dessus "
               "ouvre sa fiche." + plancher)
    # Paroi examinée : surlignée dans le dessin, avec sa fiche ; une paroi disparue de la boîte (baies d'une façade
    # passée à 0 % ou adiabatique) est oubliée avant d'afficher la liste
    choix = fiche_paroi.parois(boite)
    if st.session_state.get("paroi_examinee") not in choix:
        st.session_state.pop("paroi_examinee", None)
    paroi = st.selectbox("Paroi examinée", list(choix), index=None, format_func=choix.get, key="paroi_examinee",
                         placeholder="Cliquer sur le dessin, ou choisir une façade, ses baies, la toiture ou le "
                                     "plancher bas",
                         help=aide("paroi_examinee"))
    if paroi is not None:
        projection = axonometrie.Projection(axonometrie.VUES[vue])
        cachee = "" if axonometrie.paroi_visible(boite, paroi, projection) else \
            " Cachée dans cette vue : son contour est en pointillé."
        st.markdown(f"**{choix[paroi]}**.{cachee}\n\n| Grandeur | Valeur |\n|---|---|\n"
                    + "\n".join(f"| {grandeur} | {valeur} |" for grandeur, valeur in fiche_paroi.fiche(boite, paroi)))
        _bilan_paroi(paroi, boite, boite_calculee, calculs_lances)
    # SVG écrit dans la page par un composant (interface/dessin_cliquable.py) : infobulle de chaque paroi au
    # survol, clé de la paroi renvoyée au clic. Le rappel tourne avant le passage suivant du fragment : la paroi
    # cliquée est mise dans la liste avant qu'elle ne s'affiche
    def _clic():
        cle = paroi_cliquee(st.session_state.get("dessin_axonometrie"), choix)
        if cle is not None:
            st.session_state["paroi_examinee"] = cle

    svg = axonometrie.dessiner(boite, axonometrie.VUES[vue], heure, surlignee=paroi,
                               infobulles=fiche_paroi.infobulles(boite))
    description = (f"Axonométrie de la boîte, façade principale au {point_cardinal(boite.orientation_deg)}, "
                   f"soleil du 21 juin à {heure} h ; cliquer sur une paroi ouvre sa fiche")
    with dessin:
        dessin_cliquable(svg, description, key="dessin_axonometrie", on_clic=_clic)


colonne_dessin, colonne_chiffres = st.columns([3, 2], gap="large")
with colonne_dessin:
    _dessin(boite, boite_calculee, calculs_lances)

with colonne_chiffres:
    st.subheader("Chiffres clés")
    surface_baies = sum(facade["baies_m2"] for facade in boite.facades())
    geometrie = st.columns(2)
    geometrie[0].metric("Surface habitable", nombre(boite.surface_habitable_m2, 0, "m²"))
    geometrie[1].metric("Baies / surface habitable", nombre(100 * surface_baies / boite.surface_habitable_m2, 0, "%"))
    zone_resultats = st.container()

# ============================================================
# 3. CALCUL (les éléments rapides sont déjà affichés)
# ============================================================
try:
    with st.spinner(f"Calcul {' et '.join(LIBELLES_CALCULS[nom] for nom in calculs_lances)}, heure par heure "
                    "sur une année…"):
        resultats = _calculer(boite_calculee, calculs_lances)
except ValueError as erreur:                                # saisie incohérente : message du moteur, en clair
    st.error(str(erreur), title="Saisie à corriger", icon=":material/error:")
    st.stop()

with zone_resultats:
    # Un chiffre clé par calcul lancé ; sous chacun, l'écart avec le calcul précédent ; en dessous, la part du max
    chiffres = {}
    if resultats.bbio is not None:
        chiffres["bbio"] = resultats.bbio["bbio"]
    if resultats.dh is not None:
        chiffres["dh"] = resultats.dh["dh"]
    avant = _retenir_calcul(boite_calculee, chiffres)
    cles = st.columns(2)
    parts_du_max = []
    if resultats.bbio is not None:
        cles[0].metric("Bbio (points)", nombre(resultats.bbio["bbio"], 1),      # unité au libellé : 114,7 tient
                       _ecart_precedent(resultats.bbio["bbio"], avant.get("bbio"), 1), delta_color="inverse")
        parts_du_max.append(_part_du_max("Bbio", resultats.bbio["bbio"], resultats.bbio["bbio_max"], 1))
    if resultats.dh is not None:
        cles[len(resultats.calculs()) - 1].metric(
            "DH", nombre(resultats.dh["dh"], 0, "°C.h"),
            _ecart_precedent(resultats.dh["dh"], avant.get("dh"), 0, "°C.h"), delta_color="inverse")
        parts_du_max.append(_part_du_max("DH", resultats.dh["dh"], resultats.dh["dh_max"], 0, "°C.h"))
    st.markdown("  \n".join(parts_du_max))
    if not a_jour:
        st.warning("La saisie a changé : ces résultats sont ceux du calcul précédent.", icon=":material/update:")
        # Second bouton, sous les yeux : celui du menu de gauche disparaît quand on fait défiler les volets
        st.button("Calculer", type="primary", icon=":material/play_arrow:", key="calculer_ici",
                  on_click=st.session_state.update, kwargs=demande)
    reference = st.session_state.get("reference")
    st.button("Garder comme référence", icon=":material/bookmark:", key="garder_reference",
              disabled=reference == boite_calculee, on_click=st.session_state.update,
              kwargs={"reference": boite_calculee}, help=aide("garder_reference"))

# ============================================================
# 4. COMPARAISON : la boîte calculée face à la référence gardée
# ============================================================
if reference == boite_calculee:
    st.info("Ce calcul est la référence. Changer une saisie et cliquer sur « Calculer » pour lire l'écart.",
            icon=":material/bookmark:")
elif reference is not None:
    with st.container(border=True):
        titre_comparaison, oublier = st.columns([4, 1], vertical_alignment="center")
        titre_comparaison.subheader("Variante face à la référence")
        oublier.button("Oublier la référence", icon=":material/bookmark_remove:", key="oublier_reference",
                       on_click=st.session_state.pop, args=("reference", None), width="stretch")
        # La référence passe par les mêmes calculs que la variante : immédiat s'ils sont en mémoire
        with st.spinner("Calcul de la référence…"):
            resultats_reference = _calculer(reference, calculs_lances)
        comparaison.afficher(reference, resultats_reference, boite_calculee, resultats)

# ============================================================
# 5. BRIQUES : une seule est affichée à la fois, parmi celles des calculs lancés
# ============================================================
st.divider()
briques = [brique for brique in BRIQUES if not brique.besoin or brique.besoin in calculs_lances]
titres = {brique.cle: f"{brique.icone} {brique.titre}" for brique in briques}
if st.session_state.get("brique") not in titres:            # brique d'un calcul qui n'est plus lancé
    st.session_state.pop("brique", None)
choix = st.segmented_control("Comprendre", list(titres), default=briques[0].cle, format_func=titres.get,
                             required=True, key="brique")
montrer(next(brique for brique in briques if brique.cle == choix), resultats, boite_calculee)
