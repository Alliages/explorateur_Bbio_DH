"""Protections mobiles et ouverture des baies (annexe III, fiches 5.9, 5.10 et 5.13)."""

import numpy as np
import pytest

from moteur.besoins import bilan_besoins, calculer_besoins
from moteur.calendrier import construire_calendrier
from moteur.meteo import charger_meteo
from moteur.ouvertures import (OuverturesGroupe, contrainte_ouverture, debit_surventilation, moderation_exterieure,
                               ratio_selon_temperature, seuils_ouverture, surface_traversante)
from moteur.protections import (ProtectionsGroupe, ligne_saison, matrices_automatiques, matrices_manuelles,
                                occupation_gpm, rprot_selon_eclairement)
from moteur.scenarios import charger_scenarios
from moteur.structures import Baie, Groupe, Paroi

FLUX_DU_BILAN = ["flux_ventilation", "flux_baies", "flux_parois", "flux_apports", "flux_inerties_longues"]
SURFACE = 300.0
HIVER, MI_SAISON, ETE = 3, 2, 1         # saisons propres du groupe (fiche 4.6)


def baie(nom="Sud", orientation=0, **options):
    """Baie de 20 m² : U 1,4 nue et 1,1 protégée, Sw 0,5 nue et 0,1 protégée."""
    return Baie(nom, 20.0, orientation, uw=1.4, sw_e=0.5, sw_c=0.5, tl=0.6, **options)


def volet(gestion="manuelle_motorisee", **options):
    return dict(protection="volet", gestion_protection=gestion, uw_protege=1.1, sw_protege=0.1, sw2_protege=0.04,
                **options)


def groupe(baies):
    return Groupe("G", SURFACE, nb_logements=5, debit_ventilation_m3h=300.0, volume_m3=750.0, traversant=True,
                  parois=[Paroi("Mur", "mur", 150.0, u=0.25, orientation_deg=0, alpha=0.6),
                          Paroi("Toit", "toiture", 100.0, u=0.15, alpha=0.6)], baies=baies)


@pytest.fixture(scope="module")
def meteo():
    return charger_meteo("H3", "th_bc", 100.0)


# ------------------------------------------------------------------
# Matrices conventionnelles et occupation (fiches 5.9 et 4.1)
# ------------------------------------------------------------------
def test_matrices_conventionnelles():
    manuelles = matrices_manuelles()
    assert len(manuelles) == 2 * 6 * 4          # 2 protections, 6 couples gestion × occupation, 4 lignes
    assert manuelles[("volet", "manuelle_non_motorisee", "occupation", "ete_chaud")] == (0.25, 60000.0, 0.8)
    assert manuelles[("volet", "manuelle_motorisee", "inoccupation", "ete_chaud")] == (0.5, None, 0.8)
    assert manuelles[("store_enroulable", "manuelle_motorisee", "inoccupation", "ete_chaud")] == (0.6, None, 0.1)
    assert manuelles[("volet", "derogation_avec_detecteur", "occupation", "ete_frais")] == (0.2, 30000.0, 0.9)
    automatiques = matrices_automatiques()
    assert automatiques[("occupation", "ete")]["jour_clair_chaud"] == 1.0
    assert automatiques[("occupation", "ete")]["jour_clair_frais"] == 0.75
    assert automatiques[("inoccupation", "mi_saison")]["jour_clair_chaud"] == 0.5
    assert all(automatiques[(o, "hiver")]["nuit_frais"] == 1.0 for o in ("occupation", "inoccupation"))


def test_occupation_au_sens_des_protections():
    indice = occupation_gpm(charger_scenarios(), construire_calendrier())
    # 6 748 heures occupées ; absences de journée : 51 semaines × 36 h + 8 h du jour 365 ; vacances : 168 h
    assert {v: int((indice == v).sum()) for v in (1, 0, -1)} == {1: 6748, 0: 1844, -1: 168}
    # Lundi 1er janvier : absent de 9 h à 17 h légales, soit les heures 8 à 15 (UTC + 1)
    assert indice[:24].tolist() == [1] * 8 + [0] * 8 + [1] * 8


