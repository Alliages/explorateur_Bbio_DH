"""
============================================================
 SAISIE — une boîte simple, traduite en projet du moteur
============================================================
 L'interface ne décrit pas un bâtiment réel : elle décrit une
 BOÎTE, que l'on peut tourner, vitrer et isoler, et qui devient
 un projet d'un seul groupe (moteur/structures.py).

   Vue de dessus, façade principale au sud (orientation 0) :

            façade arrière (orientation + 180°)
          +--------------------------+
   pignon |                          |  pignon
     A    |        longueur          |    B            profondeur
  (+ 90°) |                          |  (− 90°)
          +--------------------------+
            façade principale (orientation : 0 = sud, 90 = ouest)

   hauteur = nombre de niveaux × hauteur d'étage
   surface habitable = longueur × profondeur × niveaux × part habitable

 Ce fichier ne dépend pas de Streamlit : la boîte se construit et
 se teste seule. Pour ajouter une saisie : un champ dans Boite
 (avec sa valeur par défaut), son emploi dans construire_projet,
 son widget dans interface/formulaire.py.

 Ce que la boîte ne sait pas décrire (voir ROADMAP.md) : masques
 lointains, joues et loggias, plusieurs groupes, part réémise Sw2
 de la baie nue (celle de la baie protégée et la perméabilité de
 la protection suivent le type de protection, guide Actibaie),
 gestion des brasseurs par thermostat, ponts thermiques au détail.
============================================================
"""

import csv
import io
import math
import os
from dataclasses import dataclass, fields, replace

from config.reglages import (CHEMIN_TYPOLOGIES, DECIMALE_CSV, DOSSIER_BATIMENTS, SEPARATEUR_CSV,
                             ZONES_CLIMATIQUES)
from moteur.hypotheses import hyp
from moteur.structures import (Baie, Batiment, Brasseur, Groupe, MasqueProcheHorizontal, Paroi, PontThermique,
                               Projet, Zone, ramener_azimut)

# ============================================================
# RÉGLAGES
# ============================================================
# Les quatre façades, dans l'ordre de la saisie : (clé, libellé, écart d'orientation avec la façade principale,
# dimension horizontale : « longueur » ou « profondeur »)
FACADES = (("principale", "Façade principale", 0.0, "longueur"),
           ("pignon_a", "Pignon A", 90.0, "profondeur"),
           ("arriere", "Façade arrière", 180.0, "longueur"),
           ("pignon_b", "Pignon B", -90.0, "profondeur"))
# Parois que l'on peut rendre adiabatiques (sur un local chauffé : mitoyenneté, logement voisin), dans l'ordre de la
# saisie : les quatre façades, puis la toiture et le plancher bas (clé → libellé)
PAROIS_ADIABATIQUES = {**{cle: libelle for cle, libelle, _, _ in FACADES}, "toiture": "Toiture",
                       "plancher_bas": "Plancher bas"}
# Orientation saisie en azimut géographique (0 = nord, 90 = est, 180 = sud, 270 = ouest), par pas de :
PAS_ORIENTATION_DEG = 10
# Points cardinaux : (azimut du moteur, nom) — 0 = sud, 90 = ouest, ± 180 = nord, − 90 = est
POINTS_CARDINAUX = ((0, "sud"), (45, "sud-ouest"), (90, "ouest"), (135, "nord-ouest"), (180, "nord"),
                    (-135, "nord-est"), (-90, "est"), (-45, "sud-est"))
# Teinte des parois → clé de l'absorption solaire dans donnees/hypotheses.csv (règles Th-Bât, tableau 66)
TEINTES = {"claire": "alpha_teinte_claire", "moyenne": "alpha_teinte_moyenne", "sombre": "alpha_teinte_sombre",
           "noire": "alpha_teinte_noire"}
