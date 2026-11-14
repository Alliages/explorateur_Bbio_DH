r"""
============================================================
 PROTECTIONS MOBILES — volets et stores des baies
============================================================
 Sources : annexe III de l'arrêté du 4 août 2021
   fiche 5.9 (C_BAT_Gestion_protections_mobiles), éq. 175 à 192,
     figures 34, 35, 38 et 44 : ratio de fermeture Rprot ;
   fiche 4.1, éq. 50 à 53 : occupation au sens des protections ;
   fiche 5.10 (C_BAT_Baie vitrée), éq. 209 à 211 et 219 à 222 :
     effet sur la déperdition et sur les flux de la baie.

 Chaque heure, une baie est partagée en une part protégée
 (Rprot) et une part nue (1 − Rprot) :

     flux solaire   = A × Isr × [(1 − Rprot) × Sw_nu + Rprot × Sw_protégé]
     déperdition    = A × [(1 − Rprot) × U_nu + Rprot × U_protégé]

 Rprot n'est pas saisi : il est CONVENTIONNEL. Il dépend de la
 protection (volet, store enroulable), de sa gestion, de la
 saison du groupe, de l'occupation, de l'éclairement reçu par la
 baie et de la chaleur de la veille.

 Gestion manuelle — matrices conventionnelles de l'habitation :

   locaux occupés, de jour     Rprot
   (70 % des baies)             1 |            ________
                                  |          /
                           Rprot0 |________/
                                  +--------------------> éclairement
                                  0        Ecl1             (lux)

      Rprot0 et Ecl1 dépendent de la saison ; en été, la ligne
      « chaude » s'applique si la température opérative a
      dépassé 26,5 °C la veille ;
   locaux occupés, de nuit     une valeur par saison (volets
                               fermés à 80 ou 90 %) ;
   locaux inoccupés            une valeur de jour, une de nuit.

 Gestion automatique : six valeurs par saison et par occupation
 (jour sombre, jour clair, nuit ; ambiance chaude ou fraîche),
 et, pendant l'occupation, une part des baies reprise à la main
 (dérogation : 25 % des 70 %).

 « Jour » et « nuit » : en gestion manuelle et en occupation, il
 fait jour quand la baie reçoit de la lumière ; pendant une
 absence de journée les protections gardent leur position de
 jour, pendant les vacances celle de nuit (fiche 4.1, éq. 52).

 Hypothèses de l'outil (docs/audit.md, 0.8.12) : les trois seuils
 de la gestion automatique ne figurent ni dans l'annexe ni dans
 les fichiers d'étude ; stores vénitiens et seconde protection
 non traités ; éclairage artificiel calculé baies nues.
============================================================
"""

import csv
from functools import lru_cache

import numpy as np

from config.reglages import (CHEMIN_PROTECTIONS_AUTOMATIQUES, CHEMIN_PROTECTIONS_MANUELLES, DECIMALE_CSV,
                             ENCODAGE_CSV, SEPARATEUR_CSV)
from moteur.enveloppe import u_baie
from moteur.hypotheses import hyp
from moteur.solaire import environnement_proche, sw2_baie, sw_baie

FAMILLE = "habitation"      # seule famille d'usages décrite (logement collectif)
# Saison propre du groupe (fiche 4.6 : 1 refroidissement, 2 mi-saison, 3 chauffage, 4 mixte) → saison des
# protections (fiche 5.9, éq. 181)
SAISON_GPM = {3: "hiver", 2: "mi_saison", 4: "mi_saison", 1: "ete"}
# Occupation au sens des protections mobiles (fiche 4.1, éq. 50 à 53)
OCCUPE, ABSENCE_DE_JOUR, ABSENCE_LONGUE = 1, 0, -1
COLONNES_AUTO = ("jour_sombre_chaud", "jour_sombre_frais", "jour_clair_chaud", "jour_clair_frais", "nuit_chaud",
                 "nuit_frais")


def _nombre(texte):
    return float(texte.replace(DECIMALE_CSV, ".")) if texte != "" else None


