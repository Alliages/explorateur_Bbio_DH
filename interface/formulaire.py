"""
============================================================
 FORMULAIRE — la saisie de la boîte, dans le menu de gauche
============================================================
 En tête, trois choix : le bâtiment de départ (la forme), le
 niveau de l'enveloppe (performant, moyen ou faible) et le calcul
 à lancer (DH, Bbio ou les deux). Puis un volet par thème, dont
 le titre résume les valeurs (resumes) ; chaque volet lit ses
 widgets et rend les champs de Boite
 (interface/saisie.py) qu'il renseigne. Les valeurs de départ
 sont celles de boite_de_depart(bâtiment, niveau) :
   - changer de bâtiment donne à chaque widget sa valeur de départ ;
   - changer de niveau ne touche que les 13 widgets de
     l'enveloppe : la forme saisie est gardée.

 Ajouter une saisie : un champ dans Boite, puis un widget dans
 le volet qui convient, avec pour clé le nom du champ ; si le
 widget montre la valeur sous une autre forme (pour cent,
 entier), l'inscrire dans CHAMPS_EN_POURCENT ou CHAMPS_ENTIERS.
 Son aide (bulle « ? ») s'écrit dans interface/textes/aides.csv,
 sur une ligne qui porte la clé du widget : help=aide(clé).
============================================================
"""

from dataclasses import fields, replace

import streamlit as st

from config.reglages import ZONES_CLIMATIQUES
from interface.aides import aide
from interface.axonometrie import PREFIXE_BAIES
from interface.saisie import (BATIMENTS_DE_DEPART, DEBORD_MAX_M, FACADES, NIVEAU_D_OUVERTURE, NIVEAUX_ENVELOPPE,
                              PAROIS_ADIABATIQUES, PART_VITREE_MAX, PAS_ORIENTATION_DEG, SANS_PROTECTION, TEINTES,
                              Boite, azimut_geographique, boite_de_depart, libelle_orientation, orientation_moteur,
                              point_cardinal)
from moteur.structures import EXPOSITIONS_BRUIT, GESTIONS_PROTECTION, INERTIES_QUOTIDIENNES, PROTECTIONS_MOBILES

# ============================================================
# RÉGLAGES : libellés des listes
# ============================================================
# Calculs proposés : libellé → calculs lancés (voir interface/calcul.py) ; le premier est le choix par défaut
CHOIX_CALCULS = {"DH": ("dh",), "Bbio": ("bbio",), "Bbio et DH": ("bbio", "dh")}
# Widgets de saisie : chacun a pour clé le nom de son champ de Boite, sauf l'orientation (clé « orientation »,
# saisie en azimut géographique, en degrés entiers). Champs sans widget, et champs dont le widget montre une autre
# forme :
CHAMPS_NON_SAISIS = ("orientation_deg", "part_habitable", "hauteur_etage_m")
CHAMPS_EN_POURCENT = ("part_vitree_principale", "part_vitree_pignon_a", "part_vitree_arriere", "part_vitree_pignon_b",
                      "ratio_ouverture_max")
CHAMPS_ENTIERS = ("altitude_m", "brasseur_debit_m3h", "brasseur_puissance_w")
# Orientations proposées : azimut géographique, du nord (0°) par l'est (90°), le sud (180°) et l'ouest (270°)
ORIENTATIONS = list(range(0, 360, PAS_ORIENTATION_DEG))
LIBELLES_PROTECTION = {SANS_PROTECTION: "Aucune", "volet": "Volets", "store_enroulable": "Stores enroulables"}
LIBELLES_GESTION = {"manuelle_non_motorisee": "Manuelle", "manuelle_motorisee": "Manuelle motorisée",
                    "automatique": "Automatique"}
LIBELLES_INERTIE = {"tres_legere": "Très légère", "legere": "Légère", "moyenne": "Moyenne", "lourde": "Lourde",
                    "tres_lourde": "Très lourde"}