SANS_PROTECTION = "aucune"
PART_VITREE_MAX = 0.9       # au-delà, la façade n'a plus de mur : la saisie est bornée
# Gabarit d'une baie dans sa travée : part de la hauteur d'étage qu'elle occupe, et place du vide restant
PART_HAUTEUR_BAIE_MIN, PART_HAUTEUR_BAIE_MAX = 0.45, 0.92
TRAME_M = 3.0               # largeur d'une travée de baies (m) : une baie par travée et par niveau
PART_ALLEGE = 0.55          # part du vide restant placée sous la baie (allège) ; le reste est au-dessus (linteau)
DEBORD_MAX_M = 3.0          # profondeur maximale d'un balcon ou d'une casquette (saisie bornée)
NOM_BATIMENT, NOM_ZONE, NOM_GROUPE = "Bâtiment", "Logements", "Boîte"
CLE_GROUPE = (NOM_BATIMENT, NOM_ZONE, NOM_GROUPE)       # clé des résultats horaires du moteur
# Niveaux d'enveloppe (donnees/typologies_logements.csv) : libellé affiché → colonne du CSV ; « Moyen » à l'ouverture
NIVEAUX = {"Performant": "performant", "Moyen": "moyen", "Faible": "faible"}
NIVEAU_D_OUVERTURE = "Moyen"
# Colonne source du CSV (premier mot) → champ de Boite. psi_moyen couvre tous les ponts thermiques ; la boîte
# l'applique aux seules rives des planchers (hypothèse 88 de docs/audit.md).
CHAMPS_TYPOLOGIES = {"uw": "uw", "sw_e": "sw", "tl": "tl", "sw_protege": "sw_protege", "uw_protege": "uw_protege",
                     "u_mur": "u_mur", "u_toiture": "u_toiture", "u_plancher_bas": "u_plancher",
                     "psi_moyen": "psi_planchers", "ventilation_m3h_m2": "debit_ventilation_m3h_m2",
                     "permeabilite_q4pa": "permeabilite_q4pa", "ratio_ouverture_max": "ratio_ouverture_max",
                     "inertie_quotidienne": "inertie"}
# Classes d'inertie écrites dans le CSV → classes du moteur
CLASSES_INERTIE = {"très légère": "tres_legere", "légère": "legere", "moyenne": "moyenne", "lourde": "lourde",
                   "très lourde": "tres_lourde"}
# CSV des bâtiments de départ (donnees/batiments/) : colonnes lues, ligne du nom, écriture des oui / non
COLONNES_BATIMENT = ("champ", "valeur")         # les autres colonnes (unité, description) servent au lecteur
CHAMP_NOM = "nom"
OUI_NON = {"oui": True, "non": False}


