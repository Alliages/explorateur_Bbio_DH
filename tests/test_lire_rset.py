"""Lecture d'un RSET et comparaison à une étude (outils/lire_rset.py, outils/comparer_reference.py).

Le RSET d'essai est fabriqué ici, à la main : aucune étude réelle n'entre dans le dépôt. Les tests marqués
« etudes locales » ne tournent que si des RSET sont présents dans _sources/ (hors dépôt).
"""

import glob
import os

import pytest

from config.reglages import RACINE
from moteur.enveloppe import transmission_baies, transmission_parois, transmission_ponts
from outils.comparer_reference import comparer, comparer_enveloppe, enveloppe_zone, variantes_besoins
from outils.lire_rset import _repartir_logements, lire_rset


def _balises(**champs):
    return "".join(f"<{nom}>{valeur}</{nom}>" for nom, valeur in champs.items())


def _mois(prefixe, valeur):
    lignes = "".join(f"<Sortie_Mensuelle><Index>{m}</Index><Mois>{m}</Mois><Valeur>{valeur}</Valeur></Sortie_Mensuelle>"
                     for m in range(1, 13))
    return f"<{prefixe}_mois>{lignes}</{prefixe}_mois><{prefixe}_annuel>{12 * valeur}</{prefixe}_annuel>"


def _sorties(nom, sref):
    return (_balises(Name=nom, O_SREF=sref, O_Bbio_Max=61.5) + _mois("O_B_Ch", 1.0) + _mois("O_B_Fr", 0.5)
            + _mois("O_B_Ecl", 0.15) + _mois("O_Bbio_pts", 3.75))


GAMMA = " ".join(["10"] * 36)
MASQUES_BAIE = ("<Masque_Collection>"
                f"<Masque_Horizontal>{_balises(Dhm=0.5, Dhp=0.1, hp_b=2.2)}</Masque_Horizontal>"
                f"<Masque_Vert_Gauche>{_balises(Dpg=0, Dvg=0.3, lp_b=1.5)}</Masque_Vert_Gauche>"
                f"<Masque_Vert_Droite>{_balises(Dpd=0.2, Dvd=0.4, lp_b=1.5)}</Masque_Vert_Droite>"
                f"<Masque_Lointain_Azimutal><Gamma>{GAMMA}</Gamma></Masque_Lointain_Azimutal>"
                "</Masque_Collection>")


def _baie(nom, alpha):
    return ("<Baie>" + _balises(Name=nom, Alpha=alpha, Beta=90, Ab=20, Usp_Vert=1.3, Uap_Vert=1.1, Usp_Horiz=1.7,
                                Sw1_sp_c=0.35, Sw2_sp_c=0.05, Sw3_sp_c=0, Sw1_sp_e=0.36, Sw2_sp_e=0.06, Sw3_sp_e=0,
                                Sw1_ap=0.05, Sw2_ap=0.03, Sw3_ap=0, Tli_sp=0.6, Tli_ap=0.1, Id_Et=0, Prot_Ext=1,
                                Choix_PM_GPM=1, Baie_ouvrable=1, Rouv_Max=0.64, Has_Gestion_Auto_Ouverture=0,
                                Param_OuvBaie_Ete="3 1 22 2 8 16")
            + MASQUES_BAIE + "</Baie>")


def _paroi(nom, type_paroi, beta, surface, u, id_et=0):
    return "<Paroi_Opaque>" + _balises(Name=nom, Alpha=0, Beta=beta, Ak=surface, Type_Paroi_Inclk=type_paroi, Uk=u,
                                       Sf_ck=0.004, Sf_ek=0.007, Is_Vegetalise=0, Id_Et=id_et) + "</Paroi_Opaque>"


