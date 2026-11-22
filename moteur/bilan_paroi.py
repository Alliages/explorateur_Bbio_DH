"""
============================================================
 BILAN PAR PAROI — ce que chaque baie et chaque paroi opaque
                   apporte ou fait perdre au groupe
============================================================
 Calcul fait après celui du groupe (moteur/besoins.py), avec ses
 sorties horaires : il ne change aucun résultat, il les répartit.

     météo ──→ rayonnement reçu par la paroi, Isr (fiche 3.2)
     heures du groupe : θi, fermeture de chaque baie (rprot),
                        période de confort adaptatif (Th-D)
                  │
                  ▼
     pour chaque baie et chaque paroi opaque, heure par heure :
       isr          rayonnement reçu, masques compris (W/m²)
       solaire      flux solaire transmis au groupe (W)
                      baie   A . Isr . [(1 − r) . Sw + r . Sw protégé]   (éq. 219 à 221, 209)
                      paroi  A . Sf . Isr                                 (éq. 289)
       froid        rayonnement froid vers la voûte céleste (W, négatif)
                      baie   A . U . Qer / he                             (éq. 222)
                      paroi  A . U . Qer / he                             (éq. 297)
       deperdition  chaleur qui sort par conduction, telle que le
                    modèle du groupe la calcule (fiche 5.21 ; W,
                    négative quand la paroi fait entrer de la chaleur) :
                      baie   part A . U de Hg,es . (θs − θe), plus la
                             part A du rayonnement intérieur perdu par
                             les vitrages (1 − garde des baies, éq. 361)
                      paroi  part A . b . U de Hg,em . (θmq − θe), moins
                             le soleil et le ciel que Hg,em / H_TH ajoute
                             à φsh (éq. 344)
       rprot        fermeture de la protection (baie), 0 à 1
       rouv         part ouverte des baies du groupe (rouv_moyen de
                    moteur/besoins.py : une moyenne de toutes les
                    baies, la même pour chacune ; 0 pour une paroi)
 Les températures sont celles des nœuds du modèle, en moyenne sur
 l'heure : θs (surfaces intérieures) pour les baies, θmq (masse)
 pour les parois opaques et les ponts thermiques ; parois et
 baies ne voient pas l'air θi.

 Les autres échanges du groupe (postes_du_groupe), heure par
 heure, pour le bilan en coupe (brique « Le bilan en coupe ») :
       ventilation       hg_ventilation . (θsouffle − θi)
       infiltrations     hg_infiltrations . (θe − θi)
       ouvertures        hg_ouvertures . (θe − θi)   (baies ouvertes)
       ponts_thermiques  part H_TH,pt de Hg,em . (θe − θmq)    (éq. 305)
       apports_internes  occupants, usages, éclairage, brasseurs
       chauffage         puissance émise (q_ch)
       refroidissement   − puissance de froid (q_fr)
 Signe : positif quand la chaleur entre dans le logement.

 Bilan exact, heure par heure (hypothèse 103 de docs/audit.md) :
     Σ ce qui entre par les parois et les baies (entrant) + Σ postes
       = stockage de la masse quotidienne − flux des inerties longues
       = masse_gardee(horaire)
 Les trois termes d'air redonnent Hg,ei . (θeieq − θi), le flux
 d'air du modèle ; parois, baies et ponts redonnent flux_parois et
 flux_baies (moteur/groupe.py), la seule répartition entre parois
 étant au prorata de leur conductance.

 Contrôles (tests/test_bilan_paroi.py) : soleil et ciel des baies
 = fs1 + fs3 + φsl du groupe, des parois opaques = φsh ; bilan
 exact à 10⁻⁶ W près.

 Limite (hypothèse 102) : le U des baies suit le ratio rprot des
 flux solaires ; en gestion automatique, le moteur prend pour le
 U un ratio un peu différent (éq. 211). Il ne sert qu'à répartir
 Hg,es entre les baies : la somme reste exacte.

 Ce fichier ne dépend pas de l'interface.
============================================================
"""

import numpy as np
import pandas as pd

from moteur.besoins import PREFIXE_RPROT_BAIE
from moteur.enveloppe import transmission_ponts, u_baie, u_paroi
from moteur.groupe import preparer_modele
from moteur.hypotheses import hyp
from moteur.protections import u_protege
from moteur.solaire import environnement_proche, flux_solaires_paroi, sw_baie

# ============================================================
# RÉGLAGES
# ============================================================
COLONNES = ("isr", "solaire", "froid", "deperdition", "rprot", "rouv")
POSTES = ("ventilation", "infiltrations", "ouvertures", "ponts_thermiques", "apports_internes", "chauffage",
          "refroidissement")
WH_PAR_KWH = 1000.0


