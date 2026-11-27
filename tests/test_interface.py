"""Interface (0.8.18, 0.9.0, 0.9.1, 0.9.2, 0.9.4) : la boîte et son projet, les bâtiments de départ (lus dans
donnees/batiments/), les niveaux d'enveloppe, l'axonométrie, les briques, la comparaison de deux variantes, le
choix du calcul et la page entière.

L'immeuble de 9 logements fait 576 m² ; depuis la 0.9.4, ses pignons sont aveugles : les tests qui suivent les
quatre façades emploient QUATRE_FACADES, l'immeuble vitré comme en 0.9.0."""

import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import fields, replace

import pytest

from config.reglages import RACINE
from interface.axonometrie import VUES, Projection, decouper_baies, dessiner, direction
from interface.comparaison import LIBELLES, differences, ecarts
from config.reglages import DOSSIER_BATIMENTS
from interface.saisie import (BATIMENTS_DE_DEPART, CHAMPS_TYPOLOGIES, CLE_GROUPE, NIVEAUX_ENVELOPPE,
                              PART_VITREE_MAX, Boite, boite_de_depart, construire_projet, gabarit_baie,
                              largeur_travee, lire_batiment, lire_batiments, lire_niveaux_enveloppe,
                              point_cardinal)
from moteur.hypotheses import hyp

IMMEUBLE = BATIMENTS_DE_DEPART["Immeuble de 9 logements"]
# Les parts vitrées de la 0.9.0 (30, 10, 20 et 10 %), sur lesquelles les tests de géométrie ont été écrits
QUATRE_FACADES = replace(IMMEUBLE, part_vitree_principale=0.30, part_vitree_pignon_a=0.10,
                         part_vitree_arriere=0.20, part_vitree_pignon_b=0.10)


def _groupe(boite):
    return construire_projet(boite).batiments[0].groupes[0]


# ============================================================
# SAISIE : de la boîte au projet
# ============================================================
def test_boite_de_depart_surfaces_et_orientations():
    boite = QUATRE_FACADES
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


def test_batiments_de_depart():
    """Le logement de 70 m² est la boîte par défaut ; l'immeuble ne change que la forme."""
    assert list(BATIMENTS_DE_DEPART) == ["Logement de 70 m²", "Immeuble de 9 logements"]
    logement = BATIMENTS_DE_DEPART["Logement de 70 m²"]
    assert next(iter(BATIMENTS_DE_DEPART.values())) == logement == Boite()
    # 7 m de façade principale sur 10 m de profondeur, en H1a, vitré à 25 % devant et derrière, pignons aveugles
    assert (logement.zone_climatique, logement.longueur_m, logement.profondeur_m) == ("H1a", 7.0, 10.0)
    assert logement.gestion_protection == "manuelle_motorisee"
    groupe = _groupe(logement)
    assert groupe.surface_m2 == pytest.approx(70.0) and groupe.nb_logements == 1
    assert [p.surface_m2 for p in groupe.parois if p.type != "mur"] == [70.0, 70.0]
    assert [b.orientation_deg for b in groupe.baies] == [0.0, -180.0]
    assert groupe.surface_baies_m2 == pytest.approx(2 * 7.0 * 2.8 * 0.25)
    assert _groupe(IMMEUBLE).surface_m2 == pytest.approx(576.0)
    changes = {c.name for c in fields(Boite) if getattr(logement, c.name) != getattr(IMMEUBLE, c.name)}
    assert changes == {"longueur_m", "profondeur_m", "nb_niveaux", "part_habitable", "nb_logements"}


def test_batiments_lus_dans_les_csv(tmp_path):
    """Un CSV par bâtiment : les deux fichiers fournis sont complets ; un champ absent prend la valeur par défaut ;
    l'enveloppe, un champ inconnu ou une valeur illisible sont refusés en nommant le fichier et la ligne."""
    # Fichiers fournis : toutes les saisies hors enveloppe, pour servir de modèle
    hors_enveloppe = {c.name for c in fields(Boite)} - set(CHAMPS_TYPOLOGIES.values())
    for fichier in sorted(os.listdir(DOSSIER_BATIMENTS)):
        if fichier.endswith(".csv"):
            with open(os.path.join(DOSSIER_BATIMENTS, fichier), encoding="utf-8") as f:
                champs = {ligne.split(";")[0] for ligne in f.read().splitlines()[1:]}
            assert champs == hors_enveloppe | {"nom"}, fichier

    entete = "champ;valeur;unite;description\n"

    def ecrire(nom_fichier, lignes):
        chemin = tmp_path / nom_fichier
        chemin.write_text(entete + lignes, encoding="utf-8")
        return chemin

    # Un bâtiment réduit à trois lignes : le reste vient de Boite ; virgule décimale, oui / non, liste
    chemin = ecrire("b_maison.csv", "nom;Maison;;\nhauteur_etage_m;3,1;m;\nnb_niveaux;2;;\ntraversant;non;;\n"
                                    "\n" "facades_debord;principale, arriere;;\n")
    assert lire_batiment(chemin) == ("Maison", replace(Boite(), hauteur_etage_m=3.1, nb_niveaux=2,
                                                       traversant=False, facades_debord=("principale", "arriere")))
    # Ordre alphabétique des fichiers ; les fichiers d'un autre type sont ignorés
    ecrire("a_studio.csv", "nom;Studio;;\nlongueur_m;6;m;\n")
    (tmp_path / "notes.txt").write_text("rien", encoding="utf-8")
    assert list(lire_batiments(tmp_path)) == ["Studio", "Maison"]
    ecrire("c_double.csv", "nom;Studio;;\n")
    with pytest.raises(ValueError, match="déjà pris"):
        lire_batiments(tmp_path)

    # Refus en clair
    refus = {"nom;X;;\nuw;1,2;;\n": "c.csv, ligne 3 : « uw » fait partie de l'enveloppe",
             "nom;X;;\nlargeur_m;7;;\n": "ligne 3 : champ inconnu « largeur_m »",
             "nom;X;;\nnb_niveaux;1,5;;\n": "valeur illisible pour « nb_niveaux »",
             "nom;X;;\ntraversant;vrai;;\n": "écrire oui ou non",
             "nom;X;;\nlongueur_m;7;;\nlongueur_m;8;;\n": "« longueur_m » écrit deux fois",
             "longueur_m;7;;\n": "ligne « nom » absente",
             "nom;X;;\nzone_climatique;H1;;\n": "zone climatique inconnue « H1 »",
             "nom;X;;\npart_vitree_principale;0,95;;\n": "c.csv : Façade principale : la part vitrée",
             "nom;X;;\nteinte;rose;;\n": "valeur inconnue 'rose'"}
    for lignes, message in refus.items():
        with pytest.raises(ValueError, match=message):
            lire_batiment(ecrire("c.csv", lignes))
    (tmp_path / "d.csv").write_text("champ,valeur\nnom,X\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colonnes"):
        lire_batiment(tmp_path / "d.csv")


def test_batiment_ecrit_puis_relu(tmp_path):
    """0.9.8 : « Télécharger ce bâtiment » écrit un CSV que lire_batiment relit à l'identique, enveloppe exceptée."""
    from interface.saisie import ecrire_batiment
    enveloppe = set(CHAMPS_TYPOLOGIES.values())
    variante = replace(IMMEUBLE, orientation_deg=-90.0, debord_m=1.2, facades_debord=("principale", "pignon_b"),
                       traversant=False, brasseurs=True, altitude_m=437.5, hauteur_etage_m=2.95, uw=0.9)
    for boite in (*BATIMENTS_DE_DEPART.values(), variante):
        chemin = tmp_path / "03_mon_batiment.csv"
        chemin.write_text(ecrire_batiment(boite, "Ma variante"), encoding="utf-8")
        nom, relue = lire_batiment(chemin)
        assert nom == "Ma variante"
        assert all(getattr(relue, c.name) == getattr(boite, c.name) for c in fields(Boite) if c.name not in enveloppe)
        assert relue.uw == Boite().uw                       # l'enveloppe vient du niveau, pas du fichier
    texte = ecrire_batiment(variante, "Ma variante")
    assert "altitude_m;437,5;m;" in texte and "facades_debord;principale, pignon_b;" in texte
    assert "traversant;non;" in texte and "\nuw;" not in texte