def test_rprot_selon_l_eclairement_et_ligne_d_ete():
    assert rprot_selon_eclairement(np.array([0.0, 30000.0, 60000.0, 90000.0]), 0.2, 60000.0).tolist() \
        == pytest.approx([0.2, 0.6, 1.0, 1.0])
    assert (ligne_saison("hiver", 30.0), ligne_saison("ete", 26.4), ligne_saison("ete", 26.5)) \
        == ("hiver", "ete_frais", "ete_chaud")


# ------------------------------------------------------------------
# Ratio de fermeture, flux et déperdition d'une baie (fiches 5.9 et 5.10)
# ------------------------------------------------------------------
def test_volet_manuel(meteo):
    p = ProtectionsGroupe(groupe([baie(**volet())]), meteo, "th_bc")
    nuit, midi = 2, int(np.argmax(p.etp[0]))            # une heure sans lumière, l'heure la plus éclairée
    assert p.etp[0, nuit] == 0 and p.etp[0, midi] > 30000
    # Hiver, occupé, de nuit : 70 % des baies fermées à 90 %, 30 % à 80 % (locaux inoccupés, de nuit)
    r, r_u = p.ratios(nuit, HIVER, True, 1, 20.0, 20.0)
    assert r[0] == pytest.approx(0.7 * 0.9 + 0.3 * 0.8) and r_u[0] == r[0]
    # Absence de journée : position de jour des locaux inoccupés (10 %), même sans lumière ; vacances : de nuit
    assert p.ratios(nuit, HIVER, False, 0, 20.0, 20.0)[0][0] == pytest.approx(0.10)
    assert p.ratios(midi, HIVER, False, -1, 20.0, 20.0)[0][0] == pytest.approx(0.80)
    # Été chaud (veille à 27 °C), occupé, de jour : Rprot0 = 30 %, plein à 40 000 lux ; inoccupés : 50 %
    etp = p.etp[0, midi]
    occupes = 1.0 if etp >= 40000 else 0.3 + 0.7 * etp / 40000
    r, _ = p.ratios(midi, ETE, True, 1, 26.0, 27.0)
    assert r[0] == pytest.approx(0.7 * occupes + 0.3 * 0.5)
    # Flux : parts nue et protégée (éq. 219-220) ; déperdition : (1 − R) × 1,4 + R × 1,1 par m² (éq. 210)
    f = p.flux(midi, r, r)
    isr = p.a_isr[0, midi]
    assert f["fs1"] == pytest.approx(isr * ((1 - r[0]) * 0.5 + r[0] * 0.06))
    assert f["fs2"] == pytest.approx(isr * r[0] * 0.04) and f["fs3"] == 0.0
    assert f["hg_es"] == pytest.approx(20.0 * ((1 - r[0]) * 1.4 + r[0] * 1.1))
    assert f["rprot_moyen"] == pytest.approx(r[0])


