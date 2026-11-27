# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 26/11/2026

- **0.9.38** (poussée sur `travail` avec les 0.9.36 et 0.9.37, `3678f8d` ; tests : 407 réussis, 2 sautés) : boussole dans le dessin
  (`axonometrie.dessiner_boussole`, clic → session « vue »), curseur de l'heure au-dessus, boîte « Indicateurs »
  (`st.popover` + formulaire, session « indicateurs ») et cartouche dans une bande à droite du dessin
  (`BANDE_DROITE`), registre `interface/indicateurs.py`, interrupteur « adiabatique » de la fiche
  (`formulaire.CLE_FICHE_ADIABATIQUE`), couleurs des températures (seuil en couche à part,
  `graphiques.lignes_des_series`). Vérifié dans le navigateur : clic sur la boussole, choix des huit indicateurs,
  toiture adiabatique depuis la fiche, seuil à 1 px dans les deux graphiques.
- **Prochaine version : 0.9.40** (`ROADMAP.md`) : masques sur les façades, choix des fichiers météo.
- **Étude « compacité × traversant »** (27/11/2026) : plan révisé dans `docs/plan_etude_compacite_traversant.md`
  (non suivi par git), lots L0 à L8 (0.9.46 à 0.9.61 proposés, après les 0.9.40 à 0.9.44), chacun découpé en
  parties lancées une par une. Première étape : L0.1, réponses de Guigui aux questions du § 10.
- **0.9.37** (poussée avec la 0.9.38 ; tests : 405 réussis, 2 sautés) : 27 hypothèses lues à chaque heure
  devenues constantes de `infiltrations.py`, `protections.py`, `ouvertures.py` (appels à `hyp()` par calcul DH :
  152 294 → 3 081) ; séries de la boucle de `besoins.py` en listes. Résultats identiques au bit près (banc de 22
  sorties horaires, hors dépôt). Gain estimé 2 à 3 % seulement, non mesurable sur le poste (même code : 1,4 à
  3,6 s) ; l'estimation de 10 à 15 % était fausse (`docs/audit.md`, 0.9.37). Pour aller plus vite : numba ou
  plusieurs variantes à la fois (`ROADMAP.md`, « Vitesse du calcul, suites »).
- **0.9.36** (poussée avec la 0.9.38 ; tests : 405 réussis, 2 sautés) : caractère traversant déduit des baies (règle des 75 %,
  `Boite.traversant_impose`, hypothèse 106) ; résultats des bâtiments de départ inchangés. Feuille de route
  décalée : calcul plus rapide 0.9.37, saisies et dessin 0.9.38, masques 0.9.40, diffusion 0.9.42. Menu « Forme » vérifié
  dans le navigateur (verdict, interrupteur libre et grisé).
- Mesure du 23/11/2026 : DH du logement de départ en 3,6 à 4,5 s, dont 90 % dans la boucle horaire. Numba évalué
  (compatible, × 6 à 10 si toute la boucle est portée), Rust écarté ; chiffres dans `ROADMAP.md`.
- **0.9.34** (poussée sur `travail` avec les 0.9.30 et 0.9.32 ; tests : 403 réussis, 2 sautés) : note de conception
  validée le 22/11/2026. Variantes A à D (`interface/variantes.py` ; session « variantes », « lettre_reference »,
  « depart_calcule ») à la place de la référence unique : « Garder en A », pastilles dans la barre des résultats,
  un clic remet la saisie (`formulaire.remettre`) et le calcul, menu de la référence et des retraits. Synthèse
  « Bbio et DH ensemble » (`interface/synthese.py`). Saisies de la paroi dans sa fiche (`formulaire.
  saisir_dans_la_fiche`, clés « fiche_<champ> » recopiées dans le menu, puis `st.rerun()` du fragment). Résultats
  du moteur inchangés. Vu dans Chrome (A puis B gardées, retour à A, synthèse face à A, Uw changé dans la fiche,
  menu des variantes). Le serveur Streamlit ne recharge pas les modules importés modifiés : le relancer.
