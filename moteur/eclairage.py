r"""
============================================================
 ÉCLAIRAGE — lumière naturelle et consommation d'éclairage
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 5.10 (C_BAT_Baie vitrée), éq. 225, 226, 231 à 233 :
     flux lumineux transmis par les baies ;
   fiche 7.1 (C_ECL_éclairage), § 7.1.3 : éclairement naturel
     intérieur, éq. 789, figure 86 (éclairage résidentiel).

 En habitation, le système d'éclairage est conventionnel : la
 consommation ne dépend que des baies.

 Chaîne de calcul, heure par heure :
   1. flux lumineux entrant par chaque baie (lumens), sans
      protection mobile, baie non diffusante :
        Flt1 = A × Tl × éclairement direct      (éq. 231)
        Flt2 = A × Tl × éclairement diffus      (éq. 232)
        Flt3 = A × Tl × éclairement réfléchi    (éq. 233)
      les éclairements étant ceux reçus par la baie, masques
      compris (moteur/solaire.py) ;
   2. éclairement naturel du plan utile (lux) :
        Einat = (K1 × Flt1 + K2 × Flt2 + K3 × Flt3) / surface
      K1, K2, K3 traduisant la vue directe du ciel par la baie,
      le renvoi par le plafond et les réflexions entre parois ;
   3. taux d'utilisation de l'éclairage selon la lumière
      naturelle, C2 (figure 86) :

        C2
        1 |-----.                    A (0 ; 1)    B (100 ; 1)
          |      \                   G (200 ; 0,05)
          |       \                  J (2 800 ; 0)
     0,05 |        '-----.....____
        0 +-----|----|------------|---> Einat (lux)
               100  200         2800

   4. consommation (éq. 789), quand l'éclairage est autorisé
      par le scénario « eclairage » :
        Cecl = 1 W/m² × C1 × C2 × surface      avec C1 = 0,9
   5. cette consommation est rendue au groupe en chaleur,
      moitié par convection, moitié par rayonnement.

 Hypothèses de l'outil : voir docs/audit.md (0.8.6).
============================================================
"""

import numpy as np
import pandas as pd

from moteur.hypotheses import hyp
from moteur.solaire import environnement_proche


def flux_lumineux_baie(baie, meteo):
    """Flux lumineux transmis au groupe par une baie sans protection mobile (lumens), heure par heure.

    Colonnes flt1 (direct), flt2 (diffus), flt3 (réfléchi par le sol) : fiche 5.10, éq. 231 à 233, avec
    Tlid = 0 (baie non diffusante) et le même facteur Tl pour les trois composantes (éq. 226).
    """
    if baie.tl is None:
        raise ValueError(f"Baie « {baie.nom} » : transmission lumineuse tl à renseigner")
    env = environnement_proche(meteo, baie)
    facteur = baie.surface_m2 * baie.tl
    return pd.DataFrame({"flt1": facteur * env["erp_m"], "flt2": facteur * env["efp_m"],
                         "flt3": facteur * env["errp_m"]}, index=meteo.index)


def coefficients_einat():
    """(K1, K2, K3) : éclairement du plan utile par lumen entrant, par m² de groupe (fiche 7.1, K1vn à K3vn).

        réflexion moyenne  Ro = (Rosol + Rmursol × Romurs + Roplafond) / (2 + Rmursol)
        interréflexions    I  = Ro / (1 − Ro) / 4,5
        K1 = Rosol × I                                   direct : il doit d'abord être renvoyé par le sol
        K2 = FFbpu_h + I                                 diffus : vu directement du plan utile
        K3 = Roplafond × FFplpu_h + Roplafond × I        réfléchi : renvoyé par le plafond
    """
    ro_sol, ro_murs, ro_plafond = hyp("ecl_reflexion_sol"), hyp("ecl_reflexion_murs"), hyp("ecl_reflexion_plafond")
    ratio_murs = hyp("ecl_ratio_murs_sol")
    ro_moyen = (ro_sol + ratio_murs * ro_murs + ro_plafond) / (2.0 + ratio_murs)
    interreflexions = ro_moyen / (1.0 - ro_moyen) / hyp("ratio_atparois")
    return (ro_sol * interreflexions,
            hyp("ecl_forme_baie") + interreflexions,
            ro_plafond * hyp("ecl_forme_plafond") + ro_plafond * interreflexions)


def eclairement_naturel(groupe, meteo):
    """Éclairement naturel intérieur du groupe, Einat (lux), heure par heure (fiche 7.1, baies de type 2).

    Toute la surface du groupe est réputée avoir accès à la lumière naturelle (Ratio_ecl_nat = 1 en
    habitation). Sans baie, l'éclairement est nul.
    """
    flux = np.zeros((len(meteo), 3))
    for baie in groupe.baies:
        flux += flux_lumineux_baie(baie, meteo)[["flt1", "flt2", "flt3"]].to_numpy()
    einat = flux @ np.array(coefficients_einat()) / groupe.surface_m2
    return pd.Series(einat, index=meteo.index, name="einat")


def coefficient_c2(einat):
    """C2 : taux d'utilisation de l'éclairage selon l'éclairement naturel (fiche 7.1, figure 86, habitation)."""
    points_einat = [0.0, hyp("ecl_c2_einat_plein"), hyp("ecl_c2_einat_coude"), hyp("ecl_c2_einat_nul")]
    points_c2 = [1.0, 1.0, hyp("ecl_c2_valeur_coude"), 0.0]
    return np.interp(einat, points_einat, points_c2)


def eclairage_groupe(groupe, meteo, autorisation):
    """Consommation d'éclairage du groupe et chaleur rendue, heure par heure (fiche 7.1, éq. 789).

    autorisation : scénario « eclairage » déroulé sur l'année (1 = éclairage autorisé, 0 = non).
    Colonnes : einat (lux), c2, cecl_wh (consommation de l'heure, Wh), phi_conv et phi_rad (W).
    """
    einat = eclairement_naturel(groupe, meteo).to_numpy()
    c2 = coefficient_c2(einat)
    autorise = np.asarray(autorisation, dtype=float) > 0
    if autorise.shape != (len(meteo),):
        raise ValueError(f"autorisation d'éclairage : {len(meteo)} valeurs attendues")
    cecl = np.where(autorise, hyp("ecl_puissance_habitation") * hyp("ecl_c1_habitation") * c2 * groupe.surface_m2,
                    0.0)
    return pd.DataFrame({"einat": einat, "c2": c2, "cecl_wh": cecl,
                         "phi_conv": hyp("ecl_part_convective") * cecl,
                         "phi_rad": hyp("ecl_part_radiative") * cecl}, index=meteo.index)
