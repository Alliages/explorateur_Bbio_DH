"""Scénarios du logement collectif : comparaison au classeur des scénarios conventionnels et à l'annexe III."""

import os

import numpy as np
import pytest

from config.reglages import CLASSEUR_SCENARIOS
from moteur.calendrier import construire_calendrier
from moteur.scenarios import charger_scenarios

# --- Référence écrite indépendamment du moteur -----------------------------------------------------
# Annexe III, fiche 4.1 et classeur du 29/04/2026 : absences en heures légales [début ; fin[
ABSENCES = {1: (9, 17), 2: (9, 17), 3: (9, 13), 4: (9, 17), 5: (9, 17)}   # lundi → vendredi ; week-end occupé
JOURS_INOCCUPES = range(358, 365)                                          # 4e semaine de décembre
NB_SCENARIOS = 13


@pytest.fixture(scope="module")
def calendrier():
    return construire_calendrier()


@pytest.fixture(scope="module")
def scenarios():
    return charger_scenarios("logement_collectif")


def occupation_attendue(calendrier):
    """Occupation heure par heure, reconstruite à partir des seules constantes ci-dessus."""
    attendu = np.ones(len(calendrier))
    for i, (jour_semaine, case, jour_annee) in enumerate(zip(calendrier["jour_semaine"], calendrier["case"],
                                                             calendrier["jour_annee"])):
        debut_legal = case - 1                          # la case k couvre [k−1 ; k[ en heure légale
        absence = ABSENCES.get(jour_semaine)
        if (absence and absence[0] <= debut_legal < absence[1]) or jour_annee in JOURS_INOCCUPES:
            attendu[i] = 0
    return attendu


def test_scenarios_presents(scenarios):
    assert len(scenarios.noms) == NB_SCENARIOS
    for nom in ("occupation", "chauffage", "refroidissement", "eclairage", "logements_apports_chaleur"):
        assert nom in scenarios.noms


def test_occupation_heure_par_heure(scenarios, calendrier):
    occupation = scenarios.derouler("occupation", calendrier)
    assert np.array_equal(occupation, occupation_attendue(calendrier))
    assert set(np.unique(occupation)) == {0.0, 1.0}


def test_nombre_d_heures_occupees(scenarios, calendrier):
    """Compte fait à la main sur l'année conventionnelle.

    Heures d'absence d'une semaine normale : 4 × 8 + 4 = 36. Semaines 1 à 51, plus le lundi 365 :
    51 × 36 + 8 = 1 844 h. Semaine 52 inoccupée : 168 h. Les changements d'heure (1h-2h légal un jeudi
    sauté, un vendredi doublé) tombent la nuit, hors des absences : ils ne changent pas le compte.
    """
    occupation = scenarios.derouler("occupation", calendrier)
    assert int((occupation == 0).sum()) == 51 * 36 + 8 + 168
    assert int(occupation.sum()) == 8760 - (51 * 36 + 8 + 168)


def test_consignes(scenarios, calendrier):
    chauffage = scenarios.consigne("chauffage", calendrier)
    refroidissement = scenarios.consigne("refroidissement", calendrier)
    occupation = scenarios.derouler("occupation", calendrier)
    assert set(np.unique(chauffage)) == {16.0, 19.0}
    assert set(np.unique(refroidissement)) == {26.0, 30.0}
    # Consigne normale exactement quand le logement est occupé
    assert np.array_equal(chauffage == 19.0, occupation == 1)
    assert np.array_equal(refroidissement == 26.0, occupation == 1)
    # Semaine inoccupée : état « réduit de plus de 48 h » sur ses 168 heures
    assert int((scenarios.derouler("chauffage", calendrier) == -1).sum()) == 168


def test_apports_internes(scenarios, calendrier):
    """Apports hors occupants : 5,7 W/m², à 100 % de 6h à 9h et de 17h à 22h en semaine, 20 % sinon, 0 en vacances."""
    ratio = scenarios.derouler("logements_apports_chaleur", calendrier)
    assert scenarios.parametres["logements_apports_chaleur"] == pytest.approx(5.7)
    assert scenarios.parametres["logements_chaleur_occupant"] == pytest.approx(90)
    lundi = calendrier[(calendrier["jour_annee"] == 8)].sort_values("case")
    attendu_lundi = [0.2] * 6 + [1] * 3 + [0.2] * 8 + [1] * 5 + [0.2] * 2
    assert np.allclose(ratio[lundi["h"].to_numpy()], attendu_lundi)
    assert (ratio[calendrier["jour_annee"].isin(JOURS_INOCCUPES).to_numpy()] == 0).all()


def test_ventilation_permanente(scenarios, calendrier):
    assert (scenarios.derouler("ventilation", calendrier) == 1).all()


def test_scenario_inconnu(scenarios, calendrier):
    with pytest.raises(KeyError):
        scenarios.derouler("piscine", calendrier)
    with pytest.raises(KeyError):
        scenarios.consigne("occupation", calendrier)
    with pytest.raises(ValueError):
        charger_scenarios("bureaux")


@pytest.mark.skipif(not os.path.exists(CLASSEUR_SCENARIOS), reason="classeur officiel absent de _references/")
def test_identique_au_classeur_officiel(scenarios):
    """Tableau d'occupation relu directement dans le classeur (lignes 31 à 37, colonnes C à Z)."""
    import openpyxl
    feuille = openpyxl.load_workbook(CLASSEUR_SCENARIOS, read_only=True, data_only=True)["LC"]
    lignes = list(feuille.iter_rows(min_row=31, max_row=37, min_col=3, max_col=26, values_only=True))
    assert np.array_equal(scenarios.horaire["occupation"], np.array(lignes, dtype=float))
