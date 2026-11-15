"""
Graphique pédagogique (palette HUB) : performant / moyen / faible pour les logements.

Usage : python -I graphique_pedagogique_logements.py <csv_entree> <png_sortie>

Par variable : barre min-max, boîte P25-P75 (pondérée SHAB), repères performant / moyen / faible
(valeurs arrondies comme dans le CSV), flèche du sens de la performance. Pas de points individuels.
Réutilise les calculs de calcul_typologies_logements.py.
"""
import importlib.util
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# RÉGLAGES
# ---------------------------------------------------------------------------
JAUNE, ORANGE, NOIR = "#FABD4A", "#FA9600", "#000000"
NUIT, ARDOISE, CORAIL = "#283246", "#55739B", "#FF554B"
GRIS_TEXTE = "#444444"          # texte secondaire (nuance du noir)
GRIS_GRILLE = "#E4E7EC"
COULEUR_NIVEAU = {"performant": NUIT, "moyen": ORANGE, "faible": CORAIL}
FORME_NIVEAU = {"performant": "o", "moyen": "D", "faible": "s"}   # forme en plus de la couleur
# Classes d'inertie, de la moins à la plus performante
COULEURS_INERTIE = [CORAIL, ORANGE, JAUNE, ARDOISE, NUIT]
TEXTE_SUR_INERTIE = [NOIR, NOIR, NOIR, "white", "white"]
TEXTE_FLECHE = "plus performant"

# Regroupement des variables en 4 colonnes (colonne source du calcul)
GROUPES = [
    ("Les baies : isolation et ouverture", ["uw", "uw_protege", "ratio_ouverture_max"]),
    ("Les baies : soleil et lumière", ["sw_e", "sw_protege", "tl"]),
    ("Les parois opaques", ["u_mur", "u_toiture", "u_plancher_bas", "psi_moyen"]),
    ("Inertie, air, étanchéité", ["inertie", "ventilation_m3h_m2", "permeabilite_q4pa"]),
]
LIBELLES = {
    "uw": "Uw de la baie (W/m².K)",
    "uw_protege": "Uw, protection baissée (W/m².K)",
    "ratio_ouverture_max": "Part ouvrante de la baie (-)",
    "sw_e": "Facteur solaire Sw en été (-)",
    "sw_protege": "Facteur solaire, protection baissée (-)",
    "tl": "Transmission lumineuse (-)",
    "u_mur": "U des murs (W/m².K)",
    "u_toiture": "U de la toiture (W/m².K)",
    "u_plancher_bas": "U du plancher bas (W/m².K)",
    "psi_moyen": "Ponts thermiques, ψ moyen (W/m.K)",
    "inertie": "Inertie quotidienne (part de la surface)",
    "ventilation_m3h_m2": "Ventilation (m³/h par m² habitable)",
    "permeabilite_q4pa": "Perméabilité Q4Pa-surf (m³/h.m²)",
}
# Notes sous le titre (une ligne par élément)
NOTES = {
    "sw_e": ["bas = performant pour l'été seulement", "(en hiver, un Sw élevé est préférable)"],
    "sw_protege": ["bas = performant pour l'été seulement", "(en hiver, un Sw élevé est préférable)"],
}

# Mise en page en pouces
FIG_L = 18.0
MARGE_G, MARGE_D = 0.45, 0.35
ENTETE_H = 3.75                  # titre + schéma explicatif
PIED_H = 0.95
PANNEAU_H = 1.45                 # hauteur des axes d'un panneau
PANNEAU_PAS = 2.45               # pas vertical (axes + titre + graduations)
TITRE_H = 0.74                   # place au-dessus des axes pour titre + notes
COL_ECART = 0.5
DPI = 160
MARGE_X = 0.24                   # marge de l'axe x autour de min-max (fraction de l'étendue)
YLIM = (-1.3, 1.15)
Y_FLECHE = 1.0                   # hauteur de la flèche de performance (coordonnées de données)

# Réutilise les fonctions du script de calcul (même dossier)
chemin_calcul = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calcul_typologies_logements.py")
spec = importlib.util.spec_from_file_location("calcul", chemin_calcul)
calcul = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calcul)
SENS = {c: s for c, _, _, s in calcul.VARIABLES}
NB_LIGNES = max(len(cols) for _, cols in GROUPES)
FIG_H = ENTETE_H + NB_LIGNES * PANNEAU_PAS + PIED_H
fmt = calcul.fmt_nombre


