"""Besoins de chauffage, de refroidissement et d'éclairage (annexe III, fiches 4.5, 4.6, 8.1 et 13.1)."""

import numpy as np
import pytest

from moteur.besoins import SAISONS, Saisons, bilan_besoins, calculer_besoins, puissance_requise
from moteur.calendrier import construire_calendrier
from moteur.meteo import charger_meteo
from moteur.structures import Baie, Groupe, Paroi, PontThermique

FLUX_DU_BILAN = ["flux_ventilation", "flux_baies", "flux_parois", "flux_apports", "flux_inerties_longues"]
SURFACE = 650.0


def immeuble(u_murs=0.25, **options):
    """Dix logements de 65 m² : deux façades, une toiture, un plancher sur sous-sol."""
    return Groupe("Immeuble", SURFACE, nb_logements=10, debit_ventilation_m3h=600.0,
                  debit_ventilation_pointe_m3h=1350.0,
                  parois=[Paroi("Sud", "mur", 200.0, u=u_murs, orientation_deg=0, alpha=0.6),
                          Paroi("Nord", "mur", 200.0, u=u_murs, orientation_deg=180, alpha=0.6),
                          Paroi("Toit", "toiture", 220.0, u=0.15, alpha=0.6),
                          Paroi("Plancher", "plancher_bas", 220.0, u=0.25, contact="local_non_chauffe",
                                b_therm=0.8)],
                  baies=[Baie("Sud", 60.0, 0, uw=1.3, sw_e=0.5, tl=0.7),
                         Baie("Nord", 50.0, 180, uw=1.3, sw_e=0.5, tl=0.7)],
                  ponts_thermiques=[PontThermique("Planchers", 300.0, 0.3)], **options)


@pytest.fixture(scope="module")
def besoins_h1a():
    return calculer_besoins(immeuble(), charger_meteo("H1a", "th_bc", 100.0))


@pytest.fixture(scope="module")
def besoins_h3():
    return calculer_besoins(immeuble(), charger_meteo("H3", "th_bc", 100.0))


# ------------------------------------------------------------------
# Émetteur conventionnel (fiche 8.1, éq. 802 à 808)
# ------------------------------------------------------------------
def test_puissance_requise():
    # Sonde à 15 °C sans émission, 17 °C avec 500 W : droite de pente 250 W/°C
    assert puissance_requise(15.0, 17.0, 500.0, 19.0, 26.0) == pytest.approx(1000.0)     # 4 °C à gagner
    assert puissance_requise(28.0, 30.0, 500.0, 19.0, 26.0) == pytest.approx(-500.0)     # 2 °C à perdre
    assert puissance_requise(22.0, 24.0, 500.0, 19.0, 26.0) == 0.0                       # entre les consignes
    assert puissance_requise(19.0, 21.0, 500.0, 19.0, 26.0) == 0.0                       # juste à la consigne


# ------------------------------------------------------------------
# Saisons (fiche 4.6)
# ------------------------------------------------------------------
def journee(saisons, jour, dh_ch=0.0, dh_fr=0.0, q_ch=0.0, q_fr=0.0):
    """Ajoute 24 heures occupées identiques, puis évalue les saisons du jour « jour »."""
    for _ in range(24):
        saisons.ajouter_heure(1, dh_ch, dh_fr, q_ch, q_fr)
    saisons.nouveau_jour(jour)
    return saisons.aut_ch, saisons.aut_fr


def test_saison_de_chauffage():
    s = Saisons(surface_m2=100.0, nbh_occ_ref=132.0)
    # Jours 1 à 56 : chauffage en fonction, même sans besoin (éq. 76)
    assert all(journee(s, j)[0] == 1 for j in range(1, 57))
    # Jour 57 : besoin horaire moyen nul ≤ 2 Wh/m² : arrêt (éq. 78)
    assert journee(s, 57)[0] == 0
    # Lendemain de l'arrêt : pas encore de test ; ensuite l'inconfort froid se cumule (1 °C × 24 h par jour).
    # Seuil : 40 × max(0,5 ; heures occupées / 528) = 20 °C.h, atteint le premier jour testé
    assert journee(s, 58, dh_ch=1.0)[0] == 0
    assert journee(s, 59, dh_ch=1.0)[0] == 1 and s.nb_redemarrages == 1
    # Redémarré : au moins une semaine de fonctionnement avant un nouvel arrêt
    assert all(journee(s, j)[0] == 1 for j in range(60, 66))
    assert journee(s, 66)[0] == 0
    # Un seul redémarrage : l'arrêt est définitif jusqu'à l'automne
    assert all(journee(s, j, dh_ch=5.0)[0] == 0 for j in range(67, 253))
    # À partir du 253e jour, le chauffage redémarre sur le même critère, puis reste en fonction (éq. 81)
    assert journee(s, 253, dh_ch=0.5)[0] == 0          # 12 °C.h < 20
    assert journee(s, 254, dh_ch=0.5)[0] == 1          # 24 °C.h
    assert all(journee(s, j)[0] == 1 for j in range(255, 366))


