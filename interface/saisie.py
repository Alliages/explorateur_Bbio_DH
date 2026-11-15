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
 lointains, joues et loggias, plusieurs groupes, part réémise Sw2,
 gestion des brasseurs par thermostat, ponts thermiques au détail.
============================================================
"""

import math
from dataclasses import dataclass

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


# ============================================================
# LA BOÎTE
# ============================================================
@dataclass(frozen=True)
class Boite:
    """Description simple d'un bâtiment de logements : tout ce que l'interface fait saisir.

    Valeurs par défaut : le logement de 70 m² de BATIMENTS_DE_DEPART, un petit bâtiment isolé (quatre façades,
    toiture et plancher bas sur l'extérieur ou le sol), calculé comme du logement collectif.
    Figée (frozen) : deux boîtes égales donnent le même calcul, ce qui sert de clé au cache de l'interface.
    """
    # --- Site ---
    zone_climatique: str = "H3"
    altitude_m: float = 50.0
    exposition_bruit: str = "BR1"           # BR1, BR2 ou BR3 : module le Bbio max et l'ouverture des baies
    # --- Forme ---
    longueur_m: float = 10.0                # façade principale
    profondeur_m: float = 7.0
    nb_niveaux: int = 1
    hauteur_etage_m: float = 2.8            # de plancher à plancher
    hauteur_sous_plafond_m: float = 2.5
    orientation_deg: float = 0.0            # de la façade principale : 0 = sud, 90 = ouest
    part_habitable: float = 1.0             # surface habitable / surface de plancher
    nb_logements: int = 1
    traversant: bool = True
    # --- Baies ---
    part_vitree_principale: float = 0.30    # surface de baies / surface de la façade
    part_vitree_pignon_a: float = 0.10
    part_vitree_arriere: float = 0.20
    part_vitree_pignon_b: float = 0.10
    uw: float = 1.4                         # W/m².K
    sw: float = 0.5                         # facteur solaire sans protection
    tl: float = 0.6                         # transmission lumineuse
    protection: str = "volet"               # « aucune », « volet » ou « store_enroulable »
    gestion_protection: str = "manuelle_non_motorisee"
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
        boîte), surface_m2, part_vitree, surface de baies et surface de mur (m²)."""
        liste = []
        for cle, libelle, ecart, dimension in FACADES:
            largeur, autre = (self.longueur_m, self.profondeur_m) if dimension == "longueur" \
                else (self.profondeur_m, self.longueur_m)
            surface = largeur * self.hauteur_m
            part = getattr(self, f"part_vitree_{cle}")
            liste.append({"cle": cle, "libelle": libelle,
                          "orientation_deg": ramener_azimut(self.orientation_deg + ecart),
                          "largeur_m": largeur, "recul_m": autre / 2.0, "surface_m2": surface, "part_vitree": part,
                          "baies_m2": surface * part, "mur_m2": surface * (1.0 - part)})
        return liste


# ============================================================
# BÂTIMENTS DE DÉPART (premier choix du menu de gauche)
# ============================================================
# Choisir l'un d'eux remet toutes les saisies à ses valeurs. Le premier est celui de la page à son ouverture.
BATIMENTS_DE_DEPART = {
    # 10 m × 7 m, un niveau, un logement : 70 m² habitables
    "Logement de 70 m²": Boite(),
    # 20 m × 12 m, trois niveaux, 80 % habitables : 576 m² (la boîte de départ de la 0.9.0, Bbio 62,3, DH 1 777)
    "Immeuble de 9 logements": Boite(longueur_m=20.0, profondeur_m=12.0, nb_niveaux=3, part_habitable=0.8,
                                     nb_logements=9),
}


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


# ============================================================
# DE LA BOÎTE AU PROJET
# ============================================================
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
    alpha = hyp(TEINTES[boite.teinte])
    avec_protection = boite.protection != SANS_PROTECTION

    # --- Façades : un mur et, si elle est vitrée, une baie par façade ---
    parois, baies = [], []
    for facade in boite.facades():
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
                              ouvrable=boite.ouvrable,
                              ratio_ouverture_max=boite.ratio_ouverture_max if boite.ouvrable else None))
    # --- Toiture et plancher bas : l'emprise de la boîte ---
    parois.append(Paroi("Toiture", "toiture", boite.emprise_m2, u=boite.u_toiture, alpha=alpha))
    parois.append(Paroi("Plancher bas", "plancher_bas", boite.emprise_m2, u=boite.u_plancher,
                        contact="sol" if boite.plancher_sur_sol else "exterieur"))
    # --- Ponts thermiques : la rive de chaque plancher (bas, intermédiaires et toiture) sur tout le périmètre ---
    ponts = []
    if boite.psi_planchers > 0:
        ponts.append(PontThermique("Rives des planchers", boite.perimetre_m * (boite.nb_niveaux + 1),
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
