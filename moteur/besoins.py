r"""
============================================================
 BESOINS — chauffage, refroidissement et éclairage d'un groupe
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 8.1 (C-Emi-Systèmes Emissions du groupe), § 8.1.3.1
     et éq. 800 à 810 : émetteur conventionnel du Bbio ;
   fiche 4.5 (C_Ein_Indicateurs de confort), éq. 56 à 61 ;
   fiche 4.6 (C_Ein_Détermination des saisons), éq. 67 à 91 ;
   fiche 13.1 (C_CALC_Sorties du mode Th-B), éq. 2379 à 2384.

 Le calcul est celui du mode Th-B (jeu météo Th-BC) : il donne
 les besoins Bch, Bfr et Becl qui composent le Bbio.

 Calcul d'une heure :
   1. matrice du groupe (moteur/groupe.py) : températures sans
      puissance émise, avec 10 W/m² convectifs, avec 10 W/m²
      radiatifs ;
   2. émetteur conventionnel : moitié convectif, moitié
      radiatif, puissance illimitée, sans pertes ; sa sonde
      mesure θsd = 0,5 × θi + 0,5 × θrm (moyennes de l'heure) ;
   3. « droite du groupe » : la puissance émise Φ et θsd sont
      liées par Φ = a0 + a1 × θsd (éq. 803), a0 et a1 venant
      des deux points connus (0 et 10 W/m²) ;

            Φ (W)
              |          /  droite du groupe
        Φch --|-------- *
              |        /|
            0 +-------/-+---------------> θsd (°C)
                  θsd_0  consigne de chauffage

   4. si θsd sans émission est sous la consigne de chauffage,
      Φ = a0 + a1 × consigne (> 0) ; s'il dépasse la consigne
      de refroidissement, Φ = a0 + a1 × consigne (< 0)
      (éq. 802, 807) ; sinon Φ = 0 ;
   5. la puissance n'est retenue que si la saison l'autorise
      (éq. 809) ; le besoin de l'heure est |Φ| (éq. 810) ;
   6. le groupe est recalculé avec cette puissance, ce qui
      donne ses températures de l'heure et son état suivant.

 Saisons propres au groupe (fiche 4.6), réévaluées chaque jour
 à 9 h légales :
   - chauffage : en fonction les 8 premières semaines ; arrêt
     possible du 57e au 182e jour, quand le besoin horaire
     moyen des 4 dernières semaines passe sous 2 Wh/m² (un seul
     redémarrage admis, si l'inconfort froid cumulé atteint
     40 °C.h) ; interdit du 183e au 252e jour ; redémarrage à
     partir du 253e jour, sur le même critère d'inconfort ;
   - refroidissement : interdit la première semaine ;
     démarrage du 8e au 182e jour quand l'inconfort chaud cumulé
     atteint 40 °C.h ; autorisé d'office du 183e au 245e jour ;
     arrêt à partir du 246e jour quand le besoin horaire moyen
     passe sous 2 Wh/m².
   L'inconfort (fiche 4.5) se mesure en occupation, sur la
   température opérative du groupe sans émission : écart à la
   consigne de chauffage ; écart au seuil chaud
   MAX(consigne de refroidissement ; 0,33 × θrm + 18,8 + 2),
   θrm étant la moyenne glissante de la température extérieure.

 Pas de relance du chauffage avant le retour des occupants :
 la fiche 8.5 ne l'applique qu'au calcul des consommations.

 Lectures et hypothèses de l'outil : docs/audit.md (0.8.6,
 revues en 0.8.8).
============================================================
"""

from collections import deque

import numpy as np
import pandas as pd

from config.reglages import HEURES_PAR_JOUR
from moteur.apports import apports_internes
from moteur.calendrier import construire_calendrier
from moteur.eclairage import eclairage_groupe
from moteur.groupe import (avancer_etat, debit_ventilation, etat_initial, pas_groupe, preparer_modele,
                           sollicitations_groupe)
from moteur.hypotheses import hyp
from moteur.scenarios import charger_scenarios

JEU = "th_bc"       # les besoins du Bbio se calculent sur le climat moyen (mode Th-B)
WH_PAR_KWH = 1000.0
# Saison propre du groupe selon (autorisation de chauffage, autorisation de refroidissement) : fiche 4.6, tableau 11
SAISONS = {(0, 1): 1,       # refroidissement
           (0, 0): 2,       # mi-saison
           (1, 0): 3,       # chauffage
           (1, 1): 4}       # mixte