LIBELLES_BRUIT = {"BR1": "BR1 (calme)", "BR2": "BR2", "BR3": "BR3 (bruyant)"}
assert set(LIBELLES_PROTECTION) == {SANS_PROTECTION, *PROTECTIONS_MOBILES}
assert set(LIBELLES_GESTION) == set(GESTIONS_PROTECTION) and set(LIBELLES_BRUIT) == set(EXPOSITIONS_BRUIT)
assert set(LIBELLES_INERTIE) <= set(INERTIES_QUOTIDIENNES)
# Curseurs repris dans la fiche de la paroi : champ → (libellé, minimum, maximum, pas). Les pas sont assez fins
# pour les valeurs des niveaux d'enveloppe (donnees/typologies_logements.csv)
CURSEURS = {"uw": ("Uw des baies (W/m².K)", 0.7, 3.0, 0.05),
            "sw": ("Facteur solaire Sw", 0.1, 0.8, 0.01),
            "u_mur": ("U des murs (W/m².K)", 0.10, 1.50, 0.05),
            "u_toiture": ("U de la toiture (W/m².K)", 0.08, 1.00, 0.01),
            "u_plancher": ("U du plancher bas (W/m².K)", 0.10, 1.50, 0.01)}
# Saisies de la fiche, par sorte de paroi (« {facade} » : la façade de la paroi), et ce que couvre une saisie
# commune à plusieurs parois (la boîte n'a qu'un Uw, qu'un U de mur…)
SAISIES_FICHE = {"baies": ("part_vitree_{facade}", "uw", "sw", "protection"),
                 "facade": ("part_vitree_{facade}", "u_mur", "teinte"),
                 "toiture": ("u_toiture", "teinte"),
                 "plancher_bas": ("u_plancher", "plancher_sur_sol")}
SAISIES_COMMUNES = {"uw": "toutes les baies", "sw": "toutes les baies", "protection": "toutes les baies",
                    "u_mur": "tous les murs", "teinte": "murs et toiture"}
CLES_FACADES = tuple(cle for cle, _, _, _ in FACADES)
PREFIXE_FICHE = "fiche_"        # clé d'une saisie de la fiche : « fiche_uw » (celle du menu : « uw »)
# Volets du menu, dans l'ordre : titre → suffixe de leur clé (« volet_baies »)
VOLETS = {"Site": "site", "Forme": "forme", "Baies": "baies", "Parois": "parois", "Air": "air",
          "Confort d'été": "confort"}


def _pourcent(libelle, valeur, cle, maxi=1.0, pas=5, desactive=False):
    """Curseur en pour cent, rendu en part (0 à 1)."""
    return st.slider(libelle, 0, round(maxi * 100), round(valeur * 100), step=pas, format="%d %%", key=cle,
                     help=aide(cle), disabled=desactive) / 100.0


def _curseur(champ, defaut, desactive=False):
    """Curseur d'un champ de CURSEURS, dans le menu (clé : le nom du champ)."""
    libelle, mini, maxi, pas = CURSEURS[champ]
    return st.slider(libelle, mini, maxi, getattr(defaut, champ), step=pas, key=champ, help=aide(champ),
                     disabled=desactive)


# ============================================================
# VOLETS
# ============================================================
def _site(defaut):
    zone = st.selectbox("Zone climatique", ZONES_CLIMATIQUES, index=ZONES_CLIMATIQUES.index(defaut.zone_climatique),
                        key="zone_climatique", help=aide("zone_climatique"))
    altitude = st.number_input("Altitude (m)", 0, 2500, round(defaut.altitude_m), step=50, key="altitude_m",
                               help=aide("altitude_m"))
    bruit = st.segmented_control("Exposition au bruit", list(LIBELLES_BRUIT), default=defaut.exposition_bruit,
                                 format_func=LIBELLES_BRUIT.get, required=True, key="exposition_bruit",
                                 help=aide("exposition_bruit"))
    return {"zone_climatique": zone, "altitude_m": float(altitude), "exposition_bruit": bruit}


