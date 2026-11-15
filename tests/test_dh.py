"""Degrés-heures d'inconfort d'été, DH max et calcul Th-D.

Sources : annexe III, fiches 13.5, 4.6 et 8.32 ; annexe à l'article R. 172-4.
"""

import numpy as np
import pytest

from moteur.besoins import Saisons, calculer_besoins
from moteur.dh import (avertissements_confort, calculer_dh, categorie_contraintes, degres_heures, dh_groupe,
                       dh_max)
from moteur.groupe import FLUX_DU_BILAN
from moteur.meteo import charger_meteo
from moteur.structures import Baie, Batiment, Brasseur, Groupe, Paroi, Projet, Zone

SURFACE = 300.0
DEBUT_H3, FIN_H3 = 2952, 7199       # période de confort adaptatif du jeu Th-D de la zone H3 (heures de simulation)


def groupe(nom="G", brasseurs=(), **options):
    """Cinq logements de 60 m², volets manuels et baies ouvrables au sud et au nord."""
    def baie(nom_baie, orientation):
        return Baie(nom_baie, 20.0, orientation, uw=1.4, sw_e=0.5, tl=0.6, protection="volet",
                    gestion_protection="manuelle_motorisee", uw_protege=1.1, sw_protege=0.1, sw2_protege=0.04,
                    ouvrable=True, ratio_ouverture_max=0.6)
    return Groupe(nom, SURFACE, nb_logements=5, debit_ventilation_m3h=300.0, volume_m3=750.0, traversant=True,
                  parois=[Paroi("Mur", "mur", 150.0, u=0.25, orientation_deg=0, alpha=0.6),
                          Paroi("Toit", "toiture", 100.0, u=0.15, alpha=0.6)],
                  baies=[baie("Sud", 0), baie("Nord", 180)], brasseurs=list(brasseurs), **options)


def brasseur():
    return Brasseur("Séjours", nombre=10, surface_desservie_m2=150.0, debit_max_m3h=11000.0, puissance_max_w=40.0,
                    usage="jour_et_nuit", caractere_debit="justifiee")


@pytest.fixture(scope="module")
def meteo():
    return charger_meteo("H3", "th_d", 100.0)


@pytest.fixture(scope="module")
def th_d(meteo):
    """Calcul Th-D du même groupe, sans et avec brasseurs d'air."""
    return {"sans": calculer_besoins(groupe(), meteo, mode="th_d"),
            "avec": calculer_besoins(groupe(brasseurs=[brasseur()]), meteo, mode="th_d")}


# ------------------------------------------------------------------
# Degrés-heures (fiche 13.5, éq. 2548 à 2551)
# ------------------------------------------------------------------
def test_degres_heures_a_la_main():
    r = degres_heures(theta_op=[27.0, 29.0, 30.0, 25.0, 30.0], seuil=[26.0, 28.0, 28.0, 26.0, 26.0],
                      occupe=[1, 1, 0, 1, 1], confort_adaptatif=[1, 1, 1, 1, 0])
    # Seules comptent les heures occupées en période de confort adaptatif : 1 + 1 °C.h
    assert r["dh"] == pytest.approx(2.0) and r["dh_horaire"].tolist() == [1.0, 1.0, 0.0, 0.0, 0.0]
    assert (r["nb_h_inconfort"], r["nb_h_inconfort_1"], r["nb_h_inconfort_2"]) == (2, 2, 0)
    # Juste au seuil : une heure d'inconfort (≥), sans degré-heure
    r = degres_heures([26.0], [26.0], [1], [1])
    assert (r["dh"], r["nb_h_inconfort"]) == (0.0, 1)


# ------------------------------------------------------------------
# DH max (annexe à l'article R. 172-4, chapitre III, IV)
# ------------------------------------------------------------------
def test_categorie_de_contraintes():
    assert categorie_contraintes(True, "BR2") == 2 and categorie_contraintes(True, "BR3") == 2
    assert categorie_contraintes(True, "BR1") == 1 and categorie_contraintes(False, "BR3") == 1


