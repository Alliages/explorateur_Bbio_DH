"""
============================================================
 FORMULAIRE — la saisie de la boîte, dans le menu de gauche
============================================================
 Un volet par thème ; chaque volet lit ses widgets et rend les
 champs de Boite (interface/saisie.py) qu'il renseigne. Les
 valeurs de départ sont celles de Boite() : il n'y a qu'un
 endroit où les changer.

 Ajouter une saisie : un champ dans Boite, puis un widget dans
 le volet qui convient (ou un nouveau volet dans VOLETS).
============================================================
"""

import streamlit as st

from config.reglages import ZONES_CLIMATIQUES
from interface.saisie import (DEBORD_MAX_M, FACADES, PART_VITREE_MAX, POINTS_CARDINAUX, SANS_PROTECTION, TEINTES,
                              Boite, point_cardinal)
from moteur.structures import EXPOSITIONS_BRUIT, GESTIONS_PROTECTION, INERTIES_QUOTIDIENNES, PROTECTIONS_MOBILES

# ============================================================
# RÉGLAGES : libellés des listes
# ============================================================
DEFAUT = Boite()
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


def _pourcent(libelle, valeur, cle, maxi=1.0, aide=None):
    """Curseur en pour cent, rendu en part (0 à 1)."""
    return st.slider(libelle, 0, round(maxi * 100), round(valeur * 100), step=5, format="%d %%", key=cle,
                     help=aide) / 100.0


# ============================================================
# VOLETS
# ============================================================
def _site():
    zone = st.selectbox("Zone climatique", ZONES_CLIMATIQUES, index=ZONES_CLIMATIQUES.index(DEFAUT.zone_climatique),
                        key="zone_climatique", help="Les huit zones de la RE2020, de H1a (nord) à H3 "
                        "(Méditerranée).")
    altitude = st.number_input("Altitude (m)", 0, 2500, round(DEFAUT.altitude_m), step=50, key="altitude_m")
    bruit = st.segmented_control("Exposition au bruit", list(LIBELLES_BRUIT), default=DEFAUT.exposition_bruit,
                                 format_func=LIBELLES_BRUIT.get, required=True, key="exposition_bruit",
                                 help="Près d'une voie bruyante, on ouvre moins les fenêtres la nuit.")
    return {"zone_climatique": zone, "altitude_m": float(altitude), "exposition_bruit": bruit}


def _forme():
    longueur = st.slider("Longueur de la façade principale (m)", 6.0, 60.0, DEFAUT.longueur_m, step=1.0,
                         key="longueur_m")
    profondeur = st.slider("Profondeur (m)", 6.0, 30.0, DEFAUT.profondeur_m, step=1.0, key="profondeur_m")
    niveaux = st.slider("Niveaux", 1, 10, DEFAUT.nb_niveaux, key="nb_niveaux")
    orientation = st.select_slider("Orientation de la façade principale", list(ORIENTATIONS),
                                   value=point_cardinal(DEFAUT.orientation_deg), key="orientation")
    logements = st.number_input("Logements", 1, 400, DEFAUT.nb_logements, key="nb_logements")
    traversant = st.toggle("Logements traversants", DEFAUT.traversant, key="traversant",
                           help="Un logement traversant ouvre sur deux façades : l'air le balaie mieux.")
    hsp = st.slider("Hauteur sous plafond (m)", 2.3, 3.5, DEFAUT.hauteur_sous_plafond_m, step=0.05,
                    key="hauteur_sous_plafond_m")
    return {"longueur_m": longueur, "profondeur_m": profondeur, "nb_niveaux": niveaux,
            "orientation_deg": float(ORIENTATIONS[orientation]), "nb_logements": int(logements),
            "traversant": traversant, "hauteur_sous_plafond_m": hsp,
            "hauteur_etage_m": max(DEFAUT.hauteur_etage_m, hsp + 0.3)}


