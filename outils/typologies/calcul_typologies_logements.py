"""
Typologies Bon / Médian / Nul des caractéristiques d'enveloppe des logements
(collectif + maison individuelle) à partir de caracteristiques_rset.csv.

Usage : python -I calcul_typologies_logements.py <csv_entree> <csv_sortie>

Méthode
- Périmètre : usage = logement collectif ou maison individuelle (même traitement).
- Doublons stricts écartés (colonne copie_de renseignée).
- Une seule version retenue par opération (liste EMPREINTES_RETENUES).
- Quantiles pondérés par la SHAB de la zone (shab_m2).
- Performant / Faible = P25 / P75 du côté favorable / défavorable, Moyen = P50, puis valeurs
  arrondies avec le pas le plus grossier (0,1 / 0,05 / 0,01) qui garde les niveaux distincts.
- Valeurs vides exclues variable par variable (ex. pas de toiture, pas de protection).
"""
import sys
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# RÉGLAGES (tout est regroupé ici)
# ---------------------------------------------------------------------------
USAGES_LOGEMENT = ["logement collectif", "maison individuelle"]
COL_POIDS = "shab_m2"            # pondération des quantiles
Q_FAVORABLE = 0.25               # P25 : côté favorable pour une variable « bas = bon »
Q_MEDIAN = 0.50
Q_DEFAVORABLE = 0.75             # P75 : côté défavorable
DECIMALES = 2                    # décimales des min / max affichés
PAS_ARRONDI = [0.1, 0.05, 0.01]  # pas d'arrondi essayés, du plus grossier au plus fin
TOLERANCE_REL = 0.06             # erreur relative maximale acceptée par l'arrondi
NOMS_NIVEAUX = ("performant", "moyen", "faible")

# Une version par opération : empreinte_entrees -> nom de l'opération
EMPREINTES_RETENUES = {
    "ca9da388": "SPGL ouest (maisons)",
    "267474db": "Hébert RS2E (Paris)",
    "be8e17ab": "Nice Brancolar - Bât A (version 2026-10-12)",
    "5ad22e2f": "Nice Brancolar - Bât B",
    "b5852b48": "SETE RSENV",
    "5b08d9f1": "rsee.xml (Bât A, B, C)",
}
# Versions alternatives écartées (même opération), pour information
EMPREINTES_ECARTEES = {
    "3a448098": "SETE monozone (même bâtiment que SETE RSENV)",
    "ac56287b": "SETE scénario 2",
    "36cf825a": "Hébert scénario 2",
    "1d43e15d": "Nice Bât A - V5 (ancienne version)",
    "3ce265ba": "Nice Bât A - 2026-4-15 (ancienne version)",
}

# variable : (colonne, libellé, unité, sens)  sens = "bas" (bas = bon) ou "haut" (haut = bon)
VARIABLES = [
    ("uw", "Uw baie", "W/m².K", "bas"),
    ("sw_e", "Sw baie été (menuiserie + vitrage, sans protection)", "-", "bas"),
    ("tl", "Transmission lumineuse", "-", "haut"),
    ("sw_protege", "Facteur solaire, protection baissée", "-", "bas"),
    ("uw_protege", "Uw, protection baissée", "W/m².K", "bas"),
    ("u_mur", "U des murs", "W/m².K", "bas"),
    ("u_toiture", "U de la toiture", "W/m².K", "bas"),
    ("u_plancher_bas", "U du plancher bas", "W/m².K", "bas"),
    ("psi_moyen", "Ponts thermiques (psi moyen, tous ponts)", "W/m.K", "bas"),
    ("ventilation_m3h_m2", "Ventilation (par m² habitable)", "m³/h.m²", "haut"),
    ("permeabilite_q4pa", "Perméabilité à l'air Q4Pa-surf", "m³/h.m²", "bas"),
    ("ratio_ouverture_max", "Part ouvrante de la baie (ratio d'ouverture max)", "-", "haut"),
]

# Remarques ajoutées au CSV (colonne -> texte)
REMARQUES = {
    "sw_e": "bas = performant en été seulement ; en hiver, un Sw élevé est préférable",
    "sw_protege": "bas = performant en été seulement ; en hiver, un Sw élevé est préférable",
    "psi_moyen": "tous ponts thermiques confondus (pas seulement les planchers)",
    "ratio_ouverture_max": "ratio d'ouverture maximale de la baie",
}

