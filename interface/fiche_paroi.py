"""
============================================================
 FICHE D'UNE PAROI — ce que l'on sait d'une façade, de ses
 baies, de la toiture ou du plancher bas
============================================================
 Un clic sur le dessin (interface/dessin_cliquable.py) ou la
 liste « Paroi examinée » sous le dessin choisit une paroi :
 elle est surlignée dans le dessin (interface/axonometrie.py) et
 sa fiche dit ce que la boîte en fait saisir, avec ce qui s'en
 déduit sans calcul (surfaces, U × surface).

     paroi choisie ──→ surlignée dans le dessin
                  ├──→ fiche : surface, U (ou Uw, Sw, Tl,
                  │    protection), orientation, part vitrée,
                  │    masque (balcon), adiabatique ou non
                  └──→ ce qu'elle fait, une fois la boîte
                       calculée (moteur/bilan_paroi.py) : soleil
                       reçu et transmis, rayonnement froid,
                       déperditions, protections baissées, sur
                       les périodes du calcul lancé (0.9.20)

 Le survol d'une paroi du dessin montre son infobulle, une ligne
 tirée des mêmes grandeurs.

 Clés des parois (les mêmes pour la liste, la fiche, l'infobulle
 et le surlignage) :
   « principale », « pignon_a », « arriere », « pignon_b »   murs
   « baies_principale », …        baies d'une façade (si elle en a)
   « toiture », « plancher_bas »

 Fonctions sans Streamlit (elles se testent seules) : parois(),
 fiche(), infobulles(), bilan(). Sous la fiche, app.py ajoute le
 bouton « Mesurer l'effet de cette paroi » (interface/calcul.py,
 effet_paroi) ; la part de chaque paroi dans le DH est dans la
 brique « Le bilan en coupe » (interface/briques/bilan.py).
============================================================
"""

from interface.axonometrie import PREFIXE_BAIES
from interface.briques.graphiques import nombre
from interface.calcul import PERIODES_PAROIS
from interface.formulaire import LIBELLES_GESTION, LIBELLES_PROTECTION
from interface.saisie import SANS_PROTECTION, TEINTES, gabarit_baie, largeur_travee, libelle_orientation, \
    point_cardinal
from moteur.hypotheses import hyp

# ============================================================
# RÉGLAGES
# ============================================================
ADIABATIQUE = "oui : sur un local chauffé, sans échange de chaleur ni soleil"
UNITE_U = "W/m².K"


# ============================================================
# OUTILS
# ============================================================
def _facades(boite):
    """Les façades de la boîte, par clé (voir Boite.facades)."""
    return {facade["cle"]: facade for facade in boite.facades()}


def _pour_cent(part):
    return nombre(100 * part, 0, "%")


def _debord(boite, facade):
    """Balcon ou casquette au-dessus des baies de la façade, en texte."""
    if boite.debord_m > 0 and facade["cle"] in boite.facades_debord and not facade["adiabatique"]:
        return f"balcon ou casquette de {nombre(boite.debord_m, 1, 'm')} au nu de chaque plancher haut"
    return "aucun"


def _teinte(boite):
    return f"{boite.teinte} (absorption α = {nombre(hyp(TEINTES[boite.teinte]), 1)})"


# ============================================================
# LES PAROIS DE LA BOÎTE
# ============================================================
def parois(boite):
    """Les parois que l'on peut examiner, dans l'ordre de la liste : {clé: libellé}. Les baies d'une façade n'y
    sont que si elle en a (une façade adiabatique n'en a pas)."""
    choix = {}
    facades = boite.facades()
    for facade in facades:
        choix[facade["cle"]] = f"{facade['libelle']} ({point_cardinal(facade['orientation_deg'])})"
    for facade in facades:
        if facade["baies_m2"] > 0:
            choix[PREFIXE_BAIES + facade["cle"]] = \
                f"Baies — {facade['libelle'].lower()} ({point_cardinal(facade['orientation_deg'])})"
    choix["toiture"] = "Toiture"
    choix["plancher_bas"] = "Plancher bas"
    return choix