# ============================================================
# LA BOÎTE
# ============================================================
@dataclass(frozen=True)
class Boite:
    """Description simple d'un bâtiment de logements : tout ce que l'interface fait saisir.

    Valeurs par défaut : celles du logement de 70 m² (donnees/batiments/01_logement_70m2.csv ; un test vérifie
    l'accord), un petit bâtiment isolé (quatre façades, toiture et plancher bas sur l'extérieur ou le sol), calculé
    comme du logement collectif. Elles complètent un CSV de bâtiment qui omet un champ. La page, elle, s'ouvre sur
    l'enveloppe du niveau « Moyen » (boite_de_depart) : seules la forme et les saisies hors enveloppe viennent de
    ces valeurs.
    Figée (frozen) : deux boîtes égales donnent le même calcul, ce qui sert de clé au cache de l'interface.
    """
    # --- Site ---
    zone_climatique: str = "H1a"
    altitude_m: float = 50.0
    exposition_bruit: str = "BR1"           # BR1, BR2 ou BR3 : module le Bbio max et l'ouverture des baies
    # --- Forme ---
    longueur_m: float = 7.0                 # façade principale
    profondeur_m: float = 10.0
    nb_niveaux: int = 1
    hauteur_etage_m: float = 2.8            # de plancher à plancher
    hauteur_sous_plafond_m: float = 2.5
    orientation_deg: float = 0.0            # de la façade principale : 0 = sud, 90 = ouest
    part_habitable: float = 1.0             # surface habitable / surface de plancher
    nb_logements: int = 1
    traversant: bool = True
    # --- Baies ---
    part_vitree_principale: float = 0.25    # surface de baies / surface de la façade
    part_vitree_pignon_a: float = 0.0
    part_vitree_arriere: float = 0.25
    part_vitree_pignon_b: float = 0.0
    uw: float = 1.4                         # W/m².K
    sw: float = 0.5                         # facteur solaire sans protection
    tl: float = 0.6                         # transmission lumineuse
    protection: str = "volet"               # « aucune », « volet » ou « store_enroulable »
    gestion_protection: str = "manuelle_motorisee"      # ou « manuelle_non_motorisee », « automatique »
    uw_protege: float = 1.1                 # avec la protection en place
    sw_protege: float = 0.1
    ouvrable: bool = True
    ratio_ouverture_max: float = 0.6        # surface d'ouverture / surface de la baie
    debord_m: float = 0.0                   # profondeur des balcons ou casquettes au-dessus des baies ; 0 : aucun
    facades_debord: tuple = ("principale",)     # façades qui portent ces débords (clés de FACADES)
    # --- Parois ---
    u_mur: float = 0.25                     # W/m².K
    u_toiture: float = 0.15
    u_plancher: float = 0.25
    plancher_sur_sol: bool = True           # sinon : plancher sur l'extérieur
    parois_adiabatiques: tuple = ()         # parois sur un local chauffé, sans échange (clés de PAROIS_ADIABATIQUES)
    teinte: str = "moyenne"                 # absorption solaire des murs et de la toiture
    psi_planchers: float = 0.3              # W/m.K : liaison de chaque plancher avec la façade
    inertie: str = "moyenne"                # classe d'inertie quotidienne
    # --- Air ---
    debit_ventilation_m3h_m2: float = 1.0   # débit d'air neuf par m² habitable
    permeabilite_q4pa: float = 1.0          # m³/h par m² de paroi sous 4 Pa ; 0 : pas d'infiltrations
    # --- Confort d'été ---
    climatise: bool = False                 # change le DH max ; le DH se calcule toujours sans climatisation
    brasseurs: bool = False
    brasseurs_par_logement: int = 2
    brasseur_debit_m3h: float = 11000.0     # valeurs du fabricant, par brasseur
    brasseur_puissance_w: float = 40.0

    # ---------- Grandeurs déduites ----------
    @property
    def emprise_m2(self):
        return self.longueur_m * self.profondeur_m

    @property
    def hauteur_m(self):
        return self.nb_niveaux * self.hauteur_etage_m

    @property
    def surface_habitable_m2(self):
        return self.emprise_m2 * self.nb_niveaux * self.part_habitable

    @property
    def volume_m3(self):
        return self.surface_habitable_m2 * self.hauteur_sous_plafond_m

    @property
    def perimetre_m(self):
        return 2.0 * (self.longueur_m + self.profondeur_m)

    def facades(self):
        """Les quatre façades : cle, libelle, orientation_deg, largeur_m, recul_m (distance au centre de la
        boîte), surface_m2, part_vitree, surface de baies et surface de mur (m²), adiabatique (vrai si la façade
        donne sur un local chauffé : elle n'a alors aucune baie, quelle que soit la part vitrée saisie)."""
        liste = []
        for cle, libelle, ecart, dimension in FACADES:
            largeur, autre = (self.longueur_m, self.profondeur_m) if dimension == "longueur" \
                else (self.profondeur_m, self.longueur_m)
            surface = largeur * self.hauteur_m
            adiabatique = cle in self.parois_adiabatiques
            part = 0.0 if adiabatique else getattr(self, f"part_vitree_{cle}")
            liste.append({"cle": cle, "libelle": libelle, "adiabatique": adiabatique,
                          "orientation_deg": ramener_azimut(self.orientation_deg + ecart),
                          "largeur_m": largeur, "recul_m": autre / 2.0, "surface_m2": surface, "part_vitree": part,
                          "baies_m2": surface * part, "mur_m2": surface * (1.0 - part)})
        return liste


