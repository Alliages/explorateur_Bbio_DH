"""
============================================================
 AXONOMÉTRIE — la boîte dessinée, orientée et vitrée
============================================================
 Dessin SVG de la boîte saisie (interface/saisie.py), dans le
 style de CBSh visuel : aplats clairs, traits fins et sombres.

 Ce que montre le dessin, à l'échelle :
   - la forme (longueur, profondeur, niveaux) ;
   - l'orientation : la boîte tourne sur un sol dont les points
     cardinaux sont fixes ; une flèche marque le nord ;
   - les baies de chaque façade, de surface proportionnelle à la
     part vitrée saisie, avec leur protection mobile ;
   - les balcons ou casquettes, de la profondeur saisie ;
   - les parois adiabatiques (sur un local chauffé), en gris ;
   - le soleil du 21 juin (à 46,5° N, 2,5° E) :
       · sa course dans le ciel, du lever au nord-est au coucher
         au nord-ouest, un point toutes les deux heures ;
       · la même course portée au bord du sol (sa direction, sans
         sa hauteur) : vue du sud, la course dans le ciel est vue
         presque par la tranche, la trace au sol reste lisible ;
       · le soleil de l'heure choisie (16 h légale par défaut, de
         6 à 20 h), à sa vraie hauteur, relié au sol par un trait ;
         à 6 h, encore sous l'horizon, il est dessiné à son lever
         (HAUTEUR_MIN_SOLEIL_DEG) ;
       · l'ombre que la boîte porte au sol à cette heure, coupée au
         bord du sol, et les façades à l'ombre, plus sombres.

 Projection : le spectateur se tient à l'azimut « vue_deg »
 (même convention que le moteur : 0 = sud, 90 = ouest) et
 regarde le centre de la boîte de haut, sous l'angle ELEVATION.

     écran x =  position le long de la droite du spectateur
     écran y = − (z × cos(e) + éloignement × sin(e))

 Seules les deux façades tournées vers le spectateur sont
 visibles : l'interface propose de changer de point de vue.

 Ce fichier ne dépend pas de Streamlit : dessiner(boite) rend le
 texte d'un SVG.
============================================================
"""

import math
from xml.sax.saxutils import escape

from interface import charte
from interface.saisie import PAROIS_ADIABATIQUES, SANS_PROTECTION, gabarit_baie, largeur_travee, point_cardinal

# ============================================================
# RÉGLAGES DU DESSIN
# ============================================================
LARGEUR, HAUTEUR = 720, 470         # dimensions du SVG (px)
MARGE = 34                          # marge autour de la scène (px)
ELEVATION_DEG = 30.0                # hauteur du regard au-dessus de l'horizon
VUE_PAR_DEFAUT_DEG = 45.0           # spectateur au sud-ouest : façades sud et ouest visibles
VUES = {"sud-ouest": 45.0, "sud-est": -45.0, "nord-est": -135.0, "nord-ouest": 135.0}
RAYON_SOL = 0.95                    # rayon du disque du sol, en diagonales de la boîte
RAYON_CIEL = 1.0                    # rayon de la voûte où court le soleil, en rayons du sol : lever et coucher au bord du sol
# Soleil du 21 juin : position calculée pour un lieu moyen de la France métropolitaine
LATITUDE_DEG = 46.5                 # milieu de la France métropolitaine (de 42 à 51° N)
LONGITUDE_DEG = 2.5                 # degrés à l'est de Greenwich (de − 4,8 à 8,2° E)
DECLINAISON_ETE_DEG = 23.44         # déclinaison du soleil au solstice d'été
EQUATION_DU_TEMPS_MIN = -1.7        # le 21 juin, le soleil vrai retarde de 1,7 min sur le soleil moyen
DECALAGE_HEURE_ETE_H = 2.0          # heure légale d'été = temps universel + 2 h
SOLEIL_HEURE = 16.0                 # heure légale du soleil dessiné par défaut : l'après-midi, qui chauffe le plus
HEURES_SOLEIL = tuple(range(6, 21, 2))  # heures légales proposées pour le soleil dessiné (curseur sous le dessin)
HAUTEUR_MIN_SOLEIL_DEG = 2.0        # plus bas, le soleil est dessiné à cette hauteur (lever ou coucher) : visible
ARRONDI_LEVER_MIN = 5               # heure du lever ou du coucher affichée à 5 min près
PAS_REPERES_H = 2                   # un point sur la course toutes les deux heures légales
POINTS_COURSE = 48                  # nombre de segments de la course
PART_VOLET = 0.28                   # part haute de la baie couverte par la protection dessinée
TRAIT = 1.4                         # épaisseur des traits (px)
POLICE = "font-family='Helvetica, Arial, sans-serif'"
# Couleur des murs selon la teinte saisie
MURS = {"claire": "#FBF7EE", "moyenne": "#EBD6B0", "sombre": "#A98F78", "noire": "#5F5962"}
OMBRE = 0.88                        # une façade à l'ombre est un peu plus sombre
OPACITE_OMBRE_PORTEE = 0.22         # ombre de la boîte sur le sol
# Points cardinaux du sol : (lettre, azimut du moteur) ; le nord porte en plus une flèche
CARDINAUX = (("S", 0.0), ("O", 90.0), ("N", 180.0), ("E", -90.0))
FLECHE_NORD = (0.86, 1.14, 0.07)    # flèche du nord : de, à (en rayons du sol), demi-largeur de la pointe


