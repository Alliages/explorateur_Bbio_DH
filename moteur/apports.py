"""
============================================================
 APPORTS INTERNES — occupants et usages du logement collectif
============================================================
 Source : annexe III de l'arrêté du 4 août 2021,
   fiche 4.1 (C_EIN_Scénarios conventionnels), éq. 33 à 42 ;
   valeurs : classeur des scénarios conventionnels
   (donnees/scenarios/logement_collectif_parametres.csv).

 En logement collectif, la zone compte deux locaux : les
 logements (90 % de la surface) et la circulation (10 %).

 Chaîne de calcul :
   1. surface habitable : Ahab = 0,9 × surface du groupe (éq. 33) ;
      surface moyenne d'un logement : Algt = Ahab / Nblgt (éq. 34) ;
   2. occupation maximale d'un logement (éq. 35) :
        Nmax = 1                              si Algt < 10 m²
             = 1,75 − 0,01875 × (50 − Algt)   de 10 à 50 m²
             = 0,035 × Algt                   au-delà
      adultes équivalents du groupe (éq. 36) :
        Nadeq = Nblgt × Nmax                         si Nmax < 1,75
              = Nblgt × (1,75 + 0,3 × (Nmax − 1,75)) sinon
   3. occupants présents à l'heure h (éq. 37) :
        Nocc = Nadeq × occupation de la zone × taux d'occupation
   4. chaleur des occupants : Nocc × 90 W ;
      chaleur des usages : surface du local × 5,7 W/m² × ratio
      horaire (éq. 41) ;
   5. chaque apport est émis pour moitié par convection et
      pour moitié par rayonnement (éq. 39 et 41).

 L'éclairage est traité à part (moteur/eclairage.py).
 Hypothèses de l'outil : voir docs/audit.md (0.8.6).
============================================================
"""

import pandas as pd

from moteur.hypotheses import hyp

# Les deux locaux du logement collectif : préfixe des scénarios et des paramètres du classeur
LOCAUX = ("logements", "circulation")


def nombre_adultes_equivalents(surface_habitable_m2, nb_logements):
    """Nadeq du logement collectif (fiche 4.1, éq. 34 à 36)."""
    surface_logement = surface_habitable_m2 / nb_logements
    if surface_logement < hyp("nadeq_surface_min"):
        n_max = 1.0
    elif surface_logement < hyp("nadeq_surface_max"):
        n_max = hyp("nadeq_base") - hyp("nadeq_pente") * (hyp("nadeq_surface_max") - surface_logement)
    else:
        n_max = hyp("nadeq_par_m2") * surface_logement
    if n_max >= hyp("nadeq_base"):
        n_max = hyp("nadeq_base") + hyp("nadeq_reduction") * (n_max - hyp("nadeq_base"))
    return nb_logements * n_max


def apports_internes(groupe, scenarios, calendrier):
    """Apports internes du groupe, heure par heure, hors éclairage (fiche 4.1, éq. 37 à 42).

    Colonnes :
        occupe          1 si la zone est occupée (scénario « occupation »), 0 sinon
        n_occ           nombre d'occupants présents (adultes équivalents)
        phi_occupants   chaleur dégagée par les occupants (W)
        phi_usages      chaleur dégagée par les usages (W)
        phi_conv        part convective de la somme (W)
        phi_rad         part radiative de la somme (W)
    """
    if groupe.nb_logements is None:
        raise ValueError(f"Groupe « {groupe.nom} » : nb_logements à renseigner pour les apports internes")
    p = scenarios.parametres
    occupe = (scenarios.derouler("occupation", calendrier) > 0).astype(float)

    # Occupants : seuls les logements en ont (éq. 37) ; la circulation n'a ni occupant ni usage en 2026
    surface_habitable = p["logements_ratio_surface"] * groupe.surface_m2
    n_adeq = nombre_adultes_equivalents(surface_habitable, groupe.nb_logements)
    n_occ = n_adeq * occupe * scenarios.derouler("logements_taux_occupation", calendrier)
    phi_occupants = n_occ * p["logements_chaleur_occupant"]

    # Usages : puissance surfacique du local × sa surface × ratio horaire (éq. 41), sommée sur les locaux (éq. 42)
    phi_usages = 0.0
    for local in LOCAUX:
        surface_local = p[f"{local}_ratio_surface"] * groupe.surface_m2
        phi_usages = phi_usages + (surface_local * p[f"{local}_apports_chaleur"]
                                   * scenarios.derouler(f"{local}_apports_chaleur", calendrier))

    part_conv = hyp("part_convective_apports")
    total = phi_occupants + phi_usages
    return pd.DataFrame({"occupe": occupe, "n_occ": n_occ, "phi_occupants": phi_occupants,
                         "phi_usages": phi_usages, "phi_conv": part_conv * total,
                         "phi_rad": (1.0 - part_conv) * total}, index=calendrier.index)