# Inertie quotidienne : classes ordonnées (Th-I, tableau 11 du fascicule inertie)
CLASSES_INERTIE = ["très légère", "légère", "moyenne", "lourde", "très lourde"]
# Colonnes (bornes basses de Cmq_surf, kJ/m²K) et lignes (bornes basses de Amq_surf)
BORNES_CMQ = [80, 110, 165, 220, 260, 310, 330, 350, 370, 500]
BORNES_AMQ = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
# Classes (0 = très légère ... 4 = très lourde) ; une ligne par tranche Amq
TABLE_INERTIE = [
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
    [0, 0, 1, 2, 2, 2, 2, 2, 2, 2],
    [0, 1, 2, 2, 2, 2, 2, 3, 3, 3],
    [0, 1, 2, 2, 3, 3, 3, 3, 3, 3],
    [0, 1, 2, 3, 3, 3, 3, 3, 3, 4],
    [0, 1, 2, 3, 3, 3, 3, 3, 4, 4],
    [0, 1, 2, 3, 3, 3, 3, 4, 4, 4],
    [0, 1, 2, 3, 3, 3, 4, 4, 4, 4],
    [0, 1, 2, 3, 3, 4, 4, 4, 4, 4],
]
CORRESPONDANCE_NOMS = {"légère": 1, "moyenne": 2, "lourde": 3}  # classes saisies directement


# ---------------------------------------------------------------------------
# FONCTIONS
# ---------------------------------------------------------------------------
def en_nombre(serie):
    """Convertit une colonne texte (décimale virgule, notation 1,2e+04) en float."""
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def quantile_pondere(valeurs, poids, q):
    """Quantile pondéré avec interpolation (convention des milieux de poids cumulés)."""
    ordre = np.argsort(valeurs)
    v, w = np.asarray(valeurs)[ordre], np.asarray(poids)[ordre]
    cumul = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, cumul, v))


def quantile_discret(valeurs, poids, q):
    """Quantile pondéré pour une variable ordinale : première valeur dont le cumul atteint q."""
    ordre = np.argsort(valeurs)
    v, w = np.asarray(valeurs)[ordre], np.asarray(poids)[ordre]
    cumul = np.cumsum(w) / w.sum()
    return v[np.searchsorted(cumul, q - 1e-12)]


def classe_inertie(ligne):
    """Indice de classe (0..4) : classe saisie, ou calculée via Cmq/Amq si « personnalisée »."""
    nom = ligne["inertie_quotidienne"]
    if nom in CORRESPONDANCE_NOMS:
        return CORRESPONDANCE_NOMS[nom]
    if nom == "personnalisee":
        cmq, amq = ligne["cmq_surf"], ligne["amq_surf"]
        if pd.isna(cmq) or pd.isna(amq):
            return np.nan
        col = max(np.searchsorted(BORNES_CMQ, cmq, side="right") - 1, 0)
        lig = max(np.searchsorted(BORNES_AMQ, amq, side="right") - 1, 0)
        return TABLE_INERTIE[lig][col]
    return np.nan


def arrondir_niveaux(perf, moy, faib):
    """Arrondit les 3 niveaux avec le pas le plus grossier qui garde les niveaux distincts
    (hors égalités réelles) et une erreur relative <= TOLERANCE_REL. Renvoie (perf, moy, faib, pas)."""
    brut = [perf, moy, faib]
    nb_distincts = len({round(x, 3) for x in brut})
    for pas in PAS_ARRONDI:
        arr = [round(round(x / pas) * pas, 4) for x in brut]
        erreur = max(abs(a - b) / abs(b) for a, b in zip(arr, brut))
        if len(set(arr)) == nb_distincts and erreur <= TOLERANCE_REL:
            return (*arr, pas)
    pas = PAS_ARRONDI[-1]
    return (*[round(round(x / pas) * pas, 4) for x in brut], pas)


def fmt_nombre(x, decimales=None):
    """Texte avec virgule décimale, sans zéros inutiles (1,10 -> 1,1)."""
    texte = f"{x:.{decimales}f}" if decimales is not None else f"{x:.4f}".rstrip("0").rstrip(".")
    return texte.replace(".", ",")