# ============================================================
# HEURE PAR HEURE
# ============================================================
def _baie(baie, rang, meteo, jeu, horaire):
    """Heures d'une baie, sans la déperdition (calculée pour toutes les baies ensemble) ; colonne « au » : A . U de
    l'heure, pour répartir Hg,es entre les baies."""
    env = environnement_proche(meteo, baie)
    colonne = f"{PREFIXE_RPROT_BAIE}{rang}"
    r = horaire[colonne].to_numpy(float) if colonne in horaire else np.zeros(len(meteo))
    sw_nu, u_nu = sw_baie(baie, jeu), u_baie(baie)
    # Sans protection mobile, r reste nul : les valeurs « protégées » ne servent pas
    sw_pro = baie.sw_protege if baie.protection is not None else sw_nu
    u_pro = u_protege(baie) if baie.protection is not None else u_nu
    u = (1.0 - r) * u_nu + r * u_pro
    isr = env["isr"].to_numpy()
    return pd.DataFrame({"isr": isr,
                         "solaire": baie.surface_m2 * isr * ((1.0 - r) * sw_nu + r * sw_pro),
                         "froid": baie.surface_m2 * u * env["qer"].to_numpy() / hyp("he"),
                         "deperdition": 0.0, "rprot": r, "rouv": horaire["rouv_moyen"].to_numpy(float),
                         "au": baie.surface_m2 * u}, index=meteo.index)


def _paroi(paroi, meteo, jeu, confort_adaptatif, vers_la_masse, renfort):
    """Heures d'une paroi opaque : voir l'en-tête du module. vers_la_masse : Hg,em . (θmq − θe) / H_TH heure par
    heure ; renfort : Hg,em / H_TH. Une paroi sur le sol ou sur un local non chauffé ne reçoit pas de soleil
    (solaire.flux_solaires_paroi) : son rayonnement reçu est compté nul."""
    flux = flux_solaires_paroi(paroi, meteo, jeu, confort_adaptatif)
    isr = environnement_proche(meteo, paroi)["isr"].to_numpy() if paroi.contact == "exterieur" \
        else np.zeros(len(meteo))
    solaire, froid = flux["phi_s"].to_numpy(), flux["phi_vc"].to_numpy()
    h_paroi = paroi.surface_m2 * paroi.b_therm * u_paroi(paroi)
    # Le modèle injecte φsh . Hg,em / H_TH dans la masse (éq. 344) : le surplus est compté avec la conduction
    deperdition = h_paroi * vers_la_masse - (renfort - 1.0) * (solaire + froid)
    return pd.DataFrame({"isr": isr, "solaire": solaire, "froid": froid, "deperdition": deperdition,
                         "rprot": 0.0, "rouv": 0.0}, index=meteo.index)


def _modele(groupe, jeu, meteo, horaire):
    """(Hg,em / H_TH, Hg,em . (θmq − θe) / H_TH heure par heure) : de quoi répartir flux_parois au prorata des
    conductances."""
    modele = preparer_modele(groupe, jeu)
    if modele.h_th <= 0:
        return 1.0, np.zeros(len(meteo))
    ecart = horaire["theta_mq_moy"].to_numpy(float) - meteo["te"].to_numpy(float)
    return modele.hg_em / modele.h_th, modele.hg_em * ecart / modele.h_th


def rayonnement_perdu_par_les_baies(horaire):
    """Part des apports radiatifs (occupants, appareils, émetteur) que les baies laissent repartir dehors, heure par
    heure (W) : ce que le modèle injecte en moins dans les nœuds (1 − garde des baies, éq. 361)."""
    return (horaire["fs1"] + horaire["fs3"] + horaire["phi_apports"] + horaire["q_ch_wh"] - horaire["q_fr_wh"]
            - horaire["flux_apports"]).to_numpy(float)


def bilan_parois(groupe, meteo, jeu, horaire):
    """Bilan heure par heure de chaque baie et de chaque paroi opaque du groupe : {nom du composant: DataFrame aux
    colonnes COLONNES}.

    meteo     la météo du calcul (jeu « th_bc » pour le Bbio, « th_d » pour le DH), altitude corrigée
    horaire   le résultat de moteur.besoins.calculer_besoins pour ce groupe et cette météo : températures des
              nœuds, flux du modèle, rprot_baie_<rang> (s'il y a des protections) et, en Th-D, confort_adaptatif
    """
    if len(horaire) != len(meteo):
        raise ValueError(f"Bilan par paroi : {len(meteo)} heures de météo, {len(horaire)} heures de calcul")
    confort_adaptatif = horaire["confort_adaptatif"].to_numpy() if jeu == "th_d" else None
    # Baies : Hg,es . (θs − θe) réparti au prorata de A . U, le rayonnement intérieur perdu au prorata de A
    baies = {baie.nom: _baie(baie, rang, meteo, jeu, horaire) for rang, baie in enumerate(groupe.baies)}
    if baies:
        somme_au = sum(h["au"] for h in baies.values()).to_numpy()
        surface = sum(baie.surface_m2 for baie in groupe.baies)
        vers_les_surfaces = horaire["hg_es"].to_numpy(float) * (horaire["theta_s_moy"].to_numpy(float)
                                                                 - meteo["te"].to_numpy(float))
        perdu = rayonnement_perdu_par_les_baies(horaire)
        for baie in groupe.baies:
            heures = baies[baie.nom]
            part = np.divide(heures["au"].to_numpy(), somme_au, out=np.zeros(len(meteo)), where=somme_au > 0)
            heures["deperdition"] = part * vers_les_surfaces + baie.surface_m2 / surface * perdu
            baies[baie.nom] = heures.drop(columns="au")
    renfort, vers_la_masse = _modele(groupe, jeu, meteo, horaire)
    bilan = dict(baies)
    bilan.update({paroi.nom: _paroi(paroi, meteo, jeu, confort_adaptatif, vers_la_masse, renfort)
                  for paroi in groupe.parois})
    return bilan