def axes_pouces(x, y_haut, l, h):
    """Crée des axes à partir de coordonnées en pouces (y mesuré depuis le haut de la figure)."""
    return fig.add_axes([x / FIG_L, 1 - (y_haut + h) / FIG_H, l / FIG_L, h / FIG_H])


def repere(ax, x, niveau, y=0.0, taille=95):
    """Marqueur coloré (couleur + forme) d'un niveau."""
    ax.scatter([x], [y], s=taille, marker=FORME_NIVEAU[niveau], color=COULEUR_NIVEAU[niveau],
               edgecolor="white", linewidth=1.4, zorder=8, clip_on=False)


def fleche_performance(ax, vers_gauche, y=Y_FLECHE):
    """Flèche pleine largeur vers le côté performant, avec son texte au centre."""
    trans = ax.get_yaxis_transform()          # x en fraction de l'axe, y en données
    x_debut, x_fin = (0.97, 0.03) if vers_gauche else (0.03, 0.97)
    ax.annotate("", xy=(x_fin, y), xytext=(x_debut, y), xycoords=trans, textcoords=trans,
                arrowprops=dict(arrowstyle="-|>", color=ARDOISE, lw=1.8, mutation_scale=15,
                                shrinkA=0, shrinkB=0))
    ax.text(0.5, y, TEXTE_FLECHE, transform=trans, ha="center", va="center", fontsize=8.8,
            color=GRIS_TEXTE, style="italic", bbox=dict(fc="white", ec="none", pad=1.5), zorder=9)


def style_axe(ax):
    for cote in ("top", "right", "left"):
        ax.spines[cote].set_visible(False)
    ax.spines["bottom"].set_color("#B8BEC8")
    ax.tick_params(axis="x", colors=GRIS_TEXTE, labelsize=8.5, length=3)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRIS_GRILLE, lw=0.8)
    ax.set_axisbelow(True)


def titre_panneau(ax, titre, notes=()):
    """Titre (gras) au-dessus des axes, précédé d'éventuelles notes en italique juste au-dessus des axes."""
    decalage = 4
    if notes:
        ax.annotate("\n".join(notes), (0, 1), xycoords="axes fraction", xytext=(0, 4),
                    textcoords="offset points", ha="left", va="bottom", fontsize=8.8,
                    color=GRIS_TEXTE, style="italic", linespacing=1.15)
        decalage = 4 + 10.6 * len(notes) + 3
    ax.annotate(titre, (0, 1), xycoords="axes fraction", xytext=(0, decalage), textcoords="offset points",
                ha="left", va="bottom", fontsize=11, color=NUIT, fontweight="bold")


def panneau_numerique(ax, df, col):
    """Barre min-max + boîte P25-P75 + repères ; moyen au-dessus, performant / faible dessous."""
    d = df[[col, calcul.COL_POIDS]].dropna()
    v, w = d[col].to_numpy(), d[calcul.COL_POIDS].to_numpy()
    vmin, vmax = v.min(), v.max()
    p25, p50, p75 = (calcul.quantile_pondere(v, w, q)
                     for q in (calcul.Q_FAVORABLE, 0.5, calcul.Q_DEFAVORABLE))
    bas_bon = SENS[col] == "bas"
    perf, faib = (p25, p75) if bas_bon else (p75, p25)
    r_perf, r_moy, r_faib, _ = calcul.arrondir_niveaux(perf, p50, faib)   # valeurs affichées

    # étendue min-max
    ax.hlines(0, vmin, vmax, color=ARDOISE, lw=2.2, zorder=2)
    for x in (vmin, vmax):
        ax.vlines(x, -0.16, 0.16, color=ARDOISE, lw=2.2, zorder=2)
    # boîte P25-P75 (moitié centrale de la surface de logements)
    ax.add_patch(plt.Rectangle((p25, -0.3), p75 - p25, 0.6, fc=JAUNE, ec=NUIT, lw=1.6, zorder=3))
    ax.vlines(p50, -0.3, 0.3, color=NUIT, lw=2.6, zorder=4)
    for x, niv in ((perf, "performant"), (p50, "moyen"), (faib, "faible")):
        repere(ax, x, niv)

    # moyen AU-DESSUS ; performant et faible EN DESSOUS (alignés vers l'extérieur)
    ax.annotate(f"moyen {fmt(r_moy)}", (p50, 0.3), xytext=(0, 6), textcoords="offset points",
                ha="center", va="bottom", fontsize=9, color=NOIR, fontweight="bold")
    gauche_perf = perf < faib
    for x, niv, r, a_gauche in ((perf, "performant", r_perf, gauche_perf), (faib, "faible", r_faib, not gauche_perf)):
        ax.annotate(f"{niv}\n{fmt(r)}", (x, -0.3), xytext=(0, -6), textcoords="offset points",
                    ha="right" if a_gauche else "left", va="top", fontsize=9, color=NOIR,
                    multialignment="right" if a_gauche else "left", linespacing=1.15, fontweight="bold")

    # min / max (valeurs extrêmes observées), décalés d'un cran si un repère est tout près
    etendue = (vmax - vmin) or 1
    proche = lambda a, b: abs(a - b) < 0.07 * etendue * (1 + 2 * MARGE_X)
    dec_min = 16 if proche(min(perf, p50, faib), vmin) else 6
    dec_max = 16 if proche(max(perf, p50, faib), vmax) else 6
    ax.annotate(f"min\n{fmt(vmin, calcul.DECIMALES)}", (vmin, 0), xytext=(-dec_min, 0), textcoords="offset points",
                ha="right", va="center", fontsize=8.5, color=GRIS_TEXTE, linespacing=1.1)
    ax.annotate(f"max\n{fmt(vmax, calcul.DECIMALES)}", (vmax, 0), xytext=(dec_max, 0), textcoords="offset points",
                ha="left", va="center", fontsize=8.5, color=GRIS_TEXTE, linespacing=1.1)

    ax.set_xlim(vmin - MARGE_X * etendue, vmax + MARGE_X * etendue)
    ax.set_ylim(*YLIM)
    style_axe(ax)
    fleche_performance(ax, vers_gauche=bas_bon)
    titre_panneau(ax, LIBELLES[col], NOTES.get(col, ()))