def _forme(defaut):
    longueur = st.slider("Longueur de la façade principale (m)", 6.0, 60.0, defaut.longueur_m, step=1.0,
                         key="longueur_m", help=aide("longueur_m"))
    profondeur = st.slider("Profondeur (m)", 6.0, 30.0, defaut.profondeur_m, step=1.0, key="profondeur_m",
                           help=aide("profondeur_m"))
    niveaux = st.slider("Niveaux", 1, 10, defaut.nb_niveaux, key="nb_niveaux", help=aide("nb_niveaux"))
    azimut = st.select_slider("Orientation de la façade principale", ORIENTATIONS,
                              value=_azimut_du_curseur(defaut.orientation_deg), key="orientation",
                              format_func=lambda a: libelle_orientation(orientation_moteur(a)),
                              help=aide("orientation"))
    orientation_deg = orientation_moteur(azimut)
    # Parois sur un local chauffé (mitoyenneté, logement voisin) : sans échange, grises dans le dessin
    noms = {cle: f"{libelle} ({point_cardinal(orientation_deg + ecart)})" for cle, libelle, ecart, _ in FACADES}
    noms.update({cle: libelle for cle, libelle in PAROIS_ADIABATIQUES.items() if cle not in noms})
    adiabatiques = st.pills("Parois adiabatiques (sur un local chauffé)", list(noms), selection_mode="multi",
                            default=list(defaut.parois_adiabatiques), format_func=noms.get,
                            key="parois_adiabatiques", help=aide("parois_adiabatiques"))
    logements = st.number_input("Logements", 1, 400, defaut.nb_logements, key="nb_logements", help=aide("nb_logements"))
    traversant = st.toggle("Logements traversants", defaut.traversant, key="traversant", help=aide("traversant"))
    hsp = st.slider("Hauteur sous plafond (m)", 2.3, 3.5, defaut.hauteur_sous_plafond_m, step=0.05,
                    key="hauteur_sous_plafond_m", help=aide("hauteur_sous_plafond_m"))
    return {"longueur_m": longueur, "profondeur_m": profondeur, "nb_niveaux": niveaux,
            "orientation_deg": orientation_deg, "nb_logements": int(logements),
            "parois_adiabatiques": tuple(cle for cle in noms if cle in adiabatiques),   # dans l'ordre des parois
            "traversant": traversant, "hauteur_sous_plafond_m": hsp,
            "hauteur_etage_m": max(defaut.hauteur_etage_m, hsp + 0.3)}


def _azimut_du_curseur(orientation_deg):
    """Position du curseur d'orientation la plus proche d'une orientation du moteur : azimut géographique arrondi
    au pas du curseur (un bâtiment de départ peut donner une orientation hors du pas)."""
    return round(azimut_geographique(orientation_deg) / PAS_ORIENTATION_DEG) * PAS_ORIENTATION_DEG % 360


def _baies(defaut, orientation_deg, adiabatiques):
    champs = {}
    st.caption("Part vitrée de chaque façade (aucune baie sur une façade adiabatique)")
    for cle, libelle, ecart, _ in FACADES:
        nom = f"{libelle} ({point_cardinal(orientation_deg + ecart)})"
        champs[f"part_vitree_{cle}"] = _pourcent(nom, getattr(defaut, f"part_vitree_{cle}"), f"part_vitree_{cle}",
                                                 PART_VITREE_MAX, desactive=cle in adiabatiques)
    champs["uw"] = _curseur("uw", defaut)
    champs["sw"] = _curseur("sw", defaut)
    champs["tl"] = st.slider("Transmission lumineuse", 0.1, 0.9, defaut.tl, step=0.01, key="tl", help=aide("tl"))
    protection = st.segmented_control("Protection mobile", list(LIBELLES_PROTECTION), default=defaut.protection,
                                      format_func=LIBELLES_PROTECTION.get, required=True, key="protection",
                                      help=aide("protection"))
    champs["protection"] = protection
    if protection != SANS_PROTECTION:
        champs["gestion_protection"] = st.selectbox("Gestion de la protection", list(LIBELLES_GESTION),
                                                    index=list(LIBELLES_GESTION).index(defaut.gestion_protection),
                                                    format_func=LIBELLES_GESTION.get, key="gestion_protection",
                                                    help=aide("gestion_protection"))
        champs["sw_protege"] = st.slider("Facteur solaire, protection baissée", 0.02, 0.5, defaut.sw_protege,
                                         step=0.01, key="sw_protege", help=aide("sw_protege"))
        champs["uw_protege"] = st.slider("Uw, protection baissée (W/m².K)", 0.5, 3.0,
                                         min(defaut.uw_protege, champs["uw"]), step=0.05, key="uw_protege",
                                         help=aide("uw_protege"))
    # Balcons ou casquettes : un débord au-dessus des baies, sur les façades choisies
    champs["debord_m"] = st.slider("Balcons ou casquettes : profondeur (m)", 0.0, DEBORD_MAX_M, defaut.debord_m,
                                   step=0.1, key="debord_m", help=aide("debord_m"))
    if champs["debord_m"] > 0:
        noms = {cle: f"{libelle} ({point_cardinal(orientation_deg + ecart)})" for cle, libelle, ecart, _ in FACADES}
        choisies = st.pills("Façades à balcons", list(noms), selection_mode="multi",
                            default=list(defaut.facades_debord), format_func=noms.get, key="facades_debord")
        champs["facades_debord"] = tuple(cle for cle in noms if cle in choisies)      # dans l'ordre des façades
    champs["ouvrable"] = st.toggle("Baies ouvrables", defaut.ouvrable, key="ouvrable", help=aide("ouvrable"))
    if champs["ouvrable"]:
        champs["ratio_ouverture_max"] = _pourcent("Part ouvrante de la baie", defaut.ratio_ouverture_max,
                                                  "ratio_ouverture_max", pas=1)
    return champs