def _baies(orientation_deg):
    champs = {}
    st.caption("Part vitrée de chaque façade")
    for cle, libelle, ecart, _ in FACADES:
        nom = f"{libelle} ({point_cardinal(orientation_deg + ecart)})"
        champs[f"part_vitree_{cle}"] = _pourcent(nom, getattr(DEFAUT, f"part_vitree_{cle}"), f"part_vitree_{cle}",
                                                 PART_VITREE_MAX)
    champs["uw"] = st.slider("Uw des baies (W/m².K)", 0.7, 3.0, DEFAUT.uw, step=0.1, key="uw",
                             help="Plus Uw est bas, moins la baie laisse passer de chaleur. Double vitrage "
                             "courant : 1,3 à 1,5.")
    champs["sw"] = st.slider("Facteur solaire Sw", 0.1, 0.8, DEFAUT.sw, step=0.05, key="sw",
                             help="Part de l'énergie du soleil qui entre par la baie nue.")
    champs["tl"] = st.slider("Transmission lumineuse", 0.1, 0.9, DEFAUT.tl, step=0.05, key="tl")
    protection = st.segmented_control("Protection mobile", list(LIBELLES_PROTECTION), default=DEFAUT.protection,
                                      format_func=LIBELLES_PROTECTION.get, required=True, key="protection")
    champs["protection"] = protection
    if protection != SANS_PROTECTION:
        champs["gestion_protection"] = st.selectbox("Gestion de la protection", list(LIBELLES_GESTION),
                                                    format_func=LIBELLES_GESTION.get, key="gestion_protection")
        champs["sw_protege"] = st.slider("Facteur solaire, protection baissée", 0.02, 0.5, DEFAUT.sw_protege,
                                         step=0.01, key="sw_protege")
        champs["uw_protege"] = st.slider("Uw, protection baissée (W/m².K)", 0.5, 3.0,
                                         min(DEFAUT.uw_protege, champs["uw"]), step=0.1, key="uw_protege")
    # Balcons ou casquettes : un débord au-dessus des baies, sur les façades choisies
    champs["debord_m"] = st.slider("Balcons ou casquettes : profondeur (m)", 0.0, DEBORD_MAX_M, DEFAUT.debord_m,
                                   step=0.1, key="debord_m",
                                   help="Dalle en débord au-dessus des baies, à chaque niveau. Elle arrête le "
                                   "soleil haut de l'été et laisse passer le soleil bas de l'hiver. 0 : aucune.")
    if champs["debord_m"] > 0:
        noms = {cle: f"{libelle} ({point_cardinal(orientation_deg + ecart)})" for cle, libelle, ecart, _ in FACADES}
        choisies = st.pills("Façades à balcons", list(noms), selection_mode="multi",
                            default=list(DEFAUT.facades_debord), format_func=noms.get, key="facades_debord")
        champs["facades_debord"] = tuple(cle for cle in noms if cle in choisies)      # dans l'ordre des façades
    champs["ouvrable"] = st.toggle("Baies ouvrables", DEFAUT.ouvrable, key="ouvrable")
    if champs["ouvrable"]:
        champs["ratio_ouverture_max"] = _pourcent("Part ouvrante de la baie", DEFAUT.ratio_ouverture_max,
                                                  "ratio_ouverture_max",
                                                  aide="Une fenêtre à la française ouvre presque toute sa "
                                                  "surface, un coulissant la moitié.")
    return champs


