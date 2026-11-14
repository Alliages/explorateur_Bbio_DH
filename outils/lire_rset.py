r"""
============================================================
 LIRE UN RSET — d'une étude réglementaire à un projet de l'outil
============================================================
 Un RSET (récapitulatif standardisé d'étude thermique) est le
 fichier XML que produit tout logiciel RE2020 (Climawin,
 Pleiades…). Il contient, au format du moteur Th-BCE du CSTB :

     <projet>
       <Datas_Comp>            données administratives
       <RSET>
         <Entree_Projet>       ENTRÉES du moteur : bâtiments, zones,
                               groupes, parois, baies, ponts thermiques
         <Sortie_Projet>       SORTIES du moteur : Bbio, Cep, DH

 Ce module en tire :
   - un Projet de l'outil (moteur/structures.py), pour refaire
     le calcul avec notre moteur ;
   - une Reference : les résultats de l'étude, pour comparer.

 Correspondance des entrées (noms du moteur → structures) :
   Groupe        SHAB → surface_m2 ; V → volume_m3 ;
                 Exp_BR_Groupe (1, 2, 3) → BR1, BR2, BR3 ;
                 Qv_occ_BBIO → débit de ventilation du Bbio ;
                 NB_logement de la zone → nb_logements
   Paroi_Opaque  Ak, Uk, Alpha (orientation), Beta (inclinaison),
                 Type_Paroi_Inclk (1 mur, 2 toiture, 3 plancher bas),
                 Sf_ck, Sf_ek ; Id_Et → espace tampon → b_therm
   Baie          Ab, Alpha, Beta ; Usp_Vert et Usp_Horiz (U sans
                 protection mobile) ; Sw1 + Sw2 + Sw3 sans protection
                 (conditions C et E) ; Tli_sp ;
                 Choix_PM_GPM → protection mobile et sa gestion
                 (1 à 3 volet, 4 à 6 store enroulable : automatique,
                 manuelle non motorisée, manuelle motorisée), avec
                 Uap, Sw1_ap + Sw2_ap + Sw3_ap et Tli_ap ;
                 Baie_ouvrable, Rouv_Max, Exp_BR → ouverture
   Groupe (suite) Delta_trav_surv → traversant ; Httf si
                 Def_Httf = 0 → hauteur de tirage
   Lineaire      Ll, Psil (multiplié par b sur un espace tampon,
                 fiche 5.19, éq. 304 ; l'indicateur H_Th_PT des
                 sorties, lui, est la somme des Ll × Psil sans b)
   Permeabilite  Q4PaSurf → perméabilité à l'air du groupe
   Zone          Hauteur_Zone → hauteur ; Hauteur + Hauteur_Zone / 2
                 → hauteur moyenne (prise au vent des infiltrations)
   Inertie       classe quotidienne 1 à 5 (très légère à très lourde),
                 0 = valeurs Amq_surf et Cmq_surf saisies
   Masques       horizontal (Dhm, Dhp, hauteur hp_b), verticaux gauche
                 et droite (Dvg, Dpg, largeur lp_b), lointain par 36
                 tranches azimutales (Gamma)

 Ce que l'outil ne sait pas encore reprendre est compté dans
 Reference.infos["non_repris"] : gestion automatique de
 l'ouverture, stores vénitiens et secondes protections, baies sur un espace tampon,
 entrées d'air, flux solaires des ponts thermiques, usages autres que le
 logement collectif.

 Les RSET sont des études de projets réels : ils restent hors
 du dépôt (dossiers commençant par « _ »).

 Usage :
     from outils.lire_rset import lire_rset
     projet, reference = lire_rset("_sources/mon_etude.xml")
============================================================
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pandas as pd

from config.reglages import ZONES_CLIMATIQUES
from moteur.structures import (Baie, Batiment, Groupe, MasqueProcheHorizontal, MasqueProcheVertical,
                               MasqueTranches, Paroi, PontThermique, Projet, Zone)

# ============================================================
# CODES DU MOTEUR TH-BCE
# ============================================================
USAGE_LOGEMENT_COLLECTIF = "2"                      # Usage de la zone
TYPES_PAROI = {"1": "mur", "2": "toiture", "3": "plancher_bas"}        # Type_Paroi_Inclk
# Type_Inertie_Quotidienne : 0 = valeurs saisies, 1 à 5 = classes du tableau 53 (fiche 5.21).
# Code 4 = « lourde » : recoupé avec le récapitulatif PDF d'une étude (voir docs/audit.md, 0.8.10)
INERTIES_QUOTIDIENNES = {"1": "tres_legere", "2": "legere", "3": "moyenne", "4": "lourde", "5": "tres_lourde"}
INERTIE_SAISIE = "0"
SANS_ESPACE_TAMPON = "0"                            # Id_Et : le composant donne sur l'extérieur
# Choix_PM_GPM (fiche 5.9) : 0 pas de protection ; 1 à 3 volet ; 4 à 6 store enroulable ; 7 à 9 store vénitien.
# Dans chaque trio : gestion automatique avec dérogation, manuelle non motorisée, manuelle motorisée
PROTECTIONS = {"1": ("volet", "automatique"), "2": ("volet", "manuelle_non_motorisee"),
               "3": ("volet", "manuelle_motorisee"), "4": ("store_enroulable", "automatique"),
               "5": ("store_enroulable", "manuelle_non_motorisee"), "6": ("store_enroulable", "manuelle_motorisee")}
SANS_PROTECTION = "0"
HORLOGE_CREPUSCULAIRE = "1"                         # Type_Horl
MOIS = range(1, 13)
BESOINS = {"b_ch": "O_B_Ch", "b_fr": "O_B_Fr", "b_ecl": "O_B_Ecl", "bbio": "O_Bbio_pts"}
MODULATIONS = {"mb_geo": "O_Mbgeo", "mb_combles": "O_Mbcombles", "mb_surf_moy": "O_Mbsurf_moy",
               "mb_surf_tot": "O_Mbsurf_tot", "mb_bruit": "O_Mbbruit", "mb_hsp": "O_Mbhsp"}
# Coefficients de déperdition donnés par zone dans les sorties du mode Th-B (W/K)
DEPERDITIONS = {"h_baies": "Hg_es_hiver", "h_parois": "H_Th_op", "h_ponts": "H_Th_PT",
                "h_ventilation": "H_Vent_Hiver", "h_infiltrations": "H_V_Def_Hiver"}
SURFACES = {"a_parois_verticales": "A_opv", "a_toitures": "A_ophh", "a_planchers_bas": "A_ophb",
            "a_baies": "A_baies", "l_ponts": "L_PT"}
CONFORT = {"dh": "O_NbDegresHeures", "dh_max": "O_NbDegresHeures_max", "debut_confort_adaptatif": "O_DebutConfAdapt",
           "fin_confort_adaptatif": "O_FinConfAdapt", "nb_h_inconfort": "O_Nb_h_inconf",
           "nb_h_inconfort_1": "O_Nb_h_inconf_1", "nb_h_inconfort_2": "O_Nb_h_inconf_2"}


@dataclass
class Reference:
    """Résultats de l'étude, lus dans les sorties du moteur.

    groupes, zones, batiments   besoins annuels b_ch, b_fr, b_ecl (kWh/m²), bbio et bbio_max (points), sref_m2 ;
                                modulations du Bbio max par groupe ; déperditions et surfaces par zone
    mensuel     une ligne par niveau (« groupe », « zone », « batiment »), objet et mois : b_ch, b_fr, b_ecl, bbio
    baies       une ligne par baie de l'étude (batiment, zone, groupe, baie, dans l'ordre et sous les noms du
                Projet) : surface, orientation, inclinaison, U, Sw et Tl sans protection (« sp ») et avec
                protection mobile fermée (« ap »), ouverture (ouvrable, rouv_max, réglages par saison)
    confort     une ligne par groupe : dh, dh_max, période de confort adaptatif (heures de début et de fin)
    infos       logiciel, version du moteur, zone climatique, altitude, et « non_repris » : ce que l'outil
                ne reprend pas de l'étude
    """
    groupes: pd.DataFrame
    zones: pd.DataFrame
    batiments: pd.DataFrame
    mensuel: pd.DataFrame
    baies: pd.DataFrame
    confort: pd.DataFrame
    infos: dict


# ============================================================
# 1. PETITS OUTILS DE LECTURE
# ============================================================
def _texte(element, balise, defaut=None):
    """Texte d'une balise fille, sans espaces ; « defaut » si elle manque ou est vide."""
    valeur = element.findtext(balise)
    return valeur.strip() if valeur is not None and valeur.strip() else defaut