def _parois(defaut, adiabatiques):
    # Une toiture ou un plancher bas adiabatique n'échange rien : ses saisies restent visibles mais sans effet
    u_mur = _curseur("u_mur", defaut)
    u_toiture = _curseur("u_toiture", defaut, desactive="toiture" in adiabatiques)
    u_plancher = _curseur("u_plancher", defaut, desactive="plancher_bas" in adiabatiques)
    sur_sol = st.toggle("Plancher bas sur le sol", defaut.plancher_sur_sol, key="plancher_sur_sol",
                        help=aide("plancher_sur_sol"), disabled="plancher_bas" in adiabatiques)
    teinte = st.segmented_control("Teinte des murs et de la toiture", list(TEINTES), default=defaut.teinte,
                                  format_func=str.capitalize, required=True, key="teinte", help=aide("teinte"))
    psi = st.slider("Ponts thermiques des planchers (W/m.K)", 0.0, 1.0, defaut.psi_planchers, step=0.01,
                    key="psi_planchers", help=aide("psi_planchers"))
    inertie = st.select_slider("Inertie", list(LIBELLES_INERTIE), value=defaut.inertie,
                               format_func=LIBELLES_INERTIE.get, key="inertie", help=aide("inertie"))
    return {"u_mur": u_mur, "u_toiture": u_toiture, "u_plancher": u_plancher, "plancher_sur_sol": sur_sol,
            "teinte": teinte, "psi_planchers": psi, "inertie": inertie}


def _air(defaut):
    debit = st.slider("Ventilation (m³/h par m² habitable)", 0.3, 3.0, defaut.debit_ventilation_m3h_m2, step=0.1,
                      key="debit_ventilation_m3h_m2", help=aide("debit_ventilation_m3h_m2"))
    q4pa = st.slider("Perméabilité à l'air Q4Pa-surf (m³/h.m²)", 0.0, 3.0, defaut.permeabilite_q4pa, step=0.1,
                     key="permeabilite_q4pa", help=aide("permeabilite_q4pa"))
    return {"debit_ventilation_m3h_m2": debit, "permeabilite_q4pa": q4pa}