def test_chauffage_maintenu_tant_que_le_besoin_reste():
    s = Saisons(surface_m2=100.0, nbh_occ_ref=132.0)
    # 3 Wh/m² par heure : au-dessus du seuil de 2 Wh/m², le chauffage continue au printemps
    assert all(journee(s, j, q_ch=300.0)[0] == 1 for j in range(1, 183))
    # 183e au 252e jour : chauffage interdit quel que soit le besoin (éq. 79)
    assert all(journee(s, j, q_ch=300.0, dh_ch=5.0)[0] == 0 for j in range(183, 253))


def test_saison_de_refroidissement():
    s = Saisons(surface_m2=100.0, nbh_occ_ref=132.0)
    # Première semaine : pas de refroidissement, même en inconfort (éq. 87)
    assert all(journee(s, j, dh_fr=5.0)[1] == 0 for j in range(1, 8))
    # 8e jour : le cumul commence sur la journée écoulée : 5 °C × 24 h = 120 °C.h ≥ 20 : démarrage (éq. 88)
    assert journee(s, 8, dh_fr=5.0)[1] == 1
    assert all(journee(s, j)[1] == 1 for j in range(9, 246))               # une fois démarré, il le reste
    # À partir du 246e jour : arrêt quand le besoin moyen passe sous 2 Wh/m² (éq. 90)
    assert journee(s, 246, q_fr=10000.0)[1] == 1
    assert journee(s, 247)[1] == 1                                         # la moyenne garde la veille en mémoire
    assert all(journee(s, j)[1] == 1 for j in range(248, 274))
    assert journee(s, 274)[1] == 0                                         # 28 jours plus tard, la pointe est sortie
    assert all(journee(s, j, dh_fr=5.0)[1] == 0 for j in range(275, 366))  # pas de redémarrage à l'automne


def test_refroidissement_d_office_en_ete_ou_jamais():
    s = Saisons(surface_m2=100.0, nbh_occ_ref=132.0)
    assert all(journee(s, j)[1] == 0 for j in range(1, 183))               # sans inconfort : pas de démarrage
    assert all(journee(s, j, q_fr=1000.0)[1] == 1 for j in range(183, 246))   # autorisé d'office (éq. 89)
    sans = Saisons(surface_m2=100.0, nbh_occ_ref=132.0, refroidissement=False)
    assert all(journee(sans, j, dh_fr=5.0)[1] == 0 for j in range(1, 366))


# ------------------------------------------------------------------
# Année entière
# ------------------------------------------------------------------
def test_consignes_tenues(besoins_h1a):
    r = besoins_h1a
    assert len(r) == 8760 and not r.isna().any().any()
    chauffe, refroidit = r["q_ch_wh"] > 0, r["q_fr_wh"] > 0
    assert chauffe.sum() > 500 and refroidit.sum() > 100
    assert not (chauffe & refroidit).any()
    # L'émetteur, de puissance illimitée, amène la sonde exactement à la consigne
    assert (r.loc[chauffe, "theta_sd"] - r.loc[chauffe, "consigne_ch"]).abs().max() < 1e-6
    assert (r.loc[refroidit, "theta_sd"] - r.loc[refroidit, "consigne_fr"]).abs().max() < 1e-6
    # Sans émission, la sonde reste entre les consignes, sauf si la saison interdit le système
    libre = ~chauffe & ~refroidit
    trop_froid = libre & (r["theta_sd"] < r["consigne_ch"] - 1e-6)
    trop_chaud = libre & (r["theta_sd"] > r["consigne_fr"] + 1e-6)
    assert (r.loc[trop_froid, "aut_ch"] == 0).all() and (r.loc[trop_chaud, "aut_fr"] == 0).all()
    # Consignes du logement : 19 °C ou 16 °C, 26 °C ou 30 °C
    assert set(r["consigne_ch"].unique()) == {16.0, 19.0} and set(r["consigne_fr"].unique()) == {26.0, 30.0}


