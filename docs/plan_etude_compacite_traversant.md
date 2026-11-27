# Plan de travail — étude « compacité × traversant »

Suit les règles de `CLAUDE.md` (« Lance » puis « Push », numéro de version demandé avant chaque lot). État de
départ : `travail` en 0.9.38, non commitée avec les 0.9.36 et 0.9.37 ; **les pousser avant L0**. Les versions
0.9.40 à 0.9.44 sont déjà prévues dans `ROADMAP.md` (masques et météo, aide, diffusion) : les numéros ci-dessous
viennent après elles et restent à confirmer.

Révision du 27/11/2026 : règle des 75 % (hypothèse 106), groupes construits sans fusion de `Boite`, niveau virtuel
limité à l'ouverture des baies, SHAB moyenne fixée au lieu de la SHAB totale, circulations en local non chauffé,
calage du carbone par lot, tests de tendance reformulés, campagne recomptée, travail découpé en parties.

## 1. Objet

Mesurer l'effet de la compacité et du caractère traversant sur trois indicateurs : le confort d'été (DH, avec le
Bbio pour l'effet en hiver), le coût et le carbone. Dans les projets, les deux grandeurs sont liées : un bâtiment
compact est rarement traversant. L'étude doit donc séparer leurs effets.

Décisions prises (27/11/2026) :

| Sujet | Décision |
|---|---|
| Carbone | Calcul dans un logiciel externe, à partir d'un export **IFC** |
| Coût | **Ratios** par ouvrage, appliqués à un métré ; la compacité seule sert de proxy de contrôle |
| Confort | DH lu **par groupe** (méthode Th-BCE : groupe traversant et groupe non traversant), comme `moteur/dh.py` |
| Traversant | Règle de l'annexe I (hypothèse 106 : chaque orientation porte moins de 75 % des baies du logement) ; dans le moteur, drapeau `Groupe.traversant` et secteurs d'orientation (`moteur/ouvertures.py`, éq. 251 à 254) |

## 2. Principes

1. **Deux niveaux d'analyse.**
   - **Niveau réel.** Un catalogue de plans constructibles. Leur compacité et leur part traversante découlent de
     l'épaisseur et du mode de desserte. Il donne le confort, le coût et le carbone.
   - **Niveau virtuel (confort seulement).** On reprend les mêmes géométries et on inverse le drapeau `traversant`
     des groupes dont les baies couvrent au moins deux secteurs. `traversant_hiver` garde la valeur du niveau
     réel : sinon les infiltrations changeraient aussi (tableau 22, `moteur/infiltrations.py:134`), dans le DH
     comme dans le Bbio. On obtient ainsi l'effet propre de l'ouverture traversante à compacité égale. Le Bbio du
     niveau virtuel est relevé aussi, car il varie par l'ouverture des baies en Th-B (`moteur/besoins.py:411`).
     Ce niveau ne change ni le coût ni le carbone : la géométrie est la même. Le coût et le carbone du traversant
     viennent seulement de la desserte (cages, ascenseurs, coursives), donc du niveau réel.
2. **Une seule description du plan.** Le confort, le métré, le coût, le carbone et l'IFC sont tous tirés de la
   même description. Un test vérifie que les surfaces de l'IFC, du métré et du projet thermique sont les mêmes.
3. **Le moteur ne change pas.** L'étude utilise `moteur/` sans le modifier. Si un besoin du moteur apparaît, il
   passe par `ROADMAP.md` et une version à part.
4. **Lien avec l'interface.** L'enveloppe de l'étude est une `Boite` de référence (`boite_de_depart`, niveau
   d'enveloppe choisi en L0). `vers_moteur.py` réutilise `gabarit_baie`, `largeur_travee` et
   `_conventions_protection` de `interface/saisie.py`. `etudes/` dépend donc de l'interface ; si celle-ci change
   ces fonctions, le test de non-régression de L2.1 le signale.
5. **Thermique d'un côté, coût et carbone de l'autre.** La campagne calcule le DH, le Bbio et le métré. Le coût et
   le carbone sont appliqués au métré au moment de l'analyse : changer un ratio ou un facteur ne relance aucun
   calcul thermique.
6. **Ce qui reste hors du dépôt.** Les résultats et l'IFC vont dans `_resultats/etude_ct/` ; les ratios de coût,
   s'ils sont confidentiels, dans `_donnees_etude/`. Les dossiers en `_` sont déjà exclus par `.gitignore`.
7. **Dépendances.** Seul l'export IFC ajoute une bibliothèque, `ifcopenshell`. Elle va dans
   `etudes/compacite_traversant/requirements.txt` et n'entre pas dans le `requirements.txt` de l'outil. Ses
   tests commencent par `pytest.importorskip("ifcopenshell")`. Le calcul en parallèle utilise `multiprocessing`
   (bibliothèque standard ; sous Windows, garde `if __name__ == "__main__"` et fonction de calcul importable) ;
   les graphiques, Altair (déjà présent).
8. **Tests rapides.** Les tests de l'étude lancés par `python -m pytest` se limitent à quelques calculs annuels ;
   la campagne n'est jamais lancée par les tests.

## 3. Arborescence

```
etudes/__init__.py
etudes/compacite_traversant/
  __init__.py
  README.md               mode d'emploi, commandes PowerShell
  requirements.txt        ifcopenshell (export IFC seulement)
  reglages.py             tous les réglages de l'étude (à valider en L0)
  donnees/
    typologies.csv        catalogue des typologies et de leurs plages de paramètres
    ratios_couts.csv      ouvrage;unite;cout_eur_ht;source;commentaire (gabarit, valeurs de Guigui)
    facteurs_carbone.csv  ouvrage;lot;unite;kgco2e;source;commentaire (tirés des pivots en L6)
    compositions.csv      composition des parois pour l'IFC (couches, épaisseurs, matériaux) ; U cohérents
  plan.py                 description paramétrique : corps, niveaux, logements, circulations, cages
  classement.py           classe réglementaire (règle des 75 %) et classe géométrique de chaque logement
  generateur.py           typologie + paramètres → Plan ; indicateurs de forme
  dessin.py               SVG d'un étage courant (contrôle visuel)
  vers_moteur.py          Plan → Projet multi-groupes du moteur ; inversion du niveau virtuel
  metre.py                Plan → quantités par ouvrage
  couts_carbone.py        quantités × ratios et facteurs ; proxy de compacité
  export_ifc.py           Plan → IFC4 (géométrie extrudée, matériaux, quantités de base)
  lire_carbone.py         lecture des résultats du logiciel carbone, facteurs par lot
  plan_experience.py      liste des variantes (niveau réel, niveau virtuel, sensibilités)
  lancer.py               campagne de calcul : parallèle, cache, reprise
  analyse.py              tables, régressions, graphiques, rapport HTML
tests/test_etude_ct_*.py  tests de l'étude (lancés par python -m pytest)
```

## 4. Modèle du plan

`Plan` (dataclass figée, comme `Boite`) :

- **corps** : rectangles extrudés (longueur, épaisseur, position, orientation, nombre de niveaux). Barre = 1
  corps, L = 2 corps, plot cruciforme = 1 noyau et 4 ailes ;
- **desserte** : `palier_2`, `palier_4`, `coursive`, `couloir_central`, `duplex_rue_interieure` ;
- **logements** : pour chaque niveau type, liste des logements avec SHAB, façades sur l'extérieur (corps,
  façade, longueur), baies par façade, classe réglementaire (`T` ou `NT`) et classe géométrique (`mono`, `angle`,
  `oppose`) ;
