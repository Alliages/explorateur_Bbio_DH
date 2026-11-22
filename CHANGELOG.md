# Journal des versions — Explorateur Bbio / DH

Règle : `0.8.x` tant que l'outil n'est pas fonctionnel, `0.9.x` quand il fonctionne, `1.0` à la première version
annoncée et diffusée. Dernier chiffre **pair** = évolution, **impair** = correction.

## 0.9.27 — correction (22/11/2026), audit de la 0.9.25

Audit sans changement du calcul (détail : `docs/audit.md`, 0.9.27).

- **Non-régression** : DH et Bbio des six bâtiments de départ identiques à la 0.9.15 (à 0,2 point près sur le
  Bbio). Validation sur les études et comparaison horaire au moteur : à relancer sur le poste qui les a.
- **Relecture** de `dh.py`, `confort.py`, `brasseurs.py` et `enveloppe.py` (sans l'annexe III). Quatre points à
  vérifier, texte ou moteur en main : inertie séquentielle sans effet dès que Ams ≥ Amq, d'où un effet non
  monotone (classe lourde sans effet, moyenne − 16 % de DH) ; hystérésis des brasseurs (régime maximal gardé
  jusqu'à l'arrêt, effet ≤ 2,5 °C.h sur la boîte) ; **position du soleil des fichiers météo en retard d'une heure
  sur l'heure du calcul** (l'outil suit les fichiers ; le dessin, lui, montre le soleil astronomique) ; sources du
  confort adaptatif citées de deux façons.
- **Tendances de la boîte** (H1a et H3, une saisie à la fois) : sens attendu pour l'inertie, le traversant,
  l'ouverture, la teinte, le Sw, l'isolation, le balcon, les brasseurs. Deux signaux : plus de vitrage donne moins
  de DH (la surface ouvrante suit la surface des baies ; à surface ouvrante égale, le DH monte bien) ; une façade
  vitrée à l'est donne un peu plus de DH qu'à l'ouest. Six tendances testées (`tests/test_tendances.py`).
- **Documentation** : `README.md` (état, résultat de l'exemple 27,8 et 1 981 au lieu de 34,3 et 1 978, lien de la
  capture), fiabilité affichée à l'accueil et dans les briques Bbio et DH (46 groupes de 16 études, chiffres de la
  0.9.15), `docs/passation.md`.

## 0.9.25 — correction (22/11/2026), bilan en coupe exact et heure de pointe

- **Correction du bilan en coupe** : la conduction des parois et des baies est désormais celle du modèle du groupe
  (parois opaques et ponts vers la masse θmq, baies vers les surfaces θs, rayonnement intérieur perdu par les
  vitrages compris), et non plus la lecture H × (θi − θe). Le bilan ferme exactement : « gardés par la masse » est
  le stockage du modèle. Sur le logement faible sans protection, semaine la plus chaude : 19 kWh affichés en
  0.9.24, dont 6 seulement stockés ; 6 kWh désormais. La 0.9.24 disait à tort « 10 % sur la semaine
  (stockage) » : hypothèse 103 corrigée dans `docs/audit.md`.
- **Heure de pointe** : choix « Sur la période (kWh) / Heure de pointe (Wh) » au-dessus de la coupe. L'heure de
  pointe est celle où le soleil transmis est le plus fort ; date, température dehors et dedans, chaque poste en Wh
  (hypothèse 105). Même cas : baies sud 976 Wh en une heure, apports internes 530 Wh, 4 035 Wh gardés par la masse
  (39,2 °C dehors, baies fermées).
- **Fiche d'une paroi** : « Soleil transmis, heure la plus forte » (Wh) ; « Chaleur perdue par conduction » (celle
  du modèle) remplace U × S × (θi − θe).
- Moteur : `bilan_paroi` lit les nœuds du modèle (`preparer_modele`, `theta_mq_moy`, `theta_s_moy`, `hg_es`),
  `masse_gardee`, `rayonnement_perdu_par_les_baies` ; `postes_du_groupe` prend le jeu météo. Résultats inchangés
  (DH 732 °C.h, Bbio 119,8 ; logement faible sans protection : DH 942).
- Tests : bilan exact heure par heure (10⁻⁶ W), parois et ponts = flux_parois, baies = flux du modèle ; heure de
  pointe. Aide `lecture_coupe`.

## 0.9.24 — évolution (22/11/2026), bilan en coupe et effet d'une paroi

Étape 4 du plan « informations au clic sur une paroi ou un vitrage » (`ROADMAP.md`) : le plan est achevé.

- **Brique « Le bilan en coupe »** (`interface/briques/bilan.py`), proposée avec le Bbio comme avec le DH :
  - coupe schématique de la boîte, hors échelle (`interface/coupe.py`) : façade principale à gauche, arrière à
    droite, toiture, plancher bas ; une flèche par poste, d'épaisseur proportionnelle à ses kWh, dans le sens où
    passe la chaleur : soleil transmis (baies, murs, toiture), échange par les parois (H × Δθ et rayonnement vers
    le ciel), ponts thermiques, ventilation, infiltrations, baies ouvertes, apports internes, chauffage, froid ;
    les deux pignons en un cercle (⊙ la chaleur sort, ⊗ elle entre) ; la chaleur gardée par la masse ;
  - périodes des calculs lancés : semaine la plus chaude et été (DH), année moyenne (Bbio) ;
  - tableau du bilan, entré et sorti par famille, équilibré par la masse ;
  - avec le DH, « Ce qui chauffe le logement aux heures d'inconfort » : part de chaque paroi et de chaque poste
    dans la chaleur entrée aux heures qui comptent des DH ;
  - un clic sur une paroi de la coupe l'ouvre dans la fiche sous l'axonométrie (composant de la 0.9.22) ; la paroi
    examinée est entourée dans la coupe aussi.
- **Bouton « Mesurer l'effet de cette paroi »** sous la fiche : le calcul relancé sans elle (baies remplacées par
  le mur de leur façade ; mur, toiture ou plancher bas retirés comme une paroi adiabatique), DH et Bbio comparés au
  calcul affiché (`calcul.effet_paroi`, `saisie.construire_projet(…, sans=…)`, mis en cache). Logement de 70 m²
  moyen : sans les baies sud, DH 732 → 994 °C.h (elles servent aussi à ventiler la nuit) ; sans la toiture,
  732 → 615 °C.h.
- **Moteur** : `calculer_besoins` sort l'air poste par poste (`hg_ventilation`, `theta_souffle`, `hg_ouvertures`)
  et les apports internes injectés (`phi_apports`) ; `bilan_paroi.postes_du_groupe` et `entrant`. Aucun résultat
  ne change (logement de 70 m² moyen : DH 732 °C.h, Bbio 119,8).
- **Lecture** (hypothèses 103 et 104 de `docs/audit.md`) : air séparé exactement (θeieq est la moyenne pesée) ;
  le reste du bilan est la chaleur gardée par la masse plus l'écart de lecture des parois : 0,7 % des apports sur
  l'année du Bbio, 2,2 % sur l'été, 10 % sur la semaine la plus chaude (et non du stockage seul : corrigé en
  0.9.25).
- Tests : fermeture du bilan, séparation de l'air, projet sans une paroi, coupe et tableau, effet de la toiture.
  Aides `periode_coupe`, `bilan_coupe`, `part_dh`, `effet_paroi`.

## 0.9.22 — évolution (22/11/2026), clic sur le dessin

Étape 5 du plan « informations au clic sur une paroi ou un vitrage » (`ROADMAP.md`).

- **Cliquer sur un mur, des baies (ou leur protection) ou la toiture du dessin** les choisit dans la liste « Paroi
  examinée » : contour orange, fiche et « Ce qu'elle fait ». La liste reste, pour le clavier et pour les parois
  cachées dans la vue (façade de dos, plancher bas). Survol : main et forme éclaircie ; infobulles inchangées.
- **`interface/dessin_cliquable.py`** : petit composant Streamlit (`st.components.v2`, HTML, CSS et JavaScript
  écrits dans le fichier, sans outil de construction) qui affiche le SVG et renvoie la clé de la paroi cliquée
  (événement `clic`). Il remplace `st.markdown(unsafe_allow_html=True)` (0.9.18).
- **`interface/axonometrie.py`** : chaque mur, baie, protection et la toiture portent la clé de leur paroi
  (attribut `data-cle`, les clés de `fiche_paroi.parois`).
- Test `test_dessin_cliquable` ; aide `paroi_examinee` et légende du dessin complétées. Résultats inchangés.

## 0.9.20 — évolution (22/11/2026), ce que fait une paroi

Étape 3 du plan « informations au clic sur une paroi ou un vitrage » (`ROADMAP.md`).

