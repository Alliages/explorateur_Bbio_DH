"""Tendances du guide Actibaie « Les protections solaires dans la RE 2020 » (v8, 2024) sur la boîte (0.9.13).

Les cas du guide (maison individuelle en H3, immeuble de 48 logements à Nantes, pp. 28-29) sont décrits trop
sommairement pour une comparaison chiffrée : seules les tendances sont vérifiées, sur le logement de 70 m² de départ
placé en H3. Calcul complet du DH (quatre calculs, une trentaine de secondes).

Tendance vérifiée : à produit égal, DH sans protection > gestion manuelle non motorisée > manuelle motorisée >
automatique (pp. 28-29). Tendances du guide NON reproduites, inscrites dans docs/audit.md (0.9.13) au lieu d'être
testées : DH environ divisé par deux par les protections (ici − 11 %), Bbio rangé dans le même ordre que le DH.
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
