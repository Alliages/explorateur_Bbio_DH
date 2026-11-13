"""
============================================================
 STRUCTURES — description d'un projet
============================================================
 Hiérarchie de la méthode Th-BCE (annexe III, chapitre 2) :

     Projet → Bâtiment → Zone → Groupe → Parois et Baies

   - la ZONE porte un usage unique (ici : logement collectif) ;
   - le GROUPE est l'unité de calcul thermique : chaque groupe
     a sa propre température. Il n'y a pas de conduction entre
     groupes, seulement des transferts d'air ;
   - en logement collectif, la méthode distingue les logements
     traversants et non traversants : une zone porte donc une
     LISTE de groupes dès cette version.

 Version 0.8.2 : géométrie, masques et caractéristiques solaires
 (Sw des baies, absorption ou Sf des parois opaques).
 Version 0.8.4 : données du modèle thermique du groupe (fiche
 5.21) : inertie, ponts thermiques, débit de ventilation, part
 réémise Sw2 des baies, U horizontal des baies, coefficient b des
 parois sur un local non chauffé. Les protections mobiles
 arrivent avec le module qui les utilise (0.9.4).

 Conventions d'angle (annexe III, fiche 3.2, confirmées en 0.8.2) :
   - orientation : azimut de la normale extérieure, en degrés,
     0 = sud, 90 = ouest, ±180 = nord, −90 = est (la fiche écrit
     270 pour l'est : même direction). Toute valeur est ramenée
     dans [−180 ; 180[, comme l'azimut solaire Psi de la météo ;
   - inclinaison : 0 = horizontale vers le haut (toiture),
     90 = verticale, 180 = horizontale vers le bas (plancher
     donnant sur l'extérieur). Sans saisie, une paroi prend
     l'inclinaison de son type : mur 90, toiture 0, plancher
     bas 180.

 Masques (annexe III, fiche 3.2) : chaque baie ou paroi porte
 une liste de masques ; les masques proches demandent la largeur
 et la hauteur du composant. « Gauche » et « droite » s'entendent
 pour un observateur placé dehors, face à la paroi.
============================================================
"""

from dataclasses import dataclass, field

from config.reglages import USAGES, ZONES_CLIMATIQUES
from moteur.hypotheses import hyp

# ============================================================
# VALEURS ADMISES
# ============================================================
TYPES_PAROI = ("mur", "toiture", "plancher_bas")
CONTACTS_PAROI = ("exterieur", "sol", "local_non_chauffe")
COTES_MASQUE = ("gauche", "droite")
INCLINAISON_VERTICALE = 90.0
# Inclinaison par défaut d'une paroi selon son type : c'est aussi la position pour laquelle son U est donné
# (Incl_k de la fiche 5.17 : 1 verticale, 2 horizontale flux ascendant, 3 horizontale flux descendant)
INCLINAISON_PAR_TYPE = {"mur": 90.0, "toiture": 0.0, "plancher_bas": 180.0}
# Classes d'inertie (annexe III, fiche 5.21, tableaux 53 et 54 ; règles Th-Bât, tableau 89)
INERTIES_QUOTIDIENNES = ("tres_legere", "legere", "moyenne", "lourde", "tres_lourde", "personnalisee")
INERTIES_SEQUENTIELLES = ("defaut", "tres_legere", "legere", "moyenne", "lourde", "personnalisee")
INERTIES_ANNUELLES = ("defaut", "personnalisee")
# Brasseurs d'air (annexe III, fiche 8.32) : usage Usp, mode de gestion, caractère des valeurs du fabricant
USAGES_BRASSEUR = ("nuit", "jour", "jour_et_nuit")          # Usp = 0, 1, 2
GESTIONS_BRASSEUR = ("manuelle", "thermostat", "automatique")  # mode_gestion_br_p = 1, 2, 3
CARACTERES_VALEUR = ("certifiee", "justifiee", "declaree")