def _nombre(element, balise, defaut=None):
    """Nombre porté par une balise fille (point décimal)."""
    valeur = _texte(element, balise)
    return float(valeur) if valeur is not None else defaut


def _exiger(element, balise, objet):
    """Nombre obligatoire : erreur claire s'il manque."""
    valeur = _nombre(element, balise)
    if valeur is None:
        raise ValueError(f"RSET : « {balise} » manque dans {objet}")
    return valeur


def _noms_uniques(noms):
    """Noms rendus uniques dans leur liste, en ajoutant « (2) », « (3) »… aux doublons."""
    vus, resultat = {}, []
    for nom in noms:
        vus[nom] = vus.get(nom, 0) + 1
        resultat.append(nom if vus[nom] == 1 else f"{nom} ({vus[nom]})")
    return resultat


def _zone_climatique(racine):
    """Zone climatique du projet : « H1a », « H1-a » ou « H2a (Rennes) » selon les logiciels."""
    brut = next((e.text for e in racine.iter("zone_climatique") if e.text), None)
    if brut is None:
        raise ValueError("RSET : zone climatique introuvable (balise zone_climatique)")
    zone = brut.split()[0].replace("-", "")
    if zone not in ZONES_CLIMATIQUES:
        raise ValueError(f"RSET : zone climatique « {brut} » inconnue")
    return zone


