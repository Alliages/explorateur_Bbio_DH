"""
============================================================
 COUPE — le bilan de chaleur de la boîte, en coupe schématique
============================================================
 Coupe transversale de la boîte, perpendiculaire à la façade
 principale, hors échelle : façade principale à gauche, façade
 arrière à droite, toiture en haut, plancher bas en bas. Les
 deux pignons, devant et derrière le plan de coupe, sont réunis
 en un cercle au milieu du logement (⊙ : la chaleur sort vers le
 lecteur ; ⊗ : elle entre).

     bilan en coupe d'une période (interface/calcul.py, Resultats.
     coupe_bbio ou coupe_dh) : chaleur entrée par poste, négative
     si elle sort, cumulée sur la période (kWh) ou sur l'heure de
     pointe (Wh)
                  │
                  ▼
     une flèche par poste, d'épaisseur proportionnelle à sa valeur,
     tournée vers l'intérieur si la chaleur entre :
       jaune      soleil transmis (baies, murs, toiture)
       bleu nuit  échange par les parois (conduction et rayonnement
                  froid vers le ciel) et ponts thermiques
       gris       air : ventilation, infiltrations, baies ouvertes
       orange     apports internes (occupants, appareils, éclairage)
       prune      chauffage ; bleu ciel : froid

 Chaque paroi et ses flèches portent la clé de la paroi (attribut
 data-cle) : un clic l'ouvre dans la fiche sous l'axonométrie
 (interface/dessin_cliquable.py). L'air des baies ouvertes n'est
 pas réparti par façade (hypothèse 103 de docs/audit.md) : une
 seule flèche, par les baies de la façade arrière.

 Ce fichier ne dépend pas de Streamlit : dessiner_coupe() rend le
 texte d'un SVG.
============================================================
"""

import math
from xml.sax.saxutils import escape

from interface import charte
from interface.calcul import ECHANGE, RESTE, SOLEIL
from interface.saisie import point_cardinal

# ============================================================
# RÉGLAGES DU DESSIN (px)
# ============================================================
LARGEUR, HAUTEUR = 720, 500
X0, X1 = 250, 470               # nus extérieurs des façades principale (gauche) et arrière (droite)
YT, YB = 140, 360               # dessus de la toiture, dessous du plancher bas
EPAISSEUR = 12                  # des parois
BAIE = (175, 255)               # haut et bas des baies dans les façades
FLECHE_MAX = 22                 # épaisseur de la flèche du plus grand poste
FLECHE_MIN = 1.5                # épaisseur des plus petits postes, pour qu'ils restent visibles
VALEUR_MIN = {"kWh": 1.0, "Wh": 10.0}     # en dessous (en valeur absolue), le poste n'est pas dessiné
TAILLE_TEXTE = 11.5
LARGEUR_AFFICHEE = 820          # largeur maximale à l'écran (px) : la brique occupe toute la page
COULEURS = {"soleil": charte.JAUNE, "paroi": charte.BLEU_NUIT, "air": charte.GRIS, "apports": charte.ORANGE,
            "chauffage": charte.COULEUR_CHAUFFAGE, "froid": charte.COULEUR_FROID}
LEGENDE = (("soleil", "Soleil"), ("paroi", "Parois et ponts thermiques"), ("air", "Air"),
           ("apports", "Apports internes"), ("chauffage", "Chauffage"), ("froid", "Froid"))
LIBELLES_POSTES = {"ventilation": "Ventilation", "infiltrations": "Infiltrations", "ouvertures": "Baies ouvertes",
                   "ponts_thermiques": "Ponts thermiques", "apports_internes": "Apports internes",
                   "chauffage": "Chauffage", "refroidissement": "Froid"}


# ============================================================
# OÙ VA CHAQUE FLÈCHE
# ============================================================
def _miroir(point):
    """Le point symétrique par rapport à l'axe vertical de la coupe (façade arrière ↔ façade principale)."""
    return LARGEUR - point[0], point[1]


# Façade principale (à gauche) : (poste, genre, point dehors, point dedans, côté de l'étiquette)
_GAUCHE = (("baies.soleil", "soleil", (120, 100), (EPAISSEUR + X0, 200), "gauche"),
           ("baies.echange", "paroi", (150, 240), (X0 + 22, 240), "gauche"),
           ("mur.soleil", "soleil", (140, 266), (X0 + EPAISSEUR, 295), "gauche"),
           ("mur.echange", "paroi", (150, 322), (X0 + 22, 322), "gauche"))