def rset_essai(usage_seconde_zone=3):
    """RSET minimal : un bâtiment, une zone de logements (un groupe) et une zone d'un autre usage."""
    groupe = ("<Groupe>" + _balises(Name="Groupe A", SU=0, SHAB=300, V=780, Is_Climatise=0, Exp_BR_Groupe=2,
                                    Qv_occ_BBIO=330, Qv_inocc_BBIO=0)
              + "<Paroi_opaque_Collection>"
              + _paroi("Mur", 1, 90, 150, 0.25) + _paroi("Mur", 1, 90, 50, 0.3)       # deux parois de même nom
              + _paroi("Toit", 2, 0, 100, 0.15) + _paroi("Plancher", 3, 180, 100, 0.3, id_et=7)
              + "</Paroi_opaque_Collection><Lineaire_Collection>"
              + "<Lineaire>" + _balises(Name="Plancher", Ll=40, Psil=0.5, Id_Et=0) + "</Lineaire>"
              + "<Lineaire>" + _balises(Name="Sous-sol", Ll=20, Psil=0.6, Id_Et=7) + "</Lineaire>"
              + "</Lineaire_Collection>"
              + "<Inertie>" + _balises(Type_Inertie_Quotidienne=4, Amq_surf=4, Cmq_surf=100) + "</Inertie>"
              + "<Permeabilite>" + _balises(Q4PaSurf=0.8) + "</Permeabilite>"
              + "<Baie_Collection>" + _baie("Baie sud", 0) + _baie("Baie nord", 180) + "</Baie_Collection>"
              + "</Groupe>")
    zone = ("<Zone>" + _balises(Name="Logements", Usage=2, NB_logement=5, Is_Traversant=1, HSP_moy=2.7, Hauteur=3,
                                Hauteur_Zone=9)
            + f"<Groupe_Collection>{groupe}</Groupe_Collection></Zone>")
    autre = ("<Zone>" + _balises(Name="Commerce", Usage=usage_seconde_zone, NB_logement=1)
             + "<Groupe_Collection><Groupe>" + _balises(Name="G", SHAB=0, SU=80) + "</Groupe></Groupe_Collection></Zone>")
    sortie_groupe = ("<Sortie_Groupe_B>" + _sorties("Groupe A", 300)
                     + _balises(Is_Climatise=0, O_Mbgeo=-0.1, O_Mbcombles=0, O_Mbsurf_moy=0, O_Mbsurf_tot=0.23,
                                O_Mbbruit=0.1) + "</Sortie_Groupe_B>")
    sortie_zone = ("<Sortie_Zone_B>" + _sorties("Logements", 300)
                   + _balises(Usage=2, A_opv=200, A_ophh=100, A_ophb=100, A_baies=40, L_PT=60, Hg_es_hiver=50,
                              H_Th_op=89.5, H_Th_PT=32, H_Vent_Hiver=46.1, H_V_Def_Hiver=60)
                   + f"<Sortie_Groupe_B_Collection>{sortie_groupe}</Sortie_Groupe_B_Collection></Sortie_Zone_B>")
    confort = "<Sortie_Groupe_D>" + _balises(Name="Groupe A", O_NbDegresHeures=850.5, O_NbDegresHeures_max=1250,
                                             O_DebutConfAdapt=2952, O_FinConfAdapt=7199) + "</Sortie_Groupe_D>"
    return ('<?xml version="1.0" encoding="UTF-8"?><projet>'
            "<Datas_Comp><donnees_generales><logiciel><editeur>Essai</editeur></logiciel>"
            "<operation><zone_climatique>H2c (Agen)</zone_climatique></operation></donnees_generales></Datas_Comp>"
            "<RSET><Entree_Projet><Batiment_Collection><Batiment>" + _balises(Name="Bâtiment A")
            + "<Espace_Tampon_Collection><Espace_Tampon_Non_Solarise>" + _balises(Index=7, b_et_ns=0.8)
            + "</Espace_Tampon_Non_Solarise></Espace_Tampon_Collection>"
            + f"<Zone_Collection>{zone}{autre}</Zone_Collection></Batiment></Batiment_Collection>"
            + "<Simu>" + _balises(Altitude=150) + "</Simu></Entree_Projet>"
            + "<Sortie_Projet>" + _balises(Name="Essai", Version="2026.E1.0.0", Altitude=100)
            + f"<Groupe_Inconf_Collection>{confort}{confort}</Groupe_Inconf_Collection>"
            + "<Sortie_Batiment_B_Collection><Sortie_Batiment_B>" + _sorties("Bâtiment A", 300)
            + f"<Sortie_Zone_B_Collection>{sortie_zone}</Sortie_Zone_B_Collection>"
            + "</Sortie_Batiment_B></Sortie_Batiment_B_Collection></Sortie_Projet></RSET></projet>")


@pytest.fixture(scope="module")
def chemin_rset(tmp_path_factory):
    chemin = tmp_path_factory.mktemp("rset") / "essai.xml"
    chemin.write_text(rset_essai(), encoding="utf-8")
    return str(chemin)


