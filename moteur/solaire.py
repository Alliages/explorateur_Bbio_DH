"""
============================================================
 SOLAIRE — rayonnement et éclairement reçus par une paroi,
           flux solaires transmis au groupe
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 3.1 (C_EEX_Climat extérieur)       : EDn et Edi ;
   fiche 3.2 (C_EEX_environnement_proche)  : éq. 7 à 18, 23 à 26 ;
   fiche 5.10 (C_BAT_Baie vitrée)           : éq. 206, 215, 219 à 222 ;
   fiche 5.17 (C_BAT_paroi opaque)          : éq. 288 à 292, 297 ;
 et règles Th-Bât, fascicule Parois opaques (facteur solaire S,
 formules 259 et 260).

 Données météo utilisées (une ligne par heure) :
   dirN   IDn, rayonnement direct normal (W/m²)
   diff   Idi, rayonnement diffus horizontal (W/m²)
   Gamma  hauteur du soleil (°)
   Psi    azimut du soleil (°), 0 = sud, sens horaire
   Teciel température du ciel (°C)
   te     température extérieure corrigée de l'altitude (°C)

 Chaîne de calcul pour une baie ou une paroi :
   1. angle d'incidence : cos(theta) = Max(0 ; cos(gamma).sin(beta).
      cos(psi − alpha) + sin(gamma).cos(beta))            (éq. 7)
   2. direct    Drp = IDn . cos(theta)                     (éq. 8)
      diffus    Dfp = Idi . 0,5 . (1 + cos(beta))          (éq. 9)
      réfléchi  Rrp = (IDn.sin(gamma) + Idi) . alb .
                      0,5 . (1 − |cos(beta)|)              (éq. 10-11)
   3. masques : Drp* = Drp.f_dir, Dfp* = Dfp.f_dif, Rrp* = Rrp
   4. Isr = Drp* + Dfp* + Rrp*                             (éq. 206, 288)
   5. flux transmis : baie  Fs = A . Sw . Isr, réparti en
                            Fs1 (courte longueur d'onde), Fs2
                            (réémis) et Fs3 (lame d'air ventilée)
                      paroi Phi = A . Sf . Isr
   L'éclairement suit la même chaîne avec EDn et Edi (éq. 12-16).

 Hypothèse retenue (docs/audit.md, 0.8.2) : les formules sont
 appliquées telles quelles, y compris aux quelques heures où le
 direct est non nul alors que le soleil est à l'horizon.

 Simplifications de cette version :
   - pas de protection mobile (Rprot = 0) : module 0.9.4 ;
   - pas d'espace tampon (bsolaire = bvoute = 1) ;
   - Sw = Sw1 + Sw2 + Sw3 (règles Th-Bât, formules 173 à 176) :
     Sw2 est saisi (sw2_e, sw2_c) ou pris par défaut comme une
     part de Sw (hypothèse sw2_part_defaut, docs/audit.md) ;
     Sw3 = 0 sans protection intérieure ; le facteur de pertes
     solaires flf, qui ne porte que sur Sw1, est nul (fiche 5.10).
 Depuis la 0.8.4, le U du rayonnement froid suit l'inclinaison
 (moteur/enveloppe.py, fiches 5.10 éq. 207 et 5.17 éq. 294).
============================================================
"""

import numpy as np
import pandas as pd

from config.reglages import JEUX_METEO
from moteur.enveloppe import u_baie, u_paroi
from moteur.hypotheses import hyp
from moteur.masques import facteurs_masques

COLONNES_REQUISES = ("dirN", "diff", "Gamma", "Psi", "Teciel", "te")


# ============================================================
# SOLEIL ET CIEL (indépendants de la paroi)
# ============================================================
def _controler_meteo(meteo):
    """Erreur claire s'il manque une colonne (te vient de meteo.charger_meteo)."""
    manquantes = [c for c in COLONNES_REQUISES if c not in meteo.columns]
    if manquantes:
        raise ValueError(f"Météo : colonnes manquantes {manquantes} (utiliser moteur.meteo.charger_meteo)")