# Ailleurs : (poste, genre, point dehors, point dedans, côté de l'étiquette)
_AUTRES = (("toiture.soleil", "soleil", (270, 50), (318, YT + EPAISSEUR), "haut"),
           ("toiture.echange", "paroi", (350, 55), (350, YT + EPAISSEUR), "haut"),
           ("ventilation", "air", (435, 55), (435, YT + EPAISSEUR), "haut_droite"),
           ("plancher_bas.echange", "paroi", (335, 445), (335, YB - EPAISSEUR), "bas"),
           ("infiltrations", "air", (150, 348), (X0 + 22, 348), "gauche"),
           ("ouvertures", "air", _miroir((150, 218)), _miroir((X0 + 22, 218)), "droite"),
           ("ponts_thermiques", "paroi", (530, 445), (X1 - 8, YB - 8), "bas"))
# Dans le logement : (poste, genre, point de départ, point d'arrivée quand la chaleur entre)
_DEDANS = (("apports_internes", "apports", (300, YB - 18), (300, 285)),
           ("chauffage", "chauffage", (370, YB - 18), (370, 285)),
           ("refroidissement", "froid", (430, YB - 18), (430, 285)))
NOMS_DEDANS = {"apports_internes": "Apports", "chauffage": "Chauffage", "refroidissement": "Froid"}
CENTRE_PIGNONS = (360, 205)


def _postes_de_facade(cle_facade, droite):
    """Les quatre flèches d'une façade (baies et mur) : postes du bilan, genre, points, côté de l'étiquette."""
    fleches = []
    for poste, genre, dehors, dedans, cote in _GAUCHE:
        partie, sorte = poste.split(".")
        cle = cle_facade if partie == "mur" else f"baies_{cle_facade}"
        if droite:
            dehors, dedans, cote = _miroir(dehors), _miroir(dedans), "droite"
        fleches.append((f"{cle}.{sorte}", cle, genre, dehors, dedans, cote))
    return fleches


# ============================================================
# FORMES
# ============================================================
def _fleche(depart, arrivee, epaisseur, couleur, titre, cle=None):
    """Flèche pleine de depart à arrivee : un polygone (corps et pointe), son infobulle et sa clé de paroi."""
    dx, dy = arrivee[0] - depart[0], arrivee[1] - depart[1]
    longueur = math.hypot(dx, dy)
    ux, uy = dx / longueur, dy / longueur           # le long de la flèche
    nx, ny = -uy, ux                                # en travers
    pointe = min(max(9.0, 1.3 * epaisseur), 0.6 * longueur)
    demi, demi_pointe = epaisseur / 2.0, max(5.0, 0.95 * epaisseur)
    bx, by = arrivee[0] - ux * pointe, arrivee[1] - uy * pointe
    points = [(depart[0] + nx * demi, depart[1] + ny * demi), (bx + nx * demi, by + ny * demi),
              (bx + nx * demi_pointe, by + ny * demi_pointe), arrivee,
              (bx - nx * demi_pointe, by - ny * demi_pointe), (bx - nx * demi, by - ny * demi),
              (depart[0] - nx * demi, depart[1] - ny * demi)]
    attribut_cle = f" data-cle='{cle}'" if cle else ""
    return (f"<polygon points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in points)}' fill='{couleur}' "
            f"fill-opacity='0.92' stroke='{charte.BLEU_NUIT}' stroke-width='0.6' stroke-linejoin='round'"
            f"{attribut_cle}><title>{escape(titre)}</title></polygon>")


def _texte(point, contenu, ancre="middle", taille=TAILLE_TEXTE, gras=False, couleur=charte.BLEU_NUIT, rotation=0):
    tourner = f" transform='rotate({rotation} {point[0]:.1f} {point[1]:.1f})'" if rotation else ""
    poids = " font-weight='600'" if gras else ""
    return (f"<text x='{point[0]:.1f}' y='{point[1]:.1f}' text-anchor='{ancre}' font-size='{taille}' "
            f"fill='{couleur}'{poids}{tourner}>{escape(contenu)}</text>")


def _etiquette(dehors, cote, contenu):
    """Valeur d'une flèche, posée au-delà de son point extérieur."""
    decalages = {"gauche": ((-6, 4), "end"), "droite": ((6, 4), "start"), "haut": ((0, -8), "middle"),
                 "haut_droite": ((8, 10), "start"), "bas": ((0, 16), "middle")}
    (dx, dy), ancre = decalages[cote]
    return _texte((dehors[0] + dx, dehors[1] + dy), contenu, ancre)