# ============================================================
# BÂTIMENTS DE DÉPART (premier choix du menu de gauche)
# ============================================================
# Choisir l'un d'eux remet toutes les saisies à ses valeurs, l'enveloppe étant celle du niveau choisi
# (boite_de_depart). Chaque bâtiment est un CSV de donnees/batiments/ (format décrit dans le README.md du
# dossier) : un fichier ajouté apparaît dans le menu au lancement suivant. Les fichiers sont lus par ordre
# alphabétique (d'où le numéro en tête de leur nom) ; le premier est celui de la page à son ouverture.
#
#   champ;valeur;unite;description
#   nom;Logement de 70 m²;;nom affiché dans le menu
#   longueur_m;7;m;longueur de la façade principale
#   …
#
# Un champ absent prend la valeur par défaut de Boite ; les 13 saisies d'enveloppe sont refusées (elles viennent
# du niveau) ; un champ inconnu, une valeur illisible ou une boîte que construire_projet refuse lèvent une
# ValueError qui nomme le fichier.
def _convertir(champ, texte):
    """Valeur d'un CSV de bâtiment, convertie au type du champ de Boite (nombre, entier, oui / non, liste, texte)."""
    if champ.type is bool:
        if texte.lower() not in OUI_NON:
            raise ValueError(f"« {texte} » : écrire oui ou non")
        return OUI_NON[texte.lower()]
    if champ.type is int:
        return int(texte)                                       # « 1,5 » est refusé : un entier est attendu
    if champ.type is float:
        return float(texte.replace(DECIMALE_CSV, "."))
    if champ.type is tuple:                                     # clés séparées par une virgule
        return tuple(cle.strip() for cle in texte.split(",") if cle.strip())
    return texte


def lire_batiment(chemin):
    """Lit un CSV de bâtiment : (nom affiché, Boite). L'enveloppe de la Boite rendue est celle des valeurs par
    défaut, remplacée ensuite par celle du niveau choisi (boite_de_depart)."""
    fichier = os.path.basename(chemin)
    champs = {champ.name: champ for champ in fields(Boite)}
    enveloppe = set(CHAMPS_TYPOLOGIES.values())
    nom, valeurs = None, {}
    with open(chemin, encoding="utf-8-sig", newline="") as f:          # accepte un CSV enregistré par Excel (BOM)
        lecteur = csv.DictReader(f, delimiter=SEPARATEUR_CSV)
        if not set(COLONNES_BATIMENT) <= set(lecteur.fieldnames or ()):
            raise ValueError(f"{fichier} : colonnes « {' » et « '.join(COLONNES_BATIMENT)} » attendues "
                             f"(séparateur « {SEPARATEUR_CSV} »)")
        for numero, ligne in enumerate(lecteur, start=2):               # ligne 1 : les titres des colonnes
            champ, texte = (ligne["champ"] or "").strip(), (ligne["valeur"] or "").strip()
            lieu = f"{fichier}, ligne {numero}"
            if not champ:                                               # ligne vide : ignorée
                continue
            if champ == CHAMP_NOM:
                if nom is not None:
                    raise ValueError(f"{lieu} : « nom » écrit deux fois")
                nom = texte
            elif champ in enveloppe:
                raise ValueError(f"{lieu} : « {champ} » fait partie de l'enveloppe, donnée par le niveau "
                                 "(performant, moyen ou faible) et non par le bâtiment")
            elif champ not in champs:
                raise ValueError(f"{lieu} : champ inconnu « {champ} »")
            elif champ in valeurs:
                raise ValueError(f"{lieu} : « {champ} » écrit deux fois")
            else:
                try:
                    valeurs[champ] = _convertir(champs[champ], texte)
                except ValueError as erreur:
                    raise ValueError(f"{lieu} : valeur illisible pour « {champ} » ({erreur})") from None
    if not nom:
        raise ValueError(f"{fichier} : ligne « {CHAMP_NOM} » absente ou vide")
    boite = Boite(**valeurs)
    # Contrôles de la boîte entière : ceux de construire_projet et du moteur, plus la zone (lue par la météo)
    if boite.zone_climatique not in ZONES_CLIMATIQUES:
        raise ValueError(f"{fichier} : zone climatique inconnue « {boite.zone_climatique} » "
                         f"({', '.join(ZONES_CLIMATIQUES)})")
    try:
        construire_projet(boite)
    except KeyError as erreur:
        raise ValueError(f"{fichier} : valeur inconnue {erreur}") from None
    except ValueError as erreur:
        raise ValueError(f"{fichier} : {erreur}") from None
    return nom, boite


