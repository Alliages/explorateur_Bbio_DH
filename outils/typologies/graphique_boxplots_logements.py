"""
Boxplots pondérés (par SHAB) des variables d'enveloppe des logements.

Usage : python -I graphique_boxplots_logements.py <csv_entree> <png_sortie>

Lecture d'un panneau
- Boîte : P25 à P75 ; trait épais : médiane (P50) ; moustaches : P10 à P90.
- Étiquettes : « performant » et « faible » aux bords de la boîte (P25 / P75 selon le sens),
  « moyen » sur la médiane, avec leurs valeurs (arrondies).
- Points : une zone chacune, surface proportionnelle à la SHAB.
- Inertie (ordinale) : barre empilée des parts de SHAB par classe.
"""
import importlib.util
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# RÉGLAGES
# ---------------------------------------------------------------------------
COULEUR_BOITE = "#cfe0f5"
COULEUR_TRAIT = "#2b5c9e"
COULEUR_TEXTE = "#222222"
COULEUR_SECOND = "#666666"
COULEURS_INERTIE = ["#eaf1fa", "#c4d8f0", "#8fb4e0", "#4f86c6", "#1f4f8f"]  # 1 teinte, clair -> foncé
COLONNES = 3
TAILLE_POINT_MAX = 160           # surface du plus gros point (SHAB max)
DPI = 160
MOUSTACHES = (0.10, 0.90)         # extrémités des moustaches (non étiquetées)

# Réutilise les fonctions et réglages du script de calcul (même dossier)
chemin_calcul = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calcul_typologies_logements.py")
spec = importlib.util.spec_from_file_location("calcul", chemin_calcul)
calcul = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calcul)


def panneau_numerique(ax, df, col, libelle, unite, sens):
    """Boxplot pondéré horizontal d'une variable numérique."""
    d = df[[col, calcul.COL_POIDS]].dropna()
    v, w = d[col].to_numpy(), d[calcul.COL_POIDS].to_numpy()
    qp = lambda q: calcul.quantile_pondere(v, w, q)
    p10, p50, p90 = qp(MOUSTACHES[0]), qp(0.50), qp(MOUSTACHES[1])
    p25, p75 = qp(calcul.Q_FAVORABLE), qp(calcul.Q_DEFAVORABLE)
    bon, nul = (p25, p75) if sens == "bas" else (p75, p25)

    # moustaches, boîte, médiane
    ax.hlines(0, p10, p90, color=COULEUR_TRAIT, lw=1.5, zorder=2)
    ax.add_patch(plt.Rectangle((p25, -0.28), p75 - p25, 0.56, fc=COULEUR_BOITE,
                               ec=COULEUR_TRAIT, lw=1.5, zorder=3))
    ax.vlines(p50, -0.28, 0.28, color=COULEUR_TEXTE, lw=3, zorder=4)
    for x in (p10, p90):
        ax.vlines(x, -0.14, 0.14, color=COULEUR_TRAIT, lw=1.5, zorder=2)

    # zones : points (surface ~ SHAB), décalés sous la boîte
    tailles = TAILLE_POINT_MAX * w / calcul.df_shab_max
    ax.scatter(v, np.full_like(v, -1.0), s=tailles, color=COULEUR_TRAIT, alpha=0.55,
               edgecolor="white", linewidth=0.8, zorder=5, clip_on=False)

    # étiquettes (valeurs en texte secondaire, noms en texte principal)
    fmt = calcul.fmt_nombre
    r_bon, r_med, r_nul, _ = calcul.arrondir_niveaux(bon, p50, nul)   # valeurs arrondies affichées
    # étiquettes au-dessus de la boîte, alignées vers l'extérieur pour ne pas se chevaucher
    for x, r, nom_niveau in ((bon, r_bon, calcul.NOMS_NIVEAUX[0]), (nul, r_nul, calcul.NOMS_NIVEAUX[2])):
        a_gauche = x == min(bon, nul)
        ax.annotate(f"{nom_niveau}\n{fmt(r)}", (x, 0.28), xytext=(0, 6), textcoords="offset points",
                    ha="right" if a_gauche else "left", va="bottom", fontsize=8.5,
                    multialignment="right" if a_gauche else "left",
                    color=COULEUR_TEXTE, linespacing=1.1)
    ax.text(p50, -0.34, f"{calcul.NOMS_NIVEAUX[1]}\n{fmt(r_med)}", ha="center", va="top", fontsize=8.5,
            color=COULEUR_SECOND, linespacing=1.1, zorder=6)

    ax.set_ylim(-1.3, 1.0)
    ax.set_yticks([])
    # marge pour que les étiquettes ne sortent pas du panneau
    marge = 0.22 * (max(v.max(), p90) - min(v.min(), p10) or 1)
    ax.set_xlim(min(v.min(), p10) - marge, max(v.max(), p90) + marge)
    titre = f"{libelle} ({unite})" if unite not in ("-", "") else libelle
    ax.set_title(f"{titre}\nn = {len(d)} zones", fontsize=9.5, color=COULEUR_TEXTE, loc="left")