def _valeur(valeur, unite):
    """Valeur d'une flèche, sans signe (la flèche dit le sens) : « 1 262 Wh », « 59 kWh »."""
    return f"{abs(valeur):,.0f} {unite}".replace(",", " ")


def _paroi(x, y, largeur, hauteur, cle, titre, adiabatique):
    remplissage = charte.GRIS_ADIABATIQUE if adiabatique else "#E8D9BC"
    return (f"<rect x='{x}' y='{y}' width='{largeur}' height='{hauteur}' fill='{remplissage}' "
            f"stroke='{charte.BLEU_NUIT}' stroke-width='1' data-cle='{cle}'><title>{escape(titre)}</title></rect>")


# ============================================================
# LA COUPE
# ============================================================
def dessiner_coupe(boite, bilan, titre_periode, surlignee=None, unite="kWh"):
    """SVG de la coupe de la boîte avec un bilan : {poste: chaleur entrée, négative si elle sort}, cumulée sur une
    période (kWh) ou sur l'heure de pointe (Wh) (interface/calcul.py, Resultats.coupe_bbio ou coupe_dh).
    surlignee : clé de la paroi examinée, entourée."""
    seuil = VALEUR_MIN[unite]
    facades = {facade["cle"]: facade for facade in boite.facades()}
    adiabatiques = set(boite.parois_adiabatiques)
    morceaux = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {LARGEUR} {HAUTEUR}' width='{LARGEUR}' "
                f"height='{HAUTEUR}' role='img' font-family='sans-serif' "
                f"style='max-width:{LARGEUR_AFFICHEE}px;margin:auto'>",
                f"<title>{escape('Coupe schématique de la boîte, hors échelle : ' + titre_periode)}</title>",
                f"<rect width='{LARGEUR}' height='{HAUTEUR}' rx='22' fill='{charte.FOND_SCHEMA}'/>"]

    # --- Le sol, sous un plancher sur terre-plein ---
    if boite.plancher_sur_sol:
        morceaux.append(f"<rect x='{X0 - 90}' y='{YB}' width='{X1 - X0 + 180}' height='{HAUTEUR - YB - 40}' "
                        f"fill='{charte.SOL}'/>")

    # --- Les parois : toiture, plancher bas, façades (mur plein ou mur et baie) ---
    morceaux.append(_paroi(X0, YT, X1 - X0, EPAISSEUR, "toiture", "Toiture", "toiture" in adiabatiques))
    morceaux.append(_paroi(X0, YB - EPAISSEUR, X1 - X0, EPAISSEUR, "plancher_bas", "Plancher bas",
                           "plancher_bas" in adiabatiques))
    for cle, x in (("principale", X0), ("arriere", X1 - EPAISSEUR)):
        facade = facades[cle]
        nom = f"{facade['libelle']} ({point_cardinal(facade['orientation_deg'])})"
        if facade["baies_m2"] > 0:
            morceaux.append(_paroi(x, YT, EPAISSEUR, BAIE[0] - YT, cle, nom, facade["adiabatique"]))
            morceaux.append(_paroi(x, BAIE[1], EPAISSEUR, YB - BAIE[1], cle, nom, facade["adiabatique"]))
            morceaux.append(f"<rect x='{x}' y='{BAIE[0]}' width='{EPAISSEUR}' height='{BAIE[1] - BAIE[0]}' "
                            f"fill='{charte.BLEU_CIEL}' fill-opacity='0.75' stroke='{charte.BLEU_NUIT}' "
                            f"stroke-width='1' data-cle='baies_{cle}'><title>{escape('Baies — ' + nom)}</title>"
                            f"</rect>")
        else:
            morceaux.append(_paroi(x, YT, EPAISSEUR, YB - YT, cle, nom, facade["adiabatique"]))
        # Nom de la façade, dans le coin haut de son côté
        adiab = " · adiabatique" if facade["adiabatique"] else ""
        nom_coin = f"{facade['libelle']} · {point_cardinal(facade['orientation_deg'])}{adiab}"
        morceaux.append(_texte((24, 30), f"← {nom_coin}", ancre="start", gras=True) if cle == "principale"
                        else _texte((LARGEUR - 24, 30), f"{nom_coin} →", ancre="end", gras=True))

    # --- Les flèches : leur épaisseur suit les kWh, le plus grand poste dessiné prend FLECHE_MAX ---
    fleches = _postes_de_facade("principale", False) + _postes_de_facade("arriere", True)
    cles_parois = {"toiture.soleil": "toiture", "toiture.echange": "toiture", "plancher_bas.echange": "plancher_bas"}
    # L'air des baies ouvertes passe par les baies de la façade arrière, ou de la principale si l'arrière n'en a pas
    par_la_principale = facades["arriere"]["baies_m2"] == 0 and facades["principale"]["baies_m2"] > 0
    for poste, genre, dehors, dedans, cote in _AUTRES:
        if poste == "ouvertures" and par_la_principale:
            dehors, dedans, cote = _miroir(dehors), _miroir(dedans), "gauche"
        fleches.append((poste, cles_parois.get(poste), genre, dehors, dedans, cote))
    pignons = _pignon(bilan, "pignon_a") + _pignon(bilan, "pignon_b")
    dessinees = [bilan.get(poste, 0.0) for poste, *_ in fleches] + [bilan.get(p, 0.0) for p, *_ in _DEDANS]
    plus_grand = max([abs(v) for v in dessinees] + [abs(pignons), seuil])

    def epaisseur(valeur):
        return max(FLECHE_MIN, FLECHE_MAX * abs(valeur) / plus_grand)

    for poste, cle, genre, dehors, dedans, cote in fleches:
        valeur = bilan.get(poste, 0.0)
        if abs(valeur) < seuil:
            continue
        depart, arrivee = (dehors, dedans) if valeur > 0 else (dedans, dehors)
        nom = LIBELLES_POSTES[poste] if poste in LIBELLES_POSTES else _nom_poste(poste, facades)
        sens = "entrés" if valeur > 0 else "sortis"
        morceaux.append(_fleche(depart, arrivee, epaisseur(valeur), COULEURS[genre],
                                f"{nom} : {_valeur(valeur, unite)} {sens}", cle))
        etiquette = _valeur(valeur, unite) if poste not in LIBELLES_POSTES else f"{nom} {_valeur(valeur, unite)}"
        morceaux.append(_etiquette(dehors, cote, etiquette))

    # --- Dans le logement : apports internes, chauffage, froid (flèches qui partent du plancher) ---
    for poste, genre, bas, haut in _DEDANS:
        valeur = bilan.get(poste, 0.0)
        if abs(valeur) < seuil:
            continue
        depart, arrivee = (bas, haut) if valeur > 0 else (haut, bas)
        sens = "apportés" if valeur > 0 else "retirés"
        morceaux.append(_fleche(depart, arrivee, epaisseur(valeur), COULEURS[genre],
                                f"{LIBELLES_POSTES[poste]} : {_valeur(valeur, unite)} {sens}"))
        morceaux.append(_texte((haut[0], haut[1] - 8), NOMS_DEDANS[poste], taille=10.5))
        morceaux.append(_texte((haut[0], haut[1] - 20), _valeur(valeur, unite), taille=10.5))

    # --- Les pignons, de part et d'autre du plan de coupe : ⊙ la chaleur sort vers le lecteur, ⊗ elle entre ---
    if abs(pignons) >= seuil and not {"pignon_a", "pignon_b"} <= adiabatiques:
        rayon = max(7.0, 0.9 * epaisseur(pignons))
        cx, cy = CENTRE_PIGNONS
        detail = " ; ".join(f"{facades[cle]['libelle']} {_valeur(_pignon(bilan, cle), unite)}"
                            for cle in ("pignon_a", "pignon_b") if cle not in adiabatiques)
        sens = "entrés" if pignons > 0 else "sortis"
        infobulle = f"Pignons, soleil et échange : {_valeur(pignons, unite)} {sens} ({detail})"
        signe = (f"<line x1='{cx - rayon * 0.55:.1f}' y1='{cy - rayon * 0.55:.1f}' x2='{cx + rayon * 0.55:.1f}' "
                 f"y2='{cy + rayon * 0.55:.1f}' stroke='white' stroke-width='2'/>"
                 f"<line x1='{cx - rayon * 0.55:.1f}' y1='{cy + rayon * 0.55:.1f}' x2='{cx + rayon * 0.55:.1f}' "
                 f"y2='{cy - rayon * 0.55:.1f}' stroke='white' stroke-width='2'/>") if pignons > 0 else \
            f"<circle cx='{cx}' cy='{cy}' r='{max(2.0, rayon * 0.22):.1f}' fill='white'/>"
        morceaux.append(f"<g data-cle='{'pignon_a' if 'pignon_a' not in adiabatiques else 'pignon_b'}'>"
                        f"<title>{escape(infobulle)}</title>"
                        f"<circle cx='{cx}' cy='{cy}' r='{rayon:.1f}' fill='{COULEURS['paroi']}' "
                        f"fill-opacity='0.92'/>{signe}</g>")
        morceaux.append(_texte((cx, cy + rayon + 15), f"Pignons {_valeur(pignons, unite)}", taille=10.5))

    # --- Ce qui reste : la chaleur gardée par la masse (exacte : moteur.bilan_paroi.masse_gardee) ---
    reste = bilan.get(RESTE, 0.0)
    if abs(reste) >= seuil:
        verbe = "gardés par la masse" if reste > 0 else "rendus par la masse"
        morceaux.append(_texte(((X0 + X1) / 2.0, YT + EPAISSEUR + 20), f"{_valeur(reste, unite)} {verbe}", taille=10.5,
                               couleur=charte.GRIS))

    # --- La paroi examinée, entourée ---
    if surlignee:
        morceaux.extend(_contour(surlignee, facades))

    # --- Légende ---
    x = 24
    for genre, libelle in LEGENDE:
        morceaux.append(f"<rect x='{x}' y='{HAUTEUR - 27}' width='12' height='12' rx='2' fill='{COULEURS[genre]}'/>")
        morceaux.append(_texte((x + 17, HAUTEUR - 17), libelle, ancre="start", taille=11))
        x += 30 + 6.2 * len(libelle)
    morceaux.append("</svg>")
    return "\n".join(morceaux)


