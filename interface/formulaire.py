"""
============================================================
 FORMULAIRE — la saisie de la boîte, dans le menu de gauche
============================================================
 En tête, trois choix : le bâtiment de départ (la forme), le
 niveau de l'enveloppe (performant, moyen ou faible) et le calcul
 à lancer (DH, Bbio ou les deux). Puis un volet par thème ;
 chaque volet lit ses widgets et rend les champs de Boite
 (interface/saisie.py) qu'il renseigne. Les valeurs de départ
 sont celles de boite_de_depart(bâtiment, niveau) :
   - changer de bâtiment donne à chaque widget sa valeur de départ ;
   - changer de niveau ne touche que les 13 widgets de
     l'enveloppe : la forme saisie est gardée.

 Ajouter une saisie : un champ dans Boite, puis un widget dans
 le volet qui convient, avec pour clé le nom du champ ; si le
 widget montre la valeur sous une autre forme (pour cent,
 entier), l'inscrire dans CHAMPS_EN_POURCENT ou CHAMPS_ENTIERS.
============================================================
"""

from dataclasses import fields, replace

import streamlit as st

from config.reglages import ZONES_CLIMATIQUES
from interface.saisie import (BATIMENTS_DE_DEPART, DEBORD_MAX_M, FACADES, NIVEAU_D_OUVERTURE, NIVEAUX_ENVELOPPE,
                              PART_VITREE_MAX, POINTS_CARDINAUX, SANS_PROTECTION, TEINTES, Boite, boite_de_depart,
                              point_cardinal)
from moteur.structures import EXPOSITIONS_BRUIT, GESTIONS_PROTECTION, INERTIES_QUOTIDIENNES, PROTECTIONS_MOBILES

# ============================================================
# RÉGLAGES : libellés des listes
# ============================================================
# Calculs proposés : libellé → calculs lancés (voir interface/calcul.py) ; le premier est le choix par défaut
CHOIX_CALCULS = {"DH": ("dh",), "Bbio": ("bbio",), "Bbio et DH": ("bbio", "dh")}
# Widgets de saisie : chacun a pour clé le nom de son champ de Boite, sauf l'orientation (clé « orientation »,
# saisie par son nom de point cardinal). Champs sans widget, et champs dont le widget montre une autre forme :
CHAMPS_NON_SAISIS = ("orientation_deg", "part_habitable", "hauteur_etage_m")
CHAMPS_EN_POURCENT = ("part_vitree_principale", "part_vitree_pignon_a", "part_vitree_arriere", "part_vitree_pignon_b",
                      "ratio_ouverture_max")
CHAMPS_ENTIERS = ("altitude_m", "brasseur_debit_m3h", "brasseur_puissance_w")
# Orientations proposées, d'est en ouest par le sud puis retour par le nord : nom → azimut du moteur
ORIENTATIONS = {nom: azimut for azimut, nom in sorted(POINTS_CARDINAUX, key=lambda p: (p[0] + 90) % 360)}
LIBELLES_PROTECTION = {SANS_PROTECTION: "Aucune", "volet": "Volets", "store_enroulable": "Stores enroulables"}
LIBELLES_GESTION = {"manuelle_non_motorisee": "Manuelle", "manuelle_motorisee": "Manuelle motorisée",
                    "automatique": "Automatique"}
LIBELLES_INERTIE = {"tres_legere": "Très légère", "legere": "Légère", "moyenne": "Moyenne", "lourde": "Lourde",
                    "tres_lourde": "Très lourde"}
LIBELLES_BRUIT = {"BR1": "BR1 (calme)", "BR2": "BR2", "BR3": "BR3 (bruyant)"}
assert set(LIBELLES_PROTECTION) == {SANS_PROTECTION, *PROTECTIONS_MOBILES}
assert set(LIBELLES_GESTION) == set(GESTIONS_PROTECTION) and set(LIBELLES_BRUIT) == set(EXPOSITIONS_BRUIT)
assert set(LIBELLES_INERTIE) <= set(INERTIES_QUOTIDIENNES)


def _pourcent(libelle, valeur, cle, maxi=1.0, aide=None, pas=5):
    """Curseur en pour cent, rendu en part (0 à 1)."""
    return st.slider(libelle, 0, round(maxi * 100), round(valeur * 100), step=pas, format="%d %%", key=cle,
                     help=aide) / 100.0