# ============================================================
# 1. SAISONS DE CHAUFFAGE ET DE REFROIDISSEMENT (fiche 4.6)
# ============================================================
class Saisons:
    """Autorisations de chauffage et de refroidissement propres au groupe, réévaluées chaque jour.

    Usage : ajouter_heure() à chaque heure calculée, nouveau_jour() chaque jour à 9 h légales ; les
    attributs aut_ch et aut_fr (0 ou 1) valent jusqu'au lendemain.
    """
    # Grandeurs cumulées sur chaque journée, puis gardées sur une fenêtre glissante de 28 jours
    GRANDEURS = ("dh_ch",       # degrés-heures d'inconfort froid (°C.h), pour un (re)démarrage du chauffage
                 "occ_ch",      # heures d'occupation de la même fenêtre
                 "dh_fr",       # degrés-heures d'inconfort chaud (°C.h), pour le démarrage du refroidissement
                 "occ_fr",
                 "q_ch",        # besoins de chauffage (Wh), pour l'arrêt du chauffage
                 "h_ch",        # heures de la même fenêtre
                 "q_fr",        # besoins de refroidissement (Wh), pour l'arrêt du refroidissement
                 "h_fr")

    def __init__(self, surface_m2, nbh_occ_ref, refroidissement=True):
        self.surface_m2 = surface_m2
        self.nbh_occ_ref = nbh_occ_ref              # heures d'occupation d'une semaine type
        self.refroidissement = refroidissement
        self.aut_ch, self.aut_fr = 1, 0             # début d'année : chauffage en fonction, pas de froid
        self.jours_chauffage = 0                    # jours consécutifs de chauffage en fonction
        self.jours_arret = 0                        # jours écoulés depuis un arrêt du chauffage
        self.nb_redemarrages = 0
        jours = int(hyp("saison_jours_glissants"))
        self.cumul = dict.fromkeys(self.GRANDEURS, 0.0)
        self.fenetres = {nom: deque(maxlen=jours) for nom in self.GRANDEURS}

    def ajouter_heure(self, occupe, dh_ch, dh_fr, q_ch, q_fr):
        """Ajoute une heure calculée aux cumuls de la journée en cours."""
        c = self.cumul
        c["dh_ch"] += dh_ch
        c["dh_fr"] += dh_fr
        c["occ_ch"] += occupe
        c["occ_fr"] += occupe
        c["q_ch"] += q_ch
        c["q_fr"] += q_fr
        c["h_ch"] += 1
        c["h_fr"] += 1

    def _somme(self, nom):
        return sum(self.fenetres[nom])

    def _recommencer(self, *noms, garder=0):
        """Vide des fenêtres glissantes, en gardant éventuellement les « garder » derniers jours."""
        for nom in noms:
            fenetre = self.fenetres[nom]
            while len(fenetre) > garder:
                fenetre.popleft()

    def _seuil_debut(self, occupation):
        """Seuil de début de saison, réduit si la fenêtre compte peu d'heures d'occupation (éq. 78, 81, 88)."""
        part = self._somme(occupation) / (4.0 * self.nbh_occ_ref)
        return hyp("saison_seuil_debut") * max(hyp("saison_part_occupation_min"), part)

    def _besoin_moyen(self, besoin, heures):
        """Besoin horaire moyen de la fenêtre, par m² de groupe (Wh/m², éq. 71 à 75 et 85-86)."""
        nb_heures = self._somme(heures)
        return self._somme(besoin) / nb_heures / self.surface_m2 if nb_heures > 0 else 0.0

    def nouveau_jour(self, jour):
        """Clôt la journée écoulée et fixe les autorisations du jour « jour » (1 à 365)."""
        for nom in self.GRANDEURS:
            self.fenetres[nom].append(self.cumul[nom])
            self.cumul[nom] = 0.0
        self._chauffage(jour)
        self._refroidissement(jour)

    def _chauffage(self, jour):
        fin_possible = hyp("saison_chauffage_fin_possible")
        ete = hyp("saison_ete_debut")
        debut_possible = hyp("saison_chauffage_debut_possible")
        if jour < fin_possible:
            self.aut_ch = 1                                                         # éq. 76
        elif jour < ete:                                                            # éq. 78
            if self.aut_ch == 1:
                # Arrêt : besoin moyen sous le seuil, chauffage en fonction depuis au moins une semaine
                if (self.jours_chauffage >= hyp("saison_delai_arret")
                        and self._besoin_moyen("q_ch", "h_ch") <= hyp("saison_seuil_fin")):
                    self.aut_ch, self.jours_arret = 0, 0
            else:
                self.jours_arret += 1
                if self.jours_arret == 1:
                    # Une journée de coupure passée : l'inconfort froid se cumule à partir d'ici
                    self._recommencer("dh_ch", "occ_ch")
                elif (self._somme("dh_ch") >= self._seuil_debut("occ_ch")
                      and self.nb_redemarrages < hyp("saison_redemarrages_max")):
                    # Redémarrage : le besoin moyen se recalcule à partir d'ici
                    self.aut_ch = 1
                    self.nb_redemarrages += 1
                    self.jours_chauffage = 0
                    self._recommencer("q_ch", "h_ch")
        elif jour < debut_possible:
            self.aut_ch = 0                                                         # éq. 79
        elif self.aut_ch == 0:                                                      # éq. 81
            if jour == debut_possible:
                self._recommencer("dh_ch", "occ_ch", garder=1)      # le cumul commence sur une journée (éq. 68)
            if self._somme("dh_ch") >= self._seuil_debut("occ_ch"):
                self.aut_ch = 1
        self.jours_chauffage = self.jours_chauffage + 1 if self.aut_ch == 1 else 0

    def _refroidissement(self, jour):
        debut_possible = hyp("saison_froid_debut_possible")
        ete = hyp("saison_ete_debut")
        fin_possible = hyp("saison_froid_fin_possible")
        if not self.refroidissement or jour < debut_possible:
            self.aut_fr = 0                                                         # éq. 87
        elif jour < ete:                                                            # éq. 88
            if jour == debut_possible:
                self._recommencer("dh_fr", "occ_fr", garder=1)                      # éq. 82
            if self.aut_fr == 0 and self._somme("dh_fr") >= self._seuil_debut("occ_fr"):
                self.aut_fr = 1
        elif jour < fin_possible:
            self.aut_fr = 1                                                         # éq. 89
        elif self.aut_fr == 1 and self._besoin_moyen("q_fr", "h_fr") <= hyp("saison_seuil_fin"):
            self.aut_fr = 0                                                         # éq. 90


