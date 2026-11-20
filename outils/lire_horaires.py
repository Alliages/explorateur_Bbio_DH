r"""
============================================================
 LIRE LES SORTIES HORAIRES D'UN MOTEUR TH-BCE (COMETH)
============================================================
 Un calcul réglementaire peut écrire, pour chaque objet du
 projet, toutes ses grandeurs heure par heure : un fichier CSV
 par mode et par objet, par exemple

     Th_B_Bat_1_Zone_1_Groupe_1.csv     groupe 1 (mode Th-B)
     Th_DC_Bat_1_Zone_2_Groupe_2.csv    groupe 2 (mode Th-D)
     Th_B_Impact_Ss_Apports_Sol_...     variante sans soleil

 Format : UTF-8 avec BOM, séparateur « ; », virgule décimale,
 quatre lignes d'en-tête puis une ligne par heure (8 760) :

     ligne 1   objet       COMETH_Data_Sortie_Groupe:1,
                           COMETH_Data_Sortie_Baie:9…
     ligne 2   variable    O_Temp_op_moy, O_B_Ch_Horaire…
     ligne 3   libellé     texte libre
     ligne 4   unité       °C, Wh, W…

 Un fichier de groupe compte 140 grandeurs du groupe et 12 par
 baie : il dépasse 260 Mo pour 300 baies. On ne lit donc que
 les colonnes demandées, et on les garde dans un cache (pickle
 de pandas, dossier _resultats/, hors dépôt) : la seconde
 lecture est immédiate.

 Les fichiers restent hors du dépôt (../_RSEE/Horaires).
============================================================
"""

import re
from pathlib import Path

import pandas as pd

# ============================================================
# RÉGLAGES
# ============================================================
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_HORAIRES = RACINE.parent / "_RSEE" / "Horaires"    # un dossier par calcul
DOSSIER_CACHE = RACINE / "_resultats" / "horaires_cache"   # colonnes déjà lues (hors dépôt)
LIGNES_ENTETE = 4                                          # objet, variable, libellé, unité
ENCODAGE = "utf-8-sig"
MOTIF_OBJET = re.compile(r"(?:COMETH_Data_Sortie_)?(?P<type>[A-Za-z_]+?):(?P<numero>\d+)$")
MOTIF_GROUPE = re.compile(r"^Th_(?P<mode>B|C|DC)_(?P<variante>(?:Impact_\w+?_)?)Bat_(?P<batiment>\d+)"
                          r"_Zone_(?P<zone>\d+)_Groupe_(?P<groupe>\d+)\.csv$")


# ============================================================
# 1. EN-TÊTE : QUELLES COLONNES CONTIENT LE FICHIER ?
# ============================================================
def lire_entete(chemin):
    """Les quatre lignes d'en-tête d'un fichier horaire, une ligne par colonne.

    Sortie : colonnes position, objet (texte brut), type (Groupe, Baie, Ventilation_Mecanique…), numero,
    variable, libelle, unite et nom. « nom » est unique dans le fichier : la variable seule pour le premier
    objet de chaque variable, « variable:numéro » pour les autres objets du même type (les baies), avec un
    suffixe « #2 », « #3 »… si la même variable revient sous le même objet (O_Einat, par exemple).
    """
    with open(chemin, encoding=ENCODAGE) as f:
        lignes = [f.readline().rstrip("\r\n").split(";") for _ in range(LIGNES_ENTETE)]
    n = max(len(l) for l in lignes)
    objets, variables, libelles, unites = (l + [""] * (n - len(l)) for l in lignes)
    lignes_entete, vus, premier_objet = [], {}, {}
    for position in range(n):
        objet, variable = objets[position].strip(), variables[position].strip()
        if not variable:
            continue                                # point-virgule final : colonne vide
        trouve = MOTIF_OBJET.search(objet)
        type_objet, numero = (trouve["type"], int(trouve["numero"])) if trouve else (objet, 0)
        # Nom unique : la variable du premier objet, « variable:numéro » pour les suivants
        premier = premier_objet.setdefault((type_objet, variable), numero)
        nom = variable if numero == premier else f"{variable}:{numero}"
        vus[nom] = vus.get(nom, 0) + 1
        if vus[nom] > 1:
            nom = f"{nom}#{vus[nom]}"
        lignes_entete.append({"position": position, "objet": objet, "type": type_objet, "numero": numero,
                              "variable": variable, "libelle": libelles[position].strip(),
                              "unite": unites[position].strip(), "nom": nom})
    return pd.DataFrame(lignes_entete)