- **0.9.32** (poussée avec la 0.9.34) : page « Explorer » reprise après
  une critique de conception (25/40 ; rapport dans `.impeccable/critique/`, hors dépôt à décider). « Calculer »
  collé en bas du menu ; barre des résultats collée en haut (`barre_resultats` : Bbio, DH, écart à la référence ou
  au calcul précédent, état périmé, boutons) ; résultats périmés pâlis (`STYLE_PERIME`) ; surface, paroi examinée et
  fiche à droite du dessin (deux colonnes dans le fragment `_dessin`), « Ce qu'elle fait » dessous ; titres des
  volets résumés (`formulaire.resumes`, volets à clé), « Baies » ouvert. Styles dans `app.py` (`STYLE`) : le
  `sticky` se pose sur l'enveloppe `stLayoutWrapper` du conteneur (sélecteur `:has`). Résultats du moteur inchangés.
  Vu dans Chrome (1440 × 900 : défilement, saisie périmée, référence puis calcul, Bbio et DH, clic sur les baies).
  **Suite : 0.9.34**, à concevoir avant de coder (bande de variantes, briques côte à côte, saisies dans la fiche) ;
  points P2 de la critique dans `ROADMAP.md`, « Idées ».
- **0.9.30** (poussée avec la 0.9.34) : audit du code entier (sept constats,
  `docs/audit.md`, 0.9.30) ; résultats du moteur inchangés.
  - Constat 1 : `tests/test_non_regression.py` fige le Bbio et le DH des six boîtes de départ et de l'exemple du
    README (± 0,05 point, ± 0,5 % de DH). Une modification voulue des résultats doit y mettre à jour les valeurs.
  - Constat 2 : `simuler_groupe()` supprimée de `moteur/groupe.py` ; ses tests passent par `calculer_besoins()`
    ou `pas_groupe()` ; contrôle de l'efficacité de l'échangeur ajouté à `calculer_besoins()`.
  - Constat 3 : `requirements.txt` épinglé sur les versions des tests.
  - Constat 4 déjà traité par la 0.9.29. Constats 5 à 7 : `besoins.temperature_sonde()` et `calcul.calculer()`
    supprimées, docstring de `valider.lister_etudes()` corrigée.
  - Tests : 400 réussis, 2 sautés (3 min 17).
- **0.9.29** (poussée sur `travail`) : calcul 1,16 fois plus rapide, résultats identiques au bit près
  (`moteur/infiltrations.py` : bilans des bornes gardés ; `moteur/ouvertures.py` : secteurs traversants, Cpr,
  hystérésis). Vectorisation numpy essayée et écartée (la boucle horaire lit l'heure précédente ; numpy plus lent
  sur 2 à 9 éléments). Constat : DH sensible à 0,2 % près à une perturbation de 1e-12 (seuils). Détail :
  `docs/audit.md`, 0.9.29 ; suites dans `ROADMAP.md`. Tests : 392 réussis, 3 sautés.
- Version précédente sur `travail` : **0.9.27** (commit `b6c4eb2`, 22/11/2026). Avant : **0.9.25** (commit
  `652b972`), avec les 0.9.18 à 0.9.24 dans le même commit. Avant : 0.9.16 avec la 0.9.15 (`dee10e0`), 0.9.13
  avec les 0.9.9 à 0.9.11 (`667d842`), 0.9.8 avec la 0.9.6 (`acab5fb`). `main` n'a pas bougé (0.9.4).
- **0.9.27** (poussée, `b6c4eb2`) : audit de la 0.9.25, faite dans claude.ai sans les études ni l'annexe III ;
  calcul inchangé (détail : `docs/audit.md`, 0.9.27).
  - Non-régression : bâtiments de départ identiques à la 0.9.15. L'exemple du `README.md` était périmé
    (Bbio 27,8, DH 1 981). **À relancer sur le poste** : `python -m outils.valider "..\_RSEE" "_sources" --dh` et
    `python -m outils.comparer_horaires tous`.
  - Relecture de `dh.py`, `confort.py`, `brasseurs.py`, `enveloppe.py` : R1 inertie séquentielle non monotone
    (nulle dès que Ams ≥ Amq) ; R2 hystérésis des brasseurs (effet faible sur la boîte) ; **R3 soleil des
    fichiers météo en retard d'une heure sur l'heure du calcul** (l'outil suit les fichiers ; le dessin montre le
    soleil astronomique) ; R4 citations du confort adaptatif. Tous à vérifier texte ou moteur en main.
  - Tendances de la boîte (H1a, H3) : sens attendu partout sauf deux signaux, plus de vitrage = moins de DH (la
    surface ouvrante suit la surface des baies ; à surface ouvrante égale, le DH monte) et est un peu au-dessus de
    l'ouest. Six tendances testées dans `tests/test_tendances.py`.
  - Fiabilité affichée (accueil, briques Bbio et DH) et `README.md` mis aux chiffres de la 0.9.15.
  - Tests : 392 réussis, 3 sautés ici (aucun RSET dans `_sources/`).
