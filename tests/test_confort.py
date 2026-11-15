"""Confort adaptatif : moyenne glissante, période et seuil de confort chaud (annexe III, fiches 3.1 et 13.5)."""

import numpy as np
import pytest

from moteur.calendrier import construire_calendrier
from moteur.confort import (ecart_confort_adaptatif, est_jour, moyenne_glissante_exterieure,
                            periode_confort_adaptatif, seuil_confort_chaud)
from moteur.meteo import charger_meteo


def test_moyenne_glissante_a_la_main():
    # 20 °C constants : θrm = 0 le premier jour, puis 0,2 × 20 = 4, puis 0,8 × 4 + 0,2 × 20 = 7,2
    theta_rm = moyenne_glissante_exterieure(np.full(72, 20.0))
    assert theta_rm[[0, 23, 24, 47, 48, 71]].tolist() == pytest.approx([0.0, 0.0, 4.0, 4.0, 7.2, 7.2])
    # Seule la veille compte : une journée à 10 °C puis une à 30 °C
    theta_rm = moyenne_glissante_exterieure(np.r_[np.full(24, 10.0), np.full(24, 30.0), np.zeros(24)])
    assert theta_rm[[24, 48]].tolist() == pytest.approx([2.0, 0.8 * 2.0 + 0.2 * 30.0])
    # Un dernier jour incomplet garde sa valeur
    assert len(moyenne_glissante_exterieure(np.full(30, 20.0))) == 30


def test_periode_du_premier_au_dernier_jour_chaud():
    theta_rm = np.array([10.0, 17.0, 12.0, 16.0, 15.0])
    assert periode_confort_adaptatif(theta_rm).tolist() == [False, True, True, True, False]     # sans interruption
    assert not periode_confort_adaptatif(np.full(5, 15.9)).any()
    assert periode_confort_adaptatif(np.full(5, 16.0)).all()


def test_jour_de_7h_a_23h_legales():
    assert [h for h in range(24) if est_jour(h)] == list(range(7, 23))


def test_seuil_de_confort_chaud():
    # De jour : plancher 26 °C (θrm = 10), droite 0,33 × 20 + 20,8 = 27,4 °C, plafond 28 °C (θrm = 30)
    assert seuil_confort_chaud([10.0, 20.0, 30.0], [12, 12, 12], 26.0).tolist() == pytest.approx([26.0, 27.4, 28.0])
    # De nuit, en habitation : la consigne ; ailleurs le seuil suit θrm à toute heure
    assert seuil_confort_chaud([30.0] * 4, [6, 7, 22, 23], 26.0).tolist() == [26.0, 28.0, 28.0, 26.0]
    assert seuil_confort_chaud([30.0], [3], 26.0, habitation=False).tolist() == [28.0]
    # Écart à la consigne (éq. 2546) : jamais négatif
    assert ecart_confort_adaptatif([26.0, 27.4, 25.0], 26.0).tolist() == pytest.approx([0.0, 1.4, 0.0])


@pytest.mark.parametrize("zone, debut, fin", [("H1a", 3480, 6167), ("H3", 2952, 7199)])
def test_periode_des_fichiers_meteo(zone, debut, fin):
    """Période de confort adaptatif des jeux Th-D : heures de début et de fin données par des études (RSET)."""
    theta_rm = moyenne_glissante_exterieure(charger_meteo(zone, "th_d", 100.0)["te"])
    heures = np.flatnonzero(periode_confort_adaptatif(theta_rm))
    assert (heures[0], heures[-1]) == (debut, fin)
    assert len(heures) == fin - debut + 1 and len(construire_calendrier()) == len(theta_rm)