def angles_soleil(meteo):
    """Hauteur gamma et azimut psi du soleil, en radians (tableaux numpy)."""
    return np.radians(meteo["Gamma"].to_numpy(float)), np.radians(meteo["Psi"].to_numpy(float))


def jour_astro(meteo):
    """Éq. 18 : 1 si le soleil est levé (gamma ≥ 0,0001 rad), 0 sinon."""
    gamma, _ = angles_soleil(meteo)
    return pd.Series((gamma >= hyp("seuil_jour_astro")).astype(int), index=meteo.index, name="jour_astro")


def eclairement_exterieur(meteo):
    """Fiche 3.1 : éclairements direct normal EDn et diffus horizontal Edi (lux).

    EDn = IDn × polynôme de degré 6 en x, x étant la hauteur du soleil en degrés (la fiche ne définit
    pas x : lecture retenue et vérifiée dans docs/audit.md, efficacité d'environ 100 lm/W).
    Edi = 124, 116 ou 128 × Idi selon que le direct normal est < 1, entre 1 et 120, ou > 120 W/m².
    """
    x = meteo["Gamma"].to_numpy(float)
    coefficients = [hyp(f"edn_a{n}") for n in range(6, -1, -1)]     # du degré 6 au terme constant
    efficacite_directe = np.polyval(coefficients, x)
    idn = meteo["dirN"].to_numpy(float)
    idi = meteo["diff"].to_numpy(float)
    efficacite_diffuse = np.where(idn < hyp("edi_seuil_bas"), hyp("edi_efficacite_couvert"),
                                  np.where(idn > hyp("edi_seuil_haut"), hyp("edi_efficacite_clair"),
                                           hyp("edi_efficacite_moyen")))
    return pd.DataFrame({"edn": idn * efficacite_directe, "edi": idi * efficacite_diffuse}, index=meteo.index)


# ============================================================
# GÉOMÉTRIE DE LA PAROI
# ============================================================
def cos_incidence(gamma, psi, orientation_deg, inclinaison_deg):
    """Éq. 7 : cosinus de l'angle entre le soleil et la normale à la paroi.

    theta = Min[pi/2 ; Arccos(...)], donc cos(theta) = Max(0 ; ...) : nul quand le soleil est derrière.
    Une paroi horizontale n'a pas besoin d'orientation (sin(beta) = 0).
    """
    beta = np.radians(inclinaison_deg)
    if orientation_deg is None:
        if abs(np.sin(beta)) > 1e-9:
            raise ValueError("Orientation à renseigner pour une paroi non horizontale")
        orientation_deg = 0.0
    alpha = np.radians(orientation_deg)
    produit = np.cos(gamma) * np.sin(beta) * np.cos(psi - alpha) + np.sin(gamma) * np.cos(beta)
    return np.maximum(0.0, np.clip(produit, -1.0, 1.0))


def facteurs_inclinaison(inclinaison_deg):
    """Facteurs de vue du ciel 0,5.(1 + cos beta) (éq. 9) et du sol 0,5.(1 − |cos beta|) (éq. 10)."""
    cos_beta = np.cos(np.radians(inclinaison_deg))
    return 0.5 * (1.0 + cos_beta), 0.5 * (1.0 - abs(cos_beta))