def lire_batiments(dossier=DOSSIER_BATIMENTS):
    """Lit tous les CSV du dossier, par ordre alphabétique des fichiers : {nom affiché: Boite}."""
    fichiers = sorted(f for f in os.listdir(dossier) if f.lower().endswith(".csv"))
    if not fichiers:
        raise ValueError(f"{dossier} : aucun bâtiment de départ (fichier .csv)")
    batiments = {}
    for fichier in fichiers:
        nom, boite = lire_batiment(os.path.join(dossier, fichier))
        if nom in batiments:
            raise ValueError(f"{fichier} : le nom « {nom} » est déjà pris par un autre bâtiment")
        batiments[nom] = boite
    return batiments


def _ecrire_valeur(valeur):
    """Valeur d'un champ de Boite écrite comme dans un CSV de bâtiment (inverse de _convertir)."""
    if isinstance(valeur, bool):
        return next(texte for texte, sens in OUI_NON.items() if sens is valeur)
    if isinstance(valeur, float):
        texte = repr(valeur)                                    # le plus court qui relit la même valeur
        return (texte[:-2] if texte.endswith(".0") else texte).replace(".", DECIMALE_CSV)
    if isinstance(valeur, tuple):
        return ", ".join(valeur)
    return str(valeur)


def ecrire_batiment(boite, nom, dossier=DOSSIER_BATIMENTS):
    """Texte du CSV de bâtiment qui décrit cette boîte, sous le nom donné (bouton « Télécharger ce bâtiment »).

    Le fichier a le format de donnees/batiments/ et se relit avec lire_batiment : la forme, le site, les baies
    (parts vitrées, protection, balcons) et le confort d'été. Les 13 saisies d'enveloppe n'y sont pas : comme pour
    tout bâtiment de départ, elles viennent du niveau choisi. Unités et descriptions : celles du premier CSV du
    dossier, qui sert de modèle ; un champ qu'il ne décrit pas garde des colonnes vides.
    """
    modele = sorted(f for f in os.listdir(dossier) if f.lower().endswith(".csv"))[0]
    with open(os.path.join(dossier, modele), encoding="utf-8-sig", newline="") as f:
        notes = {ligne["champ"]: (ligne.get("unite") or "", ligne.get("description") or "")
                 for ligne in csv.DictReader(f, delimiter=SEPARATEUR_CSV)}
    enveloppe = set(CHAMPS_TYPOLOGIES.values())
    lignes = [("champ", "valeur", "unite", "description"), (CHAMP_NOM, nom, *notes.get(CHAMP_NOM, ("", "")))]
    lignes += [(champ.name, _ecrire_valeur(getattr(boite, champ.name)), *notes.get(champ.name, ("", "")))
               for champ in fields(Boite) if champ.name not in enveloppe]
    sortie = io.StringIO()
    csv.writer(sortie, delimiter=SEPARATEUR_CSV, lineterminator="\n").writerows(lignes)
    return sortie.getvalue()


