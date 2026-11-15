# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 15/11/2026

- Dernière version publiée sur `travail` : **0.9.2**. **0.9.4** prête, non poussée (attend « Push »).
- **0.9.4** : bâtiments de départ lus dans `donnees/batiments/` (un CSV par bâtiment, `champ;valeur;unite;
  description`, ligne `nom`, ordre alphabétique des fichiers ; mode d'emploi dans le `README.md` du dossier).
  `saisie.lire_batiment`, `lire_batiments` ; `BATIMENTS_DE_DEPART` est lu en fin de `interface/saisie.py`
  (la lecture contrôle chaque boîte avec `construire_projet`). Champ absent = valeur de `Boite` ; enveloppe,
  champ inconnu, valeur illisible, zone inconnue refusés avec fichier et ligne. Nouveau logement de 70 m²
  (= `Boite()`) : H1a, 7 × 10 m, baies 25 / 0 / 25 / 0 %, gestion manuelle motorisée ; l'immeuble suit (seule
  la forme diffère). Logement : Bbio 90,7 / 114,8 / 135,5 (max 91,0), DH 609 / 786 / 991 ; immeuble : Bbio
  48,7 / 58,2 / 65,8 (max 82,8), DH 511 / 675 / 859 (performant / moyen / faible). Vu dans Chrome. Toute
  nouvelle saisie de `Boite` doit aussi entrer dans les deux CSV (un test vérifie qu'ils sont complets).
  Versions revues : pédagogie 0.9.6, export CSV 0.9.8 (avec la validation), diffusion de la chaleur 0.9.12.
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
- Tests : `python -m pytest` → 348 réussis, 2 sautés (classeurs de `_references/` absents), en moins d'une
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

« Push » de la 0.9.4, puis mise en ligne sur accord. Ensuite la 0.9.6 (pédagogie) : page d'accueil,
nouvelles briques (point « Interface, suites de la 0.9.0 » de `ROADMAP.md`). Écrire une brique : un fichier dans
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
- `../_RSEE` (à côté du dépôt) : autres études RE2020, pour la validation (0.9.8).
- `../bon résultat.csv`, `../bon résultat_H3_tracc.csv` : sorties horaires d'un moteur Th-BCE (référence du DH).
- `_references/` : les deux classeurs officiels (absents de ce poste : deux tests sautés).
- Tout dossier commençant par `_` est exclu de git (`.gitignore`).
- Lecture des PDF : `pdftotext` est disponible, pas `pdftoppm` (les tableaux en image ne peuvent pas être relus).

## En attente de Guillaume

Chapitre V de l'annexe à l'article R. 172-4 (catégories de contraintes extérieures, hypothèse 76) ; RSET du même
calcul que les classeurs horaires ; seuils de la gestion automatique des volets, à lire dans Climawin ou Pleiades
(hypothèse 57) ; accord et lien Streamlit pour la mise en ligne de la 0.9.0, extraction OPEE (0.9.8), accord DHUP
(avant 1.0.0), seuils du plan de contrôle.
