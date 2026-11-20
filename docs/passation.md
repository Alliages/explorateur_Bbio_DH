# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 20/11/2026

- Dernière version publiée sur `travail` : **0.9.8**, avec la **0.9.6** dans le même commit (les fichiers de la
  0.9.6 et de la 0.9.8 se mêlent dans `app.py`, `formulaire.py`, `saisie.py`). **0.9.9 à 0.9.13** prêtes, non poussées.
- **0.9.13** (prête, non poussée) : lecture du guide Actibaie *Les protections solaires dans la RE 2020* (PDF et
  note d'analyse dans `_sources/guide_protections_solaires_re2020.*`, hors dépôt). Correction des protections de la
  boîte (`saisie._conventions_protection`, hypothèse 99) : Typo_PM 1 au lieu de 0, Sw protégé d'un volet tout en
  Sw2 (store : 40 %). DH des bâtiments de départ − 9 à − 13 % (logement 70 m² 559 / 728 / 883, immeuble 454 / 601
  / 744 ; Bbio inchangé à ± 0,4) ; études (RSET) inchangées. `tests/test_tendances.py` : ordre des gestions sur
  le DH (H3). Écarts au guide inscrits (`docs/audit.md`, 0.9.13) : volets − 11 % de DH au lieu d'environ − 50 %,
  Typo_PM trop influente, Bbio pas rangé comme le DH ; piste : fermeture de nuit et ouverture des baies (éq. 239),
  à rapprocher du ratio d'ouverture Th-D trop faible. Feuille de route : types de protection 0.9.12, maison
  individuelle 0.9.14, diffusion 0.9.16. Tests : 372 réussis, 2 sautés.
- **0.9.11** (prête, non poussée ; 0.9.9 et 0.9.10 non plus) : relecture indépendante de la 0.9.8
  (`relecture_0.9.8.md`, à la racine, non suivie), mesurée face au moteur et aux études (`_resultats/mesures_0.9.11/`).
  Correction principale : écart de confort adaptatif nul en Th-B (`besoins.py`) ; froid face au moteur + 25 à
  + 189 % → − 34 à − 2 %, ouverture des baies + 5 à + 10 %, fin de saison de froid au jour 246 comme le moteur.
  Validation : H3 0 → 9 groupes sur 13 dans ± 10 % (froid 1,0 fois l'étude), 46 groupes 18 → 29, médiane du
  Bbio − 2 %. Autres : traversant d'hiver de la zone pour les infiltrations (`Groupe.traversant_hiver`, hypothèse
  95), store manuel par grand vent hors occupation, Q4Pa par défaut et bornes de Httf à la lecture des RSET,
  jointure du DH dans `outils/valider.py` (Vélizy comptait 3 fois : 46 groupes, pas 58). Gardés après mesure :
  facteur 1 de l'éq. 61, heure légale (identique au moteur), Sw2. Hypothèses 93 à 98. Écart restant : chauffage
  trop fort de certains groupes (entrées d'air). Bâtiments de départ : logement 70 m² Bbio 94,1 / 119,9 /
  138,9, immeuble 50,1 / 60,5 / 67,9 (performant / moyen / faible). Tests : 371 réussis, 2 sautés.
- **0.9.10** (prête, non poussée ; 0.9.9 non poussée non plus) : perméabilité à l'air des protections devant une
  baie ouverte (fiche 5.12, `Typo_Permea_PM`) ; entrées d'air du projet gardées dans les infiltrations du Bbio
  (hypothèse 92, remplace la 67 ; `Groupe.module_entrees_air_m3h`, lu dans `Entree_Air`). Face au moteur :
  chauffage à ± 6 % dans 4 groupes sur 6, DH de Paris à ± 6 %. Validation : H1a 4 sur 4 dans ± 10 %, mais
  chauffage trop fort dans certains groupes (Sète traversant + 50 %, `rsee.xml` jusqu'à + 45 %) : H2a 3 sur 6,
  H3 0 sur 13 ; 58 groupes : 18 dans la cible, médiane + 22 %. Feuille de route décalée (maison individuelle
  0.9.12, diffusion 0.9.14). Tests : 364 réussis, 2 sautés.
- **0.9.9** (comparaison horaire, lot L1 fait) : sorties horaires du moteur COMETH 2025.E1 dans
  `../_RSEE/Horaires` (Paris, Sète, Nice A ; modes Th-B, Th-C, Th-D ; 3,2 Go), appariées aux RSET de la
  validation (`ETUDES` en tête de `outils/comparer_horaires.py`). `outils/lire_horaires.py` lit les seules
  colonnes demandées (cache `_resultats/horaires_cache/`). `python -m outils.comparer_horaires tous` (≈ 5 min)
  écrit synthèse, mensuel et séries horaires dans `_resultats/horaires/`. Le moteur sort aussi `hg_ei`,
  `theta_eieq`, `fs1`, `fs3`, `phi_sl`, `phi_sh`, `phi_i/s/m` et `occupe` (résultats inchangés). Constats
  (`docs/audit.md`, 0.9.9) : (1) l'outil n'ouvre pas les baies à la mi-saison en Th-B (éq. 244), le moteur
  si : mi-saison trop chaude, saison de froid de 98 à 140 jours au lieu de 63 à 74, froid 1,8 à 3,6 fois trop
  fort ; (2) infiltrations d'hiver 1,5 à 3,5 fois trop faibles, ventilation du Bbio juste à 1-2 % : chauffage
  trop faible ; (3) Φsh des ponts thermiques absent ; (4) Th-D : même seuil, même DH, écart venant de la
  température (baies 31 à 52 % moins ouvertes).
- **0.9.9, correction décidée le 19/11/2026 : l'outil suit le moteur, pas le texte** (hypothèse 91,
  `moteur/ouvertures.py`, réglage `OUVERTURE_TH_B_COMME_LE_MOTEUR`) : en Th-B, hors période de refroidissement,
  règle générale de la gestion manuelle au lieu de l'éq. 244 (aucune ouverture) ; plafond « consigne − 1 °C »
  seulement en période de refroidissement ; rien hors occupation. Saison de froid de Paris identique au moteur ;
  Sète et Nice 85 à 93 jours (moteur 63 à 74). Bbio H3 + 20 → + 17 % (médiane des 13 groupes), H1a et H2a un peu
  plus bas ; DH inchangé. Fiabilité affichée mise à jour. Reste : ratio d'ouverture 23 à 64 % sous le moteur.
  Tests : 362 réussis, 2 sautés.
- Nouvelles études dans `../_RSEE` (Strasbourg et variantes) : la validation compte 16 études et 58 groupes
  (13 dans ± 10 %), non examinées. Table d'avant la correction : `_resultats/validation_0.9.8_avant_ouverture.csv`.
- **0.9.8** (validation, en partie) : `outils/valider.py` (`python -m outils.valider --dh`, table dans
  `_resultats/validation.csv`) sur `../_RSEE` et `_sources` : 10 études, 23 groupes, 5 bâtiments distincts ;
  9 groupes dans ± 10 % sur le Bbio (H2a 6 sur 6, H1a 2 sur 4 avec chauffage trop faible, H3 1 sur 13 avec froid
  environ 2 fois trop fort). Aucun coefficient ajusté. Parois à U = 0 lues adiabatiques (hypothèse 90 ; `rsee.xml`
  plantait). Bouton « Télécharger ce bâtiment » (`saisie.ecrire_batiment`) : forme, site, baies et confort d'été,
  sans l'enveloppe (règle des bâtiments de départ). Détail et points ouverts : `docs/audit.md`, 0.9.8.
- **Diagnostic des écarts** (Word, hors dépôt) : `_resultats/Ecarts_Bbio_DH_diagnostic_0.9.8.docx`. Constats
  clés : froid de H3 trop fort aussi sans soleil (2 à 6 fois) et surtout en mai, juin, septembre ; chauffage
  sans soleil juste à ± 6 % en H3 et H2a (lu dans `Ss_Apports_Sol_Bbio_*` des RSET, en points) ; janvier à 77-85 %
  de l'étude ; départ à 12 °C : + 1,6 des 3,8 kWh/m² manquants à Paris ; échangeur sans effet sur le froid.
  Plan en six lots (L1 instruments, L2 saison de froid, L3 ouvertures, L4 solaire, L5 hiver, L6 base et DH) ;
  données attendues D1 à D9 (d'abord sorties horaires du moteur et nouvelles études).
- **0.9.6** (pédagogie) : page d'accueil (`interface/accueil.py`, texte `interface/textes/accueil.md`), ouverte au
  lancement, sans calcul ; « Explorer la boîte » ou « Calculer » ouvre « Explorer » (clé de session `page`).
  Textes hors du code dans `interface/textes/` : `aides.csv` (cle;aide, clé du widget, lue par
  `interface.aides.aide`) et `glossaire.csv` (82 termes du Glossaire du confort, Notion, identifiant de page,
  site public `guillaume-meunier.notion.site`). `[[terme]]` ou `[[terme|texte]]` devient un lien (`lier`) ; un
  test vérifie que chaque terme cité existe et qu'aucun `help="…"` ne reste dans le code. Toute nouvelle saisie :
  une ligne dans `aides.csv` et `help=aide("clé")`. Briques : équation et « Ce qu'elle dit » visibles,
  « Pour aller plus loin » (`Brique.glossaire`), volet « Référence et code du moteur ». Dessin : course du
  21 juin au bord du sol (46,5° N), soleil de 16 h. Chiffres clés : écart avec le calcul précédent
  (`_retenir_calcul` dans `app.py`), part du max en dessous. Vu dans Chrome (logement 70 m², moyen → performant :
  DH 804 → 639 °C.h). Nouvelles briques non faites (voir `ROADMAP.md`).
- Écart trouvé : `donnees/typologies_logements.csv` a été arrondi dans le commit de la 0.9.4 (Uw 1,2 / 1,3 / 1,4,
  Sw moyen 0,40…) sans que les tests ni les chiffres de la 0.9.4 ci-dessous (DH 609 / 786 / 991) suivent : tests
  alignés en 0.9.6 ; à l'écran, le logement de 70 m² moyen donne DH 804 °C.h, performant 639.
- **0.9.4** : bâtiments de départ lus dans `donnees/batiments/` (un CSV par bâtiment, `champ;valeur;unite;
  description`, ligne `nom`, ordre alphabétique des fichiers ; mode d'emploi dans le `README.md` du dossier).
  `saisie.lire_batiment`, `lire_batiments` ; `BATIMENTS_DE_DEPART` est lu en fin de `interface/saisie.py`
  (la lecture contrôle chaque boîte avec `construire_projet`). Champ absent = valeur de `Boite` ; enveloppe,
  champ inconnu, valeur illisible, zone inconnue refusés avec fichier et ligne. Nouveau logement de 70 m²
  (= `Boite()`) : H1a, 7 × 10 m, baies 25 / 0 / 25 / 0 %, gestion manuelle motorisée ; l'immeuble suit (seule
  la forme diffère). Logement : Bbio 90,7 / 114,8 / 135,5 (max 91,0), DH 609 / 786 / 991 ; immeuble : Bbio
  48,7 / 58,2 / 65,8 (max 82,8), DH 511 / 675 / 859 (performant / moyen / faible). Vu dans Chrome. Toute
  nouvelle saisie de `Boite` doit aussi entrer dans les deux CSV (un test vérifie qu'ils sont complets).
  Versions revues : pédagogie 0.9.6, export CSV 0.9.8 (avec la validation), diffusion de la chaleur 0.9.14 (décalée en 0.9.10).
- **0.9.2** : trois niveaux d'enveloppe, « Performant », « Moyen » (à l'ouverture) et « Faible », lus dans
  `donnees/typologies_logements.csv` (`saisie.NIVEAUX_ENVELOPPE`, `CHAMPS_TYPOLOGIES` : colonne du CSV → champ de
  `Boite`). Choix « Enveloppe » sous « Bâtiment de départ » (`formulaire.choisir_depart`) ; départ =
  `boite_de_depart(bâtiment, niveau)`. Changer de niveau ne réécrit que les 13 saisies d'enveloppe ; changer de
  bâtiment réécrit tout avec le niveau gardé. Scripts et méthode : `outils/typologies/` (source hors dépôt,
  graphiques avec `matplotlib`, absent de `.venv`). Hypothèses 88 (ψ moyen sur les seules rives des planchers) et
  89 (6 opérations). Logement 70 m² : Bbio 78,5 / 99,1 / 116,3, DH 858 / 1 308 / 1 756 ; immeuble : Bbio
  46,6 / 54,9 / 63,1, DH 746 / 1 125 / 1 541 (performant / moyen / faible). Vu dans Chrome : passage à
  « Performant », curseurs à jour à l'écran, DH 858. « Pédagogie » passe en 0.9.4.
  `outils/typologies/valeurs_3_rset.py` : valeurs des 13 variables par groupe pour les 3 RSET « scénario 2 » de
  `_sources` (Nice A = version retenue, Paris et Sète = versions écartées) → `_resultats/valeurs_typologies_3_rset.csv`.
- **0.9.1** : choix du calcul, « DH » (par défaut), « Bbio » ou « Bbio et DH » (`formulaire.choisir_calculs`) ;
  seul le calcul demandé est lancé, chacun a son cache dans `app.py` (`_bbio`, `_dh`) ; `Brique.besoin` dit
  quel calcul une brique lit. Bâtiment de départ (`saisie.BATIMENTS_DE_DEPART`) : « Logement de 70 m² »
  (= `Boite()`) ou « Immeuble de 9 logements » (la boîte de la 0.9.0). Changer de bâtiment écrit la valeur de
  chaque widget (`formulaire.valeurs_des_widgets`). Effacer les clés ne suffit pas : à l'écran, les curseurs
  gardaient l'ancienne valeur, défaut que seul le navigateur montrait. Toute nouvelle saisie montrée en pour cent ou en
  entier doit être inscrite dans `CHAMPS_EN_POURCENT` ou `CHAMPS_ENTIERS`.
  Logement : Bbio 114,7 (max 78,0), DH 1 964 °C.h (max 1 250), hypothèse 87. Temps : 2 s par calcul (4 s les
  deux) sur un poste peu chargé.
- **0.9.0** : l'outil s'emploie de bout en bout (`streamlit run app.py`) : décrire une boîte, calculer,
  comprendre par briques, comparer deux variantes. **Non mis en ligne** : il faut un accord explicite et le lien
  Streamlit ; le dépôt est prêt (`README.md`, « Mise en ligne »).
  - Contrôle visuel fait dans Chrome ; défauts corrigés : hauteurs des graphiques (`interface/briques/
    graphiques.py` : la hauteur donnée à Streamlit comprend légende et axes), étiquettes de l'axonométrie,
    second bouton « Calculer ». Capture : `docs/capture_interface.jpg`.
  - `interface/comparaison.py` : `differences` (saisies changées), `ecarts` (sept indicateurs), `afficher`.
    Toute nouvelle saisie de `Boite` doit recevoir un libellé dans `LIBELLES` (un test le vérifie).
  - Balcons et casquettes : `Boite.debord_m`, `Boite.facades_debord` ; masque proche horizontal sur les baies ;
    `gabarit_baie` et `largeur_travee` communs au dessin et au calcul (hypothèse 85 de `docs/audit.md`).
  - `moteur/infiltrations.py` : pression d'équilibre par fausse position bornée (12 évaluations du bilan par
    heure au lieu de 62) ; résultats égaux à 12 chiffres ; étude de Paris inchangée.
- Immeuble de 9 logements (boîte de départ de la 0.9.0) : Bbio 62,3 pour un maximum de 69,8 ; DH 1 777 °C.h
  pour 1 250. Temps de calcul en 0.9.0 sur le poste chargé : 15 s (25 s avant), 10 s sans infiltrations.
  Streamlit 1.67 dans `.venv`.
- 0.8.17 : relecture sans effet sur le calcul. 0.8.16 : `moteur/confort.py`, `moteur/dh.py`,
  `calculer_besoins(mode="th_d")`, règles Th-D des protections et des ouvertures, brasseurs lus dans les RSET,
  `outils/comparer_reference.py --dh`.
- Tests : `python -m pytest` → 371 réussis, 2 sautés (classeurs de `_references/` absents), en moins d'une
  minute sur un poste peu chargé.
- `docs/audit.md` : sections 0.8.16 (hypothèses 75 à 84), 0.8.17, 0.9.0 (constats du contrôle visuel, temps de
  calcul, hypothèses 85 et 86) et 0.9.1 (temps par calcul, hypothèse 87).
- **Résultat à garder en tête** : période de confort adaptatif et DH max identiques aux études ; DH de − 2 à
  + 13 % sur les quatre groupes sans brasseurs, + 14 à + 28 % à Paris et à Nice avec brasseurs, − 35 à − 41 % à
  Sète.
- **Deux hypothèses à faire valider** : ventilation du calcul Th-D sans échangeur (75) ; catégorie 2 du DH max =
  climatisé et BR2 ou BR3 (76).
- Bbio : chauffage 2 à 26 % sous les études, froid 1,7 à 4 fois au-dessus (inchangé depuis la 0.8.14).

## Prochaine étape

« Push » des 0.9.9 à 0.9.11, puis mise en ligne sur accord. Ensuite : entrées d'air trop fortes (chauffage de
Sète traversant, `rsee.xml`, Vélizy, Saint-Ouen), ouverture des baies en Th-D encore 16 à 32 % sous le moteur, Φsh,
relecture des modules restants (`relecture_0.9.8.md`, § 1), chaque fois vérifiés avec
`python -m outils.comparer_horaires tous` ; autres études ou OPEE ou les nouvelles briques (version à fixer). Écrire une brique : un fichier dans
`interface/briques/` (voir `base.py`) et une ligne dans `__init__.py`. Deux points vus à l'écran et notés dans
`ROADMAP.md` : protections baissées à 75 % jour et nuit pendant la semaine chaude ; dernier jour incomplet sur le
graphique de la brique DH.

## Pour reprendre

```powershell
cd explorateur_Bbio_DH
git checkout travail
git pull
.\.venv\Scripts\Activate.ps1
python -m pytest
streamlit run app.py
python -m outils.comparer_reference "_sources\paris_scenario2_resultats_groupes_occ.xml" --dh
```

## Fichiers locaux nécessaires (hors dépôt)

- `_sources/` : annexes de l'arrêté, annexe à l'article R. 172-4 (trois versions), règles Th-Bât (PDF), et les
  études de référence : `paris_…`, `sete_…`, `nice_…` (XML et classeur horaire, PDF pour Paris),
  `Fichier source + RSET 04-2026` (Nice A) et le dossier « Annexe 3 … BAT B_V2 » (Nice B).
- `../_RSEE` (à côté du dépôt) : autres études RE2020, pour la validation (0.9.8) ; `../_RSEE/Horaires` :
  sorties horaires du moteur COMETH (0.9.9).
- `../bon résultat.csv`, `../bon résultat_H3_tracc.csv` : sorties horaires d'un moteur Th-BCE (référence du DH).
- `_references/` : les deux classeurs officiels (absents de ce poste : deux tests sautés).
- Tout dossier commençant par `_` est exclu de git (`.gitignore`).
- Lecture des PDF : `pdftotext` est disponible, pas `pdftoppm` (les tableaux en image ne peuvent pas être relus).

## En attente de Guillaume

Chapitre V de l'annexe à l'article R. 172-4 (catégories de contraintes extérieures, hypothèse 76) ; seuils de la gestion automatique des volets, à lire dans Climawin ou Pleiades
(hypothèse 57) ; accord et lien Streamlit pour la mise en ligne de la 0.9.0, extraction OPEE (0.9.8), accord DHUP
(avant 1.0.0), seuils du plan de contrôle.