@pytest.fixture(scope="module")
def lecture(chemin_rset):
    return lire_rset(chemin_rset)


# ------------------------------------------------------------------
# Entrées : le projet de l'outil
# ------------------------------------------------------------------
def test_projet_lu(lecture):
    projet, reference = lecture
    assert (projet.nom, projet.zone_climatique, projet.altitude_m) == ("Essai", "H2c", 150.0)
    assert [b.nom for b in projet.batiments] == ["Bâtiment A"]
    # Seule la zone de logements collectifs est reprise ; l'autre est signalée
    zones = projet.batiments[0].zones
    assert [z.nom for z in zones] == ["Logements"] and zones[0].hauteur_sous_plafond_m == 2.7
    assert reference.infos["non_repris"]["zones d'un autre usage que le logement collectif (usage 3)"] == 1
    groupe = zones[0].groupes[0]
    assert (groupe.nom, groupe.surface_m2, groupe.volume_m3, groupe.nb_logements) == ("Groupe A", 300.0, 780.0, 5)
    assert (groupe.traversant, groupe.climatise, groupe.exposition_bruit) == (True, False, "BR2")
    assert groupe.debit_ventilation_m3h == 330.0 and groupe.inertie_quotidienne == "lourde"


def test_parois_et_ponts_lus(lecture):
    groupe = lecture[0].batiments[0].zones[0].groupes[0]
    assert [p.nom for p in groupe.parois] == ["Mur", "Mur (2)", "Toit", "Plancher"]       # doublon renommé
    assert [p.type for p in groupe.parois] == ["mur", "mur", "toiture", "plancher_bas"]
    plancher = groupe.parois[3]
    assert (plancher.contact, plancher.b_therm, plancher.inclinaison_deg) == ("local_non_chauffe", 0.8, 180.0)
    assert (groupe.parois[0].sf_c, groupe.parois[0].sf_e) == (0.004, 0.007)
    # H parois = 150 × 0,25 + 50 × 0,3 + 100 × 0,15 + 100 × 0,3 × 0,8 = 91,5 W/K
    assert transmission_parois(groupe) == pytest.approx(91.5)
    # Ponts : 40 × 0,5 + 20 × 0,6 × 0,8 (espace tampon) = 29,6 W/K
    assert transmission_ponts(groupe) == pytest.approx(29.6)


def test_baies_et_masques_lus(lecture):
    groupe = lecture[0].batiments[0].zones[0].groupes[0]
    sud, nord = groupe.baies
    assert (sud.nom, sud.surface_m2, sud.orientation_deg, nord.orientation_deg) == ("Baie sud", 20.0, 0.0, -180.0)
    assert (sud.uw, sud.uw_horizontal, sud.tl) == (1.3, 1.7, 0.6)
    assert (sud.sw_c, sud.sw2_c, sud.sw_e, sud.sw2_e) == pytest.approx((0.40, 0.05, 0.42, 0.06))
    assert (sud.largeur_m, sud.hauteur_m) == (1.5, 2.2)
    horizontal, gauche, droite, tranches = sud.masques
    assert (horizontal.debord_m, horizontal.distance_m) == (0.5, 0.1)
    assert (gauche.cote, gauche.debord_m, droite.cote, droite.debord_m, droite.distance_m) \
        == ("gauche", 0.3, "droite", 0.4, 0.2)
    assert tranches.hauteurs_deg == [10.0] * 36
    assert transmission_baies(groupe) == pytest.approx(2 * 20.0 * 1.3)


def test_repartition_des_logements():
    assert _repartir_logements(12, [500.0]) == [12]
    assert _repartir_logements(10, [600.0, 400.0]) == [6, 4]
    assert _repartir_logements(3, [900.0, 50.0, 50.0]) == [1, 1, 1]         # au moins un logement par groupe
    assert sum(_repartir_logements(7, [100.0, 100.0, 100.0])) == 7