def _exiger_positif(valeur, nom):
    """Erreur claire si une grandeur qui doit être strictement positive ne l'est pas."""
    if not valeur > 0:
        raise ValueError(f"{nom} doit être strictement positif (reçu : {valeur})")


def _exiger_entre(valeur, mini, maxi, nom):
    """Erreur claire si une grandeur facultative sort de [mini ; maxi]."""
    if valeur is not None and not mini <= valeur <= maxi:
        raise ValueError(f"{nom} doit être compris entre {mini} et {maxi} (reçu : {valeur})")


def ramener_azimut(azimut_deg):
    """Azimut ramené dans [−180 ; 180[ (270 → −90, l'est). None reste None."""
    if azimut_deg is None:
        return None
    return (azimut_deg + 180.0) % 360.0 - 180.0


# ============================================================
# MASQUES (annexe III, fiche 3.2) — les calculs sont dans moteur/masques.py
# ============================================================
@dataclass
class MasqueProcheHorizontal:
    """Débord horizontal infini au-dessus du composant (balcon, casquette). Composant vertical seulement."""
    debord_m: float             # dhm : profondeur du débord
    distance_m: float = 0.0     # dhp : distance entre le haut du composant et le débord

    def __post_init__(self):
        if self.debord_m < 0 or self.distance_m < 0:
            raise ValueError("Masque proche horizontal : débord et distance doivent être positifs ou nuls")


@dataclass
class MasqueProcheVertical:
    """Joue verticale infinie à gauche ou à droite du composant (refend, loggia). Composant vertical seulement."""
    cote: str                   # « gauche » ou « droite », vu de dehors, face à la paroi
    debord_m: float             # dvg ou dvd : profondeur de la joue
    distance_m: float = 0.0     # dpg ou dpd : distance entre le bord du composant et la joue

    def __post_init__(self):
        if self.cote not in COTES_MASQUE:
            raise ValueError(f"Masque proche vertical : côté « {self.cote} » inconnu ({', '.join(COTES_MASQUE)})")
        if self.debord_m < 0 or self.distance_m < 0:
            raise ValueError("Masque proche vertical : débord et distance doivent être positifs ou nuls")


@dataclass
class MasqueLointainVertical:
    """Plan vertical éloigné (immeuble en face), parallèle au composant, de hauteur infinie en largeur."""
    distance_m: float           # dE : distance entre le masque et le composant
    hauteur_m: float            # hpE : hauteur du masque au-dessus du centre du composant
    orientation_deg: float = None   # orientation du masque, utile pour un composant horizontal

    def __post_init__(self):
        _exiger_positif(self.distance_m, "Distance du masque lointain")
        self.orientation_deg = ramener_azimut(self.orientation_deg)


@dataclass
class MasqueTranches:
    """Horizon décrit par 36 tranches de 10° : hauteur (°) de l'horizon vu du centre du composant.

    Convention de l'outil : la 1re tranche couvre l'azimut relatif du soleil (par rapport à la normale)
    de −180° à −170°, la 19e de 0° à 10°, la 36e de 170° à 180°.
    """
    hauteurs_deg: list

    def __post_init__(self):
        nombre = int(hyp("masque_tranches_nombre"))
        if len(self.hauteurs_deg) != nombre:
            raise ValueError(f"Masque par tranches : {nombre} hauteurs attendues (reçu : {len(self.hauteurs_deg)})")
        for hauteur in self.hauteurs_deg:
            _exiger_entre(hauteur, 0.0, 90.0, "Hauteur d'horizon d'une tranche")


TYPES_MASQUE = (MasqueProcheHorizontal, MasqueProcheVertical, MasqueLointainVertical, MasqueTranches)