def test_volet_automatique(meteo):
    p = ProtectionsGroupe(groupe([baie(**volet("automatique"))]), meteo, "th_bc")
    midi = int(np.argmax(p.etp[0]))
    etp = p.etp[0, midi]
    assert etp > 10000
    # Été, occupé, baie éclairée, ambiance chaude (27 °C) : automatique 100 % ; dérogation sur 0,7 × 0,25
    derogation = 1.0 if etp >= 60000 else 0.2 + 0.8 * etp / 60000           # été frais, sans détecteur
    r, r_u = p.ratios(midi, ETE, True, 1, 27.0, 20.0)
    assert r[0] == pytest.approx(0.175 * derogation + 0.825 * 1.0) and r_u[0] == pytest.approx(r[0])
    # Hystérésis : à 25 °C l'ambiance reste « chaude » ; sous 24 °C elle devient « fraîche » (75 %)
    assert p.ratios(midi, ETE, True, 1, 25.0, 20.0)[0][0] == pytest.approx(r[0])
    r, r_u = p.ratios(midi, ETE, True, 1, 23.0, 20.0)
    assert r[0] == pytest.approx(0.175 * derogation + 0.825 * 0.75)
    # Déperdition (éq. 211) : la part automatique ne compte que fermée en entier
    assert r_u[0] == pytest.approx(0.175 * derogation)
    # Inoccupé : tout en automatique ; en hiver, de jour, volets ouverts (pas d'horloge : jamais « nuit »)
    assert p.ratios(2, HIVER, False, -1, 20.0, 20.0)[0][0] == 0.0
    crepusculaire = ProtectionsGroupe(groupe([baie(**volet("automatique", horloge_crepusculaire=True))]), meteo,
                                      "th_bc")
    assert crepusculaire.ratios(2, HIVER, False, -1, 20.0, 20.0)[0][0] == 1.0      # de nuit : fermés


def test_store_releve_par_grand_vent_et_baie_nue(meteo):
    store = dict(volet(), protection="store_enroulable")
    p = ProtectionsGroupe(groupe([baie(**store), baie("Nue", 180)]), meteo, "th_bc")
    r, _ = p.ratios(2, HIVER, True, 1, 20.0, 20.0)
    assert r[0] == pytest.approx(0.7 * 0.1 + 0.3 * 0.1) and r[1] == 0.0        # store : 10 % la nuit ; baie nue : 0
    p.vent[2] = 12.0
    assert p.ratios(2, HIVER, True, 1, 20.0, 20.0)[0][0] == 0.0
    interieur = ProtectionsGroupe(groupe([baie(**dict(store, protection_exterieure=False))]), meteo, "th_bc")
    interieur.vent[2] = 12.0
    assert interieur.ratios(2, HIVER, True, 1, 20.0, 20.0)[0][0] == pytest.approx(0.1)


@pytest.mark.parametrize("fabrique", [
    lambda: baie(protection="persienne", uw_protege=1.1, sw_protege=0.1),
    lambda: baie(protection="volet", gestion_protection="domotique", uw_protege=1.1, sw_protege=0.1),
    lambda: baie(protection="volet", sw_protege=0.1),                       # U protégé manquant
    lambda: baie(protection="volet", uw_protege=1.1, sw_protege=0.1, sw2_protege=0.2),
    lambda: baie(ouvrable=True),                                            # ratio d'ouverture manquant
    lambda: baie(ouvrable=True, ratio_ouverture_max=1.4),
    lambda: baie(exposition_bruit="BR5"),
])
def test_saisies_refusees(fabrique):
    with pytest.raises(ValueError):
        fabrique()


# ------------------------------------------------------------------
# Ouverture des baies (fiche 5.13)
# ------------------------------------------------------------------
def test_moderation_par_la_temperature_exterieure():
    # Consigne 26 °C : plafond Th-B à 25 °C ; opérative 26 °C : limite MIN(25 ; 29) = 25 °C
    assert [moderation_exterieure(te, 26.0, 26.0) for te in (8.0, 14.0, 18.0, 24.0, 25.5)] \
        == pytest.approx([0.0, 0.5, 1.0, 1.0, 0.0])
    # Opérative 20 °C : on ferme dès que l'extérieur dépasse 23 °C
    assert moderation_exterieure(22.0, 20.0, 26.0) == 1.0 and moderation_exterieure(24.0, 20.0, 26.0) == 0.0