def test_inertie_saisie_et_fichier_refuse(tmp_path):
    texte = rset_essai().replace("<Type_Inertie_Quotidienne>4</Type_Inertie_Quotidienne><Amq_surf>4</Amq_surf>"
                                 "<Cmq_surf>100</Cmq_surf>",
                                 "<Type_Inertie_Quotidienne>0</Type_Inertie_Quotidienne><Amq_surf>3</Amq_surf>"
                                 "<Cmq_surf>500</Cmq_surf><Ams_surf>3.8</Ams_surf><Cms_surf>837</Cms_surf>")
    chemin = tmp_path / "inertie.xml"
    chemin.write_text(texte, encoding="utf-8")
    groupe = lire_rset(str(chemin))[0].batiments[0].zones[0].groupes[0]
    assert (groupe.inertie_quotidienne, groupe.amq_surf, groupe.cmq_surf) == ("personnalisee", 3.0, 500.0)
    assert (groupe.inertie_sequentielle, groupe.ams_surf, groupe.cms_surf) == ("personnalisee", 3.8, 837.0)
    autre = tmp_path / "autre.xml"
    autre.write_text("<projet><Datas_Comp/></projet>", encoding="utf-8")
    with pytest.raises(ValueError, match="n'est pas un RSET"):
        lire_rset(str(autre))


# ------------------------------------------------------------------
# Sorties : la référence
# ------------------------------------------------------------------
def test_reference_lue(lecture):
    reference = lecture[1]
    groupe = reference.groupes.iloc[0]
    assert (groupe["groupe"], groupe["sref_m2"], groupe["bbio_max"]) == ("Groupe A", 300.0, 61.5)
    assert (groupe["b_ch"], groupe["b_fr"], groupe["bbio"]) == pytest.approx((12.0, 6.0, 45.0))
    assert (groupe["mb_geo"], groupe["mb_bruit"]) == (-0.1, 0.1) and not groupe["climatise"]
    zone = reference.zones.iloc[0]
    assert (zone["h_parois"], zone["h_infiltrations"], zone["a_baies"]) == (89.5, 60.0, 40.0)
    assert len(reference.mensuel) == 3 * 12 and set(reference.mensuel["niveau"]) == {"groupe", "zone", "batiment"}
    assert reference.mensuel["b_ch"].tolist() == [1.0] * 36
    # Confort d'été : le groupe figure deux fois dans le fichier, une seule dans la référence
    assert len(reference.confort) == 1
    assert reference.confort.iloc[0][["dh", "dh_max", "debut_confort_adaptatif"]].tolist() == [850.5, 1250.0, 2952.0]
    baie = reference.baies.iloc[0]
    assert (baie["baie"], baie["sw_ap"], baie["sw2_ap"], baie["u_ap"], baie["rouv_max"]) \
        == ("Baie sud", pytest.approx(0.08), 0.03, 1.1, 0.64)
    assert baie["ouvrable"] and baie["ouverture_ete"] == "3 1 22 2 8 16"
    assert reference.infos["version_moteur"] == "2026.E1.0.0" and reference.infos["altitude_corrigee_m"] == 100.0


# ------------------------------------------------------------------
# Comparaison
# ------------------------------------------------------------------
def test_enveloppe_de_la_zone(lecture):
    projet, reference = lecture
    zone = projet.batiments[0].zones[0]
    valeurs = enveloppe_zone(zone)
    assert valeurs["h_parois"] == pytest.approx(91.5) and valeurs["h_baies"] == pytest.approx(52.0)
    assert valeurs["h_ventilation"] == pytest.approx(0.34 * 330.0 * 0.5)
    assert (valeurs["a_parois_verticales"], valeurs["a_toitures"], valeurs["a_planchers_bas"]) == (200.0, 100.0, 100.0)
    assert (valeurs["a_baies"], valeurs["l_ponts"]) == (40.0, 60.0)
    table = comparer_enveloppe(projet, reference).set_index("grandeur")
    assert table.loc["h_parois", "ecart_pct"] == pytest.approx((91.5 / 89.5 - 1.0) * 100.0)
    assert table.loc["a_baies", "ecart_pct"] == pytest.approx(0.0)


