# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 14/11/2026

- Version **0.8.10** (cas de référence), préparée et testée dans le dossier local, publiée sur `travail` le 14/11/2026, après
  la 0.8.8 (deux commits).
- `outils/lire_rset.py` : `lire_rset(chemin)` rend le `Projet` de l'outil et la `Reference` de l'étude (résultats,
  indicateurs, baies avec protections et ouvertures, confort d'été).
- `outils/comparer_reference.py` : `comparer(chemin)` et `variantes_besoins(projet, reference)` ; en ligne de
  commande : `python -m outils.comparer_reference "_sources\mon_etude.xml" --variantes`.
- `moteur/bbio.py` (0.8.8) : `calculer_bbio(projet)` ; la hauteur sous plafond du Bbio max est maintenant la moyenne
  du bâtiment.
- Tests : `python -m pytest` → 253 réussis, 2 sautés (classeurs de `_references/` absents). Le test des études
  locales tourne ici, il est sauté sans RSET dans `_sources/`.
- `docs/audit.md`, section 0.8.10 : tableau des écarts sur cinq études, hypothèses 46 (revue) et 48 à 54.
- **Résultat à garder en tête** : la lecture est juste (parois, surfaces, Bbio max retrouvés), l'éclairage aussi.
  Le chauffage est 6 à 46 % trop faible (pas d'infiltrations), le froid 4 à 46 fois trop fort. Les protections
  mobiles sont le premier levier du froid, l'ouverture des baies le second.
- **Les brasseurs d'air lisent encore la case** pour « 6 < hlég ≤ 22 » : une heure trop tôt (hypothèse 42).

## Prochaine étape

0.8.12 « Protections et ouvertures » : protections mobiles d'abord (fiche 5.9), puis ouverture des baies du mode
Th-B (fiche 5.13). Cible chiffrée : le Bfr des dix groupes de `docs/audit.md`. Les données d'entrée existent déjà
dans `Reference.baies` (Sw, Tl et U avec protection, gestion, réglages d'ouverture par saison) ; il reste à les
porter dans `Baie`. Avant de coder : relire les fiches 5.9 et 5.13, proposer la démarche.

0.8.14 « Infiltrations » : version à part, après les protections (décidé le 14/11/2026). Sans elles le chauffage reste
sous-estimé ; elles demandent le vrai modèle de la méthode (voir `ROADMAP.md`).

0.8.16 « DH » : les classeurs horaires de Paris, Sète et Nice et le module `..\meteo_et_chaleur\calcul\dh_re2020.py`
donnent la référence ; voir les points 0.8.16 de `ROADMAP.md`.

## Pour reprendre

```powershell
cd explorateur_Bbio_DH
git checkout travail
git pull
.\.venv\Scripts\Activate.ps1
python -m pytest
```

## Fichiers locaux nécessaires (hors dépôt)

- `_sources/` : annexes de l'arrêté, annexe à l'article R. 172-4 (trois versions), règles Th-Bât (PDF), et les
  études de référence : `paris_…`, `sete_…`, `nice_…` (XML et classeur horaire, PDF pour Paris),
  `Fichier source + RSET 04-2026` (Nice A) et le dossier « Annexe 3 … BAT B_V2 » (Nice B).
- `../_RSEE` (à côté du dépôt) : autres études RE2020, pour la validation (0.9.8).
- `../bon résultat.csv`, `../bon résultat_H3_tracc.csv` : sorties horaires d'un moteur Th-BCE (référence du DH).
- `_references/` : les deux classeurs officiels (absents de ce poste : deux tests sautés).
- Tout dossier commençant par `_` est exclu de git (`.gitignore`).

## En attente de Guillaume

Lien Streamlit (0.9.0), extraction OPEE (0.9.8), accord DHUP (avant 1.0.0),
seuils du plan de contrôle.
