"""Interface (0.8.18, 0.9.0) : la boîte et son projet, l'axonométrie, les briques, la comparaison de deux
variantes et la page entière."""

import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from config.reglages import RACINE
from interface.axonometrie import VUES, Projection, decouper_baies, dessiner, direction
from interface.comparaison import LIBELLES, differences, ecarts
from interface.saisie import (CLE_GROUPE, PART_VITREE_MAX, Boite, construire_projet, gabarit_baie, largeur_travee,
                              point_cardinal)
from moteur.hypotheses import hyp


def _groupe(boite):
    return construire_projet(boite).batiments[0].groupes[0]


# ============================================================
# SAISIE : de la boîte au projet
# ============================================================
def test_boite_de_depart_surfaces_et_orientations():
    boite = Boite()
    groupe = _groupe(boite)
    # 20 m × 12 m × 3 niveaux × 0,8 de part habitable
    assert groupe.surface_m2 == pytest.approx(576.0)
    assert groupe.volume_m3 == pytest.approx(576.0 * boite.hauteur_sous_plafond_m)
    # Murs et baies se partagent chaque façade ; toiture et plancher valent l'emprise
    facades = 2 * (20.0 + 12.0) * boite.hauteur_m
    murs = sum(p.surface_m2 for p in groupe.parois if p.type == "mur")
    assert murs + groupe.surface_baies_m2 == pytest.approx(facades)
    assert [p.surface_m2 for p in groupe.parois if p.type != "mur"] == [240.0, 240.0]
    # Façade principale au sud : les baies tournent dans l'ordre sud, ouest, nord, est
    assert [b.orientation_deg for b in groupe.baies] == [0.0, 90.0, -180.0, -90.0]
    assert groupe.baies[0].surface_m2 == pytest.approx(20.0 * boite.hauteur_m * boite.part_vitree_principale)
    assert (construire_projet(boite).batiments[0].nom, "Logements", groupe.nom) == CLE_GROUPE


def test_orientation_tourne_toutes_les_facades():
    groupe = _groupe(replace(Boite(), orientation_deg=135.0))
    assert [b.orientation_deg for b in groupe.baies] == [135.0, -135.0, -45.0, 45.0]
    assert point_cardinal(135.0) == "nord-ouest" and point_cardinal(-180.0) == "nord"
    assert point_cardinal(350.0) == "sud" and point_cardinal(-80.0) == "est"


def test_options_de_la_boite():
    # Façade aveugle : pas de baie ; sans protection ni ouverture : le moteur le saura
    groupe = _groupe(replace(Boite(), part_vitree_arriere=0.0, protection="aucune", ouvrable=False))
    assert len(groupe.baies) == 3
    assert all(b.protection is None and not b.ouvrable for b in groupe.baies)
    # Teinte : absorption lue dans les hypothèses ; plancher sur l'extérieur ; étanchéité parfaite
    groupe = _groupe(replace(Boite(), teinte="sombre", plancher_sur_sol=False, permeabilite_q4pa=0.0,
                             psi_planchers=0.0))
    assert groupe.parois[0].alpha == hyp("alpha_teinte_sombre") == 0.8
    assert groupe.parois[-1].contact == "exterieur"
    assert groupe.permeabilite_q4pa is None and groupe.ponts_thermiques == []
    # Ponts thermiques : une rive par plancher, sur tout le périmètre
    assert _groupe(Boite()).ponts_thermiques[0].longueur_m == pytest.approx(64.0 * 4)
    # Brasseurs : surface desservie plafonnée (15 m² par brasseur, sans dépasser la surface habitable)
    brasseur = _groupe(replace(Boite(), brasseurs=True)).brasseurs[0]
    assert brasseur.nombre == 18 and brasseur.surface_desservie_m2 == pytest.approx(270.0)
    assert _groupe(replace(Boite(), brasseurs=True, brasseurs_par_logement=6)).brasseurs[0] \
        .surface_desservie_m2 == pytest.approx(576.0)


def test_saisies_refusees_en_clair():
    with pytest.raises(ValueError, match="part vitrée"):
        construire_projet(replace(Boite(), part_vitree_principale=PART_VITREE_MAX + 0.05))
    with pytest.raises(ValueError, match="climatisé"):
        construire_projet(replace(Boite(), brasseurs=True, climatise=True))