# ============================================================
# 2. ÉMETTEUR CONVENTIONNEL DU BBIO (fiche 8.1)
# ============================================================
def temperature_sonde(resultat):
    """θsd : température vue par la sonde de l'émetteur, sur les moyennes de l'heure (éq. 801)."""
    psd = hyp("emetteur_bbio_psd")
    return psd * resultat["theta_i_moy"] + (1.0 - psd) * resultat["theta_rm_moy"]


def puissance_requise(theta_sd_0, theta_sd_10, puissance_10, consigne_ch, consigne_fr):
    """Puissance que l'émetteur doit fournir pour tenir la consigne (W) : positive en chauffage, négative en
    refroidissement, nulle entre les deux consignes (éq. 802 à 808).

    theta_sd_0 et theta_sd_10 : température de la sonde sans émission et avec la puissance « puissance_10 ».
    """
    a1 = puissance_10 / (theta_sd_10 - theta_sd_0)      # pente de la droite du groupe (W/°C)
    a0 = -a1 * theta_sd_0                               # ordonnée à l'origine (W)
    if theta_sd_0 < consigne_ch:                        # le chauffage est prioritaire (éq. 802)
        return a0 + a1 * consigne_ch
    if theta_sd_0 > consigne_fr:
        return a0 + a1 * consigne_fr
    return 0.0