- **circulations** : couloirs, coursives (extérieures : masque proche horizontal sur la façade qu'elles longent,
  par `debord_m`), cages d'escalier, ascenseurs ;
- **groupes Th-BCE** : `T` (logements traversants selon la règle des 75 %) et `NT`. Un groupe absent est omis.

Classement d'un logement (`classement.py`) :

- **classe réglementaire** : règle de l'annexe I, la même que `Boite.traversant_selon_les_baies` (hypothèse 106,
  seuil `trav_part_max_orientation`). Un logement d'angle qui porte 75 % de ses baies ou plus sur une façade est
  `NT` ;
- **classe géométrique** : `mono` (une façade vitrée), `angle` (deux façades à 90°), `oppose` (deux façades à
  135° ou plus). Elle sert à la lecture, pas au calcul ;
- **répartition des baies** dans un logement à plusieurs façades : réglage `REPARTITION_BAIES` (proportionnelle
  aux longueurs de façade, par défaut). Le classement en découle.

Indicateurs de forme calculés sur le plan :

- `compacite` = surface déperditive / SHAB (m²/m²), même définition que `interface/indicateurs.py`
  (hypothèse 107) : parois et baies sur l'extérieur ou le sol. Les parois sur circulation n'y entrent pas, quelle
  que soit l'hypothèse thermique retenue pour elles : la compacité reste une donnée de forme. Parts façade,
  toiture et plancher bas ;