# ============================================================
# 1. MATRICES CONVENTIONNELLES (fiche 5.9, figures 35, 38 et 44)
# ============================================================
@lru_cache(maxsize=1)
def matrices_manuelles():
    """{(protection, gestion, occupation, ligne): (rprot0, ecl1, rprot_nuit)} pour l'habitation.

    gestion : manuelle_non_motorisee, manuelle_motorisee, derogation_sans_detecteur, derogation_avec_detecteur ;
    ligne : hiver, mi_saison, ete_frais, ete_chaud. En inoccupation, rprot0 est la valeur de jour et ecl1 est vide.
    """
    table = {}
    with open(CHEMIN_PROTECTIONS_MANUELLES, encoding=ENCODAGE_CSV, newline="") as f:
        for ligne in csv.DictReader(f, delimiter=SEPARATEUR_CSV):
            if ligne["famille"] == FAMILLE:
                cle = (ligne["protection"], ligne["gestion"], ligne["occupation"], ligne["ligne"])
                table[cle] = (_nombre(ligne["rprot0"]), _nombre(ligne["ecl1"]), _nombre(ligne["rprot_nuit"]))
    return table


@lru_cache(maxsize=1)
def matrices_automatiques():
    """{(occupation, saison): {colonne: ratio}} pour l'habitation, volets et stores enroulables (figure 44)."""
    table = {}
    with open(CHEMIN_PROTECTIONS_AUTOMATIQUES, encoding=ENCODAGE_CSV, newline="") as f:
        for ligne in csv.DictReader(f, delimiter=SEPARATEUR_CSV):
            if ligne["famille"] == FAMILLE:
                table[(ligne["occupation"], ligne["saison"])] = {c: _nombre(ligne[c]) for c in COLONNES_AUTO}
    return table


# ============================================================
# 2. OCCUPATION AU SENS DES PROTECTIONS MOBILES (fiche 4.1, éq. 50 à 53)
# ============================================================
def occupation_gpm(scenarios, calendrier):
    """Indice heure par heure : 1 occupé, 0 absence de journée, −1 absence de nuit ou de vacances.

    Une absence « de journée » est une plage inoccupée comprise entre les cases 7 et 22, précédée et suivie d'une
    heure occupée le même jour (éq. 52) : les protections y gardent leur position de jour.
    """
    horaire = scenarios.horaire["occupation"] > 0           # 7 jours × 24 cases
    indice = np.where(horaire, OCCUPE, ABSENCE_LONGUE)
    debut, fin = int(hyp("gpm_heure_debut_absence_jour")), int(hyp("gpm_heure_fin_absence_jour"))
    for jour in range(horaire.shape[0]):
        occupe = horaire[jour]
        for h_deb in range(debut, fin + 1):                 # cases comptées de 1 : la case h est à l'indice h − 1
            if not occupe[h_deb - 1] and occupe[h_deb - 2]:
                for h_fin in range(h_deb, fin + 1):
                    if not occupe[h_fin - 1] and occupe[h_fin]:
                        indice[jour, h_deb - 1:h_fin] = np.where(occupe[h_deb - 1:h_fin], OCCUPE, ABSENCE_DE_JOUR)
                        break
    heures = indice[calendrier["jour_semaine"].to_numpy() - 1, calendrier["case"].to_numpy() - 1]
    # Semaine de vacances (scénario hebdomadaire à 0) : absence longue, quelle que soit l'heure (éq. 50 et 53)
    semaine = scenarios.semaine["occupation"][calendrier["semaine_mois"].to_numpy() - 1,
                                              calendrier["mois"].to_numpy() - 1]
    return np.where(semaine > 0, heures, ABSENCE_LONGUE)


# ============================================================
# 3. RATIO DE FERMETURE D'UNE PROTECTION (fiche 5.9, éq. 177, 186 à 192)
# ============================================================
def ligne_saison(saison_gpm, theta_op_max_veille):
    """Ligne des matrices manuelles : l'été se dédouble selon la température maximale de la veille (26,5 °C)."""
    if saison_gpm != "ete":
        return saison_gpm
    return "ete_chaud" if theta_op_max_veille >= hyp("gpm_temperature_limite_manuelle") else "ete_frais"


def rprot_selon_eclairement(etp, rprot0, ecl1):
    """Ratio de fermeture en occupation, de jour : croît de Rprot0 (éclairement nul) à 1 (éclairement Ecl1) (éq. 177)."""
    return np.where(etp >= ecl1, 1.0, rprot0 + (1.0 - rprot0) * etp / ecl1)


def rprot_manuel_occupe(protection, gestion, ligne, etp, jour):
    """Rprot des locaux occupés, gestion manuelle ou dérogation manuelle (éq. 188) ; etp et jour par baie."""
    rprot0, ecl1, nuit = matrices_manuelles()[(protection, gestion, "occupation", ligne)]
    return np.where(jour, rprot_selon_eclairement(etp, rprot0, ecl1), nuit)


def rprot_manuel_inoccupe(protection, gestion, ligne, jour):
    """Rprot des locaux inoccupés, gestion manuelle : une valeur de jour, une de nuit (éq. 189)."""
    de_jour, _, de_nuit = matrices_manuelles()[(protection, gestion, "inoccupation", ligne)]
    return np.where(jour, de_jour, de_nuit)