def _controler_composant(composant, libelle):
    """Contrôles communs aux baies et aux parois : angles, dimensions et masques."""
    composant.orientation_deg = ramener_azimut(composant.orientation_deg)
    _exiger_entre(composant.inclinaison_deg, 0.0, 180.0, f"Inclinaison {libelle}")
    for masque in composant.masques:
        if not isinstance(masque, TYPES_MASQUE):
            raise ValueError(f"Masque inconnu sur {libelle} : {masque!r}")
        if isinstance(masque, (MasqueProcheHorizontal, MasqueProcheVertical)):
            if composant.largeur_m is None or composant.hauteur_m is None:
                raise ValueError(f"Masque proche sur {libelle} : largeur et hauteur du composant à renseigner")


@dataclass
class Baie:
    """Baie vitrée d'un groupe."""
    nom: str
    surface_m2: float
    orientation_deg: float
    inclinaison_deg: float = INCLINAISON_VERTICALE
    uw: float = None            # coefficient de transmission thermique en position verticale (W/m².K)
    sw_e: float = None          # facteur solaire global sans protection mobile, conditions E (Th-D)
    sw_c: float = None          # idem, conditions C (Th-BC) ; par défaut sw_e − 0,1 (fiche 5.10, éq. 215)
    sw2_e: float = None         # part réémise de sw_e (grande longueur d'onde et convection) ; défaut : hypothèse
    sw2_c: float = None         # part réémise de sw_c ; Sw1 = Sw − Sw2 (règles Th-Bât, formules 173 à 176)
    uw_horizontal: float = None     # Uw en position horizontale (fiche 5.10, éq. 207) ; par défaut uw
    tl: float = None            # transmission lumineuse
    largeur_m: float = None     # utiles pour les masques proches
    hauteur_m: float = None
    masques: list = field(default_factory=list)

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface de la baie « {self.nom} »")
        _exiger_entre(self.sw_e, 0.0, 1.0, f"Sw-e de la baie « {self.nom} »")
        _exiger_entre(self.sw_c, 0.0, 1.0, f"Sw-c de la baie « {self.nom} »")
        _exiger_entre(self.sw2_e, 0.0, 1.0, f"Sw2-e de la baie « {self.nom} »")
        _exiger_entre(self.sw2_c, 0.0, 1.0, f"Sw2-c de la baie « {self.nom} »")
        _exiger_entre(self.tl, 0.0, 1.0, f"Transmission lumineuse de la baie « {self.nom} »")
        if self.uw_horizontal is not None:
            _exiger_positif(self.uw_horizontal, f"Uw horizontal de la baie « {self.nom} »")
        _controler_composant(self, f"la baie « {self.nom} »")


@dataclass
class Paroi:
    """Paroi opaque d'un groupe, donnant sur l'extérieur, le sol ou un local non chauffé."""
    nom: str
    type: str
    surface_m2: float
    u: float = None             # coefficient de transmission thermique Up-C (W/m².K), dans la position du type
    orientation_deg: float = None
    inclinaison_deg: float = None   # par défaut celle du type : mur 90, toiture 0, plancher bas 180
    contact: str = "exterieur"
    b_therm: float = 1.0        # coefficient de réduction des déperditions (fiche 5.17, éq. 295) : local non chauffé
    alpha: float = None         # coefficient d'absorption solaire (Th-Bât : 0,4 clair à 1,0 noir)
    sf_c: float = None          # facteur solaire saisi, conditions C ; sinon calculé (alpha, u)
    sf_e: float = None          # facteur solaire saisi, conditions E ; sinon calculé (alpha, u)
    largeur_m: float = None     # utiles pour les masques proches
    hauteur_m: float = None
    masques: list = field(default_factory=list)

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface de la paroi « {self.nom} »")
        if self.type not in TYPES_PAROI:
            raise ValueError(f"Paroi « {self.nom} » : type « {self.type} » inconnu ({', '.join(TYPES_PAROI)})")
        if self.contact not in CONTACTS_PAROI:
            raise ValueError(f"Paroi « {self.nom} » : contact « {self.contact} » inconnu ({', '.join(CONTACTS_PAROI)})")
        _exiger_entre(self.alpha, 0.0, 1.0, f"Absorption de la paroi « {self.nom} »")
        _exiger_entre(self.sf_c, 0.0, 1.0, f"Sf-c de la paroi « {self.nom} »")
        _exiger_entre(self.sf_e, 0.0, 1.0, f"Sf-e de la paroi « {self.nom} »")
        _exiger_entre(self.b_therm, 0.0, 1.0, f"Coefficient b de la paroi « {self.nom} »")
        if self.inclinaison_deg is None:
            self.inclinaison_deg = INCLINAISON_PAR_TYPE[self.type]
        _controler_composant(self, f"la paroi « {self.nom} »")