def test_balcons_masque_et_gabarit():
    """Un balcon devient un débord horizontal au-dessus des baies des façades choisies (fiche 3.2)."""
    # Gabarit : la baie, son allège et son linteau remplissent la hauteur d'étage
    fh, hauteur, allege, linteau = gabarit_baie(0.30, 2.8)
    assert hauteur + allege + linteau == pytest.approx(2.8) and hauteur == pytest.approx(fh * 2.8)
    assert largeur_travee(20.0) == pytest.approx(20.0 / 7) and largeur_travee(2.0) == 2.0
    # Sans balcon (boîte de départ) : aucun masque
    assert all(b.masques == [] for b in _groupe(Boite()).baies)
    groupe = _groupe(replace(Boite(), debord_m=1.2, facades_debord=("principale", "pignon_b")))
    assert [len(b.masques) for b in groupe.baies] == [1, 0, 0, 1]
    masque, baie = groupe.baies[0].masques[0], groupe.baies[0]
    assert masque.debord_m == 1.2 and masque.distance_m == pytest.approx(linteau)
    assert baie.hauteur_m == pytest.approx(hauteur)
    # La surface de la façade principale se retrouve : baies de (largeur × hauteur) par travée et par niveau
    assert baie.largeur_m * baie.hauteur_m * 7 * 3 == pytest.approx(baie.surface_m2)
    with pytest.raises(ValueError, match="balcons"):
        construire_projet(replace(Boite(), debord_m=5.0))
    with pytest.raises(ValueError, match="inconnues"):
        construire_projet(replace(Boite(), debord_m=1.0, facades_debord=("toit",)))


def test_boite_figee_et_comparable():
    """Deux boîtes égales sont la même clé de cache ; une boîte ne se modifie pas en place."""
    assert Boite() == Boite() and hash(Boite()) == hash(Boite())
    assert replace(Boite(), nb_niveaux=4) != Boite()
    with pytest.raises(Exception):
        Boite().nb_niveaux = 4


# ============================================================
# AXONOMÉTRIE
# ============================================================
def test_projection_et_facades_visibles():
    # Spectateur au sud : l'est est à droite, le nord s'éloigne (monte à l'écran), la hauteur monte
    proj = Projection(0.0)
    assert proj.point(1, 0)[0] > 0 and proj.point(0, 1)[1] < 0 and proj.point(0, 0, 1)[1] < 0
    assert direction(0.0) == pytest.approx((0.0, -1.0)) and direction(90.0) == pytest.approx((-1.0, 0.0))
    # Du sud-ouest, on voit les façades sud et ouest, pas les autres
    proj = Projection(VUES["sud-ouest"])
    assert [proj.voit(direction(a)) for a in (0.0, 90.0, 180.0, -90.0)] == [True, True, False, False]


@pytest.mark.parametrize("part", [0.05, 0.3, 0.6, 0.9])
def test_baies_dessinees_a_l_echelle(part):
    rectangles = decouper_baies(part, largeur_m=20.0, nb_niveaux=3, hauteur_etage_m=2.8)
    surface = sum((u1 - u0) * (z1 - z0) for u0, u1, z0, z1 in rectangles)
    assert surface == pytest.approx(part * 20.0 * 3 * 2.8)
    assert all(-10.0 <= u0 < u1 <= 10.0 and 0.0 <= z0 < z1 <= 8.4 for u0, u1, z0, z1 in rectangles)
    assert decouper_baies(0.0, 20.0, 3, 2.8) == []


@pytest.mark.parametrize("vue", list(VUES))
def test_svg_valide_dans_toutes_les_vues(vue):
    boite = replace(Boite(), orientation_deg=30.0, nb_niveaux=6, teinte="sombre")
    svg = dessiner(boite, VUES[vue])
    assert svg.startswith("<svg xmlns=")
    racine = ET.fromstring(svg)
    espace = "{http://www.w3.org/2000/svg}"
    # Sol, deux façades et la toiture au moins ; chaque point reste dans le cadre
    polygones = racine.findall(f"{espace}polygon")
    assert len(polygones) > 4
    for polygone in polygones:
        for point in polygone.get("points").split():
            x, y = (float(v) for v in point.split(","))
            assert -1 <= x <= 721 and -1 <= y <= 471 and math.isfinite(x + y)
    # Deux façades étiquetées, quatre points cardinaux
    textes = [t.text for t in racine.findall(f"{espace}text")]
    assert sum("%" in t for t in textes) == 2 and {"N", "S", "E", "O"} <= set(textes)


