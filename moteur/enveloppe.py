r"""
============================================================
 ENVELOPPE — coefficients de transmission thermique
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 5.10 (C_BAT_Baie vitrée)    : éq. 207, 210 ;
   fiche 5.17 (C_BAT_paroi opaque)   : § 5.17.3.4, éq. 294 à 296 ;
   fiche 5.19 (C_BAT_pont thermique) : éq. 305.

 Le U d'une baie ou d'une paroi dépend de son inclinaison,
 parce que les échanges de surface ne sont pas les mêmes pour
 un flux horizontal, ascendant ou descendant :

     U
     ^
     |  horizontal
     |-----------\
     |            \
     |             \------------  vertical
     +-----|--------|-----------> inclinaison
     0     30       60        90

   - baie : U horizontal jusqu'à 30°, U vertical à partir de
     60°, interpolation linéaire entre les deux (éq. 207) ;
   - paroi opaque : même principe, avec en plus le flux
     descendant au-delà de 120° (interpolation) et de 150°
     (éq. 294). Le U saisi est celui de la position du type
     de la paroi (mur : verticale ; toiture : horizontale,
     flux ascendant ; plancher bas : horizontale, flux
     descendant). On en tire la résistance propre de la paroi,
     Rth = 1/U − (Rsi + Rse), puis le U de chaque position
     avec Rsi + Rse = 0,17 (verticale), 0,14 (ascendant) ou
     0,21 (descendant).

 Transmissions globales d'un groupe (W/K) :
   baies            Hg_es   = somme A × U          (éq. 210, sans protection mobile ni espace tampon)
   parois opaques   H_TH,k  = somme A × b × U      (éq. 295)
   ponts thermiques H_TH,pt = somme l × psi        (éq. 305)

 Hypothèses de l'outil : voir docs/audit.md (0.8.4).
============================================================
"""

from moteur.hypotheses import hyp

# Position pour laquelle le U d'une paroi est saisi, selon son type (Incl_k de la fiche 5.17)
POSITION_PAR_TYPE = {"mur": "verticale", "toiture": "ascendant", "plancher_bas": "descendant"}


def _interpoler(x, x_a, y_a, x_b, y_b):
    """Valeur en x de la droite passant par (x_a, y_a) et (x_b, y_b)."""
    return y_a + (y_b - y_a) * (x - x_a) / (x_b - x_a)


def u_baie(baie):
    """U de la baie sans protection mobile (W/m².K), selon son inclinaison (fiche 5.10, éq. 207).

    Sans Uw horizontal saisi, le Uw vertical est repris tel quel (hypothèse de l'outil).
    Au-delà de 90° (baie tournée vers le bas, cas non décrit par la fiche), la baie est traitée comme verticale.
    """
    if baie.uw is None:
        raise ValueError(f"Baie « {baie.nom} » : uw à renseigner")
    u_vertical = baie.uw
    u_horizontal = baie.uw_horizontal if baie.uw_horizontal is not None else baie.uw
    beta, beta1, beta2 = baie.inclinaison_deg, hyp("inclinaison_beta1"), hyp("inclinaison_beta2")
    if beta < beta1:
        return u_horizontal
    if beta < beta2:
        return _interpoler(beta, beta1, u_horizontal, beta2, u_vertical)
    return u_vertical


def u_paroi(paroi):
    """U de la paroi opaque (W/m².K), selon son inclinaison (fiche 5.17, § 5.17.3.4 et éq. 294).

    Une paroi posée dans la position de son type garde le U saisi.
    """
    if paroi.u is None:
        raise ValueError(f"Paroi « {paroi.nom} » : u à renseigner")
    # Résistance propre de la paroi, hors résistances superficielles de la position de saisie
    r_th = 1.0 / paroi.u - hyp(f"resistances_superficielles_{POSITION_PAR_TYPE[paroi.type]}")
    if r_th < 0:
        raise ValueError(f"Paroi « {paroi.nom} » : U = {paroi.u} W/m².K dépasse ce que permettent les seules "
                         "résistances superficielles")
    u_vertical = 1.0 / (r_th + hyp("resistances_superficielles_verticale"))
    u_ascendant = 1.0 / (r_th + hyp("resistances_superficielles_ascendant"))
    u_descendant = 1.0 / (r_th + hyp("resistances_superficielles_descendant"))
    beta = paroi.inclinaison_deg
    beta1, beta2 = hyp("inclinaison_beta1"), hyp("inclinaison_beta2")
    beta3, beta4 = hyp("inclinaison_beta3"), hyp("inclinaison_beta4")
    if beta < beta1:
        return u_ascendant
    if beta < beta2:
        return _interpoler(beta, beta1, u_ascendant, beta2, u_vertical)
    if beta < beta3:
        return u_vertical
    if beta < beta4:
        # La formule imprimée donne Uhoriz,des à beta3 et Uvert à beta4 : inversion corrigée (docs/audit.md)
        return _interpoler(beta, beta3, u_vertical, beta4, u_descendant)
    return u_descendant


def transmission_baies(groupe):
    """Hg_es = H_TH,b (W/K) : somme des A × U des baies du groupe (éq. 210 et 341, sans protection mobile)."""
    return sum(baie.surface_m2 * u_baie(baie) for baie in groupe.baies)


def transmission_parois(groupe):
    """H_TH,k (W/K) : somme des A × b × U des parois opaques du groupe (éq. 295)."""
    return sum(paroi.surface_m2 * paroi.b_therm * u_paroi(paroi) for paroi in groupe.parois)


def transmission_ponts(groupe):
    """H_TH,pt (W/K) : somme des l × psi des ponts thermiques du groupe (éq. 305)."""
    return sum(pont.longueur_m * pont.psi for pont in groupe.ponts_thermiques)