- `circulation_par_shab` : surface des parois sur circulation chauffée ou non / SHAB ;
- `part_traversante` = SHAB des logements `T` / SHAB, avec la part `angle` et la part `oppose` séparées ;
- `facade_par_shab`, `vitrage_par_shab`, `logements_par_cage`, `ascenseurs_par_logement`.

Plus l'indicateur `compacite` est grand, moins le plan est compact. Toutes les phrases de l'étude parlent de
« surface déperditive / SHAB » qui monte ou qui descend, pour éviter ce contresens.

## 5. Découpage du travail

Chaque **lot** est une version. Chaque lot est découpé en **parties**, lancées une par une :

- une partie = un « Lance » ; elle se termine par des tests qui passent (`python -m pytest`), un résumé court, une
  mise à jour de `docs/passation.md`, et un arrêt pour validation ;
- le numéro de version est demandé avant la première partie du lot ; les parties suivantes restent sur la même
  version ;
- « Push » en fin de lot (ou plus tôt sur demande) ; `VERSION`, `CHANGELOG.md` et `ROADMAP.md` sont mis à jour à
  la dernière partie du lot ;
- une partie marquée **attente** dépend d'une réponse ou d'un calcul de Guigui : rien ne se lance avant.

### L0 — Cadrage (sans calcul) — proposé 0.9.46

