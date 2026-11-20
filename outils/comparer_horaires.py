r"""
============================================================
 COMPARER HEURE PAR HEURE — l'outil face à un moteur Th-BCE
============================================================
 Pour une étude dont on a à la fois le RSET et les sorties
 horaires du moteur réglementaire (outils/lire_horaires.py),
 refait le calcul avec le moteur de l'outil et met les deux
 séries côte à côte, grandeur par grandeur (table GRANDEURS) :

   saison et consignes      L2 : autorisations de chauffage et
                            de refroidissement, consignes ;
   renouvellement d'air     L5 : Hgei, air entrant ;
   soleil et apports        L4 : Fs1, Fs2 + Ftvc, Fs3, Φsh,
                            Φi, Φs, Φm, apports internes ;
   baies                    L3 : protections mobiles et
                            ouverture (moyenne des baies) ;
   températures, besoins    résultat : θop, θair, θm, besoins
                            de chaud, de froid, d'éclairage ;
   confort d'été (Th-D)     L6 : seuil de confort, degrés-heures.

 Pour chaque grandeur : valeur annuelle (somme ou moyenne)
 des deux calculs, écart moyen et maximal heure par heure,
 première heure où l'écart dépasse la tolérance, et la même
 chose mois par mois. Aucun coefficient de l'outil n'est
 ajusté : l'outil ne fait que constater.

 Sorties (dossier _resultats/horaires/, hors dépôt ; « ; »,
 virgule décimale) :
   <étude>_synthese.csv     une ligne par groupe, mode et grandeur ;
   <étude>_mensuel.csv      la même chose mois par mois ;
   <étude>_<mode>_groupe<n>.csv   les deux séries, heure par heure.

 Usage (PowerShell) :
     python -m outils.comparer_horaires paris
     python -m outils.comparer_horaires sete --mode th_b
     python -m outils.comparer_horaires tous

 Les RSET et les sorties horaires restent hors du dépôt.
============================================================
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from moteur.bbio import calculer_bbio
from moteur.besoins import JEUX_DES_MODES
from moteur.calendrier import construire_calendrier
from moteur.dh import calculer_dh
from moteur.meteo import charger_meteo
from outils.lire_horaires import (DOSSIER_HORAIRES, RACINE, fichiers_groupes, lire_colonnes, lire_entete,
                                  lire_resultats_th_dc, noms_baies)
from outils.lire_rset import lire_rset

# ============================================================
# RÉGLAGES
# ============================================================
# Études : dossier des sorties horaires (dans DOSSIER_HORAIRES) et RSET du même calcul (chemin depuis la racine
# du dépôt). L'appariement a été vérifié sur les besoins et les DH des deux fichiers (docs/audit.md, 0.9.9).
ETUDES = {
    "paris": ("Paris_re2020_scénario_final", "_sources/paris_scenario2_resultats_groupes_occ.xml"),
    "sete": ("Sete_re2020_scénario_final", "_sources/sete_scenario2_resultats_groupes_occ.xml"),
    "nice": ("Nice_re2020_scénario_final",
             "../_RSEE/RSET/CW2020_RE2020_RSET_COV-NICE_BRANCOLAR-Bâtiment A_2026-10-12 - sans clim.xml"),
}
# Mode de l'outil → préfixe des fichiers du moteur (Th_B_…, Th_DC_…)
MODES = {"th_b": "B", "th_d": "DC"}
DOSSIER_SORTIES = RACINE / "_resultats" / "horaires"
DECALAGE_MAX_H = 3          # recherche du décalage horaire entre les deux températures extérieures (± 3 h)


@dataclass(frozen=True)
class Grandeur:
    """Une grandeur comparée.

    nom      nom de la grandeur dans les tables de sortie
    outil    colonne du résultat horaire de l'outil (moteur.besoins.calculer_besoins), ou « te » pour la météo
    moteur   colonnes du moteur à additionner ; « baies:VAR » = moyenne simple de VAR sur les baies du groupe
    somme    True : énergie ou degrés-heures, lus en somme (Wh → kWh) ; False : lus en moyenne
    tolerance    écart horaire au-delà duquel deux heures diffèrent (unité de la grandeur)
    lot      lot du plan de diagnostic (docs/passation.md)
    modes    modes où la grandeur existe
    """
    nom: str
    outil: str
    moteur: tuple
    somme: bool
    tolerance: float
    lot: str
    modes: tuple = ("th_b", "th_d")


GRANDEURS = (
    # L1 : alignement des deux calculs
    Grandeur("temperature_exterieure", "te", ("O_Temp_ext",), False, 0.05, "L1"),
    Grandeur("occupation", "occupe", ("O_Ind_occ",), False, 0.01, "L1"),
    # L2 : saison propre du groupe, consignes
    Grandeur("autorisation_chauffage", "aut_ch", ("O_Auth_ch",), False, 0.01, "L2"),
    Grandeur("autorisation_refroidissement", "aut_fr", ("O_Auth_fr",), False, 0.01, "L2"),
    Grandeur("consigne_chauffage", "consigne_ch", ("O_Temp_Cons_Init_Ch",), False, 0.05, "L2"),
    Grandeur("consigne_refroidissement", "consigne_fr", ("O_Temp_Cons_Init_Fr",), False, 0.05, "L2"),
    # L5 : renouvellement d'air (ventilation, infiltrations, baies ouvertes)
    Grandeur("hg_ei", "hg_ei", ("O_Hgei",), False, 1.0, "L5"),
    Grandeur("temperature_air_entrant", "theta_eieq", ("O_Temp_eieq",), False, 0.1, "L5"),
    Grandeur("hg_es", "hg_es", ("O_Hges",), False, 1.0, "L5"),
    # L4 : soleil et apports
    Grandeur("fs1", "fs1", ("O_Fs1",), True, 10.0, "L4"),
    Grandeur("fs2_ftvc", "phi_sl", ("O_Fs2", "O_Ftvc"), True, 10.0, "L4"),
    Grandeur("fs3", "fs3", ("O_Fs3",), True, 10.0, "L4"),
    Grandeur("phi_sh", "phi_sh", ("O_Phi_sh",), True, 10.0, "L4"),
    Grandeur("apports_occupants", "phi_occupants", ("O_Phiint_rad_Occ", "O_Phiint_conv_Occ"), True, 10.0, "L4"),
    Grandeur("apports_usages", "phi_usages", ("O_Phiint_rad_Proc", "O_Phiint_conv_Proc"), True, 10.0, "L4"),
    Grandeur("phi_i", "phi_i", ("O_Phi_i",), True, 10.0, "L4"),
    Grandeur("phi_s", "phi_s", ("O_Phi_s",), True, 10.0, "L4"),
    Grandeur("phi_m", "phi_m", ("O_Phi_m",), True, 10.0, "L4"),
    Grandeur("eclairement_naturel", "einat", ("O_Einat",), False, 10.0, "L4"),
    # L3 : baies, en moyenne simple ; Rouv de l'éq. 240, avant Rouvmax et protections (O_Rouv du moteur)
    Grandeur("protections_fermees", "rprot_moyen", ("baies:O_Rprot1_b",), False, 0.05, "L3"),
    Grandeur("ouverture_baies", "rouv_brut_moyen", ("baies:O_Rouv",), False, 0.05, "L3"),
    # Résultat : températures et besoins
    Grandeur("temperature_operative", "theta_op_moy", ("O_Temp_op_moy",), False, 0.1, "résultat"),
    Grandeur("temperature_air", "theta_i_moy", ("O_Temp_air_moy",), False, 0.1, "résultat"),
    Grandeur("temperature_masse", "theta_mq_moy", ("O_Temp_m_moy",), False, 0.1, "résultat"),
    Grandeur("besoin_chauffage", "q_ch_wh", ("O_B_Ch_Horaire",), True, 10.0, "résultat", ("th_b",)),
    Grandeur("besoin_refroidissement", "q_fr_wh", ("O_B_Fr_Horaire",), True, 10.0, "résultat", ("th_b",)),
    Grandeur("besoin_eclairage", "cecl_wh", ("O_W_Ecl_Horaire",), True, 10.0, "résultat", ("th_b",)),
    # L6 : confort d'été
    Grandeur("theta_rm_ext", "theta_rm_ext", ("O_Theta_rm_J",), False, 0.05, "L6", ("th_d",)),
    Grandeur("seuil_confort", "seuil_confort", ("Theta_op_conf_ch",), False, 0.05, "L6", ("th_d",)),
    Grandeur("seuil_confort_corrige", "seuil_confort_corrige", ("Theta_op_conf_ch_corr",), False, 0.05, "L6",
             ("th_d",)),
    Grandeur("temperature_operative_fin", "theta_op", ("O_Temp_op",), False, 0.1, "L6", ("th_d",)),
    Grandeur("degres_heures", "dh_horaire", ("NbDegresHeures",), True, 0.05, "L6", ("th_d",)),
    Grandeur("energie_brasseurs", "energie_brasseurs_wh", ("O_Q_Cef_BA",), True, 1.0, "L6", ("th_d",)),
)


@dataclass
class ComparaisonHoraire:
    """Résultats d'une étude : tables de synthèse et mensuelle, séries horaires par (mode, groupe)."""
    etude: str
    synthese: pd.DataFrame
    mensuel: pd.DataFrame
    series: dict = field(default_factory=dict)      # {(mode, numéro de groupe): DataFrame heure par heure}
    controles: list = field(default_factory=list)   # textes : appariement des groupes, décalage horaire