def test_saisons_sur_l_annee(besoins_h1a):
    r = besoins_h1a
    jour = construire_calendrier()["jour_annee"].to_numpy()
    assert (r["saison"] == [SAISONS[(c, f)] for c, f in zip(r["aut_ch"], r["aut_fr"])]).all()
    # Chauffage en fonction en janvier, interdit en été, revenu en décembre ; froid autorisé en plein été
    assert (r.loc[jour <= 56, "aut_ch"] == 1).all()
    assert (r.loc[(jour >= 190) & (jour <= 245), ["aut_ch", "aut_fr"]] == [0, 1]).all().all()
    assert (r.loc[jour >= 350, "aut_ch"] == 1).all()
    assert (r.loc[r["aut_ch"] == 0, "q_ch_wh"] == 0).all() and (r.loc[r["aut_fr"] == 0, "q_fr_wh"] == 0).all()
    # L'inconfort ne se compte qu'en occupation
    assert (r["dh_ch"] >= 0).all() and (r["dh_fr"] >= 0).all()


def test_bilan_d_energie_avec_emission(besoins_h1a):
    r = besoins_h1a
    assert (r["stockage"] - r[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6


def test_bilan_des_besoins(besoins_h1a, besoins_h3):
    mensuel, annuel = bilan_besoins(besoins_h1a, SURFACE)
    assert list(mensuel.index) == list(range(1, 13)) and list(mensuel.columns) == ["b_ch", "b_fr", "b_ecl"]
    assert annuel["b_ch"] == pytest.approx(besoins_h1a["q_ch_wh"].sum() / 1000.0 / SURFACE)
    assert annuel["b_fr"] == pytest.approx(mensuel["b_fr"].sum())
    # Le chauffage est un besoin d'hiver, le froid un besoin d'été
    assert mensuel.loc[[12, 1, 2], "b_ch"].sum() > 0.7 * annuel["b_ch"]
    assert mensuel.loc[[6, 7, 8], "b_fr"].sum() > mensuel.loc[[12, 1, 2], "b_fr"].sum()
    # Ordres de grandeur d'un immeuble isolé (kWh/m².an), et effet du climat
    _, annuel_h3 = bilan_besoins(besoins_h3, SURFACE)
    assert 3.0 < annuel["b_ch"] < 40.0 and 0.5 < annuel["b_ecl"] < 3.0
    assert annuel_h3["b_ch"] < annuel["b_ch"] and annuel_h3["b_fr"] > annuel["b_fr"]


def test_sensibilites(besoins_h1a):
    meteo = charger_meteo("H1a", "th_bc", 100.0)
    _, reference = bilan_besoins(besoins_h1a, SURFACE)
    # Murs moins isolés : plus de chauffage
    _, passoire = bilan_besoins(calculer_besoins(immeuble(u_murs=1.0), meteo), SURFACE)
    assert passoire["b_ch"] > 1.5 * reference["b_ch"]
    # Sans refroidissement : aucun besoin de froid, même éclairage
    sans_froid = calculer_besoins(immeuble(), meteo, refroidissement=False)
    _, bilan_sans_froid = bilan_besoins(sans_froid, SURFACE)
    assert bilan_sans_froid["b_fr"] == 0 and (sans_froid["aut_fr"] == 0).all()
    assert bilan_sans_froid["b_ecl"] == pytest.approx(reference["b_ecl"])
    # Sans échangeur sur la ventilation : plus de chauffage
    _, simple_flux = bilan_besoins(calculer_besoins(immeuble(), meteo, efficacite_echangeur=0.0), SURFACE)
    assert simple_flux["b_ch"] > reference["b_ch"]


def test_entrees_incoherentes():
    meteo = charger_meteo("H1a", "th_bc", 100.0)
    with pytest.raises(ValueError, match="même longueur"):
        calculer_besoins(immeuble(), meteo.iloc[:100])
    with pytest.raises(ValueError, match="nb_logements"):
        calculer_besoins(Groupe("Sans logements", 50.0), meteo)