def panneau_inertie(ax, df):
    """Barre empilée des parts de surface par classe d'inertie + repères."""
    d = df[["classe_inertie", calcul.COL_POIDS]].dropna()
    total = d[calcul.COL_POIDS].sum()
    gauche, y_barre = 0.0, 0.3
    for i, nom in enumerate(calcul.CLASSES_INERTIE):
        part = d.loc[d["classe_inertie"] == i, calcul.COL_POIDS].sum() / total
        if part <= 0:
            continue
        ax.barh(y_barre, part, left=gauche, height=0.65, color=COULEURS_INERTIE[i],
                edgecolor="white", linewidth=2, zorder=3)
        if part > 0.08:
            ax.text(gauche + part / 2, y_barre, f"{nom}\n{part:.0%}".replace("%", " %"), ha="center",
                    va="center", fontsize=9, color=TEXTE_SUR_INERTIE[i], fontweight="bold", zorder=4)
        gauche += part
    q = lambda x: calcul.CLASSES_INERTIE[int(calcul.quantile_discret(d["classe_inertie"], d[calcul.COL_POIDS], x))]
    n = calcul.NOMS_NIVEAUX
    niveaux = [(n[0], q(calcul.Q_DEFAVORABLE)), (n[1], q(0.5)), (n[2], q(calcul.Q_FAVORABLE))]
    for k, (niv, classe) in enumerate(niveaux):
        y = -0.28 - 0.32 * k
        repere(ax, 0.015, niv, y=y, taille=60)
        ax.text(0.05, y, f"{niv} : {classe}", fontsize=9, color=NOIR, fontweight="bold", va="center")
    ax.set_xlim(0, 1)
    ax.set_ylim(*YLIM)
    style_axe(ax)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["0 %", "50 %", "100 %"])
    fleche_performance(ax, vers_gauche=False)          # plus lourd (à droite) = plus performant
    titre_panneau(ax, LIBELLES["inertie"])


