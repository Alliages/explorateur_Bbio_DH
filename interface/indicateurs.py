"""
============================================================
 INDICATEURS DU PROJET — chiffres de la boîte, sans calcul
============================================================
 Grandeurs que l'on lit sur la forme et l'enveloppe saisies,
 avant tout calcul annuel : compacité, taux de vitrage… Elles
 s'affichent dans le cartouche du dessin (bande de droite,
 interface/axonometrie.dessiner_cartouche) ; la boîte
 « Indicateurs », au-dessus du dessin, fait cocher celles que
 l'on veut voir (app.py).

     INDICATEURS (registre, dans l'ordre d'affichage)
          │  cle, libellé, calcul(boîte) → texte, coché d'office
          ▼
     valeurs(boite, cles) → [(libellé, texte)] → cartouche

 Ajouter un indicateur : une fonction qui reçoit la boîte
 (interface/saisie.Boite) et rend le texte à afficher, une
 ligne de plus dans INDICATEURS, et son aide dans
 interface/textes/aides.csv (clé « indicateur_<cle> »). Rien
 d'autre à changer : la boîte à cocher et le cartouche suivent.

 Surfaces : celles du groupe du moteur (construire_projet), une
 paroi adiabatique n'étant pas déperditive.

 Ce fichier ne dépend pas de Streamlit.
============================================================
"""

from dataclasses import dataclass
from typing import Callable

from interface.briques.graphiques import nombre
from interface.saisie import construire_projet, point_cardinal

# ============================================================
# RÉGLAGES
# ============================================================
PREFIXE_AIDE = "indicateur_"        # clé de l'aide d'un indicateur dans aides.csv : « indicateur_compacite »
# Points cardinaux en abrégé (le cartouche est étroit)
ABREGES = {"sud": "S", "sud-ouest": "SO", "ouest": "O", "nord-ouest": "NO", "nord": "N", "nord-est": "NE",
           "est": "E", "sud-est": "SE"}


# ============================================================
# GRANDEURS DE LA BOÎTE
# ============================================================
def _groupe(boite):
    """Le groupe du moteur décrit par la boîte : ses parois, baies et ponts thermiques."""
    return construire_projet(boite).batiments[0].zones[0].groupes[0]


def surface_deperditive_m2(boite):
    """Parois et baies sur l'extérieur ou le sol (m²) : murs, baies, toiture, plancher bas ; sans les parois
    adiabatiques."""
    groupe = _groupe(boite)
    return sum(p.surface_m2 for p in groupe.parois) + sum(b.surface_m2 for b in groupe.baies)


def surface_baies_m2(boite):
    return sum(facade["baies_m2"] for facade in boite.facades())


def u_moyen(boite):
    """Coefficient moyen de l'enveloppe (W/m².K) : (Σ U.A des parois et des baies + Σ ψ.l des ponts thermiques)
    / surface déperditive ; U des baies sans leur protection. Proche de l'Ubât, sans ses coefficients b."""
    groupe = _groupe(boite)
    deperditions = (sum(p.u * p.surface_m2 for p in groupe.parois) + sum(b.uw * b.surface_m2 for b in groupe.baies)
                    + sum(pont.psi * pont.longueur_m for pont in groupe.ponts_thermiques))
    surface = sum(p.surface_m2 for p in groupe.parois) + sum(b.surface_m2 for b in groupe.baies)
    return deperditions / surface if surface > 0 else 0.0


# ============================================================
# TEXTES AFFICHÉS
# ============================================================
def _compacite(boite):
    return nombre(surface_deperditive_m2(boite) / boite.surface_habitable_m2, 2, "m²/m²")


def _taux_vitrage(boite):
    return nombre(100.0 * surface_baies_m2(boite) / boite.surface_habitable_m2, 0, "%")


def _part_vitree_facades(boite):
    facades = [f for f in boite.facades() if not f["adiabatique"]]
    surface = sum(f["surface_m2"] for f in facades)
    return nombre(100.0 * surface_baies_m2(boite) / surface, 0, "%") if surface > 0 else "aucune façade"


def _baies_par_orientation(boite):
    """Surface de baies de chaque point cardinal vitré, en abrégé, dans l'ordre des façades (« S 18 · N 18 m² »)."""
    surfaces = {}
    for facade in boite.facades():
        if facade["baies_m2"] > 0:
            point = ABREGES[point_cardinal(facade["orientation_deg"])]
            surfaces[point] = surfaces.get(point, 0.0) + facade["baies_m2"]
    if not surfaces:
        return "aucune baie"
    return " · ".join(f"{point} {nombre(surface, 0)}" for point, surface in surfaces.items()) + " m²"


@dataclass(frozen=True)
class Indicateur:
    cle: str
    libelle: str                            # court : il tient dans le cartouche, avec sa valeur
    calcul: Callable                        # boîte → texte affiché (nombre et unité)
    coche: bool = False                     # affiché à l'ouverture de la page


# Registre, dans l'ordre du cartouche et de la boîte à cocher
INDICATEURS = (
    Indicateur("compacite", "Compacité", _compacite, coche=True),
    Indicateur("taux_vitrage", "Baies / surface habitable", _taux_vitrage, coche=True),
    Indicateur("part_vitree_facades", "Baies / façades", _part_vitree_facades),
    Indicateur("surface_habitable", "Surface habitable", lambda boite: nombre(boite.surface_habitable_m2, 0, "m²")),
    Indicateur("volume", "Volume habitable", lambda boite: nombre(boite.volume_m3, 0, "m³")),
    Indicateur("surface_deperditive", "Surface déperditive",
               lambda boite: nombre(surface_deperditive_m2(boite), 0, "m²")),
    Indicateur("baies_orientation", "Baies", _baies_par_orientation),
    Indicateur("u_moyen", "U moyen de l'enveloppe", lambda boite: nombre(u_moyen(boite), 2, "W/m².K")),
)
PAR_CLE = {indicateur.cle: indicateur for indicateur in INDICATEURS}
COCHES_D_OFFICE = tuple(indicateur.cle for indicateur in INDICATEURS if indicateur.coche)


def valeurs(boite, cles):
    """[(libellé, texte)] des indicateurs demandés, dans l'ordre du registre ; une clé inconnue est ignorée (choix
    gardé d'une version antérieure). Une boîte que le moteur refuse ne donne rien : le message d'erreur est
    affiché avec les résultats."""
    try:
        return [(indicateur.libelle, indicateur.calcul(boite)) for indicateur in INDICATEURS
                if indicateur.cle in cles]
    except ValueError:
        return []