# ---------------------------------------------------------------------------
# TRAITEMENT
# ---------------------------------------------------------------------------
def charger_zones(chemin_entree):
    """Lit le CSV et renvoie les zones logement retenues (colonnes numériques converties)."""
    df = pd.read_csv(chemin_entree, sep=";", dtype=str, encoding="utf-8-sig")

    # 1. Périmètre logements, sans doublons stricts
    df = df[df["usage"].isin(USAGES_LOGEMENT)]
    df = df[df["copie_de"].isna() | (df["copie_de"].str.strip() == "")]

    # 2. Une version par opération (alerte si une empreinte n'est pas connue)
    inconnues = set(df["empreinte_entrees"]) - set(EMPREINTES_RETENUES) - set(EMPREINTES_ECARTEES)
    if inconnues:
        print("ATTENTION : empreintes logement non classées :", inconnues)
    df = df[df["empreinte_entrees"].isin(EMPREINTES_RETENUES)].copy()

    # 3. Conversion numérique
    colonnes_num = [c for c, *_ in VARIABLES] + [COL_POIDS, "cmq_surf", "amq_surf"]
    for c in colonnes_num:
        df[c] = en_nombre(df[c])
    print(f"{len(df)} zones, {df['empreinte_entrees'].nunique()} opérations, "
          f"SHAB totale {df[COL_POIDS].sum():.0f} m²")
    df["classe_inertie"] = df.apply(classe_inertie, axis=1)
    return df


def main(chemin_entree, chemin_sortie):
    df = charger_zones(chemin_entree)

    # 4. Quantiles des variables numériques
    lignes = []
    for col, libelle, unite, sens in VARIABLES:
        d = df[[col, COL_POIDS, "empreinte_entrees"]].dropna()
        q_bon, q_nul = (Q_FAVORABLE, Q_DEFAVORABLE) if sens == "bas" else (Q_DEFAVORABLE, Q_FAVORABLE)
        brut = [quantile_pondere(d[col], d[COL_POIDS], q) for q in (q_bon, Q_MEDIAN, q_nul)]
        perf, moy, faib, _ = arrondir_niveaux(*brut)
        lignes.append({
            "variable": libelle, "colonne_source": col, "unite": unite,
            "sens": "bas = performant" if sens == "bas" else "haut = performant",
            "n_zones": len(d), "n_operations": d["empreinte_entrees"].nunique(),
            NOMS_NIVEAUX[0]: fmt_nombre(perf), NOMS_NIVEAUX[1]: fmt_nombre(moy),
            NOMS_NIVEAUX[2]: fmt_nombre(faib),
            "remarque": REMARQUES.get(col, ""),
        })

    # 5. Inertie (ordinale : haut = bon)
    d = df[["classe_inertie", COL_POIDS, "empreinte_entrees"]].dropna()
    nom = lambda i: CLASSES_INERTIE[int(i)]
    lignes.append({
        "variable": "Inertie quotidienne", "colonne_source": "inertie_quotidienne (+cmq_surf, amq_surf)",
        "unite": "classe", "sens": "haut = performant",
        "n_zones": len(d), "n_operations": d["empreinte_entrees"].nunique(),
        NOMS_NIVEAUX[0]: nom(quantile_discret(d["classe_inertie"], d[COL_POIDS], Q_DEFAVORABLE)),
        NOMS_NIVEAUX[1]: nom(quantile_discret(d["classe_inertie"], d[COL_POIDS], Q_MEDIAN)),
        NOMS_NIVEAUX[2]: nom(quantile_discret(d["classe_inertie"], d[COL_POIDS], Q_FAVORABLE)),
        "remarque": "classes Th-I ; « personnalisée » convertie via cmq_surf et amq_surf",
    })

    # 6. Écriture : séparateur ;, décimale ,, UTF-8 avec BOM (Excel FR)
    res = pd.DataFrame(lignes)
    # les niveaux sont déjà du texte (virgule décimale, colonne mixte avec les classes d'inertie)
    res.to_csv(chemin_sortie, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(res.to_string(index=False))
    print("\nDétail inertie (zones) :")
    print(df[["empreinte_entrees", "zone", "inertie_quotidienne", "cmq_surf", "amq_surf",
              "classe_inertie", COL_POIDS]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