def fiche(boite, cle):
    """Fiche d'une paroi : liste de (grandeur, valeur en texte). Lève une KeyError si la clé n'est pas dans
    parois(boite)."""
    if cle not in parois(boite):
        raise KeyError(f"Paroi inconnue ou absente de la boîte : {cle}")
    facades = _facades(boite)
    adiabatique = cle in boite.parois_adiabatiques

    # --- Baies d'une façade : vitrage, protection, ouverture, masque ---
    if cle.startswith(PREFIXE_BAIES):
        facade = facades[cle[len(PREFIXE_BAIES):]]
        fh, hauteur, _, _ = gabarit_baie(facade["part_vitree"], boite.hauteur_etage_m)
        largeur = facade["part_vitree"] / fh * largeur_travee(facade["largeur_m"])
        lignes = [("Façade", f"{facade['libelle']}, {libelle_orientation(facade['orientation_deg'])}"),
                  ("Surface de baies", f"{nombre(facade['baies_m2'], 1, 'm²')} "
                                       f"({_pour_cent(facade['part_vitree'])} de la façade)"),
                  ("Une baie (largeur × hauteur)", f"{nombre(largeur, 2)} × {nombre(hauteur, 2, 'm')}, "
                                                   "une par travée et par niveau"),
                  ("Uw (baie nue)", nombre(boite.uw, 2, UNITE_U)),
                  ("Uw × surface", nombre(boite.uw * facade["baies_m2"], 1, "W/K")),
                  ("Sw (baie nue)", nombre(boite.sw, 2)),
                  ("Tl (baie nue)", nombre(boite.tl, 2))]
        if boite.protection == SANS_PROTECTION:
            lignes.append(("Protection mobile", "aucune"))
        else:
            lignes += [("Protection mobile", f"{LIBELLES_PROTECTION[boite.protection]}, gestion "
                                             f"{LIBELLES_GESTION[boite.gestion_protection].lower()}"),
                       ("Uw et Sw protégés", f"{nombre(boite.uw_protege, 2, UNITE_U)} ; "
                                             f"{nombre(boite.sw_protege, 2)}")]
        lignes.append(("Ouverture", f"ouvrable, jusqu'à {_pour_cent(boite.ratio_ouverture_max)} de la baie"
                                    if boite.ouvrable else "fixe"))
        lignes.append(("Masque proche", _debord(boite, facade)))
        return lignes

    # --- Mur d'une façade ---
    if cle in facades:
        facade = facades[cle]
        lignes = [("Orientation", libelle_orientation(facade["orientation_deg"])),
                  ("Surface de la façade", f"{nombre(facade['largeur_m'], 1)} × {nombre(boite.hauteur_m, 1, 'm')}"
                                           f" = {nombre(facade['surface_m2'], 1, 'm²')}")]
        if adiabatique:
            return lignes + [("Adiabatique", ADIABATIQUE + " ; ni baie, ni rive de plancher")]
        return lignes + [("Part vitrée", f"{_pour_cent(facade['part_vitree'])} "
                                         f"({nombre(facade['baies_m2'], 1, 'm²')} de baies)"),
                         ("Surface de mur", nombre(facade["mur_m2"], 1, "m²")),
                         ("U du mur", nombre(boite.u_mur, 2, UNITE_U)),
                         ("U × surface (mur)", nombre(boite.u_mur * facade["mur_m2"], 1, "W/K")),
                         ("Teinte", _teinte(boite)),
                         ("Masque proche des baies", _debord(boite, facade)),
                         ("Adiabatique", "non")]

    # --- Toiture et plancher bas : l'emprise de la boîte ---
    surface = ("Surface", f"{nombre(boite.longueur_m, 1)} × {nombre(boite.profondeur_m, 1, 'm')} = "
                          f"{nombre(boite.emprise_m2, 1, 'm²')}")
    if adiabatique:
        return [surface, ("Adiabatique", ADIABATIQUE + " ; sa rive de plancher reste comptée")]
    if cle == "toiture":
        return [surface, ("U", nombre(boite.u_toiture, 2, UNITE_U)),
                ("U × surface", nombre(boite.u_toiture * boite.emprise_m2, 1, "W/K")),
                ("Teinte", _teinte(boite)), ("Adiabatique", "non")]
    # Sur le sol, le moteur compte l'échange face à l'air extérieur (b = 1), sans soleil
    contact = "sur le sol (échange compté face à l'air extérieur, sans soleil)" if boite.plancher_sur_sol         else "sur l'extérieur"
    return [surface, ("U", nombre(boite.u_plancher, 2, UNITE_U)),
            ("U × surface", nombre(boite.u_plancher * boite.emprise_m2, 1, "W/K")), ("Contact", contact),
            ("Adiabatique", "non")]