def environnement_proche(meteo, composant):
    """Rayonnement et éclairement reçus par une baie ou une paroi, heure par heure (fiche 3.2).

    Colonnes (W/m² pour le rayonnement, lux pour l'éclairement) :
      cos_theta                      cosinus de l'angle d'incidence
      drp, dfp, rrp                  direct, diffus, réfléchi incidents, sans masque
      f_dir, f_dif                   facteurs d'affaiblissement des masques
      drp_m, dfp_m, rrp_m            les mêmes, masques compris (Drp*, Dfp*, Rrp*)
      isr                            rayonnement global atteignant la paroi
      erp_m, efp_m, errp_m, etp      éclairements atteignant la paroi, masques compris
      qer                            rayonnement froid vers la voûte céleste (W/m², éq. 17)
    """
    _controler_meteo(meteo)
    gamma, psi = angles_soleil(meteo)
    idn = meteo["dirN"].to_numpy(float)
    idi = meteo["diff"].to_numpy(float)

    cos_theta = cos_incidence(gamma, psi, composant.orientation_deg, composant.inclinaison_deg)
    vue_ciel, vue_sol = facteurs_inclinaison(composant.inclinaison_deg)
    f_dir, f_dif = facteurs_masques(composant, gamma, psi)

    # Rayonnement (éq. 8 à 11), puis masques (éq. 23 à 25 : le réfléchi n'est pas masqué)
    drp = idn * cos_theta
    dfp = idi * vue_ciel
    rrp = (idn * np.sin(gamma) + idi) * hyp("albedo_sol") * vue_sol

    # Éclairement (éq. 12 à 16), mêmes facteurs de masque
    eclairement = eclairement_exterieur(meteo)
    edn = eclairement["edn"].to_numpy()
    edi = eclairement["edi"].to_numpy()
    erp = edn * cos_theta
    efp = edi * vue_ciel
    errp = (edn * np.sin(gamma) + edi) * hyp("albedo_eclairement") * vue_sol

    # Rayonnement froid vers la voûte céleste (éq. 17) : nul pour une paroi verticale ou tournée vers le bas
    cos_beta = np.cos(np.radians(composant.inclinaison_deg))
    qer = hyp("hre") * (meteo["Teciel"].to_numpy(float) - meteo["te"].to_numpy(float)) * max(cos_beta, 0.0)

    resultat = pd.DataFrame({
        "cos_theta": cos_theta, "drp": drp, "dfp": dfp, "rrp": rrp, "f_dir": f_dir, "f_dif": f_dif,
        "drp_m": drp * f_dir, "dfp_m": dfp * f_dif, "rrp_m": rrp,
        "erp_m": erp * f_dir, "efp_m": efp * f_dif, "errp_m": errp,
        "qer": qer,
    }, index=meteo.index)
    resultat["isr"] = resultat["drp_m"] + resultat["dfp_m"] + resultat["rrp_m"]
    resultat["etp"] = resultat["erp_m"] + resultat["efp_m"] + resultat["errp_m"]
    return resultat


# ============================================================
# FACTEURS SOLAIRES
# ============================================================
def _controler_jeu(jeu):
    if jeu not in JEUX_METEO:
        raise ValueError(f"Jeu météo inconnu : « {jeu} » (attendu : {', '.join(JEUX_METEO)})")


def sw_baie(baie, jeu):
    """Sw global de la baie sans protection mobile : Sw-e en Th-D, Sw-c en Th-BC (fiche 5.10, éq. 223-224).

    Sans Sw-c saisi, Sw-c = Sw-e − 0,1 (éq. 215), borné à 0.
    """
    _controler_jeu(jeu)
    if baie.sw_e is None:
        raise ValueError(f"Baie « {baie.nom} » : facteur solaire sw_e à renseigner")
    if jeu == "th_d":
        return baie.sw_e
    if baie.sw_c is not None:
        return baie.sw_c
    return max(0.0, baie.sw_e - hyp("ecart_sw_c_e"))


def sw2_baie(baie, jeu):
    """Sw2 de la baie sans protection mobile : part de Sw réémise vers l'intérieur (grande longueur d'onde et
    convection). Valeur saisie (sw2_e en Th-D, sw2_c en Th-BC), sinon part par défaut de Sw (hypothèse).

    Sw1 = Sw − Sw2 (courte longueur d'onde) ; Sw3 = 0 sans protection intérieure (formules 173 à 176).
    """
    sw = sw_baie(baie, jeu)
    saisi = baie.sw2_e if jeu == "th_d" else baie.sw2_c
    sw2 = saisi if saisi is not None else hyp("sw2_part_defaut") * sw
    if sw2 > sw:
        raise ValueError(f"Baie « {baie.nom} » : Sw2 ({sw2}) dépasse Sw ({sw}) en {jeu}")
    return sw2


