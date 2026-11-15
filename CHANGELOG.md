# Journal des versions — Explorateur Bbio / DH

Règle : `0.8.x` tant que l'outil n'est pas fonctionnel, `0.9.x` quand il fonctionne, `1.0` à la première version
annoncée et diffusée. Dernier chiffre **pair** = évolution, **impair** = correction.

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
