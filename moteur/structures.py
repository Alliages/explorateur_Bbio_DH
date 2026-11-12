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

 Version 0.8.0 : identité et géométrie seulement. Les données
 thermiques (inertie, ponts thermiques, ventilation, protections
 solaires) arrivent avec les modules qui les utilisent.

 Conventions d'angle (provisoires, à confirmer avec le module
 solaire 0.8.2) :
   - orientation : azimut de la normale extérieure, en degrés,
     0 = sud, 90 = ouest, −90 = est, ±180 = nord (même repère
     que l'azimut solaire Psi des fichiers météo) ;
   - inclinaison : 90 = paroi verticale, 0 = paroi horizontale.
============================================================
"""

from dataclasses import dataclass, field

from config.reglages import USAGES, ZONES_CLIMATIQUES

# ============================================================
# VALEURS ADMISES
# ============================================================
TYPES_PAROI = ("mur", "toiture", "plancher_bas")
CONTACTS_PAROI = ("exterieur", "sol", "local_non_chauffe")
INCLINAISON_VERTICALE = 90.0


def _exiger_positif(valeur, nom):
    """Erreur claire si une grandeur qui doit être strictement positive ne l'est pas."""
    if not valeur > 0:
        raise ValueError(f"{nom} doit être strictement positif (reçu : {valeur})")


@dataclass
class Baie:
    """Baie vitrée d'un groupe."""
    nom: str
    surface_m2: float
    orientation_deg: float
    inclinaison_deg: float = INCLINAISON_VERTICALE
    uw: float = None            # coefficient de transmission thermique (W/m².K)
    sw: float = None            # facteur solaire, sans protection mobile
    tl: float = None            # transmission lumineuse

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface de la baie « {self.nom} »")


@dataclass
class Paroi:
    """Paroi opaque d'un groupe, donnant sur l'extérieur, le sol ou un local non chauffé."""
    nom: str
    type: str
    surface_m2: float
    u: float = None             # coefficient de transmission thermique (W/m².K)
    orientation_deg: float = None
    inclinaison_deg: float = INCLINAISON_VERTICALE
    contact: str = "exterieur"

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface de la paroi « {self.nom} »")
        if self.type not in TYPES_PAROI:
            raise ValueError(f"Paroi « {self.nom} » : type « {self.type} » inconnu ({', '.join(TYPES_PAROI)})")
        if self.contact not in CONTACTS_PAROI:
            raise ValueError(f"Paroi « {self.nom} » : contact « {self.contact} » inconnu ({', '.join(CONTACTS_PAROI)})")


@dataclass
class Groupe:
    """Unité de calcul thermique : un ensemble de locaux à la même température."""
    nom: str
    surface_m2: float           # surface de référence du groupe
    traversant: bool = False    # logements traversants ou non (confort d'été)
    parois: list = field(default_factory=list)
    baies: list = field(default_factory=list)

    def __post_init__(self):
        _exiger_positif(self.surface_m2, f"Surface du groupe « {self.nom} »")

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