def test_hysteresis_d_ouverture():
    assert seuils_ouverture(ETE, 26.0, 0.0) == (23.0, 25.0, 23.0, 22.0)
    assert seuils_ouverture(HIVER, 26.0, 1.5)[1] == 28.5
    seuils = seuils_ouverture(ETE, 26.0, 0.0)
    ratio = ratio_selon_temperature(0.0, 24.0, seuils)             # on ouvre : à mi-chemin de 23 à 25 °C
    assert ratio == pytest.approx(0.5)
    assert ratio_selon_temperature(ratio, 22.5, seuils) == pytest.approx(0.5)       # on referme entre 23 et 22 °C
    ratio = ratio_selon_temperature(ratio, 26.0, seuils)
    assert ratio == 1.0 and ratio_selon_temperature(ratio, 23.5, seuils) == 1.0     # reste ouvert en redescendant
    assert ratio_selon_temperature(ratio, 22.2, seuils) == pytest.approx(0.2)


def test_contrainte_d_ouverture():
    assert contrainte_ouverture("BR1", ETE, 12) == 1.0 and contrainte_ouverture("BR1", ETE, 2) == 1.0
    assert (contrainte_ouverture("BR2", ETE, 12), contrainte_ouverture("BR3", ETE, 23)) == (0.7, 0.3)
    assert contrainte_ouverture("BR1", HIVER, 12) == 0.3


def test_debit_par_les_baies_ouvertes():
    aouv, facade = np.array([2.0, 2.0]), np.array([90.0, 90.0])
    sud_nord, sud_sud = np.array([0.0, -180.0]), np.array([0.0, 10.0])
    # Deux orientations opposées de 2 m² : Sors = 2 × (1 / racine(1/4 + 1/4)) / 4 = 0,707 m²
    assert surface_traversante(aouv, sud_nord, facade) == pytest.approx(np.sqrt(2.0) / 2.0)
    assert surface_traversante(aouv, sud_sud, facade) == 0.0            # une seule orientation : pas de balayage
    # Une baie de façade et une de toiture : la toiture, « sous le vent », compte dans le reste de la surface
    assert surface_traversante(aouv, sud_nord, np.array([90.0, 0.0])) == pytest.approx(np.sqrt(2.0) / 4.0)
    # Non traversant, sans vent, 4 °C d'écart : 3 600 × (4 / 2) × racine(0,0035 × 1,5 × 4)
    assert debit_surventilation(aouv, sud_nord, facade, False, 1.5, 0.0, 20.0, 24.0) \
        == pytest.approx(3600.0 * 2.0 * np.sqrt(0.021))
    # Non traversant, vent de 5 m/s : le vent l'emporte (0,001 × 25 > 0,021)
    assert debit_surventilation(aouv, sud_nord, facade, False, 1.5, 5.0, 20.0, 24.0) \
        == pytest.approx(3600.0 * 2.0 * np.sqrt(0.025))
    # Traversant : 3 600 × 0,6 × Sors × MIN(5 ; 3) × racine(0,75)
    assert debit_surventilation(aouv, sud_nord, facade, True, 1.5, 5.0, 20.0, 24.0) \
        == pytest.approx(3600.0 * 0.6 * np.sqrt(2.0) / 2.0 * 3.0 * np.sqrt(0.75))
    assert debit_surventilation(np.zeros(2), sud_nord, facade, True, 1.5, 5.0, 20.0, 24.0) == 0.0


