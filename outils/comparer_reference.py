r"""
============================================================
 COMPARER À UNE ÉTUDE — notre Bbio face à celui d'un RSET
============================================================
 Lit un RSET (outils/lire_rset.py), refait le calcul du Bbio
 avec le moteur de l'outil, et met les deux côte à côte :

   enveloppe   déperditions (W/K) et surfaces de chaque zone :
               contrôle de la LECTURE, avant tout calcul ;
   annuel      Bch, Bfr, Becl, Bbio et Bbio max par groupe, par
               zone et par bâtiment ;
   mensuel     les mêmes besoins, mois par mois, par groupe.

 Variantes (variantes_besoins) : le même calcul en retirant un
 module à la fois, pour mesurer ce que chacun apporte :

   sans infiltrations         enveloppe étanche (lire le chauffage) ;
   sans ouverture des baies   baies jamais ouvertes ;
   sans protections mobiles   baies toujours nues ;
   sans aucun des trois       outil de la 0.8.10.

 Usage (PowerShell) :
     python -m outils.comparer_reference "_sources\mon_etude.xml"
     python -m outils.comparer_reference "_sources\mon_etude.xml" --variantes

 Les RSET restent hors du dépôt (dossiers commençant par « _ »).
============================================================
"""

import argparse
import copy
import sys
from dataclasses import dataclass

import pandas as pd

from moteur.bbio import calculer_bbio
from moteur.besoins import JEU, bilan_besoins, calculer_besoins
from moteur.calendrier import construire_calendrier
from moteur.enveloppe import transmission_baies, transmission_parois, transmission_ponts
from moteur.hypotheses import hyp
from moteur.meteo import charger_meteo
from moteur.structures import INCLINAISON_PAR_TYPE
from outils.lire_rset import lire_rset

# ============================================================
# RÉGLAGES
# ============================================================
GRANDEURS = ["b_ch", "b_fr", "b_ecl", "bbio", "bbio_max"]
CLES = {"groupe": ["batiment", "zone", "groupe"], "zone": ["batiment", "zone"], "batiment": ["batiment"]}
# Variantes : (nom, infiltrations, protections mobiles, ouverture des baies)
VARIANTES = (("outil", True, True, True),
             ("sans infiltrations", False, True, True),
             ("sans ouverture des baies", True, True, False),
             ("sans protections mobiles", True, False, True),
             ("sans aucun des trois", False, False, False))
TOLERANCE_VERTICALE_DEG = 1.0       # une paroi à ±1° de l'inclinaison de son type est comptée dans ce type


@dataclass
class Comparaison:
    """Projet lu, résultats de l'outil, résultats de l'étude et tableaux de comparaison."""
    projet: object
    reference: object           # outils.lire_rset.Reference
    resultat: object            # moteur.bbio.ResultatBbio
    enveloppe: pd.DataFrame     # une ligne par zone et par grandeur : outil, etude, ecart_pct
    annuel: pd.DataFrame        # une ligne par niveau et objet : <grandeur>_outil, <grandeur>_etude
    mensuel: pd.DataFrame       # une ligne par groupe et par mois : b_ch, b_fr, b_ecl, bbio (outil et étude)


# ============================================================
# 1. CONTRÔLE DE LA LECTURE : ENVELOPPE
# ============================================================
def enveloppe_zone(zone):
    """Déperditions (W/K) et surfaces (m², m) d'une zone, calculées par l'outil à partir du projet lu.

    h_ventilation : 0,34 × débit × (1 − efficacité de l'échangeur du Bbio), fiche 6.1, éq. 382.
    h_ponts : avec le coefficient b des espaces tampons (l'indicateur des études ne l'applique pas).
    h_infiltrations : nul ici ; comparer() y met la moyenne de janvier et février du calcul horaire.
    """
    def surface(type_paroi):
        return sum(p.surface_m2 for g in zone.groupes for p in g.parois if p.type == type_paroi
                   and abs(p.inclinaison_deg - INCLINAISON_PAR_TYPE[type_paroi]) <= TOLERANCE_VERTICALE_DEG)

    recuperation = 1.0 - hyp("ventilation_bbio_efficacite")
    return {"h_baies": sum(transmission_baies(g) for g in zone.groupes),
            "h_parois": sum(transmission_parois(g) for g in zone.groupes),
            "h_ponts": sum(transmission_ponts(g) for g in zone.groupes),
            "h_ventilation": sum(hyp("chaleur_volumique_air") * g.debit_ventilation_m3h for g in zone.groupes)
            * recuperation,
            "h_infiltrations": 0.0,
            "a_parois_verticales": surface("mur"), "a_toitures": surface("toiture"),
            "a_planchers_bas": surface("plancher_bas"),
            "a_baies": sum(g.surface_baies_m2 for g in zone.groupes),
            "l_ponts": sum(pt.longueur_m for g in zone.groupes for pt in g.ponts_thermiques)}