- **L0.1 — Réponses (attente).** Guigui répond aux questions du § 10. Les réponses sont reportées dans ce plan.
- **L0.2 — Squelette.** `etudes/__init__.py`, `etudes/compacite_traversant/__init__.py`, `README.md`,
  `reglages.py` et les gabarits CSV (`ratios_couts.csv`, `facteurs_carbone.csv`, `compositions.csv` vides,
  `typologies.csv` prérempli d'après le § 6). Test : les réglages et les CSV se lisent ; une colonne manquante
  donne une erreur claire (fichier, ligne).
- **L0.3 — Hypothèses et feuille de route.** Hypothèses de l'étude dans `docs/audit.md`, numérotées à partir de
  108 (§ 8) ; l'étude dans `ROADMAP.md`. Push.

### L1 — Plan, classement, générateur — proposé 0.9.48

- **L1.1 — Modèle et indicateurs.** `plan.py` et les indicateurs de forme. Tests : compacité analytique d'une
  barre et d'un cube ; somme des surfaces ; conservation de la SHAB, sur des plans faits à la main.
- **L1.2 — Classement.** `classement.py`. Tests : mono, angle et opposé sur des plans faits à la main ; angle à
  80 % sur une façade classé `NT` ; accord avec `Boite.traversant_selon_les_baies` sur des boîtes d'un logement.
- **L1.3 — Barres.** `generateur.py`, typologies A, B, C et G. Contrôles : chaque logement a au moins une façade
  extérieure ; SHAB moyenne tenue à ± 2 % ; part vitrée de chaque façade ≤ `PART_VITREE_MAX` ; vitrage / SHAB
  égal au réglage.
- **L1.4 — Plots et duplex.** Typologies D, E et F, mêmes contrôles.
- **L1.5 — Contrôle visuel.** `dessin.py` : SVG d'un étage courant par typologie (une planche de contact),
  logements colorés par classe, vue dans Chrome avant validation. Push.

### L2 — Passage au moteur — proposé 0.9.50

- **L2.1 — Un groupe.** `vers_moteur.py` construit les `Groupe` directement à partir du `Plan` : parois, baies
  (`gabarit_baie`, `largeur_travee`), protections (`_conventions_protection` de la `Boite` de référence), masques,
  rives des planchers, brasseurs. Une fusion de `Boite` ne convient pas : une `Boite` n'a que des façades entières,
  alors qu'un groupe n'occupe souvent qu'une partie d'un corps (logements d'angle en bout de barre A). Test de
  non-régression : un plan à un corps et un groupe donne, au bit près, le DH et le Bbio de la `Boite` équivalente
  (logement de 70 m² et immeuble de 9 logements).
- **L2.2 — Deux groupes et circulations.** Façades entre groupes : pas de conduction (hypothèse 109). Murs sur
  circulation : `contact="local_non_chauffe"` avec `b_therm` (réglage `B_CIRCULATION`), ou adiabatiques selon le
  réglage `CIRCULATIONS` (hypothèse 108). Garde-fou : un groupe `T` doit respecter la règle des 75 % et avoir des
  baies sur deux secteurs au moins ; sinon Sors est nul et le groupe ventilerait moins qu'un non traversant
  (éq. 254). Tests : somme des surfaces des groupes = surfaces du plan ; plan non conforme refusé avec un message
  clair.
- **L2.3 — Niveau virtuel et temps.** Fonction d'inversion : `traversant` inversé, `traversant_hiver` gardé.
  Tests : infiltrations identiques heure par heure entre réel et virtuel ; seul le débit des baies change. Mesure
  du temps d'un calcul DH + Bbio à deux groupes, qui sert au dimensionnement de L5. Push.

### L3 — Métré et coût — proposé 0.9.52

- **L3.1 — Métré.** `metre.py`, pour chaque ouvrage :
  - façade opaque (m²) ;
  - menuiseries (m²) ;
  - toiture (m²) ;
  - plancher bas et fondations (m² d'emprise) ;
  - planchers intermédiaires (m²) ;
  - refends et murs séparatifs (m²) ;
  - murs et cloisons de circulation (m²) ;
  - couloirs et coursives (m²) ;
  - cages d'escalier (unités × niveaux) ;
  - ascenseurs (unités, arrêts) ;
  - balcons (m²) ;
  - ponts thermiques (ml).

  Test : métré d'une barre simple calculé à la main.
- **L3.2 — Coût et proxy.** `couts_carbone.py` : coût = Σ quantités × ratios, rapporté à la SHAB (€ HT/m² SHAB),
  puis comparaison au proxy (régression du coût sur la compacité seule, R² affiché). On sait ainsi si la
  compacité suffit comme indicateur du coût, et ce que la desserte y ajoute. Test : ratio absent → erreur claire
  (fichier, ligne). Push.

### L4 — Export IFC — proposé 0.9.54

- **L4.1 — Fichier test.** `export_ifc.py` minimal (IFC4, `ifcopenshell.api`) pour un seul plan (barre A à
  couloir central) : niveaux, murs, dalles, fenêtres, espaces. Test : le fichier se relit.
- **L4.2 — Import (attente).** Guigui importe le fichier dans le logiciel carbone et dit ce qui est lu et ce qui
  manque. Rien ne suit tant que l'import n'est pas validé.
- **L4.3 — Export complet.** Selon le retour de L4.2 :
  - `IfcBuildingStorey` par niveau ;
  - `IfcWall` (façades, refends, circulations), avec `IfcMaterialLayerSetUsage` tiré de `compositions.csv` ;
  - `IfcSlab` (planchers, toiture, dalle basse, coursives, balcons) ;
  - `IfcWindow` dans des `IfcOpeningElement` ;
  - `IfcStair` et `IfcTransportElement` pour les cages et les ascenseurs ;
  - `IfcSpace` par logement, avec un jeu de propriétés `Pset_EtudeCT` : groupe, classe réglementaire, classe
    géométrique, identifiant du plan ;
  - quantités de base `Qto_*BaseQuantities`.

  Test : relire l'IFC et retrouver le métré à 0,1 % près.
- **L4.4 — Pivots.** Chaque typologie × deux tailles, soit 14 IFC, dans `_resultats/etude_ct/ifc/`. Push.
  Guigui les calcule dans le logiciel carbone pendant L5.

### L5 — Plan d'expérience et campagne — proposé 0.9.56

- **L5.1 — Liste des variantes.** `plan_experience.py` : la grille du § 6, les variantes virtuelles, la
  sensibilité aux circulations, sans doublons (orientations équivalentes des plans symétriques). Sortie : le
  nombre de calculs par catégorie et la durée estimée avec le temps mesuré en L2.3. **Arrêt** pour valider la
  taille de la campagne.
- **L5.2 — Lanceur séquentiel.** `lancer.py`, en ligne de commande : `--zones`, `--calculs dh,bbio`, `--filtre` ;
  cache par empreinte dans `_resultats/etude_ct/cache/` (hachage du `Plan`, de `moteur/*.py`,
  `donnees/hypotheses.csv`, des fichiers météo et des scénarios ; pas de `VERSION`, qui change avec l'interface) ;
  reprise après une interruption ; journal des erreurs, sans arrêt de la campagne. Essai sur cinq plans.
- **L5.3 — Parallèle et campagne.** `--processus`. Test : mêmes résultats en séquentiel et en parallèle sur deux
  plans. La campagne complète est lancée par Guigui (§ 11), hors session.
- **L5.4 — Calcul par logement.** Option `--par-logement`, sur les pivots seulement : un groupe par logement, pour
  le DH du pire logement (L7). Push.

Sortie : `_resultats/etude_ct/resultats.csv`, une ligne par plan, zone et groupe, plus une ligne « bâtiment »
(`;`, virgule décimale). Colonnes :

- identifiant, typologie, paramètres, niveau (réel, virtuel ou sensibilité) ;
- indicateurs de forme ;
- quantités du métré ;
- DH, DH max, écart et respect par groupe ;
- pour le bâtiment : DH pondéré par la SHAB, DH du pire groupe, part de SHAB au-dessus du DH max ;
- Bbio et Bbio max du bâtiment.

Le coût et le carbone n'y sont pas : `analyse.py` les calcule à partir des quantités (§ 2, principe 5).

### L6 — Carbone — proposé 0.9.58

- **L6.1 — Lecture des résultats (attente des pivots).** Guigui remplit `_donnees_etude/resultats_carbone.csv`
  (`plan_id;ic_construction;` puis un poste par lot). `lire_carbone.py` lit le fichier et contrôle les plans et
  les lots.
- **L6.2 — Facteurs.** Chaque facteur est tiré de son lot : carbone du lot / quantité de l'ouvrage. Les
  compositions étant fixes (`compositions.csv`), le carbone est presque proportionnel au métré. Une régression
  serait sous-déterminée (onze pivots pour une douzaine de facteurs liés entre eux). Contrôle : trois pivots
  tenus à part, écart affiché par lot. Ce qui n'est pas proportionnel (forfaits du logiciel, lots techniques)
  est relevé à part. Push.

### L7 — Analyse — proposé 0.9.60

- **L7.1 — Tables et effets.** `analyse.py` : coût et carbone appliqués au métré ; effets propres tirés du
  niveau virtuel (régression DH ~ surface déperditive / SHAB + traversant + interaction, par zone) ; effet de
  l'hypothèse sur les circulations. Sorties CSV.
- **L7.2 — Rapport.** `_resultats/etude_ct/rapport.html` (Altair, un seul fichier) :
  - nuage surface déperditive / SHAB × part traversante, coloré par DH, Bbio, coût et carbone, avec la zone
    atteignable par le niveau réel ;
  - fronts de Pareto confort / coût / carbone ;
  - `angle` et `oppose` toujours séparés.
- **L7.3 — Fiches.** Une fiche par typologie (plan SVG, indicateurs, résultats) ; l'écart entre le DH par groupe
  et le DH du pire logement (L5.4), pour montrer ce que la moyenne du groupe cache (mono-orientés ouest). Style des
  graphiques : celui de Guigui (axes en gras fléchés, grille en pointillé gris, légende à droite) et palette du
  HUB (`ROADMAP.md`). Vu dans Chrome. Push.

### L8 — Contrôle — proposé 0.9.61

- **L8.1 — Relecture.** Par un agent qui n'a pas écrit le code : métré, agrégation, signes des effets,
  cohérence entre l'IFC et le métré.
- **L8.2 — Tests de tendance**, ajoutés à `tests/test_tendances.py` :
  - DH(T) < DH(NT) à géométrie égale, **pour des baies réparties à parts égales sur deux façades opposées**.
    Avec des baies très déséquilibrées, l'inverse est possible : le débit par le vent du groupe traversant suit
    Sors (éq. 254) et non la surface ouverte totale (éq. 251) ;
  - Bbio croissant quand la surface déperditive / SHAB augmente, à enveloppe égale.
- **L8.3 — Logiciel réglementaire (attente).** Guigui calcule le DH de deux ou trois pivots dans Climawin ou
  Pleiades, avec les groupes T et NT. L'effet du traversant repose sur l'ouverture des baies en Th-D, que
  l'outil sous-estime de 16 à 32 % par rapport au moteur COMETH (`docs/passation.md`) ; l'effet du traversant
  pourrait donc être sous-estimé. Le rapport affiche l'écart. Push.

## 6. Plan d'expérience

**Typologies (niveau réel)**

| Code | Typologie | Épaisseur (m) | Desserte | Attendu |
|---|---|---|---|---|
| A | Barre épaisse | 14 / 16 / 18 | couloir central | compacte, NT |
| B | Barre mince | 10 / 11 / 12 | palier à 2 logements | peu compacte, T opposé |
| C | Barre à coursive | 9 / 10 / 11 (+ coursive 1,5) | coursive extérieure | peu compacte, T opposé, masque sur une façade |
| D | Plot | 16 × 16 / 20 × 20 | palier à 4 logements | compacte, T d'angle (selon la règle des 75 %) |
| E | Barre épaisse en duplex | 14 / 16 / 18 | rue intérieure tous les 2 niveaux | compacte et T opposé (contre-exemple) |
| F | Plot cruciforme | ailes de 10 / 12 | noyau central | peu compacte, T d'angle (selon la règle des 75 %) |
| G | Barre mince mono-orientée | 7 / 8 | coursive fermée ou adossée | peu compacte, NT (contre-exemple) |

**Facteurs variables** : épaisseur (tableau), longueur des barres (2 ou 3 cages, ou modules pour C et E),
hauteur (R+3 / R+6), orientation de l'axe (0 / 45 / 90° ; 0 et 45° seulement pour D et F, symétriques), zone
(par exemple H1a, H2d, H3, à valider en L0).

**Facteurs fixés** (`reglages.py`) :

- **SHAB moyenne et répartition des logements** (T2, T3…). Le DH max et le Bbio max en dépendent : le DH max
  lit la SHAB moyenne de la zone (`moteur/dh.py:204`). La SHAB totale découle de la forme et varie d'un plan à
  l'autre ; elle est relevée, pas fixée. Fixer à la fois la SHAB totale, l'épaisseur et la hauteur imposerait la
  longueur ;
- **vitrage rapporté à la SHAB**. Les tendances de la 0.9.27 montrent que plus de vitrage fait baisser le DH,
  parce que la surface ouvrante suit la surface des baies. Sans ce réglage, le traversant gagnerait ou perdrait
  simplement par sa surface vitrée ;
- répartition des baies dans un logement (§ 4), ratio d'ouverture, enveloppe, protection et gestion, inertie,
  teinte, débit de ventilation, perméabilité ;
- circulations : local non chauffé avec coefficient b (réglage), par défaut.

**Contrôle des interactions** : une sous-grille sur les typologies A, B et E seulement, avec la protection
(aucune / volet) et l'inertie (légère / lourde).

**Sensibilité aux circulations** : A, D, E et F (desserte intérieure) recalculés avec les murs sur circulation
adiabatiques. Les circulations en local non chauffé ou adiabatiques favorisent différemment les typologies
compactes, précisément celles que l'étude compare.

**Niveau virtuel** : A, B, C, D, E et F avec le drapeau `traversant` inversé, pour couvrir toute la plage de
compacité. G n'entre pas : un seul secteur, ce que le garde-fou de L2.2 refuse.

**Taille estimée** (à recompter en L5.1) :

| Catégorie | Plans |
|---|---|
| Grille de base (A, B, C, E : 36 chacun ; G : 24 ; D, F : 8 chacun) | 184 |
| Sous-grille protection × inertie (A, B, E : 108 plans × 3 combinaisons de plus) | 324 |
| Niveau virtuel (A à F, grille de base) | 160 |
| Sensibilité aux circulations (A, D, E, F) | 88 |
| **Total par zone** | **756** |

Soit environ 2 300 calculs pour trois zones. À 8 s par plan à deux groupes (DH + Bbio, à remesurer en L2.3) :
5 h sur un processus, environ 1 h sur six.

## 7. Agrégation et lecture

- Le DH est lu par groupe, comme dans la méthode. Pour le bâtiment, on lit : DH pondéré par la SHAB, DH du pire
  groupe, respect de chaque groupe.
- Le Bbio est lu à l'échelle du bâtiment (`ResultatBbio.batiments`).
- Unités : coût en € HT/m² SHAB ; carbone en kgCO₂e/m² de surface de référence (comme l'Ic construction).
- Toujours séparer `angle` et `oppose` dans les graphiques : le moteur traite les deux par les secteurs, mais
  leurs effets diffèrent.

## 8. Hypothèses à inscrire dans `docs/audit.md` (à partir de 108)

108. Circulations hors groupe ; murs sur circulation en local non chauffé avec coefficient b (réglage), ou
     adiabatiques en sensibilité. Ils n'entrent pas dans la compacité.
109. Logements d'un même groupe confondus en une température (méthode Th-BCE) ; pas de conduction entre groupes.
110. Classe réglementaire d'un logement : règle des 75 % (hypothèse 106) ; baies réparties selon
     `REPARTITION_BAIES`.
111. Niveau virtuel : `traversant` inversé, `traversant_hiver` gardé ; seule l'ouverture des baies change.
112. Coursive extérieure = masque proche horizontal sur la façade qu'elle longe.
113. Duplex sur rue intérieure : la rue est une circulation hors groupe, et chaque duplex a deux façades opposées.
114. Ascenseur à partir de R+3 (réglage) ; une cage dessert au plus N logements par palier (réglage).
115. Carbone des variantes non exportées : facteurs par lot tirés des pivots, avec l'écart de contrôle affiché.
116. Coût : ratios hors VRD, fondations spéciales et lots techniques (à confirmer avec Guigui).

## 9. Limites connues du moteur qui touchent l'étude

- Ouverture des baies en Th-D 16 à 32 % sous le moteur COMETH : l'effet du traversant pourrait être sous-estimé
  (voir L8.3).
- θop d'été 0,3 à 0,6 °C trop bas sur certaines études ; DH à ± 10 % dans 21 groupes sur 37.
- Soleil des fichiers météo en retard d'une heure (R3, non tranché) : effet possible sur l'écart entre est et
  ouest.
- Les conclusions porteront sur des **écarts entre variantes**, plus robustes que les valeurs absolues. Le rapport
  le dit.

## 10. À valider par Guigui avant L1 (L0.1)

1. Logiciel carbone visé (pour le fichier test IFC de L4).
2. Zones climatiques ; SHAB moyenne et répartition des logements.
3. Enveloppe (niveau de `typologies_logements.csv`), protection, gestion et inertie de référence.
4. Circulations : coefficient b retenu.
5. Répartition des baies dans un logement à plusieurs façades.
6. Liste des typologies (§ 6) : retirer ou ajouter ; taille de la campagne.
7. Source des ratios de coût et périmètre (lots compris).
8. Place de l'étude par rapport aux 0.9.40 à 0.9.44 prévues, et numéros de version.

## 11. Commandes (PowerShell)

```powershell
cd explorateur_Bbio_DH
git checkout travail
.\.venv\Scripts\Activate.ps1
pip install -r etudes\compacite_traversant\requirements.txt      # seulement pour l'export IFC
python -m pytest tests -k etude_ct
python -m etudes.compacite_traversant.plan_experience            # nombre de calculs et durée estimée
python -m etudes.compacite_traversant.lancer --zones H1a,H2d,H3 --calculs dh,bbio --processus 6
python -m etudes.compacite_traversant.lancer --par-logement --filtre pivots
python -m etudes.compacite_traversant.export_ifc --pivots
python -m etudes.compacite_traversant.lire_carbone "_donnees_etude\resultats_carbone.csv"
python -m etudes.compacite_traversant.analyse
```