# ============================================================
# 2. ENTRÉES : DU GROUPE DU MOTEUR AU GROUPE DE L'OUTIL
# ============================================================
def _masques(element, non_repris):
    """Masques d'un composant, et ses dimensions (largeur, hauteur) portées par les masques proches."""
    masques, largeur, hauteur = [], None, None
    collection = element.find("Masque_Collection")
    for masque in (collection if collection is not None else ()):
        if masque.tag == "Masque_Horizontal":
            masques.append(MasqueProcheHorizontal(debord_m=_nombre(masque, "Dhm", 0.0),
                                                  distance_m=_nombre(masque, "Dhp", 0.0)))
            hauteur = _nombre(masque, "hp_b", hauteur)
        elif masque.tag in ("Masque_Vert_Gauche", "Masque_Vert_Droite"):
            gauche = masque.tag.endswith("Gauche")
            masques.append(MasqueProcheVertical(cote="gauche" if gauche else "droite",
                                                debord_m=_nombre(masque, "Dvg" if gauche else "Dvd", 0.0),
                                                distance_m=_nombre(masque, "Dpg" if gauche else "Dpd", 0.0)))
            largeur = _nombre(masque, "lp_b", largeur)
        elif masque.tag == "Masque_Lointain_Azimutal":
            masques.append(MasqueTranches([float(v) for v in _texte(masque, "Gamma", "").split()]))
        else:
            non_repris[f"masques « {masque.tag} »"] = non_repris.get(f"masques « {masque.tag} »", 0) + 1
    return masques, largeur, hauteur