# ============================================================
# VOLETS
# ============================================================
def _site(defaut):
    zone = st.selectbox("Zone climatique", ZONES_CLIMATIQUES, index=ZONES_CLIMATIQUES.index(defaut.zone_climatique),
                        key="zone_climatique", help="Les huit zones de la RE2020, de H1a (nord) à H3 "
                        "(Méditerranée).")
    altitude = st.number_input("Altitude (m)", 0, 2500, round(defaut.altitude_m), step=50, key="altitude_m")
    bruit = st.segmented_control("Exposition au bruit", list(LIBELLES_BRUIT), default=defaut.exposition_bruit,
                                 format_func=LIBELLES_BRUIT.get, required=True, key="exposition_bruit",
                                 help="Près d'une voie bruyante, on ouvre moins les fenêtres la nuit.")
    return {"zone_climatique": zone, "altitude_m": float(altitude), "exposition_bruit": bruit}


def _forme(defaut):
    longueur = st.slider("Longueur de la façade principale (m)", 6.0, 60.0, defaut.longueur_m, step=1.0,
                         key="longueur_m")
    profondeur = st.slider("Profondeur (m)", 6.0, 30.0, defaut.profondeur_m, step=1.0, key="profondeur_m")
    niveaux = st.slider("Niveaux", 1, 10, defaut.nb_niveaux, key="nb_niveaux")
    orientation = st.select_slider("Orientation de la façade principale", list(ORIENTATIONS),
                                   value=point_cardinal(defaut.orientation_deg), key="orientation")
    logements = st.number_input("Logements", 1, 400, defaut.nb_logements, key="nb_logements")
    traversant = st.toggle("Logements traversants", defaut.traversant, key="traversant",
                           help="Un logement traversant ouvre sur deux façades : l'air le balaie mieux.")
    hsp = st.slider("Hauteur sous plafond (m)", 2.3, 3.5, defaut.hauteur_sous_plafond_m, step=0.05,
                    key="hauteur_sous_plafond_m")
    return {"longueur_m": longueur, "profondeur_m": profondeur, "nb_niveaux": niveaux,
            "orientation_deg": float(ORIENTATIONS[orientation]), "nb_logements": int(logements),
            "traversant": traversant, "hauteur_sous_plafond_m": hsp,
            "hauteur_etage_m": max(defaut.hauteur_etage_m, hsp + 0.3)}


def _baies(defaut, orientation_deg):
    champs = {}
    st.caption("Part vitrée de chaque façade")
    for cle, libelle, ecart, _ in FACADES:
        nom = f"{libelle} ({point_cardinal(orientation_deg + ecart)})"
        champs[f"part_vitree_{cle}"] = _pourcent(nom, getattr(defaut, f"part_vitree_{cle}"), f"part_vitree_{cle}",
                                                 PART_VITREE_MAX)
    # Pas des curseurs : assez fins pour les valeurs des niveaux d'enveloppe (donnees/typologies_logements.csv)
    champs["uw"] = st.slider("Uw des baies (W/m².K)", 0.7, 3.0, defaut.uw, step=0.05, key="uw",
                             help="Plus Uw est bas, moins la baie laisse passer de chaleur. Double vitrage "
                             "courant : 1,3 à 1,5.")
    champs["sw"] = st.slider("Facteur solaire Sw", 0.1, 0.8, defaut.sw, step=0.01, key="sw",
                             help="Part de l'énergie du soleil qui entre par la baie nue.")
    champs["tl"] = st.slider("Transmission lumineuse", 0.1, 0.9, defaut.tl, step=0.01, key="tl")
    protection = st.segmented_control("Protection mobile", list(LIBELLES_PROTECTION), default=defaut.protection,
                                      format_func=LIBELLES_PROTECTION.get, required=True, key="protection")
    champs["protection"] = protection
    if protection != SANS_PROTECTION:
        champs["gestion_protection"] = st.selectbox("Gestion de la protection", list(LIBELLES_GESTION),
                                                    index=list(LIBELLES_GESTION).index(defaut.gestion_protection),
                                                    format_func=LIBELLES_GESTION.get, key="gestion_protection")
        champs["sw_protege"] = st.slider("Facteur solaire, protection baissée", 0.02, 0.5, defaut.sw_protege,
                                         step=0.01, key="sw_protege")
        champs["uw_protege"] = st.slider("Uw, protection baissée (W/m².K)", 0.5, 3.0,
                                         min(defaut.uw_protege, champs["uw"]), step=0.05, key="uw_protege")
    # Balcons ou casquettes : un débord au-dessus des baies, sur les façades choisies
    champs["debord_m"] = st.slider("Balcons ou casquettes : profondeur (m)", 0.0, DEBORD_MAX_M, defaut.debord_m,
                                   step=0.1, key="debord_m",
                                   help="Dalle en débord au-dessus des baies, à chaque niveau. Elle arrête le "
                                   "soleil haut de l'été et laisse passer le soleil bas de l'hiver. 0 : aucune.")
    if champs["debord_m"] > 0:
        noms = {cle: f"{libelle} ({point_cardinal(orientation_deg + ecart)})" for cle, libelle, ecart, _ in FACADES}
        choisies = st.pills("Façades à balcons", list(noms), selection_mode="multi",
                            default=list(defaut.facades_debord), format_func=noms.get, key="facades_debord")
        champs["facades_debord"] = tuple(cle for cle in noms if cle in choisies)      # dans l'ordre des façades
    champs["ouvrable"] = st.toggle("Baies ouvrables", defaut.ouvrable, key="ouvrable")
    if champs["ouvrable"]:
        champs["ratio_ouverture_max"] = _pourcent("Part ouvrante de la baie", defaut.ratio_ouverture_max,
                                                  "ratio_ouverture_max", pas=1,
                                                  aide="Une fenêtre à la française ouvre presque toute sa "
                                                  "surface, un coulissant la moitié.")
    return champs