def entrant(heures):
    """Chaleur qui entre dans le logement par un composant, heure par heure (W ; négatif : elle sort) : soleil
    transmis, moins le rayonnement froid vers le ciel et la déperdition."""
    return heures["solaire"] + heures["froid"] - heures["deperdition"]


def postes_du_groupe(groupe, meteo, horaire, jeu):
    """Les échanges du groupe qui ne passent pas par une paroi, heure par heure : DataFrame aux colonnes POSTES,
    en W, positif quand la chaleur entre dans le logement (voir l'en-tête du module). horaire : le résultat de
    moteur.besoins.calculer_besoins pour ce groupe et cette météo (jeu « th_bc » ou « th_d »)."""
    if len(horaire) != len(meteo):
        raise ValueError(f"Bilan du groupe : {len(meteo)} heures de météo, {len(horaire)} heures de calcul")
    te = meteo["te"].to_numpy(float)
    ti = horaire["theta_i_moy"].to_numpy(float)
    _, vers_la_masse = _modele(groupe, jeu, meteo, horaire)

    def colonne(nom):
        return horaire[nom].to_numpy(float)

    return pd.DataFrame({"ventilation": colonne("hg_ventilation") * (colonne("theta_souffle") - ti),
                         "infiltrations": colonne("hg_infiltrations") * (te - ti),
                         "ouvertures": colonne("hg_ouvertures") * (te - ti),
                         "ponts_thermiques": -transmission_ponts(groupe) * vers_la_masse,
                         "apports_internes": colonne("phi_apports"),
                         "chauffage": colonne("q_ch_wh"),
                         "refroidissement": -colonne("q_fr_wh")}, index=meteo.index)


def masse_gardee(horaire):
    """Chaleur gardée par les masses du groupe, heure par heure (W) : stockage de la masse quotidienne, moins ce que
    lui cèdent les masses séquentielle et annuelle. C'est exactement la somme de ce qui entre par les parois, les
    baies et les postes (voir l'en-tête du module)."""
    return (horaire["stockage"] - horaire["flux_inerties_longues"]).to_numpy(float)


# ============================================================
# SUR UNE PÉRIODE
# ============================================================
def resumer(heures, surface_m2, masque=None):
    """Bilan d'un composant sur une période (masque : heures retenues, toutes par défaut) :

      rayonnement_kwh_m2   rayonnement reçu par m² de paroi (kWh/m²)
      solaire_kwh          flux solaire transmis au groupe (kWh)
      froid_kwh            rayonnement froid vers le ciel (kWh, négatif : une perte)
      solaire_max_wh       flux solaire transmis à l'heure la plus forte (Wh)
      deperdition_kwh      conduction cumulée (kWh ; négatif : la paroi a fait entrer de la chaleur)
      rprot_soleil         fermeture moyenne de la protection pendant les heures où la paroi reçoit du soleil
      rouv_moyen           part ouverte moyenne des baies sur la période
      heures               nombre d'heures de la période
    """
    retenues = heures if masque is None else heures[np.asarray(masque, dtype=bool)]
    soleil = retenues["isr"] > 0
    return {"rayonnement_kwh_m2": retenues["isr"].sum() / WH_PAR_KWH if surface_m2 > 0 else 0.0,
            "solaire_kwh": retenues["solaire"].sum() / WH_PAR_KWH,
            "solaire_max_wh": float(retenues["solaire"].max()) if len(retenues) else 0.0,
            "froid_kwh": retenues["froid"].sum() / WH_PAR_KWH,
            "deperdition_kwh": retenues["deperdition"].sum() / WH_PAR_KWH,
            "rprot_soleil": float(retenues.loc[soleil, "rprot"].mean()) if soleil.any() else 0.0,
            "rouv_moyen": float(retenues["rouv"].mean()) if len(retenues) else 0.0,
            "heures": int(len(retenues))}