- **`moteur/bilan_paroi.py`** (sans dépendre de l'interface) : après le calcul du groupe, bilan heure par heure de
  chaque baie et de chaque paroi opaque, avec les sorties horaires du calcul : rayonnement reçu (Isr), flux solaire
  transmis (baie : Sw nu et Sw protégé pesés par la fermeture ; paroi : Sf), rayonnement froid vers le ciel,
  déperdition H × (θi − θe), fermeture de la protection, ouverture des baies. `resumer` cumule une période.
  - Contrôle : la somme des baies redonne Fs1 + Fs3 + φsl du groupe, celle des parois opaques φsh (écart
    10⁻¹³ W ; tests `tests/test_bilan_paroi.py`).
  - Lecture et limites : hypothèse 102 de `docs/audit.md`.
- **Moteur** : `calculer_besoins` sort la fermeture de chaque baie (`rprot_baie_0`, `rprot_baie_1`…, si le groupe
  a des protections) ; `protections.u_protege` devient public ; `dh.debut_semaine_la_plus_chaude` (venue de la
  brique « Une semaine chaude », qui l'emploie). Aucun résultat ne change : logement de 70 m² moyen DH 732 °C.h,
  Bbio 119,8 ; étude de Paris : DH − 6,1 et + 6,9 %.
- **`interface/calcul.py`** : chaque calcul rend le bilan de chaque paroi résumé sur ses périodes (`parois_dh` :
  semaine la plus chaude et période de confort adaptatif ; `parois_bbio` : année moyenne), gardé dans le cache.
  Noms des composants du projet : `saisie.noms_composants`, employé aussi par `construire_projet`.
- **Sous la fiche de la paroi examinée** : tableau « Ce qu'elle fait », une colonne par période des calculs
  lancés : durée, soleil reçu (kWh/m²), soleil transmis (kWh), rayonnement froid (s'il compte : toiture), chaleur
  perdue U × S × (θi − θe), et pour des baies, protections baissées aux heures de soleil et baies ouvertes. Rien de
  recalculé : le bilan est lu dans le cache, et seulement si la saisie n'a pas changé depuis le calcul. Aide
  `bilan_paroi`.
- **Correction de la fiche (0.9.18)** : plancher sur le sol, U × surface affiché ; le moteur compte cet échange
  face à l'air extérieur (b = 1), la fiche disait à tort « calculé à part ».
- Feuille de route : « Diffusion » passe en 0.9.22.
- Vu dans Chrome (logement de 70 m², Bbio et DH, baies du sud : semaine la plus chaude 27 kWh/m² reçus, 15 kWh
  transmis, volets baissés 84 % des heures de soleil). Tests : 382 réussis, 2 sautés.

## 0.9.18 — évolution (22/11/2026), fiche d'une paroi et infobulles du dessin

Étapes 1 et 2 du plan « informations au clic sur une paroi ou un vitrage » (`ROADMAP.md`).

- **Paroi examinée** : liste sous le dessin, dans le même `st.fragment` (changer de paroi ne relance ni le calcul
  ni les graphiques) : les quatre façades, les baies de chaque façade vitrée, la toiture, le plancher bas. Aucune
  à l'ouverture ; une paroi disparue de la boîte (baies passées à 0 %, façade adiabatique) est oubliée.
  - **Dans le dessin** : contour orange épais ; en pointillé si la paroi est cachée dans la vue (façade de dos,
    plancher bas), ce que la fiche signale.
  - **Fiche** (`interface/fiche_paroi.py`, sans Streamlit) : surface, U et U × surface (hors ponts thermiques ;
    sans objet pour un plancher sur le sol), teinte, part vitrée, balcon ; pour des baies : gabarit d'une baie,
    Uw, Uw × surface, Sw, Tl, protection et sa gestion, Uw et Sw protégés, ouverture, masque proche ; une paroi
    adiabatique le dit, sans U.
- **Infobulles** : chaque mur, baie et toiture du dessin porte un `<title>` (nom, surface, U ou Uw, Sw, Tl), que
  le navigateur montre au survol. Le dessin est écrit dans la page en SVG par `st.markdown(unsafe_allow_html=True)`
  et non plus par `st.image` (une image ne transmet pas le survol) ni par `st.html`, dont DOMPurify (profil
  « html ») retire tout SVG.
- `interface/axonometrie.py` : `dessiner(…, surlignee, infobulles)`, `point_de_facade`, `contours_paroi`,
  `paroi_visible` ; `charte.COULEUR_SURLIGNAGE` ; aide `paroi_examinee` dans `interface/textes/aides.csv`.
- Feuille de route : « Diffusion » passe en 0.9.20.
- Vu dans Chrome (logement de 70 m², vue du sud-ouest : baies de la façade principale entourées, façade arrière
  en pointillé, fiches ; sept `<title>` dans la page). Tests : 378 réussis, 2 sautés.

## 0.9.16 — évolution (20/11/2026), soleil, orientation, parois adiabatiques, zoom

- **Dessin** (`interface/axonometrie.py`) :
  - course du soleil le 21 juin dessinée dans le ciel (un point toutes les deux heures légales), en plus de sa
    trace au bord du sol ;
  - soleil de 16 h en heure légale, à sa hauteur (environ 55° au sud-ouest). L'heure solaire vient de la
    longitude (2,5° E) et de l'équation du temps (− 1,7 min), avec 46,5° N comme avant. Un trait vertical relie
    le soleil au sol ;
  - ombre portée de la boîte au sol (enveloppe des coins bas et des coins hauts glissés au sol) ;
  - façades assombries selon le soleil de 16 h, et non plus selon leur rang à l'écran ;
  - flèche du nord sur le bord du sol ;
  - disque du sol plus large (0,95 diagonale au lieu de 0,7), pour que lever et coucher tombent sur son bord ;
  - **heure du soleil réglable** : curseur sous le dessin, de 6 à 20 h par pas de 2 h (16 h par défaut). Le
    soleil, l'ombre au sol et les façades à l'ombre suivent l'heure. Le curseur, le choix de la vue et le dessin
    sont dans un `st.fragment` : ils se redessinent seuls, sans relancer la page.
    - À 6 h pile, le soleil est encore 0,4° sous l'horizon (lever à 6 h 03 à 46,5° N). Il est dessiné à 2° de
      hauteur, sous l'étiquette « lever (6 h 15) » (`heure_dessinee`, `HAUTEUR_MIN_SOLEIL_DEG`).
    - L'ombre est coupée au bord du sol (`couper`, Sutherland-Hodgman). Sans cela, le soleil bas l'étire sur
      plus de 200 m et le cadrage change d'une heure à l'autre.
    - Un soleil placé derrière la boîte reçoit en plus un contour pointillé par-dessus elle, pour rester visible
      (vue du sud-ouest à 6 h). L'étiquette se place du côté du centre pour ne pas sortir du cadre.
- **Orientation par pas de 10°** : la saisie affiche l'azimut géographique (« 190° · sud » ; 0 = nord, 90 = est).
  Le moteur et les CSV gardent leur convention (0 = sud, 90 = ouest). Nouvelles fonctions `azimut_geographique`,
  `orientation_moteur` et `libelle_orientation` dans `interface/saisie.py`. Une orientation hors du pas, venue
  d'un CSV, est arrondie au pas dans le curseur.
- **Parois adiabatiques** (champ `parois_adiabatiques` de `Boite`, choix dans le volet « Forme », ligne ajoutée aux
  deux CSV de `donnees/batiments/`) : les quatre façades, la toiture et le plancher bas.
  - Une paroi cochée n'entre pas dans le groupe : ni échange, ni soleil, ni perméabilité.
  - Une façade cochée n'a pas de baie, et sa rive de plancher sort des ponts thermiques.
  - La toiture et le plancher bas gardent leur rive.
  - Dans le dessin, ces parois sont grises ; dans la saisie, les curseurs devenus sans effet sont désactivés.
  - Hypothèse 101 de `docs/audit.md`.
- **Couleurs des températures** (`interface/charte.py`) : extérieur en noir, seuil de confort en orange (en
  pointillé), intérieur en jaune ; dans les briques « DH » et « Semaine chaude ».
- **Brique DH** : graphique heure par heure sur la période de confort adaptatif, avec les degrés-heures comptés en
  orange, à la place des maximums du jour.
  - Trois boutons : « Été entier », « Semaine la plus chaude », « Jour le plus chaud ».
  - En dessous, les DH de chaque jour : un cadre tracé à la souris montre ces jours-là au-dessus (liaison par
    `on_select` de Streamlit), et la molette zoome.
  - Deux graphiques séparés : réunis dans un `alt.vconcat` de couches, ils s'élargissaient sans fin dans
    Streamlit 1.66.
- **Feuille de route** : plan de bataille « informations au clic sur une paroi ou un vitrage » (cinq étapes) ;
  « Diffusion » passe en 0.9.18.

Résultats : les bâtiments de départ n'ont pas changé (aucune paroi adiabatique ; même longueur de rives).
Logement de 70 m², enveloppe moyenne :

| Parois adiabatiques | DH (°C.h) | Bbio |
|---|---|---|
| aucune (départ) | 732 | 119,8 |
| deux pignons | 607 | 71,1 |
| deux pignons et toiture | 505 | 49,2 |
| deux pignons, toiture et plancher bas | 499 | 28,6 |

Tests : 375 réussis, 2 sautés (3 nouveaux : parois adiabatiques, orientation, soleil et ombre ; fenêtres du DH
dans le test de la semaine chaude). Vu dans Chrome : dessin vu du sud-ouest et du nord-est, parois grises, boutons et cadre
de zoom du DH.

## 0.9.15 — correction (20/11/2026), ouverture des baies comme le moteur réglementaire

Diagnostic heure par heure sur les sorties du moteur COMETH (Paris, Sète, Nice A) : le moteur ne suit pas le texte
de la fiche 5.13 pour le réglage des fenêtres par les occupants. Détail dans `docs/audit.md` (diagnostic du
20/11/2026 et 0.9.15, hypothèse 100).

- **Correction : profil d'ouverture des baies** (`moteur/ouvertures.py`, réglage `OUVERTURE_COMME_LE_MOTEUR`,
  False : texte). Seuil d'ouverture θouv2 = consigne − 1 °C, sans l'écart de confort adaptatif (Th-D compris) ;
  ouverture de θouv2 − 1 à θouv2 (texte : − 2) ; réglage à toutes les heures d'occupation, la nuit aussi (texte :
  de jour, position du soir gardée la nuit). Cette règle reproduit l'ouverture du moteur 92 à 99,9 % des heures
  (texte : 72 à 84 %).
- Constat sans correction : fermeture des protections et passage d'air à travers une protection fermée
  (fiche 5.12, éq. 239) sont déjà ceux du moteur.
- Nouvelle clé `ouv_moteur_ecart_ouv1` dans `donnees/hypotheses.csv` ; tests de `tests/test_protections.py` pour
  les deux règles.

Résultats

| | 0.9.13 | 0.9.15 |
|---|---|---|
| Ouverture face au moteur, Th-B / Th-D | + 5 à + 10 % / − 16 à − 32 % | − 4 à + 3 % / − 4 à − 16 % |
| Validation : groupes dans ± 10 % (46) | 29 | 30 |
| Bbio, écart médian ; froid outil / étude | − 1,5 % ; 0,78 | 0,0 % ; 0,94 |
| DH dans ± 10 % (37 groupes) ; écart absolu médian | 17 ; 11,1 % | 21 ; 8,0 % |
| Logement de 70 m², DH (performant / moyen / faible) | 559 / 728 / 883 | 544 / 732 / 884 |
| Immeuble de 9 logements, DH | 454 / 601 / 744 | 448 / 599 / 748 |

Le DH de Sète (− 33 à − 39 %) et de Nice A (+ 15 à + 27 %) ne bouge pas : la cause est dans le bilan du calcul Th-D.

## 0.9.13 — correction (20/11/2026), protections de la boîte d'après le guide Actibaie

Lecture du guide *Les protections solaires dans la RE 2020* (Actibaie, v8, 2024 ; hors dépôt). Détail, tableaux et
écarts dans `docs/audit.md`, 0.9.13 (hypothèse 99).

- **Correction : protection mobile de la boîte** (`interface/saisie.py`, `_conventions_protection` ; quatre clés
  `boite_…` dans `donnees/hypotheses.csv`). Un volet ou un store laisse passer 10 % de l'air une fois fermé
  (Typo_PM 1 au lieu de 0, étanche) ; le Sw protégé d'un volet est tout réémis (Sw2, Sw1 = 0), celui d'un store en
  toile à 40 %. Avant, les volets motorisés du logement de 70 m² augmentaient le DH (808 contre 790 sans
  protection). Les études lues (RSET) ne changent pas.
- **Test de tendance** (`tests/test_tendances.py`) : sur la boîte en H3, DH sans protection > gestion manuelle non
  motorisée > manuelle motorisée > automatique, comme le guide.
- Écarts au guide inscrits, non corrigés : effet des protections sur le DH trop faible (− 11 % contre environ
  − 50 %), effet de Typo_PM trop fort, Bbio non rangé comme le DH.
- `docs/audit.md` : hypothèse 49 marquée levée (les valeurs avec protection entrent dans le calcul depuis la 0.8.12).
- Feuille de route : « Types de protection » en 0.9.12, maison individuelle en 0.9.14, diffusion en 0.9.16.

Résultats (DH en °C.h ; Bbio à ± 0,4 point)

| Bâtiment de départ | Performant | Moyen | Faible |
|---|---|---|---|
| Logement de 70 m² | 639 → 559 | 804 → 728 | 969 → 883 |
| Immeuble de 9 logements | 524 → 454 | 685 → 601 | 848 → 744 |

## 0.9.11 — correction (19/11/2026), relecture indépendante de la 0.9.8

Remarques de la relecture `relecture_0.9.8.md` mesurées face au moteur COMETH (Paris, Sète, Nice A) et aux études,
puis appliquées. Détail et décisions dans `docs/audit.md`, 0.9.11 ; tables dans `_resultats/mesures_0.9.11/`.

- **Correction : écart de confort adaptatif nul en Th-B** (`moteur/besoins.py`, fiche 13.5 éq. 2546 et fiche 5.13
  éq. 242). L'outil relevait les seuils d'ouverture des baies de 0,33 θrm + 18,8 + 2 − θiifr : en été, les baies ne
  s'ouvraient presque plus. Le Bbio change (froid plus faible), pas le DH.
- **Correction : caractère traversant d'hiver pour les infiltrations** (fiche 5.6, tableau 22) : celui de la zone
  (`Is_Traversant`, `Groupe.traversant_hiver`) ; l'ouverture des baies garde le traversant d'été (hypothèse 95).
  Change 4 groupes (Vélizy cage B, Saint-Ouen).
- **Correction : store enroulable par grand vent** remonté seulement en occupation en gestion manuelle (fiche 5.9,
  éq. 192-193).
- **Correction de `outils/valider.py`** : le DH était joint par le seul nom du groupe ; Vélizy (noms répétés d'une
  zone à l'autre) comptait 18 lignes pour 6 groupes. Les « 58 groupes » des 0.9.9 et 0.9.10 sont 46.
- Lecture d'un RSET : perméabilité absente → 1 m³/(h.m²) (tableau 30) ; Httf hors de ]4 ; 15] m ramené à 1,5 m ou
  plafonné, signalé. `Groupe` refuse un Httf hors de ces bornes. Avertissement si la hauteur moyenne d'une zone
  traversante manque (infiltrations). EDn borné à 0.
- Gardés après mesure : facteur 1 de l'éq. 61 (hypothèse 94 ; 0,5 retarderait à tort le froid de Nice A, groupe 2),
  convention de l'heure légale (identique au moteur heure par heure), Sw2 par défaut (sans effet : les études
  donnent Sw2).
- Documentation : sources de `chaleur_volumique_air` (éq. 377 et 379) et de Cvent (fiche 3.2) ; éq. 403 dans
  `debit_ventilation` ; citations de la fiche 5.9 ; variable γ du polynôme EDn ; hypothèses 93 à 98 ; piste de la
  ventilation d'hiver (0,1397) close (éq. 382, indicateur de sortie) ; points mineurs dans `ROADMAP.md`.
- Coefficients EDn : déjà exacts depuis la 0.9.8, la remarque ne s'appliquait pas.

Résultats

| Face au moteur (6 groupes, Th-B) | 0.9.10 | 0.9.11 |
|---|---|---|
| Froid | + 25 à + 189 % | − 34 à − 2 % |
| Ouverture des baies | − 54 à − 20 % | + 5 à + 10 % |
| Fin de la saison de froid | jours 246 à 267 | 246 (Nice A 2 : 257 ; moteur 246 à 250) |
| Chauffage, DH | inchangés | |

| Validation | Dans ± 10 % | Écart médian du Bbio |
|---|---|---|
| H1a (4 groupes) | 4 → 4 | − 4 → − 5 % |
| H2a (6) | 3 → 3 | + 10 → + 9 % (chauffage + 17 %) |
| H3 (13) | 0 → 9 | + 23 → − 2 % (froid 1,73 → 0,97 fois l'étude) |
| 46 groupes de 16 études | 18 → 29 | + 16 → − 2 % |

- Écart principal restant : chauffage trop fort de certains groupes (entrées d'air) : Sète traversant + 47 à
  + 53 %, `rsee.xml` jusqu'à + 45 %, Vélizy et Saint-Ouen.
- Fiabilité affichée mise à jour (accueil, brique Bbio).

Vérification

- Tests : 371 réussis, 2 sautés. Nouveaux : seuils d'ouverture en Th-B indépendants de θrm, store manuel par grand vent
  hors occupation (`tests/test_protections.py`) ; équilibre à température uniforme avec baies
  (`tests/test_groupe.py`) ; traversant d'hiver, avertissement de hauteur, bornes de Httf
  (`tests/test_infiltrations.py`).

## 0.9.10 — évolution (19/11/2026), ouverture des baies et infiltrations

- **Protections mobiles devant une baie ouverte** (fiche 5.12, tableau 40, éq. 239) : la part fermée laisse passer
  0 à 75 % de l'air selon la typologie `Typo_Permea_PM`, lue dans les RSET (`Baie.typo_permeabilite_protection`).
  L'outil comptait 0 % : une baie protégée à 70 % ne pouvait plus s'ouvrir qu'à 30 %. Vérifié sur le moteur
  (Rouv_corrigé = 0,21 / (0,7 × 0,1 + 0,3) = 0,568, sa valeur).
- **Entrées d'air du projet gardées dans les infiltrations** (`Groupe.module_entrees_air_m3h`, éq. 141 : q = M ×
  (|ΔP| / 20 Pa)^0,5, altitude 0,92 × MIN(h ; 3)), comme le moteur (hypothèse 92, remplace la 67). Essai sur les
  6 groupes horaires : infiltrations d'hiver de 0,55 à 1,05 fois celles du moteur (total).
- `rouv_brut_moyen` (Rouv de l'éq. 240, comme `O_Rouv` du moteur) dans le résultat horaire et la comparaison.
- Feuille de route décalée : maison individuelle 0.9.12, diffusion 0.9.14.
- Fiabilité affichée mise à jour (accueil, briques Bbio et DH).

Résultats (détail dans `docs/audit.md`, 0.9.10)

| Face au moteur (6 groupes horaires) | 0.9.9 | 0.9.10 |
|---|---|---|
| Chauffage | − 2 à − 21 % | ± 6 % dans 4 groupes ; Sète 1 + 47 %, Nice A 1 + 15 % |
| Froid | + 47 à + 210 % | + 25 à + 189 % |
| Ouverture des baies, Th-B / Th-D | − 23 à − 64 % / − 31 à − 52 % | − 20 à − 54 % / − 16 à − 32 % |
| DH | − 41 à + 28 % | − 37 à + 30 % (Paris ± 6 %) |

| Validation, 23 groupes | Dans ± 10 % | Écart médian du Bbio |
|---|---|---|
| H1a | 2 → 4 | − 11 → − 4 % |
| H2a | 5 → 3 | − 7 → + 10 % (chauffage parfois trop fort, jusqu'à + 45 %) |
| H3 | 1 → 0 | + 17 → + 23 % (froid 1,7 fois l'étude ; Sète traversant + 50 %) |

- Sur les 58 groupes de 16 études : 18 dans ± 10 % (13 avant), écart médian + 22 % (+ 15 %).
- Les entrées d'air sont justes en moyenne, trop fortes dans certains groupes (zones traversantes de Sète,
  petit groupe de `rsee.xml`) : à reprendre.

Vérification

- Tests : 364 réussis, 2 sautés ; nouveaux : entrées d'air (`tests/test_infiltrations.py`), passage de l'air à
  travers une protection et Rouv brut (`tests/test_protections.py`).

## 0.9.9 — correction (19/11/2026), comparaison heure par heure à un moteur Th-BCE

- **Sorties horaires d'un moteur réglementaire** (COMETH 2025.E1) pour Paris, Sète et Nice A, hors dépôt dans
  `../_RSEE/Horaires` : modes Th-B, Th-C et Th-D, avec toutes les grandeurs de chaque groupe et de chaque baie.
  Chaque calcul a son RSET dans la validation (besoins et DH identiques) : le point en attente « RSET
  correspondant aux classeurs horaires » est levé.
- `outils/lire_horaires.py` : lecture des seules colonnes demandées (un fichier de groupe dépasse 260 Mo), avec un
  cache dans `_resultats/horaires_cache/` (hors dépôt).
- `outils/comparer_horaires.py` (`python -m outils.comparer_horaires paris|sete|nice|tous`) : refait le calcul
  avec l'outil et met 33 grandeurs face à celles du moteur, heure par heure. On y trouve la saison, les consignes,
  le renouvellement d'air, les flux solaires, les apports, les protections, les ouvertures, les températures, les
  besoins et le confort d'été. Tables par grandeur, par mois et heure par heure dans `_resultats/horaires/`.
- Moteur : le résultat horaire de `calculer_besoins` donne aussi les sollicitations de l'heure (`hg_ei`,
  `theta_eieq`, `fs1`, `fs3`, `phi_sl`, `phi_sh`, `phi_i`, `phi_s`, `phi_m`) et `occupe` dans les deux modes.
- **Correction : ouverture des baies en Th-B, l'outil suit le moteur et non le texte** (`moteur/ouvertures.py`,
  hypothèse 91). L'annexe (fiche 5.13, éq. 244) n'ouvre aucune baie hors période de refroidissement. Le moteur
  COMETH applique là la règle générale de la gestion manuelle, sans le plafond « consigne de froid − 1 °C »,
  qu'il réserve à la période de refroidissement ; rien ne s'ouvre hors occupation. Réglage
  `OUVERTURE_TH_B_COMME_LE_MOTEUR` (True ; False = texte de l'annexe). Le Bbio change (froid plus faible), pas
  le DH. Sur les 23 groupes de la 0.9.8 : H3 + 20 → + 17 % (médiane, étendue + 3 à + 22 %), H1a − 10 → − 11 %,
  H2a − 6 → − 7 % (5 groupes sur 6 dans ± 10 %, contre 6). Fiabilité affichée mise à jour (accueil, brique Bbio).

Constats (détail dans `docs/audit.md`, 0.9.9 ; aucun coefficient ajusté)

| Constat | Effet |
|---|---|
| Ouverture des baies en Th-B : l'outil n'ouvrait qu'en saison de froid, comme le dit l'annexe (éq. 244) ; le moteur ouvre aussi à la mi-saison (946 à 1 929 heures par an) | avant correction : mi-saison 0,4 à 1,1 °C trop chaude, saison de froid de 98 à 140 jours au lieu de 63 à 74, froid 1,8 à 3,6 fois trop fort ; après : saison de Paris identique au moteur, Sète et Nice 85 à 93 jours, froid 1,5 à 3,1 fois trop fort |
| Ratio d'ouverture des baies encore 23 à 64 % (Th-B) et 31 à 52 % (Th-D) sous celui du moteur | froid encore trop fort ; DH de − 41 à + 28 % |
| Infiltrations d'hiver 1,5 à 3,5 fois trop faibles (ventilation identique, à 1-2 % près) | chauffage 2 à 21 % trop faible |
| Flux des parois opaques (Φsh) 19 à 92 % trop faibles | ponts thermiques sans flux solaire ni voûte céleste |
| Apports des usages 7 % trop faibles, éclairement naturel 20 à 80 % trop fort | petits écarts de chauffage et d'éclairage |
| Th-D : même seuil de confort et même calcul du DH ; l'écart du DH vient de la température (baies moins ouvertes, 31 à 52 %) | DH de − 41 à + 28 % |

Vérification

- Tests : 362 réussis, 2 sautés. Nouveaux : `tests/test_horaires.py` (7), un test des sollicitations dans
  `tests/test_besoins.py`, un test de l'ouverture en Th-B hors saison de froid dans `tests/test_protections.py`
  (deux tests y suivent la nouvelle règle).
- Contrôle des 12 appariements (3 études × 2 groupes × 2 modes) : Bch du moteur = Bch du RSET, DH horaire du
  moteur = DH de ses résultats, température extérieure alignée sans décalage.

## 0.9.8 — évolution (18/11/2026), validation (en partie)

- **Validation par lot** (`outils/valider.py`) : tous les RSET et RSEE d'un ou plusieurs dossiers (par défaut
  `../_RSEE` et `_sources`) passent dans `outils/comparer_reference.py`. Doublons de contenu comptés une fois,
  fichiers sans logement collectif écartés et listés, une étude illisible n'arrête pas les autres. Table par
  groupe (besoins, Bbio, Bbio max, écarts, cible ± 10 %, DH avec `--dh`) écrite dans `_resultats/validation.csv`
  (hors dépôt), et résumé.
- **Parois à U = 0** lues comme adiabatiques (`moteur/enveloppe.py`, `moteur/solaire.py`, hypothèse 90) : l'étude
  `rsee.xml` (H2a, 6 groupes, 192 parois à U = 0) faisait planter le calcul (division par zéro).
- **Bouton « Télécharger ce bâtiment »** (menu de gauche ; `interface/saisie.py`, `ecrire_batiment`) : la saisie en
  CSV de bâtiment de départ (forme, site, baies, protections, balcons, confort d'été), relu à l'identique par
  `lire_batiment`. L'enveloppe n'y est pas : comme pour tout bâtiment de départ, elle vient du niveau choisi.
  Fichier proposé : `03_mon_batiment.csv`, avec BOM pour Excel.
- Fiabilité affichée (accueil, briques Bbio et DH) mise à jour avec les 23 groupes.

Résultats (détail dans `docs/audit.md`, 0.9.8)

| Zone | Groupes | Bbio dans ± 10 % | Écart du Bbio (médiane) | Cause principale |
|---|---|---|---|---|
| H1a | 4 | 2 | − 10 % | chauffage 11 à 20 % trop faible |
| H2a | 6 | 6 | − 6 % | froid faible ; chauffage 9 % trop faible |
| H3 | 13 | 1 | + 20 % | froid 1,2 à 3,8 fois trop fort |

- 10 études, 23 groupes, mais 5 bâtiments distincts : la cible « plus de 10 RSEE » et l'OPEE restent à faire.
- Aucun coefficient ajusté pour coller aux études. Écart de ventilation d'hiver (+ 22 % dans l'outil, les
  23 groupes) toujours inexpliqué.

Vérification

- Tests : 353 réussis, 2 sautés ; 3 nouveaux (paroi adiabatique, validation par lot, bâtiment écrit puis relu).
- Résultats des 17 groupes déjà lisibles : inchangés par la correction U = 0.

## 0.9.6 — évolution (18/11/2026), pédagogie

- **Page d'accueil** (`interface/accueil.py`, texte dans `interface/textes/accueil.md`), comme Météo et Chaleur :
  à quoi sert l'outil, comment s'en servir, trois notions (Bbio, DH, une boîte), limites et fiabilité, liens
  utiles. La page s'ouvre sur l'accueil, qui ne lance aucun calcul ; « Explorer la boîte » ou « Calculer » ouvre
  la page « Explorer ». Choix de page en tête (`app.py`, clé `page`).
- **Équations montrées** : dans chaque brique, l'équation et sa lecture passent du volet à la page, dans un cadre
  « L'équation », avec un paragraphe « Ce qu'elle dit » ; le volet garde la référence et le code du moteur
  (`interface/briques/base.py`, titre « Référence et code du moteur »).
- **Glossaire du confort dans le bâtiment** (Notion, site public `guillaume-meunier.notion.site`) : dans tout
  texte, `[[terme]]` ou `[[terme|texte montré]]` devient un lien vers la page du terme
  (`interface/aides.py`, `lier`) ; 82 termes dans `interface/textes/glossaire.csv` (terme ; identifiant de page).
  Liens dans l'accueil, les aides et les briques ; chaque brique finit par « Pour aller plus loin »
  (`Brique.glossaire`).
- **Aides hors du code** : la bulle « ? » de chaque saisie vient de `interface/textes/aides.csv` (clé du widget ;
  texte), lue par `aide(clé)`. Plus aucun `help="…"` dans `formulaire.py`, `app.py` ni les briques ; 20 aides
  nouvelles (altitude, forme, protections, parois, ventilation, brasseurs…), vérifiées sur le moteur. L'aide de la
  transmission lumineuse reprend le texte ajouté à la main avant la version.
- **Course solaire d'été** dans le sol du dessin (`interface/axonometrie.py`) : le bord du disque, du lever
  (nord-est) au coucher (nord-ouest) par le sud, au 21 juin et à 46,5° N (`direction_soleil`, `angle_coucher`,
  `bord_du_sol`), et le soleil de 16 h posé dans sa direction. Remplace l'arc schématique est-ouest. Tracée en
  hauteur, la vraie course se projetait presque en un trait vue du sud : elle est portée au sol.
- **Chiffres clés** : sous le Bbio et le DH, l'écart avec le calcul précédent (« -165 °C.h depuis le calcul
  précédent », « inchangé » à l'arrondi) ; la part du maximum passe sur une ligne en dessous, en rouge au-dessus du
  max, en vert en dessous. Un calcul est une boîte calculée : ajouter le Bbio au DH de la même boîte ne compte pas.
- Tests : `donnees/typologies_logements.csv`, arrondi dans le commit de la 0.9.4 (Uw 1,2 / 1,3 / 1,4, Sw moyen
  0,40, U mur performant 0,25), faisait échouer deux tests restés sur les anciennes valeurs : valeurs attendues
  alignées sur le CSV.

Vérification

- Tests : 350 réussis, 2 sautés ; 2 nouveaux (course du soleil d'été ; aides, glossaire et liens), page entière
  étendue (ouverture sur l'accueil, retour à l'accueil puis « Calculer », écart avec le calcul précédent).
- Vu dans Chrome : accueil (titres, notions, liens), page « Explorer », course au sol (lever NE, coucher NO,
  soleil de 16 h à l'ouest), brique DH avec son équation et ses liens, bulle d'aide avec lien, passage à
  « Performant » puis calcul : DH 804 → 639 °C.h, « -165 °C.h depuis le calcul précédent ». Page Notion « DH »
  ouverte par son lien public.

## 0.9.4 — évolution (15/11/2026), bâtiments de départ en CSV

« Pédagogie » passe en 0.9.6 ; « Diffusion » (module de la chaleur), qui occupait ce numéro, passe en 0.9.12,
après la maison individuelle, pour ne pas renuméroter la validation (0.9.8) ni la maison individuelle (0.9.10).

- **Bâtiments de départ lus dans des CSV** (`donnees/batiments/`, `interface/saisie.py`, `lire_batiment`,
  `lire_batiments`) : un fichier par bâtiment, colonnes `champ;valeur;unite;description`, ligne `nom` obligatoire.
  Les fichiers sont lus au lancement par ordre alphabétique ; le premier est celui de la page à son ouverture.
  Un champ absent prend la valeur par défaut de `Boite`. Refusés avec le fichier et la ligne : les 13 saisies
  d'enveloppe (données par le niveau), un champ inconnu ou écrit deux fois, une valeur illisible, une zone
  climatique inconnue, une boîte que `construire_projet` refuse, deux bâtiments de même nom. Deux fichiers
  fournis, complets, qui servent de modèle : `01_logement_70m2.csv`, `02_immeuble_9_logements.csv` ; mode
  d'emploi dans `donnees/batiments/README.md`.
- **Nouveau logement de 70 m²** (valeurs par défaut de `Boite`) : zone H1a (H3 avant), façade principale 7 m et
  profondeur 10 m (10 × 7 avant), baies 25 % devant et derrière, pignons aveugles (30 / 10 / 20 / 10 % avant),
  protections à gestion manuelle motorisée (manuelle avant). L'immeuble prend les mêmes valeurs et ne garde à
  lui que sa forme.
- `config/reglages.py` : `DOSSIER_BATIMENTS`. Aide du menu « Bâtiment de départ » : le dossier des CSV.

Vérification

| Bâtiment | Niveau | Bbio (max) | DH °C.h (max 1 250) |
|---|---|---|---|
| Logement de 70 m² | Performant | 90,7 (91,0) | 609 |
| Logement de 70 m² | Moyen | 114,8 (91,0) | 786 |
| Logement de 70 m² | Faible | 135,5 (91,0) | 991 |
| Immeuble de 9 logements | Performant | 48,7 (82,8) | 511 |
| Immeuble de 9 logements | Moyen | 58,2 (82,8) | 675 |
| Immeuble de 9 logements | Faible | 65,8 (82,8) | 859 |

- `Boite()` : Bbio 121,2 (max 91,0), DH 1 062 °C.h.
- Tests : 348 réussis, 2 sautés ; 1 nouveau (lecture des CSV et refus). Les tests de géométrie emploient
  `QUATRE_FACADES`, l'immeuble vitré comme en 0.9.0.
- Vu dans Chrome : ouverture sur le logement 7 × 10 m (pignon A à 0 %, façade principale à 25 %, DH 786) ;
  passage à l'immeuble, curseurs à jour.

## 0.9.2 — évolution (15/11/2026), niveaux d'enveloppe

« Pédagogie » passe en 0.9.4 (numéro libre depuis la révision de l'ordre des versions).

- **Trois niveaux d'enveloppe** (`interface/saisie.py`, `NIVEAUX_ENVELOPPE`, `boite_de_depart`) : « Performant »,
  « Moyen » (à l'ouverture) et « Faible », lus dans `donnees/typologies_logements.csv`. Ce sont les repères P25,
  P50 et P75, pondérés par la surface habitable, de 18 zones de logements de 6 études RE2020. Ils fixent 13
  saisies : Uw, Sw, TL, Sw et Uw protection baissée, part ouvrante, U des murs, de la toiture et du plancher bas,
  ponts thermiques, inertie, ventilation, perméabilité. Le ψ moyen de tous les ponts est appliqué aux rives des
  planchers (hypothèse 88 de `docs/audit.md`).
- **Menu de gauche** (`interface/formulaire.py`, `choisir_depart`) : choix « Enveloppe » sous « Bâtiment de
  départ ». Changer de niveau ne réécrit que les 13 saisies d'enveloppe et garde la forme ; changer de bâtiment
  remet tout à ses valeurs, avec l'enveloppe du niveau choisi.
- **Pas des curseurs** affinés pour accueillir les valeurs des niveaux : Uw et Uw protégé 0,05 ; Sw, TL, U du
  plancher bas, ψ 0,01 ; part ouvrante 1 %. La comparaison écrit Uw avec deux décimales.
- **Scripts** `outils/typologies/` (calcul du CSV, graphique pédagogique `docs/graphique_pedagogique_logements.png`,
  boîtes à moustaches, valeurs par groupe de quelques RSET avec `valeurs_3_rset.py`) et leur `README.md`. Leur
  source, tirée des RSEE, reste hors du dépôt.
- `config/reglages.py` : `CHEMIN_TYPOLOGIES`.

Vérification

| Bâtiment | Niveau | Bbio (max) | DH °C.h (max 1 250) |
|---|---|---|---|
| Logement de 70 m² | Performant | 78,5 (78,0) | 858 |
| Logement de 70 m² | Moyen | 99,1 (78,0) | 1 308 |
| Logement de 70 m² | Faible | 116,3 (78,0) | 1 756 |
| Immeuble de 9 logements | Performant | 46,6 (69,8) | 746 |
| Immeuble de 9 logements | Moyen | 54,9 (69,8) | 1 125 |
| Immeuble de 9 logements | Faible | 63,1 (69,8) | 1 541 |

- `Boite()` (valeurs de la 0.9.1) inchangée : Bbio 114,7, DH 1 964 °C.h.
- Tests : 1 nouveau (niveaux d'enveloppe) ; page entière étendue (niveau à l'ouverture, changement de niveau
  après une forme modifiée, changement de bâtiment avec le niveau gardé).

## 0.9.1 — évolution (15/11/2026), choix du calcul et bâtiment de départ

Numéro impair pour une évolution, à la demande : 0.9.2 reste réservé à « Pédagogie ».

- **Choix du calcul** (`interface/formulaire.py`, `interface/calcul.py`, `app.py`) : « DH » (par défaut),
  « Bbio » ou « Bbio et DH », en haut du menu de gauche, au-dessus du bouton « Calculer ». Seul le calcul demandé
  est lancé. Le Bbio et le DH sont gardés en mémoire séparément : passer du DH seul aux deux ne lance que le
  Bbio. `calculer()` devient `resultats_bbio()` et `resultats_dh()`, et les champs de `Resultats` d'un calcul
  non lancé valent `None`.
- **Briques et comparaison selon le calcul** : chaque brique déclare le calcul dont elle lit les résultats
  (`Brique.besoin`). La page ne montre que les chiffres clés, les briques et les lignes de comparaison des calculs
  lancés.
- **Bâtiment de départ** (`interface/saisie.py`, `BATIMENTS_DE_DEPART`) : « Logement de 70 m² » (par défaut ;
  10 m × 7 m, un niveau, un logement, 100 % habitable) ou « Immeuble de 9 logements » (la boîte de la 0.9.0).
  Choisir un bâtiment donne à chaque saisie la valeur de ce bâtiment (`valeurs_des_widgets`). Le logement est un
  petit bâtiment isolé, calculé comme du logement collectif (hypothèse 87 de `docs/audit.md`).
- Chiffre clé du Bbio : l'unité passe dans le libellé (« Bbio (points) »), sans quoi « 114,7 points » était coupé.

Vérification

- Immeuble de 9 logements : Bbio 62,3 et DH 1 777 °C.h, comme en 0.9.0.
- Logement de 70 m² : Bbio 114,7 pour un maximum de 78,0 ; DH 1 964 °C.h pour 1 250.
- Temps de calcul (poste peu chargé) : Bbio et DH 4,0 s avant ; Bbio seul 1,8 à 2,0 s, DH seul 1,9 à 2,0 s.
- Page vue dans Chrome : DH seul, Bbio seul, les deux ; aller-retour entre les deux bâtiments après une saisie
  modifiée à la main.
- Tests : 1 nouveau (bâtiments de départ) ; page entière, écarts et briques étendus. Suite complète : 346 réussis,
  2 sautés.

## 0.9.0 — évolution (15/11/2026), outil fonctionnel

L'outil s'emploie de bout en bout : décrire une boîte, la calculer, comprendre le résultat, comparer deux
variantes. La page a été vue dans un navigateur et corrigée. **Non mis en ligne** : la mise en ligne attend un
accord explicite et le lien Streamlit.

- **Comparaison de deux variantes** (`interface/comparaison.py`, `app.py`) : « Garder comme référence » retient
  le calcul affiché ; après une nouvelle saisie et un nouveau calcul, un cadre montre ce qui a changé dans la
  saisie et l'écart sur sept indicateurs (Bbio, chauffage, refroidissement, éclairage, DH, heures d'inconfort,
  température la plus haute). « Oublier la référence » referme le cadre.
- **Balcons et casquettes** (`interface/saisie.py`, `interface/formulaire.py`) : profondeur du débord et façades
  équipées, dans le volet « Baies ». Le moteur reçoit un masque proche horizontal au-dessus des baies (fiche 3.2,
  éq. 20 et 21) ; l'axonométrie dessine une dalle par niveau. Le gabarit d'une baie (hauteur, allège, linteau)
  est désormais commun au dessin et au calcul (`gabarit_baie`).
- **Corrections après contrôle visuel** : barre annuelle du Bbio et graphique des protections de la semaine
  chaude, écrasés (la hauteur donnée à Streamlit comprend la légende et les axes) ; étiquettes des façades
  couchées le long de leur pied, sans chevaucher les baies ; second bouton « Calculer » près de l'avertissement
  « la saisie a changé ».
- **Temps de calcul** (`moteur/infiltrations.py`) : la pression d'équilibre des infiltrations est cherchée par
  fausse position bornée au lieu d'une dichotomie seule (12 au lieu de 62 évaluations du bilan par heure). Boîte de
  départ, poste chargé : 25 s → 15 s. Même équation, mêmes résultats.
- **Documentation** : `README.md` (les quatre gestes de la page, une capture, la mise en ligne), `docs/audit.md`
  (constats du contrôle visuel, hypothèses 85 et 86).

Vérification

- Boîte de départ : Bbio 62,3 points et DH 1 777 °C.h, égaux à 12 chiffres à ceux de la 0.8.18.
- Bilan aéraulique nul à la pression trouvée, sur 14 cas (écart < 1e-9 kg/s).
- Balcons de 1,2 m au sud : froid 15,6 → 12,3 kWh/m², chauffage 11,6 → 12,5, DH 1 777 → 1 477 °C.h.
- Page vue dans Chrome (1 440 × 900) : trois briques, balcon, comparaison ; capture `docs/capture_interface.jpg`.
- Tests : 18 nouveaux (balcons, dessin, comparaison, bilan aéraulique ; page entière étendue). Suite complète :
  345 réussis, 2 sautés.

## 0.8.18 — évolution (14/11/2026), interface

Première interface (Streamlit), volontairement simple et construite par briques. Le moteur ne change pas.

```powershell
streamlit run app.py
```

- **Saisie d'une boîte** (`interface/saisie.py`) : longueur, profondeur, niveaux, orientation, part vitrée de
  chacune des quatre façades, baies (Uw, Sw, transmission lumineuse, protection mobile et sa gestion, ouverture),
  parois (U, teinte, plancher sur le sol ou sur l'extérieur, ponts thermiques des planchers, inertie), air
  (ventilation, perméabilité), confort d'été (climatisation, brasseurs d'air), site (zone climatique, altitude,
  bruit). `construire_projet(boite)` en fait un projet du moteur d'un seul groupe. Sans Streamlit : se teste seul.
- **Axonométrie** (`interface/axonometrie.py`) : la boîte dessinée en SVG, à l'échelle, tournée selon son
  orientation sur un sol aux points cardinaux fixes ; baies de la surface saisie, protection mobile, course du
  soleil ; quatre points de vue. Le dessin suit la saisie sans attendre le calcul.
- **Calcul au bouton** (`interface/calcul.py`, `app.py`) : le Bbio et le DH prennent 3 à 8 s ; ils partent au
  bouton « Calculer » et restent en mémoire pour les 24 dernières saisies. Tant que le calcul n'est pas relancé,
  la page signale que les résultats sont ceux de la saisie précédente.
- **Briques pédagogiques** (`interface/briques/`) : chaque brique explique un phénomène sur deux niveaux — le
  phénomène, un graphique et des ordres de grandeur par défaut ; l'équation, sa référence et le code du moteur
  (lu à la source) dans un volet. Trois briques : « Bbio : les trois besoins » (besoins pondérés face au Bbio
  max, répartition par mois), « DH : l'inconfort d'été » (maximums du jour dehors et dedans face au seuil,
  degrés-heures par jour), « Une semaine chaude » (heure par heure : températures, seuil, degrés-heures comptés,
  protections baissées et fenêtres ouvertes). Ajouter une brique : un fichier et une ligne dans
  `interface/briques/__init__.py`.
- **Formulaire** (`interface/formulaire.py`) : un volet par thème dans le menu de gauche ; les valeurs de départ
  sont celles de `Boite()`.
- **Charte** : palette du HUB (`interface/charte.py`, `.streamlit/config.toml`), une couleur par rôle.
- **Hypothèses** : absorption solaire par teinte (claire 0,4, moyenne 0,6, sombre 0,8, noire 1,0 ; règles
  Th-Bât, tableau 66) dans `donnees/hypotheses.csv`.
- **Dépendance** : `streamlit>=1.57` (Altair vient avec).

Vérification

- Boîte de départ (H3, 20 m × 12 m, 3 niveaux, façade principale au sud) : Bbio 62,3 points pour un maximum de
  69,8 ; DH 1 777 °C.h pour un maximum de 1 250.
- Page conduite sans navigateur (API d'agent de Streamlit) : les trois briques, une saisie modifiée, le bouton
  « Calculer », l'avertissement d'un bâtiment sans protection ; aucune erreur ni avertissement dans la console.
- Tests : 19 nouveaux (`tests/test_interface.py`) : surfaces et orientations de la boîte, saisies refusées,
  projection, baies dessinées à l'échelle, SVG valide dans les quatre vues, briques complètes, moteur indépendant
  de l'interface, page entière (`AppTest`). Suite complète : 327 réussis, 2 sautés.
- **Non fait** : contrôle visuel dans un navigateur (dessin, graphiques, mise en page) et capture d'écran ; le
  serveur d'essai a été arrêté par le poste, faute de mémoire.

## 0.8.17 — correction (14/11/2026), relecture de la 0.8.16

Relecture du dépôt après la 0.8.16 : documentation, clarté du code, doublons. **Aucun résultat ne change** : le
Bbio et le DH des dix groupes des cinq études sont identiques avant et après, à l'unité près du dernier chiffre.

Documentation

- **`README.md`** : un premier calcul en Python (un projet d'un groupe, son Bbio et son DH), la table des modules
  du moteur, le DH max dans les sources et un renvoi aux hypothèses de l'outil.
- **En-têtes périmés** de `moteur/bbio.py`, `moteur/solaire.py` et `moteur/groupe.py` remis au présent (ils
  annonçaient encore les protections mobiles et le calcul des besoins comme à venir).

Usage

- **Avertissement du DH** : `calculer_dh` ajoute une colonne `avertissement` qui signale un groupe sans protection
  mobile ou sans baie ouvrable (`moteur.dh.avertissements_confort`). Sans elles, la température de l'année
  caniculaire dépasse 40 °C et le DH n'a plus de sens ; rien ne le disait.
- **Comparaison du DH à une étude** (`outils.comparer_reference.comparer_dh`) : les groupes sont appariés par
  leur nom et non plus par leur rang dans le fichier ; un groupe inconnu de l'étude garde des colonnes vides.
- **Contrôle du projet** : `moteur.bbio.controler_projet` devient public (le DH s'en sert aussi) ; son message
  cite le DH max.

Code

- **Moyenne glissante extérieure** nommée `theta_rm_ext` partout (`moteur/confort.py`, `moteur/besoins.py`) :
  `theta_rm` reste la température radiante moyenne du groupe.
- **`calculer_besoins` allégé** : la préparation du confort adaptatif (`preparer_confort`, classe `ConfortAnnee`)
  et le pas des brasseurs d'air (`brasseurs_de_l_heure`) sont sortis de la boucle horaire.
- **Doublons supprimés** : une seule fonction `est_jour` (`moteur/confort.py`, reprise par les brasseurs) ;
  `KELVIN` et `SECONDES_PAR_HEURE` dans `config/reglages.py`, avec `HEURES_PAR_JOUR` qui y était déjà ;
  `FLUX_DU_BILAN` défini dans `moteur/groupe.py` au lieu de cinq fichiers de tests ; un seul repère pour le jeu
  météo du DH (`JEUX_DES_MODES`).
- **Lignes de plus de 120 caractères** coupées dans le code et les tests (une vingtaine).
- **Modèle du groupe, calcul d'une heure en deux temps** (`moteur/groupe.py`) : `preparer_pas` fait une fois ce
  qui ne dépend pas de la puissance émise par le système, `resoudre_pas` donne les températures pour une
  puissance, `temperatures_sonde` les deux seules que lit l'émetteur. Le calcul des besoins ne refait plus le
  travail commun pour ses trois ou quatre cas par heure ; `pas_groupe` reste disponible et enchaîne les deux.
  Mêmes opérations dans le même ordre : résultats identiques au dernier chiffre.
- **Gain mesuré** (temps processeur) : 10 à 15 % sur un groupe simple (Bbio de 1,0 à 0,9 s, DH de 1,7 à 1,4 s) ;
  rien de mesurable sur une étude de 800 composants, où le modèle du groupe ne pesait que 4 % du temps.

Vérification

- Bbio et DH des cinq études recalculés avec le code de la 0.8.16 puis avec celui-ci : besoins, Bbio, Bbio max,
  DH, heures d'inconfort, DH max et sommes de toutes les colonnes horaires identiques (écart nul).
- Tests : 310 (deux nouveaux : avertissements du DH, préparation puis résolution d'une heure ; l'appariement par
  nom est ajouté à un test existant).
- Reste à faire, noté dans `ROADMAP.md` : sur une étude, le temps part pour un tiers dans l'équilibre de pression
  des infiltrations et pour près d'un tiers dans le rayonnement reçu par chaque paroi, calculé plusieurs fois.

## 0.8.16 — évolution (14/11/2026), DH

Degrés-heures d'inconfort d'été (DH) sur l'année caniculaire, et comparaison au DH max.

- **Confort adaptatif** (`moteur/confort.py`, annexe III, fiches 3.1 et 13.5) : moyenne glissante de la
  température extérieure, période de confort adaptatif (du premier au dernier jour où cette moyenne atteint
  16 °C) et température limite de confort chaud (26 °C la nuit, 26 à 28 °C le jour).
- **Calcul Th-D** : `calculer_besoins(mode="th_d")` déroule le groupe sur le jeu météo Th-D, sans
  refroidissement, avec les inerties séquentielle et annuelle. En période de confort adaptatif, le chauffage est
  interdit et le groupe est en saison de refroidissement (fiche 4.6).
- **DH** (`moteur/dh.py`, fiche 13.5) : somme des dépassements du seuil de confort par la température opérative,
  en occupation et en période de confort adaptatif ; trois compteurs d'heures d'inconfort ; `calculer_dh(projet)`
  donne le DH de chaque groupe.
- **DH max** du logement collectif (annexe à l'article R. 172-4) : 1 250 °C.h en catégorie 1, valeurs selon la
  surface moyenne des logements pour les parties climatisées en H2d et H3 et pour la catégorie 2.
- **Protections mobiles en Th-D** (fiche 5.9, tableau 34) : après une journée à plus de 26,5 °C, fermeture de
  jour portée à 70 ou 80 %, volets limités à 70 % la nuit, stores enroulables à 50 %.
- **Ouverture des baies en Th-D** (fiche 5.13) : règle générale, sans condition de saison de refroidissement ni
  plafond lié à la consigne.
- **Brasseurs d'air** : branchés dans le calcul Th-D (régime piloté heure par heure, chaleur dégagée dans le
  groupe, seuil de confort relevé). Ils lisent désormais l'heure légale de début de pas : le jour va du pas de
  7h-8h au pas de 22h-23h (une heure plus tard qu'avant). `COLONNES_ENTREES` et `COLONNES_BRASSEURS` portent
  `hleg` au lieu de `case`.
- **Lecture des études** : brasseurs d'air lus dans les RSET ; `python -m outils.comparer_reference … --dh`
  compare le DH, le DH max, les heures d'inconfort et la période de confort adaptatif à ceux de l'étude.
- **Vérifié sur les sorties horaires d'un moteur Th-BCE** : moyenne glissante, période, seuil et DH identiques
  (écart inférieur à 1e-6 °C.h) quand on part de la température opérative du moteur.
- **Résultat** sur dix groupes de cinq études : période de confort adaptatif et DH max identiques ; DH de − 2 à
  + 28 % à Paris et à Nice, 35 à 41 % trop bas à Sète. Détail dans `docs/audit.md`.
- **Hypothèses de l'outil** : ventilation du calcul Th-D sans échangeur ; catégorie 2 du DH max pour un groupe
  climatisé exposé au bruit (BR2 ou BR3). 18 constantes ajoutées, chacune sourcée.
- Le mode Th-B est inchangé : mêmes besoins et même Bbio qu'en 0.8.14.
- Tests : 308. Le DH d'une étude de 800 composants se calcule en 10 à 45 s.

## 0.8.14 — évolution (14/11/2026), infiltrations

Air entrant par les défauts d'étanchéité de l'enveloppe.

- **Infiltrations** (`moteur/infiltrations.py`, annexe III, fiche 5.6) : à partir de la perméabilité à l'air du
  groupe (débit de fuite sous 4 Pa par m² de paroi), défauts répartis par convention au vent, sous le vent et en
  toiture ; chaque heure, la pression intérieure qui équilibre les débits entrants et sortants est cherchée par
  dichotomie, sous l'effet du vent, du tirage thermique et de la ventilation double flux du Bbio. L'air qui entre
  est à la température extérieure et ne passe pas par l'échangeur.
- **Besoins** : les infiltrations s'ajoutent à la ventilation dès que la perméabilité du groupe est renseignée ;
  sinon rien ne change. Nouvelles sorties horaires : `debit_infiltrations_m3h`, `hg_infiltrations`.
- **Vent corrigé** : la vitesse du vent du fichier météo est multipliée par 0,9 (fiche 3.1), pour les
  infiltrations comme pour les protections mobiles et l'ouverture des baies de la 0.8.12.
- **Structures** : `Groupe.permeabilite_q4pa` ; `Zone.hauteur_m` et `Zone.hauteur_moyenne_m`.
- **Lecture des études** : perméabilité et hauteurs de zone lues dans les RSET ; la comparaison donne la moyenne de
  janvier et février des infiltrations de l'outil, à côté de l'indicateur des études ; les variantes retirent
  aussi les infiltrations.
- **Résultat** sur les cinq études : le chauffage, 12 à 55 % sous les études en 0.8.12, n'en est plus qu'à 2 à
  26 %. Détail dans `docs/audit.md`.
- **Point ouvert** : l'indicateur d'infiltrations d'hiver des études vaut 3 à 6 fois celui de l'outil ; les entrées
  d'air du projet, que l'outil ne compte pas en Bbio, n'en expliquent qu'une partie.
- **Hypothèses** : 13 constantes ajoutées, chacune sourcée.
- Tests : 287. Une étude de 800 composants se calcule en 20 s environ (13 s en 0.8.12).

## 0.8.12 — évolution (14/11/2026), protections et ouvertures

Protections mobiles des baies et ouverture des baies pour la surventilation naturelle.

- **Protections mobiles** (`moteur/protections.py`, annexe III, fiches 5.9 et 5.10) : ratio de fermeture
  conventionnel de chaque baie, heure par heure, pour les volets et les stores enroulables, en gestion manuelle
  (motorisée ou non) et automatique avec dérogation. Il dépend de la saison du groupe, de l'occupation, de
  l'éclairement reçu par la baie et de la température de la veille. La baie est partagée entre une part nue et une
  part protégée : flux solaires, rayonnement froid et déperdition suivent ce ratio.
- **Matrices conventionnelles** de l'habitation (figures 35, 38 et 44 de la fiche 5.9) dans
  `donnees/protections_mobiles_manuelles.csv` et `donnees/protections_mobiles_automatiques.csv`.
- **Ouverture des baies** (`moteur/ouvertures.py`, fiche 5.13) : gestion manuelle du mode Th-B (ouverture en
  saison de refroidissement et en occupation, selon les températures intérieure et extérieure, le bruit et l'heure),
  puis débit d'air par tirage thermique ou par le vent, traversant ou non. L'air entre sans passer par l'échangeur.
- **Besoins** (`moteur/besoins.py`) : les deux modules s'appliquent dès qu'une baie porte une protection ou est
  ouvrable ; sans cela les résultats sont inchangés. Nouvelles sorties horaires : `rprot_moyen`, `hg_es`,
  `rouv_moyen`, `debit_ouvertures_m3h`.
- **Structures** : `Baie` reçoit la protection mobile, sa gestion et ses caractéristiques protégées (`uw_protege`,
  `sw_protege`, `tl_protege`…), `ouvrable`, `ratio_ouverture_max`, `exposition_bruit` ; `Groupe` reçoit
  `hauteur_tirage_m`.
- **Lecture des études** : protections, gestion et ouverture des baies lues dans les RSET ; les variantes de
  `outils/comparer_reference.py` retirent maintenant un module à la fois.
- **Résultat** sur les cinq études : le besoin de froid passe de 4 à 46 fois celui des études à 1,7 à 4 fois ; à
  Paris, seule étude à gestion entièrement manuelle, 1,6 et 0,6 kWh/m² contre 0,4 et 0,3. Détail dans
  `docs/audit.md`.
- **Limites** : les trois seuils de la gestion automatique des protections ne sont ni dans l'annexe ni dans les
  fichiers d'étude (valeurs de l'outil, signalées) ; stores vénitiens, seconde protection et ouverture automatique
  non traités ; l'éclairage est calculé baies nues ; pas d'infiltrations (0.8.14).
- **Hypothèses** : 33 constantes ajoutées, chacune sourcée.
- Tests : 277.

## 0.8.10 — évolution (14/11/2026), cas de référence

Lecture d'une étude réglementaire et comparaison de son Bbio à celui de l'outil.

- **Lecteur de RSET** (`outils/lire_rset.py`) : `lire_rset(chemin)` transforme le fichier XML d'une étude RE2020
  (Climawin, Pleiades : même format du moteur) en `Projet` de l'outil : groupes, parois opaques, baies sans
  protection, ponts thermiques, espaces tampons, masques proches et lointains, inertie, débit du Bbio. Il rend aussi
  une `Reference` : résultats de l'étude par groupe, zone et bâtiment (annuels et mensuels), indicateurs de
  déperdition, confort d'été, et description des baies avec leurs protections et leurs réglages d'ouverture. Ce que
  l'outil ne reprend pas encore est compté.
- **Comparaison** (`outils/comparer_reference.py`) : enveloppe (contrôle de la lecture), besoins annuels et
  mensuels, Bbio et Bbio max, côte à côte ; six variantes grossières (infiltrations de l'étude, protections fermées,
  sans échangeur, surventilation) pour mesurer ce qui manque. En ligne de commande :
  `python -m outils.comparer_reference "_sources\mon_etude.xml" --variantes`.
- **Bbio max** : la hauteur sous plafond moyenne est celle de tous les logements collectifs du bâtiment, pondérée
  par la surface (`hauteur_sous_plafond_moyenne()`), comme dans les études ; en 0.8.8 chaque zone gardait la sienne.
- **Constat** sur cinq études (Paris, Sète, Nice ; dix groupes) : parois opaques, surfaces et Bbio max retrouvés à
  l'arrondi, éclairage à 0,1 kWh/m² ; chauffage sous-estimé de 6 à 46 % (pas d'infiltrations) ; froid 4 à 46 fois
  trop fort (ni protections mobiles, ni ouverture des baies). Détail et variantes dans `docs/audit.md`.
- **Feuille de route** : « Cas de référence » intercalé ; protections et ouvertures en 0.8.12, infiltrations en
  0.8.14, DH en 0.8.16, interface en 0.8.18.
- Aucune étude réelle n'entre dans le dépôt : les tests fabriquent leur propre RSET ; un test supplémentaire
  contrôle les études présentes dans `_sources/`, et il est sauté ailleurs.
- Tests : 255.

## 0.8.8 — évolution (14/11/2026), Bbio

Bbio d'un projet, par groupe, par zone et par bâtiment, et comparaison au Bbio max.

- **Bbio** (`moteur/bbio.py`, annexe III, fiche 13.1) : `calculer_bbio(projet)` déroule les besoins de chaque
  groupe, puis donne Bch, Bfr, Becl et Bbio = 2 × Bch + 2 × Bfr + 5 × Becl par groupe, par zone et par bâtiment
  (pondération par la surface de référence), par mois et par an ; les résultats horaires sont conservés.
- **Bbio max** (annexe à l'article R. 172-4, version du décret n° 2026-200) : 65 points en logement collectif,
  modulés par la zone climatique et l'altitude (Mbgéo), la surface moyenne des logements (Mbsurf_moy), la surface
  du bâtiment (Mbsurf_tot), l'exposition au bruit (Mbbruit) et la hauteur sous plafond (MbHSP). Écart au Bbio max
  donné à titre indicatif.
- **Structures** : `Groupe.exposition_bruit` (BR1, BR2, BR3), `Zone.hauteur_sous_plafond_m`, `Zone.nb_logements`.
  La surface du groupe est sa surface habitable.
- **Heure légale des tests** : le calendrier donne `hleg`, heure légale de début de pas (Hleg = IHJ + EHLO) ; les
  saisons sont réévaluées à hlég = 9 (une heure plus tard qu'en 0.8.6). Effet sur l'immeuble d'essai : Bch à
  ± 0,06 kWh/m².
- **Revue des quatre points de l'audit** (hypothèses 29, 30, 31 et 36), à partir des textes, de sorties horaires
  d'un moteur Th-BCE et d'études réglementaires gardées hors du dépôt : besoin de froid compté d'office et surface
  de référence confirmés, relances sans objet en Bbio, fenêtres des saisons relues sans changement. Détail dans
  `docs/audit.md`.
- **Hypothèses** : 51 constantes ajoutées, chacune sourcée (fiche 13.1, annexe à l'article R. 172-4).
- **Limite** : le besoin de froid reste très surestimé sans protections mobiles ni ouverture des baies ; le Bbio
  de cette version n'est pas encore comparable à celui d'une étude (voir `docs/audit.md`).
- Tests : 245 (formule, modulations calculées à la main, pondérations par zone et par bâtiment, projets refusés).

## 0.8.6 — évolution (13/11/2026), besoins

Besoins de chauffage, de refroidissement et d'éclairage d'un groupe, heure par heure (mode Th-B, climat Th-BC).

- **Besoins** (`moteur/besoins.py`) : émetteur conventionnel du Bbio (annexe III, fiche 8.1 : moitié convectif,
  moitié radiatif, sonde à mi-chemin de l'air et du rayonnement, puissance illimitée), « droite du groupe » tirée de
  la matrice du groupe, consignes des scénarios (19 / 16 °C et 26 / 30 °C). `calculer_besoins()` déroule l'année ;
  `bilan_besoins()` donne Bch, Bfr et Becl par mois et par an, en kWh/m² (fiche 13.1).
- **Saisons** (fiche 4.6) : autorisations de chauffage et de refroidissement propres au groupe, réévaluées chaque
  jour à 9 h légales, à partir des degrés-heures d'inconfort (fiche 4.5) et des besoins moyens des 4 dernières
  semaines.
- **Apports internes** (`moteur/apports.py`, fiche 4.1) : adultes équivalents selon la surface moyenne des logements,
  occupants et usages tirés des scénarios, moitié convectifs, moitié radiatifs.
- **Éclairage** (`moteur/eclairage.py`, fiches 5.10 et 7.1) : flux lumineux des baies, éclairement naturel
  intérieur, consommation conventionnelle de l'habitation (1 W/m², C1 = 0,9, courbe C2), chaleur rendue au groupe.
- **Ventilation** : débit moyen entre le débit de base et le débit de pointe (grand débit 14 heures par semaine,
  fiche 6.2).
- **Structures** : `Groupe` reçoit `nb_logements` et `debit_ventilation_pointe_m3h` ; la transmission lumineuse
  `tl` des baies est contrôlée.
- **Hypothèses** : 40 constantes ajoutées, chacune sourcée (fiches 4.1, 4.5, 4.6, 6.2, 7.1, 8.1).
- **Correction** : 12 lignes de `donnees/hypotheses.csv` contenaient un « ; » dans leur source ou leur commentaire,
  ce qui tronquait la source à la lecture (les valeurs étaient justes). Remplacé par une virgule ; un test le contrôle.
- Lectures du texte et simplifications : `docs/audit.md` (hypothèses 29 à 41).
- Tests : 229 (émetteur, automate des saisons, consignes tenues sur l'année, bilan d'énergie avec émission,
  apports, lumière naturelle, sensibilités).

## 0.8.4 — évolution (13/11/2026), groupe

Modèle thermique horaire du groupe : températures de l'air, des parois et opérative, heure par heure.

- **Modèle du groupe** (`moteur/groupe.py`, annexe III, fiche 5.21, éq. 311 à 373) : réseau RC à trois nœuds (air,
  nœud des surfaces, masse), bilan de la masse par Crank-Nicolson, températures en moyenne et en fin d'heure,
  température radiante moyenne et température opérative, matrice du groupe (évolution libre, 10 W/m² convectifs,
  10 W/m² radiatifs). `simuler_groupe()` déroule l'année en évolution libre ou avec une puissance imposée, et
  donne le bilan d'énergie de chaque heure.
- **Inertie** : classes quotidiennes (tableau 53) et séquentielles (tableau 54 ; surfaces d'échange des règles
  Th-Bât, tableau 89), ou valeurs saisies. Les inerties séquentielle et annuelle ne jouent qu'en Th-D.
- **Enveloppe** (`moteur/enveloppe.py`) : U des baies et des parois selon l'inclinaison (fiches 5.10, éq. 207, et
  5.17, éq. 294), transmissions des baies, des parois opaques (coefficient b) et des ponts thermiques (l × ψ).
  Le rayonnement froid vers la voûte céleste utilise désormais ce U.
- **Baies** : flux solaire réparti en Fs1 (courte longueur d'onde), Fs2 (réémis) et Fs3 (lame d'air ventilée,
  nul sans protection) ; Sw2 saisi (`sw2_e`, `sw2_c`) ou nul par défaut.
- **Ventilation** : débit constant du groupe, échangeur d'efficacité 0,5 (ventilation conventionnelle du Bbio,
  fiche 6.1).
- **Brasseurs d'air** branchés sur le groupe : régime piloté par les températures de l'heure précédente, chaleur
  dégagée dans le bilan de l'heure ; refusés dans un groupe climatisé.
- **Structures** : `PontThermique` ; `Groupe` reçoit l'inertie, les ponts thermiques, le débit de ventilation et
  `climatise` ; `Baie` reçoit `sw2_e`, `sw2_c` et `uw_horizontal` ; `Paroi` reçoit `b_therm` et prend par défaut
  l'inclinaison de son type (mur 90°, toiture 0°, plancher bas 180°).
- **Hypothèses** : 38 constantes ajoutées, chacune sourcée (fiches 5.10, 5.17, 5.21, 6.1, règles Th-Bât).
- Lectures du texte et simplifications : `docs/audit.md` (hypothèses 17 à 28).
- Tests : 196 (régimes permanents analytiques, constante de temps, linéarité de la matrice, bilan d'énergie
  horaire et annuel à 0,1 % sur trois zones).

## 0.8.2 — évolution (12/11/2026), solaire

Rayonnement et éclairement reçus par une paroi orientée, masques, flux solaires transmis au groupe.

- **Rayonnement sur une paroi** (`moteur/solaire.py`, annexe III, fiche 3.2) : angle d'incidence, direct, diffus
  isotrope, réfléchi par le sol (albédo 0,2), rayonnement froid vers la voûte céleste, indicateur de jour.
- **Éclairement naturel** (fiches 3.1 et 3.2) : EDn et Edi tirés du rayonnement, puis direct, diffus et réfléchi
  sur la paroi, avec les mêmes masques.
- **Masques** (`moteur/masques.py`) : débord horizontal (direct et diffus), joues verticales gauche et droite, plan
  vertical lointain, horizon par 36 tranches de 10° ; combinaison par produit.
- **Flux transmis** : baie sans protection mobile `A × Sw × Isr` (Sw-c = Sw-e − 0,1 par défaut) ; paroi opaque
  `A × Sf × Isr`, avec Sf calculé selon les règles Th-Bât (`alpha × U × Rse`) ou saisi ; rayonnement froid
  `A × U × Qer / he`.
- **Structures** : convention d'orientation confirmée (0 = sud, 90 = ouest, valeurs ramenées dans [−180 ; 180[),
  inclinaison de 0 à 180°, masques, dimensions des composants, `sw_e` et `sw_c` (remplacent `sw`), `alpha`, `sf_c`,
  `sf_e` pour les parois opaques.
- **Hypothèses** : 23 constantes ajoutées, chacune sourcée (fiches 3.1, 3.2, 5.10, 5.17, règles Th-Bât).
- Tests : 121 (cas analytiques à 1 %, bilan horizontal à 0,1 % sur les 8 zones, ordres de grandeur).

## 0.8.0 — évolution (10/11/2026), socle

Première version : les données d'entrée du futur moteur et leurs contrôles. Aucun calcul thermique, aucune interface.

- **Structures** (`moteur/structures.py`) : Projet → Bâtiment → Zone → Groupe → Parois et Baies. Une zone porte une
  liste de groupes (logements traversants et non traversants).
- **Calendrier conventionnel** (`moteur/calendrier.py`) : heure légale (UTC + 1 l'hiver, UTC + 2 l'été, de l'heure
  1 896 à l'heure 7 031), année débutant un lundi, 52 semaines réparties 4-4-5-4-5-4-4-5-4-4-5-4, case des scénarios.
- **Météo** (`moteur/meteo.py`) : 8 zones climatiques × 2 jeux (Th-BC, Th-D), toutes les colonnes du classeur
  officiel, correction d'altitude (100, 500 ou 900 m).
- **Scénarios du logement collectif** (`moteur/scenarios.py`) : 13 scénarios (occupation, consignes 19/16 °C et
  26/30 °C, apports internes, éclairage, ventilation…), déroulés heure par heure sur l'année.
- **Hypothèses** (`donnees/hypotheses.csv`) : chaque constante avec son unité et sa source.
- **Extraction** (`outils/extraire_donnees.py`) : régénère les CSV de `donnees/` depuis les deux classeurs officiels,
  gardés en local dans `_references/`.
- Deux cas non décrits par les textes sont tranchés par hypothèse et consignés dans `docs/audit.md` : le jour 365 et
  la dernière heure de l'année.
- Tests : 61, dont la comparaison aux classeurs officiels quand ils sont présents en local.
