"""Calendrier conventionnel : comparaison au tableau de la fiche 4.1 (annexe III) et contrôles d'ensemble."""

import numpy as np
import pytest

from moteur.calendrier import construire_calendrier

# Lignes du tableau de correspondance de la fiche 4.1 : heure de simulation → (ehlo, case des scénarios)
TABLEAU_FICHE_4_1 = {
    0: (1, 2),         # UTC 0h-1h, légal 1h-2h
    1: (1, 3),         # UTC 1h-2h, légal 2h-3h
    1895: (1, 1),      # dernière heure d'hiver : UTC 23h-0h, légal 0h-1h
    1896: (2, 3),      # passage à l'heure d'été : UTC 0h-1h, légal 2h-3h
    7031: (2, 2),      # dernière heure d'été : UTC 23h-0h, légal 1h-2h
    7032: (1, 2),      # retour à l'heure d'hiver : UTC 0h-1h, légal 1h-2h
}


@pytest.fixture(scope="module")
def calendrier():
    return construire_calendrier()


def test_correspondance_fiche_4_1(calendrier):
    for heure, (ehlo, case) in TABLEAU_FICHE_4_1.items():
        ligne = calendrier.iloc[heure]
        assert (ligne["ehlo"], ligne["case"]) == (ehlo, case), f"heure {heure}"


def test_8760_heures_et_bornes(calendrier):
    assert len(calendrier) == 8760
    assert calendrier["case"].between(1, 24).all()
    # hlég, heure légale de début de pas (Hleg = IHJ + EHLO), précède la case d'une heure
    assert calendrier["hleg"].between(0, 23).all() and (calendrier["case"] == calendrier["hleg"] + 1).all()
    assert (calendrier["hleg"] == (calendrier["heure_utc"] + calendrier["ehlo"]) % 24).all()
    assert calendrier["jour_annee"].between(1, 365).all()
    assert calendrier["jour_semaine"].between(1, 7).all()
    assert calendrier["mois"].between(1, 12).all()
    assert calendrier["semaine_mois"].between(1, 5).all()


def test_annee_commence_un_lundi(calendrier):
    assert calendrier.iloc[0]["jour_semaine"] == 1
    assert calendrier.iloc[0]["jour_annee"] == 1
    # Heure 23 : UTC 23h-0h, soit 0h-1h légal le mardi 2 janvier
    assert tuple(calendrier.iloc[23][["jour_annee", "jour_semaine", "case"]]) == (2, 2, 1)


def test_changements_d_heure(calendrier):
    """Chaque case de chaque jour est vue une fois, sauf une case sautée au printemps et une doublée à l'automne."""
    vues = calendrier.groupby(["jour_annee", "case"]).size()
    assert len(vues) == 8760 - 1                      # une case manque, une autre est vue deux fois
    assert vues[vues == 2].index.tolist() == [(294, 2)]   # 1h-2h légal répété au retour à l'hiver
    assert (80, 2) not in vues.index                  # 1h-2h légal sauté au passage à l'été


def test_semaines_par_mois(calendrier):
    """52 semaines réparties 4-4-5-4-5-4-4-5-4-4-5-4, vérifiées par le nombre de jours de chaque mois."""
    jours = calendrier.drop_duplicates("jour_annee")
    jours = jours[jours["jour_annee"] <= 364]
    nb_jours = jours.groupby("mois").size().tolist()
    assert nb_jours == [28, 28, 35, 28, 35, 28, 28, 35, 28, 28, 35, 28]
    # Quatrième semaine de décembre : jours 358 à 364
    semaine_4_decembre = jours[(jours["mois"] == 12) & (jours["semaine_mois"] == 4)]["jour_annee"]
    assert (semaine_4_decembre.min(), semaine_4_decembre.max()) == (358, 364)


def test_jour_365_par_hypothese(calendrier):
    """Jour 365, hors des 52 semaines : un lundi, rattaché à la 1re semaine de décembre (hypothèse de l'outil)."""
    jour_365 = calendrier[calendrier["jour_annee"] == 365]
    assert len(jour_365) == 24
    assert set(jour_365["jour_semaine"]) == {1}
    assert set(zip(jour_365["mois"], jour_365["semaine_mois"])) == {(12, 1)}
    # Dernière heure de l'année : 0h-1h légal, reportée sur le 1er janvier (l'année est un cycle)
    assert tuple(calendrier.iloc[8759][["jour_annee", "case"]]) == (1, 1)
    assert np.array_equal(np.sort(calendrier["h"].to_numpy()), np.arange(8760))