def test_comparaison_complete(chemin_rset):
    c = comparer(chemin_rset)
    assert c.annuel["niveau"].tolist() == ["groupe", "zone", "batiment"]
    groupe = c.annuel.iloc[0]
    assert groupe["b_ch_etude"] == pytest.approx(12.0) and groupe["bbio_etude"] == pytest.approx(45.0)
    assert groupe["b_ch_outil"] > 0 and groupe["bbio_outil"] == pytest.approx(
        2 * groupe["b_ch_outil"] + 2 * groupe["b_fr_outil"] + 5 * groupe["b_ecl_outil"])
    # Bbio max de l'outil : H2c sous 400 m (−0,1), 60 m² par logement (0), 300 m² ((19,5 − 4,5) / 65),
    # BR2 en H2c (0,1), 2,7 m sous plafond ((2,7 / 2,5 − 1) / 1,5)
    assert groupe["bbio_max_outil"] == pytest.approx(65.0 * (1.0 + 0.08 / 1.5) + 15.0)
    assert len(c.mensuel) == 12 and c.mensuel["b_fr_etude"].tolist() == [0.5] * 12
    assert c.mensuel["b_ch_outil"].sum() == pytest.approx(groupe["b_ch_outil"])
    # Infiltrations : l'outil donne sa moyenne de janvier et février, à côté de l'indicateur de l'étude (60 W/K)
    infiltrations = c.enveloppe.set_index("grandeur").loc["h_infiltrations"]
    assert infiltrations["etude"] == 60.0 and infiltrations["outil"] > 5.0
    assert infiltrations["ecart_pct"] == pytest.approx((infiltrations["outil"] / 60.0 - 1.0) * 100.0)


def test_variantes_des_besoins(lecture):
    projet, reference = lecture
    v = variantes_besoins(projet, reference).set_index("variante")
    assert list(v.index) == ["outil", "sans infiltrations", "sans ouverture des baies", "sans protections mobiles",
                             "sans aucun des trois"]
    assert (v["b_fr_etude"] == 6.0).all() and (v["b_ch_etude"] == 12.0).all()
    # Sans infiltrations : moins de chauffage
    assert v.loc["sans infiltrations", "b_ch"] < v.loc["outil", "b_ch"]
    # Chaque module retiré augmente le besoin de froid
    assert v.loc["outil", "b_fr"] < v.loc["sans ouverture des baies", "b_fr"]
    assert v.loc["outil", "b_fr"] < v.loc["sans protections mobiles", "b_fr"] < v.loc["sans aucun des trois", "b_fr"]
    # Le projet lu n'est pas modifié par les variantes
    groupe = projet.batiments[0].zones[0].groupes[0]
    assert groupe.baies[0].protection == "volet" and groupe.baies[0].ouvrable and groupe.permeabilite_q4pa == 0.8


def test_protections_et_ouvertures_lues(lecture):
    groupe = lecture[0].batiments[0].zones[0].groupes[0]
    baie = groupe.baies[0]
    # Choix_PM_GPM = 1 : volet en gestion automatique ; valeurs « ap » de la baie
    assert (baie.protection, baie.gestion_protection, baie.protection_exterieure) == ("volet", "automatique", True)
    assert (baie.uw_protege, baie.sw_protege, baie.sw2_protege, baie.tl_protege) == (1.1, pytest.approx(0.08), 0.03, 0.1)
    assert (baie.ouvrable, baie.ratio_ouverture_max, baie.exposition_bruit) == (True, 0.64, None)
    assert groupe.traversant and groupe.hauteur_tirage_m is None
    # Perméabilité du groupe ; hauteur de la zone et hauteur moyenne au-dessus du sol (3 + 9 / 2)
    zone = lecture[0].batiments[0].zones[0]
    assert (groupe.permeabilite_q4pa, zone.hauteur_m, zone.hauteur_moyenne_m) == (0.8, 9.0, 7.5)


# ------------------------------------------------------------------
# Études locales (hors dépôt) : la lecture retrouve les indicateurs des études
# ------------------------------------------------------------------
ETUDES_LOCALES = sorted(glob.glob(os.path.join(RACINE, "_sources", "*.xml"))
                        + glob.glob(os.path.join(RACINE, "_sources", "*", "*.xml")))


@pytest.mark.skipif(not ETUDES_LOCALES, reason="aucun RSET dans _sources/ (études gardées hors du dépôt)")
def test_etudes_locales_enveloppe_identique():
    for chemin in ETUDES_LOCALES:
        projet, reference = lire_rset(chemin)
        table = comparer_enveloppe(projet, reference)
        identiques = table[table["grandeur"].isin(["h_parois", "a_parois_verticales", "a_toitures",
                                                   "a_planchers_bas", "a_baies", "l_ponts"])]
        # Les études arrondissent leurs surfaces à 0,1 m² : 0,5 % de marge pour les plus petites
        assert len(identiques) and identiques["ecart_pct"].abs().max() < 0.5, os.path.basename(chemin)
        proches = table[table["grandeur"].isin(["h_baies", "h_ponts"])]
        assert proches["ecart_pct"].abs().max() < 25.0, os.path.basename(chemin)
