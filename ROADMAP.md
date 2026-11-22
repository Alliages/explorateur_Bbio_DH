# Feuille de route — Explorateur Bbio / DH

Seule liste de suivi du projet. Le plan détaillé (limites, plan de contrôle, organigrammes) est dans le document
« plan de bataille » : https://claude.ai/artifact/6joP54tckVZQdM8LYVeLRF

## Versions

| Version | Nom | Contenu | État |
|---|---|---|---|
| 0.8.0 | Socle | Structures multi-groupes, calendrier, météo (8 zones, Th-BC et Th-D), scénarios du logement collectif | fait |
| 0.8.2 | Solaire | Rayonnement sur une paroi orientée, masques simples, facteurs solaires | fait |
| 0.8.4 | Groupe | Modèle thermique horaire du groupe (fiche 5.21) : réseau RC, inertie, température opérative | fait |
| 0.8.6 | Besoins | Besoins de chauffage, de refroidissement et d'éclairage | fait |
| 0.8.8 | Bbio | Revue des hypothèses 29, 30, 31 et 36 de l'audit. Bbio = 2 × Bch + 2 × Bfr + 5 × Becl par groupe, zone et bâtiment, comparaison au Bbio max | fait |
| 0.8.10 | Cas de référence | Lecteur de RSET (`outils/lire_rset.py`), comparaison du Bbio à des études (`outils/comparer_reference.py`), variantes du besoin de froid | fait |
| 0.8.12 | Protections et ouvertures | Protections mobiles (fiche 5.9 : volets et stores enroulables, gestion manuelle et automatique) et ouverture des baies du mode Th-B (fiche 5.13) | fait |
| 0.8.14 | Infiltrations | Débits d'air par les défauts d'étanchéité (fiche 5.6) : perméabilité à l'air, vent, tirage thermique, équilibre de pression | fait |
| 0.8.16 | DH | Degrés-heures d'inconfort (fiche 13.5) sur le jeu Th-D, comparaison au DH max ; confort adaptatif, règles Th-D des protections et des ouvertures, brasseurs d'air dans le calcul | fait |
| — | Brasseurs d'air (anticipé pour le DH) | `moteur/brasseurs.py` (fiche 8.32) : régulation, effet ΔθopBA sur le seuil d'inconfort, consommation ; classe `Brasseur`, `Groupe.volume_m3` et `Groupe.brasseurs` ; `tests/test_brasseurs.py` ; branchés sur le groupe en 0.8.4 | fait |
| 0.8.17 | Relecture | Correction : documentation (premier calcul et modules dans le README), avertissement du DH, appariement des études par nom, doublons et noms clarifiés ; résultats inchangés | fait |
| 0.8.18 | Interface | Streamlit : boîte en axonométrie (style cbsh_visuel), saisie, résultats ; briques pédagogiques à deux niveaux (Bbio, DH, semaine chaude) | fait |
| 0.9.0 | Fonctionnel | Outil utilisable de bout en bout : contrôle visuel, balcons, comparaison de deux variantes, calcul plus rapide | fait, hors mise en ligne (accord et lien en attente) |
| 0.9.1 | Choix du calcul | DH, Bbio ou les deux (seul le calcul demandé est lancé) ; bâtiment de départ : logement de 70 m² ou immeuble de 9 logements | fait |
| 0.9.2 | Niveaux d'enveloppe | Trois enveloppes de départ (performante, moyenne, faible) tirées de 18 zones de logements de 6 études RE2020 (`donnees/typologies_logements.csv`, `outils/typologies/`) | fait |
| 0.9.4 | Bâtiments en CSV | Bâtiments de départ lus dans `donnees/batiments/` (un CSV par bâtiment) ; nouveau logement de 70 m² (H1a, 7 × 10 m, baies 25 % devant et derrière, pignons aveugles, gestion motorisée) | fait |
| 0.9.6 | Pédagogie | Page d'accueil (comme Météo et Chaleur), équations montrées dans les briques avec ce qu'elles disent, course solaire d'été (21 juin) au bord du sol du dessin, écart avec le calcul précédent dans les chiffres clés, aides des saisies dans un fichier à part (`interface/textes/aides.csv`), liens vers le Glossaire du confort dans le bâtiment (Notion) | fait |
| 0.9.8 | Validation | Validation par lot (`outils/valider.py`) sur 10 études, 5 bâtiments, 23 groupes : 9 groupes dans la cible Bbio de ± 10 % (6 sur 6 en H2a, 2 sur 4 en H1a, 1 sur 13 en H3) ; parois à U = 0 lues ; bouton « Télécharger ce bâtiment ». Reste : plus de bâtiments (OPEE, nouveaux RSEE), froid en H3, chauffage en H1a | en partie |
| 0.9.9 | Comparaison horaire | Sorties horaires d'un moteur Th-BCE (Paris, Sète, Nice A) face à l'outil, heure par heure (`outils/lire_horaires.py`, `outils/comparer_horaires.py`) ; correction : ouverture des baies en Th-B hors saison de froid comme le moteur, pas comme l'éq. 244 (hypothèse 91) ; restent infiltrations d'hiver 1,5 à 3,5 fois trop faibles, Φsh des ponts thermiques absent, ratio d'ouverture trop faible | fait |
| 0.9.10 | Ouverture et infiltrations | Perméabilité à l'air des protections mobiles devant une baie ouverte (fiche 5.12, typologie `Typo_Permea_PM`) ; entrées d'air du projet gardées dans les infiltrations du Bbio, comme le moteur (hypothèse 92) | fait |
| 0.9.11 | Relecture indépendante de la 0.9.8 | Remarques mesurées face au moteur et aux études : écart de confort adaptatif nul en Th-B (froid de H3 : 1,7 → 1,0 fois l'étude, 9 groupes sur 13 dans ± 10 %), traversant d'hiver de la zone pour les infiltrations, store par grand vent, comptage des groupes de `valider.py` (46 et non 58) ; hypothèses 93 à 98 | fait |
| 0.9.12 | Types de protection | Liste « type de protection » dans l'interface (volet roulant, persienne, store toile extérieur ou intérieur ; clair ou sombre) qui remplit Sw1, Sw2, Sw3, ΔR (d'où le U protégé), Tl protégée et Typo_PM, d'après le guide Actibaie (pp. 27, 45-48 ; `donnees/protections_types.csv`, double vitrage σ 0,70) ; les valeurs de la baie nue restent saisies (le guide ne les donne pas) | à faire |
| 0.9.13 | Protections de la boîte | Correction d'après le guide Actibaie : volets et stores perméables à 10 % (Typo_PM 1), Sw protégé d'un volet tout en Sw2 ; test de tendance des gestions sur le DH ; DH des bâtiments de départ − 9 à − 13 % (hypothèse 99) | fait |
| 0.9.14 | Maison individuelle | Second usage. Cas du guide Actibaie à reprendre : Bbio max d'une maison de 100 m² par ville (p. 6), DH et Bbio de la maison H3 (pp. 7, 28), maison de plain-pied H2b de l'AICVF (p. 33 : inertie, casquette, brasseurs) | à faire |
| 0.9.15 | Ouverture des baies comme le moteur | Correction : profil d'ouverture du moteur COMETH (θouv2 sans Δθconf_adapt, θouv1 à 1 °C, réglage la nuit aussi ; hypothèse 100), retrouvé 92 à 99,9 % des heures. Ouverture face au moteur − 4 à + 3 % en Th-B, − 4 à − 16 % en Th-D ; validation 30 groupes sur 46 dans ± 10 %, froid 0,94 fois l'étude, DH à ± 10 % dans 21 groupes sur 37 | fait |
| 0.9.16 | Soleil, orientation, parois adiabatiques, zoom | Dessin : course du 21 juin dans le ciel, soleil à sa hauteur à l'heure choisie (curseur 6 à 20 h, 16 h légale par défaut), ombre portée au sol coupée au bord, façades à l'ombre assombries, flèche du nord. Orientation par pas de 10° (azimut géographique). Parois adiabatiques (façades, toiture, plancher bas ; grises dans le dessin ; hypothèse 101). Graphiques : extérieur noir, seuil orange, intérieur jaune ; brique DH heure par heure, zoomable (été entier, semaine ou jour le plus chaud, cadre tracé sur les DH de chaque jour) | fait |
| 0.9.18 | Fiche d'une paroi | Étapes 1 et 2 du plan « informations au clic » : liste « Paroi examinée » sous le dessin (façades, baies de chaque façade, toiture, plancher bas), paroi entourée dans le dessin (en pointillé si cachée), fiche (surface, U et U × surface, Uw, Sw, Tl, protection, orientation, part vitrée, balcon, adiabatique) ; infobulle de chaque mur, baie et toiture au survol (dessin écrit en SVG dans la page) | fait |
| 0.9.20 | Ce que fait une paroi | Étape 3 du plan « informations au clic » : bilan de chaque baie et paroi opaque heure par heure (`moteur/bilan_paroi.py`, hypothèse 102), sommes égales aux flux du groupe ; sous la fiche, soleil reçu et transmis, rayonnement froid, chaleur perdue U × S × (θi − θe), protections baissées et baies ouvertes, sur la semaine la plus chaude, l'été (confort adaptatif) et l'année moyenne du Bbio, selon les calculs lancés | fait |
| 0.9.22 | Clic sur le dessin | Étape 5 du plan « informations au clic » : cliquer sur un mur, des baies ou la toiture du dessin ouvre sa fiche (composant `interface/dessin_cliquable.py`, `st.components.v2` ; clé de paroi `data-cle` sur chaque forme) ; la liste « Paroi examinée » reste pour le clavier et les parois cachées | fait |
| 0.9.24 | Coupe du bilan | Étape 4 du plan « informations au clic » et coupe schématique : coupe transversale de la boîte (toiture, plancher bas, façades principale et arrière avec leurs baies, pignons en une flèche), flèches proportionnelles aux kWh (soleil transmis, U × S × Δθ, rayonnement froid, ventilation et infiltrations, apports internes, ponts thermiques, besoin), hiver (Bbio) ou été et semaine la plus chaude (DH) ; part de chaque paroi dans les apports des heures qui comptent des DH ; bouton « Mesurer l'effet de cette paroi » (calcul relancé sans elle : baie remplacée par le mur de sa façade, paroi opaque rendue adiabatique ; ΔDH, ΔBbio) ; clic sur la coupe. Brique « Le bilan en coupe » (`interface/coupe.py`, `interface/briques/bilan.py`), hypothèses 103 et 104 | fait |
| 0.9.25 | Bilan en coupe exact | Correction : conduction des parois et des baies lue dans le modèle (masse θmq, surfaces θs), bilan fermé exactement, reste = stockage de la masse (hypothèse 103 corrigée) ; lecture « Heure de pointe (Wh) » de la coupe, pic du soleil transmis dans la fiche (hypothèse 105) | fait |
| 0.9.27 | Audit de la 0.9.25 | Non-régression des bâtiments de départ ; relecture de `dh.py`, `confort.py`, `brasseurs.py`, `enveloppe.py` (points R1 à R6 de `docs/audit.md`) ; tendances de la boîte (six testées) ; documentation et fiabilité affichée mises à jour ; calcul inchangé | fait |
| 0.9.29 | Calcul plus rapide | Infiltrations (bilans des bornes gardés) et ouverture des baies (secteurs, Cpr, hystérésis) : 1,16 fois plus rapide, résultats identiques au bit près ; vectorisation numpy essayée et écartée ; sensibilité du DH de 0,2 % à une perturbation de 1e-12 (`docs/audit.md`, 0.9.29) | fait |
| 0.9.30 | Audit du code | Relecture d'ensemble (`docs/audit.md`, 0.9.30, constats 1 à 7) : test de non-régression des six boîtes de départ et de l'exemple du README, `simuler_groupe()` supprimée (une seule boucle annuelle, tests reportés sur `calculer_besoins()`), versions des dépendances épinglées ; nettoyages des constats 5 à 7 ; résultats inchangés | fait |
| 0.9.32 | Page « Explorer » resserrée | Critique de conception (25/40) : « Calculer » collé en bas du menu, barre des résultats collée en haut (écart à la référence, état périmé), résultats périmés pâlis, la boîte et la fiche à droite du dessin, volets résumés dans leur titre, « Baies » ouvert | fait |
| 0.9.34 | Variantes et lecture côte à côte | Variantes A à D (pastilles dans la barre des résultats, un clic remet la saisie, référence au choix) à la place de la référence unique ; synthèse « Bbio et DH ensemble » face à la référence ; saisies de la paroi dans sa fiche, liées au menu | fait |
| 0.9.26 | Diffusion | Module pédagogique séparé sur la diffusion de la chaleur (sans lien de calcul) ; 0.9.6 avant le 15/11/2026 ; décalée de 0.9.16 le 20/11/2026, de 0.9.18, 0.9.20, 0.9.22 et 0.9.24 le 22/11/2026 | à faire |
| 1.0.0 | Diffusion publique | Version annoncée | à faire |

