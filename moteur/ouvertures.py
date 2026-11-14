r"""
============================================================
 OUVERTURES — surventilation naturelle par les baies ouvertes
============================================================
 Source : annexe III de l'arrêté du 4 août 2021, fiche 5.13
   (C_BAT_Surventilation naturelle par ouverture des baies),
   éq. 240 à 256, tableaux 42 à 44, figures 61 à 63 ;
   § 5.13.3.1.2 : cas du mode Th-B (calcul du Bbio).

 Deux étapes chaque heure :

 1. RATIO D'OUVERTURE de chaque baie ouvrable (gestion manuelle) :

        Rouv = occupation × Pocc × Cpr × Mod_ext × Rouv_op      (éq. 240)

    Pocc      70 % des baies sont dans des locaux occupés ;
    Cpr       frein du bruit et de la sécurité (tableau 42) :
              1 en BR1 ; en BR2 et BR3 0,7 le jour et 0,3 la
              nuit ; 0,3 en saison de chauffage ;
    Mod_ext   selon la température extérieure (figure 61) :

          1 |        __________
            |       /          |
          0 |______/           |______
            +------|---|-------|-------> θ extérieure
                  10  18   θop + 3 °C

    Rouv_op   selon la température opérative de l'heure
              précédente, avec hystérésis (figure 62) : on ouvre
              entre θouv1 et θouv2, on referme entre θfer1 et
              θfer2, plus bas.

    En mode Th-B, l'ouverture ne sert qu'à modérer le besoin de
    froid : elle n'a lieu qu'en saison de refroidissement, en
    occupation, et jamais quand l'air extérieur approche la
    consigne de refroidissement (à 1 °C près).

 2. DÉBIT D'AIR du groupe, à partir de la surface ouverte :
      non traversant : tirage thermique ou vent (éq. 251) ;
      traversant     : vent entre façades d'orientations
                       différentes, ou tirage (éq. 252 à 254).
    L'air entre à la température extérieure, sans échangeur.

 Hypothèses de l'outil (docs/audit.md, 0.8.12) : la nuit, les
 occupants laissent les baies dans la position du soir ; une
 protection mobile fermée réduit d'autant la surface ouvrable ;
 gestion automatique de l'ouverture non traitée.
============================================================
"""

import numpy as np

from moteur.hypotheses import hyp

SAISON_CHAUFFAGE = 3            # saison propre du groupe : chauffage sans refroidissement (fiche 4.6)
SECONDES_PAR_HEURE = 3600.0
KELVIN = 273.0
INCLINAISON_FACADE_DEG = 60.0   # en dessous, la baie est en toiture : hors du calcul traversant (éq. 252)
SECTEURS = 4                    # quatre orientations globales, pour deux roses décalées de 45° (éq. 253)


# ============================================================
# 1. RATIO D'OUVERTURE (fiche 5.13, éq. 240 à 245)
# ============================================================
def moderation_exterieure(te, theta_op_prec, consigne_fr):
    """Mod_ext_man en mode Th-B : part d'ouverture admise par la température extérieure (figure 61, éq. 244).

    Nul sous 10 °C, croissant jusqu'à 18 °C, plein jusqu'à la température opérative + 3 °C, nul au-delà ; en Th-B
    ces deux bornes sont plafonnées à la consigne de refroidissement − 1 °C.
    """
    bas = hyp("ouv_seuil_exterieur_bas")
    plafond = consigne_fr - hyp("ouv_thb_marge_consigne")
    haut = min(plafond, hyp("ouv_seuil_exterieur_haut"))
    limite = min(plafond, theta_op_prec - hyp("ouv_ecart_exterieur_interieur_manuel"))
    if te < bas or te > limite:
        return 0.0
    if te < haut:
        return (te - bas) / (haut - bas)
    return 1.0


def seuils_ouverture(saison, consigne_fr_confort, ecart_confort_adaptatif):
    """(θouv1, θouv2, θfer1, θfer2) du profil à hystérésis (éq. 242-243)."""
    decalage = hyp("ouv_decalage_chauffage") if saison == SAISON_CHAUFFAGE else hyp("ouv_decalage_hors_chauffage")
    ouv2 = consigne_fr_confort + ecart_confort_adaptatif + decalage
    return ouv2 - hyp("ouv_ecart_ouv1"), ouv2, ouv2 - hyp("ouv_ecart_fer1"), ouv2 - hyp("ouv_ecart_fer2")