def anatomie():
    """Schéma explicatif d'une boîte, en tête de page (même disposition que les graphiques)."""
    larg = FIG_L - MARGE_G - MARGE_D
    ax = axes_pouces(MARGE_G, 1.3, larg, 2.05)
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.95, 1.95)
    ax.axis("off")
    vmin, p25, p50, p75, vmax = 20, 36, 47, 61, 80
    ax.hlines(0, vmin, vmax, color=ARDOISE, lw=2.2)
    for x in (vmin, vmax):
        ax.vlines(x, -0.22, 0.22, color=ARDOISE, lw=2.2)
    ax.add_patch(plt.Rectangle((p25, -0.4), p75 - p25, 0.8, fc=JAUNE, ec=NUIT, lw=1.6, zorder=3))
    ax.vlines(p50, -0.4, 0.4, color=NUIT, lw=2.6, zorder=4)
    for x, niv in ((p25, "performant"), (p50, "moyen"), (p75, "faible")):
        repere(ax, x, niv, taille=130)
    # moyen au-dessus
    ax.annotate("moyen : la moitié de la surface fait mieux,\nl'autre moitié fait moins bien", (p50, 0.4),
                xytext=(0, 7), textcoords="offset points", ha="center", va="bottom",
                fontsize=9.5, color=NOIR, linespacing=1.2)
    # performant et faible dessous
    for x, nom, expl, ha in ((p25, "performant", "25 % de la surface\nfait mieux", "right"),
                             (p75, "faible", "25 % de la surface\nfait moins bien", "left")):
        ax.annotate(f"{nom}\n{expl}", (x, -0.4), xytext=(0, -7), textcoords="offset points",
                    ha=ha, va="top", fontsize=9.5, color=NOIR, linespacing=1.2, multialignment=ha)
    ax.annotate("min\nvaleur la plus basse\nobservée", (vmin, 0), xytext=(-8, 0), textcoords="offset points",
                ha="right", va="center", fontsize=9, color=GRIS_TEXTE, linespacing=1.15)
    ax.annotate("max\nvaleur la plus haute\nobservée", (vmax, 0), xytext=(8, 0), textcoords="offset points",
                ha="left", va="center", fontsize=9, color=GRIS_TEXTE, linespacing=1.15)
    # flèche du sens de la performance (ici : le plus petit est le plus performant)
    ax.annotate("", xy=(vmin, 1.65), xytext=(vmax, 1.65), arrowprops=dict(
        arrowstyle="-|>", color=ARDOISE, lw=1.8, mutation_scale=15, shrinkA=0, shrinkB=0))
    ax.text(50, 1.65, TEXTE_FLECHE + " (ici : plus petit = mieux)", ha="center", va="center", fontsize=9,
            color=GRIS_TEXTE, style="italic", bbox=dict(fc="white", ec="none", pad=1.5), zorder=9)


def main(chemin_entree, chemin_png):
    global fig
    df = calcul.charger_zones(chemin_entree)
    fig = plt.figure(figsize=(FIG_L, FIG_H), facecolor="white")

    txt = lambda x, y, s, **kw: fig.text(x / FIG_L, 1 - y / FIG_H, s, **kw)
    txt(MARGE_G, 0.3, "Logements : quelles performances pour l'enveloppe ?", fontsize=21,
        color=NUIT, fontweight="bold", va="top")
    txt(MARGE_G, 0.82,
        f"Valeurs observées sur {len(df)} zones de logements ({df['empreinte_entrees'].nunique()} opérations, "
        + f"{df[calcul.COL_POIDS].sum():,.0f}".replace(",", " ") + " m² habitables), quantiles pondérés par la surface",
        fontsize=10.5, color=GRIS_TEXTE, va="top")
    txt(FIG_L / 2, 1.3, "Comment lire chaque graphique : la boîte jaune contient la moitié centrale des logements",
        fontsize=10.5, color=NUIT, fontweight="bold", va="bottom", ha="center")
    anatomie()

    nb_col = len(GROUPES)
    larg_col = (FIG_L - MARGE_G - MARGE_D - (nb_col - 1) * COL_ECART) / nb_col
    for c, (titre, cols) in enumerate(GROUPES):
        x = MARGE_G + c * (larg_col + COL_ECART)
        y_titre = ENTETE_H - 0.15
        txt(x, y_titre, titre, fontsize=13, color=NUIT, fontweight="bold", va="bottom")
        fig.add_artist(plt.Line2D([x / FIG_L, (x + larg_col) / FIG_L],
                                  [1 - (y_titre + 0.08) / FIG_H] * 2, color=ORANGE, lw=2.4))
        for r, col in enumerate(cols):
            y_haut = ENTETE_H + 0.25 + r * PANNEAU_PAS + TITRE_H
            ax = axes_pouces(x, y_haut, larg_col, PANNEAU_H)
            if col == "inertie":
                panneau_inertie(ax, df)
            else:
                panneau_numerique(ax, df, col)

    txt(MARGE_G, FIG_H - 0.25,
        "Lecture : performant, moyen et faible = repères P25, P50 et P75 des surfaces de logements (valeurs arrondies), "
        "du côté favorable au côté défavorable. La flèche indique le sens de la performance.",
        fontsize=9, color=GRIS_TEXTE, va="bottom")
    fig.savefig(chemin_png, dpi=DPI, facecolor="white")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