def noms_baies(entete, variable):
    """Noms des colonnes d'une variable de baie (O_Rouv, O_Rprot1_b…), une par baie du groupe."""
    return entete.loc[(entete["type"] == "Baie") & (entete["variable"] == variable), "nom"].tolist()


# ============================================================
# 2. LECTURE DES COLONNES, AVEC CACHE
# ============================================================
def _chemin_cache(chemin):
    chemin = Path(chemin)
    return DOSSIER_CACHE / chemin.parent.name / (chemin.stem + ".pkl")


def _en_nombres(table):
    """Colonnes en nombres : virgule décimale déjà traitée ; True / False (O_Relance) en 1 / 0."""
    for colonne in table.columns:
        if table[colonne].dtype == object:
            texte = table[colonne].astype(str).str.strip()
            table[colonne] = pd.to_numeric(texte.replace({"True": "1", "False": "0"}).str.replace(",", "."),
                                           errors="coerce")
    return table


def lire_colonnes(chemin, noms, cache=True):
    """Colonnes « noms » (voir lire_entete) d'un fichier horaire, une ligne par heure.

    Les colonnes déjà lues viennent du cache ; les autres sont lues dans le CSV, en une passe, puis ajoutées
    au cache. Un nom absent du fichier lève une erreur qui les cite tous.
    """
    chemin = Path(chemin)
    noms = list(dict.fromkeys(noms))
    fichier_cache = _chemin_cache(chemin)
    deja = pd.DataFrame()
    if cache and fichier_cache.exists() and fichier_cache.stat().st_mtime >= chemin.stat().st_mtime:
        deja = pd.read_pickle(fichier_cache)
    manquants = [n for n in noms if n not in deja.columns]
    if manquants:
        entete = lire_entete(chemin).set_index("nom")
        inconnus = [n for n in manquants if n not in entete.index]
        if inconnus:
            raise KeyError(f"{chemin.name} : colonnes absentes : {', '.join(inconnus)}")
        positions = entete.loc[manquants, "position"].astype(int).tolist()
        lues = pd.read_csv(chemin, sep=";", decimal=",", header=None, skiprows=LIGNES_ENTETE,
                           usecols=positions, encoding=ENCODAGE, low_memory=False)
        lues = _en_nombres(lues.rename(columns=dict(zip(positions, manquants))))
        deja = lues if deja.empty else pd.concat([deja.reset_index(drop=True), lues], axis=1)
        if cache:
            fichier_cache.parent.mkdir(parents=True, exist_ok=True)
            deja.to_pickle(fichier_cache)
    return deja[noms].copy()


# ============================================================
# 3. FICHIERS D'UN CALCUL
# ============================================================
def fichiers_groupes(dossier, mode="B", variante=""):
    """Fichiers de groupe d'un calcul, dans l'ordre (bâtiment, zone, groupe) des numéros du moteur.

    mode       « B » (Th-B), « C » (Th-C) ou « DC » (Th-D)
    variante   « » pour le calcul réglementaire, « Impact_Ss_Apports_Sol_ » (sans soleil) ou
               « Impact_Ss_Apports_Sol_Lum_ » (sans soleil ni lumière) en mode Th-B
    Sortie : liste de (numéro de bâtiment, numéro de zone, numéro de groupe, chemin). Le numéro de groupe
    court sur tout le bâtiment (Zone_2_Groupe_2), pas sur la zone.
    """
    trouves = []
    for chemin in Path(dossier).glob(f"Th_{mode}_*Groupe_*.csv"):
        m = MOTIF_GROUPE.match(chemin.name)
        if m and m["mode"] == mode and m["variante"] == variante:
            trouves.append((int(m["batiment"]), int(m["zone"]), int(m["groupe"]), chemin))
    return sorted(trouves)


def lire_resultats_th_dc(dossier):
    """Degrés-heures par groupe du fichier Resultats_Th_DC.csv : liste de (DH en °C.h, heures d'inconfort)."""
    resultats = []
    with open(Path(dossier) / "Resultats_Th_DC.csv", encoding=ENCODAGE) as f:
        for ligne in f:
            champs = ligne.rstrip("\r\n").split(";")
            if len(champs) > 5 and champs[3].startswith("Groupe"):
                resultats.append((float(champs[4].replace(",", ".")), int(champs[5])))
    # Le fichier écrit deux fois le même tableau : on garde la première moitié
    return resultats[:len(resultats) // 2] if len(resultats) % 2 == 0 else resultats
