"""
============================================================
 MASQUES — facteurs d'affaiblissement du rayonnement solaire
============================================================
 Source : annexe III, fiche 3.2 (C_EEX_environnement_proche).

 Chaque masque donne, heure par heure, deux facteurs entre 0 et 1 :
   f_dir  sur le rayonnement direct (et l'éclairement direct) ;
   f_dif  sur le rayonnement diffus (et l'éclairement diffus).
 Le rayonnement réfléchi par le sol n'est jamais masqué (éq. 25).
 Plusieurs masques se combinent par produit (éq. 23 et 24).

 Notations (angles en radians dans les calculs) :
   gamma  hauteur du soleil ;
   phi    azimut du soleil par rapport à la normale du composant,
          phi = psi − alpha, ramené dans [−pi ; pi[ ;
   beta   inclinaison du composant (pi/2 = vertical).

 Masques traités (0.8.2) :
   - proche horizontal : direct (éq. 20) et diffus (éq. 21) ;
   - proches verticaux gauche et droit : direct (éq. 19) ;
   - lointain défini par un plan vertical : direct (éq. 22) ;
   - lointain par 36 tranches azimutales : direct.
 Les masques proches ne s'appliquent qu'aux composants verticaux ;
 pour les autres, leurs facteurs valent 1 (fiche 3.2).
 Arbres à feuilles caduques : non traités (voir ROADMAP.md).
============================================================
"""

import numpy as np

from moteur.hypotheses import hyp
from moteur.structures import (MasqueLointainVertical, MasqueProcheHorizontal, MasqueProcheVertical,
                               MasqueTranches)

# Tolérance pour reconnaître un composant vertical (inclinaison saisie en degrés)
TOLERANCE_VERTICAL_DEG = 1e-9


def est_vertical(inclinaison_deg):
    """Vrai si le composant est vertical (beta = pi/2) : seule inclinaison où les masques proches agissent."""
    return abs(inclinaison_deg - 90.0) < TOLERANCE_VERTICAL_DEG


def azimut_relatif(psi, alpha):
    """phi = psi − alpha (rad), ramené dans [−pi ; pi[."""
    return (psi - alpha + np.pi) % (2.0 * np.pi) - np.pi


def _limiter(valeur):
    """Min[Max(0 ; valeur) ; 1]."""
    return np.clip(valeur, 0.0, 1.0)