@dataclass
class PontThermique:
    """Pont thermique linéique d'un groupe (annexe III, fiche 5.19) : déperdition l × ψ (éq. 305)."""
    nom: str
    longueur_m: float           # l : longueur du pont thermique
    psi: float                  # ψ : coefficient de transmission linéique (W/m.K)

    def __post_init__(self):
        _exiger_positif(self.longueur_m, f"Longueur du pont thermique « {self.nom} »")
        if self.psi < 0:
            raise ValueError(f"Pont thermique « {self.nom} » : ψ doit être positif ou nul (reçu : {self.psi})")


@dataclass
class Brasseur:
    """Un type p de brasseurs d'air de plafond, fixés au bâti (annexe III, fiche 8.32).

    Les calculs sont dans moteur/brasseurs.py. Réglages de la gestion (fiche 8.32, § 8.32.3.2.4) :
      - « manuelle »    : valeurs conventionnelles, rien à saisir ;
      - « thermostat »  : ecart_arret, ecart_max et ecart_declenchement à saisir ;
      - « automatique » : ecart_arret, ecart_max et temperature_declenchement à saisir,
                          ecart_declenchement facultatif (0 par défaut).
    """
    nom: str
    nombre: int                         # Nbr_p : nombre de brasseurs de ce type
    surface_desservie_m2: float         # surface des pièces cloisonnées équipées (donne Ratbr_p)
    debit_max_m3h: float                # Qvair_br_p_max : débit individuel maximal du fabricant
    puissance_max_w: float              # Pelec_br_p_max : puissance individuelle maximale du fabricant
    usage: str = "jour"                 # Usp : « jour », « nuit » ou « jour_et_nuit »
    gestion: str = "manuelle"           # mode_gestion_br_p
    caractere_debit: str = "declaree"   # type_Qvair_br_p_max : certifiée, justifiée ou déclarée
    caractere_puissance: str = "declaree"   # type_Pelec_br_p_max
    ecart_arret: float = None           # Δθop_1_br : arrêt sous V1 − Δθop_1 (°C)
    ecart_max: float = None             # Δθop_2_br : vitesse maximale à partir de V1 + Δθop_2 (°C)
    ecart_declenchement: float = None   # Δθop_3_br : décalage du déclenchement (°C)
    temperature_declenchement: float = None   # θop_dec_br_p_aut, gestion automatique (°C)

    def __post_init__(self):
        if not self.nombre >= 1 or int(self.nombre) != self.nombre:
            raise ValueError(f"Brasseur « {self.nom} » : le nombre doit être un entier ≥ 1 (reçu : {self.nombre})")
        _exiger_positif(self.surface_desservie_m2, f"Surface desservie du brasseur « {self.nom} »")
        _exiger_positif(self.debit_max_m3h, f"Débit maximal du brasseur « {self.nom} »")
        _exiger_positif(self.puissance_max_w, f"Puissance maximale du brasseur « {self.nom} »")
        for nom_champ, valeur, admises in (("usage", self.usage, USAGES_BRASSEUR),
                                           ("gestion", self.gestion, GESTIONS_BRASSEUR),
                                           ("caractere_debit", self.caractere_debit, CARACTERES_VALEUR),
                                           ("caractere_puissance", self.caractere_puissance, CARACTERES_VALEUR)):
            if valeur not in admises:
                raise ValueError(f"Brasseur « {self.nom} » : {nom_champ} « {valeur} » inconnu "
                                 f"({', '.join(admises)})")
        # Réglages exigés par le mode de gestion ; la gestion manuelle est entièrement conventionnelle
        if self.gestion == "thermostat":
            exiges = ("ecart_arret", "ecart_max", "ecart_declenchement")
        elif self.gestion == "automatique":
            exiges = ("ecart_arret", "ecart_max", "temperature_declenchement")
        else:
            exiges = ()
        manquants = [nom_champ for nom_champ in exiges if getattr(self, nom_champ) is None]
        if manquants:
            raise ValueError(f"Brasseur « {self.nom} » : gestion « {self.gestion} », réglages à saisir : "
                             f"{', '.join(manquants)}")
        for nom_champ in ("ecart_arret", "ecart_max", "ecart_declenchement"):
            valeur = getattr(self, nom_champ)
            if valeur is not None and valeur < 0:
                raise ValueError(f"Brasseur « {self.nom} » : {nom_champ} doit être positif ou nul (reçu : {valeur})")