def infobulles(boite):
    """Une ligne par paroi, montrée par le navigateur au survol du dessin : {clé: texte}."""
    textes = {}
    for cle, libelle in parois(boite).items():
        details = dict(fiche(boite, cle))
        if cle in boite.parois_adiabatiques:
            textes[cle] = f"{libelle} · adiabatique"
        elif cle.startswith(PREFIXE_BAIES):
            protection = "" if boite.protection == SANS_PROTECTION \
                else f" · {LIBELLES_PROTECTION[boite.protection].lower()}"
            textes[cle] = (f"{libelle} · {details['Surface de baies']} · Uw {nombre(boite.uw, 2)}, "
                           f"Sw {nombre(boite.sw, 2)}, Tl {nombre(boite.tl, 2)}{protection}")
        elif cle in ("toiture", "plancher_bas"):
            textes[cle] = f"{libelle} · {nombre(boite.emprise_m2, 1, 'm²')} · U {details['U']}"
        else:
            textes[cle] = (f"{libelle} · mur {details['Surface de mur']}, U {details['U du mur']} · "
                           f"part vitrée {details['Part vitrée'].split(' (')[0]}")
    return textes


# ============================================================
# CE QUE FAIT LA PAROI (boîte calculée)
# ============================================================
def bilan(resultats, cle):
    """Ce que fait la paroi sur les périodes des calculs lancés : (en-têtes des périodes, lignes de (grandeur,
    valeur par période)). Rien si la paroi n'entre pas dans le groupe (adiabatique) ou si aucun calcul ne la
    compte : ([], [])."""
    tables = {"dh": resultats.parois_dh, "bbio": resultats.parois_bbio}
    periodes = [(libelle, tables[calcul][(cle, periode)]) for calcul, periode, libelle in PERIODES_PAROIS
                if tables[calcul] is not None and (cle, periode) in tables[calcul]]
    if not periodes:
        return [], []
    baies = cle.startswith(PREFIXE_BAIES)

    def ligne(grandeur, valeur):
        return grandeur, [valeur(r) for _, r in periodes]

    def kwh(valeur, unite="kWh"):
        """Arrondi au kWh, sans « −0 »."""
        return nombre(round(valeur) + 0.0, 0, unite)

    lignes = [ligne("Durée", lambda r: nombre(r["heures"] / 24, 0, "jours")),
              ligne("Soleil reçu", lambda r: kwh(r["rayonnement_kwh_m2"], "kWh/m²")),
              ligne("Soleil transmis au logement", lambda r: kwh(r["solaire_kwh"])),
              # Pic : l'heure où la paroi fait entrer le plus de soleil, en Wh sur l'heure (sa puissance moyenne en W)
              ligne("Soleil transmis, heure la plus forte", lambda r: kwh(r["solaire_max_wh"], "Wh"))]
    # Rayonnement froid vers le ciel : nul pour une paroi verticale (éq. 17), la ligne n'est montrée que s'il compte
    if any(round(r["froid_kwh"]) != 0 for _, r in periodes):
        lignes.append(ligne("Rayonnement froid vers le ciel", lambda r: kwh(r["froid_kwh"])))
    lignes.append(ligne("Chaleur perdue par conduction", lambda r: kwh(r["deperdition_kwh"])))
    if baies:
        lignes.append(ligne("Protections baissées, heures de soleil", lambda r: _pour_cent(r["rprot_soleil"])))
        lignes.append(ligne("Baies ouvertes (moyenne du logement)", lambda r: _pour_cent(r["rouv_moyen"])))
    return [libelle for libelle, _ in periodes], lignes
