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


def test_niveaux_d_enveloppe(tmp_path):
    """Trois niveaux lus dans donnees/typologies_logements.csv, chacun pour les 13 saisies d'enveloppe."""
    assert list(NIVEAUX_ENVELOPPE) == ["Performant", "Moyen", "Faible"]
    performant, moyen, faible = NIVEAUX_ENVELOPPE.values()
    assert all(set(n) == set(CHAMPS_TYPOLOGIES.values()) for n in NIVEAUX_ENVELOPPE.values())
    assert len(moyen) == 13 and set(moyen) <= {champ.name for champ in fields(Boite)}
    # Valeurs du CSV (virgule décimale, classes d'inertie traduites)
    assert (performant["uw"], moyen["uw"], faible["uw"]) == (1.35, 1.4, 1.45)
    assert moyen["sw"] == 0.43 and moyen["psi_planchers"] == 0.22 and moyen["ratio_ouverture_max"] == 0.78
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


def test_balcons_dessines_et_etiquettes_couchees():
    espace = "{http://www.w3.org/2000/svg}"
    sans = ET.fromstring(dessiner(IMMEUBLE))
    avec = ET.fromstring(dessiner(replace(IMMEUBLE, debord_m=1.5, facades_debord=("principale", "arriere"))))
    # Du sud-ouest, seule la façade principale est visible : une dalle par niveau
    assert len(avec.findall(f"{espace}polygon")) - len(sans.findall(f"{espace}polygon")) == IMMEUBLE.nb_niveaux
    # Les deux étiquettes de façade suivent le pied de leur façade
    assert sum("rotate(" in t.get("transform", "") for t in sans.findall(f"{espace}text")) == 2


# ============================================================
# COMPARAISON DE DEUX VARIANTES
# ============================================================
def test_differences_de_saisie():
    from dataclasses import fields
    assert set(LIBELLES) == {champ.name for champ in fields(Boite)}        # chaque saisie a son libellé
    assert differences(IMMEUBLE, IMMEUBLE) == []
    variante = replace(IMMEUBLE, uw=1.1, orientation_deg=90.0, traversant=False, part_vitree_arriere=0.35)
    assert differences(IMMEUBLE, variante) == [
        ("Orientation de la façade principale", "sud", "ouest"), ("Logements traversants", "oui", "non"),
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
    # Chaque calcul a au moins une brique, et chaque brique dit de quel calcul elle lit les résultats
    assert {b.besoin for b in BRIQUES} == set(CALCULS)
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
    return calculer(replace(IMMEUBLE, permeabilite_q4pa=0.0))       # sans infiltrations : deux fois plus rapide


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
    # DH seul d'un côté : seuls les indicateurs du DH sont comparés
    from interface.calcul import Resultats
    dh_seul = Resultats(dh=resultats.dh, ete=resultats.ete)
    assert dh_seul.calculs() == ("dh",) and resultats.calculs() == ("bbio", "dh")
    assert [ligne["indicateur"] for ligne in ecarts(resultats, dh_seul)] == [
        "DH", "Heures d'inconfort", "Température la plus haute"]


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

    # Ouverture : le logement de 70 m², l'enveloppe moyenne, le DH seul, sans brique Bbio
    assert [m.label for m in page.metric][:3] == ["Surface habitable", "Baies / surface habitable", "DH"]
    assert "Bbio (points)" not in [m.label for m in page.metric] and page.metric[0].value.startswith("70")
    assert appels == [("dh", boite_de_depart())] and page.button(key="calculer").disabled and not page.warning
    assert page.segmented_control(key="niveau_enveloppe").value == "Moyen" and page.slider(key="sw").value == 0.43
    assert page.segmented_control(key="brique").options == [b.titre for b in BRIQUES if b.besoin == "dh"]

    # Bbio et DH : seul le Bbio est calculé, le DH vient de la mémoire
    page.segmented_control(key="choix_calculs").set_value("Bbio et DH").run()
    assert not page.button(key="calculer").disabled and any("calcul précédent" in w.value for w in page.warning)
    page.button(key="calculer").click().run()
    assert not page.exception and [nom for nom, _ in appels] == ["dh", "bbio"]
    assert [m.label for m in page.metric][2:4] == ["Bbio (points)", "DH"]
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
    assert page.metric[0].value.startswith("350")
    page.button(key="calculer").click().run()
    assert not page.exception and page.button(key="calculer").disabled

    # Changer de niveau ne touche que l'enveloppe : la forme modifiée à la main (5 niveaux) reste
    from interface.formulaire import valeurs_des_widgets
    page.slider(key="u_mur").set_value(0.5).run()
    page.segmented_control(key="niveau_enveloppe").set_value("Performant").run()
    assert not page.exception and page.slider(key="nb_niveaux").value == 5
    performant = valeurs_des_widgets(boite_de_depart(niveau="Performant"))
    assert all(page.session_state[cle] == performant[cle] for cle in NIVEAUX_ENVELOPPE["Performant"])
    assert page.slider(key="uw").value == 1.35 and page.slider(key="u_mur").value == 0.2
    assert page.select_slider(key="inertie").value == "tres_lourde"
    page.button(key="calculer").click().run()
    assert appels[-1] == ("dh", replace(boite_de_depart(niveau="Performant"), nb_niveaux=5))

    # Changer de bâtiment remet toutes les saisies à ses valeurs, avec l'enveloppe du niveau choisi
    page.selectbox(key="batiment_depart").set_value("Immeuble de 9 logements").run()
    assert not page.exception and page.slider(key="nb_niveaux").value == 3 and page.slider(key="longueur_m").value == 20
    immeuble = boite_de_depart("Immeuble de 9 logements", "Performant")
    assert all(page.session_state[cle] == valeur for cle, valeur in valeurs_des_widgets(immeuble).items())
    assert page.metric[0].value.startswith("576")
    page.button(key="calculer").click().run()
    assert not page.exception and appels[-1] == ("dh", immeuble)
    page.segmented_control(key="niveau_enveloppe").set_value("Moyen").run()
    page.selectbox(key="batiment_depart").set_value("Logement de 70 m²").run()
    assert page.slider(key="nb_niveaux").value == 1 and page.metric[0].value.startswith("70")
    assert all(page.session_state[cle] == valeur for cle, valeur in valeurs_des_widgets(boite_de_depart()).items())

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