def test_traversant_selon_les_baies():
    """0.9.36 : la règle des 75 % ; elle décide pour un logement, et pour plusieurs si une seule façade est vitrée."""
    logement = Boite()                                                  # 25 % devant et derrière : 50 / 50
    assert logement.traversant_impose is True and replace(logement, traversant=False).traversant
    # Une seule façade, ou aucune baie : non traversant
    for devant in (0.25, 0.0):
        seule = replace(logement, part_vitree_principale=devant, part_vitree_arriere=0.0)
        assert seule.traversant_impose is False and not seule.traversant and not _groupe(seule).traversant
    # Seuil : 75 % pile n'est pas traversant, un peu moins l'est
    assert not replace(logement, part_vitree_principale=0.15, part_vitree_arriere=0.05).traversant
    assert replace(logement, part_vitree_principale=0.14, part_vitree_arriere=0.05).traversant
    # La surface compte, pas la part vitrée : façade de 7 m et pignon de 10 m à 25 % chacun, façades perpendiculaires
    assert replace(logement, part_vitree_arriere=0.0, part_vitree_pignon_a=0.25).traversant
    # Une façade adiabatique n'a pas de baie
    assert not replace(logement, parois_adiabatiques=("arriere",)).traversant
    # Plusieurs logements : libre avec deux façades vitrées (même à 75 % ou plus), imposé avec une seule
    plusieurs = replace(logement, nb_logements=4, part_vitree_principale=0.60, part_vitree_arriere=0.05)
    assert plusieurs.traversant_impose is None and not plusieurs.traversant_selon_les_baies
    assert replace(plusieurs, traversant=True).traversant and not replace(plusieurs, traversant=False).traversant
    assert replace(plusieurs, part_vitree_arriere=0.0).traversant is False


def test_traversant_dans_la_page(resultats, monkeypatch):
    """0.9.36 : sans interrupteur pour un logement ; grisé avec une seule façade ; sinon libre, remis à la règle
    quand les baies changent son verdict."""
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    import interface.calcul
    monkeypatch.setattr(interface.calcul, "resultats_dh", lambda boite: {"dh": resultats.dh, "ete": resultats.ete})
    page = AppTest.from_file(os.path.join(RACINE, "app.py"), default_timeout=60).run()
    page.button(key="accueil_explorer").click().run()
    verdict = lambda: next(m.value for m in page.markdown if m.value.startswith("Logement traversant"))
    assert "oui" in verdict() and "traversant" not in [t.key for t in page.toggle]
    page.slider(key="part_vitree_arriere").set_value(0).run()
    assert not page.exception and "non" in verdict()
    # Plusieurs logements, une seule façade : grisé
    page.number_input(key="nb_logements").set_value(4).run()
    assert not page.exception and page.toggle(key="traversant").disabled and not page.toggle(key="traversant").value
    # Deux façades : libre, à la valeur de la règle ; le choix à la main tient tant que le verdict ne change pas
    page.slider(key="part_vitree_arriere").set_value(25).run()
    assert not page.toggle(key="traversant").disabled and page.toggle(key="traversant").value
    page.toggle(key="traversant").set_value(False).run()
    page.slider(key="part_vitree_arriere").set_value(30).run()
    assert not page.exception and not page.toggle(key="traversant").value
    page.slider(key="part_vitree_arriere").set_value(5).run()           # 83 % au sud : la règle passe à non
    page.slider(key="part_vitree_arriere").set_value(25).run()          # puis à oui
    assert page.toggle(key="traversant").value
    # Changer de bâtiment reprend sa valeur
    page.toggle(key="traversant").set_value(False).run()
    page.selectbox(key="batiment_depart").set_value("Immeuble de 9 logements").run()
    assert not page.exception and page.toggle(key="traversant").value
    st.cache_data.clear()                   # ses calculs simulés ne servent pas aux tests suivants