# ============================================================
# 1. SÉRIES DU MOTEUR
# ============================================================
def series_moteur(chemin, grandeurs):
    """Séries horaires du moteur pour les grandeurs demandées : {nom: tableau numpy}, et noms absents."""
    entete = lire_entete(chemin)
    besoin, sources = [], {}
    for g in grandeurs:
        colonnes = []
        for source in g.moteur:
            colonnes += noms_baies(entete, source[6:]) if source.startswith("baies:") else [source]
        sources[g.nom] = colonnes
        besoin += colonnes
    presents = set(entete["nom"])
    absents = sorted({c for c in besoin if c not in presents})
    table = lire_colonnes(chemin, [c for c in besoin if c in presents])
    series = {}
    for g in grandeurs:
        colonnes = sources[g.nom]
        if not colonnes or any(c not in presents for c in colonnes):
            continue
        valeurs = table[colonnes].to_numpy(float)
        baies = g.moteur[0].startswith("baies:")
        series[g.nom] = valeurs.mean(axis=1) if baies else valeurs.sum(axis=1)
    return series, absents


# ============================================================
# 2. ÉCARTS
# ============================================================
def decalage_horaire(a, b, maximum=DECALAGE_MAX_H):
    """Retard (h) de la série b sur la série a : d tel que b[t + d] ≈ a[t] ; 0 si les deux sont alignées."""
    n, meilleur, ecart_min = min(len(a), len(b)), 0, np.inf
    for d in range(-maximum, maximum + 1):
        x, y = (a[:n - d], b[d:n]) if d >= 0 else (a[-d:n], b[:n + d])
        ecart = np.nanmean(np.abs(x - y))
        if ecart < ecart_min:
            meilleur, ecart_min = d, ecart
    return meilleur