def ratio_selon_temperature(ratio_prec, theta_op_prec, seuils):
    """Rouv_op : profil à hystérésis de la figure 62, à partir du ratio de l'heure précédente."""
    ouv1, ouv2, fer1, fer2 = seuils
    en_ouvrant = float(np.clip((theta_op_prec - ouv1) / (ouv2 - ouv1), 0.0, 1.0))
    en_fermant = float(np.clip((theta_op_prec - fer2) / (fer1 - fer2), 0.0, 1.0))
    return max(en_ouvrant, min(ratio_prec, en_fermant))


def contrainte_ouverture(exposition_bruit, saison, hleg):
    """Cpr en occupation (tableau 42) : frein du bruit et de la sécurité à l'ouverture."""
    if saison == SAISON_CHAUFFAGE:
        return hyp("ouv_cpr_chauffage")
    if exposition_bruit == "BR1":
        return hyp("ouv_cpr_br1")
    de_jour = hyp("ouv_cpr_heure_debut_jour") <= hleg <= hyp("ouv_cpr_heure_fin_jour")
    return hyp("ouv_cpr_bruit_jour") if de_jour else hyp("ouv_cpr_bruit_nuit")


# ============================================================
# 2. DÉBIT PAR LES BAIES OUVERTES (fiche 5.13, éq. 251 à 255)
# ============================================================
def surface_traversante(aouv, orientations_deg, inclinaisons_deg):
    """Sors (m²) : surface équivalente du balayage traversant (éq. 252-253).

    Les baies de façade sont regroupées en quatre orientations ; le calcul est fait pour deux roses décalées de
    45° et la plus faible valeur est retenue. Il faut au moins deux orientations ouvertes, sinon Sors est nul.
    """
    total = float(aouv.sum())
    facade = inclinaisons_deg >= INCLINAISON_FACADE_DEG
    azimut = np.mod(orientations_deg, 360.0)
    resultats = []
    for k in range(2):
        somme = 0.0
        for n in range(SECTEURS):
            reference = k * 45.0 + n * 90.0
            ecart = np.mod(azimut - reference + 45.0, 360.0)        # dans [0 ; 90[ si la baie est dans le secteur
            a_n = float(aouv[facade & (ecart < 90.0)].sum())
            reste = total - a_n
            if a_n > 0 and reste > 0:
                somme += 1.0 / np.sqrt(1.0 / a_n ** 2 + 1.0 / reste ** 2)
        resultats.append(somme / SECTEURS)
    return min(resultats)


def debit_surventilation(aouv, orientations_deg, inclinaisons_deg, traversant, hauteur_tirage_m, vent, te,
                         theta_i_prec):
    """Débit volumique par les baies ouvertes (m³/h) : éq. 251 (non traversant) ou 254 (traversant)."""
    total = float(aouv.sum())
    if total <= 0:
        return 0.0
    tirage = hyp("ouv_constante_tirage") * hauteur_tirage_m * abs(te - theta_i_prec)
    if not traversant:
        return SECONDES_PAR_HEURE * total / 2.0 * np.sqrt(max(hyp("ouv_constante_vent") * vent ** 2, tirage))
    sors = surface_traversante(aouv, orientations_deg, inclinaisons_deg)
    par_le_vent = (hyp("ouv_coefficient_decharge") * sors * min(vent, hyp("ouv_vent_max"))
                   * np.sqrt(hyp("ouv_ecart_pression")))
    return SECONDES_PAR_HEURE * max(par_le_vent, total / 2.0 * np.sqrt(tirage))


# ============================================================
# 3. LES BAIES OUVRABLES D'UN GROUPE, HEURE PAR HEURE
# ============================================================
def groupe_ouvrable(groupe):
    """Vrai si au moins une baie du groupe peut s'ouvrir."""
    return any(baie.ouvrable for baie in groupe.baies)