def _lire_paroi(element, nom, coefficients_b, non_repris):
    """Paroi opaque du moteur → Paroi de l'outil."""
    code = _texte(element, "Type_Paroi_Inclk")
    if code not in TYPES_PAROI:
        raise ValueError(f"RSET : paroi « {nom} », Type_Paroi_Inclk « {code} » inconnu")
    espace = _texte(element, "Id_Et", SANS_ESPACE_TAMPON)
    sur_tampon = espace != SANS_ESPACE_TAMPON
    if sur_tampon and espace not in coefficients_b:
        raise ValueError(f"RSET : paroi « {nom} », espace tampon « {espace} » non décrit")
    if _texte(element, "Is_Vegetalise", "0") != "0":
        non_repris["parois végétalisées (lues comme des parois nues)"] = \
            non_repris.get("parois végétalisées (lues comme des parois nues)", 0) + 1
    masques, largeur, hauteur = _masques(element, non_repris)
    return Paroi(nom, TYPES_PAROI[code], _exiger(element, "Ak", f"la paroi « {nom} »"),
                 u=_exiger(element, "Uk", f"la paroi « {nom} »"),
                 orientation_deg=_nombre(element, "Alpha"), inclinaison_deg=_nombre(element, "Beta"),
                 contact="local_non_chauffe" if sur_tampon else "exterieur",
                 b_therm=coefficients_b[espace] if sur_tampon else 1.0,
                 sf_c=_nombre(element, "Sf_ck"), sf_e=_nombre(element, "Sf_ek"),
                 largeur_m=largeur, hauteur_m=hauteur, masques=masques)


def _lire_baie(element, nom, non_repris):
    """Baie du moteur → Baie de l'outil, sans protection mobile (« sp »)."""
    objet = f"la baie « {nom} »"
    if _texte(element, "Id_Et", SANS_ESPACE_TAMPON) != SANS_ESPACE_TAMPON:
        cle = "baies sur un espace tampon (lues comme donnant sur l'extérieur)"
        non_repris[cle] = non_repris.get(cle, 0) + 1
    sw2_c, sw2_e = _nombre(element, "Sw2_sp_c", 0.0), _nombre(element, "Sw2_sp_e", 0.0)
    sw3_c, sw3_e = _nombre(element, "Sw3_sp_c", 0.0), _nombre(element, "Sw3_sp_e", 0.0)
    if sw3_c or sw3_e:
        non_repris["baies avec Sw3 sans protection (ajouté à Sw1)"] = \
            non_repris.get("baies avec Sw3 sans protection (ajouté à Sw1)", 0) + 1
    masques, largeur, hauteur = _masques(element, non_repris)
    # Protection mobile et sa gestion ; les stores vénitiens (7 à 9) ne sont pas modélisés : baie lue nue
    choix = _texte(element, "Choix_PM_GPM", SANS_PROTECTION)
    protection = {}
    if choix in PROTECTIONS:
        protection = dict(protection=PROTECTIONS[choix][0], gestion_protection=PROTECTIONS[choix][1],
                          protection_exterieure=_texte(element, "Prot_Ext", "1") == "1",
                          detecteur_presence=_texte(element, "Detec_Pres", "0") == "1",
                          horloge_crepusculaire=_texte(element, "Type_Horl", "0") == HORLOGE_CREPUSCULAIRE,
                          uw_protege=_exiger(element, "Uap_Vert", objet),
                          uw_horizontal_protege=_nombre(element, "Uap_Horiz"),
                          sw_protege=sum(_nombre(element, b, 0.0) for b in ("Sw1_ap", "Sw2_ap", "Sw3_ap")),
                          sw2_protege=_nombre(element, "Sw2_ap", 0.0), sw3_protege=_nombre(element, "Sw3_ap", 0.0),
                          tl_protege=_nombre(element, "Tli_ap"))
    elif choix != SANS_PROTECTION:
        cle = "baies à store vénitien (lues sans protection mobile)"
        non_repris[cle] = non_repris.get(cle, 0) + 1
    # Ouverture pour la surventilation naturelle : lue en gestion manuelle (seule traitée par l'outil)
    ouvrable = _texte(element, "Baie_ouvrable", "0") == "1" and _nombre(element, "Rouv_Max", 0.0) > 0
    bruit = _texte(element, "Exp_BR")
    if ouvrable and _texte(element, "Has_Gestion_Auto_Ouverture", "0") != "0":
        cle = "baies : ouverture automatique (lue en gestion manuelle)"
        non_repris[cle] = non_repris.get(cle, 0) + 1
    if _texte(element, "PM2", "0") == "1":
        cle = "baies : seconde protection mobile (anti-éblouissement)"
        non_repris[cle] = non_repris.get(cle, 0) + 1
    return Baie(nom, _exiger(element, "Ab", objet), orientation_deg=_exiger(element, "Alpha", objet),
                inclinaison_deg=_exiger(element, "Beta", objet),
                uw=_exiger(element, "Usp_Vert", objet), uw_horizontal=_nombre(element, "Usp_Horiz"),
                sw_c=_exiger(element, "Sw1_sp_c", objet) + sw2_c + sw3_c, sw2_c=sw2_c,
                sw_e=_exiger(element, "Sw1_sp_e", objet) + sw2_e + sw3_e, sw2_e=sw2_e,
                tl=_nombre(element, "Tli_sp"), largeur_m=largeur, hauteur_m=hauteur, masques=masques,
                ouvrable=ouvrable, ratio_ouverture_max=_nombre(element, "Rouv_Max") if ouvrable else None,
                exposition_bruit=("BR" + bruit) if bruit in ("1", "2", "3") else None, **protection)