def test_ouverture_d_une_heure(meteo):
    g = groupe([baie(ouvrable=True, ratio_ouverture_max=0.5), baie("Nord", 180, ouvrable=True,
                                                                   ratio_ouverture_max=0.5)])
    o = OuverturesGroupe(g, meteo)
    h = 4000
    o.te[h], o.vent[h] = 20.0, 0.0
    arguments = dict(consigne_fr=26.0, consigne_fr_confort=26.0, ecart_confort_adaptatif=0.0, theta_op_prec=26.0,
                     theta_i_prec=26.0)
    # Hors saison de refroidissement, ou hors occupation : baies fermées
    assert o.pas(h, MI_SAISON, False, True, 12, **arguments)["debit_m3h"] == 0.0
    assert o.pas(h, ETE, True, False, 12, **arguments)["debit_m3h"] == 0.0
    # Été, occupé, midi, 26 °C dedans et 20 °C dehors : Rouv = 0,7 × 1 × 1 × 1 ; Aouv = 0,7 × 0,5 × 40 m² = 14 m²
    r = o.pas(h, ETE, True, True, 12, **arguments)
    assert r["aouv_m2"] == pytest.approx(14.0) and r["rouv_moyen"] == pytest.approx(0.7)
    assert r["debit_m3h"] == pytest.approx(3600.0 * 7.0 * np.sqrt(0.0035 * 1.5 * 6.0))     # tirage seul, sans vent
    assert r["hg"] == pytest.approx(0.34 * r["debit_m3h"] * 292.0 / 293.0)
    # Protections fermées à 80 % : il ne reste que 20 % de la surface ouvrable, soit 4 m²
    assert o.pas(h, ETE, True, True, 12, rprot=np.array([0.8, 0.8]), **arguments)["aouv_m2"] == pytest.approx(4.0)
    # La nuit, la position du soir est gardée ; l'extérieur trop chaud (25,5 °C) fait tout refermer
    assert o.pas(h, ETE, True, True, 2, **dict(arguments, theta_op_prec=22.0))["aouv_m2"] == pytest.approx(14.0)
    o.te[h] = 25.5
    assert o.pas(h, ETE, True, True, 12, **arguments)["debit_m3h"] == 0.0


# ------------------------------------------------------------------
# Effet sur les besoins
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def besoins(meteo):
    """Besoins du même groupe : baies nues, avec volets, avec volets et baies ouvrables."""
    ouverture = dict(ouvrable=True, ratio_ouverture_max=0.6)
    cas = {"nu": [baie(), baie("Nord", 180)],
           "volets": [baie(**volet()), baie("Nord", 180, **volet())],
           "volets_ouvrants": [baie(**volet(), **ouverture), baie("Nord", 180, **volet(), **ouverture)]}
    return {nom: calculer_besoins(groupe(baies), meteo) for nom, baies in cas.items()}


def test_moins_de_froid_avec_volets_et_ouvertures(besoins):
    annuel = {nom: bilan_besoins(r, SURFACE)[1] for nom, r in besoins.items()}
    assert annuel["volets_ouvrants"]["b_fr"] < annuel["volets"]["b_fr"] < annuel["nu"]["b_fr"]
    assert annuel["volets_ouvrants"]["b_fr"] < 0.6 * annuel["nu"]["b_fr"]
    # L'ouverture n'a lieu qu'en saison de refroidissement : le chauffage n'en dépend pas
    assert annuel["volets_ouvrants"]["b_ch"] == pytest.approx(annuel["volets"]["b_ch"], rel=0.02)


def test_sorties_horaires_des_protections_et_des_ouvertures(besoins):
    nu, complet = besoins["nu"], besoins["volets_ouvrants"]
    assert (nu["rprot_moyen"] == 0).all() and (nu["debit_ouvertures_m3h"] == 0).all()
    assert nu["hg_es"].nunique() == 1 and nu["hg_es"].iloc[0] == pytest.approx(2 * 20.0 * 1.4)
    assert complet["rprot_moyen"].between(0.0, 1.0).all() and complet["rprot_moyen"].max() > 0.8
    assert complet["hg_es"].between(2 * 20.0 * 1.1, 2 * 20.0 * 1.4).all()
    ouvert = complet["debit_ouvertures_m3h"] > 0
    assert ouvert.sum() > 200 and (complet.loc[ouvert, "aut_fr"] == 1).all()
    assert complet["rouv_moyen"].between(0.0, 0.7).all()


def test_bilan_d_energie_avec_protections_et_ouvertures(besoins):
    for nom, r in besoins.items():
        assert (r["stockage"] - r[FLUX_DU_BILAN].sum(axis=1)).abs().max() < 1e-6, nom