def comparer_enveloppe(projet, reference):
    lignes = []
    for batiment in projet.batiments:
        for zone in batiment.zones:
            etude = reference.zones[(reference.zones["batiment"] == batiment.nom)
                                    & (reference.zones["zone"] == zone.nom)]
            for grandeur, valeur in enveloppe_zone(zone).items():
                ref = float(etude[grandeur].iloc[0]) if len(etude) and pd.notna(etude[grandeur].iloc[0]) else None
                ecart = (valeur / ref - 1.0) * 100.0 if ref else None
                lignes.append({"batiment": batiment.nom, "zone": zone.nom, "grandeur": grandeur,
                               "outil": valeur, "etude": ref, "ecart_pct": ecart})
    return pd.DataFrame(lignes)


# ============================================================
# 2. COMPARAISON DES BESOINS ET DU BBIO
# ============================================================
def comparer_annuel(resultat, reference):
    """Besoins annuels, Bbio et Bbio max de l'outil et de l'étude, aux trois niveaux."""
    blocs = []
    for niveau, cles in CLES.items():
        outil = getattr(resultat, niveau + "s")[cles + ["sref_m2"] + GRANDEURS]
        etude = getattr(reference, niveau + "s")
        if etude.empty:
            continue
        fusion = outil.merge(etude[cles + GRANDEURS], on=cles, how="left", suffixes=("_outil", "_etude"))
        fusion.insert(0, "niveau", niveau)
        blocs.append(fusion)
    return pd.concat(blocs, ignore_index=True) if blocs else pd.DataFrame()


def comparer_mensuel(resultat, reference):
    """Besoins mensuels par groupe : outil et étude."""
    grandeurs = ["b_ch", "b_fr", "b_ecl", "bbio"]
    cles = CLES["groupe"] + ["mois"]
    if reference.mensuel.empty:
        return pd.DataFrame()
    etude = reference.mensuel[reference.mensuel["niveau"] == "groupe"]
    return resultat.mensuel[cles + grandeurs].merge(etude[cles + grandeurs], on=cles, how="left",
                                                    suffixes=("_outil", "_etude"))


def comparer(chemin):
    """Lit le RSET « chemin », calcule le Bbio avec l'outil et compare aux résultats de l'étude."""
    projet, reference = lire_rset(chemin)
    resultat = calculer_bbio(projet)
    enveloppe = comparer_enveloppe(projet, reference)
    # Infiltrations : moyenne de janvier et février du coefficient d'échange, comme l'indicateur des études
    # (fiche 13.1, éq. 2407) ; elle vient du calcul horaire, pas de la seule description
    mois = construire_calendrier()["mois"].to_numpy()
    for (batiment, zone, _), heures in resultat.horaire.items():
        ligne = ((enveloppe["batiment"] == batiment) & (enveloppe["zone"] == zone)
                 & (enveloppe["grandeur"] == "h_infiltrations"))
        enveloppe.loc[ligne, "outil"] += float(heures["hg_infiltrations"].to_numpy()[mois <= 2].mean())
    avec_etude = enveloppe["etude"].notna() & (enveloppe["etude"] != 0)
    enveloppe.loc[avec_etude, "ecart_pct"] = (enveloppe["outil"] / enveloppe["etude"] - 1.0)[avec_etude] * 100.0
    return Comparaison(projet=projet, reference=reference, resultat=resultat, enveloppe=enveloppe,
                       annuel=comparer_annuel(resultat, reference),
                       mensuel=comparer_mensuel(resultat, reference))