def test_dh_max():
    # Catégorie 1 : 1 250 °C.h, quelle que soit la surface des logements
    assert dh_max("H3", 45.0)["dh_max"] == 1250.0
    assert dh_max("H3", 45.0, climatise=False, exposition_bruit="BR2") == {"categorie": 1, "dh_max": 1250.0}
    assert dh_max("H1a", 45.0, climatise=True)["dh_max"] == 1250.0
    # Catégorie 1 climatisée en H2d ou H3 : 1 600, 1 700 − 5 × S, 1 400
    assert [dh_max(zone, s, climatise=True)["dh_max"] for zone, s in (("H2d", 15.0), ("H3", 40.0), ("H3", 70.0))] \
        == [1600.0, 1500.0, 1400.0]
    # Catégorie 2 : 2 600, 2 850 − 12,5 × S, 2 100
    # (valeurs de deux études : 49,73 m² → 2 228,4 ; 78,3 m² → 2 100)
    assert dh_max("H3", 15.0, True, "BR2") == {"categorie": 2, "dh_max": 2600.0}
    assert dh_max("H3", 49.73, True, "BR3")["dh_max"] == pytest.approx(2228.375)
    assert dh_max("H3", 78.3, True, "BR2")["dh_max"] == 2100.0
    # Continuité aux deux seuils de surface
    assert dh_max("H3", 20.0, True, "BR2")["dh_max"] == 2600.0 and dh_max("H3", 60.0, True, "BR2")["dh_max"] == 2100.0
    assert dh_max("H3", 20.0, True)["dh_max"] == 1600.0 and dh_max("H3", 60.0, True)["dh_max"] == 1400.0
    with pytest.raises(ValueError, match="usage"):
        dh_max("H3", 45.0, usage="bureaux")


# ------------------------------------------------------------------
# Saisons en mode Th-D (fiche 4.6, éq. 76 à 90)
# ------------------------------------------------------------------
def test_saisons_en_confort_adaptatif():
    saisons = Saisons(100.0, 100.0)

    def jour(numero, confort_adaptatif):
        for _ in range(24):
            saisons.ajouter_heure(1, 0.0, 0.0, 0.0, 0.0)
        saisons.nouveau_jour(numero, confort_adaptatif)
        return saisons.aut_ch, saisons.aut_fr

    assert jour(20, False) == (1, 0)
    # Confort adaptatif : chauffage interdit même dans les 8 premières semaines, saison de refroidissement lancée
    assert jour(21, True) == (0, 1)
    # Le chauffage reprend ; le refroidissement ne s'arrête pas avant l'automne
    assert jour(22, False) == (1, 1)
    # À l'automne, sans besoin de froid, la saison de refroidissement tient tant que dure le confort adaptatif
    assert jour(250, True) == (0, 1)
    assert jour(251, False) == (0, 0)


# ------------------------------------------------------------------
# Calcul Th-D d'un groupe
# ------------------------------------------------------------------
def test_mode_refuse(meteo):
    with pytest.raises(ValueError, match="Mode"):
        calculer_besoins(groupe(), meteo, mode="th_e")