def rprot_automatique(occupe, saison_gpm, etp, jour, chaud):
    """Rprot en gestion automatique (figure 44) : selon l'éclairement de la baie et l'ambiance chaude ou fraîche."""
    valeurs = matrices_automatiques()[("occupation" if occupe else "inoccupation", saison_gpm)]
    suffixe = "chaud" if chaud else "frais"
    clair = etp >= hyp("gpm_auto_eclairement_seuil")
    de_jour = np.where(clair, valeurs[f"jour_clair_{suffixe}"], valeurs[f"jour_sombre_{suffixe}"])
    return np.where(jour, de_jour, valeurs[f"nuit_{suffixe}"])


# ============================================================
# 4. LES BAIES D'UN GROUPE, HEURE PAR HEURE
# ============================================================
def groupe_protege(groupe):
    """Vrai si au moins une baie du groupe porte une protection mobile."""
    return any(baie.protection is not None for baie in groupe.baies)


def _u_protege(baie):
    """U de la baie protection en place, selon son inclinaison : même interpolation que le U nu (éq. 208)."""
    horizontal = baie.uw_horizontal_protege if baie.uw_horizontal_protege is not None else baie.uw_protege
    copie = type(baie)(baie.nom, baie.surface_m2, baie.orientation_deg, baie.inclinaison_deg, uw=baie.uw_protege,
                       uw_horizontal=horizontal)
    return u_baie(copie)