# ============================================================
# NIVEAUX D'ENVELOPPE (second choix du menu de gauche)
# ============================================================
# Le bâtiment donne la forme, le niveau donne l'enveloppe (13 saisies : baies, parois, ponts thermiques, inertie,
# ventilation, perméabilité). Les trois niveaux sont les repères P25, P50 et P75, pondérés par la surface
# habitable, de 18 zones de logements tirées de 6 études RE2020 (outils/typologies/, graphique dans
# docs/graphique_pedagogique_logements.png).
def lire_niveaux_enveloppe(chemin=CHEMIN_TYPOLOGIES):
    """Lit le CSV des typologies : {libellé du niveau: {champ de Boite: valeur}}.

    Une colonne source inconnue ou un champ manquant lève une ValueError : le CSV et CHAMPS_TYPOLOGIES doivent
    rester d'accord.
    """
    niveaux = {libelle: {} for libelle in NIVEAUX}
    with open(chemin, encoding="utf-8-sig", newline="") as f:          # le CSV est écrit avec un BOM (Excel)
        for ligne in csv.DictReader(f, delimiter=SEPARATEUR_CSV):
            colonne = ligne["colonne_source"].split()[0]                # « inertie_quotidienne (+cmq_surf, …) »
            if colonne not in CHAMPS_TYPOLOGIES:
                raise ValueError(f"{chemin} : colonne source inconnue « {colonne} »")
            champ = CHAMPS_TYPOLOGIES[colonne]
            for libelle, colonne_niveau in NIVEAUX.items():
                texte = ligne[colonne_niveau].strip()
                niveaux[libelle][champ] = CLASSES_INERTIE[texte] if champ == "inertie" \
                    else float(texte.replace(DECIMALE_CSV, "."))
    for libelle, champs in niveaux.items():
        manquants = set(CHAMPS_TYPOLOGIES.values()) - set(champs)
        if manquants:
            raise ValueError(f"{chemin} : niveau {libelle}, champs absents : {', '.join(sorted(manquants))}")
    return niveaux


NIVEAUX_ENVELOPPE = lire_niveaux_enveloppe()


def boite_de_depart(batiment=None, niveau=NIVEAU_D_OUVERTURE):
    """Boîte de départ : la forme du bâtiment choisi (le premier par défaut), l'enveloppe du niveau choisi."""
    return replace(BATIMENTS_DE_DEPART[batiment or next(iter(BATIMENTS_DE_DEPART))], **NIVEAUX_ENVELOPPE[niveau])


def gabarit_baie(part_vitree, hauteur_etage_m):
    """Gabarit conventionnel d'une baie : (part de la hauteur d'étage, hauteur, allège, linteau), en mètres.

    La baie occupe une part fh de la hauteur d'étage et fw = part vitrée / fh de la largeur de sa travée : le
    dessin (interface/axonometrie.py) et le masque des débords partent du même gabarit.

        plancher haut  ---------------   ← un balcon ou une casquette déborde ici
        linteau        |             |
                       +-------------+
        baie           |             |   hauteur = fh × hauteur d'étage
                       +-------------+
        allège         |             |
        plancher bas   ---------------
    """
    fh = min(PART_HAUTEUR_BAIE_MAX, max(PART_HAUTEUR_BAIE_MIN, math.sqrt(part_vitree)))
    vide = hauteur_etage_m * (1.0 - fh)
    return fh, fh * hauteur_etage_m, vide * PART_ALLEGE, vide * (1.0 - PART_ALLEGE)


def largeur_travee(largeur_facade_m):
    """Largeur d'une travée (m) : la façade est partagée en travées égales, proches de TRAME_M."""
    return largeur_facade_m / max(1, round(largeur_facade_m / TRAME_M))


def point_cardinal(orientation_deg):
    """Nom du point cardinal le plus proche d'une orientation du moteur (0 = sud, 90 = ouest)."""
    azimut = ramener_azimut(orientation_deg)
    ecart = lambda point: abs(ramener_azimut(azimut - point[0]))
    return min(POINTS_CARDINAUX, key=ecart)[1]


# Deux conventions d'orientation : le moteur compte depuis le sud vers l'ouest (0 = sud, 90 = ouest, − 90 = est) ;
# la saisie montre l'azimut géographique, compté depuis le nord vers l'est (0 = nord, 90 = est, 180 = sud).
def azimut_geographique(orientation_deg):
    """Azimut géographique (0 à 360°, 0 = nord, 90 = est) d'une orientation du moteur."""
    return (orientation_deg + 180.0) % 360.0


def orientation_moteur(azimut_geo_deg):
    """Orientation du moteur (− 180 à 180°, 0 = sud, 90 = ouest) d'un azimut géographique."""
    return ramener_azimut(azimut_geo_deg - 180.0)