def _parois(defaut):
    u_mur = st.slider("U des murs (W/m².K)", 0.10, 1.50, defaut.u_mur, step=0.05, key="u_mur")
    u_toiture = st.slider("U de la toiture (W/m².K)", 0.08, 1.00, defaut.u_toiture, step=0.01, key="u_toiture")
    u_plancher = st.slider("U du plancher bas (W/m².K)", 0.10, 1.50, defaut.u_plancher, step=0.01, key="u_plancher")
    sur_sol = st.toggle("Plancher bas sur le sol", defaut.plancher_sur_sol, key="plancher_sur_sol",
                        help="Sinon, le plancher bas donne sur l'extérieur (pilotis, porche).")
    teinte = st.segmented_control("Teinte des murs et de la toiture", list(TEINTES), default=defaut.teinte,
                                  format_func=str.capitalize, required=True, key="teinte",
                                  help="Une paroi sombre absorbe davantage le soleil.")
    psi = st.slider("Ponts thermiques des planchers (W/m.K)", 0.0, 1.0, defaut.psi_planchers, step=0.01,
                    key="psi_planchers", help="Fuite de chaleur à la jonction de chaque plancher avec la façade, "
                    "par mètre de façade. Avec rupteur ou isolation par l'extérieur : 0,1 à 0,3. Les niveaux "
                    "d'enveloppe y placent le ψ moyen de tous les ponts thermiques des études.")
    inertie = st.select_slider("Inertie", list(LIBELLES_INERTIE), value=defaut.inertie,
                               format_func=LIBELLES_INERTIE.get, key="inertie",
                               help="Capacité des planchers et des murs à stocker la chaleur du jour.")
    return {"u_mur": u_mur, "u_toiture": u_toiture, "u_plancher": u_plancher, "plancher_sur_sol": sur_sol,
            "teinte": teinte, "psi_planchers": psi, "inertie": inertie}


def _air(defaut):
    debit = st.slider("Ventilation (m³/h par m² habitable)", 0.3, 3.0, defaut.debit_ventilation_m3h_m2, step=0.1,
                      key="debit_ventilation_m3h_m2")
    q4pa = st.slider("Perméabilité à l'air Q4Pa-surf (m³/h.m²)", 0.0, 3.0, defaut.permeabilite_q4pa, step=0.1,
                     key="permeabilite_q4pa", help="Air qui passe par les défauts de l'enveloppe. 0 : enveloppe "
                     "parfaitement étanche (calcul deux fois plus rapide).")
    return {"debit_ventilation_m3h_m2": debit, "permeabilite_q4pa": q4pa}


def _confort(defaut):
    climatise = st.toggle("Logements climatisés", defaut.climatise, key="climatise",
                          help="Ne change que le DH max : le DH se calcule toujours sans climatisation.")
    brasseurs = st.toggle("Brasseurs d'air de plafond", defaut.brasseurs, key="brasseurs", disabled=climatise,
                          help="Non comptés dans un logement climatisé (fiche 8.32).")
    champs = {"climatise": climatise, "brasseurs": brasseurs and not climatise}
    if champs["brasseurs"]:
        champs["brasseurs_par_logement"] = st.slider("Brasseurs par logement", 1, 6, defaut.brasseurs_par_logement,
                                                     key="brasseurs_par_logement")
        champs["brasseur_debit_m3h"] = float(st.number_input("Débit maximal d'un brasseur (m³/h)", 1000, 30000,
                                                             round(defaut.brasseur_debit_m3h), step=500,
                                                             key="brasseur_debit_m3h"))
        champs["brasseur_puissance_w"] = float(st.number_input("Puissance maximale d'un brasseur (W)", 5, 200,
                                                               round(defaut.brasseur_puissance_w), step=5,
                                                               key="brasseur_puissance_w"))
    return champs