def _decrire_baie(element, cle):
    """Ligne de Reference.baies : la baie telle que l'étude la décrit, protections et ouverture comprises."""
    def somme(*balises):
        return sum(_nombre(element, balise, 0.0) for balise in balises)

    return dict(cle, surface_m2=_nombre(element, "Ab"), orientation_deg=_nombre(element, "Alpha"),
                inclinaison_deg=_nombre(element, "Beta"),
                u_sp=_nombre(element, "Usp_Vert"), u_ap=_nombre(element, "Uap_Vert"),
                sw_sp_c=somme("Sw1_sp_c", "Sw2_sp_c", "Sw3_sp_c"), sw_sp_e=somme("Sw1_sp_e", "Sw2_sp_e", "Sw3_sp_e"),
                sw_ap=somme("Sw1_ap", "Sw2_ap", "Sw3_ap"), sw2_ap=_nombre(element, "Sw2_ap", 0.0),
                tl_sp=_nombre(element, "Tli_sp"), tl_ap=_nombre(element, "Tli_ap"),
                protection_exterieure=_texte(element, "Prot_Ext") == "1",
                gestion_protection=_texte(element, "Choix_PM_GPM"),
                ouvrable=_texte(element, "Baie_ouvrable") == "1", rouv_max=_nombre(element, "Rouv_Max"),
                ouverture_auto=_texte(element, "Has_Gestion_Auto_Ouverture") == "1",
                ouverture_hiver=_texte(element, "Param_OuvBaie_Hiver"),
                ouverture_mi_saison=_texte(element, "Param_OuvBaie_MiSaison"),
                ouverture_ete=_texte(element, "Param_OuvBaie_Ete"))


