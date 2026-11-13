"""
============================================================
 GROUPE — modèle thermique horaire d'un groupe
============================================================
 Source : annexe III de l'arrêté du 4 août 2021,
   fiche 5.21 (C_BAT_comportement thermique d'un groupe),
   éq. 311 à 373, tableaux 53 et 54 ;
   fiche 6.1 (C_VEN_BBIO), éq. 378 et 382 : ventilation ;
   règles Th-Bât, fascicule Inertie, tableau 89 : Ams_surf.

 Le groupe est un réseau de résistances et d'une capacité, à
 trois nœuds de température :

     θeieq ──Hg_ei── θi           air du groupe
                      │
                    Hg_is
                      │
     θes ───Hg_es─── θs           nœud fictif : surfaces légères
                      │           et baies, échanges internes
                    Hg_ms
                      │
     θem ───Hg_em─── θmq ══ Cmq   masse (inertie quotidienne)

   θeieq  température de l'air entrant (ventilation)
   θes    température extérieure vue par les baies, flux
          solaire réémis et rayonnement froid compris
   θem    température extérieure vue par les parois opaques,
          soleil absorbé et rayonnement froid compris

 Calcul d'une heure (fiche 5.21, § 5.21.3.1) :
   1. coefficients Hg_ei, Hg_es, Hg_em, Hg_is, Hg_ms (éq. 323 à 341) ;
   2. températures extérieures équivalentes (éq. 342 à 345) ;
   3. flux injectés aux nœuds : φi, φs, φmq (éq. 346 à 352, 361) ;
   4. inerties séquentielle et annuelle, en Th-D seulement
      (éq. 353 à 360) : deux masses lentes θms et θma, qui
      suivent les moyennes de θmq sur 24 h et sur 14 jours et
      rendent ou prennent de la chaleur au nœud θmq ;
   5. bilan de la masse sur l'heure, schéma de Crank-Nicolson
      (éq. 362 à 366), puis θs, θi, θrm et θop (éq. 367 à 371).

 Toutes les températures sont données « en moyenne » sur
 l'heure (calculées avec la moyenne de θmq) et « en fin »
 d'heure (calculées avec θmq final).

 Matrice du groupe (éq. 373) : les mêmes températures pour
 trois puissances émises — nulle, 10 W/m² convectifs, 10 W/m²
 radiatifs. Le modèle étant linéaire, elle donne la « droite
 du groupe », que le calcul des besoins (0.8.6) croisera avec
 l'émetteur.

 Unités : flux en W, coefficients en W/K, capacités en Wh/K
 (kJ/K divisés par 3,6), pas de temps d'une heure.

 Lectures et hypothèses de l'outil (docs/audit.md, 0.8.4) :
   - le terme Hg_es.θes, absent de l'éq. 366 imprimée, est
     rétabli (il figure dans l'éq. 367) ;
   - la part des apports radiatifs reçue par les parois
     légères, frs, n'est définie par aucune équation : elle
     vaut le complément (Atparois − Amq − Abaies) / Atparois ;
   - la puissance radiative de l'émetteur est répartie comme
     les apports internes radiatifs ;
   - les échanges entre groupes (φmig, Hs,ig,eq) sont nuls ;
   - humidité de l'air non traitée : Hg_ei = 0,34 × débit ;
   - infiltrations nulles ; flux solaires et rayonnement froid
     des ponts thermiques négligés.
============================================================
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config.reglages import JOURS_PAR_SEMAINE, USAGES_HABITATION
from moteur.brasseurs import ARRET, pas_brasseurs, preparer_brasseurs
from moteur.enveloppe import transmission_baies, transmission_parois, transmission_ponts
from moteur.hypotheses import hyp
from moteur.solaire import _controler_jeu, flux_solaires_baie, flux_solaires_paroi

KJ_PAR_WH = 3.6     # 1 Wh = 3,6 kJ : les capacités saisies en kJ/K sont converties en Wh/K
HEURES_PAR_JOUR = 24

# Températures calculées à chaque heure, dans l'ordre des lignes de la matrice (éq. 373)
TEMPERATURES = ("theta_i", "theta_s", "theta_mq", "theta_rm", "theta_op")
# Colonnes facultatives du tableau « apports » de simuler_groupe() (W)
COLONNES_APPORTS = ("phi_conv",         # apports internes convectifs (occupants, usages, éclairage…)
                    "phi_rad",          # apports internes radiatifs
                    "phi_sys_conv",     # puissance convective émise par le système (négative en refroidissement)
                    "phi_sys_rad")      # puissance radiative émise par le système
# Colonnes exigées dans « entrees_brasseurs » quand le groupe a des brasseurs d'air (voir moteur/brasseurs.py)
COLONNES_BRASSEURS = ("case", "actif", "occupe", "theta_ifr", "ecart_conf_adapt")


# ============================================================
# 1. PARAMÈTRES CONSTANTS DU GROUPE (fiche 5.21, éq. 311 à 332, 349 à 352, 370)
# ============================================================
@dataclass
class ModeleGroupe:
    """Grandeurs du groupe qui ne changent pas d'une heure à l'autre."""
    surface_m2: float           # Agr
    a_tparois: float            # Atparois : surface interne totale des parois (m²)
    a_baies: float              # Abaies (m²)
    a_mq: float                 # Amq : surface d'échange de la masse quotidienne (m²)
    h_is: float                 # his = hci + hrs (W/m².K)
    hg_is: float                # entre l'air θi et le nœud θs (W/K)
    hg_ms: float                # entre le nœud θs et la masse θmq (W/K)
    c_mq: float                 # capacité quotidienne (Wh/K)
    hg_es: float                # baies : entre l'extérieur et θs (W/K)
    h_th: float                 # parois opaques et ponts thermiques : H_TH,k+pt (W/K)
    hg_em: float                # entre l'extérieur et la masse θmq (W/K)
    fsa: float                  # part du soleil de courte longueur d'onde allant à l'air
    fr_l_baies: float           # part des apports radiatifs reçue par les baies
    fr_m: float                 # part des apports radiatifs reçue par la masse
    fr_s: float                 # part des apports radiatifs reçue par les parois légères
    fr_sd: float                # part du soleil restant allant au nœud θs
    fr_md: float                # part du soleil restant allant à la masse
    perte_baies: float          # part d'un flux radiatif reçu par les baies qui repart dehors : Hg_es / (Abaies.his)
    p_trm: float                # poids de θs dans la température radiante moyenne
    p_top: float                # poids de θrm dans la température opérative
    inerties_longues: bool      # inerties séquentielle et annuelle actives (Th-D)
    dhg_seq: float              # ΔHg_ms,s-q (W/K)
    dc_seq: float               # ΔC_m,s-q (Wh/K)
    dhg_ann: float              # ΔHg_ms,a-q (W/K)
    dc_ann: float               # ΔC_m,a-s (Wh/K)
    nb_heures_seq: int          # longueur de la séquence (h) : 24 × NBj,séq
    theta_mq24_initiale: float
    theta_mqseq_initiale: float


def inertie_groupe(groupe):
    """Surfaces d'échange (m²/m²) et capacités (kJ/K/m²) par m² de groupe, pour les trois inerties.

    Sortie : dictionnaire amq, cmq, ams, cms, ama, cma.
      - quotidienne : tableau 53, ou valeurs saisies ;
      - séquentielle : « defaut » et « tres_legere » reprennent Cmq et Amq ; sinon Cms du tableau 54 et Ams
        du tableau 89 des règles Th-Bât (ou ams_surf saisi) ;
      - annuelle : « defaut » reprend Cms (éq. 316) et Ams.
    """
    if groupe.inertie_quotidienne == "personnalisee":
        amq, cmq = groupe.amq_surf, groupe.cmq_surf
    else:
        amq = hyp(f"inertie_quo_{groupe.inertie_quotidienne}_amq")
        cmq = hyp(f"inertie_quo_{groupe.inertie_quotidienne}_cmq")

    if groupe.inertie_sequentielle == "personnalisee":
        ams, cms = groupe.ams_surf, groupe.cms_surf
    elif groupe.inertie_sequentielle in ("defaut", "tres_legere"):
        ams, cms = amq, cmq
    else:
        cms = hyp(f"inertie_seq_{groupe.inertie_sequentielle}_cms")
        ams = (groupe.ams_surf if groupe.ams_surf is not None
               else hyp(f"inertie_seq_{groupe.inertie_sequentielle}_ams"))

    if groupe.inertie_annuelle == "personnalisee":
        ama, cma = groupe.ama_surf, groupe.cma_surf
    else:
        ama = groupe.ama_surf if groupe.ama_surf is not None else ams
        cma = cms
    return {"amq": amq, "cmq": cmq, "ams": ams, "cms": cms, "ama": ama, "cma": cma}


def _transmission_differentielle(h_is, surface_lente_m2, surface_quotidienne_m2):
    """ΔHg = 1 / (R_lente − R_quotidienne), avec R = 1 / (his.A) (éq. 327 à 330).

    Nulle si les résistances sont égales (note de la fiche) ; une différence négative, que la fiche n'envisage
    pas, est aussi ramenée à zéro (hypothèse de l'outil).
    """
    ecart = 1.0 / (h_is * surface_lente_m2) - 1.0 / (h_is * surface_quotidienne_m2)
    return 1.0 / ecart if ecart > 1e-12 else 0.0


def preparer_modele(groupe, jeu):
    """Paramètres constants du modèle du groupe (ModeleGroupe), pour un jeu « th_bc » ou « th_d ».

    Les inerties séquentielle et annuelle ne sont actives qu'en Th-D (fiche 5.21, § 5.21.3.2).
    """
    _controler_jeu(jeu)
    surface = groupe.surface_m2
    inertie = inertie_groupe(groupe)

    # Surfaces (éq. 313, 317) et coefficients d'échange internes (éq. 323 à 326)
    a_tparois = hyp("ratio_atparois") * surface
    a_baies = groupe.surface_baies_m2
    a_mq = inertie["amq"] * surface
    hci = hyp("hci")
    hrs = hyp("coef_hrs") * hyp("hri")
    h_is = hci + hrs
    hg_is = a_tparois / (1.0 / hci - 1.0 / h_is)
    hg_ms = h_is * a_mq
    if a_mq + a_baies > a_tparois:
        raise ValueError(f"Groupe « {groupe.nom} » : la masse ({a_mq:.0f} m²) et les baies ({a_baies:.0f} m²) "
                         f"dépassent la surface interne des parois ({a_tparois:.0f} m² = 4,5 × surface du groupe)")

    # Enveloppe : baies vers θs (éq. 341), parois opaques et ponts thermiques vers θmq (éq. 339-340)
    hg_es = transmission_baies(groupe)
    h_th = transmission_parois(groupe) + transmission_ponts(groupe)
    if h_th >= hg_ms:
        raise ValueError(f"Groupe « {groupe.nom} » : déperdition des parois opaques ({h_th:.0f} W/K) supérieure à "
                         f"l'échange entre la masse et l'ambiance ({hg_ms:.0f} W/K) : modèle inapplicable")
    hg_em = 1.0 / (1.0 / h_th - 1.0 / hg_ms) if h_th > 0 else 0.0

    # Inerties séquentielle et annuelle (éq. 327 à 332) : seulement en Th-D
    longues = jeu == "th_d"
    dhg_seq = _transmission_differentielle(h_is, inertie["ams"] * surface, a_mq) if longues else 0.0
    dhg_ann = _transmission_differentielle(h_is, inertie["ama"] * surface, a_mq) if longues else 0.0
    dc_seq = max(0.0, inertie["cms"] - inertie["cmq"]) * surface / KJ_PAR_WH
    dc_ann = max(0.0, inertie["cma"] - inertie["cms"]) * surface / KJ_PAR_WH

    return ModeleGroupe(
        surface_m2=surface, a_tparois=a_tparois, a_baies=a_baies, a_mq=a_mq, h_is=h_is, hg_is=hg_is, hg_ms=hg_ms,
        c_mq=inertie["cmq"] * surface / KJ_PAR_WH, hg_es=hg_es, h_th=h_th, hg_em=hg_em, fsa=hyp("fsa"),
        fr_l_baies=a_baies / a_tparois,                                     # éq. 349
        fr_m=a_mq / a_tparois,                                              # éq. 350
        fr_s=(a_tparois - a_mq - a_baies) / a_tparois,                      # complément (docs/audit.md)
        fr_sd=(a_tparois - a_mq - a_baies) / (a_tparois - a_baies),         # éq. 351
        fr_md=a_mq / (a_tparois - a_baies),                                 # éq. 352
        perte_baies=hg_es / (a_baies * h_is) if a_baies > 0 else 0.0,       # éq. 361
        p_trm=1.0 + hci / hrs,                                              # éq. 370
        p_top=hyp("ptop"),
        inerties_longues=longues,
        # Une masse lente sans capacité propre n'a pas d'effet : son couplage est coupé
        dhg_seq=dhg_seq if dc_seq > 0 else 0.0, dc_seq=dc_seq,
        dhg_ann=dhg_ann if dc_ann > 0 else 0.0, dc_ann=dc_ann,
        nb_heures_seq=int(hyp("nbj_seq")) * HEURES_PAR_JOUR,
        theta_mq24_initiale=hyp("theta_mq24_initiale"), theta_mqseq_initiale=hyp("theta_mqseq_initiale"))


# ============================================================
# 2. ÉTAT DU GROUPE, d'une heure à la suivante
# ============================================================
@dataclass
class EtatGroupe:
    """Ce que le groupe garde en mémoire d'une heure à l'autre (températures de fin de pas, en °C)."""
    theta_mq: float             # masse quotidienne
    theta_i: float              # air : sert à l'échangeur de la ventilation et aux brasseurs
    theta_rm: float             # radiante moyenne : sert aux brasseurs
    theta_op: float             # opérative : sert aux brasseurs
    theta_ms: float             # masse séquentielle
    theta_ma: float             # masse annuelle
    heure: int = 0              # nombre d'heures déjà calculées
    historique: deque = field(default_factory=deque)    # θmq des dernières heures (longueur de la séquence)
    somme_24h: float = 0.0      # somme des θmq des 24 dernières heures
    somme_seq: float = 0.0      # somme des θmq de la séquence


def etat_initial():
    """État avant la première heure : toutes les températures à leur valeur initiale (18 °C)."""
    theta = hyp("theta_groupe_initiale")
    return EtatGroupe(theta_mq=theta, theta_i=theta, theta_rm=theta, theta_op=theta,
                      theta_ms=hyp("theta_ms_initiale"), theta_ma=hyp("theta_ms_initiale"))


def avancer_etat(modele, etat, resultat):
    """Nouvel état après une heure calculée par pas_groupe() : températures de fin de pas et moyennes glissantes."""
    etat.theta_mq = resultat["theta_mq"]
    etat.theta_i = resultat["theta_i"]
    etat.theta_rm = resultat["theta_rm"]
    etat.theta_op = resultat["theta_op"]
    etat.theta_ms = resultat["theta_ms"]
    etat.theta_ma = resultat["theta_ma"]
    etat.heure += 1
    # Sommes glissantes de θmq : on ajoute la nouvelle heure, on retire celles qui sortent des fenêtres
    historique = etat.historique
    historique.append(etat.theta_mq)
    etat.somme_24h += etat.theta_mq
    etat.somme_seq += etat.theta_mq
    if len(historique) > HEURES_PAR_JOUR:
        etat.somme_24h -= historique[-HEURES_PAR_JOUR - 1]
    if len(historique) > modele.nb_heures_seq:
        etat.somme_seq -= historique.popleft()
    return etat


# ============================================================
# 3. CALCUL D'UNE HEURE (fiche 5.21, éq. 342 à 371)
# ============================================================
def _inerties_longues(modele, etat):
    """Flux rendus à la masse quotidienne par les masses séquentielle et annuelle (W), et leurs températures.

    Sortie : (φmq_seq, φmq_ann, θms, θma). Hors Th-D, ou sans masse lente : flux nuls, températures inchangées.
    """
    phi_seq = phi_ann = 0.0
    theta_ms, theta_ma = etat.theta_ms, etat.theta_ma
    if modele.dhg_seq > 0:
        # Moyenne de θmq sur les 24 heures précédentes (éq. 353), fixée à 18 °C pendant les 24 premières heures
        theta_mq24 = (etat.somme_24h / HEURES_PAR_JOUR if etat.heure >= HEURES_PAR_JOUR
                      else modele.theta_mq24_initiale)
        # Masse séquentielle : Crank-Nicolson vers cette moyenne (éq. 354), puis flux rendu (éq. 355-356)
        theta_ms = (((modele.dc_seq - 0.5 * modele.dhg_seq) * etat.theta_ms + modele.dhg_seq * theta_mq24)
                    / (modele.dc_seq + 0.5 * modele.dhg_seq))
        phi_seq = modele.dhg_seq * (0.5 * (theta_ms + etat.theta_ms) - theta_mq24)
    if modele.dhg_ann > 0:
        # Moyenne de θmq sur les 14 jours précédents (éq. 357), fixée à 19 °C pendant les 14 premiers jours
        theta_mqseq = (etat.somme_seq / modele.nb_heures_seq if etat.heure >= modele.nb_heures_seq
                       else modele.theta_mqseq_initiale)
        # Masse annuelle : même schéma (éq. 358), puis flux rendu (éq. 359-360)
        theta_ma = (((modele.dc_ann - 0.5 * modele.dhg_ann) * etat.theta_ma + modele.dhg_ann * theta_mqseq)
                    / (modele.dc_ann + 0.5 * modele.dhg_ann))
        phi_ann = modele.dhg_ann * (0.5 * (theta_ma + etat.theta_ma) - theta_mqseq)
    return phi_seq, phi_ann, theta_ms, theta_ma


def pas_groupe(modele, etat, *, te, hg_ei=0.0, theta_eieq=None, fs1=0.0, fs3=0.0, phi_sl=0.0, phi_sh=0.0,
               phi_conv=0.0, phi_rad=0.0, phi_sys_conv=0.0, phi_sys_rad=0.0):
    """Calcul d'une heure du groupe. L'état n'est pas modifié : appeler avancer_etat() ensuite.

    Entrées de l'heure :
        te              température extérieure (°C)
        hg_ei           coefficient d'échange par renouvellement d'air (W/K)
        theta_eieq      température de l'air entrant (°C) ; par défaut te
        fs1, fs3        flux solaires des baies : courte longueur d'onde, lame d'air ventilée (W)
        phi_sl          Fs2 + Ftvc : flux réémis par les baies et rayonnement froid des baies (W, éq. 343)
        phi_sh          flux solaire et rayonnement froid des parois opaques (W, éq. 345)
        phi_conv        apports internes convectifs (W)
        phi_rad         apports internes radiatifs (W)
        phi_sys_conv    puissance convective émise par le système (W)
        phi_sys_rad     puissance radiative émise par le système (W)
    Sortie : dictionnaire
        theta_i, theta_s, theta_mq, theta_rm, theta_op     en fin d'heure (°C)
        les mêmes suivis de « _moy »                       en moyenne sur l'heure (°C)
        theta_ms, theta_ma, phi_mq_seq, phi_mq_ann         inerties séquentielle et annuelle
        flux_ventilation, flux_baies, flux_parois, flux_apports, flux_inerties_longues, stockage
            bilan de l'heure (W) : stockage = somme des cinq flux, le stockage étant la chaleur prise par
            la masse quotidienne. flux_apports compte tout ce qui est injecté à l'intérieur (soleil de courte
            longueur d'onde, apports internes, système), net de la part radiative repartie par les baies.
    """
    if theta_eieq is None:
        theta_eieq = te
    m = modele

    # --- Étape 3 : flux injectés aux nœuds (éq. 346 à 352, 361, 372) ---
    radiatif = phi_rad + phi_sys_rad
    soleil_restant = (1.0 - m.fsa) * fs1
    phi_i = m.fsa * fs1 + fs3 + phi_conv + phi_sys_conv                             # éq. 346 (+ système)
    phi_l = m.fr_l_baies * radiatif                                                 # éq. 347
    phi_m = m.fr_md * soleil_restant + m.fr_m * radiatif                            # éq. 348
    phi_s = (1.0 - m.perte_baies) * phi_l + m.fr_sd * soleil_restant + m.fr_s * radiatif   # éq. 361 complétée

    # --- Étape 5 : coefficients de résolution (éq. 362 à 364), écrits pour rester définis sans ventilation
    #     (Hg_ei = 0) et sans baie ni ventilation (U2 = 0) ---
    part_air = m.hg_is / (m.hg_is + hg_ei)          # = U1 / Hg_ei : part d'un flux injecté à l'air qui atteint θs
    u1 = hg_ei * part_air                           # éq. 362
    u2 = u1 + m.hg_es                               # éq. 363
    part_masse = m.hg_ms / (u2 + m.hg_ms)           # = U3 / U2 : part d'un flux injecté en θs qui atteint la masse
    u3 = u2 * part_masse                            # éq. 364

    # Tout ce qui arrive au nœud θs, températures extérieures comprises : Hg_es.θes = Hg_es.te + φsl (éq. 342)
    arrive_s = phi_s + m.hg_es * te + phi_sl + u1 * theta_eieq + part_air * phi_i
    # Hg_em.θem = Hg_em.te + φsh.Hg_em / H_TH (éq. 344, avec 1/Hg_em + 1/Hg_ms = 1/H_TH)
    gain_parois = phi_sh * m.hg_em / m.h_th if m.h_th > 0 else 0.0
    phi_seq, phi_ann, theta_ms, theta_ma = _inerties_longues(m, etat)               # étape 4
    phi_mtot = phi_m + m.hg_em * te + gain_parois + part_masse * arrive_s           # éq. 366

    # Bilan de la masse sur l'heure, Crank-Nicolson (éq. 365, Δh = 1 h, capacité en Wh/K)
    pertes = 0.5 * (u3 + m.hg_em)
    theta_mq = ((etat.theta_mq * (m.c_mq - pertes) + phi_mtot + phi_seq + phi_ann) / (m.c_mq + pertes))
    theta_mq_moy = 0.5 * (theta_mq + etat.theta_mq)

    def autres_temperatures(theta_m):
        """θs, θi, θrm et θop déduites d'une température de masse (éq. 367 à 371)."""
        theta_s = (m.hg_ms * theta_m + arrive_s) / (m.hg_ms + u2)                               # éq. 367
        theta_i = (m.hg_is * theta_s + hg_ei * theta_eieq + phi_i) / (m.hg_is + hg_ei)          # éq. 368
        theta_rm = m.p_trm * theta_s + (1.0 - m.p_trm) * theta_i                                # éq. 369
        theta_op = m.p_top * theta_rm + (1.0 - m.p_top) * theta_i                               # éq. 371
        return theta_i, theta_s, theta_rm, theta_op

    theta_i, theta_s, theta_rm, theta_op = autres_temperatures(theta_mq)
    theta_i_moy, theta_s_moy, theta_rm_moy, theta_op_moy = autres_temperatures(theta_mq_moy)

    return {
        "theta_i": theta_i, "theta_s": theta_s, "theta_mq": theta_mq, "theta_rm": theta_rm, "theta_op": theta_op,
        "theta_i_moy": theta_i_moy, "theta_s_moy": theta_s_moy, "theta_mq_moy": theta_mq_moy,
        "theta_rm_moy": theta_rm_moy, "theta_op_moy": theta_op_moy,
        "theta_ms": theta_ms, "theta_ma": theta_ma, "phi_mq_seq": phi_seq, "phi_mq_ann": phi_ann,
        # Bilan de l'heure, avec les températures moyennes
        "flux_ventilation": hg_ei * (theta_eieq - theta_i_moy),
        "flux_baies": m.hg_es * (te - theta_s_moy) + phi_sl,
        "flux_parois": m.hg_em * (te - theta_mq_moy) + gain_parois,
        "flux_apports": phi_i + phi_s + phi_m,
        "flux_inerties_longues": phi_seq + phi_ann,
        "stockage": m.c_mq * (theta_mq - etat.theta_mq),
    }


def matrice_groupe(modele, etat, **sollicitations):
    """Matrice de comportement thermique du groupe pour une heure (éq. 373) : tableau de 5 lignes × 6 colonnes.

    Lignes : θi, θs, θmq, θrm, θop. Colonnes : (moyenne, fin) sans puissance émise, puis avec 10 W/m²
    convectifs, puis avec 10 W/m² radiatifs. Les sollicitations sont celles de pas_groupe(), sans phi_sys_*.
    """
    puissance = hyp("puissance_matrice") * modele.surface_m2
    colonnes = []
    for phi_sys_conv, phi_sys_rad in ((0.0, 0.0), (puissance, 0.0), (0.0, puissance)):
        r = pas_groupe(modele, etat, phi_sys_conv=phi_sys_conv, phi_sys_rad=phi_sys_rad, **sollicitations)
        colonnes.append([r[f"{nom}_moy"] for nom in TEMPERATURES])
        colonnes.append([r[nom] for nom in TEMPERATURES])
    return np.array(colonnes).T


# ============================================================
# 4. SOLLICITATIONS DE L'ENVELOPPE, heure par heure
# ============================================================
def sollicitations_groupe(groupe, meteo, jeu, confort_adaptatif=None):
    """Flux solaires et de rayonnement froid reçus par le groupe, sommés sur ses baies et ses parois (W).

    Colonnes : te, fs1, fs2, fs3, ftvc, phi_sl (= fs2 + ftvc, éq. 343), phi_sh_s, phi_sh_vc et
    phi_sh (= phi_sh_s + phi_sh_vc, éq. 345, sans les ponts thermiques).
    En Th-D, la période de confort adaptatif est exigée dès que le groupe a une paroi opaque sur l'extérieur
    (voir moteur.solaire.flux_solaires_paroi).
    """
    n = len(meteo)
    sommes = {nom: np.zeros(n) for nom in ("fs1", "fs2", "fs3", "ftvc", "phi_sh_s", "phi_sh_vc")}
    for baie in groupe.baies:
        flux = flux_solaires_baie(baie, meteo, jeu)
        for nom in ("fs1", "fs2", "fs3", "ftvc"):
            sommes[nom] += flux[nom].to_numpy()
    for paroi in groupe.parois:
        flux = flux_solaires_paroi(paroi, meteo, jeu, confort_adaptatif)
        sommes["phi_sh_s"] += flux["phi_s"].to_numpy()
        sommes["phi_sh_vc"] += flux["phi_vc"].to_numpy()
    resultat = pd.DataFrame({"te": meteo["te"].to_numpy(float), **sommes}, index=meteo.index)
    resultat["phi_sl"] = resultat["fs2"] + resultat["ftvc"]
    resultat["phi_sh"] = resultat["phi_sh_s"] + resultat["phi_sh_vc"]
    return resultat


def debit_ventilation(groupe):
    """Débit d'air neuf moyen du groupe (m³/h), au sens du Bbio (fiche 6.2, éq. 404-405, Cdep = 1).

    Sans débit de pointe, c'est le débit saisi. Avec un débit de pointe, le grand débit est utilisé
    Dugd = 14 heures par semaine : débit = base + (pointe − base) × 14 / 168.
    """
    base = groupe.debit_ventilation_m3h
    if groupe.debit_ventilation_pointe_m3h is None:
        return base
    part_pointe = hyp("dugd_bbio") / (JOURS_PAR_SEMAINE * HEURES_PAR_JOUR)
    return base + (groupe.debit_ventilation_pointe_m3h - base) * part_pointe


# ============================================================
# 5. SIMULATION SUR TOUTES LES HEURES
# ============================================================
def simuler_groupe(groupe, meteo, jeu, apports=None, confort_adaptatif=None, efficacite_echangeur=None,
                   entrees_brasseurs=None, usage_zone="logement_collectif"):
    """Déroule le modèle du groupe sur toutes les heures de « meteo » (moteur.meteo.charger_meteo).

    apports               tableau facultatif, une ligne par heure, colonnes parmi COLONNES_APPORTS (W) ;
                          une colonne absente vaut zéro. Sans puissance de système, c'est l'évolution libre.
    confort_adaptatif     période de confort adaptatif (Th-D, parois opaques : voir moteur/solaire.py)
    efficacite_echangeur  efficacité de la récupération sur l'air extrait ; par défaut celle de la
                          ventilation conventionnelle du Bbio (0,5, fiche 6.1)
    entrees_brasseurs     exigé si le groupe a des brasseurs d'air : colonnes COLONNES_BRASSEURS

    Ventilation (fiche 6.1) : débit moyen du groupe (debit_ventilation), Hg_ei = 0,34 × débit ; l'air entre à
    θeieq = te + efficacité × (θi de fin d'heure précédente − te) (éq. 378).
    Brasseurs d'air (fiche 8.32) : leur régime suit les températures de l'heure précédente ; leur chaleur
    est ajoutée aux apports convectifs de l'heure.

    Sortie : une ligne par heure, avec les colonnes de pas_groupe(), puis theta_eieq, chaleur_brasseurs_w,
    energie_brasseurs_wh et ecart_ba (ΔθopBA, °C).
    """
    modele = preparer_modele(groupe, jeu)
    sol = sollicitations_groupe(groupe, meteo, jeu, confort_adaptatif)
    n = len(meteo)

    # Apports internes et puissances du système : colonnes absentes à zéro
    if apports is not None:
        inconnues = [c for c in apports.columns if c not in COLONNES_APPORTS]
        if inconnues or len(apports) != n:
            raise ValueError(f"apports : {n} lignes et colonnes parmi {COLONNES_APPORTS} attendues "
                             f"(colonnes inconnues : {inconnues}, lignes : {len(apports)})")
    a = {c: (apports[c].to_numpy(float) if apports is not None and c in apports.columns else np.zeros(n))
         for c in COLONNES_APPORTS}

    # Ventilation
    hg_ei = hyp("chaleur_volumique_air") * debit_ventilation(groupe)
    if efficacite_echangeur is None:
        efficacite_echangeur = hyp("ventilation_bbio_efficacite")
    if not 0.0 <= efficacite_echangeur <= 1.0:
        raise ValueError(f"Efficacité de l'échangeur hors de [0 ; 1] : {efficacite_echangeur}")

    # Brasseurs d'air
    types = preparer_brasseurs(groupe, usage_zone)
    if types:
        if entrees_brasseurs is None or any(c not in entrees_brasseurs.columns for c in COLONNES_BRASSEURS):
            raise ValueError(f"Groupe « {groupe.nom} » : brasseurs d'air présents, entrees_brasseurs doit "
                             f"porter les colonnes {COLONNES_BRASSEURS}")
        b = {c: entrees_brasseurs[c].to_numpy() for c in COLONNES_BRASSEURS}
    regimes = [ARRET] * len(types)
    habitation = usage_zone in USAGES_HABITATION

    # Colonnes en tableaux numpy : boucle horaire plus rapide qu'avec pandas
    s = {c: sol[c].to_numpy() for c in ("te", "fs1", "fs3", "phi_sl", "phi_sh")}
    etat = etat_initial()
    lignes = []
    for h in range(n):
        # Brasseurs : à l'arrêt à la première heure (pas d'heure précédente), puis pilotés par l'heure h−1
        chaleur = energie = ecart_ba = 0.0
        if types and h > 0:
            res_b = pas_brasseurs(types, regimes, groupe.volume_m3, case=int(b["case"][h]),
                                  actif=bool(b["actif"][h]), occupe=bool(b["occupe"][h]),
                                  theta_op_prec=etat.theta_op, theta_i_prec=etat.theta_i,
                                  theta_rm_prec=etat.theta_rm, theta_ifr=b["theta_ifr"][h],
                                  ecart_conf_adapt=b["ecart_conf_adapt"][h], habitation=habitation)
            regimes = res_b["regimes"]
            chaleur, energie, ecart_ba = res_b["chaleur_wh"], res_b["energie_wh"], res_b["ecart"]

        # Air soufflé après l'échangeur (éq. 378), puis calcul de l'heure
        theta_eieq = s["te"][h] + efficacite_echangeur * (etat.theta_i - s["te"][h])
        r = pas_groupe(modele, etat, te=s["te"][h], hg_ei=hg_ei, theta_eieq=theta_eieq, fs1=s["fs1"][h],
                       fs3=s["fs3"][h], phi_sl=s["phi_sl"][h], phi_sh=s["phi_sh"][h],
                       phi_conv=a["phi_conv"][h] + chaleur, phi_rad=a["phi_rad"][h],
                       phi_sys_conv=a["phi_sys_conv"][h], phi_sys_rad=a["phi_sys_rad"][h])
        avancer_etat(modele, etat, r)
        r["theta_eieq"] = theta_eieq
        r["chaleur_brasseurs_w"] = chaleur
        r["energie_brasseurs_wh"] = energie
        r["ecart_ba"] = ecart_ba
        lignes.append(r)
    return pd.DataFrame(lignes, index=meteo.index)
