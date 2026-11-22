"""
============================================================
 CALCUL — de la boîte aux résultats que montrent les briques
============================================================
 Lance sur la boîte saisie l'un des deux calculs du moteur, ou
 les deux :

     boîte → projet → Bbio (climat moyen, mode Th-B)   resultats_bbio()
                    → DH   (année caniculaire, mode Th-D) resultats_dh()

 et n'en garde que ce que l'interface affiche : le moteur rend
 8 760 heures de 40 à 50 colonnes par calcul, trop lourd à garder
 en mémoire pour chaque essai de l'utilisateur.

 Les deux calculs pèsent à peu près autant et ne dépendent pas
 l'un de l'autre : l'interface ne lance que celui qu'on lui
 demande, et les garde en mémoire séparément (passer du DH seul
 au Bbio et au DH ne lance que le Bbio).

 Chaque calcul rend aussi le bilan de chaque paroi de la boîte
 (moteur/bilan_paroi.py), déjà résumé sur ses périodes : l'année
 pour le Bbio ; la période de confort adaptatif et la semaine la
 plus chaude pour le DH (fiche sous le dessin). Sur les mêmes
 périodes, le bilan en coupe (brique « Le bilan en coupe ») : ce
 qui entre et sort par chaque paroi, l'air, les ponts thermiques,
 les apports internes et l'émetteur ; pour le DH, la part de
 chacun dans la chaleur entrée aux heures qui comptent des DH.

 effet_paroi() relance un calcul sans une paroi (bouton de la
 fiche) : DH et Bbio seulement, sans bilan.

 Ce fichier ne dépend pas de Streamlit ; app.py met
 resultats_bbio() et resultats_dh() en cache. Une brique qui a
 besoin d'une autre grandeur horaire l'ajoute à COLONNES_ETE.
============================================================
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.reglages import HEURES_PAR_JOUR, JOURS_PAR_SEMAINE
from interface.saisie import CLE_GROUPE, construire_projet, noms_composants
from moteur.bbio import calculer_bbio
from moteur.besoins import JEU as JEU_BBIO
from moteur.besoins import JEUX_DES_MODES
from moteur.bilan_paroi import POSTES, bilan_parois, entrant, postes_du_groupe, resumer
from moteur.calendrier import construire_calendrier
from moteur.dh import MODE as MODE_DH
from moteur.dh import calculer_dh, debut_semaine_la_plus_chaude
from moteur.meteo import charger_meteo

# ============================================================
# RÉGLAGES
# ============================================================
# Colonnes horaires gardées du calcul Th-D (voir moteur.besoins.calculer_besoins et moteur.dh.calculer_dh)
COLONNES_ETE = ["theta_op", "seuil_confort_corrige", "occupe", "confort_adaptatif", "dh_horaire", "rprot_moyen",
                "rouv_moyen", "ecart_ba"]
ANNEE_AFFICHEE = 2023           # année sans 29 février, pour dater les heures sur les graphiques (heure légale)
CALCULS = ("bbio", "dh")        # les deux calculs, dans l'ordre d'affichage
# Périodes du bilan par paroi, dans l'ordre d'affichage : (calcul, clé, libellé)
PERIODES_PAROIS = (("dh", "semaine", "Semaine la plus chaude"), ("dh", "confort", "Été (confort adaptatif)"),
                   ("bbio", "annee", "Année moyenne (Bbio)"))
# Bilan en coupe : postes « <clé de paroi>.soleil » et « <clé de paroi>.echange » ; RESTE, la chaleur gardée par
# la masse, plus l'écart de lecture des parois (hypothèse 103)
SOLEIL, ECHANGE = "soleil", "echange"
CUMUL, POINTE = "cumul", "pointe"           # bilan en coupe : sur la période (kWh), à l'heure de pointe (Wh)
RESTE = "reste"
WH_PAR_KWH = 1000.0


@dataclass
class Resultats:
    """Ce que les briques reçoivent ; les champs d'un calcul non lancé valent None.

    bbio      ligne du groupe de moteur.bbio.calculer_bbio (b_ch, b_fr, b_ecl, bbio, bbio_max, modulations…)
    mensuel   une ligne par mois conventionnel : mois, b_ch, b_fr, b_ecl, bbio
    dh        ligne du groupe de moteur.dh.calculer_dh (dh, dh_max, heures d'inconfort, avertissement…)
    ete       les 8 760 heures de l'année caniculaire : date (heure légale), te (extérieur, °C) et COLONNES_ETE
    parois_bbio, parois_dh   bilan de chaque paroi de la boîte par période : {(clé de paroi, période): résumé de
              moteur.bilan_paroi.resumer}, périodes de PERIODES_PAROIS ; clés de paroi : saisie.noms_composants
    coupe_bbio, coupe_dh     bilan en coupe par période : {période: {CUMUL: {poste: kWh entrés, négatifs s'ils
              sortent}, POINTE: {poste: Wh entrés à l'heure de pointe}, « heure »: sa date, « te », « theta_i »:
              températures extérieure et intérieure de cette heure}} ; l'heure de pointe est celle où le soleil
              transmis est le plus fort. Postes : « <clé de paroi>.soleil » et « <clé de paroi>.echange »
              (rayonnement froid et conduction), ceux de moteur.bilan_paroi.POSTES, et RESTE (chaleur gardée par
              la masse, exacte : hypothèse 103)
    part_dh   chaleur entrée aux heures qui comptent des DH : {clé de paroi ou poste: kWh}, parties positives,
              heure par heure, de chaque paroi (soleil et échange ensemble) et de chaque poste
    """
    bbio: dict = None
    mensuel: pd.DataFrame = None
    parois_bbio: dict = None
    dh: dict = None
    ete: pd.DataFrame = None
    parois_dh: dict = None
    coupe_bbio: dict = None
    coupe_dh: dict = None
    part_dh: dict = None

    def calculs(self):
        """Les calculs présents, parmi CALCULS."""
        return tuple(nom for nom in CALCULS if getattr(self, nom) is not None)


def dates_legales(calendrier):
    """Date et heure légales du début de chaque pas de temps, pour l'axe des graphiques.

    Heure UTC plus le décalage légal (1 h en hiver, 2 h en été) : la série saute une heure au passage à l'heure
    d'été et en répète une au retour à l'heure d'hiver, comme une horloge.
    """
    debut = pd.Timestamp(year=ANNEE_AFFICHEE, month=1, day=1)
    return debut + pd.to_timedelta(calendrier["h"] + calendrier["ehlo"], unit="h")


def _groupe(projet):
    """Le seul groupe du projet d'une boîte."""
    return projet.batiments[0].zones[0].groupes[0]


def bilan_des_parois(boite, projet, meteo, jeu, horaire, periodes, dates, heures_dh=None):
    """Bilan de chaque paroi de la boîte et bilan en coupe, sur chaque période ; periodes : {clé de période:
    masque des heures retenues, ou None pour toutes} ; dates : date légale de chaque heure. Rend (parois, coupe,
    part_dh), décrits dans Resultats ; part_dh vaut None sans heures_dh (masque des heures qui comptent des DH)."""
    groupe = _groupe(projet)
    surfaces = {composant.nom: composant.surface_m2 for composant in groupe.parois + groupe.baies}
    heures = bilan_parois(groupe, meteo, jeu, horaire)
    noms = noms_composants(boite)
    parois = {(cle, periode): resumer(heures[noms[cle]], surfaces[noms[cle]], masque)
              for cle in noms for periode, masque in periodes.items()}
    # Bilan en coupe : chaque flux heure par heure (W, positif s'il entre), cumulé sur chaque période
    flux = pd.DataFrame({f"{cle}.{SOLEIL}": heures[nom]["solaire"] for cle, nom in noms.items()})
    for cle, nom in noms.items():
        flux[f"{cle}.{ECHANGE}"] = heures[nom]["froid"] - heures[nom]["deperdition"]
    postes = postes_du_groupe(groupe, meteo, horaire, jeu)
    flux = pd.concat([flux, postes], axis=1).reset_index(drop=True)
    soleil = flux[[f"{cle}.{SOLEIL}" for cle in noms]].sum(axis=1)
    te, theta_i = meteo["te"].to_numpy(float), horaire["theta_i_moy"].to_numpy(float)
    coupe = {}
    for periode, masque in periodes.items():
        retenues = flux if masque is None else flux[np.asarray(masque, dtype=bool)]
        # Cumul (kWh) ; ce qui est entré et n'est pas ressorti est gardé par la masse (moteur.bilan_paroi)
        cumul = (retenues.sum() / WH_PAR_KWH).to_dict()
        cumul[RESTE] = sum(cumul.values())
        # Heure de pointe : celle où le soleil transmis au logement est le plus fort (Wh sur l'heure)
        rang = int(soleil.loc[retenues.index].idxmax())
        pointe = flux.loc[rang].to_dict()
        pointe[RESTE] = sum(pointe.values())
        date = pd.Timestamp(dates[rang])
        coupe[periode] = {CUMUL: cumul, POINTE: pointe, "heure": f"{date:%d/%m} à {date.hour} h",
                          "te": float(te[rang]), "theta_i": float(theta_i[rang])}
    part_dh = None
    if heures_dh is not None:
        par_poste = pd.DataFrame({cle: entrant(heures[nom]) for cle, nom in noms.items()})
        par_poste = pd.concat([par_poste, postes[list(POSTES)]], axis=1)[heures_dh]
        part_dh = (par_poste.clip(lower=0.0).sum() / WH_PAR_KWH).to_dict()
    return parois, coupe, part_dh


def resultats_bbio(boite):
    """Champs bbio, mensuel et parois_bbio de Resultats ; lève une ValueError au message clair si la saisie est
    incohérente."""
    projet = construire_projet(boite)
    calendrier = construire_calendrier()
    bbio = calculer_bbio(projet, calendrier=calendrier)
    meteo = charger_meteo(boite.zone_climatique, JEU_BBIO, boite.altitude_m)
    parois, coupe, _ = bilan_des_parois(boite, projet, meteo, JEU_BBIO, bbio.horaire[CLE_GROUPE], {"annee": None},
                                        dates_legales(calendrier))
    return {"bbio": bbio.groupes.iloc[0].to_dict(),
            "mensuel": bbio.mensuel[["mois", "b_ch", "b_fr", "b_ecl", "bbio"]].reset_index(drop=True),
            "parois_bbio": parois, "coupe_bbio": coupe}


def resultats_dh(boite):
    """Champs dh, ete et parois_dh de Resultats ; lève une ValueError au message clair si la saisie est
    incohérente."""
    calendrier = construire_calendrier()
    projet = construire_projet(boite)
    dh = calculer_dh(projet, calendrier=calendrier)
    meteo = charger_meteo(boite.zone_climatique, JEUX_DES_MODES[MODE_DH], boite.altitude_m)
    horaire = dh.horaire[CLE_GROUPE]
    ete = horaire[COLONNES_ETE].reset_index(drop=True)
    ete.insert(0, "te", meteo["te"].to_numpy())
    ete.insert(0, "date", dates_legales(calendrier).to_numpy())
    # Périodes du bilan par paroi : la semaine qui compte le plus de DH, la période de confort adaptatif
    debut = debut_semaine_la_plus_chaude(horaire["dh_horaire"])
    semaine = pd.Series(False, index=range(len(horaire)))
    semaine.iloc[debut:debut + JOURS_PAR_SEMAINE * HEURES_PAR_JOUR] = True
    periodes = {"semaine": semaine.to_numpy(), "confort": horaire["confort_adaptatif"].to_numpy() > 0}
    parois, coupe, part_dh = bilan_des_parois(boite, projet, meteo, JEUX_DES_MODES[MODE_DH], horaire, periodes,
                                              dates_legales(calendrier),
                                              heures_dh=horaire["dh_horaire"].to_numpy() > 0)
    return {"dh": dh.groupes.iloc[0].to_dict(), "ete": ete, "parois_dh": parois, "coupe_dh": coupe,
            "part_dh": part_dh}


def effet_paroi(boite, cle, calculs=CALCULS):
    """DH et Bbio de la boîte sans la paroi « cle » (hypothèse 104 : baies remplacées par du mur, paroi opaque
    retirée comme une paroi adiabatique), pour les calculs demandés : {« dh »: DH (°C.h), « bbio »: Bbio}.
    Un calcul entier par indicateur, sans bilan par paroi."""
    calendrier = construire_calendrier()
    effets = {}
    if "dh" in calculs:
        effets["dh"] = float(calculer_dh(construire_projet(boite, sans=(cle,)), calendrier=calendrier)
                             .groupes.iloc[0]["dh"])
    if "bbio" in calculs:
        effets["bbio"] = float(calculer_bbio(construire_projet(boite, sans=(cle,)), calendrier=calendrier)
                               .groupes.iloc[0]["bbio"])
    return effets


def calculer(boite, calculs=CALCULS):
    """Résultats des calculs demandés (« bbio », « dh » ou les deux), sans mémoire : app.py garde les siens."""
    fonctions = {"bbio": resultats_bbio, "dh": resultats_dh}
    champs = {}
    for nom in calculs:
        champs.update(fonctions[nom](boite))
    return Resultats(**champs)