def _lire_inertie(element):
    """Champs d'inertie du Groupe de l'outil à partir de la balise Inertie du moteur."""
    if element is None:
        return {}
    code = _texte(element, "Type_Inertie_Quotidienne")
    if code == INERTIE_SAISIE:
        # Valeurs saisies : l'inertie séquentielle l'est aussi (elle ne joue qu'en Th-D)
        champs = {"inertie_quotidienne": "personnalisee",
                  "amq_surf": _exiger(element, "Amq_surf", "l'inertie"),
                  "cmq_surf": _exiger(element, "Cmq_surf", "l'inertie")}
        ams, cms = _nombre(element, "Ams_surf"), _nombre(element, "Cms_surf")
        if ams and cms:
            champs.update(inertie_sequentielle="personnalisee", ams_surf=ams, cms_surf=cms)
        return champs
    if code not in INERTIES_QUOTIDIENNES:
        raise ValueError(f"RSET : Type_Inertie_Quotidienne « {code} » inconnu")
    return {"inertie_quotidienne": INERTIES_QUOTIDIENNES[code]}


def _lire_groupe(element, nom, zone, nb_logements, coefficients_b, non_repris, cle, lignes_baies):
    """Groupe du moteur → Groupe de l'outil."""
    def enfants(collection, balise):
        parent = element.find(collection)
        return list(parent.iter(balise)) if parent is not None else []

    parois = enfants("Paroi_opaque_Collection", "Paroi_Opaque")
    baies = enfants("Baie_Collection", "Baie")
    lineaires = enfants("Lineaire_Collection", "Lineaire")
    noms_parois = _noms_uniques([_texte(p, "Name", "Paroi") for p in parois])
    noms_baies = _noms_uniques([_texte(b, "Name", "Baie") for b in baies])
    noms_ponts = _noms_uniques([_texte(pt, "Name", "Pont thermique") for pt in lineaires])

    lignes_baies.extend(_decrire_baie(b, dict(cle, groupe=nom, baie=n)) for b, n in zip(baies, noms_baies))

    ponts = []
    for pont, nom_pont in zip(lineaires, noms_ponts):
        espace = _texte(pont, "Id_Et", SANS_ESPACE_TAMPON)
        b = coefficients_b.get(espace, 1.0) if espace != SANS_ESPACE_TAMPON else 1.0
        ponts.append(PontThermique(nom_pont, _exiger(pont, "Ll", f"le pont thermique « {nom_pont} »"),
                                   _exiger(pont, "Psil", f"le pont thermique « {nom_pont} »") * b))
    # Ce que l'outil ne modélise pas encore, compté pour le compte rendu
    for cle, nombre in (("ponts thermiques : flux solaires (Sf_cl, Sf_el) et masques", len(lineaires)),
                        ("groupes : entrées d'air (absentes du calcul du Bbio)", 1)):
        non_repris[cle] = non_repris.get(cle, 0) + nombre

    return Groupe(nom, _exiger(element, "SHAB", f"le groupe « {nom} »"),
                  traversant=_texte(element, "Delta_trav_surv", _texte(zone, "Is_Traversant", "0")) == "1",
                  hauteur_tirage_m=_nombre(element, "Httf") if _texte(element, "Def_Httf", "1") == "0" else None,
                  parois=[_lire_paroi(p, n, coefficients_b, non_repris) for p, n in zip(parois, noms_parois)],
                  baies=[_lire_baie(b, n, non_repris) for b, n in zip(baies, noms_baies)],
                  volume_m3=_nombre(element, "V"), ponts_thermiques=ponts,
                  debit_ventilation_m3h=_nombre(element, "Qv_occ_BBIO", 0.0), nb_logements=nb_logements,
                  climatise=_texte(element, "Is_Climatise", "0") == "1",
                  exposition_bruit="BR" + _texte(element, "Exp_BR_Groupe", "1"),
                  permeabilite_q4pa=(_nombre(element.find("Permeabilite"), "Q4PaSurf")
                                     if element.find("Permeabilite") is not None else None),
                  **_lire_inertie(element.find("Inertie")))