# ============================================================
# 3. VARIANTES DES BESOINS
# ============================================================
def _groupe_variante(groupe, infiltrations, protections, ouvertures):
    """Copie du groupe pour une variante : sans infiltrations, sans protections mobiles ou sans ouverture."""
    variante = copy.deepcopy(groupe)
    if not infiltrations:
        variante.permeabilite_q4pa = None
    for baie in variante.baies:
        if not protections:
            baie.protection = None
        if not ouvertures:
            baie.ouvrable = False
    return variante


def variantes_besoins(projet, reference):
    """Besoins des groupes du projet pour chaque variante de VARIANTES (kWh/m²), à côté de ceux de l'étude.

    Sortie : une ligne par groupe et par variante (batiment, zone, groupe, variante, b_ch, b_fr, b_ch_etude,
    b_fr_etude).
    """
    meteo = charger_meteo(projet.zone_climatique, JEU, projet.altitude_m)
    lignes = []
    for batiment in projet.batiments:
        for zone in batiment.zones:
            for groupe in zone.groupes:
                cle = {"batiment": batiment.nom, "zone": zone.nom, "groupe": groupe.nom}
                etude = reference.groupes[(reference.groupes[list(cle)] == pd.Series(cle)).all(axis=1)]
                for nom, infiltrations, protections, ouvertures in VARIANTES:
                    variante = _groupe_variante(groupe, infiltrations, protections, ouvertures)
                    heures = calculer_besoins(variante, meteo, hauteur_zone_m=zone.hauteur_m,
                                              hauteur_moyenne_m=zone.hauteur_moyenne_m)
                    _, annuel = bilan_besoins(heures, groupe.surface_m2)
                    lignes.append(dict(cle, variante=nom, b_ch=annuel["b_ch"], b_fr=annuel["b_fr"],
                                       b_ch_etude=float(etude["b_ch"].iloc[0]) if len(etude) else None,
                                       b_fr_etude=float(etude["b_fr"].iloc[0]) if len(etude) else None))
    return pd.DataFrame(lignes)


# ============================================================
# 4. LIGNE DE COMMANDE
# ============================================================
def _afficher(titre, table, decimales=1):
    print(f"\n--- {titre} ---")
    print(table.round(decimales).to_string(index=False) if len(table) else "(rien à comparer)")


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description="Compare le Bbio de l'outil à celui d'une étude (RSET).")
    analyseur.add_argument("rset", help="chemin du RSET (XML) de l'étude")
    analyseur.add_argument("--variantes", action="store_true",
                           help="ajoute les variantes des besoins (cinq calculs par groupe)")
    options = analyseur.parse_args(arguments)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")        # console Windows : accents et symboles
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)

    c = comparer(options.rset)
    infos = c.reference.infos
    print(f"Étude : {c.projet.nom} — zone {infos['zone_climatique']}, altitude {infos['altitude_m']:.0f} m — "
          f"{infos['fichier_logiciel']}, moteur {infos['version_moteur']}")
    print("Non repris par l'outil :")
    for cle, nombre in infos["non_repris"].items():
        print(f"  - {cle} : {nombre}")
    _afficher("Enveloppe par zone (W/K, m², m) : contrôle de la lecture", c.enveloppe)
    _afficher("Besoins annuels (kWh/m²), Bbio et Bbio max (points)", c.annuel)
    if len(c.mensuel):
        mois = c.mensuel.drop(columns=["batiment", "zone"])
        _afficher("Besoins mensuels par groupe (kWh/m²) et Bbio (points)", mois)
    if options.variantes:
        _afficher("Variantes (kWh/m²) : l'outil privé d'un module à la fois",
                  variantes_besoins(c.projet, c.reference))


if __name__ == "__main__":
    main()
