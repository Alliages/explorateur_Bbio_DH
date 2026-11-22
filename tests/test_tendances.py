"""Tendances du guide Actibaie « Les protections solaires dans la RE 2020 » (v8, 2024) sur la boîte (0.9.13).

Les cas du guide (maison individuelle en H3, immeuble de 48 logements à Nantes, pp. 28-29) sont décrits trop
sommairement pour une comparaison chiffrée : seules les tendances sont vérifiées, sur le logement de 70 m² de départ
placé en H3. Calcul complet du DH (quatre calculs, une trentaine de secondes).

Tendance vérifiée : à produit égal, DH sans protection > gestion manuelle non motorisée > manuelle motorisée >
automatique (pp. 28-29). Tendances du guide NON reproduites, inscrites dans docs/audit.md (0.9.13) au lieu d'être
testées : DH environ divisé par deux par les protections (ici − 11 %), Bbio rangé dans le même ordre que le DH.

Depuis la 0.9.27 : sens physique des principales saisies de la boîte (inertie, traversant, Sw, teinte, brasseurs,
vitrage à surface ouvrante égale), sur le logement de départ en H1a (dix calculs du DH).
"""

from dataclasses import replace

import pytest

from interface.saisie import boite_de_depart, construire_projet
from moteur.calendrier import construire_calendrier
from moteur.dh import calculer_dh


@pytest.fixture(scope="module")
def dh_selon_gestion():
    """DH de la boîte de départ en H3 : sans protection, puis volets selon les trois gestions."""
    calendrier = construire_calendrier()
    base = replace(boite_de_depart(), zone_climatique="H3")
    cas = {"aucune": replace(base, protection="aucune")}
    for gestion in ("manuelle_non_motorisee", "manuelle_motorisee", "automatique"):
        cas[gestion] = replace(base, protection="volet", gestion_protection=gestion)
    return {nom: calculer_dh(construire_projet(boite), calendrier=calendrier).groupes.iloc[0]["dh"]
            for nom, boite in cas.items()}


def test_dh_range_les_gestions_comme_le_guide(dh_selon_gestion):
    dh = dh_selon_gestion
    assert dh["aucune"] > dh["manuelle_non_motorisee"] > dh["manuelle_motorisee"] > dh["automatique"]


# ============================================================
# Sens physique des saisies de la boîte (audit de la 0.9.27)
# ============================================================
# Logement de 70 m² de départ (niveau moyen, H1a) : chaque cas change une seule saisie. Seules les tendances dont le
# sens ne fait pas débat sont testées. Celle de la part vitrée ne l'est qu'à surface ouvrante égale : à ratio
# d'ouverture égal, plus de vitrage donne MOINS de DH (la surventilation, proportionnelle à la surface des baies,
# l'emporte sur le soleil ; docs/audit.md, 0.9.27).
CAS_SENS = {
    "base": {},
    "inertie_legere": {"inertie": "legere"},
    "inertie_tres_lourde": {"inertie": "tres_lourde"},
    "non_traversant": {"traversant": False},
    "sw_faible": {"sw": 0.35},
    "sw_fort": {"sw": 0.60},
    "teinte_claire": {"teinte": "claire"},
    "teinte_sombre": {"teinte": "sombre"},
    "brasseurs": {"brasseurs": True},
}


@pytest.fixture(scope="module")
def dh_selon_saisie():
    """DH de la boîte de départ (H1a) pour chaque cas de CAS_SENS, plus 40 % de vitrage à surface ouvrante égale."""
    calendrier = construire_calendrier()
    base = boite_de_depart()
    cas = {nom: replace(base, **champs) for nom, champs in CAS_SENS.items()}
    # 40 % de vitrage devant et derrière (25 % au départ), ratio d'ouverture réduit d'autant
    cas["vitrage_40_meme_ouverture"] = replace(base, part_vitree_principale=0.40, part_vitree_arriere=0.40,
                                               ratio_ouverture_max=base.ratio_ouverture_max * 0.25 / 0.40)
    return {nom: calculer_dh(construire_projet(boite), calendrier=calendrier).groupes.iloc[0]["dh"]
            for nom, boite in cas.items()}


def test_dh_baisse_avec_l_inertie(dh_selon_saisie):
    dh = dh_selon_saisie
    assert dh["inertie_legere"] > dh["base"] > dh["inertie_tres_lourde"]      # base : inertie lourde


def test_dh_plus_fort_sans_traversant(dh_selon_saisie):
    assert dh_selon_saisie["non_traversant"] > dh_selon_saisie["base"]


def test_dh_monte_avec_le_facteur_solaire(dh_selon_saisie):
    dh = dh_selon_saisie
    assert dh["sw_faible"] < dh["base"] < dh["sw_fort"]                        # base : Sw 0,40


def test_dh_monte_avec_la_teinte(dh_selon_saisie):
    dh = dh_selon_saisie
    assert dh["teinte_claire"] < dh["base"] < dh["teinte_sombre"]


def test_dh_baisse_avec_les_brasseurs(dh_selon_saisie):
    assert dh_selon_saisie["brasseurs"] < dh_selon_saisie["base"]


def test_dh_monte_avec_le_vitrage_a_ouverture_egale(dh_selon_saisie):
    assert dh_selon_saisie["vitrage_40_meme_ouverture"] > dh_selon_saisie["base"]