def _repartir_logements(nb_logements, surfaces):
    """Logements d'une zone répartis entre ses groupes, au prorata des surfaces (au moins un par groupe)."""
    if len(surfaces) == 1:
        return [nb_logements]
    total = sum(surfaces)
    parts = [max(1, round(nb_logements * s / total)) for s in surfaces]
    parts[parts.index(max(parts))] += nb_logements - sum(parts)       # le plus grand groupe absorbe l'arrondi
    return parts


def _lire_projet(racine, non_repris, lignes_baies):
    entree = racine.find("RSET/Entree_Projet")
    if entree is None:
        raise ValueError("RSET : balise RSET/Entree_Projet introuvable (ce fichier n'est pas un RSET)")
    batiments = []
    elements_batiments = list(entree.iter("Batiment"))
    noms_batiments = _noms_uniques([_texte(b, "Name", f"Bâtiment {i + 1}") for i, b in enumerate(elements_batiments)])
    for bat, nom_batiment in zip(elements_batiments, noms_batiments):
        coefficients_b = {_texte(et, "Index"): _exiger(et, "b_et_ns", "un espace tampon")
                          for et in bat.iter("Espace_Tampon_Non_Solarise")}
        solarises = sum(1 for e in bat.iter() if e.tag.startswith("Espace_Tampon_Solarise"))
        if solarises:
            non_repris["espaces tampons solarisés"] = non_repris.get("espaces tampons solarisés", 0) + solarises
        zones = []
        elements_zones = [z for z in bat.iter("Zone") if z.find("Groupe_Collection") is not None]
        for zone, nom_zone in zip(elements_zones, _noms_uniques([_texte(z, "Name", "Zone") for z in elements_zones])):
            if _texte(zone, "Usage") != USAGE_LOGEMENT_COLLECTIF:
                cle = f"zones d'un autre usage que le logement collectif (usage {_texte(zone, 'Usage')})"
                non_repris[cle] = non_repris.get(cle, 0) + 1
                continue
            groupes = list(zone.find("Groupe_Collection").iter("Groupe"))
            noms = _noms_uniques([_texte(g, "Name", "Groupe") for g in groupes])
            logements = _repartir_logements(int(_exiger(zone, "NB_logement", f"la zone « {nom_zone} »")),
                                            [_exiger(g, "SHAB", "un groupe") for g in groupes])
            cle = {"batiment": nom_batiment, "zone": nom_zone}
            zones.append(Zone(nom_zone, groupes=[_lire_groupe(g, n, zone, nl, coefficients_b, non_repris, cle,
                                                              lignes_baies)
                                                 for g, n, nl in zip(groupes, noms, logements)],
                              hauteur_sous_plafond_m=_nombre(zone, "HSP_moy"),
                              hauteur_m=_nombre(zone, "Hauteur_Zone") or None,
                              hauteur_moyenne_m=(_nombre(zone, "Hauteur", 0.0) + 0.5 * _nombre(zone, "Hauteur_Zone")
                                                 if _nombre(zone, "Hauteur_Zone") else None)))
        batiments.append(Batiment(nom_batiment, zones=zones))
    simu = entree.find("Simu")
    altitude = _nombre(simu, "Altitude", 0.0) if simu is not None else 0.0
    nom = _texte(racine.find("RSET/Sortie_Projet"), "Name", "Étude") if racine.find("RSET/Sortie_Projet") is not None \
        else "Étude"
    return Projet(nom, _zone_climatique(racine), altitude, batiments)


# ============================================================
# 3. SORTIES : RÉSULTATS DE L'ÉTUDE
# ============================================================
def _mensuel(element, prefixe):
    """Douze valeurs mensuelles d'une sortie « <prefixe>_mois » ; liste vide si elle manque."""
    bloc = element.find(f"{prefixe}_mois")
    if bloc is None:
        return {}
    return {int(_texte(s, "Mois")): _nombre(s, "Valeur") for s in bloc.iter("Sortie_Mensuelle")}


