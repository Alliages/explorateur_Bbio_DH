# Journal des versions — Explorateur Bbio / DH

Règle : `0.8.x` tant que l'outil n'est pas fonctionnel, `0.9.x` quand il fonctionne, `1.0` à la première version
annoncée et diffusée. Dernier chiffre **pair** = évolution, **impair** = correction.

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