@dataclass
class Groupe:
    """Unité de calcul thermique : un ensemble de locaux à la même température."""
    nom: str
    surface_m2: float           # surface de référence du groupe
    traversant: bool = False    # logements traversants ou non (confort d'été)
    parois: list = field(default_factory=list)
    baies: list = field(default_factory=list)
    volume_m3: float = None     # volume du groupe ; exigé en présence de brasseurs d'air (fiche 8.32, éq. 1657)
    brasseurs: list = field(default_factory=list)
    ponts_thermiques: list = field(default_factory=list)
    debit_ventilation_m3h: float = 0.0      # débit d'air neuf du groupe (m³/h) : débit de base (d'hygiène)
    debit_ventilation_pointe_m3h: float = None     # débit de pointe (grand débit de cuisine), facultatif
    nb_logements: int = None    # nombre de logements du groupe : exigé pour les apports internes (fiche 4.1)
    climatise: bool = False     # groupe refroidi par un système : exclut les brasseurs d'air (fiche 8.32)
    # Inertie (annexe III, fiche 5.21, tableaux 53 et 54) : une classe, ou « personnalisee » et les valeurs
    inertie_quotidienne: str = "moyenne"
    amq_surf: float = None      # surface d'échange quotidienne par m² de groupe (m²/m²), classe personnalisée
    cmq_surf: float = None      # capacité quotidienne par m² de groupe (kJ/K/m²), classe personnalisée
    inertie_sequentielle: str = "defaut"    # « defaut » et « tres_legere » : Cms = Cmq, Ams = Amq
    cms_surf: float = None      # capacité séquentielle (kJ/K/m²), classe personnalisée
    ams_surf: float = None      # surface d'échange séquentielle (m²/m²) ; par défaut selon la classe (Th-Bât)
    inertie_annuelle: str = "defaut"        # « defaut » : Cma = Cms, Ama = Ams
    cma_surf: float = None      # capacité annuelle (kJ/K/m²), classe personnalisée
    ama_surf: float = None      # surface d'échange annuelle (m²/m²) ; par défaut ams_surf

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface du groupe « {self.nom} »")
        if self.debit_ventilation_m3h < 0:
            raise ValueError(f"Groupe « {self.nom} » : débit de ventilation négatif ({self.debit_ventilation_m3h})")
        if self.debit_ventilation_pointe_m3h is not None and \
                self.debit_ventilation_pointe_m3h < self.debit_ventilation_m3h:
            raise ValueError(f"Groupe « {self.nom} » : débit de pointe inférieur au débit de base")
        if self.nb_logements is not None and (self.nb_logements < 1 or int(self.nb_logements) != self.nb_logements):
            raise ValueError(f"Groupe « {self.nom} » : le nombre de logements doit être un entier ≥ 1 "
                             f"(reçu : {self.nb_logements})")
        if self.brasseurs and self.climatise:
            raise ValueError(f"Groupe « {self.nom} » : pas de brasseurs d'air dans un groupe climatisé "
                             "(fiche 8.32, domaine de validité)")
        # Classes d'inertie connues, et valeurs exigées par les classes personnalisées
        for libelle, classe, admises, exigees in (
                ("quotidienne", self.inertie_quotidienne, INERTIES_QUOTIDIENNES, ("amq_surf", "cmq_surf")),
                ("séquentielle", self.inertie_sequentielle, INERTIES_SEQUENTIELLES, ("cms_surf", "ams_surf")),
                ("annuelle", self.inertie_annuelle, INERTIES_ANNUELLES, ("cma_surf", "ama_surf"))):
            if classe not in admises:
                raise ValueError(f"Groupe « {self.nom} » : inertie {libelle} « {classe} » inconnue "
                                 f"({', '.join(admises)})")
            if classe == "personnalisee":
                manquantes = [nom_champ for nom_champ in exigees if getattr(self, nom_champ) is None]
                if manquantes:
                    raise ValueError(f"Groupe « {self.nom} » : inertie {libelle} personnalisée, valeurs à saisir : "
                                     f"{', '.join(manquantes)}")
        for nom_champ in ("amq_surf", "cmq_surf", "cms_surf", "ams_surf", "cma_surf", "ama_surf"):
            if getattr(self, nom_champ) is not None:
                _exiger_positif(getattr(self, nom_champ), f"{nom_champ} du groupe « {self.nom} »")
        if self.volume_m3 is not None:
            _exiger_positif(self.volume_m3, f"Volume du groupe « {self.nom} »")
        if self.brasseurs and self.volume_m3 is None:
            raise ValueError(f"Groupe « {self.nom} » : le volume est exigé en présence de brasseurs d'air")

    @property
    def surface_baies_m2(self):
        return sum(baie.surface_m2 for baie in self.baies)

    @property
    def surface_parois_m2(self):
        return sum(paroi.surface_m2 for paroi in self.parois)