def test_balcons_dessines_et_etiquettes_couchees():
    espace = "{http://www.w3.org/2000/svg}"
    sans = ET.fromstring(dessiner(Boite()))
    avec = ET.fromstring(dessiner(replace(Boite(), debord_m=1.5, facades_debord=("principale", "arriere"))))
    # Du sud-ouest, seule la façade principale est visible : une dalle par niveau
    assert len(avec.findall(f"{espace}polygon")) - len(sans.findall(f"{espace}polygon")) == Boite().nb_niveaux
    # Les deux étiquettes de façade suivent le pied de leur façade
    assert sum("rotate(" in t.get("transform", "") for t in sans.findall(f"{espace}text")) == 2


# ============================================================
# COMPARAISON DE DEUX VARIANTES
# ============================================================
def test_differences_de_saisie():
    from dataclasses import fields
    assert set(LIBELLES) == {champ.name for champ in fields(Boite)}        # chaque saisie a son libellé
    assert differences(Boite(), Boite()) == []
    variante = replace(Boite(), uw=1.1, orientation_deg=90.0, traversant=False, part_vitree_arriere=0.35)
    assert differences(Boite(), variante) == [
        ("Orientation de la façade principale", "sud", "ouest"), ("Logements traversants", "oui", "non"),
        ("Part vitrée, façade arrière", "20 %", "35 %"), ("Uw des baies", "1,4 W/m².K", "1,1 W/m².K")]
    # Un réglage sans effet des deux côtés n'est pas listé ; il l'est dès que son option est allumée
    assert differences(Boite(), replace(Boite(), brasseur_debit_m3h=9000.0)) == []
    assert len(differences(replace(Boite(), brasseurs=True),
                           replace(Boite(), brasseurs=True, brasseur_debit_m3h=9000.0))) == 1
    assert differences(Boite(), replace(Boite(), debord_m=1.0, facades_debord=("principale", "pignon_a"))) == [
        ("Balcons ou casquettes", "0,0 m", "1,0 m"),
        ("Façades à balcons", "façade principale", "façade principale, pignon a")]


# ============================================================
# BRIQUES
# ============================================================
def test_briques_completes_et_code_lisible():
    import inspect

    from interface.briques import BRIQUES
    assert len({b.cle for b in BRIQUES}) == len(BRIQUES) >= 3
    for brique in BRIQUES:
        assert brique.titre and brique.phenomene and brique.equation and brique.lecture and brique.reference
        assert brique.icone.startswith(":material/") and callable(brique.afficher)
        assert brique.reperes() and all(isinstance(r, str) for r in brique.reperes())
        # Le volet montre le code du moteur, lu à la source
        assert brique.code and all(f.__module__.startswith("moteur.") and inspect.getsource(f)
                                   for f in brique.code)


def test_moteur_ignore_l_interface():
    """Le moteur ne dépend jamais de l'interface : l'importer ne charge ni interface ni streamlit."""
    code = ("import sys, moteur.bbio, moteur.dh; "
            "print(any(m.split('.')[0] in ('interface', 'streamlit') for m in sys.modules))")
    sortie = subprocess.run([sys.executable, "-c", code], cwd=RACINE, capture_output=True, text=True, check=True)
    assert sortie.stdout.strip() == "False"


# ============================================================
# CALCUL ET PAGE (un calcul complet : quelques secondes)
# ============================================================
@pytest.fixture(scope="module")
def resultats():
    from interface.calcul import calculer
    return calculer(replace(Boite(), permeabilite_q4pa=0.0))       # sans infiltrations : deux fois plus rapide