def ecarts(outil, moteur, g, mois=None):
    """Valeurs et écarts de deux séries horaires : une ligne (dictionnaire) par mois ou pour l'année."""
    # Sommes : W ou Wh heure par heure → kWh sur la période ; les degrés-heures restent en °C.h
    facteur = 1e-3 if g.somme and g.nom != "degres_heures" else 1.0
    d = outil - moteur
    au_dela = np.flatnonzero(np.abs(d) > g.tolerance)
    lire = np.nansum if g.somme else np.nanmean
    ligne = {"outil": lire(outil) * facteur, "moteur": lire(moteur) * facteur,
             "ecart_moyen": float(np.nanmean(d)), "ecart_absolu_moyen": float(np.nanmean(np.abs(d))),
             "ecart_max": float(d[np.nanargmax(np.abs(d))]) if len(d) else np.nan,
             "heure_ecart_max": int(np.nanargmax(np.abs(d))) if len(d) else None,
             "heures_au_dela": int(au_dela.size),
             "premiere_heure_au_dela": int(au_dela[0]) if au_dela.size else None}
    ligne["ecart_pct"] = ((ligne["outil"] / ligne["moteur"] - 1.0) * 100.0
                          if ligne["moteur"] and abs(ligne["moteur"]) > 1e-9 else np.nan)
    if mois is not None:
        ligne["premiere_heure_au_dela"] = None      # sans objet mois par mois (heures de l'année)
    return ligne


def _unite(g):
    if g.somme:
        return "°C.h" if g.nom == "degres_heures" else "kWh"
    return ""


# ============================================================
# 3. COMPARAISON D'UNE ÉTUDE
# ============================================================
def resultats_outil(projet, mode):
    """Résultats horaires de l'outil, dans l'ordre (bâtiment, zone, groupe) du projet."""
    horaire = (calculer_bbio(projet) if mode == "th_b" else calculer_dh(projet)).horaire
    return list(horaire.items())


