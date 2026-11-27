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

    !! Ce profil suit le MOTEUR réglementaire, PAS le texte
    !! (0.9.15, hypothèse 100, constaté sur Paris, Sète et Nice A,
    !! 92 à 99,9 % des heures identiques), hors saison de chauffage :
    !!
    !!   consigne de 26 °C, Rouv_op en fonction de θop(h−1) :
    !!     en montant  0 jusqu'à 24 °C (θouv1), 1 à 25 °C (θouv2) ;
    !!     en descendant  1 jusqu'à 23 °C (θfer1), 0 à 22 °C (θfer2) ;
    !!     entre les deux, la baie garde sa position.
    !!
    !!   texte : θouv2 = consigne + Δθconf_adapt − 1, θouv1 = θouv2
    !!           − 2, réglage de jour (7 h < hlég < 23 h) seulement ;
    !!   moteur : θouv2 = consigne − 1 (sans Δθconf_adapt, Th-D
    !!           compris), θouv1 = θouv2 − 1, réglage à toute heure
    !!           d'occupation, nuit comprise.
    !! Réglage OUVERTURE_COMME_LE_MOTEUR ci-dessous (False : texte).

    En mode Th-B (§ 5.13.3.1.2), les baies ne s'ouvrent qu'en
    occupation (éq. 245). En période de refroidissement, jamais
    quand l'air extérieur approche la consigne de refroidissement
    (à 1 °C près).

    !! Hors période de refroidissement, l'outil suit le MOTEUR
    !! réglementaire (COMETH 2025.E1), PAS le texte de l'annexe.
    !! Le texte (éq. 244) y annule l'ouverture : Mod_ext_man = 0.
    !! Le moteur, lui, applique la règle générale de la gestion
    !! manuelle (sans plafond de consigne) : il ouvre à la
    !! mi-saison, d'avril à juin et de septembre à octobre
    !! (constaté heure par heure sur Paris, Sète et Nice A,
    !! docs/audit.md, 0.9.9, hypothèse 91). En saison de chauffage,
    !! la même règle ne fait rien ouvrir : la température opérative
    !! reste sous le seuil d'ouverture. Réglage
    !! OUVERTURE_TH_B_COMME_LE_MOTEUR ci-dessous (False : texte).

    En mode Th-D (confort d'été), la règle générale s'applique :
    ni condition de saison de refroidissement, ni plafond lié à
    la consigne. Les occupants ouvrent dès qu'ils sont là, qu'il
    fait assez chaud dedans et pas trop chaud dehors.

 2. DÉBIT D'AIR du groupe, à partir de la surface ouverte :
      non traversant : tirage thermique ou vent (éq. 251) ;
      traversant     : vent entre façades d'orientations
                       différentes, ou tirage (éq. 252 à 254).
    L'air entre à la température extérieure, sans échangeur.

    Une protection mobile fermée laisse passer une part de l'air
    selon sa typologie (fiche 5.12, tableau 40 et éq. 239) :

        Aouvmax_ac_PM = Aouvmax × (Rprot × Taux_passage + 1 − Rprot)

    0 % (typologie 0, par défaut) à 75 % (typologie 4, très
    ajourée) ; puis Aouv = MIN(Aouvmax_ac_PM ; Rouv × Aouvmax)
    (éq. 248-249).

 Hypothèses de l'outil (docs/audit.md) : gestion automatique de
 l'ouverture non traitée (0.8.12) ; position du soir gardée la
 nuit (hypothèse 59) seulement avec la règle du texte.
 Lectures du texte (docs/audit.md, 0.9.11) : l'hystérésis lit
 θop(h−1), comme la figure 62 (la nomenclature, tableau 41,
 cite θop,fin(h−2)) ; une baie est en façade si β ≥ 60°, comme
 la prose de la p. 269 (l'éq. 253 imprime « β < 60° »).
============================================================
"""

import numpy as np

from config.reglages import KELVIN, SECONDES_PAR_HEURE
from moteur.hypotheses import hyp

SAISON_CHAUFFAGE = 3            # saison propre du groupe : chauffage sans refroidissement (fiche 4.6)
INCLINAISON_FACADE_DEG = 60.0   # en dessous, la baie est en toiture : hors du calcul traversant (éq. 252)
SECTEURS = 4                    # quatre orientations globales, pour deux roses décalées de 45° (éq. 253)
# Mode Th-B, hors période de refroidissement : True = comme le moteur réglementaire (COMETH 2025.E1), règle générale
# de la gestion manuelle ; False = comme le texte de l'annexe (éq. 244), aucune ouverture. Voir l'en-tête du module
# et docs/audit.md (0.9.9, hypothèse 91).
OUVERTURE_TH_B_COMME_LE_MOTEUR = True
# Profil à hystérésis de la gestion manuelle (figure 62), Th-B et Th-D : True = comme le moteur réglementaire
# (COMETH 2025.E1) : θouv2 sans Δθconf_adapt, θouv1 = θouv2 − 1 °C, réglage à toutes les heures d'occupation, nuit
# comprise ; False = comme le texte (éq. 242-243, réglage de jour seulement, position du soir gardée la nuit). Voir
# l'en-tête du module et docs/audit.md (0.9.15, hypothèse 100).
OUVERTURE_COMME_LE_MOTEUR = True

# Hypothèses lues à chaque heure, lues une fois à l'import plutôt qu'à chaque appel (0.9.37 : environ 150 000
# appels à hyp() par calcul DH du logement de départ). Expressions inchangées : résultats identiques au bit près.
OUV_SEUIL_EXTERIEUR_BAS = hyp("ouv_seuil_exterieur_bas")
OUV_THB_MARGE_CONSIGNE = hyp("ouv_thb_marge_consigne")
OUV_SEUIL_EXTERIEUR_HAUT = hyp("ouv_seuil_exterieur_haut")
OUV_ECART_EXTERIEUR_INTERIEUR_MANUEL = hyp("ouv_ecart_exterieur_interieur_manuel")
OUV_DECALAGE_CHAUFFAGE = hyp("ouv_decalage_chauffage")
OUV_DECALAGE_HORS_CHAUFFAGE = hyp("ouv_decalage_hors_chauffage")
OUV_MOTEUR_ECART_OUV1 = hyp("ouv_moteur_ecart_ouv1")
OUV_ECART_OUV1 = hyp("ouv_ecart_ouv1")
OUV_ECART_FER1 = hyp("ouv_ecart_fer1")
OUV_ECART_FER2 = hyp("ouv_ecart_fer2")
OUV_CONSTANTE_TIRAGE = hyp("ouv_constante_tirage")
OUV_CONSTANTE_VENT = hyp("ouv_constante_vent")
OUV_COEFFICIENT_DECHARGE = hyp("ouv_coefficient_decharge")
OUV_VENT_MAX = hyp("ouv_vent_max")
OUV_ECART_PRESSION = hyp("ouv_ecart_pression")
OUV_TEMPERATURE_REFERENCE = hyp("ouv_temperature_reference")
CHALEUR_VOLUMIQUE_AIR = hyp("chaleur_volumique_air")


# ============================================================
# 1. RATIO D'OUVERTURE (fiche 5.13, éq. 240 à 245)
# ============================================================
def moderation_exterieure(te, theta_op_prec, consigne_fr=None):
    """Mod_ext_man : part d'ouverture admise par la température extérieure (figure 61, éq. 241 et 244).

    Nul sous 10 °C, croissant jusqu'à 18 °C, plein jusqu'à la température opérative + 3 °C, nul au-delà.
    consigne_fr : en mode Th-B seulement, consigne de refroidissement de l'heure ; ces deux bornes sont alors
    plafonnées à la consigne − 1 °C. Sans consigne (mode Th-D), la règle générale s'applique.
    """
    bas = OUV_SEUIL_EXTERIEUR_BAS
    plafond = consigne_fr - OUV_THB_MARGE_CONSIGNE if consigne_fr is not None else float("inf")
    haut = min(plafond, OUV_SEUIL_EXTERIEUR_HAUT)
    limite = min(plafond, theta_op_prec - OUV_ECART_EXTERIEUR_INTERIEUR_MANUEL)
    if te < bas or te > limite:
        return 0.0
    if te < haut:
        return (te - bas) / (haut - bas)
    return 1.0


def seuils_ouverture(saison, consigne_fr_confort, ecart_confort_adaptatif):
    """(θouv1, θouv2, θfer1, θfer2) du profil à hystérésis (éq. 242-243).

    Règle du moteur réglementaire (OUVERTURE_COMME_LE_MOTEUR, hypothèse 100) : Δθconf_adapt ignoré et θouv1 à 1 °C
    sous θouv2 ; θfer1 et θfer2 comme le texte. Règle du texte : θouv2 = consigne + Δθconf_adapt ± 1, θouv1 à 2 °C.
    """
    decalage = OUV_DECALAGE_CHAUFFAGE if saison == SAISON_CHAUFFAGE else OUV_DECALAGE_HORS_CHAUFFAGE
    if OUVERTURE_COMME_LE_MOTEUR:
        ouv2 = consigne_fr_confort + decalage
        ouv1 = ouv2 - OUV_MOTEUR_ECART_OUV1
    else:
        ouv2 = consigne_fr_confort + ecart_confort_adaptatif + decalage
        ouv1 = ouv2 - OUV_ECART_OUV1
    return ouv1, ouv2, ouv2 - OUV_ECART_FER1, ouv2 - OUV_ECART_FER2


def ratio_selon_temperature(ratio_prec, theta_op_prec, seuils):
    """Rouv_op : profil à hystérésis de la figure 62, à partir du ratio de l'heure précédente."""
    ouv1, ouv2, fer1, fer2 = seuils
    # Bornés à [0 ; 1] en Python simple : appelé à chaque heure d'occupation, sur un seul nombre (0.9.29)
    en_ouvrant = min(max((theta_op_prec - ouv1) / (ouv2 - ouv1), 0.0), 1.0)
    en_fermant = min(max((theta_op_prec - fer2) / (fer1 - fer2), 0.0), 1.0)
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
def secteurs_traversants(orientations_deg, inclinaisons_deg):
    """Baies de façade de chaque secteur, pour les deux roses décalées de 45° (éq. 253) : rangs des baies, par
    rose puis par secteur. Ne dépend que des baies : OuverturesGroupe le calcule une fois pour l'année."""
    facade = np.asarray(inclinaisons_deg) >= INCLINAISON_FACADE_DEG
    azimut = np.mod(orientations_deg, 360.0)
    roses = []
    for k in range(2):
        secteurs = []
        for n in range(SECTEURS):
            reference = k * 45.0 + n * 90.0
            ecart = np.mod(azimut - reference + 45.0, 360.0)        # dans [0 ; 90[ si la baie est dans le secteur
            secteurs.append(np.flatnonzero(facade & (ecart < 90.0)))
        roses.append(secteurs)
    return roses


def surface_traversante(aouv, orientations_deg, inclinaisons_deg, secteurs=None):
    """Sors (m²) : surface équivalente du balayage traversant (éq. 252-253).

    Les baies de façade sont regroupées en quatre orientations ; le calcul est fait pour deux roses décalées de
    45° et la plus faible valeur est retenue. Il faut au moins deux orientations ouvertes, sinon Sors est nul.
    secteurs : facultatif, secteurs_traversants() des mêmes baies, déjà calculés.
    """
    if secteurs is None:
        secteurs = secteurs_traversants(orientations_deg, inclinaisons_deg)
    total = float(aouv.sum())
    resultats = []
    for rose in secteurs:
        somme = 0.0
        for indices in rose:
            a_n = float(aouv[indices].sum())
            reste = total - a_n
            if a_n > 0 and reste > 0:
                somme += 1.0 / np.sqrt(1.0 / a_n ** 2 + 1.0 / reste ** 2)
        resultats.append(somme / SECTEURS)
    return min(resultats)


def debit_surventilation(aouv, orientations_deg, inclinaisons_deg, traversant, hauteur_tirage_m, vent, te,
                         theta_i_prec, secteurs=None):
    """Débit volumique par les baies ouvertes (m³/h) : éq. 251 (non traversant) ou 254 (traversant).

    secteurs : facultatif, secteurs_traversants() des mêmes baies, déjà calculés."""
    total = float(aouv.sum())
    if total <= 0:
        return 0.0
    tirage = OUV_CONSTANTE_TIRAGE * hauteur_tirage_m * abs(te - theta_i_prec)
    if not traversant:
        return SECONDES_PAR_HEURE * total / 2.0 * np.sqrt(max(OUV_CONSTANTE_VENT * vent ** 2, tirage))
    sors = surface_traversante(aouv, orientations_deg, inclinaisons_deg, secteurs)
    par_le_vent = (OUV_COEFFICIENT_DECHARGE * sors * min(vent, OUV_VENT_MAX)
                   * np.sqrt(OUV_ECART_PRESSION))
    return SECONDES_PAR_HEURE * max(par_le_vent, total / 2.0 * np.sqrt(tirage))


# ============================================================
# 3. LES BAIES OUVRABLES D'UN GROUPE, HEURE PAR HEURE
# ============================================================
def groupe_ouvrable(groupe):
    """Vrai si au moins une baie du groupe peut s'ouvrir."""
    return any(baie.ouvrable for baie in groupe.baies)


class OuverturesGroupe:
    """Ouverture des baies d'un groupe, en mode Th-B ou Th-D : ratio d'ouverture puis débit de chaque heure.

    Usage : pas(h, ...) à chaque heure, dans l'ordre (le ratio dépend de celui de l'heure précédente).
    """

    def __init__(self, groupe, meteo):
        baies = groupe.baies
        self.ouvrable = np.array([b.ouvrable for b in baies], dtype=bool)
        # Surface maximale d'ouverture de chaque baie : Rouvmax × surface en tableau
        self.aouv_max = np.array([b.ratio_ouverture_max * b.surface_m2 if b.ouvrable else 0.0 for b in baies])
        # Part de l'air qui traverse la protection mobile fermée (fiche 5.12, tableau 40)
        self.passage_air = np.array([hyp(f"ouv_passage_air_pm_{b.typo_permeabilite_protection}") for b in baies])
        self.exposition = [b.exposition_bruit or groupe.exposition_bruit for b in baies]
        self.orientations = np.array([b.orientation_deg for b in baies], dtype=float)
        self.inclinaisons = np.array([b.inclinaison_deg for b in baies], dtype=float)
        self.secteurs = secteurs_traversants(self.orientations, self.inclinaisons)   # fixes pour l'année
        self.contraintes = {}       # Cpr des baies, par (saison, heure légale) : calculés à la première rencontre
        self.traversant = groupe.traversant
        self.hauteur_tirage = (groupe.hauteur_tirage_m if groupe.hauteur_tirage_m is not None
                               else hyp("ouv_hauteur_tirage_defaut"))
        self.vent = hyp("vent_correction_locale") * meteo["Vent"].to_numpy(float)       # fiche 3.2 : Ventc
        self.te = meteo["te"].to_numpy(float).copy()
        self.part_occupee = hyp("gpm_part_occupee_logement_collectif")
        self.ratio_temperature = 0.0        # Rouv_op de l'heure précédente (hystérésis)

    def pas(self, h, saison, froid_autorise, occupe, hleg, consigne_fr, consigne_fr_confort,
            ecart_confort_adaptatif, theta_op_prec, theta_i_prec, rprot=None, th_b=True):
        """Ouverture et débit de l'heure h.

        th_b                    mode Th-B (défaut) : restrictions du § 5.13.3.1.2 ; False : règle générale (Th-D)
        saison                  saison propre du groupe (1 à 4)
        froid_autorise          le groupe est en saison de refroidissement. En Th-B : plafond de la consigne − 1 °C ;
                                hors de cette saison, règle générale comme le moteur réglementaire, ou aucune
                                ouverture selon le texte (éq. 244), voir OUVERTURE_TH_B_COMME_LE_MOTEUR ; sans
                                effet en Th-D
        occupe, hleg            occupation de la zone ; heure légale de début de pas
        consigne_fr             consigne de refroidissement de l'heure (°C) ; consigne_fr_confort : en occupation
        ecart_confort_adaptatif Δθconf_adapt : écart entre le seuil d'inconfort chaud et la consigne de confort (°C),
                                défini en Th-D seulement (fiche 13.5, éq. 2546) ; 0 en Th-B
        theta_op_prec, theta_i_prec   températures opérative et d'air en fin d'heure précédente (°C)
        rprot                   ratio de fermeture des protections mobiles, par baie (réduit la surface ouvrable)
        Sortie : debit_m3h, hg (W/K, air entrant à la température extérieure), aouv_m2, rouv_moyen (part ouverte
        de la surface ouvrable) et rouv_brut_moyen (Rouv de l'éq. 240, moyenne simple de toutes les baies).
        """
        te = self.te[h]
        # Rouv_op : en occupation, hystérésis, à toute heure comme le moteur réglementaire, ou de jour seulement
        # (texte), la position du soir étant alors gardée la nuit. Hors occupation, il est remis à zéro en Th-B
        # (éq. 245) ; en Th-D il garde sa valeur, mais les baies sont fermées (éq. 240)
        if not occupe:
            if th_b:
                self.ratio_temperature = 0.0
        elif OUVERTURE_COMME_LE_MOTEUR or hyp("ouv_heure_debut_journee") < hleg < hyp("ouv_heure_fin_journee"):
            seuils = seuils_ouverture(saison, consigne_fr_confort, ecart_confort_adaptatif)
            self.ratio_temperature = ratio_selon_temperature(self.ratio_temperature, theta_op_prec, seuils)
        # Mod_ext : en Th-B et en période de refroidissement, plafonné à la consigne − 1 °C (§ 5.13.3.1.2). En Th-B
        # hors de cette période, le texte annule l'ouverture (éq. 244) ; le moteur réglementaire applique la règle
        # générale, et l'outil le suit (OUVERTURE_TH_B_COMME_LE_MOTEUR)
        commun = 0.0
        ouvre = occupe and (not th_b or froid_autorise or OUVERTURE_TH_B_COMME_LE_MOTEUR)
        if ouvre:
            plafond = consigne_fr if th_b and froid_autorise else None
            commun = self.part_occupee * moderation_exterieure(te, theta_op_prec, plafond) * self.ratio_temperature
        if commun <= 0:
            return {"debit_m3h": 0.0, "hg": 0.0, "aouv_m2": 0.0, "rouv_moyen": 0.0, "rouv_brut_moyen": 0.0}

        cpr = self.contraintes.get((saison, hleg))
        if cpr is None:
            cpr = np.array([contrainte_ouverture(e, saison, hleg) for e in self.exposition])
            self.contraintes[(saison, hleg)] = cpr
        rouv = commun * cpr                                                             # éq. 240
        # Protection mobile en place : la part fermée ne laisse passer que Taux_passage de l'air (éq. 239), le
        # ratio est corrigé pour garder la même section d'ouverture (éq. 248-249)
        aouv_max_pm = (self.aouv_max * (1.0 - rprot * (1.0 - self.passage_air)) if rprot is not None
                       else self.aouv_max)
        aouv = np.minimum(aouv_max_pm, rouv * self.aouv_max)
        debit = debit_surventilation(aouv, self.orientations, self.inclinaisons, self.traversant,
                                     self.hauteur_tirage, self.vent[h], te, theta_i_prec, self.secteurs)
        # Masse volumique de l'air entrant (éq. 255), rapportée à celle de référence du coefficient 0,34
        densite = (KELVIN + OUV_TEMPERATURE_REFERENCE) / (KELVIN + te)
        total_max = float(self.aouv_max.sum())
        return {"debit_m3h": debit, "hg": CHALEUR_VOLUMIQUE_AIR * debit * densite,
                "aouv_m2": float(aouv.sum()), "rouv_moyen": float(aouv.sum()) / total_max if total_max else 0.0,
                # Rouv de l'éq. 240, avant Rouvmax et protections, en moyenne simple sur toutes les baies (nul pour
                # une baie fixe) : la grandeur O_Rouv des sorties horaires du moteur réglementaire
                "rouv_brut_moyen": float(np.mean(np.where(self.ouvrable, rouv, 0.0)))}
