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

 Protections mobiles (0.8.12) : si une baie du groupe en porte,
 les flux solaires et la déperdition des baies sont recalculés
 chaque heure selon leur ratio de fermeture conventionnel
 (moteur/protections.py) ; sinon les baies restent nues.
 Ouverture des baies (0.8.12) : si une baie est ouvrable, le
 groupe est surventilé en saison de refroidissement, selon la
 règle du mode Th-B (moteur/ouvertures.py).
 Infiltrations (0.8.14) : si la perméabilité à l'air du groupe
 est renseignée, l'air qui entre par les défauts d'étanchéité
 s'ajoute à la ventilation, sans passer par l'échangeur
 (moteur/infiltrations.py).

 Pas de relance du chauffage avant le retour des occupants :
 la fiche 8.5 ne l'applique qu'au calcul des consommations.

 Mode Th-D (0.8.16, confort d'été) : le même calcul sert à
 obtenir la température opérative de l'année caniculaire, dont
 moteur/dh.py tire les degrés-heures. Ce qui change :
   - météo Th-D, facteurs solaires des conditions d'été,
     inerties séquentielle et annuelle actives ;
   - aucun refroidissement : un groupe climatisé est calculé
     sans sa climatisation (fiche 13.5) ; le chauffage reste
     celui de l'émetteur conventionnel ;
   - en période de confort adaptatif (moteur/confort.py), le
     chauffage est interdit et le groupe est en saison de
     refroidissement (fiche 4.6, éq. 76 à 90) : cette saison
     ne commande plus que les protections mobiles ;
   - protections mobiles : valeurs du tableau 34 après une
     journée chaude ; ouverture des baies : règle générale ;
   - brasseurs d'air : pilotés heure par heure, leur chaleur
     entre dans le groupe et leur effet relève le seuil de
     confort (fiche 8.32) ;
   - ventilation : débit du groupe, sans échangeur (hypothèse
     de l'outil, qui ne décrit pas le système du projet).

 Lectures et hypothèses de l'outil : docs/audit.md (0.8.6,
 revues en 0.8.8).
============================================================
"""

from collections import deque
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.reglages import USAGES_HABITATION
from moteur.apports import apports_internes
from moteur.brasseurs import ARRET, pas_brasseurs, preparer_brasseurs
from moteur.calendrier import construire_calendrier
from moteur.confort import (ecart_confort_adaptatif, moyenne_glissante_exterieure, periode_confort_adaptatif,
                            seuil_confort_chaud)
from moteur.eclairage import eclairage_groupe
from moteur.groupe import (avancer_etat, debit_ventilation, etat_initial, preparer_modele, preparer_pas,
                           resoudre_pas, sollicitations_groupe, temperatures_sonde)
from moteur.hypotheses import hyp
from moteur.infiltrations import InfiltrationsGroupe, groupe_permeable
from moteur.ouvertures import OuverturesGroupe, groupe_ouvrable
from moteur.protections import ProtectionsGroupe, groupe_protege, occupation_gpm
from moteur.scenarios import charger_scenarios

JEU = "th_bc"       # les besoins du Bbio se calculent sur le climat moyen (mode Th-B)
# Mode de calcul → jeu météo : « th_b » pour les besoins du Bbio, « th_d » pour le confort d'été (DH)
JEUX_DES_MODES = {"th_b": JEU, "th_d": "th_d"}
WH_PAR_KWH = 1000.0
PREFIXE_RPROT_BAIE = "rprot_baie_"    # colonnes de sortie : fermeture de chaque baie (rprot_baie_0, …)
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
    En mode Th-D, nouveau_jour() reçoit aussi l'indicateur de période de confort adaptatif : pendant cette
    période le chauffage est interdit (éq. 76, 77 et 80) et le refroidissement autorisé (éq. 88 et 90).
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

    def nouveau_jour(self, jour, confort_adaptatif=False):
        """Clôt la journée écoulée et fixe les autorisations du jour « jour » (1 à 365).

        confort_adaptatif : en mode Th-D, vrai si l'heure du test est en période de confort adaptatif.
        """
        for nom in self.GRANDEURS:
            self.fenetres[nom].append(self.cumul[nom])
            self.cumul[nom] = 0.0
        self._chauffage(jour, confort_adaptatif)
        self._refroidissement(jour, confort_adaptatif)

    def _chauffage(self, jour, confort_adaptatif=False):
        fin_possible = hyp("saison_chauffage_fin_possible")
        ete = hyp("saison_ete_debut")
        debut_possible = hyp("saison_chauffage_debut_possible")
        if confort_adaptatif:
            # Mode Th-D, période de confort adaptatif : chauffage interdit, quel que soit le jour (éq. 76, 77, 80)
            if jour == debut_possible:
                self._recommencer("dh_ch", "occ_ch", garder=1)      # le cumul d'automne commence quand même ici
            if self.aut_ch == 1:
                self.jours_arret = 0
            self.aut_ch = 0
        elif jour < fin_possible:
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

    def _refroidissement(self, jour, confort_adaptatif=False):
        debut_possible = hyp("saison_froid_debut_possible")
        ete = hyp("saison_ete_debut")
        fin_possible = hyp("saison_froid_fin_possible")
        if not self.refroidissement or jour < debut_possible:
            self.aut_fr = 0                                                         # éq. 87
        elif jour < ete:                                                            # éq. 88
            if jour == debut_possible:
                self._recommencer("dh_fr", "occ_fr", garder=1)                      # éq. 82
            # En Th-D, la saison démarre au plus tard le premier jour de confort adaptatif
            if self.aut_fr == 0 and (confort_adaptatif
                                     or self._somme("dh_fr") >= self._seuil_debut("occ_fr")):
                self.aut_fr = 1
        elif jour < fin_possible:
            self.aut_fr = 1                                                         # éq. 89
        elif (self.aut_fr == 1 and not confort_adaptatif
              and self._besoin_moyen("q_fr", "h_fr") <= hyp("saison_seuil_fin")):
            self.aut_fr = 0                                                         # éq. 90 (en Th-D : hors période)


# ============================================================
# 2. ÉMETTEUR CONVENTIONNEL DU BBIO (fiche 8.1)
# ============================================================
def temperature_sonde(resultat):
    """θsd : température vue par la sonde de l'émetteur, sur les moyennes de l'heure (éq. 801)."""
    return _sonde(hyp("emetteur_bbio_psd"), resultat["theta_i_moy"], resultat["theta_rm_moy"])


def _sonde(psd, theta_i_moy, theta_rm_moy):
    """θsd = psd × θi + (1 − psd) × θrm (éq. 801), psd étant la part d'air vue par la sonde."""
    return psd * theta_i_moy + (1.0 - psd) * theta_rm_moy


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
# 3. CONFORT ADAPTATIF ET BRASSEURS D'AIR (fiches 3.1, 13.5 et 8.32)
# ============================================================
@dataclass
class ConfortAnnee:
    """Confort adaptatif de l'année, une valeur par heure (voir moteur/confort.py)."""
    theta_rm_ext: np.ndarray    # moyenne glissante de la température extérieure (°C)
    periode: np.ndarray         # période de confort adaptatif (booléens) ; toujours fausse en mode Th-B
    seuil: np.ndarray           # température limite de confort chaud θop_conf_ch (°C)
    ecart: np.ndarray           # Δθconf_adapt : seuil − consigne de refroidissement en occupation (°C)
    habitation: bool            # usage d'habitation : seuil de nuit à la consigne, brasseurs bridés la nuit


def preparer_confort(te, hleg, scenarios, th_d):
    """ConfortAnnee d'un site, à partir de la température extérieure « te » et de l'heure légale de début de
    pas « hleg », heure par heure.

    La moyenne glissante sert aux deux modes (saisons, ouverture des baies) ; la période de confort adaptatif
    n'existe qu'en mode Th-D.
    """
    consigne = scenarios.parametres["consigne_refroidissement_normal"]
    habitation = scenarios.usage in USAGES_HABITATION
    theta_rm_ext = moyenne_glissante_exterieure(te)
    periode = periode_confort_adaptatif(theta_rm_ext) if th_d else np.zeros(len(theta_rm_ext), dtype=bool)
    seuil = seuil_confort_chaud(theta_rm_ext, hleg, consigne, habitation)
    return ConfortAnnee(theta_rm_ext, periode, seuil, ecart_confort_adaptatif(seuil, consigne), habitation)


def brasseurs_de_l_heure(types, regimes, volume_m3, etat, hleg, occupe, confort_adaptatif, consigne_fr_confort,
                         ecart_confort, habitation):
    """Brasseurs d'air d'un groupe à l'heure h, pilotés par les températures de fin d'heure précédente
    (« etat »).

    Sortie : (régimes de l'heure, chaleur dégagée dans le groupe en Wh, consommation en Wh, ΔθopBA en °C).
    """
    r = pas_brasseurs(types, regimes, volume_m3, hleg=hleg, actif=confort_adaptatif, occupe=occupe,
                      theta_op_prec=etat.theta_op, theta_i_prec=etat.theta_i, theta_rm_prec=etat.theta_rm,
                      theta_ifr=consigne_fr_confort, ecart_conf_adapt=ecart_confort, habitation=habitation)
    return r["regimes"], r["chaleur_wh"], r["energie_wh"], r["ecart"]


# ============================================================
# 4. CALCUL DES BESOINS SUR L'ANNÉE
# ============================================================
def calculer_besoins(groupe, meteo, scenarios=None, calendrier=None, refroidissement=True,
                     efficacite_echangeur=None, hauteur_zone_m=None, hauteur_moyenne_m=None, mode="th_b"):
    """Besoins horaires de chauffage, de refroidissement et d'éclairage d'un groupe (mode Th-B), ou
    températures de l'année caniculaire (mode Th-D).

    meteo            météo du site : Th-BC en mode Th-B (moteur.meteo.charger_meteo(zone, "th_bc", altitude)),
                     Th-D en mode Th-D
    scenarios        scénarios de l'usage ; par défaut ceux du logement collectif
    calendrier       calendrier conventionnel ; par défaut moteur.calendrier.construire_calendrier()
    refroidissement  le Bbio compte un besoin de froid que le bâtiment soit climatisé ou non (constaté
                     sur des études réglementaires, voir docs/audit.md, hypothèse 29) ;
                     False pour ne calculer que le chauffage et l'éclairage. Sans effet en Th-D : aucun froid
    efficacite_echangeur   par défaut 0,5 en Th-B (ventilation conventionnelle du Bbio, fiche 6.1) et 0 en
                     Th-D (hypothèse de l'outil : air neuf à la température extérieure)
    hauteur_zone_m, hauteur_moyenne_m   hauteur de la zone et hauteur moyenne au-dessus du sol, pour les
                     infiltrations (voir moteur.infiltrations) ; facultatives
    mode             « th_b » (défaut) ou « th_d » : voir l'en-tête du module

    Sortie : une ligne par heure, avec
        q_ch_wh, q_fr_wh, cecl_wh          besoins de l'heure (Wh)
        aut_ch, aut_fr, saison              autorisations et saison propre du groupe (tableau 11)
        consigne_ch, consigne_fr            consignes de l'heure (°C)
        theta_sd                            température de la sonde, émission comprise (°C)
        theta_op_libre                      température opérative moyenne sans émission (°C)
        dh_ch, dh_fr                        écarts d'inconfort froid et chaud de l'heure (°C)
        rprot_moyen, hg_es                  ratio de fermeture moyen des protections mobiles (pondéré par les
                                            surfaces de baie) et transmission des baies de l'heure (W/K)
        rprot_baie_0, rprot_baie_1…         ratio de fermeture de chaque baie (rang dans groupe.baies), si le
                                            groupe a des protections mobiles (bilan par paroi, moteur/bilan_paroi.py)
        rouv_brut_moyen                     Rouv de l'éq. 240 (avant Rouvmax et protections), moyenne des baies
        rouv_moyen, debit_ouvertures_m3h    part ouverte de la surface ouvrable des baies et débit d'air entrant
                                            par les baies ouvertes (m³/h)
        debit_infiltrations_m3h, hg_infiltrations   air entrant par les défauts d'étanchéité (m³/h) et son
                                            coefficient d'échange (W/K)
        phi_occupants, phi_usages, einat    apports internes (W) et éclairement naturel (lux)
        occupe                              occupation de la zone (0 ou 1)
        hg_ei, theta_eieq                   renouvellement d'air de l'heure : coefficient d'échange (W/K ;
                                            ventilation, infiltrations et baies ouvertes) et température
                                            équivalente de l'air entrant (°C)
        fs1, fs3, phi_sl, phi_sh            flux des baies (courte longueur d'onde, lame d'air ventilée,
                                            Fs2 + Ftvc) et des parois opaques (W) : entrées du groupe
        phi_i, phi_s, phi_m                 flux injectés aux nœuds d'air, de surface et de masse (W), sans
                                            la puissance émise
        puis les colonnes de moteur.groupe.pas_groupe() : températures et bilan de l'heure.
    En mode Th-D s'ajoutent
        theta_rm_ext, confort_adaptatif     moyenne glissante de la température extérieure (°C) et indicateur
                                            de période de confort adaptatif
        seuil_confort, ecart_ba, seuil_confort_corrige   température limite de confort chaud (°C), effet des
                                            brasseurs d'air (°C) et leur somme (fiche 13.5, éq. 2547)
        energie_brasseurs_wh                consommation des brasseurs d'air (Wh)
    Les brasseurs d'air n'interviennent pas dans les besoins du mode Th-B.
    """
    if mode not in JEUX_DES_MODES:
        raise ValueError(f"Mode de calcul inconnu : « {mode} » (attendu : {', '.join(JEUX_DES_MODES)})")
    jeu, th_d = JEUX_DES_MODES[mode], mode == "th_d"
    scenarios = scenarios if scenarios is not None else charger_scenarios()
    calendrier = calendrier if calendrier is not None else construire_calendrier()
    n = len(meteo)
    if len(calendrier) != n:
        raise ValueError(f"Besoins : météo ({n} heures) et calendrier ({len(calendrier)} heures) de même longueur")
    hleg = calendrier["hleg"].to_numpy()        # heure légale de début de pas (Hleg = IHJ + EHLO)
    jour = calendrier["jour_annee"].to_numpy()
    consigne_fr_confort = scenarios.parametres["consigne_refroidissement_normal"]

    # --- Confort adaptatif (fiches 3.1 et 13.5) : moyenne glissante de la température extérieure, et en Th-D
    #     période de confort adaptatif, seuil de confort chaud et son écart à la consigne ---
    confort = preparer_confort(meteo["te"].to_numpy(float), hleg, scenarios, th_d)
    periode = confort.periode

    # --- Données de l'année, en tableaux numpy ---
    modele = preparer_modele(groupe, jeu)
    # Avec des protections mobiles, les flux des baies dépendent de l'heure : ils sont calculés dans la boucle
    protections = ProtectionsGroupe(groupe, meteo, jeu) if groupe_protege(groupe) else None
    indice_gpm = occupation_gpm(scenarios, calendrier)
    ouvertures = OuverturesGroupe(groupe, meteo) if groupe_ouvrable(groupe) else None
    sol = sollicitations_groupe(groupe, meteo, jeu, confort_adaptatif=periode if th_d else None,
                                avec_baies=protections is None)
    apports = apports_internes(groupe, scenarios, calendrier)
    eclairage = eclairage_groupe(groupe, meteo, scenarios.derouler("eclairage", calendrier))
    s = {c: sol[c].to_numpy() for c in ("te", "fs1", "fs3", "phi_sl", "phi_sh")}
    phi_conv = apports["phi_conv"].to_numpy() + eclairage["phi_conv"].to_numpy()
    phi_rad = apports["phi_rad"].to_numpy() + eclairage["phi_rad"].to_numpy()
    occupe = apports["occupe"].to_numpy()
    consigne_ch = scenarios.consigne("chauffage", calendrier)
    consigne_fr = scenarios.consigne("refroidissement", calendrier)

    # --- Ventilation : conventionnelle du Bbio (fiches 6.1 et 6.2) ; en Th-D, même débit, sans échangeur ---
    hg_ei = hyp("chaleur_volumique_air") * debit_ventilation(groupe)
    if efficacite_echangeur is None:
        efficacite_echangeur = hyp("ventilation_th_d_efficacite" if th_d else "ventilation_bbio_efficacite")
    # --- Brasseurs d'air (fiche 8.32) : en Th-D seulement ---
    types_brasseurs = preparer_brasseurs(groupe, scenarios.usage) if th_d else []
    regimes = [ARRET] * len(types_brasseurs)
    infiltrations = None
    if groupe_permeable(groupe):
        infiltrations = InfiltrationsGroupe(groupe, meteo, debit_ventilation(groupe), hauteur_zone_m,
                                            hauteur_moyenne_m)

    # --- Constantes de l'émetteur et du confort ---
    part_conv = hyp("emetteur_bbio_part_convective")
    psd = hyp("emetteur_bbio_psd")
    puissance_10 = hyp("puissance_matrice") * groupe.surface_m2
    heure_test = int(hyp("saison_heure_test"))
    pente, origine, marge = hyp("confort_pente"), hyp("confort_origine"), hyp("confort_ecart_c1")

    # En Th-D la saison de refroidissement existe pour tous les groupes (elle commande les protections mobiles),
    # mais aucune puissance de froid n'est émise
    saisons = Saisons(groupe.surface_m2, scenarios.horaire["occupation"].sum(), refroidissement or th_d)
    etat = etat_initial()
    theta_op_max_jour = 0.0     # maximum de la température opérative du jour légal en cours (fiche 5.9, éq. 175)
    theta_op_max_veille = 0.0   # le même pour la veille : nul le premier jour, comme le prévoit la fiche
    lignes = []
    for h in range(n):
        theta_op_max_jour = max(theta_op_max_jour, etat.theta_op)
        if h > 0 and jour[h] != jour[h - 1]:
            theta_op_max_veille, theta_op_max_jour = theta_op_max_jour, 0.0
        # Moyenne glissante de la température extérieure du jour : nulle le premier jour (fiche 4.5, éq. 57)
        theta_rm_ext = confort.theta_rm_ext[h]
        # Chaque jour à 9 h légales, saisons de chauffage et de refroidissement (fiche 4.6)
        if hleg[h] == heure_test:
            saisons.nouveau_jour(int(jour[h]), bool(periode[h]))

        # Brasseurs d'air (Th-D) : à l'arrêt à la première heure, puis pilotés par les températures de
        # l'heure h−1 ; leur chaleur s'ajoute aux apports convectifs de l'heure
        chaleur_brasseurs = energie_brasseurs = ecart_ba = 0.0
        if types_brasseurs and h > 0:
            regimes, chaleur_brasseurs, energie_brasseurs, ecart_ba = brasseurs_de_l_heure(
                types_brasseurs, regimes, groupe.volume_m3, etat, int(hleg[h]), bool(occupe[h]), bool(periode[h]),
                consigne_fr_confort, confort.ecart[h], confort.habitation)

        # 0. Baies : nues (flux de l'année déjà calculés) ou avec protections mobiles (ratio de l'heure)
        saison = SAISONS[(saisons.aut_ch, saisons.aut_fr)]
        rprot = None
        if protections is None:
            baies = dict(fs1=s["fs1"][h], fs3=s["fs3"][h], phi_sl=s["phi_sl"][h])
            rprot_moyen, hg_es = 0.0, modele.hg_es
        else:
            rprot, rprot_u = protections.ratios(h, saison, bool(occupe[h]), int(indice_gpm[h]), etat.theta_op,
                                                theta_op_max_veille, bool(periode[h]))
            b = protections.flux(h, rprot, rprot_u)
            baies = dict(fs1=b["fs1"], fs3=b["fs3"], phi_sl=b["fs2"] + b["ftvc"], hg_es=b["hg_es"])    # éq. 343
            rprot_moyen, hg_es = b["rprot_moyen"], b["hg_es"]

        # Air entrant : ventilation (à travers l'échangeur) et, baies ouvertes, air extérieur direct (fiche 5.13)
        te = s["te"][h]
        theta_souffle = te + efficacite_echangeur * (etat.theta_i - te)
        hg_air, theta_air, rouv_moyen, debit_ouvertures, rouv_brut = hg_ei, theta_souffle, 0.0, 0.0, 0.0
        debit_infiltrations = hg_infiltrations = hg_ouvertures = 0.0
        if infiltrations is not None:
            i = infiltrations.pas(h, etat.theta_i, theta_souffle)
            debit_infiltrations, hg_infiltrations = i["debit_m3h"], i["hg"]
            if hg_infiltrations > 0:
                theta_air = (hg_air * theta_air + hg_infiltrations * te) / (hg_air + hg_infiltrations)
                hg_air += hg_infiltrations
        if ouvertures is not None:
            # Écart de confort adaptatif Δθconf_adapt des seuils d'ouverture (fiche 5.13, éq. 242) : défini par la
            # fiche 13.5 en Th-D seulement (éq. 2542 à 2546 : plafonné à 2 °C, nul la nuit) ; nul en Th-B (0.9.11,
            # relecture de la 0.9.8 : l'outil prenait 0,33 θrm + 18,8 + 2 − θiifr, et ouvrait trop peu en été)
            ecart_confort = confort.ecart[h] if th_d else 0.0
            o = ouvertures.pas(h, saison, bool(saisons.aut_fr), bool(occupe[h]), int(hleg[h]), consigne_fr[h],
                               consigne_fr_confort, ecart_confort, etat.theta_op, etat.theta_i, rprot,
                               th_b=not th_d)
            rouv_moyen, debit_ouvertures, rouv_brut = o["rouv_moyen"], o["debit_m3h"], o["rouv_brut_moyen"]
            if o["hg"] > 0:
                hg_ouvertures = o["hg"]
                theta_air = (hg_air * theta_air + o["hg"] * te) / (hg_air + o["hg"])
                hg_air += o["hg"]

        # 1. Matrice du groupe : sans émission, 10 W/m² convectifs, 10 W/m² radiatifs
        entrees = dict(te=te, hg_ei=hg_air, theta_eieq=theta_air,
                       phi_sh=s["phi_sh"][h], phi_conv=phi_conv[h] + chaleur_brasseurs, phi_rad=phi_rad[h], **baies)
        #    Ce qui ne dépend pas de la puissance émise est préparé une fois ; pour les deux cas à 10 W/m², seules
        #    les deux températures lues par la sonde sont calculées
        prepare = preparer_pas(modele, etat, **entrees)
        libre = resoudre_pas(modele, etat, prepare)

        # 2-4. Droite du groupe et puissance requise par l'émetteur conventionnel (éq. 801 à 808)
        theta_sd_0 = _sonde(psd, libre["theta_i_moy"], libre["theta_rm_moy"])
        theta_sd_10 = (part_conv * _sonde(psd, *temperatures_sonde(modele, etat, prepare, puissance_10, 0.0))
                       + (1.0 - part_conv)
                       * _sonde(psd, *temperatures_sonde(modele, etat, prepare, 0.0, puissance_10)))     # éq. 804-805
        phi = puissance_requise(theta_sd_0, theta_sd_10, puissance_10, consigne_ch[h], consigne_fr[h])

        # 5. Effet des saisons (éq. 809) : la puissance n'est fournie que si la saison l'autorise ;
        #    en Th-D, jamais de froid (fiche 13.5 : la climatisation est désactivée)
        if (phi > 0 and not saisons.aut_ch) or (phi < 0 and (th_d or not saisons.aut_fr)):
            phi = 0.0

        # 6. Températures de l'heure avec cette puissance, et état suivant
        r = libre if phi == 0 else resoudre_pas(modele, etat, prepare, part_conv * phi, (1.0 - part_conv) * phi)
        avancer_etat(modele, etat, r)

        # Inconfort en occupation, sur la température opérative sans émission (fiche 4.5, éq. 56 à 61)
        theta_op_libre = libre["theta_op_moy"]
        seuil_chaud = max(consigne_fr[h], pente * theta_rm_ext + origine + marge)       # éq. 58
        dh_ch = max(0.0, consigne_ch[h] - theta_op_libre) if occupe[h] else 0.0
        # Éq. 61 : le facteur imprimé (iinconf_cons,ch + 1) / 2 vaudrait 0,5 en inconfort chaud ; l'outil lit
        # (iinconf_C1,fr + 1) / 2 = 1, comme l'éq. 60 (coquille probable ; le moteur va dans ce sens, docs/audit.md)
        dh_fr = max(0.0, theta_op_libre - seuil_chaud) if occupe[h] else 0.0
        q_ch, q_fr = max(0.0, phi), max(0.0, -phi)                                      # éq. 810 (1 h)
        saisons.ajouter_heure(occupe[h], dh_ch, dh_fr, q_ch, q_fr)

        r = dict(r)
        r.update(q_ch_wh=q_ch, q_fr_wh=q_fr, aut_ch=saisons.aut_ch, aut_fr=saisons.aut_fr,
                 saison=SAISONS[(saisons.aut_ch, saisons.aut_fr)], consigne_ch=consigne_ch[h],
                 consigne_fr=consigne_fr[h], theta_sd=_sonde(psd, r["theta_i_moy"], r["theta_rm_moy"]),
                 theta_op_libre=theta_op_libre,
                 dh_ch=dh_ch, dh_fr=dh_fr, rprot_moyen=rprot_moyen, hg_es=hg_es, rouv_moyen=rouv_moyen, rouv_brut_moyen=rouv_brut,
                 debit_ouvertures_m3h=debit_ouvertures, debit_infiltrations_m3h=debit_infiltrations,
                 hg_infiltrations=hg_infiltrations,
                 # Sollicitations de l'heure, pour comparer aux sorties horaires d'un moteur Th-BCE
                 hg_ei=hg_air, theta_eieq=theta_air, fs1=baies["fs1"], fs3=baies["fs3"], phi_sl=baies["phi_sl"],
                 phi_sh=s["phi_sh"][h], phi_i=libre["phi_i"], phi_s=libre["phi_s"], phi_m=libre["phi_m"],
                 # Air entrant poste par poste et apports internes, pour le bilan en coupe (moteur/bilan_paroi.py) :
                 # hg_ei . θeieq = hg_ventilation . θsouffle + (hg_infiltrations + hg_ouvertures) . θe
                 hg_ventilation=hg_ei, theta_souffle=theta_souffle, hg_ouvertures=hg_ouvertures,
                 phi_apports=phi_conv[h] + phi_rad[h] + chaleur_brasseurs)
        if rprot is not None:       # fermeture de chaque baie, pour le bilan par paroi (moteur/bilan_paroi.py)
            r.update({f"{PREFIXE_RPROT_BAIE}{i}": float(valeur) for i, valeur in enumerate(rprot)})
        if th_d:
            r.update(ecart_ba=ecart_ba, energie_brasseurs_wh=energie_brasseurs)
        lignes.append(r)

    resultat = pd.DataFrame(lignes, index=meteo.index)
    if th_d:
        # Confort d'été : seuil de confort chaud, relevé par les brasseurs d'air (fiche 13.5, éq. 2547)
        resultat["theta_rm_ext"] = confort.theta_rm_ext
        resultat["confort_adaptatif"] = periode.astype(int)
        resultat["seuil_confort"] = confort.seuil
        resultat["seuil_confort_corrige"] = confort.seuil + resultat["ecart_ba"].to_numpy()
    resultat["occupe"] = np.asarray(occupe).astype(int)
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