- **0.9.25** (poussée avec les 0.9.18 à 0.9.24) : correction du bilan en coupe, devenu exact.
  Conduction des parois opaques et des ponts vers la masse θmq, des baies vers les surfaces θs, rayonnement
  intérieur perdu par les vitrages compris : le reste du bilan est le stockage du modèle (l'ancienne lecture
  H × (θi − θe) faisait passer 13 kWh d'erreur pour du stockage sur la semaine chaude du logement faible sans
  protection). Lecture « Heure de pointe (Wh) » de la coupe (heure du soleil transmis le plus fort) ; fiche : pic
  du soleil transmis, conduction du modèle. Hypothèses 103 (corrigée) et 105. Résultats inchangés. Vu dans Chrome
  (logement faible sans protection : baies sud 976 Wh à 16 h le 11/08, 4 035 Wh gardés par la masse). Tests : 387
  réussis, 2 sautés. Suite : diffusion en 0.9.26.
- **0.9.24** (prête, non poussée, dans la même copie de travail que les 0.9.18 à 0.9.22) : étape 4 du plan
  « informations au clic », qui est achevé. Brique « Le bilan en coupe » (`interface/briques/bilan.py`, dessin
  `interface/coupe.py`) : coupe hors échelle, une flèche par poste proportionnelle aux kWh (soleil, parois, ponts
  thermiques, air en trois postes, apports internes, chauffage, froid), pignons en un cercle, masse ; périodes des
  calculs lancés ; tableau équilibré ; avec le DH, part de chaque poste dans la chaleur entrée aux heures de DH ;
  clic sur la coupe. Bouton « Mesurer l'effet de cette paroi » sous la fiche (`calcul.effet_paroi`,
  `construire_projet(…, sans=…)`). Moteur : sorties `hg_ventilation`, `theta_souffle`, `hg_ouvertures`,
  `phi_apports` ; `bilan_paroi.postes_du_groupe`. Hypothèses 103 et 104. Résultats inchangés (DH 732, Bbio 119,8).
  Logement moyen : sans les baies sud DH 994, sans toiture 615. Vu dans Chrome (trois périodes, clic sur la baie
  sud de la coupe, bouton). Tests : 387 réussis, 2 sautés.