def _parois():
    u_mur = st.slider("U des murs (W/m².K)", 0.10, 1.50, DEFAUT.u_mur, step=0.05, key="u_mur")
    u_toiture = st.slider("U de la toiture (W/m².K)", 0.08, 1.00, DEFAUT.u_toiture, step=0.01, key="u_toiture")
    u_plancher = st.slider("U du plancher bas (W/m².K)", 0.10, 1.50, DEFAUT.u_plancher, step=0.05, key="u_plancher")
    sur_sol = st.toggle("Plancher bas sur le sol", DEFAUT.plancher_sur_sol, key="plancher_sur_sol",
                        help="Sinon, le plancher bas donne sur l'extérieur (pilotis, porche).")
    teinte = st.segmented_control("Teinte des murs et de la toiture", list(TEINTES), default=DEFAUT.teinte,
                                  format_func=str.capitalize, required=True, key="teinte",
                                  help="Une paroi sombre absorbe davantage le soleil.")
    psi = st.slider("Ponts thermiques des planchers (W/m.K)", 0.0, 1.0, DEFAUT.psi_planchers, step=0.05,
                    key="psi_planchers", help="Fuite de chaleur à la jonction de chaque plancher avec la façade, "
                    "par mètre de façade. Avec rupteur ou isolation par l'extérieur : 0,1 à 0,3.")
    inertie = st.select_slider("Inertie", list(LIBELLES_INERTIE), value=DEFAUT.inertie,
                               format_func=LIBELLES_INERTIE.get, key="inertie",
                               help="Capacité des planchers et des murs à stocker la chaleur du jour.")
    return {"u_mur": u_mur, "u_toiture": u_toiture, "u_plancher": u_plancher, "plancher_sur_sol": sur_sol,
            "teinte": teinte, "psi_planchers": psi, "inertie": inertie}


def _air():
    debit = st.slider("Ventilation (m³/h par m² habitable)", 0.3, 3.0, DEFAUT.debit_ventilation_m3h_m2, step=0.1,
                      key="debit_ventilation_m3h_m2")
    q4pa = st.slider("Perméabilité à l'air Q4Pa-surf (m³/h.m²)", 0.0, 3.0, DEFAUT.permeabilite_q4pa, step=0.1,
                     key="permeabilite_q4pa", help="Air qui passe par les défauts de l'enveloppe. 0 : enveloppe "
                     "parfaitement étanche (calcul deux fois plus rapide).")
    return {"debit_ventilation_m3h_m2": debit, "permeabilite_q4pa": q4pa}


def _confort():
    climatise = st.toggle("Logements climatisés", DEFAUT.climatise, key="climatise",
                          help="Ne change que le DH max : le DH se calcule toujours sans climatisation.")
    brasseurs = st.toggle("Brasseurs d'air de plafond", DEFAUT.brasseurs, key="brasseurs", disabled=climatise,
                          help="Non comptés dans un logement climatisé (fiche 8.32).")
    champs = {"climatise": climatise, "brasseurs": brasseurs and not climatise}
    if champs["brasseurs"]:
        champs["brasseurs_par_logement"] = st.slider("Brasseurs par logement", 1, 6, DEFAUT.brasseurs_par_logement,
                                                     key="brasseurs_par_logement")
        champs["brasseur_debit_m3h"] = float(st.number_input("Débit maximal d'un brasseur (m³/h)", 1000, 30000,
                                                             round(DEFAUT.brasseur_debit_m3h), step=500,
                                                             key="brasseur_debit_m3h"))
        champs["brasseur_puissance_w"] = float(st.number_input("Puissance maximale d'un brasseur (W)", 5, 200,
                                                               round(DEFAUT.brasseur_puissance_w), step=5,
                                                               key="brasseur_puissance_w"))
    return champs


def saisir():
    """Affiche les volets de saisie (à appeler dans le menu de gauche) et rend la Boite décrite."""
    champs = {}
    with st.expander("Site", icon=":material/location_on:"):
        champs.update(_site())
    with st.expander("Forme", icon=":material/deployed_code:", expanded=True):
        champs.update(_forme())
    with st.expander("Baies", icon=":material/window:"):
        champs.update(_baies(champs["orientation_deg"]))
    with st.expander("Parois", icon=":material/layers:"):
        champs.update(_parois())
    with st.expander("Air", icon=":material/air:"):
        champs.update(_air())
    with st.expander("Confort d'été", icon=":material/mode_fan:"):
        champs.update(_confort())
    return Boite(**champs)