def _sorties(element, cle, niveau, mensuels):
    """Besoins annuels, Bbio et Bbio max d'un groupe, d'une zone ou d'un bâtiment ; les mois vont dans « mensuels »."""
    ligne = dict(cle, sref_m2=_nombre(element, "O_SREF"), bbio_max=_nombre(element, "O_Bbio_Max"))
    par_mois = {}
    for nom, prefixe in BESOINS.items():
        ligne[nom] = _nombre(element, f"{prefixe}_annuel")
        par_mois[nom] = _mensuel(element, prefixe)
    for mois in MOIS:
        if any(mois in valeurs for valeurs in par_mois.values()):
            mensuels.append(dict(cle, niveau=niveau, mois=mois,
                                 **{nom: valeurs.get(mois) for nom, valeurs in par_mois.items()}))
    return ligne


def _lire_reference(racine, projet, non_repris, lignes_baies):
    sortie = racine.find("RSET/Sortie_Projet")
    groupes, zones, batiments, mensuels, confort = [], [], [], [], []
    if sortie is not None:
        for bat in sortie.iter("Sortie_Batiment_B"):
            cle_bat = {"batiment": _texte(bat, "Name")}
            batiments.append(_sorties(bat, cle_bat, "batiment", mensuels))
            for zone in bat.iter("Sortie_Zone_B"):
                cle_zone = dict(cle_bat, zone=_texte(zone, "Name"))
                ligne = _sorties(zone, cle_zone, "zone", mensuels)
                ligne["usage"] = _texte(zone, "Usage")
                ligne.update({nom: _nombre(zone, balise) for nom, balise in {**DEPERDITIONS, **SURFACES}.items()})
                zones.append(ligne)
                for groupe in zone.iter("Sortie_Groupe_B"):
                    cle_groupe = dict(cle_zone, groupe=_texte(groupe, "Name"))
                    ligne = _sorties(groupe, cle_groupe, "groupe", mensuels)
                    ligne["climatise"] = _texte(groupe, "Is_Climatise") == "1"
                    ligne.update({nom: _nombre(groupe, balise) for nom, balise in MODULATIONS.items()})
                    groupes.append(ligne)
        # Confort d'été : un bloc par groupe (répété dans plusieurs collections : le premier suffit)
        vus = set()
        for groupe in sortie.iter("Sortie_Groupe_D"):
            nom = _texte(groupe, "Name")
            if nom not in vus and _nombre(groupe, "O_NbDegresHeures") is not None:
                vus.add(nom)
                confort.append(dict(groupe=nom, **{c: _nombre(groupe, balise) for c, balise in CONFORT.items()}))
    infos = {"fichier_logiciel": next((e.text for e in racine.iter("editeur") if e.text), None),
             "version_moteur": _texte(sortie, "Version") if sortie is not None else None,
             "zone_climatique": projet.zone_climatique, "altitude_m": projet.altitude_m,
             "altitude_corrigee_m": _nombre(sortie, "Altitude") if sortie is not None else None,
             "non_repris": dict(non_repris)}
    return Reference(groupes=pd.DataFrame(groupes), zones=pd.DataFrame(zones), batiments=pd.DataFrame(batiments),
                     mensuel=pd.DataFrame(mensuels), baies=pd.DataFrame(lignes_baies), confort=pd.DataFrame(confort), infos=infos)


# ============================================================
# 4. LECTURE D'UN FICHIER
# ============================================================
def lire_rset(chemin):
    """Lit un RSET (XML d'une étude RE2020) : (Projet de l'outil, Reference des résultats de l'étude).

    Seules les zones de logements collectifs sont reprises. Les noms en double (deux baies de même nom dans un
    groupe) sont rendus uniques par un suffixe « (2) ».
    """
    racine = ET.parse(chemin).getroot()
    non_repris, lignes_baies = {}, []
    projet = _lire_projet(racine, non_repris, lignes_baies)
    return projet, _lire_reference(racine, projet, non_repris, lignes_baies)