- **0.9.22** (prête, non poussée, dans la même copie de travail que les 0.9.18 et 0.9.20) : étape 5 du plan
  « informations au clic ». Un clic sur un mur, des baies (ou leur protection) ou la toiture du dessin les choisit
  dans la liste « Paroi examinée » (fiche, contour orange, « Ce qu'elle fait »). Composant inline
  `interface/dessin_cliquable.py` (`st.components.v2`, événement `clic`), qui remplace
  `st.markdown(unsafe_allow_html=True)` ; clé `data-cle` sur chaque forme de `axonometrie.py`. La liste reste
  (clavier, parois cachées : façade de dos, plancher bas). Résultats inchangés. Vu dans Chrome (vues sud-ouest et
  nord-est : baies, toiture, pignon ; infobulles gardées). Tests : 383 réussis, 2 sautés. **Suite : 0.9.24**, coupe schématique du bilan et étape
  4 (choix arrêtés dans `ROADMAP.md`, plan de bataille) ; diffusion en 0.9.26.
- **0.9.20** (prête, non poussée, dans la même copie de travail que la 0.9.18) : étape 3 du plan « informations
  au clic ». `moteur/bilan_paroi.py` : bilan heure par heure de chaque baie et paroi opaque (soleil reçu et transmis,
  rayonnement froid, H × (θi − θe), fermeture, ouverture), sommes égales aux flux du groupe (hypothèse 102).
  `calculer_besoins` sort `rprot_baie_<rang>` ; `interface/calcul.py` rend `parois_dh` (semaine la plus chaude,
  confort adaptatif) et `parois_bbio` (année) ; tableau « Ce qu'elle fait » sous la fiche (`fiche_paroi.bilan`),
  lu dans le cache, seulement si la saisie n'a pas changé. Fiche : plancher sur le sol corrigé (U × surface).
  Résultats inchangés (DH 732, Bbio 119,8 ; Paris − 6,1 / + 6,9 %). Diffusion en 0.9.22. Vu dans Chrome ; tests :
  382 réussis, 2 sautés. Suite : étape 4, part de la paroi dans le DH.
- **0.9.18** (prête, non poussée) : étapes 1 et 2 du plan « informations au clic » (`ROADMAP.md`). Liste
  « Paroi examinée » sous le dessin (`interface/fiche_paroi.py` : `parois`, `fiche`, `infobulles`), paroi entourée
  en orange (pointillé si cachée), fiche en tableau ; infobulle (`<title>`) de chaque mur, baie et toiture. Le
  dessin passe par `st.markdown(unsafe_allow_html=True)` : `st.image` ne transmet pas le survol, `st.html`
  (DOMPurify, profil « html ») retire le SVG. Diffusion décalée en 0.9.20. Vu dans Chrome ; tests : 378 réussis,
  2 sautés. Suite : étape 3, grandeurs calculées par paroi (`moteur/bilan_paroi.py`).
- **0.9.16** (poussée avec la 0.9.15) :
  - **dessin** : course du 21 juin dans le ciel et au bord du sol, soleil de 16 h légale à sa hauteur (55,5°,
    59° à l'ouest du sud ; 46,5° N, 2,5° E), ombre de la boîte au sol, façades à l'ombre assombries, flèche du
    nord. Vu du sud-ouest, le plan de la course est vu par la tranche : un trait étroit, avec le soleil posé sur
    la toiture (exact mais peu lisible, pistes dans `ROADMAP.md`) ;
  - **heure du soleil** : curseur sous le dessin (6 à 20 h, pas de 2 h, 16 h par défaut), dans un `st.fragment`
    avec la vue. Le soleil de 6 h, encore sous l'horizon, est dessiné à 2° (« lever (6 h 15) »). L'ombre est
    coupée au bord du sol. Le soleil caché derrière la boîte est redessiné en contour pointillé ;
  - **orientation** par pas de 10° en azimut géographique (`libelle_orientation`, « 190° · sud ») ;
  - **parois adiabatiques** : les quatre façades, la toiture et le plancher bas (`Boite.parois_adiabatiques`,
    hypothèse 101). La paroi est absente du groupe et grise dans le dessin. Logement de 70 m² moyen : DH 732 →
    607 (pignons) → 499 (pignons, toiture et plancher bas) ;
  - **graphiques** : extérieur noir, seuil orange en pointillé, intérieur jaune. Brique DH heure par heure :
    boutons « Été entier », « Semaine la plus chaude », « Jour le plus chaud », et cadre tracé sur la bande des
    DH de chaque jour (`on_select` de Streamlit). Un `alt.vconcat` de couches s'élargissait sans fin dans
    Streamlit 1.66, et un domaine imposé à l'axe du temps n'était pas suivi : le graphique du dessus reçoit les
    seules heures de la fenêtre ;
  - **plan de bataille** « informations au clic sur une paroi ou un vitrage » (cinq étapes) dans `ROADMAP.md` ;
    « Diffusion » passe en 0.9.18 ;
  - vu dans Chrome (vues sud-ouest et nord-est ; boutons et cadre du DH ; curseur de l'heure, de 6 à 20 h).
    Tests : 376 réussis, 2 sautés.
- **0.9.15** (poussée avec la 0.9.16) : ouverture des baies comme le moteur COMETH (`OUVERTURE_COMME_LE_MOTEUR`,
  hypothèse 100) : θouv2 sans Δθconf_adapt, θouv1 = θouv2 − 1, réglage la nuit aussi ; règle reproduite 92 à
  99,9 % des heures (diagnostic dans `docs/audit.md`). Protections et passage d'air (éq. 239) : déjà conformes au
  moteur. Face au moteur : ouverture Th-B − 4 à + 3 %, Th-D − 4 à − 16 % ; froid de Paris 2 − 33 → − 9 %.
  Validation (`_resultats/validation_0.9.15.csv`) : 30 groupes sur 46 dans ± 10 % (29 avant), Bbio médian 0,0 %,
  froid 0,94 fois l'étude, DH à ± 10 % dans 21 groupes sur 37 (17 avant) ; DH de Sète et Nice A inchangé (bilan
  Th-D, θop 0,3 à 0,6 °C trop bas). Bâtiments de départ : DH − 15 à + 5 °C.h. Sorties de
  `comparer_horaires` réécrites dans `_resultats/horaires/` (copie des précédentes, de la 0.9.10, dans
  `_resultats/horaires_avant_0.9.15/`). Tests : 372 réussis, 2 sautés.
- **0.9.13** : lecture du guide Actibaie *Les protections solaires dans la RE 2020* (PDF et
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
    second bouton « Calculer ». Capture : `docs/capture_interface_1.jpg`.
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

« Push » de la 0.9.27. Sur le poste : non-régression (validation et comparaison horaire), puis les points de
l'audit qui demandent le moteur, dans l'ordre : R3 (décalage de Fs1 outil / moteur, 0 ou ± 1 h), écart de θop
du calcul d'été (0,3 à 0,6 °C), vitrage 15 / 25 / 40 % dans un logiciel réglementaire ; avec l'annexe III : R1
et R4. Diffusion en 0.9.26 ; mise en ligne sur accord. Ensuite : entrées d'air trop fortes (chauffage de
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