def _pignon(bilan, cle):
    """Chaleur entrée par un pignon, mur et baies, soleil et échange (kWh ; négatif : sortie)."""
    return sum(bilan.get(f"{paroi}.{sorte}", 0.0) for paroi in (cle, f"baies_{cle}") for sorte in (SOLEIL, ECHANGE))


def _nom_poste(poste, facades):
    """Nom lisible d'un poste « <clé de paroi>.<soleil|echange> »."""
    cle, sorte = poste.split(".")
    if cle in ("toiture", "plancher_bas"):
        nom = "Toiture" if cle == "toiture" else "Plancher bas"
    elif cle.startswith("baies_"):
        nom = f"Baies — {facades[cle[len('baies_'):]]['libelle'].lower()}"
    else:
        nom = f"Mur — {facades[cle]['libelle'].lower()}"
    return f"{nom}, {'soleil transmis' if sorte == SOLEIL else 'échange (H . Δθ et ciel)'}"


def _contour(cle, facades):
    """Contour orange de la paroi examinée, s'il y en a une dans la coupe (pas pour les pignons : leur cercle)."""
    trait = (f"fill='none' stroke='{charte.COULEUR_SURLIGNAGE}' stroke-width='3.5' stroke-linejoin='round' "
             f"pointer-events='none'")
    if cle == "toiture":
        return [f"<rect x='{X0 - 2}' y='{YT - 2}' width='{X1 - X0 + 4}' height='{EPAISSEUR + 4}' {trait}/>"]
    if cle == "plancher_bas":
        return [f"<rect x='{X0 - 2}' y='{YB - EPAISSEUR - 2}' width='{X1 - X0 + 4}' height='{EPAISSEUR + 4}' {trait}/>"]
    if cle in ("principale", "arriere", "baies_principale", "baies_arriere"):
        facade = cle.replace("baies_", "")
        x = X0 if facade == "principale" else X1 - EPAISSEUR
        if cle.startswith("baies_"):
            return [f"<rect x='{x - 2}' y='{BAIE[0] - 2}' width='{EPAISSEUR + 4}' height='{BAIE[1] - BAIE[0] + 4}' "
                    f"{trait}/>"]
        return [f"<rect x='{x - 2}' y='{YT - 2}' width='{EPAISSEUR + 4}' height='{YB - YT + 4}' {trait}/>"]
    if cle in ("pignon_a", "pignon_b", "baies_pignon_a", "baies_pignon_b"):
        cx, cy = CENTRE_PIGNONS
        return [f"<circle cx='{cx}' cy='{cy}' r='{FLECHE_MAX + 6}' {trait} stroke-dasharray='6 4'/>"]
    return []
