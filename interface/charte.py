"""
============================================================
 CHARTE — couleurs de l'interface
============================================================
 Palette reçue le 12/11/2026, tirée de celle du HUB (voir
 ROADMAP.md). Le thème de Streamlit (.streamlit/config.toml)
 reprend les mêmes codes : les changer aux deux endroits.

 Un rôle par couleur, le même partout (schéma, graphiques) :
   chauffage   prune         froid      bleu ciel
   éclairage   jaune         inconfort  orange
   limite      noir
 Températures (0.9.38) : extérieur orange, intérieur jaune, seuil
 de confort en trait plein noir fin (une limite, comme le Bbio max).
 Dessin : paroi adiabatique en gris.
============================================================
"""

# ============================================================
# PALETTE DU HUB
# ============================================================
JAUNE = "#FABD4A"           # Sunflower Gold (accent4)
ORANGE = "#FA9600"          # orange HUB (accent5)
NOIR = "#000000"            # texte
ROSE = "#FFB5C2"            # Cherry Blossom
BLEU_CIEL = "#00B0F0"       # Fresh Sky
PRUNE = "#6D2E46"           # Wine Plum
BLEU_NUIT = "#283246"       # Deep Space Blue
# Teintes de fond et de trait, dérivées de la palette
FOND_SCHEMA = "#FFF6E3"     # jaune très pâle : fond de l'axonométrie
GRIS = "#8A8F99"            # grandeurs extérieures, repères secondaires
SOL = "#EFE3C8"             # disque du sol, sous la boîte
GRIS_ADIABATIQUE = "#C4C6CC"    # paroi adiabatique (sur un local chauffé) dans le dessin
BORDURE = "#E6D9BC"         # filets et bords (borderColor du thème)

# ============================================================
# RÔLES
# ============================================================
COULEUR_CHAUFFAGE = PRUNE
COULEUR_FROID = BLEU_CIEL
COULEUR_ECLAIRAGE = JAUNE
COULEUR_INCONFORT = ORANGE
COULEUR_LIMITE = NOIR
COULEUR_EXTERIEUR = ORANGE
COULEUR_INTERIEUR = JAUNE
COULEUR_SEUIL = NOIR
COULEUR_PROTECTION = PRUNE
COULEUR_OUVERTURE = BLEU_CIEL
COULEUR_SURLIGNAGE = ORANGE     # dessin : contour de la paroi examinée (trait plein, la course du soleil est pointillée)