def test_calcul_de_la_boite(resultats):
    r = resultats
    assert r.bbio["bbio"] == pytest.approx(hyp("bbio_coef_chauffage") * r.bbio["b_ch"]
                                           + hyp("bbio_coef_refroidissement") * r.bbio["b_fr"]
                                           + hyp("bbio_coef_eclairage") * r.bbio["b_ecl"])
    assert len(r.mensuel) == 12 and r.mensuel["bbio"].sum() == pytest.approx(r.bbio["bbio"])
    assert len(r.ete) == 8760 and r.ete["dh_horaire"].sum() == pytest.approx(r.dh["dh"])
    # Heure légale : 1 h entre deux pas, sauf aux deux changements d'heure (2 h, puis 0 h)
    ecarts = r.ete["date"].diff().dt.total_seconds().dropna() / 3600.0
    assert sorted(ecarts.unique()) == [0.0, 1.0, 2.0] and (ecarts != 1.0).sum() == 2
    assert r.ete["date"].iloc[0].hour == 1 and r.ete["date"].iloc[4500].hour == 14
    assert r.dh["avertissement"] == ""


def test_semaine_la_plus_chaude(resultats):
    from interface.briques.dh import par_jour
    from interface.briques.semaine_chaude import extraire_semaine
    semaine = extraire_semaine(resultats.ete)
    assert len(semaine) == 168
    # Aucune autre fenêtre de sept jours entiers ne compte plus de degrés-heures
    par_jours = resultats.ete["dh_horaire"].to_numpy().reshape(-1, 24).sum(axis=1)
    assert semaine["dh_horaire"].sum() == pytest.approx(max(par_jours[j:j + 7].sum() for j in range(358)))
    # Le décalage reste dans l'année
    assert len(extraire_semaine(resultats.ete, 400)) == 168 and len(extraire_semaine(resultats.ete, -400)) == 168
    assert par_jour(resultats.ete)["dh"].sum() == pytest.approx(resultats.dh["dh"])


def test_ecarts_entre_deux_calculs(resultats):
    from copy import deepcopy
    variante = deepcopy(resultats)
    variante.bbio["bbio"] = resultats.bbio["bbio"] * 0.9
    variante.dh["dh"] = resultats.dh["dh"] + 100.0
    lignes = {ligne["indicateur"]: ligne for ligne in ecarts(resultats, variante)}
    assert lignes["Bbio"]["ecart_pct"] == pytest.approx(-10.0)
    assert lignes["DH"]["ecart"] == pytest.approx(100.0) and lignes["Chauffage"]["ecart"] == 0.0
    assert all(ligne["ecart"] == 0.0 for ligne in ecarts(resultats, resultats))


def test_page_entiere(resultats, monkeypatch):
    """La page s'affiche, chaque brique aussi, et une saisie modifiée attend le bouton « Calculer »."""
    from streamlit.testing.v1 import AppTest

    import interface.calcul
    monkeypatch.setattr(interface.calcul, "calculer", lambda boite: resultats)      # pas de second calcul
    page = AppTest.from_file(os.path.join(RACINE, "app.py"), default_timeout=60).run()
    assert not page.exception
    assert [m.label for m in page.metric][:4] == ["Surface habitable", "Baies / surface habitable", "Bbio", "DH"]
    assert page.button(key="calculer").disabled and not page.warning

    from interface.briques import BRIQUES
    for brique in BRIQUES:
        page.session_state["brique"] = brique.cle
        page.run()
        assert not page.exception and page.subheader[-1].value == brique.titre

    # Saisie modifiée : le dessin suit, les résultats attendent
    page.slider(key="nb_niveaux").set_value(5).run()
    assert not page.exception and not page.button(key="calculer").disabled
    assert any("calcul précédent" in w.value for w in page.warning)
    assert page.metric[0].value.startswith("960")
    page.button(key="calculer").click().run()
    assert not page.exception and page.button(key="calculer").disabled

    # Référence : gardée, puis comparée à une variante avec balcons ; le second bouton « Calculer » sert aussi
    assert not page.dataframe
    page.button(key="garder_reference").click().run()
    assert page.button(key="garder_reference").disabled and any("référence" in i.value for i in page.info)
    page.slider(key="debord_m").set_value(1.5).run()
    page.button(key="calculer_ici").click().run()
    assert not page.exception and not page.warning and len(page.dataframe) == 1
    assert any("Balcons ou casquettes" in m.value for m in page.markdown)
    page.button(key="oublier_reference").click().run()
    assert not page.exception and not page.dataframe and "reference" not in page.session_state
