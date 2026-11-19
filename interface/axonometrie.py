"""
============================================================
 AXONOMÉTRIE — la boîte dessinée, orientée et vitrée
============================================================
 Dessin SVG de la boîte saisie (interface/saisie.py), dans le
 style de CBSh visuel : aplats clairs, traits fins et sombres.

 Ce que montre le dessin, à l'échelle :
   - la forme (longueur, profondeur, niveaux) ;
   - l'orientation : la boîte tourne sur un sol dont les points
     cardinaux sont fixes ;
   - les baies de chaque façade, de surface proportionnelle à la
     part vitrée saisie, avec leur protection mobile ;
   - les balcons ou casquettes, de la profondeur saisie ;
   - la course du soleil d'été (21 juin, à 46,5° N), dans le sol :
     le bord du disque, du lever au nord-est au coucher au
     nord-ouest par le sud ; le soleil de 16 h y est posé dans sa
     direction (azimut vrai, sans sa hauteur).

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
from interface.saisie import SANS_PROTECTION, gabarit_baie, largeur_travee, point_cardinal

# ============================================================
# RÉGLAGES DU DESSIN
# ============================================================
LARGEUR, HAUTEUR = 720, 470         # dimensions du SVG (px)
MARGE = 34                          # marge autour de la scène (px)
ELEVATION_DEG = 30.0                # hauteur du regard au-dessus de l'horizon
VUE_PAR_DEFAUT_DEG = 45.0           # spectateur au sud-ouest : façades sud et ouest visibles
VUES = {"sud-ouest": 45.0, "sud-est": -45.0, "nord-est": -135.0, "nord-ouest": 135.0}
RAYON_SOL = 0.7                     # rayon du disque du sol, en diagonales de la boîte
# Course du soleil d'été (21 juin) : ses vraies directions, portées au bord du sol
LATITUDE_DEG = 46.5                 # milieu de la France métropolitaine (de 42 à 51° N)
DECLINAISON_ETE_DEG = 23.44         # déclinaison du soleil au solstice d'été
SOLEIL_HEURE = 16.0                 # heure solaire du soleil dessiné : l'après-midi, qui chauffe le plus
POINTS_COURSE = 48                  # nombre de segments de la course
PART_VOLET = 0.28                   # part haute de la baie couverte par la protection dessinée
TRAIT = 1.4                         # épaisseur des traits (px)
POLICE = "font-family='Helvetica, Arial, sans-serif'"
# Couleur des murs selon la teinte saisie
MURS = {"claire": "#FBF7EE", "moyenne": "#EBD6B0", "sombre": "#A98F78", "noire": "#5F5962"}
OMBRE = 0.88                        # la seconde façade visible est un peu plus sombre
# Points cardinaux du sol : (lettre, azimut du moteur)
CARDINAUX = (("S", 0.0), ("O", 90.0), ("N", 180.0), ("E", -90.0))


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
    """Disque du sol et points cardinaux (le nord en gras)."""
    tour = [proj.point(rayon * math.cos(2 * math.pi * i / 72), rayon * math.sin(2 * math.pi * i / 72))
            for i in range(72)]
    scene.polygone(tour, fill=charte.SOL, stroke="none")
    for lettre, azimut in CARDINAUX:
        dx, dy = direction(azimut)
        scene.texte(proj.point(dx * rayon * 1.1, dy * rayon * 1.1), lettre, decalage=(0, 5),
                    text_anchor="middle", font_size=15, fill=charte.BLEU_NUIT,
                    font_weight="700" if lettre == "N" else "400")


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


def bord_du_sol(angle_horaire, rayon):
    """Point (est, nord) du bord du sol dans la direction du soleil (son azimut, sans sa hauteur)."""
    est, nord, _ = direction_soleil(angle_horaire)
    norme = math.hypot(est, nord)
    return rayon * est / norme, rayon * nord / norme


def _course_au_sol(scene, proj, rayon):
    """Course du soleil le 21 juin, dans le sol : le bord du disque, du lever (nord-est) au coucher (nord-ouest)
    par le sud, et les deux points du lever et du coucher.

    Dans le sol, et non dans le ciel : vue du sud, la vraie course en hauteur se projette presque en un trait.
    Seule la course d'été est montrée : c'est elle qui fait l'inconfort, et elle montre que le soleil du soir
    frappe les façades ouest, et même nord-ouest.
    """
    coucher = angle_coucher()
    course = [proj.point(*bord_du_sol(-coucher + 2 * coucher * i / POINTS_COURSE, rayon))
              for i in range(POINTS_COURSE + 1)]
    scene.ligne(course, stroke=charte.ORANGE, stroke_width=2.2, stroke_dasharray="2 6", stroke_linecap="round")
    for bout in (course[0], course[-1]):
        scene.cercle(bout, 4, fill=charte.ORANGE, stroke="none")


def _soleil(scene, proj, rayon):
    """Le soleil de SOLEIL_HEURE, posé sur la course au sol, dans sa direction."""
    soleil = proj.point(*bord_du_sol((SOLEIL_HEURE - 12.0) * 15.0, rayon))
    scene.cercle(soleil, 11, fill=charte.JAUNE, stroke=charte.ORANGE, stroke_width=1.6)
    scene.texte(soleil, f"21 juin, {SOLEIL_HEURE:.0f} h", decalage=(16, 4), font_size=12, fill=charte.BLEU_NUIT)


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
    if boite.debord_m > 0 and facade["cle"] in boite.facades_debord:
        for niveau in range(1, boite.nb_niveaux + 1):
            z = niveau * boite.hauteur_etage_m
            dalle = [proj.point(cx + tx * u + nx * d, cy + ty * u + ny * d, z)
                     for u, d in ((-demi, 0.0), (demi, 0.0), (demi, boite.debord_m), (-demi, boite.debord_m))]
            scene.polygone(dalle, fill=_melanger(couleur, "#FFFFFF", 0.35), fill_opacity=0.92, **trait)
    # Étiquette couchée le long du pied de la façade, lue de gauche à droite : nom, point cardinal, part vitrée
    etiquette = f"{facade['libelle']} · {point_cardinal(facade['orientation_deg'])} · {facade['part_vitree']:.0%}"
    milieu = p(0, 0)
    gauche, droite = sorted((p(-demi, 0), p(demi, 0)))
    scene.texte(milieu, etiquette.replace("%", " %"), decalage=(0, 17),
                vers=(milieu[0] + droite[0] - gauche[0], milieu[1] + droite[1] - gauche[1]),
                text_anchor="middle", font_size=12.5, fill=charte.BLEU_NUIT)


def dessiner(boite, vue_deg=VUE_PAR_DEFAUT_DEG):
    """SVG de la boîte, vue depuis l'azimut vue_deg (0 = depuis le sud, 90 = depuis l'ouest)."""
    proj = Projection(vue_deg)
    scene = _Scene()
    rayon = RAYON_SOL * math.hypot(boite.longueur_m, boite.profondeur_m)
    # Le soleil, au bord du sol, est devant la boîte s'il est du côté du spectateur, derrière sinon
    x, y = bord_du_sol((SOLEIL_HEURE - 12.0) * 15.0, rayon)
    soleil_devant = x * proj.regard[0] + y * proj.regard[1] < 0

    _sol(scene, proj, rayon)
    _course_au_sol(scene, proj, rayon)  # dans le sol : la boîte cache la partie qui passe derrière elle
    if not soleil_devant:
        _soleil(scene, proj, rayon)
    # Façades visibles : la plus éloignée d'abord ; la seconde est ombrée
    mur = MURS[boite.teinte]
    visibles = [f for f in boite.facades() if proj.voit(direction(f["orientation_deg"]))]
    visibles.sort(key=lambda f: direction(f["orientation_deg"])[0] * proj.droite[0]
                  + direction(f["orientation_deg"])[1] * proj.droite[1])
    for rang, facade in enumerate(visibles):
        _facade(scene, proj, boite, facade, mur if rang == 0 else _melanger(mur, charte.BLEU_NUIT, 1.0 - OMBRE))
    # Toiture : les quatre coins hauts de la boîte
    nx, ny = direction(boite.orientation_deg)
    tx, ty = ny, -nx
    coins = [(sx * tx * boite.longueur_m / 2 + sy * nx * boite.profondeur_m / 2,
              sx * ty * boite.longueur_m / 2 + sy * ny * boite.profondeur_m / 2)
             for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    scene.polygone([proj.point(x, y, boite.hauteur_m) for x, y in coins], fill=_melanger(mur, "#FFFFFF", 0.45),
                   stroke=charte.BLEU_NUIT, stroke_width=TRAIT, stroke_linejoin="round")
    if soleil_devant:
        _soleil(scene, proj, rayon)

    titre = (f"Boîte de {boite.longueur_m:.0f} m sur {boite.profondeur_m:.0f} m, {boite.nb_niveaux} niveaux, "
             f"façade principale au {point_cardinal(boite.orientation_deg)}")
    return scene.svg(titre)
