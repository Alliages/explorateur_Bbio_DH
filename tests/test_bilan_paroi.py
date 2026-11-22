"""
Tests du bilan par paroi (moteur/bilan_paroi.py, 0.9.20) : chaque baie et chaque paroi opaque, heure par heure,
et leurs sommes face aux flux du groupe ; postes du bilan en coupe et projet sans une paroi (0.9.24).
"""

from dataclasses import replace

import numpy as np
import pytest

from interface.saisie import boite_de_depart, construire_projet
from moteur.besoins import JEU, PREFIXE_RPROT_BAIE, calculer_besoins
from moteur.bilan_paroi import (COLONNES, POSTES, bilan_parois, entrant, masse_gardee, postes_du_groupe,
                                rayonnement_perdu_par_les_baies, resumer)
from moteur.dh import debut_semaine_la_plus_chaude, dh_groupe
from moteur.enveloppe import u_paroi
from moteur.meteo import charger_meteo


def _calcul(boite, mode):
    """Groupe de la boîte, météo et heures du calcul (Th-B : climat moyen ; Th-D : année caniculaire)."""
    projet = construire_projet(replace(boite, permeabilite_q4pa=0.0))     # sans infiltrations : plus rapide
    zone = projet.batiments[0].zones[0]
    groupe = zone.groupes[0]
    jeu = JEU if mode == "th_b" else "th_d"
    meteo = charger_meteo(boite.zone_climatique, jeu, boite.altitude_m)
    return groupe, meteo, jeu, calculer_besoins(groupe, meteo, mode=mode)


@pytest.fixture(scope="module")
def ete():
    """Logement de 70 m² avec un balcon au sud, volets motorisés, année caniculaire."""
    return _calcul(replace(boite_de_depart(), debord_m=1.0), "th_d")


def test_sommes_egales_aux_flux_du_groupe(ete):
    groupe, meteo, jeu, heures = ete
    bilan = bilan_parois(groupe, meteo, jeu, heures)
    assert set(bilan) == {c.nom for c in groupe.baies + groupe.parois}
    assert all(tuple(b.columns) == COLONNES and len(b) == len(meteo) for b in bilan.values())
    # Baies : Fs1 + Fs3 + φsl (= Fs2 + Ftvc) ; parois opaques : φsh ; à 0,1 % près, et heure par heure
    baies = sum(bilan[b.nom]["solaire"] + bilan[b.nom]["froid"] for b in groupe.baies)
    parois = sum(bilan[p.nom]["solaire"] + bilan[p.nom]["froid"] for p in groupe.parois)
    attendu_baies = heures["fs1"] + heures["fs3"] + heures["phi_sl"]
    assert baies.sum() == pytest.approx(attendu_baies.sum(), rel=1e-3)
    assert np.allclose(baies, attendu_baies, atol=1e-6)
    assert parois.sum() == pytest.approx(heures["phi_sh"].sum(), rel=1e-3)
    # Fermeture de chaque baie : sortie du moteur, de moyenne pondérée rprot_moyen
    rprot = [heures[f"{PREFIXE_RPROT_BAIE}{i}"] for i in range(len(groupe.baies))]
    moyenne = sum(r * b.surface_m2 for r, b in zip(rprot, groupe.baies)) / sum(b.surface_m2 for b in groupe.baies)
    assert np.allclose(moyenne, heures["rprot_moyen"])
    # Conduction du modèle : parois opaques et ponts redonnent flux_parois, baies (rayonnement intérieur perdu
    # compris) fs1 + fs3 + flux_baies − ce qui manque aux apports, heure par heure
    opaques = sum(entrant(bilan[p.nom]) for p in groupe.parois)
    ponts = postes_du_groupe(groupe, meteo, heures, jeu)["ponts_thermiques"]
    assert np.allclose(opaques + ponts, heures["flux_parois"], atol=1e-6)
    vitrees = sum(entrant(bilan[b.nom]) for b in groupe.baies)
    attendu = heures["fs1"] + heures["fs3"] + heures["flux_baies"] - rayonnement_perdu_par_les_baies(heures)
    assert np.allclose(vitrees, attendu, atol=1e-6)
    # La toiture perd vers le dehors en moyenne sur l'année ; sa conduction suit U × surface
    toiture = next(p for p in groupe.parois if p.type == "toiture")
    assert bilan[toiture.nom]["deperdition"].sum() > 0 and u_paroi(toiture) > 0


