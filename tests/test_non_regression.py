"""Non-régression : le Bbio et le DH de cas fixés ne bougent pas sans qu'on le décide (0.9.30).

Jusqu'à la 0.9.29, ce contrôle se faisait à la main à chaque audit (docs/audit.md, 0.9.27 : l'exemple du README
était passé de 34,3 à 27,8 points sans qu'aucun test n'échoue). Ici, les six boîtes de départ de l'interface
(deux bâtiments × trois niveaux d'enveloppe) et l'exemple du README.md sont recalculés et comparés aux valeurs de
la 0.9.29.

Tolérances : 0,05 point de Bbio ; 0,5 % de DH, au-dessus du « bruit » numérique du DH (0,2 % pour une
perturbation de 1e-12 des infiltrations, docs/audit.md, 0.9.29), qu'une autre version de numpy peut déclencher.

Une modification VOULUE des résultats met à jour ces valeurs, avec le CHANGELOG.md et la table de non-régression
de docs/audit.md. Durée : une quarantaine de secondes (quatorze calculs annuels).
"""

import pytest

from interface.saisie import boite_de_depart, construire_projet
from moteur.bbio import calculer_bbio
from moteur.calendrier import construire_calendrier
from moteur.dh import calculer_dh
from moteur.structures import Baie, Batiment, Groupe, Paroi, Projet, Zone

# ============================================================
# RÉGLAGES : valeurs de référence (0.9.29) et tolérances
# ============================================================
TOLERANCE_BBIO = 0.05               # points
TOLERANCE_DH = 0.005                # part du DH
# (bâtiment de départ, niveau d'enveloppe) → (Bbio en points, DH en °C.h)
BOITES_DE_DEPART = {("Logement de 70 m²", "Performant"): (93.963, 543.99),
                    ("Logement de 70 m²", "Moyen"): (119.779, 731.94),
                    ("Logement de 70 m²", "Faible"): (138.709, 883.75),
                    ("Immeuble de 9 logements", "Performant"): (49.996, 447.70),
                    ("Immeuble de 9 logements", "Moyen"): (60.338, 599.13),
                    ("Immeuble de 9 logements", "Faible"): (67.613, 747.90)}
EXEMPLE_README = (27.8, 1981.0)     # « Résultat attendu » de la section « Premier calcul » du README.md, arrondi


@pytest.fixture(scope="module")
def calendrier():
    return construire_calendrier()


def bbio_et_dh(projet, calendrier):
    """Bbio (points) et DH (°C.h) du premier groupe d'un projet."""
    return (calculer_bbio(projet, calendrier=calendrier).groupes.iloc[0]["bbio"],
            calculer_dh(projet, calendrier=calendrier).groupes.iloc[0]["dh"])


@pytest.mark.parametrize("batiment, niveau", list(BOITES_DE_DEPART))
def test_boites_de_depart(batiment, niveau, calendrier):
    bbio, dh = bbio_et_dh(construire_projet(boite_de_depart(batiment, niveau)), calendrier)
    bbio_attendu, dh_attendu = BOITES_DE_DEPART[(batiment, niveau)]
    assert bbio == pytest.approx(bbio_attendu, abs=TOLERANCE_BBIO)
    assert dh == pytest.approx(dh_attendu, rel=TOLERANCE_DH)


def test_exemple_du_readme(calendrier):
    """Le projet de la section « Premier calcul » du README.md, recopié tel quel."""
    baies = [Baie(nom, 20.0, orientation, uw=1.4, sw_e=0.5, tl=0.6,
                  protection="volet", uw_protege=1.1, sw_protege=0.1,
                  ouvrable=True, ratio_ouverture_max=0.6)
             for nom, orientation in (("Baies sud", 0), ("Baies nord", 180))]
    groupe = Groupe("Logements", 300.0, nb_logements=5, debit_ventilation_m3h=300.0, traversant=True,
                    parois=[Paroi("Mur sud", "mur", 150.0, u=0.25, orientation_deg=0, alpha=0.6),
                            Paroi("Toiture", "toiture", 100.0, u=0.15, alpha=0.6)],
                    baies=baies)
    projet = Projet("Essai", "H3", altitude_m=50.0,
                    batiments=[Batiment("Bâtiment", zones=[Zone("Zone", groupes=[groupe])])])
    bbio, dh = bbio_et_dh(projet, calendrier)
    # Le README écrit des valeurs arrondies au dixième de point et au °C.h : l'arrondi s'ajoute à la tolérance
    assert bbio == pytest.approx(EXEMPLE_README[0], abs=TOLERANCE_BBIO + 0.05)
    assert dh == pytest.approx(EXEMPLE_README[1], rel=TOLERANCE_DH)