# ============================================================
# MASQUES PROCHES (composant vertical seulement)
# ============================================================
def facteur_proche_horizontal_dir(masque, gamma, phi, hauteur_m):
    """Éq. 20 : part ensoleillée du composant sous un débord horizontal.

    Ombre portée sur la façade : dh = dhm × tan(gamma) / cos(phi) (tangente de l'angle de profil).
    F = Min[Max(0 ; 1 − (dh − dhp) / hp) ; 1].
    """
    cos_phi = np.cos(phi)
    entree = cos_phi >= hyp("seuil_entree_soleil")
    if masque.debord_m <= 0:
        return np.ones_like(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        dh = np.maximum(0.0, masque.debord_m * np.tan(gamma) / np.where(entree, cos_phi, 1.0))
    facteur = _limiter(1.0 - (dh - masque.distance_m) / hauteur_m)
    return np.where(entree, facteur, 1.0)


def facteur_proche_horizontal_dif(masque, hauteur_m):
    """Éq. 21 : part du ciel vue du centre du composant sous un débord horizontal.

    theta_g = arctan((dhp + hp/2) / dhm) en degrés : angle entre l'horizontale et le bord du débord,
    vu du centre du composant ; F = theta_g / 90.
    """
    if masque.debord_m <= 0:
        return 1.0
    theta_g = np.degrees(np.arctan((masque.distance_m + hauteur_m / 2.0) / masque.debord_m))
    return theta_g / 90.0


def facteur_proche_vertical_dir(masque, phi, largeur_m):
    """Éq. 19 : part ensoleillée du composant à côté d'une joue verticale.

    Masque gauche (vu de dehors) : ombre quand phi > 0, dl = Max(0 ; dv × tan(phi)).
    Masque droit : ombre quand phi < 0, dl = Max(0 ; −dv × tan(phi)).
    F = Min[Max(0 ; 1 − (dl − dp) / lp) ; 1].
    """
    cos_phi = np.cos(phi)
    entree = cos_phi >= hyp("seuil_entree_soleil")
    if masque.debord_m <= 0:
        return np.ones_like(phi)
    signe = 1.0 if masque.cote == "gauche" else -1.0
    tan_phi = np.tan(np.where(entree, phi, 0.0))
    dl = np.maximum(0.0, signe * masque.debord_m * tan_phi)
    facteur = _limiter(1.0 - (dl - masque.distance_m) / largeur_m)
    return np.where(entree, facteur, 1.0)


# ============================================================
# MASQUES LOINTAINS (toute inclinaison)
# ============================================================
def facteur_lointain_vertical_dir(masque, gamma, phi):
    """Éq. 22 : tout ou rien derrière un plan vertical éloigné.

    Hauteur du rayon au droit du masque : dhE = dE × tan(gamma) / cos(phi).
    Soleil visible (F = 1) si dhE > hpE, caché (F = 0) sinon.
    """
    cos_phi = np.cos(phi)
    entree = cos_phi >= hyp("seuil_entree_soleil")
    if masque.hauteur_m <= 0:
        return np.ones_like(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        dh_e = masque.distance_m * np.tan(gamma) / np.where(entree, cos_phi, 1.0)
    facteur = np.where(dh_e > masque.hauteur_m, 1.0, 0.0)
    return np.where(entree, facteur, 1.0)


def facteur_tranches_dir(masque, gamma, phi):
    """Masque par tranches azimutales : soleil visible si sa hauteur dépasse l'horizon de sa tranche.

    Tranche de l'heure : indice = partie entière de (phi + 180°) / 10°, de 0 (−180°) à 35 (170° à 180°).
    """
    nombre = int(hyp("masque_tranches_nombre"))
    largeur_tranche = 360.0 / nombre
    indice = np.floor((np.degrees(phi) + 180.0) / largeur_tranche).astype(int)
    indice = np.clip(indice, 0, nombre - 1)
    horizon = np.asarray(masque.hauteurs_deg, dtype=float)[indice]
    return np.where(np.degrees(gamma) > horizon, 1.0, 0.0)


# ============================================================
# COMBINAISON (éq. 23 à 25)
# ============================================================
def facteurs_masques(composant, gamma, psi):
    """Facteurs globaux (f_dir, f_dif) des masques d'une baie ou d'une paroi, heure par heure.

    gamma, psi : hauteur et azimut du soleil (rad), tableaux numpy.
    Sans masque, les deux facteurs valent 1.
    """
    f_dir = np.ones_like(gamma, dtype=float)
    f_dif = np.ones_like(gamma, dtype=float)
    if not composant.masques:
        return f_dir, f_dif

    vertical = est_vertical(composant.inclinaison_deg)
    for masque in composant.masques:
        # Orientation de référence : celle du masque si elle est donnée (composant horizontal), sinon celle
        # du composant. Une orientation est indispensable pour situer un masque (fiche 5.10, note 2).
        orientation = getattr(masque, "orientation_deg", None)
        if orientation is None:
            orientation = composant.orientation_deg
        if orientation is None:
            raise ValueError(f"« {composant.nom} » : orientation à renseigner pour appliquer ses masques")
        phi = azimut_relatif(psi, np.radians(orientation))

        if isinstance(masque, MasqueProcheHorizontal):
            if vertical:
                f_dir = f_dir * facteur_proche_horizontal_dir(masque, gamma, phi, composant.hauteur_m)
                f_dif = f_dif * facteur_proche_horizontal_dif(masque, composant.hauteur_m)
        elif isinstance(masque, MasqueProcheVertical):
            if vertical:
                f_dir = f_dir * facteur_proche_vertical_dir(masque, phi, composant.largeur_m)
        elif isinstance(masque, MasqueLointainVertical):
            f_dir = f_dir * facteur_lointain_vertical_dir(masque, gamma, phi)
        elif isinstance(masque, MasqueTranches):
            f_dir = f_dir * facteur_tranches_dir(masque, gamma, phi)
    return f_dir, f_dif