def libelle_orientation(orientation_deg):
    """Orientation du moteur écrite pour être lue : azimut géographique et point cardinal, « 190° · sud »."""
    return f"{azimut_geographique(orientation_deg):.0f}° · {point_cardinal(orientation_deg)}"


# ============================================================
# DE LA BOÎTE AU PROJET
# ============================================================
def _conventions_protection(boite):
    """Ce que la boîte ne fait pas saisir d'une protection mobile, pris selon son type (volet, store enroulable)
    dans le guide Actibaie (donnees/hypotheses.csv, clés boite_…) :

      typo_permeabilite_protection   part de l'air qui traverse la protection fermée (Typo_PM, fiche 5.12) : 1, soit
                                     10 % (tablier peu ajouré), au lieu de 0 (étanche, défaut de la méthode) ;
      sw2_protege                    part réémise du Sw protégé : tout pour un volet opaque (Sw1 = 0), 40 % pour un
                                     store en toile ; sans elle, tout le Sw protégé entrerait en Sw1.
    """
    return {"typo_permeabilite_protection": int(hyp(f"boite_typo_pm_{boite.protection}")),
            "sw2_protege": hyp(f"boite_sw2_part_protege_{boite.protection}") * boite.sw_protege}


def construire_projet(boite):
    """Projet du moteur décrit par la boîte : un bâtiment, une zone, un groupe.

    Les contrôles sont ceux du moteur (moteur/structures.py) : une valeur hors bornes lève une ValueError
    au message clair, que l'interface affiche telle quelle.
    """
    for facade in boite.facades():
        if not 0.0 <= facade["part_vitree"] <= PART_VITREE_MAX:
            raise ValueError(f"{facade['libelle']} : la part vitrée doit rester entre 0 et "
                             f"{PART_VITREE_MAX:.0%} (reçu : {facade['part_vitree']:.0%})")
    if not 0.0 < boite.part_habitable <= 1.0:
        raise ValueError(f"La part habitable doit être comprise entre 0 et 1 (reçu : {boite.part_habitable})")
    if not 0.0 <= boite.debord_m <= DEBORD_MAX_M:
        raise ValueError(f"La profondeur des balcons doit rester entre 0 et {DEBORD_MAX_M:.0f} m "
                         f"(reçu : {boite.debord_m})")
    inconnues = set(boite.facades_debord) - {cle for cle, *_ in FACADES}
    if inconnues:
        raise ValueError(f"Façades inconnues pour les balcons : {', '.join(sorted(inconnues))}")
    inconnues = set(boite.parois_adiabatiques) - set(PAROIS_ADIABATIQUES)
    if inconnues:
        raise ValueError(f"Parois adiabatiques inconnues : {', '.join(sorted(inconnues))} "
                         f"(au choix : {', '.join(PAROIS_ADIABATIQUES)})")
    alpha = hyp(TEINTES[boite.teinte])
    avec_protection = boite.protection != SANS_PROTECTION

    # --- Façades : un mur et, si elle est vitrée, une baie par façade ---
    # Une paroi adiabatique (sur un local chauffé) n'entre pas dans le groupe : ni échange de chaleur, ni soleil, ni
    # perméabilité à l'air ; l'inertie, donnée par sa classe, ne change pas (hypothèse 101 de docs/audit.md)
    parois, baies = [], []
    for facade in boite.facades():
        if facade["adiabatique"]:
            continue
        nom = f"{facade['libelle']} ({point_cardinal(facade['orientation_deg'])})"
        parois.append(Paroi(f"Mur — {nom}", "mur", facade["mur_m2"], u=boite.u_mur,
                            orientation_deg=facade["orientation_deg"], alpha=alpha))
        if facade["baies_m2"] > 0:
            # Balcon ou casquette : un débord horizontal au nu du plancher haut, donc à un linteau du haut de
            # la baie (fiche 3.2, éq. 20 et 21 : seules comptent la profondeur, cette distance et la hauteur)
            fh, hauteur_baie, _, linteau = gabarit_baie(facade["part_vitree"], boite.hauteur_etage_m)
            largeur_baie = facade["part_vitree"] / fh * largeur_travee(facade["largeur_m"])
            masques = [MasqueProcheHorizontal(boite.debord_m, distance_m=linteau)] \
                if boite.debord_m > 0 and facade["cle"] in boite.facades_debord else []
            baies.append(Baie(f"Baies — {nom}", facade["baies_m2"], facade["orientation_deg"],
                              largeur_m=largeur_baie, hauteur_m=hauteur_baie, masques=masques,
                              uw=boite.uw, sw_e=boite.sw, tl=boite.tl,
                              protection=boite.protection if avec_protection else None,
                              gestion_protection=boite.gestion_protection,
                              uw_protege=boite.uw_protege if avec_protection else None,
                              sw_protege=boite.sw_protege if avec_protection else None,
                              **(_conventions_protection(boite) if avec_protection else {}),
                              ouvrable=boite.ouvrable,
                              ratio_ouverture_max=boite.ratio_ouverture_max if boite.ouvrable else None))
    # --- Toiture et plancher bas : l'emprise de la boîte ---
    if "toiture" not in boite.parois_adiabatiques:
        parois.append(Paroi("Toiture", "toiture", boite.emprise_m2, u=boite.u_toiture, alpha=alpha))
    if "plancher_bas" not in boite.parois_adiabatiques:
        parois.append(Paroi("Plancher bas", "plancher_bas", boite.emprise_m2, u=boite.u_plancher,
                            contact="sol" if boite.plancher_sur_sol else "exterieur"))
    # --- Ponts thermiques : la rive de chaque plancher (bas, intermédiaires et toiture) le long des façades sur
    # l'extérieur. Une toiture ou un plancher bas adiabatique garde sa rive : la dalle reste liée à la façade,
    # comme un plancher intermédiaire ---
    ponts = []
    perimetre_exterieur = sum(f["largeur_m"] for f in boite.facades() if not f["adiabatique"])
    if boite.psi_planchers > 0 and perimetre_exterieur > 0:
        ponts.append(PontThermique("Rives des planchers", perimetre_exterieur * (boite.nb_niveaux + 1),
                                   boite.psi_planchers))
    # --- Brasseurs d'air : un seul type, la surface desservie plafonnée comme dans la fiche 8.32 ---
    brasseurs = []
    if boite.brasseurs:
        nombre = boite.brasseurs_par_logement * boite.nb_logements
        desservie = min(hyp("brasseur_surface_max") * nombre, boite.surface_habitable_m2)
        brasseurs.append(Brasseur("Brasseurs de plafond", nombre=nombre, surface_desservie_m2=desservie,
                                  debit_max_m3h=boite.brasseur_debit_m3h,
                                  puissance_max_w=boite.brasseur_puissance_w, usage="jour_et_nuit"))

    groupe = Groupe(NOM_GROUPE, boite.surface_habitable_m2, traversant=boite.traversant, parois=parois,
                    baies=baies, volume_m3=boite.volume_m3, brasseurs=brasseurs, ponts_thermiques=ponts,
                    debit_ventilation_m3h=boite.debit_ventilation_m3h_m2 * boite.surface_habitable_m2,
                    nb_logements=boite.nb_logements, climatise=boite.climatise,
                    inertie_quotidienne=boite.inertie, exposition_bruit=boite.exposition_bruit,
                    permeabilite_q4pa=boite.permeabilite_q4pa if boite.permeabilite_q4pa > 0 else None)
    zone = Zone(NOM_ZONE, groupes=[groupe], hauteur_sous_plafond_m=boite.hauteur_sous_plafond_m,
                hauteur_m=boite.hauteur_m, hauteur_moyenne_m=boite.hauteur_m / 2.0)
    return Projet("Boîte", boite.zone_climatique, altitude_m=boite.altitude_m,
                  batiments=[Batiment(NOM_BATIMENT, zones=[zone])])


# ============================================================
# LECTURE DES BÂTIMENTS DE DÉPART
# ============================================================
# En fin de module : la lecture contrôle chaque bâtiment avec construire_projet, défini plus haut.
BATIMENTS_DE_DEPART = lire_batiments()