def _confort(defaut):
    climatise = st.toggle("Logements climatisés", defaut.climatise, key="climatise", help=aide("climatise"))
    brasseurs = st.toggle("Brasseurs d'air de plafond", defaut.brasseurs, key="brasseurs",
                          help=aide("brasseurs"), disabled=climatise)
    champs = {"climatise": climatise, "brasseurs": brasseurs and not climatise}
    if champs["brasseurs"]:
        champs["brasseurs_par_logement"] = st.slider("Brasseurs par logement", 1, 6, defaut.brasseurs_par_logement,
                                                     key="brasseurs_par_logement", help=aide("brasseurs_par_logement"))
        champs["brasseur_debit_m3h"] = float(st.number_input("Débit maximal d'un brasseur (m³/h)", 1000, 30000,
                                                             round(defaut.brasseur_debit_m3h), step=500,
                                                             key="brasseur_debit_m3h", help=aide("brasseur_debit_m3h")))
        champs["brasseur_puissance_w"] = float(st.number_input("Puissance maximale d'un brasseur (W)", 5, 200,
                                                               round(defaut.brasseur_puissance_w), step=5,
                                                               key="brasseur_puissance_w",
                                                               help=aide("brasseur_puissance_w")))
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
    valeurs["orientation"] = _azimut_du_curseur(boite.orientation_deg)
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
                            help=aide("batiment_depart"), on_change=_reprendre_batiment)
    niveau = st.segmented_control("Enveloppe", list(NIVEAUX_ENVELOPPE), default=NIVEAU_D_OUVERTURE, required=True,
                                  key="niveau_enveloppe", help=aide("niveau_enveloppe"), on_change=_reprendre_niveau)
    return boite_de_depart(batiment, niveau)


def choisir_calculs():
    """Choix du calcul à lancer ; rend les calculs demandés (« bbio », « dh » ou les deux)."""
    choix = st.segmented_control("Calcul", list(CHOIX_CALCULS), default=next(iter(CHOIX_CALCULS)), required=True,
                                 key="choix_calculs", help=aide("choix_calculs"))
    return CHOIX_CALCULS[choix]


def resumes(defaut):
    """Résumé de chaque volet en une ligne, pour son titre : le volet fermé montre ses valeurs principales.

    Lu dans la session (la saisie en cours, avant que les widgets ne s'affichent), sinon dans la boîte de départ :
    volet → texte, par exemple « Baies » → « 25/0/15/0 % · volets ».
    """
    from interface.briques.graphiques import nombre     # import ici : les briques importent ce module
    depart = valeurs_des_widgets(defaut)

    def valeur(cle):
        return st.session_state.get(cle, depart[cle])

    point = point_cardinal(orientation_moteur(valeur("orientation")))
    niveaux = valeur("nb_niveaux")
    parts = "/".join(str(valeur(f"part_vitree_{cle}")) for cle, _, _, _ in FACADES)
    confort = ("climatisés" if valeur("climatise") else "brasseurs d'air" if valeur("brasseurs")
               else "ni climatisation ni brasseurs")
    return {"Site": f"{valeur('zone_climatique')} · {nombre(valeur('altitude_m'), 0, 'm')} · "
                    f"{valeur('exposition_bruit')}",
            "Forme": f"{nombre(valeur('longueur_m'), 0)} × {nombre(valeur('profondeur_m'), 0, 'm')} · "
                     f"{niveaux} niveau{'x' if niveaux > 1 else ''} · {point}",
            "Baies": f"{parts} % · {LIBELLES_PROTECTION[valeur('protection')].lower()}",
            "Parois": f"U murs {nombre(valeur('u_mur'), 2)} · toiture {nombre(valeur('u_toiture'), 2)}",
            "Air": f"{nombre(valeur('debit_ventilation_m3h_m2'), 1, 'm³/h.m²')} · "
                   f"Q4Pa {nombre(valeur('permeabilite_q4pa'), 1)}",
            "Confort d'été": confort}


def saisir(defaut=boite_de_depart()):
    """Affiche les volets de saisie (à appeler dans le menu de gauche) et rend la Boite décrite.

    defaut : la boîte de départ (choisir_depart), qui donne la valeur initiale de chaque widget et les champs non
    saisis (part habitable).
    Chaque volet a une clé : son titre porte le résumé de ses valeurs, qui change à chaque saisie, sans que le
    volet ne se referme. « Baies » est ouvert à l'ouverture : c'est le levier le plus essayé.
    """
    champs = {}
    resume = resumes(defaut)

    def volet(nom, icone, ouvert=False):
        return st.expander(f"{nom} · {resume[nom]}", expanded=ouvert, icon=icone, key=f"volet_{VOLETS[nom]}")

    with volet("Site", ":material/location_on:"):
        champs.update(_site(defaut))
    with volet("Forme", ":material/deployed_code:"):
        champs.update(_forme(defaut))
    with volet("Baies", ":material/window:", ouvert=True):
        champs.update(_baies(defaut, champs["orientation_deg"], champs["parois_adiabatiques"]))
    with volet("Parois", ":material/layers:"):
        champs.update(_parois(defaut, champs["parois_adiabatiques"]))
    with volet("Air", ":material/air:"):
        champs.update(_air(defaut))
    with volet("Confort d'été", ":material/mode_fan:"):
        champs.update(_confort(defaut))
    return replace(defaut, **champs)