@dataclass
class Zone:
    """Partie de bâtiment d'un seul usage, découpée en groupes."""
    nom: str
    usage: str = "logement_collectif"
    groupes: list = field(default_factory=list)

    def __post_init__(self):
        if self.usage not in USAGES:
            raise ValueError(f"Zone « {self.nom} » : usage « {self.usage} » inconnu ({', '.join(USAGES)})")

    @property
    def surface_m2(self):
        """Surface de référence de la zone : somme de celles de ses groupes."""
        return sum(groupe.surface_m2 for groupe in self.groupes)


@dataclass
class Batiment:
    """Bâtiment : une ou plusieurs zones."""
    nom: str
    zones: list = field(default_factory=list)

    @property
    def surface_m2(self):
        return sum(zone.surface_m2 for zone in self.zones)

    @property
    def groupes(self):
        """Tous les groupes du bâtiment, dans l'ordre des zones."""
        return [groupe for zone in self.zones for groupe in zone.groupes]


@dataclass
class Projet:
    """Projet : un site (zone climatique, altitude) et ses bâtiments."""
    nom: str
    zone_climatique: str
    altitude_m: float = 0.0
    batiments: list = field(default_factory=list)

    def __post_init__(self):
        if self.zone_climatique not in ZONES_CLIMATIQUES:
            raise ValueError(f"Projet « {self.nom} » : zone climatique « {self.zone_climatique} » inconnue "
                             f"({', '.join(ZONES_CLIMATIQUES)})")
        if self.altitude_m < 0:
            raise ValueError(f"Projet « {self.nom} » : altitude négative ({self.altitude_m} m)")