# ============================================================
# 3. CALCUL DES BESOINS SUR L'ANNÉE
# ============================================================
def calculer_besoins(groupe, meteo, scenarios=None, calendrier=None, refroidissement=True,
                     efficacite_echangeur=None):
    """Besoins horaires de chauffage, de refroidissement et d'éclairage d'un groupe (mode Th-B).

    meteo            météo Th-BC du site (moteur.meteo.charger_meteo(zone, "th_bc", altitude))
    scenarios        scénarios de l'usage ; par défaut ceux du logement collectif
    calendrier       calendrier conventionnel ; par défaut moteur.calendrier.construire_calendrier()
    refroidissement  le Bbio compte un besoin de froid que le bâtiment soit climatisé ou non (constaté
                     sur des études réglementaires, voir docs/audit.md, hypothèse 29) ;
                     False pour ne calculer que le chauffage et l'éclairage
    efficacite_echangeur   par défaut 0,5 (ventilation conventionnelle du Bbio, fiche 6.1)

    Sortie : une ligne par heure, avec
        q_ch_wh, q_fr_wh, cecl_wh          besoins de l'heure (Wh)
        aut_ch, aut_fr, saison              autorisations et saison propre du groupe (tableau 11)
        consigne_ch, consigne_fr            consignes de l'heure (°C)
        theta_sd                            température de la sonde, émission comprise (°C)
        theta_op_libre                      température opérative moyenne sans émission (°C)
        dh_ch, dh_fr                        écarts d'inconfort froid et chaud de l'heure (°C)
        phi_occupants, phi_usages, einat    apports internes (W) et éclairement naturel (lux)
        puis les colonnes de moteur.groupe.pas_groupe() : températures et bilan de l'heure.
    Les brasseurs d'air n'interviennent pas dans les besoins (ils servent au confort d'été, calcul Th-D).
    """
    scenarios = scenarios if scenarios is not None else charger_scenarios()
    calendrier = calendrier if calendrier is not None else construire_calendrier()
    n = len(meteo)
    if len(calendrier) != n:
        raise ValueError(f"Besoins : météo ({n} heures) et calendrier ({len(calendrier)} heures) de même longueur")

    # --- Données de l'année, en tableaux numpy ---
    modele = preparer_modele(groupe, JEU)
    sol = sollicitations_groupe(groupe, meteo, JEU)
    apports = apports_internes(groupe, scenarios, calendrier)
    eclairage = eclairage_groupe(groupe, meteo, scenarios.derouler("eclairage", calendrier))
    s = {c: sol[c].to_numpy() for c in ("te", "fs1", "fs3", "phi_sl", "phi_sh")}
    phi_conv = apports["phi_conv"].to_numpy() + eclairage["phi_conv"].to_numpy()
    phi_rad = apports["phi_rad"].to_numpy() + eclairage["phi_rad"].to_numpy()
    occupe = apports["occupe"].to_numpy()
    consigne_ch = scenarios.consigne("chauffage", calendrier)
    consigne_fr = scenarios.consigne("refroidissement", calendrier)
    hleg = calendrier["hleg"].to_numpy()        # heure légale de début de pas (Hleg = IHJ + EHLO)
    jour = calendrier["jour_annee"].to_numpy()

    # --- Ventilation conventionnelle du Bbio (fiches 6.1 et 6.2) ---
    hg_ei = hyp("chaleur_volumique_air") * debit_ventilation(groupe)
    if efficacite_echangeur is None:
        efficacite_echangeur = hyp("ventilation_bbio_efficacite")

    # --- Constantes de l'émetteur et du confort ---
    part_conv = hyp("emetteur_bbio_part_convective")
    puissance_10 = hyp("puissance_matrice") * groupe.surface_m2
    heure_test = int(hyp("saison_heure_test"))
    poids_veille = hyp("confort_poids_veille")
    pente, origine, marge = hyp("confort_pente"), hyp("confort_origine"), hyp("confort_ecart_c1")

    saisons = Saisons(groupe.surface_m2, scenarios.horaire["occupation"].sum(), refroidissement)
    etat = etat_initial()
    theta_rm_ext = 0.0          # moyenne glissante de la température extérieure : 0 le premier jour (éq. 57)
    lignes = []
    for h in range(n):
        # Chaque jour de simulation, moyenne glissante de la température extérieure (fiche 4.5, éq. 57)
        if h >= HEURES_PAR_JOUR and h % HEURES_PAR_JOUR == 0:
            veille = s["te"][h - HEURES_PAR_JOUR:h].mean()
            theta_rm_ext = poids_veille * theta_rm_ext + (1.0 - poids_veille) * veille
        # Chaque jour à 9 h légales, saisons de chauffage et de refroidissement (fiche 4.6)
        if hleg[h] == heure_test:
            saisons.nouveau_jour(int(jour[h]))

        # 1. Matrice du groupe : sans émission, 10 W/m² convectifs, 10 W/m² radiatifs
        entrees = dict(te=s["te"][h], hg_ei=hg_ei,
                       theta_eieq=s["te"][h] + efficacite_echangeur * (etat.theta_i - s["te"][h]),
                       fs1=s["fs1"][h], fs3=s["fs3"][h], phi_sl=s["phi_sl"][h], phi_sh=s["phi_sh"][h],
                       phi_conv=phi_conv[h], phi_rad=phi_rad[h])
        libre = pas_groupe(modele, etat, **entrees)
        convectif = pas_groupe(modele, etat, phi_sys_conv=puissance_10, **entrees)
        radiatif = pas_groupe(modele, etat, phi_sys_rad=puissance_10, **entrees)

        # 2-4. Droite du groupe et puissance requise par l'émetteur conventionnel (éq. 801 à 808)
        theta_sd_0 = temperature_sonde(libre)
        theta_sd_10 = (part_conv * temperature_sonde(convectif)
                       + (1.0 - part_conv) * temperature_sonde(radiatif))               # éq. 804-805
        phi = puissance_requise(theta_sd_0, theta_sd_10, puissance_10, consigne_ch[h], consigne_fr[h])

        # 5. Effet des saisons (éq. 809) : la puissance n'est fournie que si la saison l'autorise
        if (phi > 0 and not saisons.aut_ch) or (phi < 0 and not saisons.aut_fr):
            phi = 0.0

        # 6. Températures de l'heure avec cette puissance, et état suivant
        r = libre if phi == 0 else pas_groupe(modele, etat, phi_sys_conv=part_conv * phi,
                                              phi_sys_rad=(1.0 - part_conv) * phi, **entrees)
        avancer_etat(modele, etat, r)

        # Inconfort en occupation, sur la température opérative sans émission (fiche 4.5, éq. 56 à 61)
        theta_op_libre = libre["theta_op_moy"]
        seuil_chaud = max(consigne_fr[h], pente * theta_rm_ext + origine + marge)       # éq. 58
        dh_ch = max(0.0, consigne_ch[h] - theta_op_libre) if occupe[h] else 0.0
        dh_fr = max(0.0, theta_op_libre - seuil_chaud) if occupe[h] else 0.0
        q_ch, q_fr = max(0.0, phi), max(0.0, -phi)                                      # éq. 810 (1 h)
        saisons.ajouter_heure(occupe[h], dh_ch, dh_fr, q_ch, q_fr)

        r = dict(r)
        r.update(q_ch_wh=q_ch, q_fr_wh=q_fr, aut_ch=saisons.aut_ch, aut_fr=saisons.aut_fr,
                 saison=SAISONS[(saisons.aut_ch, saisons.aut_fr)], consigne_ch=consigne_ch[h],
                 consigne_fr=consigne_fr[h], theta_sd=temperature_sonde(r), theta_op_libre=theta_op_libre,
                 dh_ch=dh_ch, dh_fr=dh_fr)
        lignes.append(r)

    resultat = pd.DataFrame(lignes, index=meteo.index)
    resultat["cecl_wh"] = eclairage["cecl_wh"].to_numpy()
    resultat["einat"] = eclairage["einat"].to_numpy()
    resultat["phi_occupants"] = apports["phi_occupants"].to_numpy()
    resultat["phi_usages"] = apports["phi_usages"].to_numpy()
    premieres = ["q_ch_wh", "q_fr_wh", "cecl_wh", "aut_ch", "aut_fr", "saison", "consigne_ch", "consigne_fr",
                 "theta_sd", "theta_op_libre", "dh_ch", "dh_fr", "phi_occupants", "phi_usages", "einat"]
    return resultat[premieres + [c for c in resultat.columns if c not in premieres]]


def bilan_besoins(resultat, surface_m2, calendrier=None):
    """Besoins mensuels et annuels par m² de surface de référence (fiche 13.1, éq. 2379 à 2384).

    Sortie : (mensuel, annuel). « mensuel » : une ligne par mois conventionnel (1 à 12), colonnes b_ch, b_fr
    et b_ecl en kWh/m². « annuel » : les mêmes colonnes sommées sur l'année, en kWh/m².an.
    """
    calendrier = calendrier if calendrier is not None else construire_calendrier()
    besoins = pd.DataFrame({"b_ch": resultat["q_ch_wh"].to_numpy(), "b_fr": resultat["q_fr_wh"].to_numpy(),
                            "b_ecl": resultat["cecl_wh"].to_numpy()}) / WH_PAR_KWH / surface_m2
    mensuel = besoins.groupby(calendrier["mois"].to_numpy()).sum()
    mensuel.index.name = "mois"
    return mensuel, mensuel.sum()