def panneau_inertie(ax, df):
    """Barre empilée des parts de SHAB par classe d'inertie + Bon/Médian/Nul."""
    d = df[["classe_inertie", calcul.COL_POIDS]].dropna()
    total = d[calcul.COL_POIDS].sum()
    gauche = 0.0
    for i, nom in enumerate(calcul.CLASSES_INERTIE):
        part = d.loc[d["classe_inertie"] == i, calcul.COL_POIDS].sum() / total
        if part <= 0:
            continue
        ax.barh(0, part, left=gauche, height=0.5, color=COULEURS_INERTIE[i],
                edgecolor="white", linewidth=2)
        if part > 0.06:
            ax.text(gauche + part / 2, 0, f"{nom}\n{part:.0%}".replace("%", " %"), ha="center",
                    va="center", fontsize=8.5,
                    color="white" if i >= 3 else COULEUR_TEXTE)
        gauche += part
    q = lambda x: calcul.CLASSES_INERTIE[int(calcul.quantile_discret(d["classe_inertie"], d[calcul.COL_POIDS], x))]
    n = calcul.NOMS_NIVEAUX
    ax.text(0, -0.55, f"{n[0]} : {q(calcul.Q_DEFAVORABLE)}  ·  {n[1]} : {q(0.5)}  ·  {n[2]} : {q(calcul.Q_FAVORABLE)}",
            fontsize=8.5, color=COULEUR_TEXTE, ha="left", va="top")
    ax.set_xlim(0, 1)
    ax.set_ylim(-1.0, 1.0)
    ax.set_yticks([])
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0 %", "50 %", "100 %"])
    ax.set_title(f"Inertie quotidienne (part de SHAB par classe)\nn = {len(d)} zones",
                 fontsize=9.5, color=COULEUR_TEXTE, loc="left")


def main(chemin_entree, chemin_png):
    df = calcul.charger_zones(chemin_entree)
    calcul.df_shab_max = df[calcul.COL_POIDS].max()

    panneaux = len(calcul.VARIABLES) + 1
    lignes = int(np.ceil(panneaux / COLONNES))
    fig, axes = plt.subplots(lignes, COLONNES, figsize=(13, 2.7 * lignes))
    axes = axes.ravel()

    for ax, (col, libelle, unite, sens) in zip(axes, calcul.VARIABLES):
        panneau_numerique(ax, df, col, libelle, unite, sens)
    panneau_inertie(axes[len(calcul.VARIABLES)], df)
    for ax in axes[panneaux:]:
        ax.axis("off")

    for ax in axes[:panneaux]:
        for cote in ("top", "right", "left"):
            ax.spines[cote].set_visible(False)
        ax.spines["bottom"].set_color("#bbbbbb")
        ax.tick_params(axis="x", colors=COULEUR_SECOND, labelsize=8.5)
        ax.grid(axis="x", color="#e6e6e6", lw=0.8, zorder=0)
        ax.set_axisbelow(True)

    fig.suptitle("Logements : répartition des caractéristiques d'enveloppe (pondérée par la SHAB)",
                 x=0.01, ha="left", fontsize=13, color=COULEUR_TEXTE, y=0.995)
    fig.text(0.01, 0.962,
             f"{len(df)} zones · {df['empreinte_entrees'].nunique()} opérations · "
             f"{df[calcul.COL_POIDS].sum():,.0f} m² SHAB".replace(",", " ")
             + ". Boîte P25-P75 (performant / faible), trait épais = médiane (moyen), moustaches P10-P90 ; point = une zone (surface ~ SHAB).",
             fontsize=9, color=COULEUR_SECOND, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95), h_pad=2.2, w_pad=2.0)
    fig.savefig(chemin_png, dpi=DPI, facecolor="white")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
