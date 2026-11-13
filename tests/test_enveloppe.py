"""Coefficients de transmission thermique selon l'inclinaison (annexe III, fiches 5.10, 5.17 et 5.19)."""

import pytest

from moteur.enveloppe import transmission_baies, transmission_parois, transmission_ponts, u_baie, u_paroi
from moteur.structures import Baie, Groupe, Paroi, PontThermique


# ------------------------------------------------------------------
# Baies (fiche 5.10, éq. 207)
# ------------------------------------------------------------------
@pytest.mark.parametrize("inclinaison, attendu", [
    (90.0, 1.3),        # verticale
    (60.0, 1.3),        # verticale à partir de 60°
    (45.0, 1.55),       # milieu de l'interpolation entre 30° et 60°
    (30.0, 1.8),        # début de l'interpolation : encore la valeur horizontale
    (0.0, 1.8),         # horizontale
])
def test_u_baie_selon_inclinaison(inclinaison, attendu):
    baie = Baie("B", 2.0, 0, inclinaison_deg=inclinaison, uw=1.3, uw_horizontal=1.8)
    assert u_baie(baie) == pytest.approx(attendu)


def test_u_baie_sans_valeur_horizontale():
    assert u_baie(Baie("B", 2.0, 0, inclinaison_deg=0, uw=1.3)) == pytest.approx(1.3)
    with pytest.raises(ValueError, match="uw"):
        u_baie(Baie("B", 2.0, 0))


# ------------------------------------------------------------------
# Parois opaques (fiche 5.17, § 5.17.3.4 et éq. 294)
# ------------------------------------------------------------------
def test_u_paroi_dans_la_position_de_son_type():
    # Le U saisi est celui de la position du type : il ne change pas
    assert u_paroi(Paroi("Mur", "mur", 10.0, u=0.25, orientation_deg=0)) == pytest.approx(0.25)
    assert u_paroi(Paroi("Toit", "toiture", 10.0, u=0.15)) == pytest.approx(0.15)
    assert u_paroi(Paroi("Plancher", "plancher_bas", 10.0, u=0.20)) == pytest.approx(0.20)


def test_u_paroi_hors_de_sa_position():
    # Mur de U = 0,25 : Rth = 4 − 0,17 = 3,83 m².K/W
    r_th = 1 / 0.25 - 0.17
    u_asc, u_des = 1 / (r_th + 0.14), 1 / (r_th + 0.21)

    def mur(inclinaison):
        return Paroi("Mur", "mur", 10.0, u=0.25, orientation_deg=0, inclinaison_deg=inclinaison)

    assert u_paroi(mur(0)) == pytest.approx(u_asc)
    assert u_paroi(mur(45)) == pytest.approx((u_asc + 0.25) / 2)
    assert u_paroi(mur(100)) == pytest.approx(0.25)
    assert u_paroi(mur(135)) == pytest.approx((0.25 + u_des) / 2)
    assert u_paroi(mur(180)) == pytest.approx(u_des)
    # Continuité aux bornes de l'interpolation descendante (inversion de la formule imprimée corrigée)
    assert u_paroi(mur(120)) == pytest.approx(0.25)
    assert u_paroi(mur(149.999)) == pytest.approx(u_des, abs=1e-6)
    # Flux ascendant : moins de résistance de surface, donc U plus fort ; descendant : l'inverse
    assert u_asc > 0.25 > u_des


def test_u_paroi_impossible():
    with pytest.raises(ValueError, match="résistances superficielles"):
        u_paroi(Paroi("Mur", "mur", 10.0, u=8.0, orientation_deg=0))
    with pytest.raises(ValueError, match="u à renseigner"):
        u_paroi(Paroi("Mur", "mur", 10.0, orientation_deg=0))


# ------------------------------------------------------------------
# Transmissions du groupe
# ------------------------------------------------------------------
def test_transmissions_du_groupe():
    groupe = Groupe("G", 50.0,
                    parois=[Paroi("Mur", "mur", 20.0, u=0.25, orientation_deg=0),
                            Paroi("Sur cave", "plancher_bas", 50.0, u=0.20, contact="local_non_chauffe",
                                  b_therm=0.5)],
                    baies=[Baie("B1", 4.0, 0, uw=1.3), Baie("B2", 2.0, 180, uw=1.5)],
                    ponts_thermiques=[PontThermique("Plancher", 30.0, 0.3), PontThermique("Refend", 5.0, 0.1)])
    assert transmission_baies(groupe) == pytest.approx(4 * 1.3 + 2 * 1.5)
    assert transmission_parois(groupe) == pytest.approx(20 * 0.25 + 50 * 0.5 * 0.20)
    assert transmission_ponts(groupe) == pytest.approx(30 * 0.3 + 5 * 0.1)
    assert transmission_ponts(Groupe("Vide", 50.0)) == 0