class OuverturesGroupe:
    """Ouverture des baies d'un groupe en mode Th-B : ratio d'ouverture puis débit de chaque heure.

    Usage : pas(h, ...) à chaque heure, dans l'ordre (le ratio dépend de celui de l'heure précédente).
    """

    def __init__(self, groupe, meteo):
        baies = groupe.baies
        self.ouvrable = np.array([b.ouvrable for b in baies], dtype=bool)
        # Surface maximale d'ouverture de chaque baie : Rouvmax × surface en tableau
        self.aouv_max = np.array([b.ratio_ouverture_max * b.surface_m2 if b.ouvrable else 0.0 for b in baies])
        self.exposition = [b.exposition_bruit or groupe.exposition_bruit for b in baies]
        self.orientations = np.array([b.orientation_deg for b in baies], dtype=float)
        self.inclinaisons = np.array([b.inclinaison_deg for b in baies], dtype=float)
        self.traversant = groupe.traversant
        self.hauteur_tirage = (groupe.hauteur_tirage_m if groupe.hauteur_tirage_m is not None
                               else hyp("ouv_hauteur_tirage_defaut"))
        self.vent = hyp("vent_correction_locale") * meteo["Vent"].to_numpy(float)       # fiche 3.1 : Ventc
        self.te = meteo["te"].to_numpy(float).copy()
        self.part_occupee = hyp("gpm_part_occupee_logement_collectif")
        self.ratio_temperature = 0.0        # Rouv_op de l'heure précédente (hystérésis)

    def pas(self, h, saison, froid_autorise, occupe, hleg, consigne_fr, consigne_fr_confort,
            ecart_confort_adaptatif, theta_op_prec, theta_i_prec, rprot=None):
        """Ouverture et débit de l'heure h en mode Th-B.

        saison                  saison propre du groupe (1 à 4)
        froid_autorise          le groupe est en saison de refroidissement (sinon aucune ouverture, éq. 244)
        occupe, hleg            occupation de la zone ; heure légale de début de pas
        consigne_fr             consigne de refroidissement de l'heure (°C) ; consigne_fr_confort : en occupation
        ecart_confort_adaptatif écart entre le seuil d'inconfort chaud et la consigne de confort (°C)
        theta_op_prec, theta_i_prec   températures opérative et d'air en fin d'heure précédente (°C)
        rprot                   ratio de fermeture des protections mobiles, par baie (réduit la surface ouvrable)
        Sortie : debit_m3h, hg (W/K, air entrant à la température extérieure), aouv_m2 et rouv_moyen.
        """
        te = self.te[h]
        # Rouv_op : nul hors occupation (éq. 245) ; le jour, hystérésis ; la nuit, position du soir conservée
        if not occupe:
            self.ratio_temperature = 0.0
        elif hyp("ouv_heure_debut_journee") < hleg < hyp("ouv_heure_fin_journee"):
            seuils = seuils_ouverture(saison, consigne_fr_confort, ecart_confort_adaptatif)
            self.ratio_temperature = ratio_selon_temperature(self.ratio_temperature, theta_op_prec, seuils)
        commun = 0.0
        if occupe and froid_autorise:
            commun = (self.part_occupee * moderation_exterieure(te, theta_op_prec, consigne_fr)
                      * self.ratio_temperature)
        if commun <= 0:
            return {"debit_m3h": 0.0, "hg": 0.0, "aouv_m2": 0.0, "rouv_moyen": 0.0}

        cpr = np.array([contrainte_ouverture(e, saison, hleg) for e in self.exposition])
        rouv = commun * cpr                                                             # éq. 240
        # Protection mobile en place : la surface ouvrable se réduit, le ratio est corrigé (éq. 248-249)
        aouv_max_pm = self.aouv_max * (1.0 - rprot) if rprot is not None else self.aouv_max
        aouv = np.minimum(aouv_max_pm, rouv * self.aouv_max)
        debit = debit_surventilation(aouv, self.orientations, self.inclinaisons, self.traversant,
                                     self.hauteur_tirage, self.vent[h], te, theta_i_prec)
        # Masse volumique de l'air entrant (éq. 255), rapportée à celle de référence du coefficient 0,34
        densite = (KELVIN + hyp("ouv_temperature_reference")) / (KELVIN + te)
        total_max = float(self.aouv_max.sum())
        return {"debit_m3h": debit, "hg": hyp("chaleur_volumique_air") * debit * densite,
                "aouv_m2": float(aouv.sum()), "rouv_moyen": float(aouv.sum()) / total_max if total_max else 0.0}