# ============================================================
# CHOIX DE TÊTE ET SAISIE COMPLÈTE
# ============================================================
def valeurs_des_widgets(boite):
    """Valeur de chaque widget de saisie pour décrire cette boîte : clé du widget → valeur, sous la forme que
    le widget montre (pour cent, entier, nom du point cardinal, liste)."""
    valeurs = {}
    for champ in fields(Boite):
        if champ.name in CHAMPS_NON_SAISIS:
            continue
        valeur = getattr(boite, champ.name)
        if champ.name in CHAMPS_EN_POURCENT:
            valeur = round(valeur * 100)
        elif champ.name in CHAMPS_ENTIERS:
            valeur = round(valeur)
        elif isinstance(valeur, tuple):
            valeur = list(valeur)
        valeurs[champ.name] = valeur
    valeurs["orientation"] = point_cardinal(boite.orientation_deg)
    return valeurs


def _depart_choisi():
    """Boîte de départ des deux choix de tête, lus dans la session (appelée par leurs fonctions de rappel)."""
    return boite_de_depart(st.session_state.get("batiment_depart"),
                           st.session_state.get("niveau_enveloppe", NIVEAU_D_OUVERTURE))


def _reprendre_batiment():
    """Au changement de bâtiment : chaque widget prend sa valeur de départ (forme du bâtiment, enveloppe du niveau).

    Écrire la valeur, et non effacer la clé : un widget effacé garde à l'écran la valeur saisie.
    """
    st.session_state.update(valeurs_des_widgets(_depart_choisi()))


def _reprendre_niveau():
    """Au changement de niveau : seuls les widgets de l'enveloppe prennent les valeurs du niveau choisi."""
    valeurs = valeurs_des_widgets(_depart_choisi())
    st.session_state.update({cle: valeurs[cle] for cle in NIVEAUX_ENVELOPPE[st.session_state["niveau_enveloppe"]]})


def choisir_depart():
    """Listes « Bâtiment de départ » et « Enveloppe » ; rend la boîte de départ (valeurs initiales de la saisie)."""
    batiment = st.selectbox("Bâtiment de départ", list(BATIMENTS_DE_DEPART), key="batiment_depart",
                            on_change=_reprendre_batiment,
                            help="Choisir un bâtiment remet toutes les saisies à ses valeurs, avec l'enveloppe "
                            "du niveau choisi.")
    niveau = st.segmented_control("Enveloppe", list(NIVEAUX_ENVELOPPE), default=NIVEAU_D_OUVERTURE, required=True,
                                  key="niveau_enveloppe", on_change=_reprendre_niveau,
                                  help="Valeurs observées sur 18 zones de logements de 6 études RE2020, pondérées "
                                  "par la surface : « performant », le quart le mieux placé ; « moyen », la "
                                  "médiane ; « faible », le quart le moins bien placé. Choisir un niveau remet "
                                  "les 13 saisies d'enveloppe (baies, parois, ponts thermiques, inertie, "
                                  "ventilation, perméabilité) à ses valeurs et garde la forme.")
    return boite_de_depart(batiment, niveau)


def choisir_calculs():
    """Choix du calcul à lancer ; rend les calculs demandés (« bbio », « dh » ou les deux)."""
    choix = st.segmented_control("Calcul", list(CHOIX_CALCULS), default=next(iter(CHOIX_CALCULS)), required=True,
                                 key="choix_calculs",
                                 help="Chaque calcul prend à peu près le même temps : n'en lancer qu'un va deux "
                                 "fois plus vite.")
    return CHOIX_CALCULS[choix]


def saisir(defaut=boite_de_depart()):
    """Affiche les volets de saisie (à appeler dans le menu de gauche) et rend la Boite décrite.

    defaut : la boîte de départ (choisir_depart), qui donne la valeur initiale de chaque widget et les champs non
    saisis (part habitable).
    """
    champs = {}
    with st.expander("Site", icon=":material/location_on:"):
        champs.update(_site(defaut))
    with st.expander("Forme", icon=":material/deployed_code:", expanded=True):
        champs.update(_forme(defaut))
    with st.expander("Baies", icon=":material/window:"):
        champs.update(_baies(defaut, champs["orientation_deg"]))
    with st.expander("Parois", icon=":material/layers:"):
        champs.update(_parois(defaut))
    with st.expander("Air", icon=":material/air:"):
        champs.update(_air(defaut))
    with st.expander("Confort d'été", icon=":material/mode_fan:"):
        champs.update(_confort(defaut))
    return replace(defaut, **champs)