## En attente

- Mise en ligne de la 0.9.0 : accord explicite et lien de déploiement Streamlit (l'outil est prêt, voir
  `README.md`, « Mise en ligne »).
- Extraction OPEE en parquet (pour la 0.9.8).
- Accord de la DHUP sur l'usage des fichiers météo (avant la 1.0.0).
- Seuils du plan de contrôle : 1 % sur les cas analytiques, 0,1 % sur le bilan d'énergie, quartiles OPEE.
- Chapitre V de l'annexe à l'article R. 172-4 (catégories de contraintes extérieures), absent de `_sources/` : il
  fixe la colonne du DH max (hypothèse 76 de `docs/audit.md`).

## Points à reprendre

- **Montée de version des dépendances** (0.9.30) : les versions de `requirements.txt` sont épinglées ; pour en
  monter une, relancer `python -m pytest` (non-régression comprise) et le noter au CHANGELOG.
- **Vitesse du calcul, suites** (0.9.29, détail : `docs/audit.md`) : la boucle horaire dépend de l'heure
  précédente et ne se vectorise pas sur le temps. Pistes restantes, seulement si l'interface paraît lente ou pour
  les balayages (« Mesurer l'effet de cette paroi », tendances, validation) : calculer plusieurs variantes à la fois
  (boucle sur les heures, tableaux sur les variantes ; refonte de `besoins.py`, `protections.py`, `ouvertures.py`,
  `infiltrations.py`) ; numba sur la boucle (une dépendance de plus). Protections (`ratios`, `flux` : 20 % du
  temps restant) laissées telles quelles : leurs produits scalaires numpy ne sont pas reproductibles au bit près en
  Python.
- **Sensibilité numérique du DH** (0.9.29) : ± 0,2 % pour une perturbation de 1e-12 (seuils de l'ouverture et des
  protections). Bien sous les cibles de validation (± 10 %), mais à garder en tête pour comparer deux versions ou
  deux variantes proches.
- **Audit de la 0.9.27, suites** (détail : `docs/audit.md`, 0.9.27) :
  - relancer sur le poste `python -m outils.valider "..\_RSEE" "_sources" --dh` et `python -m outils.comparer_horaires
    tous` (non-régression face à la 0.9.15) ;
  - **R3, heure du soleil** : les fichiers météo placent le soleil de l'heure k au milieu de [k − 1 ; k[ TU, l'outil
    lit l'heure k comme [k ; k + 1[ TU. Comparer heure par heure Fs1 de l'outil et du moteur (décalage 0 ou ± 1 h).
    Si le moteur fait comme l'outil, le dire dans le dessin (soleil astronomique) ou dessiner le soleil du calcul ;
  - **R1, inertie séquentielle** : effet nul dès que Ams ≥ Amq, non monotone selon la classe ; à trancher avec les
    éq. 327 à 332 et le tableau 89 des règles Th-Bât (avec le point de l'éq. 332 plus bas) ;
  - **vitrage et DH** : plus de vitrage, moins de DH à ratio d'ouverture égal (surface ouvrante = ratio × surface
    de baie). À confirmer sur un logiciel réglementaire (cas 15 / 25 / 40 %), puis à expliquer dans une brique ;
  - est et ouest : une façade vitrée à l'est donne un peu plus de DH qu'à l'ouest (+ 3 %) ; à vérifier sur le
    moteur, peut-être lié à R3 ;
  - R2, hystérésis des brasseurs : à vérifier sur Sète (gestion par thermostat) ;
  - R4 : citations du confort adaptatif (fiche 3.1 et 13.5 dans le code, fiche 4.5 dans `hypotheses.csv`) à
    harmoniser, texte en main ;
  - R6 : domaine de la fiche 8.32 (hauteur sous plafond < 3 m, groupe non climatisé) non contrôlé dans la saisie ;
  - relecture des modules restants : `apports.py`, `eclairage.py`, `bbio.py`, `meteo.py`, `scenarios.py`,
    `calendrier.py`, `masques.py` ;
  - capture du `README.md` (`docs/capture_interface_1.jpg`) : ancienne (0.9.1, DH 1 964), à refaire.
- **Prochaine correction (version à fixer) : entrées d'air trop fortes dans certains groupes** (0.9.10 :
  Sète traversant, chauffage + 46 à + 53 % ; `rsee.xml` jusqu'à + 45 %) : coefficients de pression des zones
  traversantes, partage entre façades, autoréglage et anti-retour, bilan par zone (hypothèses 66 et 92).
- Ouverture des baies (0.9.15) : l'outil suit le moteur, pas le texte de la fiche 5.13 (hypothèse 100), comme en
  0.9.9 (hypothèse 91). À revoir si une version du moteur ou de la méthode change : `OUVERTURE_COMME_LE_MOTEUR`.
  Reste en Th-D 4 à 16 % sous le moteur, faute de la bonne température (θop 0,3 à 0,6 °C trop bas). DH de H2a :
  − 29 → − 35 % en médiane (DH faibles).
- **Protections face au guide Actibaie** (0.9.13) : sur la boîte en H3, les volets ne gagnent que 11 à 13 % de DH
  (guide : environ la moitié). Ni la fermeture des protections (identique au moteur à Paris) ni le passage d'air
  (éq. 239, même forme que le moteur) ni la règle d'ouverture n'en sont la cause. Les écarts « Typo_PM » et
  « Bbio » du guide comparent des produits différents, ou un moteur plus ancien : à ne pas corriger sans autre
  source.
- Guide Actibaie, plus tard : indicateur « Sw maximal » des baies (exigence de moyens, p. 44 : le guide écrit « au
  moins », c'est sûrement un maximum, à vérifier dans l'arrêté du 4 août 2021, absent de `_sources/`) ; aide à la
  saisie de la classe BR selon la distance à l'infrastructure (pp. 24-25), avec la saisie BR ; tendances de
  l'immeuble de 48 logements de Nantes (p. 29), à tester sur l'immeuble de départ en H2b, BR3, traversant ou non ; revue de
  l'enchaînement des calculs de baie avec le schéma des pp. 54-55. Stores vénitiens et BSO : voir plus bas.
- **DH face au moteur** : Sète − 33 à − 39 %, Nice A + 15 à + 27 %, Paris ± 6 %, avec ou sans la règle
  d'ouverture du moteur. Le θop de Th-D reste 0,3 à 0,6 °C sous celui du moteur : la cause est dans le bilan
  thermique du calcul Th-D (brasseurs de Sète par thermostat, ventilation Th-D, hypothèse 75 ; Φsh), pas dans
  l'ouverture des baies. Vérifier avec `python -m outils.comparer_horaires tous`.
- Ouverture en Th-B en saison de chauffage (groupe surchauffé) : non vérifiée sur le moteur (hypothèse 91).
- Φsh : flux solaire et voûte céleste des ponts thermiques (`O_Fsh_s_pt`, `O_Fsh_vc_pt` du moteur ; fiche 5.19).
- Th-D : débit de ventilation hors occupation du moteur plus faible (hypothèse 75).
- Apports des usages 7 % sous ceux du moteur (part variable selon le mois : pertes récupérées ?) ; éclairement
  naturel 20 à 80 % au-dessus (`O_Einat`).
- Variantes Th-B sans soleil des sorties horaires (`Th_B_Impact_Ss_Apports_Sol_*`) et mode Th-C : non exploités.
- **Interface, suites de la 0.9.0** :
  - fait en 0.9.0 : contrôle visuel dans un navigateur et capture du `README.md` ; balcons et casquettes ;
    comparaison de deux variantes ;
  - **appartement dans un immeuble** (vu en 0.9.1) : **fait en partie en 0.9.16**, parois adiabatiques (façades,
    toiture, plancher bas ; hypothèse 101). Reste : coefficient b (local non chauffé, cage d'escalier), inertie
    propre des parois adiabatiques (aujourd'hui donnée par la classe), et un bâtiment de départ « appartement
    intermédiaire » dans `donnees/batiments/` ;
  - saisies restantes : masque lointain (immeuble en face), joues et loggias, Sw2, gestion des brasseurs par
    thermostat (à attendre le calage du DH de Sète, voir plus bas), plusieurs groupes (traversant et non
    traversant). Le Uw horizontal ne concerne pas la boîte (pas de baie en toiture) ;
  - briques à écrire (non faites en 0.9.6, version à fixer) : bilan des flux d'une journée (baies, parois, ventilation, apports, inertie),
    effet des protections mobiles, rafraîchissement nocturne, Bbio max et ses modulations, brasseurs d'air,
    effet d'un balcon selon l'orientation ;
  - comparaison : superposer la référence sur les graphiques des briques (aujourd'hui : un tableau d'écarts) ;
  - ouvrir une étude (RSET) dans l'interface, avec `outils/lire_rset.py` ;
  - couleurs des graphiques : passer le validateur de palettes (daltonisme) quand `node` est disponible ;
  - semaine chaude : les protections restent baissées à 75 % jour et nuit sur la boîte de départ ; à expliquer
    dans la brique ou à vérifier dans `moteur/protections.py` ;
  - brique DH : le dernier jour de la période de confort adaptatif est incomplet, son maximum extérieur chute sur
    le graphique ;
  - temps de calcul : 15 s avec les infiltrations et 10 s sans sur le poste chargé (25 s avant la 0.9.0) ; voir
    le point « temps de calcul » plus bas.
- **Niveaux d'enveloppe, suites de la 0.9.2** :
  - 6 opérations seulement : refaire `donnees/typologies_logements.csv` avec les RSEE du calage (0.9.8), et
    séparer collectif et maison individuelle quand ce second usage arrivera (0.9.14) ;
  - montrer le graphique `docs/graphique_pedagogique_logements.png` (ou son équivalent interactif) dans
    l'interface, par exemple dans une brique ou la page d'accueil (non fait en 0.9.6) ;
- **Validation, suites de la 0.9.8** (table `_resultats/validation.csv`, détail dans `docs/audit.md`) :
  - études : 26 fichiers dans `../_RSEE`, dont 14 sans logement collectif (bureaux, maison individuelle) ; il
    reste 5 bâtiments distincts (Paris et Hébert sont deux versions du même, Sète en a trois, Nice A trois) :
    il en faut d'autres, ou l'extraction OPEE, pour « plus de 10 » ;
  - froid en H3 : 1,2 à 3,8 fois celui des études (médiane 2,1), premier écart du Bbio à Nice et à Sète ;
  - chauffage : 11 % sous les études en médiane (de − 34 à + 7 %) ; infiltrations d'hiver de l'outil à 15 à
    44 % de l'indicateur `H_V_Def_Hiver` (entrées d'air non comptées, hypothèse 67) ;
  - ventilation : `H_Vent_Hiver` des études vaut 0,1397 × `Qv_occ_BBIO` : **expliqué en 0.9.11**, c'est l'éq. 382
    de la fiche 6.1 (1006 × 0,5 / 3600, débit en m³/h, 1 kg/m³), un indicateur de sortie et non le bilan du
    groupe (éq. 333, 0,34 par m³/h, comme l'outil) ;
  - DH de H2a : 31 à 37 % sous l'étude dans quatre groupes sur six, aux DH faibles (77 à 308 °C.h).
- **Pédagogie, suites de la 0.9.6** :
  - course solaire : latitude et longitude fixes (46,5° N, 2,5° E) ; les prendre selon la zone climatique. Depuis
    la 0.9.16, la course est aussi dessinée dans le ciel ; vue du sud-ouest ou du sud-est (sous 30°), son plan est
    vu presque par la tranche : elle se projette en un trait étroit et le soleil de 16 h paraît posé sur la toiture
    (géométrie exacte, peu lisible). Vues du nord : arc bien ouvert. Pistes : regard plus haut (45 à 60°) pour le
    seul soleil, ou étiquettes d'heures sur la course ;
  - dessin (0.9.16, suites) : ombre des balcons et casquettes sur les baies (aujourd'hui : ombre de la boîte au
    sol seulement) ; heure du soleil dessiné réglable : **fait en 0.9.16** (curseur 6 h à 20 h, pas de 2 h) ;
    ombre portée seulement sur le sol, pas sur un bâtiment voisin ;
  - brique DH (0.9.16, suites) : le zoom passe par Streamlit (`on_select`), donc un nouveau calcul de la page à
    chaque cadre tracé (rapide : les résultats sont en cache) ; un graphique Altair composé (`alt.vconcat` de
    couches) se lierait sans aller-retour, mais Streamlit le fait grandir sans fin (version 1.66) : à reprendre
    si une version de Streamlit le corrige. La molette zoome encore à l'intérieur de la fenêtre ;
  - le glossaire Notion est lié par l'identifiant de chaque page (`interface/textes/glossaire.csv`) : une page
    ajoutée dans Notion doit y être ajoutée à la main ;
  - écart avec le calcul précédent : gardé pour la session seulement, sur le Bbio et le DH (pas sur les autres
    indicateurs des briques).
- **Bâtiments en CSV, suites de la 0.9.4** :
  - fait en 0.9.8 : export du bâtiment affiché en CSV, bouton « Télécharger ce bâtiment » (forme, site, baies,
    confort d'été ; l'enveloppe vient du niveau) ; à trancher : garder aussi une enveloppe retouchée à la main
    (la lecture des CSV de départ refuse aujourd'hui les 13 saisies d'enveloppe) ;
  - ouvrir un CSV de bâtiment depuis l'interface (dépôt de fichier) : nécessaire une fois l'outil en ligne, où
    l'utilisateur ne peut pas écrire dans `donnees/batiments/`.
  - ponts thermiques : le ψ moyen des études couvre tous les ponts, la boîte ne compte que les rives des
    planchers (hypothèse 88) ; une longueur de ponts par m² habitable, tirée des mêmes études, serait plus juste.

- **Ordre des versions revu le 14/11/2026** (deux fois) : « Cas de référence » intercalé en 0.8.10 ; « Protections
  et ouvertures » passe de 0.9.4 à 0.8.12, avant le DH (0.8.16) et l'interface (0.8.18) ; le numéro 0.9.4,
  libéré, est repris le 15/11/2026 par « Pédagogie » ; « Infiltrations » ajouté en 0.8.14. Raison : le besoin de froid de l'outil vaut plusieurs fois celui des études, si bien que ni le Bbio
  ni le DH ne sont exploitables sans ces modules. `CHANGELOG.md` (0.8.8 et avant), `docs/audit.md` (0.8.8 et avant)
  et les commentaires du code citent encore les anciens numéros : 0.9.4 pour les protections, 0.8.10 pour le DH,
  0.8.12 pour l'interface. Depuis : DH en 0.8.16 (fait), interface en 0.8.18.
- **Seuils de la gestion automatique des protections** (`gpm_auto_...` de `donnees/hypotheses.csv` : 10 000 lux,
  26 et 24 °C) : valeurs de l'outil, absentes de l'annexe et des fichiers d'étude. À lire dans Climawin ou
  Pleiades (écran de la gestion automatique des volets), puis à corriger. Concernent Sète et Nice.
- 0.9.8 : stores vénitiens (20 baies sur 80 à Nice, lues sans protection), seconde protection mobile, gestion
  automatique de l'ouverture des baies.
- 0.9.8 : éclairage : les protections fermées réduisent la lumière naturelle (fiche 5.10, éq. 235 à 237) ; l'outil
  calcule encore Becl baies nues (écart actuel aux études : 0,1 kWh/m²).
- 0.9.8 : **DH face aux études** (voir `docs/audit.md`, 0.8.16) : 35 à 41 % trop bas à Sète (brasseurs de nuit
  en gestion par thermostat), 28 % trop haut sur le groupe non traversant de Nice. À examiner avec des sorties
  horaires du même calcul que le RSET.
- 0.9.8 : ventilation du calcul Th-D : système du projet (débits, échangeur, surventilation mécanique) au lieu du
  débit du Bbio sans échangeur (hypothèse 75).
- 0.9.8 : chauffage du calcul Th-D : émetteur conventionnel du Bbio, faute du système du projet ; relances du
  chauffage (fiche 8.5, tableau 92), sans effet attendu sur le DH.
- 0.8.18 : saisie du caractère climatisé du groupe (`Groupe.climatise`), pour le DH max.
- 0.9.8 : ouverture des baies la nuit : la fiche 5.13 ne décrit le réglage qu'en journée (7 h à 23 h) ; l'outil
  garde la position du soir (hypothèse 59), ce qui pèse sur le rafraîchissement nocturne.
- 0.9.8 : **indicateur d'infiltrations d'hiver** (`H_V_Def_Hiver`) : celui des études vaut 3 à 6 fois la moyenne de
  janvier et février de l'outil, alors que le chauffage, lui, est proche. Pistes : les entrées d'air du projet
  gardées dans le calcul du Bbio (un essai hors moteur remonte l'outil à 43 à 77 % de l'indicateur) ; la définition
  même de l'indicateur, que la version texte de l'annexe ne donne pas ; le tirage thermique sur toute la hauteur
  de la zone. À trancher avec une sortie horaire d'un moteur, ou une étude sans entrée d'air.
- 0.9.8 : bilan aéraulique par zone (une pression commune à tous les groupes, échanges par le hall), au lieu d'un
  bilan par groupe ; sans effet sur les cinq études, qui n'ont qu'un groupe par zone.
- 0.9.8 (ou 0.8.18 si l'interface le demande) : **temps de calcul d'une étude** (800 composants, deux groupes :
  10 à 20 s pour le Bbio, autant pour le DH). Profil mesuré en 0.8.17 sur l'étude de Paris : équilibre de pression
  des infiltrations 35 % (`infiltrations.equilibre` : 62 évaluations du bilan par heure, en Python) ; rayonnement
  reçu par chaque paroi 30 % (`solaire.environnement_proche`, appelé 1 105 fois : chaque baie est recalculée par
  les sollicitations, les protections et l'éclairage) ; protections mobiles 8 % ; modèle du groupe 4 %. Pistes :
  résoudre l'équilibre par une méthode de Newton ou en numpy, calculer le rayonnement une fois par composant.
  Fait en 0.9.0 : équilibre de pression par fausse position bornée (cinq fois moins d'évaluations du bilan). Reste, sur la boîte :
  ouvertures et protections mobiles (15 % du temps), boucle horaire de `calculer_besoins`.
- Fait en 0.8.17 : calcul d'une heure du groupe en deux temps (`preparer_pas`, `resoudre_pas`) ; gain de 10 à 15 %
  sur un groupe simple, nul sur une étude.
- 0.9.8 : baies sur un espace tampon (coefficient b et soleil), aujourd'hui lues comme donnant sur l'extérieur.
- 0.9.8 : U des baies en hiver : l'indicateur `Hg_es_hiver` des études est 1 à 15 % sous la somme des A × U sans
  protection de l'outil (protections fermées la nuit ?). (Ventilation `H_Vent_Hiver` : expliquée en 0.9.11,
  indicateur de l'éq. 382.)
- 0.9.8 : masques par tranches azimutales : les études donnent le même horizon à toutes les orientations d'un
  bâtiment, alors que la fiche 3.2 compte les tranches depuis la normale à la paroi (hypothèse 7) : vérifier la
  convention des logiciels.
- 0.9.8 : débit de ventilation du Bbio : les études donnent environ 1,2 à 1,5 m³/h par m² habitable en occupation
  (`Qv_occ_BBIO`), à comparer au débit moyen de l'hypothèse 39.
- 0.8.18 : saisie de l'exposition au bruit (BR1 à BR3) et de la hauteur sous plafond moyenne, pour le Bbio max.
- 0.9.8 : infiltrations par la perméabilité de l'enveloppe (nulles pour l'instant) ; relances du
  chauffage avant l'occupation (fiche 8.5) ; humidité de l'air (terme Cv.ω de Hg_ei, éq. 333).
- 0.8.12 : sans protections mobiles ni ouverture des baies, le besoin de froid est surestimé (voir `docs/audit.md`,
  résultats de la 0.8.6) : à reprendre avec ce module, avant tout calage.
- 0.8.18 : saisie de Sw2 (défaut : nul, voir `docs/audit.md`, hypothèse 21), de l'inertie, des ponts thermiques et
  du Uw horizontal des baies de toiture.
- 0.9.8 : flux solaires et rayonnement froid des ponts thermiques (fiche 5.19, éq. 300 et 306), parois sur le sol
  (pour l'instant : U saisi × b), échanges entre groupes — à reprendre si le calage sur les RSEE le demande.
- 0.8.18 : saisie des brasseurs d'air dans l'interface (nombre, surface desservie, usage, gestion, débit et
  puissance du fabricant).
- 0.8.12 : protections mobiles (fiche 5.9, Rprot, hauteur de soleil corrigée, éq. 3 à 6) et ouverture des baies
  (fiche 5.13).
- 0.9.8 : comparer le rayonnement par orientation à un RSEE (sorties horaires, si disponibles).
- 0.8.18 : palette de l'interface (reçue le 12/11/2026, tirée de celle du HUB) :

  | Rôle | Nom | Code |
  |---|---|---|
  | Jaune HUB (accent4) | Sunflower Gold | `#FABD4A` |
  | Orange HUB (accent5) | — | `#FA9600` |
  | Texte | Noir | `#000000` |
  | Complémentaire | Cherry Blossom | `#FFB5C2` |
  | Complémentaire | Fresh Sky | `#00B0F0` |
  | Complémentaire | Wine Plum | `#6D2E46` |
  | Complémentaire | Deep Space Blue | `#283246` |

## Plan de bataille : informations au clic sur une paroi ou un vitrage (demandé le 20/11/2026 ; étapes 1 et 2 faites en 0.9.18, étape 3 en 0.9.20, étape 5 en 0.9.22, étape 4 et coupe du bilan en 0.9.24 : plan achevé)

But : cliquer sur une façade, la toiture ou une baie du dessin et lire ce qu'elle fait au bilan (pourquoi cette
paroi pèse sur le DH ou le Bbio). Le dessin est aujourd'hui une image SVG (`st.image`) : rien n'en remonte à Python.

| Étape | Contenu | Où | Difficulté |
|---|---|---|---|
| 1. Fiche par paroi, sans clic | Liste « Paroi examinée » (`st.selectbox` : 4 façades, toiture, plancher bas, baies de chaque façade) ; la paroi choisie est surlignée dans le dessin ; fiche : surface, U (ou Uw, Sw, Tl, protection), orientation, part vitrée, masque (balcon), adiabatique ou non | `interface/axonometrie.py` (argument `surlignee`), nouveau `interface/fiche_paroi.py` | faible |
| 2. Infobulles au survol | Chaque polygone du SVG reçoit un `<title>` (nom, surface, U ou Uw/Sw) : le navigateur l'affiche au survol, sans aller-retour. Contrôler que `st.image` garde les `<title>` (sinon `st.html` ou `st.markdown(unsafe_allow_html=True)`) | `axonometrie._Scene.polygone` (attribut `titre`) | faible |
| 3. Grandeurs calculées par paroi | Pour la paroi choisie, sur l'année et sur la semaine la plus chaude : rayonnement reçu (kWh/m², `solaire.environnement_proche`), flux solaires transmis (`solaire.flux_solaires_baie`, `flux_solaires_paroi`), déperditions H × (θi − θe), part des protections baissées et des baies ouvertes. Calcul à part, après celui du groupe, avec les séries horaires déjà produites (θi), mis en cache par boîte | nouveau `moteur/bilan_paroi.py` (sans dépendre de l'interface) ; colonnes ajoutées à `interface/calcul.py` | moyenne |
| 4. Part dans le DH | Apports de la paroi pendant les heures qui comptent des DH, rapportés aux apports totaux de ces heures (une part, pas une décomposition exacte : le modèle n'est pas linéaire) ; à défaut, DH recalculé sans la paroi (paroi adiabatique ou baie protégée) : écart exact, un calcul par paroi | `moteur/bilan_paroi.py`, brique « Ce que fait cette paroi » | moyenne à forte |
| 5. Clic dans le dessin | Composant Streamlit (`st.components.v2`, HTML + JS) qui affiche le SVG et renvoie l'identifiant du polygone cliqué ; remplace la liste de l'étape 1 (gardée pour le clavier et l'accessibilité) | nouveau `interface/composants/dessin_cliquable/` | moyenne (composant à maintenir) |

Ordre proposé : 1 et 2 ensemble (fait en 0.9.18 : fiche sous le dessin ; `st.html` retire les SVG, le dessin passe par `st.markdown(unsafe_allow_html=True)`), puis 3 (fait en 0.9.20 : bilan sous la fiche, périodes selon les calculs lancés), puis 5 (fait en 0.9.22 : composant inline `interface/dessin_cliquable.py`, liste gardée) et 4 avec la coupe du bilan (0.9.24). Choix du 22/11/2026 pour la 0.9.24 : coupe seule (pas de plan), pignons en une flèche ; variante « sans la paroi » : baie remplacée par le mur de sa façade, paroi opaque adiabatique ; part des flux affichée dans la coupe, variante exacte au bouton, pour la paroi choisie seulement. Contrôles : somme des flux par paroi = flux du
groupe à 0,1 % près ; test de l'identifiant cliqué ; capture avant / après dans Chrome. Points à trancher : afficher
la fiche sous le dessin ou dans une brique ; grandeurs du Bbio (année moyenne) ou du DH (année caniculaire), ou les
deux selon le calcul choisi.

## Relecture indépendante de la 0.9.8 : points inscrits en 0.9.11 (sans action immédiate)

Détail dans `docs/audit.md`, 0.9.11.

- Infiltrations (fiche 5.6) : un Pib par groupe au lieu d'un par zone avec hall (éq. 167-170) ; double flux
  sans échangeur en Th-D (éq. 154-166, hypothèse 75) ; planchers bas exclus et murs contre le sol comptés en
  façade ; humidité ignorée dans les masses volumiques (< 0,5 %) ; Cp au-delà de 50 m absent du tableau 23.
- Indicateur `H_V_Def_Hiver` des études : calculé avec le système réel (simple flux) ? À vérifier sur un RSEE
  ou une sortie horaire avant d'en tirer une conclusion.
- Caractère traversant d'hiver (0.9.11, `Is_Traversant` de la zone) : à confirmer sur une sortie horaire du
  moteur d'une étude où il diffère du traversant d'été (Saint-Ouen, Vélizy cage B).
- Ventilation hors logement : la fiche 6.2 (§ 6.2.3.2.2.1) impose qmax en occupation et qmin en inoccupation ;
  `groupe.debit_ventilation` ne traite que le logement (la zone n'admet que le logement collectif).
- Valeurs Ams par défaut (2 / 2,5 / 3, règles Th-Bât, tableau 89), non vérifiables dans l'annexe : en Th-D,
  l'inertie séquentielle ne joue que si Ams < Amq ; sinon le choix de classe est sans effet sur le DH. À
  vérifier à la relecture de `dh.py`, tableau 89 en main.
- Éq. 332 : elle écrit ΔCm,a-s, la nomenclature ΔCm,a-q ; le code suit l'équation. Si le moteur suit la
  nomenclature, l'inertie longue serait environ doublée en Th-D (DH seulement).
- ΔR < 0 ramené à 0 (`groupe.py`, inertie) : à documenter dans `docs/audit.md`.
- Surface des baies : Abaies vient de `surface_baies_m2`, Hg_es de la somme des baies ; contrôler qu'elles
  concordent, ou calculer Abaies comme Σ des baies.
- Points mineurs (≤ 1 % chacun) : φsys,rad perdu par les baies (0,5 %) ; Hg_ei = 0,34 × débit au lieu de
  qm·(Ca + Cv·ω) (± 1 %) ; flux solaires des ponts thermiques omis (éq. 345, voir Φsh) ; débit Bbio moyen au
  lieu du grand débit horaire (< 1 %).
- Protections et ouvertures (fiches 5.9 et 5.13) : seconde protection (éq. 198 à 201) ; horloge des volets
  automatiques (éq. 182 : par défaut ouverts les nuits d'hiver) ; facteur solaire avec protection tout en Sw1 ;
  éclairage artificiel calculé baies nues ; seuil de vent automatique égal au seuil manuel ; stores vénitiens
  (éq. 194 et suivantes, seuil de vent propre) ; gestion automatique des ouvrants (éq. 246-247) ; aération
  par les baies (éq. 256).
- Figure 35, cellule « dérogation avec détecteur, été frais, Ecl1 » lue 30 000 lux sur un scan flou : à
  confirmer sur un exemplaire net de l'annexe (Guillaume).
- Solaire : γ' (éq. 3-6, utile aux stores vénitiens) ; arbres à feuilles caduques ; espaces tampons ; toiture
  végétalisée (éq. 293) ; Sf par défaut des parois opaques (règles Th-Bât, non vérifiable dans l'annexe).
- Sw2 par défaut nul (hypothèse 21) : sans effet sur les études, qui donnent Sw2 (`Sw2_sp_e`, environ 0,035 à
  0,046 pour Sw1 0,13 à 0,25, soit 15 à 20 % de Sw) ; l'essai à 0,2 × Sw ne change donc rien à la validation
  (le DH trop bas en H2a ne vient pas de là). Ne joue que dans l'interface : un défaut de 0,15 à 0,2 × Sw
  serait plus proche des études.

## Idées

- Suites de la critique de la page (0.9.32), priorité basse : virgule décimale et unité sur les curseurs
  (« 1.30 » → « 1,30 W/m².K ») ; contraste de l'orange `#FA9600` en texte (1,9 à 2,2:1 sur blanc ou crème) et de
  la courbe jaune de la température intérieure ; jauge du Bbio et du DH face à leur max ; référence en fantôme dans
  les graphiques des briques ; « −0,0 (−0 %) » écrit « inchangé » dans la comparaison ; bouton « Deploy » masqué
  (`client.toolbarMode`).
- Suites de la 0.9.34 : export de la comparaison des variantes (rendu d'atelier) ; balayage d'une saisie
  (« DH selon l'orientation ») ; plus de quatre variantes.
- Import circulaire ancien : importer `interface.fiche_paroi` en premier échoue (`fiche_paroi` → `briques` →
  `bilan` → `fiche_paroi`) ; `app.py` importe dans un ordre qui passe. À défaire en sortant `nombre` de
  `interface/briques/`.

- Masques lointains constitués d'arbres à feuilles caduques (fiche 3.2) : non traités en 0.8.2.
- Valeurs par défaut de l'absorption des parois opaques (règles Th-Bât, tableau 66 : 0,4 clair, 0,6 moyen, 0,8
  sombre, 1,0 noir) à proposer dans l'interface (0.8.18).

- Autres usages du classeur des scénarios (maison individuelle, bureaux…) : `outils/extraire_donnees.py` est prêt à
  recevoir d'autres onglets.
- Météo et Chaleur (vulgarisateur_DH) : son changement d'heure suit le calendrier civil de 2018, celui de la méthode
  est fixé aux heures 1 896 et 7 032. Écart à examiner.