def test_sens_physique(ete):
    groupe, meteo, jeu, heures = ete
    bilan = bilan_parois(groupe, meteo, jeu, heures)
    sud = next(b for b in groupe.baies if "sud" in b.nom)
    nord = next(b for b in groupe.baies if "nord" in b.nom)
    plancher = next(p for p in groupe.parois if p.type == "plancher_bas")
    annee = {nom: resumer(h, 1.0) for nom, h in bilan.items()}
    # La baie sud reçoit plus de soleil que la baie nord, même sous son balcon ; le plancher sur le sol aucun
    assert annee[sud.nom]["rayonnement_kwh_m2"] > annee[nord.nom]["rayonnement_kwh_m2"] > 0
    assert annee[plancher.nom]["rayonnement_kwh_m2"] == 0 and annee[plancher.nom]["solaire_kwh"] == 0
    # Le ciel refroidit toujours ; les protections sont des parts ; transmis ≤ reçu × surface
    for nom, r in annee.items():
        assert r["froid_kwh"] <= 0 and 0 <= r["rprot_soleil"] <= 1 and 0 <= r["rouv_moyen"] <= 1
    assert annee[sud.nom]["solaire_kwh"] < annee[sud.nom]["rayonnement_kwh_m2"] * sud.surface_m2
    # Semaine la plus chaude : 168 heures, protections plus baissées qu'en moyenne sur l'été
    debut = debut_semaine_la_plus_chaude(dh_groupe(heures)["dh_horaire"])
    masque = np.zeros(len(heures), dtype=bool)
    masque[debut:debut + 168] = True
    semaine = resumer(bilan[sud.nom], sud.surface_m2, masque)
    assert semaine["heures"] == 168 and semaine["rprot_soleil"] > annee[sud.nom]["rprot_soleil"]


def test_sans_protection_ni_heures_compatibles():
    groupe, meteo, jeu, heures = _calcul(replace(boite_de_depart(), protection="aucune"), "th_b")
    assert not any(c.startswith(PREFIXE_RPROT_BAIE) for c in heures.columns)
    bilan = bilan_parois(groupe, meteo, jeu, heures)
    baies = sum(bilan[b.nom]["solaire"] + bilan[b.nom]["froid"] for b in groupe.baies)
    assert baies.sum() == pytest.approx((heures["fs1"] + heures["fs3"] + heures["phi_sl"]).sum(), rel=1e-3)
    assert all((bilan[b.nom]["rprot"] == 0).all() for b in groupe.baies)
    with pytest.raises(ValueError, match="heures"):
        bilan_parois(groupe, meteo.iloc[:100], jeu, heures)


# ============================================================
# BILAN EN COUPE (0.9.24) : les autres postes du groupe et la fermeture du bilan
# ============================================================
def test_postes_du_groupe_et_fermeture_du_bilan(ete):
    groupe, meteo, jeu, heures = ete
    postes = postes_du_groupe(groupe, meteo, heures, jeu)
    assert tuple(postes.columns) == POSTES and len(postes) == len(meteo)
    # Air : ventilation, infiltrations et baies ouvertes redonnent ensemble Hg,ei . (θeieq − θi), heure par heure
    air = postes["ventilation"] + postes["infiltrations"] + postes["ouvertures"]
    attendu = heures["hg_ei"] * (heures["theta_eieq"] - heures["theta_i_moy"])
    assert np.allclose(air, attendu, atol=1e-6)
    # Sens : les apports internes entrent, le froid ne fait que sortir (nul en Th-D), les baies ouvertes refroidissent
    # sur l'été
    assert (postes["apports_internes"] >= 0).all() and (postes["refroidissement"] <= 0).all()
    assert postes["ouvertures"][heures["confort_adaptatif"] > 0].sum() < 0
    # Fermeture exacte, heure par heure : ce qui entre et ne ressort pas est gardé par la masse (hypothèse 103)
    bilan = bilan_parois(groupe, meteo, jeu, heures)
    parois = sum(entrant(h) for h in bilan.values())
    assert np.allclose(parois + postes.sum(axis=1), masse_gardee(heures), atol=1e-6)


def test_projet_sans_une_paroi():
    boite = boite_de_depart()
    groupe = construire_projet(boite).batiments[0].zones[0].groupes[0]
    noms = {p.nom: p for p in groupe.parois}
    sud = next(f for f in boite.facades() if f["cle"] == "principale")
    # Baies retirées : remplacées par le mur de la façade, de surface la façade entière
    sans_baies = construire_projet(boite, sans=("baies_principale",)).batiments[0].zones[0].groupes[0]
    assert len(sans_baies.baies) == len(groupe.baies) - 1
    mur = next(p for p in sans_baies.parois if p.nom.startswith("Mur — Façade principale"))
    assert mur.surface_m2 == pytest.approx(sud["mur_m2"] + sud["baies_m2"])
    # Mur retiré : ses baies restent ; toiture retirée ; clé inconnue refusée
    sans_mur = construire_projet(boite, sans=("principale",)).batiments[0].zones[0].groupes[0]
    assert len(sans_mur.parois) == len(noms) - 1 and len(sans_mur.baies) == len(groupe.baies)
    sans_toit = construire_projet(boite, sans=("toiture",)).batiments[0].zones[0].groupes[0]
    assert not any(p.type == "toiture" for p in sans_toit.parois)
    with pytest.raises(ValueError, match="inconnues"):
        construire_projet(boite, sans=("cave",))