def facteurs_solaires_paroi(paroi):
    """(Sf-c, Sf-e) d'une paroi opaque : valeurs saisies, sinon règles Th-Bât (formules 259 et 260).

    Sf-c = alpha . Up-C . Rse-C          (Rse-C = 0,04 m².K/W)
    Sf-e = alpha . Up-E . Rse-E          (Rse-E = 0,07 m².K/W, 1/Up-E = 1/Up-C + 0,03)
    """
    sf_c, sf_e = paroi.sf_c, paroi.sf_e
    if sf_c is None or sf_e is None:
        if paroi.alpha is None or paroi.u is None:
            raise ValueError(f"Paroi « {paroi.nom} » : renseigner sf_c et sf_e, ou alpha et u")
        u_e = 1.0 / (1.0 / paroi.u + hyp("ecart_resistances_c_e"))
        if sf_c is None:
            sf_c = paroi.alpha * paroi.u * hyp("rse_c")
        if sf_e is None:
            sf_e = paroi.alpha * u_e * hyp("rse_e")
    return sf_c, sf_e


# ============================================================
# FLUX TRANSMIS AU GROUPE
# ============================================================
def flux_solaires_baie(baie, meteo, jeu):
    """Flux transmis au groupe par une baie sans protection mobile (W), heure par heure.

      fs1   = A . Sw1 . Isr                   (éq. 219 : courte longueur d'onde)
      fs2   = A . Sw2 . Isr                   (éq. 220 : réémis, grande longueur d'onde et convection)
      fs3   = A . Sw3 . Isr = 0               (éq. 221 : lame d'air intérieure ventilée, sans objet ici)
      fs    = fs1 + fs2 + fs3 = A . Sw . Isr  (Rprot = 0, bsolaire = 1, flf = 0)
      ftvc  = A . Uw . Qer* / he              (éq. 222, pas d'espace tampon ; Uw selon l'inclinaison)
    """
    sw = sw_baie(baie, jeu)
    sw2 = sw2_baie(baie, jeu)
    env = environnement_proche(meteo, baie)
    fs1 = baie.surface_m2 * (sw - sw2) * env["isr"]
    fs2 = baie.surface_m2 * sw2 * env["isr"]
    fs3 = 0.0 * env["isr"]
    ftvc = baie.surface_m2 * u_baie(baie) * env["qer"] / hyp("he")
    return pd.DataFrame({"fs": fs1 + fs2 + fs3, "fs1": fs1, "fs2": fs2, "fs3": fs3, "ftvc": ftvc},
                        index=meteo.index)


def flux_solaires_paroi(paroi, meteo, jeu, confort_adaptatif=None):
    """Flux transmis au groupe par une paroi opaque (W), heure par heure.

      phi_s  = A . Sf . Isr                   (éq. 289, bsolaire = 1)
      phi_vc = A . Qer* . U / he              (éq. 297, bvoute = 1 ; U selon l'inclinaison)

    Sf (éq. 290 à 292) : Sf-c en Th-BC ; en Th-D, Sf-e pendant la période de confort adaptatif et Sf-c
    en dehors. Cette période (fiche 3.1) est calculée avec les DH (0.8.10) : en Th-D, la passer dans
    confort_adaptatif (1 ou True pour les heures concernées, une valeur par heure).

    Une paroi sur le sol ou sur un local non chauffé ne reçoit pas de soleil : flux nuls.
    """
    _controler_jeu(jeu)
    if paroi.contact != "exterieur":
        return pd.DataFrame({"phi_s": 0.0, "phi_vc": 0.0}, index=meteo.index)
    sf_c, sf_e = facteurs_solaires_paroi(paroi)
    if jeu == "th_bc":
        sf = sf_c
    else:
        if confort_adaptatif is None:
            raise ValueError("Th-D : période de confort adaptatif à fournir (confort_adaptatif)")
        part_e = np.asarray(confort_adaptatif, dtype=float)
        if part_e.shape != (len(meteo),):
            raise ValueError(f"confort_adaptatif : {len(meteo)} valeurs attendues")
        sf = (1.0 - part_e) * sf_c + part_e * sf_e
    env = environnement_proche(meteo, paroi)
    phi_s = paroi.surface_m2 * sf * env["isr"]
    phi_vc = paroi.surface_m2 * env["qer"] * u_paroi(paroi) / hyp("he")
    return pd.DataFrame({"phi_s": phi_s, "phi_vc": phi_vc}, index=meteo.index)