def test_calcul_th_d_sans_froid(th_d):
    r = th_d["sans"]
    assert r["q_fr_wh"].sum() == 0.0 and r["q_ch_wh"].sum() > 0.0
    heures = np.flatnonzero(r["confort_adaptatif"].to_numpy())
    assert (heures[0], heures[-1]) == (DEBUT_H3, FIN_H3)
    # Passé le premier test de 9 h, la période de confort adaptatif est sans chauffage et en saison de refroidissement
    periode = r.iloc[DEBUT_H3 + 24:FIN_H3 + 1]
    assert (periode["aut_ch"] == 0).all() and (periode["aut_fr"] == 1).all() and (periode["q_ch_wh"] == 0).all()
    # Seuil de confort : 26 °C la nuit, entre 26 et 28 °C le jour ; sans brasseur, pas de correction
    assert r["seuil_confort"].between(26.0, 28.0).all() and r["seuil_confort"].max() == 28.0
    assert (r["ecart_ba"] == 0).all() and (r["seuil_confort_corrige"] == r["seuil_confort"]).all()
    # Protections mobiles (tableau 34) et ouverture des baies jouent pendant la canicule
    assert periode["rprot_moyen"].max() > 0.7 and (periode["debit_ouvertures_m3h"] > 0).sum() > 500
    assert (r["stockage"] - r[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6


def test_degres_heures_du_groupe(th_d):
    sans, avec = dh_groupe(th_d["sans"]), dh_groupe(th_d["avec"])
    assert sans["dh"] > 0 and sans["nb_h_inconfort"] >= sans["nb_h_inconfort_1"] >= sans["nb_h_inconfort_2"] > 0
    # Aucun degré-heure hors occupation ni hors période de confort adaptatif
    r = th_d["sans"]
    hors = (r["occupe"] == 0) | (r["confort_adaptatif"] == 0)
    assert (sans["dh_horaire"][hors.to_numpy()] == 0).all()
    assert sans["dh"] == pytest.approx(np.maximum(0.0, r["theta_op"] - r["seuil_confort"])[~hors].sum())
    # Les brasseurs relèvent le seuil : moins de degrés-heures, malgré la chaleur qu'ils dégagent
    assert avec["dh"] < 0.8 * sans["dh"]


def test_brasseurs_dans_le_calcul_th_d(th_d):
    sans, avec = th_d["sans"], th_d["avec"]
    en_marche = avec["ecart_ba"] > 0
    assert en_marche.sum() > 100 and avec["ecart_ba"].max() < 4.0
    # Ils ne tournent qu'en occupation et en période de confort adaptatif, et consomment alors de l'électricité
    assert (avec.loc[en_marche, "occupe"] == 1).all() and (avec.loc[en_marche, "confort_adaptatif"] == 1).all()
    assert (avec.loc[en_marche, "energie_brasseurs_wh"] > 0).all()
    assert (avec["seuil_confort_corrige"] == avec["seuil_confort"] + avec["ecart_ba"]).all()
    # Leur chaleur reste dans le groupe : il est un peu plus chaud, et le bilan d'énergie tient toujours
    assert avec["theta_op"].mean() > sans["theta_op"].mean()
    assert (avec["stockage"] - avec[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6


def test_mode_th_b_inchange_par_les_brasseurs():
    """Les brasseurs d'air n'entrent pas dans le calcul du Bbio."""
    meteo = charger_meteo("H3", "th_bc", 100.0).iloc[:24 * 14]
    from moteur.calendrier import construire_calendrier
    calendrier = construire_calendrier().iloc[:24 * 14]
    sans = calculer_besoins(groupe(), meteo, calendrier=calendrier)
    avec = calculer_besoins(groupe(brasseurs=[brasseur()]), meteo, calendrier=calendrier)
    assert "ecart_ba" not in sans.columns and (avec["theta_op"] == sans["theta_op"]).all()


# ------------------------------------------------------------------
# DH d'un projet
# ------------------------------------------------------------------
def test_avertissements():
    """Un groupe sans protection mobile ni baie ouvrable est signalé : son DH n'a pas de sens."""
    assert avertissements_confort(groupe()) == ""
    nu = Groupe("Nu", SURFACE, baies=[Baie("Sud", 20.0, 0, uw=1.4, sw_e=0.5)])
    assert avertissements_confort(nu) == "aucune protection mobile, aucune baie ouvrable"
    ouvrant = Groupe("Ouvrant", SURFACE, baies=[Baie("Sud", 20.0, 0, uw=1.4, sw_e=0.5, ouvrable=True,
                                                     ratio_ouverture_max=0.5)])
    assert avertissements_confort(ouvrant) == "aucune protection mobile"


def test_dh_d_un_projet(th_d):
    projet = Projet("Essai", "H3", 50.0, batiments=[Batiment("Bâtiment", zones=[
        Zone("Logements", groupes=[groupe("Non climatisé"), groupe("Climatisé", climatise=True,
                                                                   exposition_bruit="BR2")])])])
    resultat = calculer_dh(projet)
    table = resultat.groupes.set_index("groupe")
    # Même calcul que celui du groupe seul. Le groupe climatisé est calculé sans sa climatisation ; exposé au
    # bruit, il ouvre moins ses baies (Cpr de 0,7 et 0,3) : son DH est plus élevé
    assert table.loc["Non climatisé", "dh"] == pytest.approx(dh_groupe(th_d["sans"])["dh"])
    assert table.loc["Climatisé", "dh"] > table.loc["Non climatisé", "dh"]
    assert (table["debut_confort_adaptatif"] == DEBUT_H3).all() and (table["fin_confort_adaptatif"] == FIN_H3).all()
    # DH max : 60 m² par logement ; catégorie 1 : 1 250 ; climatisé en BR2, catégorie 2 :
    # 2 850 − 12,5 × 60 = 2 100
    assert table["surface_moyenne_logement_m2"].tolist() == [60.0, 60.0]
    assert table["categorie"].tolist() == [1, 2] and table["dh_max"].tolist() == [1250.0, 2100.0]
    assert (table["respecte"] == (table["dh"] <= table["dh_max"])).all()
    assert (table["avertissement"] == "").all() and resultat.groupes.columns[-1] == "avertissement"
    assert table["ecart_pct"].tolist() == pytest.approx(((table["dh"] / table["dh_max"] - 1.0) * 100.0).tolist())
    heures = resultat.horaire[("Bâtiment", "Logements", "Climatisé")]
    assert heures["q_fr_wh"].sum() == 0.0 and heures["dh_horaire"].sum() == pytest.approx(table.loc["Climatisé", "dh"])