class ProtectionsGroupe:
    """Baies d'un groupe avec leurs protections mobiles : ratios de fermeture, flux et déperdition de chaque heure.

    Usage : pas(h, ...) à chaque heure, dans l'ordre ; il rend les flux des baies et leur transmission Hg_es.
    Le rayonnement et l'éclairement reçus par chaque baie sont calculés une fois pour l'année.
    """

    def __init__(self, groupe, meteo, jeu):
        baies = groupe.baies
        nb, heures = len(baies), len(meteo)
        self.surface = np.array([b.surface_m2 for b in baies])
        # Rayonnement (W), rayonnement froid (W par W/m².K) et éclairement (lux) de chaque baie, par heure
        self.a_isr = np.zeros((nb, heures))
        self.a_qer = np.zeros((nb, heures))
        self.etp = np.zeros((nb, heures))
        for i, baie in enumerate(baies):
            env = environnement_proche(meteo, baie)
            self.a_isr[i] = baie.surface_m2 * env["isr"].to_numpy()
            self.a_qer[i] = baie.surface_m2 * env["qer"].to_numpy() / hyp("he")
            self.etp[i] = env["etp"].to_numpy()
        # Baie nue (« sp ») et baie protégée (« ap ») : Sw1, Sw2, Sw3 et U
        sw = np.array([sw_baie(b, jeu) for b in baies])
        self.sw2_nu = np.array([sw2_baie(b, jeu) for b in baies])
        self.sw1_nu = sw - self.sw2_nu
        self.u_nu = np.array([u_baie(b) for b in baies])
        protegee = [b.protection is not None for b in baies]
        self.sw2_pro = np.array([b.sw2_protege if p else 0.0 for b, p in zip(baies, protegee)])
        self.sw3_pro = np.array([b.sw3_protege if p else 0.0 for b, p in zip(baies, protegee)])
        self.sw1_pro = np.array([b.sw_protege - b.sw2_protege - b.sw3_protege if p else 0.0
                                 for b, p in zip(baies, protegee)])
        self.u_pro = np.array([_u_protege(b) if p else 0.0 for b, p in zip(baies, protegee)])
        # Baies regroupées par classe de gestion : mêmes règles, seul l'éclairement reçu diffère
        self.classes = {}
        for i, baie in enumerate(baies):
            if baie.protection is not None:
                cle = (baie.protection, baie.gestion_protection, baie.detecteur_presence,
                       baie.horloge_crepusculaire, baie.protection_exterieure)
                self.classes.setdefault(cle, []).append(i)
        self.classes = {cle: np.array(indices) for cle, indices in self.classes.items()}
        self.vent = hyp("vent_correction_locale") * meteo["Vent"].to_numpy(float)       # fiche 3.1 : Ventc
        self.part_occupee = hyp("gpm_part_occupee_logement_collectif")
        self.part_derogation = hyp("gpm_part_derogation_logement_collectif")
        self.chaud = False              # gestion automatique : ambiance chaude (hystérésis entre deux seuils)
        self.nb = nb

    def ratios(self, h, saison, occupe, indice_gpm, theta_op_prec, theta_op_max_veille):
        """Ratios de fermeture des baies à l'heure h.

        saison                 saison propre du groupe (1 à 4, fiche 4.6)
        occupe                 la zone est occupée (scénario d'occupation)
        indice_gpm             occupation au sens des protections (1, 0 ou −1)
        theta_op_prec          température opérative en fin d'heure précédente (°C)
        theta_op_max_veille    maximum de cette température la veille (°C)
        Sortie : (rprot, rprot_u), par baie. rprot pèse les flux solaires (éq. 209) ; rprot_u pèse le U : il n'en
        diffère qu'en gestion automatique, où la part automatique ne compte que si elle est fermée (éq. 211).
        """
        rprot, rprot_u = np.zeros(self.nb), np.zeros(self.nb)
        saison_gpm = SAISON_GPM[saison]
        ligne = ligne_saison(saison_gpm, theta_op_max_veille)
        # Ambiance chaude ou fraîche de la gestion automatique, avec hystérésis (fiche 5.9, figure 31)
        if theta_op_prec > hyp("gpm_auto_temperature_haute"):
            self.chaud = True
        elif theta_op_prec < hyp("gpm_auto_temperature_basse"):
            self.chaud = False
        grand_vent = self.vent[h] >= hyp("gpm_vent_limite_store")

        for (protection, gestion, detecteur, crepusculaire, exterieure), indices in self.classes.items():
            etp = self.etp[indices, h]
            eclairee = etp > 0
            if gestion == "automatique":
                # Jour de la gestion automatique : toujours, sauf horloge crépusculaire (éq. 182)
                jour = eclairee if crepusculaire else np.ones(len(indices), dtype=bool)
                auto = rprot_automatique(occupe, saison_gpm, etp, jour, self.chaud)
                part = self.part_occupee * self.part_derogation if occupe else 0.0      # éq. 179
                derogation = "derogation_avec_detecteur" if detecteur else "derogation_sans_detecteur"
                manuel = rprot_manuel_occupe(protection, derogation, ligne, etp, jour) if occupe else 0.0
                r = part * manuel + (1.0 - part) * auto                                 # éq. 209
                r_u = part * manuel + (1.0 - part) * (auto >= 1.0)                      # éq. 211
            else:
                # Jour de la gestion manuelle (éq. 183) : selon l'occupation au sens des protections
                if indice_gpm == OCCUPE:
                    jour = eclairee
                else:
                    jour = np.full(len(indices), indice_gpm == ABSENCE_DE_JOUR)
                inoccupe = rprot_manuel_inoccupe(protection, gestion, ligne, jour)
                if occupe:
                    occupes = rprot_manuel_occupe(protection, gestion, ligne, etp, jour)
                    r = self.part_occupee * occupes + (1.0 - self.part_occupee) * inoccupe     # éq. 178, 209
                else:
                    r = inoccupe
                r_u = r                                                                 # éq. 210
            # Store enroulable extérieur : remonté par grand vent (éq. 190 à 192)
            if protection == "store_enroulable" and exterieure and grand_vent:
                r, r_u = 0.0, 0.0
            rprot[indices], rprot_u[indices] = r, r_u
        return rprot, rprot_u

    def flux(self, h, rprot, rprot_u):
        """Flux des baies (W) et transmission Hg_es (W/K) de l'heure h (fiche 5.10, éq. 210-211 et 219 à 222)."""
        isr, nu = self.a_isr[:, h], 1.0 - rprot
        u_flux = nu * self.u_nu + rprot * self.u_pro
        return {"fs1": float(isr @ (nu * self.sw1_nu + rprot * self.sw1_pro)),
                "fs2": float(isr @ (nu * self.sw2_nu + rprot * self.sw2_pro)),
                "fs3": float(isr @ (rprot * self.sw3_pro)),
                "ftvc": float(self.a_qer[:, h] @ u_flux),
                "hg_es": float(self.surface @ ((1.0 - rprot_u) * self.u_nu + rprot_u * self.u_pro)),
                "rprot_moyen": float(self.surface @ rprot / self.surface.sum()) if self.nb else 0.0}

    def pas(self, h, saison, occupe, indice_gpm, theta_op_prec, theta_op_max_veille):
        """Ratios puis flux de l'heure h : dictionnaire fs1, fs2, fs3, ftvc, hg_es et rprot_moyen (pondéré par les
        surfaces de baie)."""
        return self.flux(h, *self.ratios(h, saison, occupe, indice_gpm, theta_op_prec, theta_op_max_veille))