def comparer_etude(etude, modes=("th_b", "th_d")):
    """Compare l'outil au moteur, heure par heure, sur l'étude « etude » (clé de ETUDES)."""
    dossier, rset = ETUDES[etude]
    dossier = DOSSIER_HORAIRES / dossier
    projet, reference = lire_rset((RACINE / rset).resolve())
    calendrier = construire_calendrier()
    mois = calendrier["mois"].to_numpy()
    lignes, lignes_mois, series, controles = [], [], {}, []

    for mode in modes:
        fichiers = fichiers_groupes(dossier, MODES[mode])
        groupes = resultats_outil(projet, mode)
        if len(fichiers) != len(groupes):
            raise ValueError(f"{etude} ({mode}) : {len(fichiers)} groupes chez le moteur, {len(groupes)} dans l'outil")
        meteo = charger_meteo(projet.zone_climatique, JEUX_DES_MODES[mode], projet.altitude_m)
        grandeurs = [g for g in GRANDEURS if mode in g.modes]
        dh_moteur = lire_resultats_th_dc(dossier) if mode == "th_d" else None

        for rang, ((_, _, n_groupe, chemin), (cle, heures)) in enumerate(zip(fichiers, groupes)):
            moteur, absents = series_moteur(chemin, grandeurs)
            heures = heures.assign(te=meteo["te"].to_numpy())
            # Contrôle de l'appariement : besoin annuel du moteur face au RSET (Th-B), DH face au fichier de
            # résultats du moteur (Th-D)
            groupe = next(g for b in projet.batiments for z in b.zones for g in z.groupes
                          if (b.nom, z.nom, g.nom) == cle)
            if mode == "th_b":
                ref = reference.groupes[(reference.groupes[["batiment", "zone", "groupe"]]
                                         == pd.Series(dict(zip(["batiment", "zone", "groupe"], cle)))).all(axis=1)]
                b_ch = moteur["besoin_chauffage"].sum() / 1000.0 / groupe.surface_m2
                controles.append(f"{mode} groupe {n_groupe} ↔ {cle[1]} / {cle[2]} : Bch du moteur {b_ch:.1f}, "
                                 f"du RSET {float(ref['b_ch'].iloc[0]) if len(ref) else float('nan'):.1f} kWh/m²")
            else:
                dh = moteur["degres_heures"].sum()
                controles.append(f"{mode} groupe {n_groupe} ↔ {cle[1]} / {cle[2]} : DH horaire du moteur "
                                 f"{dh:.1f}, résultat du moteur {dh_moteur[rang][0]:.1f} °C.h")
            if "temperature_exterieure" in moteur:
                d = decalage_horaire(heures["te"].to_numpy(), moteur["temperature_exterieure"])
                controles.append(f"{mode} groupe {n_groupe} : décalage de la température extérieure {d} h")
            if absents:
                controles.append(f"{mode} groupe {n_groupe} : colonnes absentes du moteur : {', '.join(absents)}")

            # Séries côte à côte et écarts, grandeur par grandeur
            cote = pd.DataFrame({"heure": np.arange(len(heures)), "mois": mois,
                                 "hleg": calendrier["hleg"].to_numpy()})
            base = {"etude": etude, "mode": mode, "groupe_moteur": n_groupe, "zone": cle[1], "groupe": cle[2]}
            for g in grandeurs:
                if g.nom not in moteur or g.outil not in heures:
                    continue
                a, b = heures[g.outil].to_numpy(float), moteur[g.nom]
                cote[f"{g.nom}_outil"], cote[f"{g.nom}_moteur"] = a, b
                commun = dict(base, lot=g.lot, grandeur=g.nom, unite=_unite(g))
                lignes.append(dict(commun, **ecarts(a, b, g)))
                for m in range(1, 13):
                    dans = mois == m
                    lignes_mois.append(dict(commun, mois=m, **ecarts(a[dans], b[dans], g, mois=m)))
            series[(mode, n_groupe)] = cote

    return ComparaisonHoraire(etude=etude, synthese=pd.DataFrame(lignes), mensuel=pd.DataFrame(lignes_mois),
                              series=series, controles=controles)


# ============================================================
# 4. ÉCRITURE ET LIGNE DE COMMANDE
# ============================================================
def ecrire(c, dossier=DOSSIER_SORTIES):
    """Écrit la synthèse, le mensuel et les séries horaires dans « dossier » (« ; », virgule décimale)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    options = dict(sep=";", decimal=",", index=False, encoding="utf-8-sig")
    c.synthese.to_csv(dossier / f"{c.etude}_synthese.csv", **options)
    c.mensuel.to_csv(dossier / f"{c.etude}_mensuel.csv", **options)
    for (mode, n), table in c.series.items():
        table.to_csv(dossier / f"{c.etude}_{mode}_groupe{n}.csv", **options)
    return dossier


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description="Compare l'outil au moteur Th-BCE, heure par heure.")
    analyseur.add_argument("etude", choices=list(ETUDES) + ["tous"], help="étude à comparer")
    analyseur.add_argument("--mode", choices=list(MODES) + ["tous"], default="tous", help="mode de calcul")
    options = analyseur.parse_args(arguments)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")        # console Windows : accents et symboles
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 200)
    modes = tuple(MODES) if options.mode == "tous" else (options.mode,)
    for etude in (ETUDES if options.etude == "tous" else [options.etude]):
        c = comparer_etude(etude, modes)
        print(f"\n=== {etude} ===")
        for texte in c.controles:
            print("  " + texte)
        colonnes = ["mode", "groupe_moteur", "lot", "grandeur", "unite", "outil", "moteur", "ecart_pct",
                    "ecart_absolu_moyen", "heures_au_dela", "premiere_heure_au_dela"]
        print(c.synthese[colonnes].round(2).to_string(index=False))
        print(f"Tables écrites dans {ecrire(c)}")


if __name__ == "__main__":
    main()
