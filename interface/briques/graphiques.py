"""
============================================================
 GRAPHIQUES — outils communs aux briques (Altair)
============================================================
 Règles suivies par tous les graphiques de l'interface :
   - une couleur par rôle, la même partout (interface/charte.py) ;
   - un seul axe vertical par graphique : deux grandeurs d'unités
     différentes font deux graphiques alignés ;
   - une légende dès qu'il y a deux séries, une infobulle sur
     chaque marque ;
   - nombres à la française dans les textes (virgule décimale).
============================================================
"""

import altair as alt

# Hauteurs TOTALES en pixels, légende et axes compris : Streamlit ajuste le tracé à la place qui reste
# (une légende prend 35 px environ, un axe horizontal 30 px)
HAUTEUR = 320                   # graphique principal
HAUTEUR_BANDE = 220             # graphique secondaire, sous le principal
HAUTEUR_BARRE = 170             # une seule barre horizontale, avec sa légende et son axe
FORMAT_JOUR = "%d/%m"           # dates : jour/mois (l'année affichée est conventionnelle)
FORMAT_HEURE = "%d/%m %Hh"
TRAIT_SERIE = 2                 # px : courbe d'une grandeur mesurée (températures)
TRAIT_FIN = 1                   # px : seuil ou limite (seuil de confort, en noir)
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def nombre(valeur, decimales=0, unite=""):
    """Nombre à la française : espace des milliers, virgule décimale, unité facultative."""
    texte = f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return f"{texte} {unite}" if unite else texte


def echelle_couleurs(roles):
    """Échelle de couleurs figée : {nom de la série: couleur}, dans l'ordre donné."""
    return alt.Scale(domain=list(roles), range=list(roles.values()))


def legende(titre=None):
    return alt.Legend(title=titre, orient="top", direction="horizontal", symbolStrokeWidth=3)


def lignes_des_series(base, fins=(), **options):
    """(lignes épaisses, lignes fines) d'un graphique dont « base » encode la série dans le champ « serie » : traits
    fins pour les séries nommées (un seuil se lit comme une limite), plus épais pour les mesures (0.9.38 ; le seuil
    était pointillé). Deux couches, la légende des couleurs restant commune : Vega-Lite ne tient pas compte d'une
    épaisseur encodée par série sur des lignes (constaté dans la page : 2 px partout)."""
    fine = alt.FieldOneOfPredicate(field="serie", oneOf=list(fins))
    epaisse = alt.LogicalNotPredicate(**{"not": fine})
    return (base.mark_line(strokeWidth=TRAIT_SERIE, **options).transform_filter(epaisse),
            base.mark_line(strokeWidth=TRAIT_FIN, **options).transform_filter(fine))


def etiquettes_heures():
    """Axe du temps lisible à toutes les échelles du zoom : la date à minuit, l'heure sinon (« 14h »)."""
    return alt.Axis(labelExpr="hours(datum.value) == 0 ? timeFormat(datum.value, '%d/%m') "
                              ": timeFormat(datum.value, '%Hh')")