# ============================================================
# SAISIES DANS LA FICHE DE LA PAROI (0.9.34)
# ============================================================
# La fiche de la paroi examinée reprend les saisies de cette paroi. Un widget n'a qu'une clé : celui de la fiche a la
# sienne (« fiche_uw »), recopiée dans celle du menu (« uw ») quand on le change. Le menu reste la seule source de
# la boîte : saisir() le lit au passage suivant, qui doit être celui de toute la page (la fiche est dans un fragment,
# voir app.py : saisie_par_la_fiche()).
def saisies_de_la_paroi(boite, cle_paroi):
    """Champs de la boîte que la fiche de cette paroi fait saisir, dans l'ordre (SAISIES_FICHE)."""
    facade = None
    if cle_paroi.startswith(PREFIXE_BAIES):
        sorte, facade = "baies", cle_paroi[len(PREFIXE_BAIES):]
    elif cle_paroi in CLES_FACADES:
        sorte, facade = "facade", cle_paroi
    else:
        sorte = cle_paroi
    return [champ.format(facade=facade) for champ in SAISIES_FICHE.get(sorte, ())]



def _recopier_dans_le_menu(champ):
    """Rappel d'une saisie de la fiche : sa valeur passe dans le widget du menu, et la page entière sera relancée."""
    st.session_state[champ] = st.session_state[PREFIXE_FICHE + champ]
    st.session_state["saisie_par_la_fiche"] = True


def saisir_dans_la_fiche(boite, cle_paroi):
    """Widgets de la fiche pour les saisies de cette paroi, à la valeur du menu ; changer l'un change le menu."""
    valeurs = valeurs_des_widgets(boite)
    for champ in saisies_de_la_paroi(boite, cle_paroi):
        cle = PREFIXE_FICHE + champ
        # La valeur du menu, posée avant le widget (pas de « value » : la session la donne)
        st.session_state[cle] = st.session_state.get(champ, valeurs[champ])
        commune = f" — {SAISIES_COMMUNES[champ]}" if champ in SAISIES_COMMUNES else ""
        options = {"key": cle, "on_change": _recopier_dans_le_menu, "args": (champ,), "help": aide(champ)}
        if champ.startswith("part_vitree_"):
            facade = champ[len("part_vitree_"):]
            st.slider("Part vitrée de la façade", 0, round(PART_VITREE_MAX * 100), step=5, format="%d %%",
                      disabled=facade in boite.parois_adiabatiques, **options)
        elif champ in CURSEURS:
            libelle, mini, maxi, pas = CURSEURS[champ]
            adiabatique = {"u_toiture": "toiture", "u_plancher": "plancher_bas"}.get(champ)
            st.slider(libelle + commune, mini, maxi, step=pas, disabled=adiabatique in boite.parois_adiabatiques,
                      **options)
        elif champ == "protection":
            st.segmented_control("Protection mobile" + commune, list(LIBELLES_PROTECTION),
                                 format_func=LIBELLES_PROTECTION.get, required=True, **options)
        elif champ == "teinte":
            st.segmented_control("Teinte" + commune, list(TEINTES), format_func=str.capitalize, required=True,
                                 **options)
        elif champ == "plancher_sur_sol":
            st.toggle("Plancher bas sur le sol", disabled="plancher_bas" in boite.parois_adiabatiques, **options)


def remettre(boite, batiment, niveau):
    """Remet dans la saisie une boîte gardée (variante) : chaque widget prend sa valeur, avec le bâtiment de départ
    et le niveau d'enveloppe d'où elle venait (ils donnent les champs non saisis, comme la part habitable)."""
    st.session_state.update(valeurs_des_widgets(boite))
    st.session_state.update({"batiment_depart": batiment, "niveau_enveloppe": niveau})