# ============================================================
# OUTILS : couleurs et géométrie
# ============================================================
def _melanger(couleur, autre, part):
    """Mélange de deux couleurs « #RRGGBB » : part = 0 rend la première, 1 la seconde."""
    a = [int(couleur[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(autre[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * part):02X}" for x, y in zip(a, b))


def direction(azimut_deg):
    """Vecteur horizontal (est, nord) pointant vers un azimut du moteur : 0 = sud, 90 = ouest."""
    a = math.radians(azimut_deg)
    return -math.sin(a), -math.cos(a)


class Projection:
    """Passe d'un point (est, nord, haut) en mètres à un point de l'écran, avant mise à l'échelle."""

    def __init__(self, vue_deg):
        vx, vy = direction(vue_deg)             # du centre vers le spectateur
        self.regard = (-vx, -vy)                # du spectateur vers le centre
        self.droite = (self.regard[1], -self.regard[0])
        self.cos_e = math.cos(math.radians(ELEVATION_DEG))
        self.sin_e = math.sin(math.radians(ELEVATION_DEG))

    def point(self, x, y, z=0.0):
        eloignement = x * self.regard[0] + y * self.regard[1]
        return (x * self.droite[0] + y * self.droite[1],
                -(z * self.cos_e + eloignement * self.sin_e))

    def voit(self, normale):
        """Vrai si une façade de normale extérieure donnée est tournée vers le spectateur."""
        return normale[0] * self.regard[0] + normale[1] * self.regard[1] < -1e-9

    def devant(self, x, y):
        """Vrai si le point (est, nord) est du côté du spectateur par rapport au centre de la boîte."""
        return x * self.regard[0] + y * self.regard[1] < 0


def decouper_baies(part_vitree, largeur_m, nb_niveaux, hauteur_etage_m):
    """Rectangles des baies d'une façade : (u0, u1, z0, z1) en mètres, u compté depuis le milieu de la façade.

    La somme des surfaces vaut part_vitree × surface de la façade : le dessin est à l'échelle. La baie occupe
    une part fh de la hauteur d'étage et fw de la largeur de sa travée, avec fh × fw = part vitrée
    (gabarit commun avec le calcul : interface.saisie.gabarit_baie).
    """
    if part_vitree <= 0:
        return []
    fh, hauteur_baie, allege, _ = gabarit_baie(part_vitree, hauteur_etage_m)
    fw = part_vitree / fh
    travee = largeur_travee(largeur_m)
    nb_travees = round(largeur_m / travee)
    rectangles = []
    for niveau in range(nb_niveaux):
        z0 = niveau * hauteur_etage_m + allege
        for t in range(nb_travees):
            milieu = -largeur_m / 2.0 + (t + 0.5) * travee
            rectangles.append((milieu - fw * travee / 2.0, milieu + fw * travee / 2.0,
                               z0, z0 + hauteur_baie))
    return rectangles


def enveloppe_convexe(points):
    """Enveloppe convexe de points du plan (algorithme de la chaîne monotone), dans le sens trigonométrique."""
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def tour(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    bas, haut = [], []
    for p in points:
        while len(bas) >= 2 and tour(bas[-2], bas[-1], p) <= 0:
            bas.pop()
        bas.append(p)
    for p in reversed(points):
        while len(haut) >= 2 and tour(haut[-2], haut[-1], p) <= 0:
            haut.pop()
        haut.append(p)
    return bas[:-1] + haut[:-1]


# ============================================================
# LE SOLEIL DU 21 JUIN
# ============================================================
def angle_horaire(heure_legale):
    """Angle horaire du soleil (degrés, 0 à midi solaire, positif l'après-midi) à une heure légale d'été :
    heure solaire vraie = heure légale − 2 h + longitude / 15 + équation du temps."""
    heure_solaire = heure_legale - DECALAGE_HEURE_ETE_H + LONGITUDE_DEG / 15.0 + EQUATION_DU_TEMPS_MIN / 60.0
    return (heure_solaire - 12.0) * 15.0


def direction_soleil(angle_horaire_deg, latitude_deg=LATITUDE_DEG, declinaison_deg=DECLINAISON_ETE_DEG):
    """Direction du soleil (est, nord, haut), vecteur unitaire, pour un angle horaire (0 à midi solaire, positif
    l'après-midi, 15° par heure). Formules classiques de la position du soleil."""
    phi, delta, h = (math.radians(a) for a in (latitude_deg, declinaison_deg, angle_horaire_deg))
    return (-math.cos(delta) * math.sin(h),
            math.cos(phi) * math.sin(delta) - math.sin(phi) * math.cos(delta) * math.cos(h),
            math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(h))


def angle_coucher(latitude_deg=LATITUDE_DEG, declinaison_deg=DECLINAISON_ETE_DEG):
    """Angle horaire du coucher du soleil (degrés) : cos H0 = − tan φ × tan δ."""
    return math.degrees(math.acos(-math.tan(math.radians(latitude_deg)) * math.tan(math.radians(declinaison_deg))))


def heure_legale(angle_horaire_deg):
    """Heure légale d'été d'un angle horaire : l'inverse de angle_horaire."""
    return (angle_horaire_deg / 15.0 + 12.0 + DECALAGE_HEURE_ETE_H - LONGITUDE_DEG / 15.0
            - EQUATION_DU_TEMPS_MIN / 60.0)


def heure_dessinee(heure):
    """Heure légale où dessiner le soleil demandé à « heure » : la même s'il est assez haut ; sinon, l'heure où il
    passe à HAUTEUR_MIN_SOLEIL_DEG, le matin (lever) ou le soir (coucher). Le soleil dessiné est donc toujours
    visible : à 46,5° N, il ne se lève qu'à 6 h 03 le 21 juin.

    sin(hauteur) = sin φ sin δ + cos φ cos δ cos H, résolu en H pour la hauteur minimale.
    """
    angle = angle_horaire(heure)
    if direction_soleil(angle)[2] >= math.sin(math.radians(HAUTEUR_MIN_SOLEIL_DEG)):
        return heure
    phi, delta = math.radians(LATITUDE_DEG), math.radians(DECLINAISON_ETE_DEG)
    cos_h = ((math.sin(math.radians(HAUTEUR_MIN_SOLEIL_DEG)) - math.sin(phi) * math.sin(delta))
             / (math.cos(phi) * math.cos(delta)))
    return heure_legale(math.copysign(math.degrees(math.acos(cos_h)), angle))


def libelle_heure(heure):
    """Texte posé à côté du soleil : « 21 juin, 16 h », ou « 21 juin, lever (6 h 15) » s'il a fallu le remonter."""
    dessinee = heure_dessinee(heure)
    if dessinee == heure:
        return f"21 juin, {heure:.0f} h"
    minutes = round(dessinee * 60 / ARRONDI_LEVER_MIN) * ARRONDI_LEVER_MIN
    moment = "lever" if angle_horaire(heure) < 0 else "coucher"
    return f"21 juin, {moment} ({minutes // 60} h {minutes % 60:02d})"


def bord_du_sol(angle_horaire_deg, rayon):
    """Point (est, nord) du bord du sol dans la direction du soleil (son azimut, sans sa hauteur)."""
    est, nord, _ = direction_soleil(angle_horaire_deg)
    norme = math.hypot(est, nord)
    return rayon * est / norme, rayon * nord / norme


def dans_le_ciel(angle_horaire_deg, rayon):
    """Point (est, nord, haut) du soleil sur la voûte de rayon donné, centrée au pied de la boîte."""
    return tuple(rayon * c for c in direction_soleil(angle_horaire_deg))


def ombre_au_sol(boite, soleil):
    """Ombre portée de la boîte sur le sol (polygone de points (est, nord)) pour une direction du soleil
    (est, nord, haut) au-dessus de l'horizon : chaque coin haut glisse au sol de hauteur / tan(hauteur du soleil),
    à l'opposé du soleil ; l'ombre est l'enveloppe des coins bas et de ces coins glissés."""
    est, nord, haut = soleil
    pente_x, pente_y = est / haut, nord / haut
    coins = _coins(boite)
    glisses = [(x - boite.hauteur_m * pente_x, y - boite.hauteur_m * pente_y) for x, y in coins]
    return enveloppe_convexe(coins + glisses)


def couper(polygone, fenetre):
    """Partie d'un polygone dans une fenêtre convexe (listes de points (x, y), fenêtre dans le sens
    trigonométrique) : algorithme de Sutherland-Hodgman, un côté de la fenêtre après l'autre."""
    def dedans(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def croisement(p, q, a, b):
        dx, dy = q[0] - p[0], q[1] - p[1]
        ex, ey = b[0] - a[0], b[1] - a[1]
        t = (ex * (a[1] - p[1]) - ey * (a[0] - p[0])) / (ex * dy - ey * dx)
        return p[0] + t * dx, p[1] + t * dy

    resultat = list(polygone)
    for a, b in zip(fenetre, fenetre[1:] + fenetre[:1]):
        entree, resultat = resultat, []
        for p, q in zip(entree[-1:] + entree[:-1], entree):     # chaque côté (p, q) du polygone
            if dedans(q, a, b):
                if not dedans(p, a, b):
                    resultat.append(croisement(p, q, a, b))
                resultat.append(q)
            elif dedans(p, a, b):
                resultat.append(croisement(p, q, a, b))
        if not resultat:
            break
    return resultat


def tour_du_sol(rayon):
    """Le disque du sol, en polygone de 72 côtés (est, nord), dans le sens trigonométrique."""
    return [(rayon * math.cos(2 * math.pi * i / 72), rayon * math.sin(2 * math.pi * i / 72)) for i in range(72)]


def _coins(boite):
    """Les quatre coins (est, nord) de l'emprise de la boîte, dans l'ordre du tour."""
    nx, ny = direction(boite.orientation_deg)
    tx, ty = ny, -nx
    return [(sx * tx * boite.longueur_m / 2 + sy * nx * boite.profondeur_m / 2,
             sx * ty * boite.longueur_m / 2 + sy * ny * boite.profondeur_m / 2)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


# ============================================================
# DESSIN
# ============================================================
class _Scene:
    """Accumule les formes en mètres projetés, puis les met à l'échelle du SVG."""

    def __init__(self):
        self.formes = []        # (genre, points, attributs ou texte)
        self.points = []        # tous les points, pour le cadrage

    def polygone(self, points, **attributs):
        self.formes.append(("polygone", list(points), attributs))
        self.points.extend(points)

    def ligne(self, points, **attributs):
        self.formes.append(("ligne", list(points), attributs))
        self.points.extend(points)

    def texte(self, point, contenu, decalage=(0, 0), **attributs):
        """Texte ancré en un point ; l'attribut « vers » (un second point) le couche le long d'une arête."""
        self.formes.append(("texte", [point], (contenu, decalage, attributs)))
        self.points.append(point)

    def cercle(self, point, rayon_px, **attributs):
        self.formes.append(("cercle", [point], (rayon_px, attributs)))
        self.points.append(point)

    def svg(self, titre):
        xs, ys = [p[0] for p in self.points], [p[1] for p in self.points]
        etendue_x, etendue_y = max(xs) - min(xs), max(ys) - min(ys)
        echelle = min((LARGEUR - 2 * MARGE) / etendue_x, (HAUTEUR - 2 * MARGE) / etendue_y)
        dx = (LARGEUR - etendue_x * echelle) / 2.0 - min(xs) * echelle
        dy = (HAUTEUR - etendue_y * echelle) / 2.0 - min(ys) * echelle

        def px(p):
            return f"{p[0] * echelle + dx:.1f},{p[1] * echelle + dy:.1f}"

        def attr(attributs):
            return " ".join(f"{nom.replace('_', '-')}='{valeur}'" for nom, valeur in attributs.items())

        lignes = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {LARGEUR} {HAUTEUR}' "
                  f"width='{LARGEUR}' height='{HAUTEUR}' role='img'>",
                  f"<title>{escape(titre)}</title>",
                  f"<rect width='{LARGEUR}' height='{HAUTEUR}' rx='22' fill='{charte.FOND_SCHEMA}'/>"]
        for genre, points, suite in self.formes:
            if genre == "polygone":
                lignes.append(f"<polygon points='{' '.join(px(p) for p in points)}' {attr(suite)}/>")
            elif genre == "ligne":
                lignes.append(f"<polyline points='{' '.join(px(p) for p in points)}' fill='none' {attr(suite)}/>")
            elif genre == "cercle":
                rayon, attributs = suite
                x, y = px(points[0]).split(",")
                lignes.append(f"<circle cx='{x}' cy='{y}' r='{rayon}' {attr(attributs)}/>")
            else:
                contenu, decalage, attributs = suite
                x, y = (float(v) for v in px(points[0]).split(","))
                # Texte couché le long d'une arête : tourné autour de son point d'ancrage, puis décalé
                attributs = dict(attributs)
                vers = attributs.pop("vers", None)
                rotation = ""
                if vers is not None:
                    x2, y2 = (float(v) for v in px(vers).split(","))
                    angle = math.degrees(math.atan2(y2 - y, x2 - x))
                    rotation = f" transform='rotate({angle:.1f} {x:.1f} {y:.1f})'"
                lignes.append(f"<text x='{x + decalage[0]:.1f}' y='{y + decalage[1]:.1f}' {POLICE} "
                              f"{attr(attributs)}{rotation}>{escape(contenu)}</text>")
        lignes.append("</svg>")
        return "\n".join(lignes)


def _sol(scene, proj, rayon):
    """Disque du sol, points cardinaux et flèche du nord, posée sur le bord du disque."""
    scene.polygone([proj.point(x, y) for x, y in tour_du_sol(rayon)], fill=charte.SOL, stroke="none")
    de, a, demi = FLECHE_NORD
    nord_x, nord_y = direction(180.0)
    travers = (nord_y, -nord_x)
    pointe = proj.point(nord_x * rayon * a, nord_y * rayon * a)
    base = [proj.point(nord_x * rayon * de + s * travers[0] * rayon * demi,
                       nord_y * rayon * de + s * travers[1] * rayon * demi) for s in (-1, 1)]
    scene.polygone([base[0], pointe, base[1], proj.point(nord_x * rayon * (de + 0.07), nord_y * rayon * (de + 0.07))],
                   fill=charte.BLEU_NUIT, stroke="none")
    for lettre, azimut in CARDINAUX:
        dx, dy = direction(azimut)
        loin = a + 0.1 if lettre == "N" else 1.1
        scene.texte(proj.point(dx * rayon * loin, dy * rayon * loin), lettre, decalage=(0, 5),
                    text_anchor="middle", font_size=15, fill=charte.BLEU_NUIT,
                    font_weight="700" if lettre == "N" else "400")


def _course_au_sol(scene, proj, rayon):
    """Course du soleil le 21 juin portée au bord du sol (sa direction, sans sa hauteur), du lever au coucher."""
    coucher = angle_coucher()
    course = [proj.point(*bord_du_sol(-coucher + 2 * coucher * i / POINTS_COURSE, rayon))
              for i in range(POINTS_COURSE + 1)]
    scene.ligne(course, stroke=charte.ORANGE, stroke_width=1.6, stroke_dasharray="2 6", stroke_linecap="round",
                stroke_opacity=0.7)
    for bout in (course[0], course[-1]):
        scene.cercle(bout, 4, fill=charte.ORANGE, stroke="none")


def _course_dans_le_ciel(scene, proj, rayon, devant):
    """Course du soleil le 21 juin dans le ciel, et un point toutes les PAS_REPERES_H heures légales.

    devant : ne dessine que la partie du côté du spectateur (après la boîte), sinon la partie derrière (avant la
    boîte, qui la cache en partie).
    """
    coucher = angle_coucher()
    angles = [-coucher + 2 * coucher * i / POINTS_COURSE for i in range(POINTS_COURSE + 1)]
    morceau = []
    for angle in angles + [None]:                   # None : ferme le dernier morceau
        point = dans_le_ciel(angle, rayon) if angle is not None else None
        if point is not None and proj.devant(point[0], point[1]) == devant:
            morceau.append(proj.point(*point))
            continue
        if point is not None and morceau:           # le morceau va jusqu'au point de bascule
            morceau.append(proj.point(*point))
        if len(morceau) >= 2:
            scene.ligne(morceau, stroke=charte.ORANGE, stroke_width=2.2, stroke_dasharray="2 6",
                        stroke_linecap="round")
        morceau = []
    for heure in range(0, 24, PAS_REPERES_H):
        angle = angle_horaire(heure)
        if abs(angle) >= coucher:                   # soleil couché
            continue
        point = dans_le_ciel(angle, rayon)
        if proj.devant(point[0], point[1]) == devant:
            scene.cercle(proj.point(*point), 2.6, fill=charte.ORANGE, stroke="none")


def _soleil(scene, proj, rayon, heure):
    """Le soleil de l'heure donnée à sa place dans le ciel, relié au sol par un trait vertical."""
    x, y, z = dans_le_ciel(angle_horaire(heure_dessinee(heure)), rayon)
    scene.ligne([proj.point(x, y, 0.0), proj.point(x, y, z)], stroke=charte.ORANGE, stroke_width=1.2,
                stroke_dasharray="1 4", stroke_linecap="round")
    scene.cercle(proj.point(x, y, 0.0), 2.6, fill=charte.ORANGE, stroke="none")
    scene.cercle(proj.point(x, y, z), 11, fill=charte.JAUNE, stroke=charte.ORANGE, stroke_width=1.6)


def _etiquette_soleil(scene, proj, rayon, heure, derriere):
    """Dessinée en dernier : l'heure à côté du soleil, du côté du centre du dessin pour ne pas sortir du cadre.
    Si le soleil est derrière la boîte, son contour en pointillé par-dessus : bas (le matin, vu du sud-ouest),
    la boîte le cacherait."""
    soleil = proj.point(*dans_le_ciel(angle_horaire(heure_dessinee(heure)), rayon))
    if derriere:
        scene.cercle(soleil, 11, fill="none", stroke=charte.ORANGE, stroke_width=1.6, stroke_dasharray="3 3")
    a_droite = soleil[0] > proj.point(0.0, 0.0)[0]
    scene.texte(soleil, libelle_heure(heure), decalage=(-16 if a_droite else 16, 4),
                text_anchor="end" if a_droite else "start", font_size=12, fill=charte.BLEU_NUIT)


def _ombre_portee(scene, proj, boite, soleil, rayon):
    """Ombre de la boîte sur le sol, sous le dessin de la boîte, coupée au bord du sol : le soleil bas du matin et
    du soir l'étire bien au-delà, et le cadrage du dessin changerait d'une heure à l'autre."""
    if soleil[2] <= 0:
        return
    ombre = couper(ombre_au_sol(boite, soleil), tour_du_sol(rayon))
    scene.polygone([proj.point(x, y) for x, y in ombre], fill=charte.BLEU_NUIT,
                   fill_opacity=OPACITE_OMBRE_PORTEE, stroke="none")


def _facade(scene, proj, boite, facade, couleur):
    """Une façade visible : le mur, les lignes de plancher, les baies et leur protection."""
    nx, ny = direction(facade["orientation_deg"])
    cx, cy = nx * facade["recul_m"], ny * facade["recul_m"]     # milieu du pied de la façade
    tx, ty = ny, -nx                            # direction horizontale de la façade

    def p(u, z):
        return proj.point(cx + tx * u, cy + ty * u, z)

    demi, haut = facade["largeur_m"] / 2.0, boite.hauteur_m
    trait = dict(stroke=charte.BLEU_NUIT, stroke_width=TRAIT, stroke_linejoin="round")
    scene.polygone([p(-demi, 0), p(demi, 0), p(demi, haut), p(-demi, haut)], fill=couleur, **trait)
    for niveau in range(1, boite.nb_niveaux):
        z = niveau * boite.hauteur_etage_m
        scene.ligne([p(-demi, z), p(demi, z)], stroke=charte.BLEU_NUIT, stroke_width=0.5, stroke_opacity=0.35)
    for u0, u1, z0, z1 in decouper_baies(facade["part_vitree"], facade["largeur_m"], boite.nb_niveaux,
                                         boite.hauteur_etage_m):
        scene.polygone([p(u0, z0), p(u1, z0), p(u1, z1), p(u0, z1)], fill=charte.BLEU_CIEL, fill_opacity=0.75,
                       stroke=charte.BLEU_NUIT, stroke_width=0.8, stroke_linejoin="round")
        if boite.protection != SANS_PROTECTION:     # protection mobile, dessinée à demi baissée
            zv = z1 - (z1 - z0) * PART_VOLET
            scene.polygone([p(u0, zv), p(u1, zv), p(u1, z1), p(u0, z1)], fill=charte.COULEUR_PROTECTION,
                           fill_opacity=0.8, stroke="none")
    # Balcons ou casquettes : une dalle en débord au nu de chaque plancher haut, dessinée par-dessus les baies
    if boite.debord_m > 0 and facade["cle"] in boite.facades_debord and not facade["adiabatique"]:
        for niveau in range(1, boite.nb_niveaux + 1):
            z = niveau * boite.hauteur_etage_m
            dalle = [proj.point(cx + tx * u + nx * d, cy + ty * u + ny * d, z)
                     for u, d in ((-demi, 0.0), (demi, 0.0), (demi, boite.debord_m), (-demi, boite.debord_m))]
            scene.polygone(dalle, fill=_melanger(couleur, "#FFFFFF", 0.35), fill_opacity=0.92, **trait)
    # Étiquette couchée le long du pied de la façade, lue de gauche à droite : nom, point cardinal, part vitrée
    fin = "adiabatique" if facade["adiabatique"] else f"{facade['part_vitree']:.0%}".replace("%", " %")
    etiquette = f"{facade['libelle']} · {point_cardinal(facade['orientation_deg'])} · {fin}"
    milieu = p(0, 0)
    gauche, droite = sorted((p(-demi, 0), p(demi, 0)))
    scene.texte(milieu, etiquette, decalage=(0, 17),
                vers=(milieu[0] + droite[0] - gauche[0], milieu[1] + droite[1] - gauche[1]),
                text_anchor="middle", font_size=12.5, fill=charte.BLEU_NUIT)


def couleur_facade(boite, facade, soleil):
    """Couleur d'une façade : celle de la teinte des murs (gris si adiabatique), assombrie si le soleil ne la voit
    pas (soleil derrière elle ou couché)."""
    mur = charte.GRIS_ADIABATIQUE if facade["adiabatique"] else MURS[boite.teinte]
    nx, ny = direction(facade["orientation_deg"])
    au_soleil = soleil[2] > 0 and nx * soleil[0] + ny * soleil[1] > 0
    return mur if au_soleil else _melanger(mur, charte.BLEU_NUIT, 1.0 - OMBRE)


def dessiner(boite, vue_deg=VUE_PAR_DEFAUT_DEG, heure=SOLEIL_HEURE):
    """SVG de la boîte, vue depuis l'azimut vue_deg (0 = depuis le sud, 90 = depuis l'ouest), avec le soleil du
    21 juin à l'heure légale donnée (remonté à son lever ou à son coucher s'il est trop bas : heure_dessinee)."""
    proj = Projection(vue_deg)
    scene = _Scene()
    rayon = RAYON_SOL * math.hypot(boite.longueur_m, boite.profondeur_m)
    rayon_ciel = RAYON_CIEL * rayon
    soleil = direction_soleil(angle_horaire(heure_dessinee(heure)))
    # Le soleil est devant la boîte s'il est du côté du spectateur, derrière sinon
    soleil_devant = proj.devant(soleil[0], soleil[1])

    # Derrière la boîte : sol, trace de la course au sol, ombre portée, partie lointaine de la course dans le ciel
    _sol(scene, proj, rayon)
    _course_au_sol(scene, proj, rayon)
    _ombre_portee(scene, proj, boite, soleil, rayon)
    _course_dans_le_ciel(scene, proj, rayon_ciel, devant=False)
    if not soleil_devant:
        _soleil(scene, proj, rayon_ciel, heure)
    # Façades visibles : la plus éloignée d'abord ; celles que le soleil ne voit pas sont ombrées
    visibles = [f for f in boite.facades() if proj.voit(direction(f["orientation_deg"]))]
    visibles.sort(key=lambda f: direction(f["orientation_deg"])[0] * proj.droite[0]
                  + direction(f["orientation_deg"])[1] * proj.droite[1])
    for facade in visibles:
        _facade(scene, proj, boite, facade, couleur_facade(boite, facade, soleil))
    # Toiture : les quatre coins hauts de la boîte ; grise si elle est adiabatique
    toiture = charte.GRIS_ADIABATIQUE if "toiture" in boite.parois_adiabatiques else MURS[boite.teinte]
    scene.polygone([proj.point(x, y, boite.hauteur_m) for x, y in _coins(boite)],
                   fill=_melanger(toiture, "#FFFFFF", 0.45),
                   stroke=charte.BLEU_NUIT, stroke_width=TRAIT, stroke_linejoin="round")
    # Devant la boîte : partie proche de la course dans le ciel, et le soleil s'il est de ce côté
    _course_dans_le_ciel(scene, proj, rayon_ciel, devant=True)
    if soleil_devant:
        _soleil(scene, proj, rayon_ciel, heure)
    _etiquette_soleil(scene, proj, rayon_ciel, heure, derriere=not soleil_devant)

    titre = (f"Boîte de {boite.longueur_m:.0f} m sur {boite.profondeur_m:.0f} m, {boite.nb_niveaux} niveaux, "
             f"façade principale au {point_cardinal(boite.orientation_deg)}")
    if boite.parois_adiabatiques:
        titre += ", parois adiabatiques : " + ", ".join(PAROIS_ADIABATIQUES[cle].lower()
                                                        for cle in boite.parois_adiabatiques)
    return scene.svg(titre)