def test_niveaux_d_enveloppe(tmp_path):
    """Trois niveaux lus dans donnees/typologies_logements.csv, chacun pour les 13 saisies d'enveloppe."""
    assert list(NIVEAUX_ENVELOPPE) == ["Performant", "Moyen", "Faible"]
    performant, moyen, faible = NIVEAUX_ENVELOPPE.values()
    assert all(set(n) == set(CHAMPS_TYPOLOGIES.values()) for n in NIVEAUX_ENVELOPPE.values())
    assert len(moyen) == 13 and set(moyen) <= {champ.name for champ in fields(Boite)}
    # Valeurs du CSV (virgule décimale, classes d'inertie traduites)
    assert (performant["uw"], moyen["uw"], faible["uw"]) == (1.2, 1.3, 1.4)
    assert moyen["sw"] == 0.4 and moyen["psi_planchers"] == 0.22 and moyen["ratio_ouverture_max"] == 0.78
    assert (performant["inertie"], moyen["inertie"]) == ("tres_lourde", "lourde")
    # Sens : U plus bas et ventilation plus forte du côté performant
    for champ in ("uw", "u_mur", "u_toiture", "u_plancher", "psi_planchers"):
        assert performant[champ] <= moyen[champ] <= faible[champ]
    assert performant["debit_ventilation_m3h_m2"] >= faible["debit_ventilation_m3h_m2"]
    # Boîte de départ : la forme du bâtiment, l'enveloppe du niveau ; le projet se construit
    for nom in BATIMENTS_DE_DEPART:
        for niveau, champs in NIVEAUX_ENVELOPPE.items():
            boite = boite_de_depart(nom, niveau)
            assert all(getattr(boite, c) == v for c, v in champs.items())
            assert boite.longueur_m == BATIMENTS_DE_DEPART[nom].longueur_m
            assert _groupe(boite).inertie_quotidienne == champs["inertie"]
    assert boite_de_depart() == boite_de_depart("Logement de 70 m²", "Moyen")
    # Un CSV qui ne correspond plus aux champs est refusé en clair
    chemin = tmp_path / "typologies.csv"
    chemin.write_text("variable;colonne_source;unite;sens;n_zones;n_operations;performant;moyen;faible;remarque\n"
                      "X;inconnue;-;-;1;1;1;1;1;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inconnue"):
        lire_niveaux_enveloppe(chemin)
    chemin.write_text("variable;colonne_source;unite;sens;n_zones;n_operations;performant;moyen;faible;remarque\n"
                      "Uw;uw;W/m².K;-;1;1;1,3;1,4;1,5;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="champs absents"):
        lire_niveaux_enveloppe(chemin)


def test_orientation_tourne_toutes_les_facades():
    groupe = _groupe(replace(QUATRE_FACADES, orientation_deg=135.0))
    assert [b.orientation_deg for b in groupe.baies] == [135.0, -135.0, -45.0, 45.0]
    assert point_cardinal(135.0) == "nord-ouest" and point_cardinal(-180.0) == "nord"
    assert point_cardinal(350.0) == "sud" and point_cardinal(-80.0) == "est"


def test_options_de_la_boite():
    # Façade aveugle : pas de baie ; sans protection ni ouverture : le moteur le saura
    groupe = _groupe(replace(QUATRE_FACADES, part_vitree_arriere=0.0, protection="aucune", ouvrable=False))
    assert len(groupe.baies) == 3
    assert all(b.protection is None and not b.ouvrable for b in groupe.baies)
    # Protection (0.9.13, guide Actibaie) : un volet laisse passer 10 % de l'air (Typo_PM 1) et son Sw protégé est
    # tout réémis (Sw1 = 0) ; un store en toile en réémet 40 %
    volet = _groupe(replace(IMMEUBLE, sw_protege=0.05)).baies[0]
    assert volet.typo_permeabilite_protection == 1 and volet.sw2_protege == pytest.approx(0.05)
    store = _groupe(replace(IMMEUBLE, protection="store_enroulable", sw_protege=0.1)).baies[0]
    assert store.typo_permeabilite_protection == 1 and store.sw2_protege == pytest.approx(0.04)
    # Teinte : absorption lue dans les hypothèses ; plancher sur l'extérieur ; étanchéité parfaite
    groupe = _groupe(replace(IMMEUBLE, teinte="sombre", plancher_sur_sol=False, permeabilite_q4pa=0.0,
                             psi_planchers=0.0))
    assert groupe.parois[0].alpha == hyp("alpha_teinte_sombre") == 0.8
    assert groupe.parois[-1].contact == "exterieur"
    assert groupe.permeabilite_q4pa is None and groupe.ponts_thermiques == []
    # Ponts thermiques : une rive par plancher, sur tout le périmètre
    assert _groupe(IMMEUBLE).ponts_thermiques[0].longueur_m == pytest.approx(64.0 * 4)
    # Brasseurs : surface desservie plafonnée (15 m² par brasseur, sans dépasser la surface habitable)
    brasseur = _groupe(replace(IMMEUBLE, brasseurs=True)).brasseurs[0]
    assert brasseur.nombre == 18 and brasseur.surface_desservie_m2 == pytest.approx(270.0)
    assert _groupe(replace(IMMEUBLE, brasseurs=True, brasseurs_par_logement=6)).brasseurs[0] \
        .surface_desservie_m2 == pytest.approx(576.0)


def test_saisies_refusees_en_clair():
    with pytest.raises(ValueError, match="part vitrée"):
        construire_projet(replace(IMMEUBLE, part_vitree_principale=PART_VITREE_MAX + 0.05))
    with pytest.raises(ValueError, match="climatisé"):
        construire_projet(replace(IMMEUBLE, brasseurs=True, climatise=True))


def test_balcons_masque_et_gabarit():
    """Un balcon devient un débord horizontal au-dessus des baies des façades choisies (fiche 3.2)."""
    # Gabarit : la baie, son allège et son linteau remplissent la hauteur d'étage
    fh, hauteur, allege, linteau = gabarit_baie(0.30, 2.8)
    assert hauteur + allege + linteau == pytest.approx(2.8) and hauteur == pytest.approx(fh * 2.8)
    assert largeur_travee(20.0) == pytest.approx(20.0 / 7) and largeur_travee(2.0) == 2.0
    # Sans balcon (boîte de départ) : aucun masque
    assert all(b.masques == [] for b in _groupe(IMMEUBLE).baies)
    groupe = _groupe(replace(QUATRE_FACADES, debord_m=1.2, facades_debord=("principale", "pignon_b")))
    assert [len(b.masques) for b in groupe.baies] == [1, 0, 0, 1]
    masque, baie = groupe.baies[0].masques[0], groupe.baies[0]
    assert masque.debord_m == 1.2 and masque.distance_m == pytest.approx(linteau)
    assert baie.hauteur_m == pytest.approx(hauteur)
    # La surface de la façade principale se retrouve : baies de (largeur × hauteur) par travée et par niveau
    assert baie.largeur_m * baie.hauteur_m * 7 * 3 == pytest.approx(baie.surface_m2)
    with pytest.raises(ValueError, match="balcons"):
        construire_projet(replace(IMMEUBLE, debord_m=5.0))
    with pytest.raises(ValueError, match="inconnues"):
        construire_projet(replace(IMMEUBLE, debord_m=1.0, facades_debord=("toit",)))


def test_parois_adiabatiques():
    """0.9.16 : une paroi sur un local chauffé n'entre pas dans le groupe (hypothèse 101) ; une façade adiabatique
    n'a ni baie ni rive de plancher ; toiture et plancher bas gardent leur rive."""
    boite = replace(QUATRE_FACADES, parois_adiabatiques=("pignon_a", "toiture"))
    groupe = _groupe(boite)
    assert [p.nom.split(" — ")[0] for p in groupe.parois] == ["Mur", "Mur", "Mur", "Plancher bas"]
    assert all("Pignon A" not in p.nom for p in groupe.parois) and len(groupe.baies) == 3
    facade = next(f for f in boite.facades() if f["cle"] == "pignon_a")
    assert facade["adiabatique"] and facade["part_vitree"] == 0.0 and facade["baies_m2"] == 0.0
    assert boite.part_vitree_pignon_a == 0.10                   # la saisie est gardée pour le jour où on décoche
    # Rives : 64 m de périmètre moins les 12 m du pignon, sur les quatre planchers (toiture comprise)
    assert groupe.ponts_thermiques[0].longueur_m == pytest.approx((64.0 - 12.0) * 4)
    # Perméabilité : la façade et la toiture adiabatiques sortent des surfaces perméables
    from moteur.infiltrations import surfaces_permeables
    facade_m2, toit_m2 = surfaces_permeables(groupe)
    assert toit_m2 == 0.0 and facade_m2 == pytest.approx((64.0 - 12.0) * boite.hauteur_m)
    # Logement entre deux étages, entre deux voisins : façades avant et arrière seules
    milieu = replace(IMMEUBLE, parois_adiabatiques=("pignon_a", "pignon_b", "toiture", "plancher_bas"))
    assert {p.type for p in _groupe(milieu).parois} == {"mur"}
    with pytest.raises(ValueError, match="adiabatiques inconnues"):
        construire_projet(replace(IMMEUBLE, parois_adiabatiques=("cave",)))
    # Lu et écrit dans un CSV de bâtiment ; dessiné en gris, nommé dans le titre
    from interface import charte
    from interface.saisie import ecrire_batiment
    assert "parois_adiabatiques;pignon_a, toiture;" in ecrire_batiment(boite, "X")
    svg = dessiner(replace(boite, orientation_deg=0.0), VUES["sud-ouest"])
    assert charte.GRIS_ADIABATIQUE in svg                   # pignon A, à l'ouest, au soleil de 16 h
    racine = ET.fromstring(svg)
    textes = [t.text for t in racine.iter("{http://www.w3.org/2000/svg}text")]
    assert any(t.startswith("Pignon A") and t.endswith("adiabatique") for t in textes)
    assert "parois adiabatiques : pignon a, toiture" in racine.find("{http://www.w3.org/2000/svg}title").text


def test_orientation_par_pas_de_10_degres():
    """0.9.16 : saisie en azimut géographique (0 nord, 90 est), le moteur garde 0 = sud, 90 = ouest."""
    from interface.formulaire import ORIENTATIONS, _azimut_du_curseur, valeurs_des_widgets
    from interface.saisie import azimut_geographique, libelle_orientation, orientation_moteur
    assert len(ORIENTATIONS) == 36 and ORIENTATIONS[18] == 180
    for moteur, geo in ((0.0, 180.0), (90.0, 270.0), (-90.0, 90.0), (180.0, 0.0), (20.0, 200.0)):
        assert azimut_geographique(moteur) == geo and orientation_moteur(geo) == pytest.approx(
            moteur if moteur != 180.0 else -180.0)
    assert libelle_orientation(20.0) == "200° · sud" and libelle_orientation(-90.0) == "90° · est"
    assert _azimut_du_curseur(-176.0) == 0 and _azimut_du_curseur(13.0) == 190
    assert valeurs_des_widgets(replace(IMMEUBLE, orientation_deg=-30.0))["orientation"] == 150
    # Une orientation hors des huit points cardinaux tourne les quatre façades
    groupe = _groupe(replace(QUATRE_FACADES, orientation_deg=20.0))
    assert [b.orientation_deg for b in groupe.baies] == [20.0, 110.0, -160.0, -70.0]


def test_boite_figee_et_comparable():
    """Deux boîtes égales sont la même clé de cache ; une boîte ne se modifie pas en place."""
    assert IMMEUBLE == IMMEUBLE and hash(IMMEUBLE) == hash(IMMEUBLE)
    assert replace(IMMEUBLE, nb_niveaux=4) != IMMEUBLE
    with pytest.raises(Exception):
        IMMEUBLE.nb_niveaux = 4


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
    boite = replace(IMMEUBLE, orientation_deg=30.0, nb_niveaux=6, teinte="sombre")
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


def test_boussole_et_cartouche():
    """Boussole (0.9.38) : un quart cliquable par vue, celui de la vue en cours orangé ; cartouche des indicateurs
    dans la bande de droite, seulement s'il y a des indicateurs à montrer."""
    from interface.axonometrie import PREFIXE_VUE
    from interface.dessin_cliquable import vue_choisie
    from interface.indicateurs import valeurs as valeurs_indicateurs
    espace = "{http://www.w3.org/2000/svg}"
    for nom, deg in VUES.items():
        racine = ET.fromstring(dessiner(IMMEUBLE, deg))
        quarts = {g.get("data-cle"): g for g in racine.iter(f"{espace}g")
                  if (g.get("data-cle") or "").startswith(PREFIXE_VUE)}
        assert set(quarts) == {PREFIXE_VUE + vue for vue in VUES}
        orange = [cle for cle, g in quarts.items() if g.find(f"{espace}path").get("fill") != "#FCFBF8"]
        assert orange == [PREFIXE_VUE + nom]
    assert all(g.get("class") != "boussole" for g in ET.fromstring(dessiner(IMMEUBLE, boussole=False)).iter())
    # Clic : « vue:nord-est » change de vue ; une paroi ou une vue inconnue, non
    assert vue_choisie({"clic": "vue:nord-est"}) == "nord-est"
    assert vue_choisie({"clic": "toiture"}) is None and vue_choisie({"clic": "vue:ouest"}) is None
    assert vue_choisie(None) is None
    # Cartouche : un texte par libellé et par valeur ; absent sans indicateur
    racine = ET.fromstring(dessiner(IMMEUBLE, cartouche=[("Compacité", "1,77 m²/m²"), ("Baies", "sud 42 m²")]))
    textes = [t.text for g in racine.iter(f"{espace}g") if g.get("class") == "cartouche"
              for t in g.iter(f"{espace}text")]
    assert textes == ["Compacité", "1,77 m²/m²", "Baies", "sud 42 m²"]
    assert "cartouche" not in dessiner(IMMEUBLE, cartouche=[])
    assert dict(valeurs_indicateurs(IMMEUBLE, ["baies_orientation"]))["Baies"] == "S 42 · N 42 m²"


def test_indicateurs_du_projet():
    """Indicateurs (0.9.38) : calculés sur la boîte ; une paroi adiabatique n'est pas déperditive ; l'ordre est celui
    du registre ; une clé inconnue est ignorée."""
    from interface.indicateurs import (COCHES_D_OFFICE, INDICATEURS, surface_baies_m2, surface_deperditive_m2,
                                       u_moyen, valeurs)
    logement = boite_de_depart("Logement de 70 m²")
    # 7 × 10 m sur 2,8 m : façades 95,2 m², toiture et plancher 70 m² chacun
    assert surface_deperditive_m2(logement) == pytest.approx(2 * (7 + 10) * 2.8 + 2 * 70)
    mitoyen = replace(logement, parois_adiabatiques=("pignon_a", "toiture"))
    assert surface_deperditive_m2(mitoyen) == pytest.approx(surface_deperditive_m2(logement) - 10 * 2.8 - 70)
    assert surface_baies_m2(logement) == pytest.approx(0.25 * 7 * 2.8 * 2)
    # U moyen : entre le plus petit et le plus grand U de l'enveloppe, ponts thermiques en plus
    assert min(logement.u_toiture, logement.u_mur) < u_moyen(logement) < logement.uw + 0.5
    assert COCHES_D_OFFICE == ("compacite", "taux_vitrage")
    lignes = valeurs(logement, ["taux_vitrage", "inconnu", "compacite"])
    assert [libelle for libelle, _ in lignes] == ["Compacité", "Baies / surface habitable"]
    assert lignes[0][1] == "3,36 m²/m²" and lignes[1][1] == "14 %"
    assert len(valeurs(logement, [i.cle for i in INDICATEURS])) == len(INDICATEURS)
    assert dict(valeurs(replace(logement, part_vitree_principale=0.0, part_vitree_arriere=0.0),
                        ["baies_orientation"]))["Baies"] == "aucune baie"


def test_balcons_dessines_et_etiquettes_couchees():
    espace = "{http://www.w3.org/2000/svg}"
    sans = ET.fromstring(dessiner(IMMEUBLE))
    avec = ET.fromstring(dessiner(replace(IMMEUBLE, debord_m=1.5, facades_debord=("principale", "arriere"))))
    # Du sud-ouest, seule la façade principale est visible : une dalle par niveau
    assert len(avec.findall(f"{espace}polygon")) - len(sans.findall(f"{espace}polygon")) == IMMEUBLE.nb_niveaux
    # Les deux étiquettes de façade suivent le pied de leur façade
    assert sum("rotate(" in t.get("transform", "") for t in sans.findall(f"{espace}text")) == 2


def test_course_du_soleil_d_ete():
    """0.9.6 : seule la course du 21 juin est dessinée : lever au nord-est, coucher au nord-ouest, haut à midi."""
    from interface.axonometrie import DECLINAISON_ETE_DEG, LATITUDE_DEG, angle_coucher, direction_soleil
    est, nord, haut = direction_soleil(0.0)
    assert est == pytest.approx(0.0) and nord < 0                          # plein sud à midi solaire
    assert math.degrees(math.asin(haut)) == pytest.approx(90.0 - LATITUDE_DEG + DECLINAISON_ETE_DEG)
    coucher = angle_coucher()
    assert 105.0 < coucher < 125.0                                          # 15 à 16 h de jour
    for signe in (-1, 1):                                                   # lever puis coucher : au nord de l'axe
        est, nord, haut = direction_soleil(signe * coucher)
        assert haut == pytest.approx(0.0, abs=1e-9) and nord > 0 and est * signe < 0
        assert math.hypot(est, nord) == pytest.approx(1.0)
    assert direction_soleil(60.0)[0] < 0                                    # l'après-midi, le soleil est à l'ouest
    textes = [t.text for t in ET.fromstring(dessiner(IMMEUBLE)).iter("{http://www.w3.org/2000/svg}text")]
    assert "21 juin, 16 h" in textes


def test_soleil_de_16_h_et_ombre_portee():
    """0.9.16 : 16 h légale ≈ 14 h 08 solaire à 2,5° E : soleil au sud-ouest, à 55° ; ombre au nord-est de la boîte,
    longue de hauteur / tan(55°) ; façades à l'ombre plus sombres."""
    from interface.axonometrie import (MURS, angle_horaire, couleur_facade, direction_soleil, enveloppe_convexe,
                                       ombre_au_sol)
    assert angle_horaire(14.0) == pytest.approx(2.08, abs=0.01)             # 14 h légale : presque midi solaire
    soleil = direction_soleil(angle_horaire(16.0))
    hauteur = math.degrees(math.asin(soleil[2]))
    azimut = math.degrees(math.atan2(-soleil[0], -soleil[1]))               # moteur : 0 = sud, 90 = ouest
    assert 54.0 < hauteur < 57.0 and 50.0 < azimut < 65.0
    # Enveloppe convexe d'un carré et de son centre : le carré
    carre = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert sorted(enveloppe_convexe(carre + [(0.5, 0.5)])) == sorted(carre)
    # Ombre d'une boîte au sud, sous ce soleil : elle déborde au nord et à l'est de l'emprise, de la bonne longueur
    boite = replace(IMMEUBLE, orientation_deg=0.0)
    ombre = ombre_au_sol(boite, soleil)
    longueur = boite.hauteur_m / math.tan(math.radians(hauteur))
    assert max(y for _, y in ombre) == pytest.approx(boite.profondeur_m / 2 - longueur * soleil[1] / math.hypot(
        soleil[0], soleil[1]))
    assert max(x for x, _ in ombre) > boite.longueur_m / 2 and min(x for x, _ in ombre) == -boite.longueur_m / 2
    # Façades : au soleil le sud et l'ouest, à l'ombre le nord et l'est
    couleurs = {f["cle"]: couleur_facade(boite, f, soleil) for f in boite.facades()}
    mur = MURS[boite.teinte]
    assert couleurs["principale"] == couleurs["pignon_a"] == mur and couleurs["arriere"] == couleurs["pignon_b"] != mur
    # Nord : une flèche (polygone sombre) et la lettre N
    from interface import charte
    svg = dessiner(boite)
    assert svg.count(f"fill='{charte.BLEU_NUIT}' stroke='none'") >= 1 and ">N</text>" in svg


def test_heure_du_soleil():
    """0.9.16 : soleil de 6 à 20 h, pas de 2 h. Toujours visible (à 6 h, remonté à son lever, vers 6 h 15) ;
    l'ombre reste dans le sol, et le dessin garde son cadrage d'une heure à l'autre."""
    from interface.axonometrie import (HAUTEUR_MIN_SOLEIL_DEG, HEURES_SOLEIL, RAYON_SOL, angle_horaire, couper,
                                       direction_soleil, heure_dessinee, libelle_heure, ombre_au_sol, tour_du_sol)
    assert HEURES_SOLEIL == (6, 8, 10, 12, 14, 16, 18, 20)
    assert direction_soleil(angle_horaire(6))[2] < 0                         # 6 h pile : encore sous l'horizon
    for heure in HEURES_SOLEIL:
        hauteur = math.degrees(math.asin(direction_soleil(angle_horaire(heure_dessinee(heure)))[2]))
        assert hauteur >= HAUTEUR_MIN_SOLEIL_DEG - 1e-9
    assert heure_dessinee(6) == pytest.approx(6.28, abs=0.02) and libelle_heure(6) == "21 juin, lever (6 h 15)"
    assert heure_dessinee(20) == 20 and libelle_heure(20) == "21 juin, 20 h"
    # Découpe d'un polygone par une fenêtre convexe
    assert sorted(couper([(0, 0), (2, 0), (2, 2), (0, 2)], [(1, -5), (5, -5), (5, 5), (1, 5)])) == \
        sorted([(1, 0), (2, 0), (2, 2), (1, 2)])
    espace = "{http://www.w3.org/2000/svg}"
    sol_16h = None
    for heure in HEURES_SOLEIL:
        soleil = direction_soleil(angle_horaire(heure_dessinee(heure)))
        rayon = RAYON_SOL * math.hypot(IMMEUBLE.longueur_m, IMMEUBLE.profondeur_m)
        ombre = couper(ombre_au_sol(IMMEUBLE, soleil), tour_du_sol(rayon))
        assert ombre and all(math.hypot(x, y) <= rayon + 1e-6 for x, y in ombre)
        svg = ET.fromstring(dessiner(IMMEUBLE, heure=heure))
        assert libelle_heure(heure) in [t.text for t in svg.iter(f"{espace}text")]
        sol = [float(v) for v in svg.find(f"{espace}polygon").get("points").replace(",", " ").split()]
        sol_16h = sol_16h or [float(v) for v in ET.fromstring(dessiner(IMMEUBLE)).find(
            f"{espace}polygon").get("points").replace(",", " ").split()]
        assert sol == pytest.approx(sol_16h, abs=2.0)                       # même cadrage, à 2 px près


# ============================================================
# FICHE D'UNE PAROI ET INFOBULLES (0.9.18)
# ============================================================
def test_fiche_de_chaque_paroi():
    from interface.briques.graphiques import nombre
    from interface.fiche_paroi import fiche, infobulles, parois
    logement = boite_de_depart()
    # Pignons aveugles : pas de baies à examiner ; deux façades vitrées, la toiture et le plancher bas
    assert list(parois(logement)) == ["principale", "pignon_a", "arriere", "pignon_b", "baies_principale",
                                      "baies_arriere", "toiture", "plancher_bas"]
    # Mur de la façade principale : 7 × 2,8 m, 25 % vitré ; U × surface = U × surface de mur
    mur = dict(fiche(logement, "principale"))
    assert mur["Surface de la façade"] == "7,0 × 2,8 m = 19,6 m²" and mur["Part vitrée"].startswith("25 %")
    assert mur["U × surface (mur)"] == nombre(logement.u_mur * 19.6 * 0.75, 1, "W/K")
    assert mur["Adiabatique"] == "non"
    baies = dict(fiche(logement, "baies_principale"))
    assert baies["Uw (baie nue)"] == nombre(logement.uw, 2, "W/m².K") and "Volets" in baies["Protection mobile"]
    assert baies["Surface de baies"].startswith("4,9 m²") and baies["Masque proche"] == "aucun"
    # Plancher sur le sol : le moteur le compte face à l'air extérieur (b = 1), d'où un U × surface
    plancher = dict(fiche(logement, "plancher_bas"))
    assert plancher["Contact"].startswith("sur le sol") and plancher["U × surface"].endswith("W/K")
    # Balcon sur la façade principale, pignon et toiture adiabatiques : baies masquées, plus de U × surface
    variante = replace(logement, debord_m=1.2, parois_adiabatiques=("pignon_a", "toiture"))
    assert dict(fiche(variante, "baies_principale"))["Masque proche"].startswith("balcon ou casquette de 1,2 m")
    for cle in ("pignon_a", "toiture"):
        lignes = dict(fiche(variante, cle))
        assert lignes["Adiabatique"].startswith("oui") and not any(g.startswith("U") for g in lignes)
    # Façade adiabatique : ses baies disparaissent de la liste ; une clé absente est refusée
    sans_arriere = replace(logement, parois_adiabatiques=("arriere",))
    assert "baies_arriere" not in parois(sans_arriere)
    with pytest.raises(KeyError):
        fiche(sans_arriere, "baies_arriere")
    # Une infobulle par paroi, sur une ligne
    bulles = infobulles(variante)
    assert set(bulles) == set(parois(variante)) and all("\n" not in t for t in bulles.values())
    assert bulles["toiture"] == "Toiture · adiabatique" and "Uw " in bulles["baies_principale"]


def test_paroi_surlignee_et_infobulles_dans_le_dessin():
    from interface.axonometrie import PREFIXE_BAIES, contours_paroi, paroi_visible
    from interface.charte import COULEUR_SURLIGNAGE
    from interface.fiche_paroi import infobulles, parois
    espace = "{http://www.w3.org/2000/svg}"
    logement = boite_de_depart()

    def surlignages(svg):
        return [p for p in ET.fromstring(svg).iter(f"{espace}polygon") if p.get("stroke") == COULEUR_SURLIGNAGE]

    # Chaque paroi a son contour ; les baies, un par baie dessinée
    for cle in parois(logement):
        contours = contours_paroi(logement, cle)
        if cle.startswith(PREFIXE_BAIES):
            facade = next(f for f in logement.facades() if PREFIXE_BAIES + f["cle"] == cle)
            assert len(contours) == len(decouper_baies(facade["part_vitree"], facade["largeur_m"],
                                                       logement.nb_niveaux, logement.hauteur_etage_m)) > 0
        else:
            assert len(contours) == 1 and len(contours[0]) == 4
    assert contours_paroi(logement, "inconnue") == []
    # Vu du sud-ouest : façade principale (sud) visible, arrière cachée, toiture visible, plancher bas caché
    proj = Projection(VUES["sud-ouest"])
    assert paroi_visible(logement, "principale", proj) and paroi_visible(logement, "baies_principale", proj)
    assert not paroi_visible(logement, "arriere", proj) and paroi_visible(logement, "toiture", proj)
    assert not paroi_visible(logement, "plancher_bas", proj)
    # Sans paroi examinée, aucun contour ; une paroi visible en trait plein, une paroi cachée en pointillé
    assert surlignages(dessiner(logement)) == []
    plein = surlignages(dessiner(logement, surlignee="principale"))
    assert len(plein) == 1 and plein[0].get("stroke-dasharray") is None and plein[0].get("fill") == "none"
    cache = surlignages(dessiner(logement, surlignee="plancher_bas"))
    assert len(cache) == 1 and cache[0].get("stroke-dasharray")
    assert len(surlignages(dessiner(logement, surlignee="baies_principale"))) == len(
        contours_paroi(logement, "baies_principale"))
    # Infobulles : le mur et les baies des deux façades visibles, et la toiture, portent leur <title>
    bulles = infobulles(logement)
    titres = [t.text for p in ET.fromstring(dessiner(logement, infobulles=bulles)).iter(f"{espace}polygon")
              for t in p.findall(f"{espace}title")]
    assert {bulles["principale"], bulles["baies_principale"], bulles["pignon_a"], bulles["toiture"]} <= set(titres)
    assert bulles["arriere"] not in titres                      # façade de dos : pas dessinée


def test_dessin_cliquable():
    """Chaque mur, baie, protection et toiture dessinés portent la clé de leur paroi (data-cle), une clé de la liste
    « Paroi examinée » ; le clic n'est retenu que pour une paroi de cette liste."""
    from interface.dessin_cliquable import paroi_cliquee
    from interface.fiche_paroi import parois
    espace = "{http://www.w3.org/2000/svg}"
    logement = boite_de_depart()
    choix = parois(logement)
    cles = {forme.get("data-cle") for vue in VUES.values()
            for forme in ET.fromstring(dessiner(logement, vue)).iter(f"{espace}polygon") if forme.get("data-cle")}
    # Les quatre vues montrent les quatre façades, leurs baies et la toiture ; le plancher bas n'est jamais vu
    assert set(cles) == set(choix) - {"plancher_bas"}
    # Les contours de la paroi surlignée ne portent pas de clé : ils laissent passer le clic
    for forme in ET.fromstring(dessiner(logement, surlignee="principale")).iter(f"{espace}polygon"):
        assert not (forme.get("pointer-events") == "none" and forme.get("data-cle"))
    # Clé reçue du composant : retenue si elle est dans la liste
    assert paroi_cliquee({"clic": "toiture"}, choix) == "toiture"
    assert paroi_cliquee({"clic": "inconnue"}, choix) is None
    assert paroi_cliquee({}, choix) is None and paroi_cliquee(None, choix) is None


# ============================================================
# TEXTES : aides, glossaire, accueil (0.9.6)
# ============================================================
def test_aides_hors_du_code_et_glossaire_complet():
    from interface import aides
    from interface.briques import BRIQUES
    # Plus aucune aide écrite dans le code : toutes viennent de interface/textes/aides.csv
    sources = {nom: open(os.path.join(RACINE, nom), encoding="utf-8").read()
               for nom in ("app.py", "interface/formulaire.py", "interface/briques/semaine_chaude.py",
                           "interface/briques/dh.py", "interface/briques/bilan.py")}
    assert all('help="' not in texte for texte in sources.values())
    # Chaque aide sert : sa clé est celle d'un widget de la page, ou d'un indicateur du registre (0.9.38), dont la
    # case porte l'aide « indicateur_<cle> » ; et chaque indicateur a la sienne
    from interface.indicateurs import INDICATEURS, PREFIXE_AIDE
    tout = "".join(sources.values()) + "".join(f'"{PREFIXE_AIDE}{i.cle}"' for i in INDICATEURS)
    assert aides.aides() and all(f'"{cle}"' in tout for cle in aides.aides())
    assert all(PREFIXE_AIDE + i.cle in aides.aides() for i in INDICATEURS)
    # Glossaire : une page Notion par terme ; chaque terme cité ([[…]] et Brique.glossaire) existe
    pages = aides.glossaire()
    assert len(pages) > 50 and all(len(url.rsplit("/", 1)[1]) == 32 for url in pages.values())
    cites = [terme for texte in aides.aides().values() for terme in aides.termes_cites(texte)]
    with open(os.path.join(aides.DOSSIER_TEXTES, "accueil.md"), encoding="utf-8") as fichier:
        cites += aides.termes_cites(fichier.read())
    for brique in BRIQUES:
        cites += aides.termes_cites(brique.phenomene + brique.lecture) + list(brique.glossaire)
    assert cites and set(cites) <= set(pages), set(cites) - set(pages)
    # Liens : terme seul, terme sous un autre texte, terme inconnu laissé en texte
    assert aides.lier("le [[DH]] et") == f"le [DH]({pages['DH']}) et"
    assert aides.lier("[[Inertie|l'inertie]]") == f"[l'inertie]({pages['Inertie']})"
    assert aides.lier("[[Inconnu]]") == "Inconnu" and aides.aide("cle_absente") is None
    assert "](https://" in aides.aide("sw")


# ============================================================
# COMPARAISON DE DEUX VARIANTES
# ============================================================
def test_differences_de_saisie():
    from dataclasses import fields
    assert set(LIBELLES) == {champ.name for champ in fields(Boite)}        # chaque saisie a son libellé
    assert differences(IMMEUBLE, IMMEUBLE) == []
    variante = replace(IMMEUBLE, uw=1.1, orientation_deg=90.0, traversant=False, part_vitree_arriere=0.35)
    assert differences(IMMEUBLE, variante) == [
        ("Orientation de la façade principale", "180° · sud", "270° · ouest"), ("Logements traversants", "oui", "non"),
        ("Part vitrée, façade arrière", "25 %", "35 %"), ("Uw des baies", "1,40 W/m².K", "1,10 W/m².K")]
    # Un réglage sans effet des deux côtés n'est pas listé ; il l'est dès que son option est allumée
    assert differences(IMMEUBLE, replace(IMMEUBLE, brasseur_debit_m3h=9000.0)) == []
    assert len(differences(replace(IMMEUBLE, brasseurs=True),
                           replace(IMMEUBLE, brasseurs=True, brasseur_debit_m3h=9000.0))) == 1
    assert differences(IMMEUBLE, replace(IMMEUBLE, debord_m=1.0, facades_debord=("principale", "pignon_a"))) == [
        ("Balcons ou casquettes", "0,0 m", "1,0 m"),
        ("Façades à balcons", "façade principale", "façade principale, pignon a")]


# ============================================================
# BRIQUES
# ============================================================
def test_briques_completes_et_code_lisible():
    import inspect

    from interface.briques import BRIQUES
    from interface.calcul import CALCULS
    assert len({b.cle for b in BRIQUES}) == len(BRIQUES) >= 3
    # Chaque calcul a au moins une brique, et chaque brique dit de quel calcul elle lit les résultats (vide : l'un ou
    # l'autre, comme le bilan en coupe)
    assert {b.besoin for b in BRIQUES} - {""} == set(CALCULS)
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
    from interface.calcul import Resultats, resultats_bbio, resultats_dh
    boite = replace(IMMEUBLE, permeabilite_q4pa=0.0)                # sans infiltrations : deux fois plus rapide
    return Resultats(**resultats_bbio(boite), **resultats_dh(boite))


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


def test_bilan_de_chaque_paroi(resultats):
    from interface.calcul import PERIODES_PAROIS
    from interface.fiche_paroi import bilan, parois
    from interface.saisie import noms_composants
    boite = replace(IMMEUBLE, permeabilite_q4pa=0.0)
    # Chaque paroi du groupe a son bilan sur chaque période de son calcul
    cles = set(noms_composants(boite))
    assert cles <= set(parois(boite))
    assert set(resultats.parois_dh) == {(c, p) for c in cles for calcul, p, _ in PERIODES_PAROIS if calcul == "dh"}
    assert set(resultats.parois_bbio) == {(c, "annee") for c in cles}
    semaine = resultats.parois_dh[("principale", "semaine")]
    assert semaine["heures"] == 168 and resultats.parois_bbio[("toiture", "annee")]["heures"] == 8760
    # Fiche : trois périodes (DH et Bbio calculés), les protections et l'ouverture pour des baies seulement
    periodes, lignes = bilan(resultats, "baies_principale")
    assert periodes == [libelle for _, _, libelle in PERIODES_PAROIS]
    assert all(len(valeurs) == 3 for _, valeurs in lignes) and lignes[0][1][0] == "7 jours"
    assert any(g.startswith("Protections baissées") for g, _ in lignes)
    assert not any(g.startswith("Protections") for g, _ in bilan(resultats, "toiture")[1])
    # Paroi hors du groupe, ou calcul absent : rien
    assert bilan(resultats, "inconnue") == ([], [])
    assert bilan(replace(resultats, parois_dh=None, parois_bbio=None), "toiture") == ([], [])


def test_bilan_en_coupe(resultats):
    """Bilan en coupe (0.9.24) : postes de chaque période, bilan qui ferme, tableau équilibré, parts du DH, coupe
    dessinée avec les clés des parois."""
    from interface.briques.bilan import parts_dh, tableau
    from interface.calcul import CUMUL, ECHANGE, POINTE, RESTE, SOLEIL
    from interface.coupe import dessiner_coupe
    from interface.saisie import noms_composants
    from moteur.bilan_paroi import POSTES
    boite = replace(IMMEUBLE, permeabilite_q4pa=0.0)
    espace = "{http://www.w3.org/2000/svg}"
    assert set(resultats.coupe_dh) == {"semaine", "confort"} and set(resultats.coupe_bbio) == {"annee"}
    coupe = resultats.coupe_bbio["annee"]
    annee, pointe = coupe[CUMUL], coupe[POINTE]
    attendus = {f"{c}.{s}" for c in noms_composants(boite) for s in (SOLEIL, ECHANGE)} | set(POSTES) | {RESTE}
    assert set(annee) == attendus == set(pointe)
    # Le reste est la somme de tout ce qui entre : la masse rend sur l'année presque tout ce qu'elle a pris
    assert annee[RESTE] == pytest.approx(sum(v for k, v in annee.items() if k != RESTE))
    entrees = sum(v for k, v in annee.items() if k != RESTE and v > 0)
    assert abs(annee[RESTE]) < 0.01 * entrees and annee["chauffage"] > 0 > annee["ventilation"]
    # Heure de pointe : la plus ensoleillée de la période, en Wh ; sa date et ses températures
    soleil = sum(v for k, v in pointe.items() if k.endswith(f".{SOLEIL}"))
    assert soleil > 0 and " à " in coupe["heure"] and coupe["te"] < 40
    semaine = resultats.coupe_dh["semaine"][POINTE]
    assert sum(v for k, v in semaine.items() if k.endswith(f".{SOLEIL}")) > 1000         # Wh sur une heure
    # Tableau : entrées et sorties s'équilibrent, la masse comprise
    lignes = tableau(annee)
    assert sum(e for _, e, _ in lignes) == pytest.approx(sum(s for _, _, s in lignes))
    # Parts du DH : du plus grand au plus petit, chacune ≤ 100 %, les apports internes parmi elles
    parts = parts_dh(resultats.part_dh, boite)
    assert list(parts["part"]) == sorted(parts["part"], reverse=True) and parts["part"].between(0, 1).all()
    assert "Apports internes" in set(parts["poste"])
    # Coupe : chaque paroi de la coupe porte sa clé ; flèches avec infobulle ; toiture adiabatique sans flèche
    svg = ET.fromstring(dessiner_coupe(boite, annee, "Année moyenne", surlignee="toiture"))
    cles = {e.get("data-cle") for e in svg.iter() if e.get("data-cle")}
    assert {"principale", "arriere", "baies_principale", "toiture", "plancher_bas"} <= cles
    fleches = [p for p in svg.iter(f"{espace}polygon") if p.find(f"{espace}title") is not None]
    assert len(fleches) >= 10 and any("Chauffage" in p.find(f"{espace}title").text for p in fleches)
    sans_toit = {k: v for k, v in annee.items() if not k.startswith("toiture.")}
    toit_adiabatique = replace(boite, parois_adiabatiques=("toiture",))
    svg = ET.fromstring(dessiner_coupe(toit_adiabatique, sans_toit, "Année moyenne"))
    assert not any(p.get("data-cle") == "toiture" for p in svg.iter(f"{espace}polygon"))


def test_effet_d_une_paroi():
    """Bouton « Mesurer l'effet de cette paroi » (0.9.24) : sans la toiture, le DH du logement baisse."""
    from interface.calcul import effet_paroi
    from interface.saisie import construire_projet
    from moteur.dh import calculer_dh
    logement = replace(boite_de_depart(), permeabilite_q4pa=0.0)       # sans infiltrations : plus rapide
    avec = calculer_dh(construire_projet(logement)).groupes.iloc[0]["dh"]
    effets = effet_paroi(logement, "toiture", ("dh",))
    assert set(effets) == {"dh"} and 0 < effets["dh"] < avec


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
    # 0.9.16 : fenêtres du graphique zoomable de la brique DH (bornes en millisecondes, comme Vega)
    import altair as alt
    import pandas as pd
    from interface.briques.dh import ETE_ENTIER, JOUR, SEMAINE, apercu, bornes_selectionnees, fenetre, temperatures
    en_date = lambda ms: pd.to_datetime(ms, unit="ms")
    assert fenetre(resultats.ete, ETE_ENTIER) is None
    bornes_semaine = fenetre(resultats.ete, SEMAINE)
    assert tuple(map(en_date, bornes_semaine)) == (semaine["date"].iloc[0], semaine["date"].iloc[-1])
    debut, fin = map(en_date, fenetre(resultats.ete, JOUR))
    jours = par_jour(resultats.ete)
    assert debut.date() == fin.date() == jours.loc[jours["dh"].idxmax(), "date"].date()
    # Cadre tracé sur la bande du dessous : rendu par Streamlit en millisecondes (ou en dates) ; absent : None
    assert bornes_selectionnees({"selection": {"zoom": {"date": list(bornes_semaine)}}}) == bornes_semaine
    assert bornes_selectionnees({"selection": {"zoom": {"date": ["2023-08-06T02:00:00", "2023-08-07"]}}})[1]         == int(pd.Timestamp("2023-08-07").value // 1_000_000)
    assert bornes_selectionnees({"selection": {"zoom": {}}}) is None and bornes_selectionnees(None) is None
    # Les deux graphiques s'écrivent : la bande porte la sélection « zoom » posée sur la semaine, le graphique du
    # dessus ne reçoit que les heures de la fenêtre (Streamlit ne suit pas un domaine imposé à l'axe du temps)
    with alt.data_transformers.disable_max_rows():          # Streamlit, lui, passe les données sans limite
        bande = apercu(resultats.ete, bornes_semaine).to_dict()
        dessus = temperatures(resultats.ete, bornes_semaine).to_dict()
        ete_entier = temperatures(resultats.ete).to_dict()
    assert bande["params"][0]["name"] == "zoom" and bande["params"][0]["value"]["x"] == list(bornes_semaine)
    lignes = lambda spec: sorted(len(donnees) for donnees in spec["datasets"].values())
    assert lignes(dessus) == [168, 3 * 168] and lignes(ete_entier)[0] > 10 * 168      # surface, puis courbes


def test_ecarts_entre_deux_calculs(resultats):
    from copy import deepcopy
    variante = deepcopy(resultats)
    variante.bbio["bbio"] = resultats.bbio["bbio"] * 0.9
    variante.dh["dh"] = resultats.dh["dh"] + 100.0
    lignes = {ligne["indicateur"]: ligne for ligne in ecarts(resultats, variante)}
    assert lignes["Bbio"]["ecart_pct"] == pytest.approx(-10.0)
    assert lignes["DH"]["ecart"] == pytest.approx(100.0) and lignes["Chauffage"]["ecart"] == 0.0
    assert all(ligne["ecart"] == 0.0 for ligne in ecarts(resultats, resultats))
    # DH seul d'un côté : seuls les indicateurs du DH sont comparés
    from interface.calcul import Resultats
    dh_seul = Resultats(dh=resultats.dh, ete=resultats.ete)
    assert dh_seul.calculs() == ("dh",) and resultats.calculs() == ("bbio", "dh")
    assert [ligne["indicateur"] for ligne in ecarts(resultats, dh_seul)] == [
        "DH", "Heures d'inconfort", "Température la plus haute"]


def test_variantes_a_a_d():
    """Garder range sous la première lettre libre, quatre au plus ; une boîte déjà gardée ne l'est pas deux fois ;
    retirer libère la lettre ; la référence retirée passe à la première qui reste."""
    from interface import variantes
    boites = [replace(boite_de_depart(), nb_niveaux=n) for n in (1, 2, 3, 4, 5)]
    liste = []
    for boite in boites[:4]:
        liste, lettre = variantes.garder(liste, boite, "Logement de 70 m²", "Moyen")
    assert [v["lettre"] for v in liste] == list("ABCD") and lettre == "D"
    assert variantes.garder(liste, boites[4], "Logement de 70 m²", "Moyen") == (liste, None)       # plein
    assert variantes.garder(liste, boites[1], "Logement de 70 m²", "Moyen") == (liste, "B")        # déjà gardée
    liste = variantes.retirer(liste, "B")
    liste, lettre = variantes.garder(liste, boites[4], "Logement de 70 m²", "Moyen")
    assert lettre == "B" and [v["lettre"] for v in liste] == list("ABCD")                    # lettre libérée
    assert variantes.trouver(liste, boites[4]) == "B" and variantes.trouver(liste, boites[1]) is None
    assert variantes.reference(liste, "C") == "C" and variantes.reference(variantes.retirer(liste, "C"), "C") == "A"
    assert variantes.reference([], "A") is None
    assert variantes.libelle(liste[0], {"bbio": 119.84, "dh": 732.2}, True) == ":material/bookmark: A · 119,8 · 732 °C.h"
    assert variantes.libelle(liste[0], {"dh": 732.2}, False) == "A · 732 °C.h"


def test_synthese_bbio_et_dh(resultats):
    """La synthèse lit l'écart de chaque besoin et du DH face à la référence ; rien sans référence."""
    from interface import synthese
    assert synthese.lecture(resultats, None, "A") is None
    assert synthese.lecture(resultats, resultats, "A") == (
        "Face à A, en kWh/m² : chauffage ± 0, refroidissement ± 0, éclairage ± 0 ; DH ± 0 °C.h.")
    points = synthese.points_par_poste(resultats, "B")
    assert [ligne["poste"] for ligne in points] == ["Chauffage", "Refroidissement", "Éclairage"]
    assert abs(sum(ligne["points"] for ligne in points) - resultats.bbio["bbio"]) < 0.05


def test_saisies_de_la_fiche():
    """La fiche reprend les saisies de sa paroi, avec des clés à elle (« fiche_ ») ; chaque saisie a un widget au
    menu (le menu reste la seule source de la boîte)."""
    from interface.formulaire import PREFIXE_FICHE, saisies_de_la_paroi, valeurs_des_widgets
    boite = boite_de_depart()
    assert saisies_de_la_paroi(boite, "baies_principale") == ["part_vitree_principale", "uw", "sw", "protection"]
    assert saisies_de_la_paroi(boite, "arriere") == ["part_vitree_arriere", "u_mur", "teinte"]
    assert saisies_de_la_paroi(boite, "toiture") == ["u_toiture", "teinte"]
    assert saisies_de_la_paroi(boite, "plancher_bas") == ["u_plancher", "plancher_sur_sol"]
    menu = valeurs_des_widgets(boite)
    assert all(champ in menu for cle in ("baies_pignon_a", "principale", "toiture", "plancher_bas")
               for champ in saisies_de_la_paroi(boite, cle))
    assert PREFIXE_FICHE == "fiche_"


def _surface(page):
    """Surface habitable écrite à droite du dessin (« Surface habitable **70 m²** · baies … »)."""
    return next(m.value for m in page.markdown if m.value.startswith("Surface habitable **")).split("**")[1]


def _lettres(page):
    """Lettres des pastilles des variantes (leur texte : « A · 119,8 · 732 °C.h », signet de la référence ôté)."""
    return [option.split(" ")[0] for option in page.pills(key="pastilles").options]


def test_page_entiere(resultats, monkeypatch):
    """La page s'affiche avec le DH seul, puis avec le Bbio et le DH ; chaque brique s'affiche ; une saisie
    modifiée attend le bouton « Calculer » ; changer de bâtiment remet les saisies à ses valeurs."""
    from streamlit.testing.v1 import AppTest

    import interface.calcul
    from interface.briques import BRIQUES
    # Pas de vrai calcul : chaque appel est compté, pour vérifier que seul le calcul demandé est lancé
    appels = []
    monkeypatch.setattr(interface.calcul, "resultats_bbio", lambda boite: appels.append(("bbio", boite)) or {
        "bbio": resultats.bbio, "mensuel": resultats.mensuel})
    monkeypatch.setattr(interface.calcul, "resultats_dh", lambda boite: appels.append(("dh", boite)) or {
        "dh": resultats.dh, "ete": resultats.ete})
    page = AppTest.from_file(os.path.join(RACINE, "app.py"), default_timeout=60).run()
    assert not page.exception

    # Ouverture sur l'accueil : aucun calcul, des liens vers le glossaire ; son bouton ouvre « Explorer »
    assert page.session_state["page"] == "Accueil" and appels == [] and not page.metric
    assert page.get("download_button") and "Télécharger ce bâtiment" in str(page.get("download_button")[0].proto)
    assert any("notion.site" in m.value for m in page.markdown)
    page.button(key="accueil_explorer").click().run()
    assert not page.exception and page.session_state["page"] == "Explorer"

    # Explorer : le logement de 70 m², l'enveloppe moyenne, le DH seul, sans brique Bbio ni calcul précédent
    assert [m.label for m in page.metric][0] == "DH" and _surface(page).startswith("70")
    assert "Bbio (points)" not in [m.label for m in page.metric]
    assert appels == [("dh", boite_de_depart())] and page.button(key="calculer").disabled and not page.warning
    assert page.metric[0].delta is None or page.metric[0].delta == ""
    assert any(m.value.startswith(":green[") and "DH max" in m.value for m in page.markdown)
    assert page.segmented_control(key="niveau_enveloppe").value == "Moyen" and page.slider(key="sw").value == 0.4
    assert page.segmented_control(key="brique").options == [b.titre for b in BRIQUES if b.besoin in ("dh", "")]
    # Volets du menu : le titre résume les valeurs ; « Baies » est ouvert
    titres = [e.label for e in page.expander]
    assert "Baies · 25/0/25/0 % · volets" in titres and "Forme · 7 × 10 m · 1 niveau · sud" in titres

    # Au-dessus du dessin (0.9.38) : la vue vient de la boussole (sud-ouest à l'ouverture) ; la boîte des
    # indicateurs coche la compacité et le taux de vitrage, « Valider » change le cartouche
    assert page.session_state["vue"] == "sud-ouest"
    assert page.session_state["indicateurs"] == ["compacite", "taux_vitrage"]
    page.checkbox(key="case_volume").check()
    page.checkbox(key="case_compacite").uncheck()
    page.button(key="valider_indicateurs").click().run()
    assert not page.exception and page.session_state["indicateurs"] == ["taux_vitrage", "volume"]
    assert len(appels) == 1
    # Paroi examinée sous le dessin : aucune à l'ouverture, puis la toiture et sa fiche, sans relancer de calcul
    assert page.selectbox(key="paroi_examinee").value is None
    page.selectbox(key="paroi_examinee").set_value("toiture").run()
    assert not page.exception and len(appels) == 1
    assert any(m.value.startswith("**Toiture**") for m in page.markdown)
    assert any("U × surface" in m.value for m in page.markdown)
    # Saisies de la fiche, liées au menu : U de la toiture changé dans la fiche, le menu le suit
    assert page.slider(key="fiche_u_toiture").value == page.slider(key="u_toiture").value
    page.slider(key="fiche_u_toiture").set_value(0.5).run()
    assert not page.exception and page.slider(key="u_toiture").value == 0.5 and len(appels) == 1
    assert any("calcul précédent" in w.value for w in page.warning)
    page.slider(key="u_toiture").set_value(boite_de_depart().u_toiture).run()
    assert page.slider(key="fiche_u_toiture").value == boite_de_depart().u_toiture and not page.warning
    # Interrupteur « adiabatique » de la fiche (0.9.38), lié au choix du menu : la toiture y entre, puis en sort
    assert page.toggle(key="fiche_adiabatique").value is False
    page.toggle(key="fiche_adiabatique").set_value(True).run()
    assert not page.exception and list(page.session_state["parois_adiabatiques"]) == ["toiture"]
    assert page.slider(key="fiche_u_toiture").disabled and len(appels) == 1
    page.toggle(key="fiche_adiabatique").set_value(False).run()
    assert not page.exception and list(page.session_state["parois_adiabatiques"]) == [] and not page.warning
    page.selectbox(key="paroi_examinee").set_value(None).run()

    # Bbio et DH : seul le Bbio est calculé, le DH vient de la mémoire
    page.segmented_control(key="choix_calculs").set_value("Bbio et DH").run()
    assert not page.button(key="calculer").disabled and any("calcul précédent" in w.value for w in page.warning)
    page.button(key="calculer").click().run()
    assert not page.exception and [nom for nom, _ in appels] == ["dh", "bbio"]
    assert [m.label for m in page.metric][:2] == ["Bbio (points)", "DH"]
    for brique in BRIQUES:
        page.session_state["brique"] = brique.cle
        page.run()
        assert not page.exception and page.subheader[-1].value == brique.titre

    # Retour au DH seul alors que la brique Bbio est affichée : la page revient à la première brique du DH
    page.session_state["brique"] = "bbio"
    page.segmented_control(key="choix_calculs").set_value("DH").run()
    page.button(key="calculer").click().run()
    assert not page.exception and page.subheader[-1].value == BRIQUES[1].titre and len(appels) == 2

    # Saisie modifiée : le dessin suit, les résultats attendent
    page.slider(key="nb_niveaux").set_value(5).run()
    assert not page.exception and not page.button(key="calculer").disabled
    assert any("calcul précédent" in w.value for w in page.warning)
    assert _surface(page).startswith("350")
    # Chiffres pâlis ; « Garder » dit qu'il garde le calcul affiché, celui d'avant la saisie
    assert any("st-key-briques" in h.proto.body for h in page.get("html"))
    assert page.button(key="garder_variante").label == "Garder le calcul affiché en A"
    page.button(key="calculer").click().run()
    assert not page.exception and page.button(key="calculer").disabled
    # Nouvelle boîte : le DH montre l'écart avec le calcul précédent (nul ici, le calcul est simulé)
    assert page.metric[0].delta == "inchangé depuis le calcul précédent"

    # Retour à l'accueil, puis « Calculer » dans le menu, qui rouvre « Explorer »
    page.segmented_control(key="page").set_value("Accueil").run()
    page.slider(key="nb_niveaux").set_value(4).run()
    assert not page.exception and not page.metric
    page.button(key="calculer").click().run()
    assert not page.exception and page.session_state["page"] == "Explorer" and appels[-1][1].nb_niveaux == 4
    page.slider(key="nb_niveaux").set_value(5).run()
    page.button(key="calculer").click().run()

    # Changer de niveau ne touche que l'enveloppe : la forme modifiée à la main (5 niveaux) reste
    from interface.formulaire import valeurs_des_widgets
    page.slider(key="u_mur").set_value(0.5).run()
    page.segmented_control(key="niveau_enveloppe").set_value("Performant").run()
    assert not page.exception and page.slider(key="nb_niveaux").value == 5
    performant = valeurs_des_widgets(boite_de_depart(niveau="Performant"))
    assert all(page.session_state[cle] == performant[cle] for cle in NIVEAUX_ENVELOPPE["Performant"])
    assert page.slider(key="uw").value == 1.2 and page.slider(key="u_mur").value == 0.25
    assert page.select_slider(key="inertie").value == "tres_lourde"
    page.button(key="calculer").click().run()
    assert appels[-1] == ("dh", replace(boite_de_depart(niveau="Performant"), nb_niveaux=5))

    # Changer de bâtiment remet toutes les saisies à ses valeurs, avec l'enveloppe du niveau choisi
    page.selectbox(key="batiment_depart").set_value("Immeuble de 9 logements").run()
    assert not page.exception and page.slider(key="nb_niveaux").value == 3 and page.slider(key="longueur_m").value == 20
    immeuble = boite_de_depart("Immeuble de 9 logements", "Performant")
    assert all(page.session_state[cle] == valeur for cle, valeur in valeurs_des_widgets(immeuble).items())
    assert _surface(page).startswith("576")
    page.button(key="calculer").click().run()
    assert not page.exception and appels[-1] == ("dh", immeuble)
    page.segmented_control(key="niveau_enveloppe").set_value("Moyen").run()
    page.selectbox(key="batiment_depart").set_value("Logement de 70 m²").run()
    assert page.slider(key="nb_niveaux").value == 1 and _surface(page).startswith("70")
    assert all(page.session_state[cle] == valeur for cle, valeur in valeurs_des_widgets(boite_de_depart()).items())

    # Variantes : A gardée (la référence), puis une variante avec balcons ; le second bouton « Calculer » sert aussi
    assert not page.dataframe and "pastilles" not in [p.key for p in page.pills]
    page.button(key="calculer").click().run()                           # la boîte de départ, calculée
    page.button(key="garder_variante").click().run()
    assert "garder_variante" not in [b.key for b in page.button]
    assert _lettres(page) == ["A"] and page.pills(key="pastilles").value == "A"
    assert any("Ce calcul est la référence A" in c.value for c in page.caption)
    page.slider(key="debord_m").set_value(1.5).run()
    page.button(key="calculer_ici").click().run()
    assert not page.exception and not page.warning and len(page.dataframe) == 1
    assert any("Balcons ou casquettes" in m.value for m in page.markdown)
    assert page.metric[0].delta == "inchangé face à A"                  # calcul simulé : même DH
    assert page.pills(key="pastilles").value is None                   # la saisie n'est aucune variante
    page.button(key="garder_variante").click().run()
    assert _lettres(page) == ["A", "B"] and page.pills(key="pastilles").value == "B"
    # Un clic sur A remet sa saisie (sans balcons) et son calcul, sans en relancer un
    nb_appels = len(appels)
    page.pills(key="pastilles").set_value("A").run()
    assert not page.exception and page.slider(key="debord_m").value == 0.0 and len(appels) == nb_appels
    assert page.button(key="calculer").disabled and page.pills(key="pastilles").value == "A"
    # B devient la référence ; A retirée : B reste seule
    page.segmented_control(key="choix_reference").set_value("B").run()
    assert page.session_state["lettre_reference"] == "B" and page.metric[0].delta == "inchangé face à B"
    page.button(key="retirer_A").click().run()
    assert not page.exception and _lettres(page) == ["B"] and len(page.dataframe) == 1
    page.button(key="retirer_B").click().run()
    assert not page.exception and not page.dataframe and "pastilles" not in [p.key for p in page.pills]
