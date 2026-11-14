# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 14/11/2026

- Versions **0.8.12** (protections et ouvertures) et **0.8.14** (infiltrations) publiées sur `travail` le
  14/11/2026 (deux commits).
- `moteur/protections.py` et `moteur/ouvertures.py` (0.8.12) : protections mobiles et ouverture des baies.
- `moteur/infiltrations.py` (0.8.14) : équilibre de pression du groupe, débit entrant par les défauts d'étanchéité.
- `moteur/besoins.py` applique les trois modules selon ce que porte le groupe (protection ou ouverture d'une baie,
  perméabilité) ; sans rien de cela, les résultats de la 0.8.10 sont inchangés.
- `outils/comparer_reference.py --variantes` retire un module à la fois.
- Tests : `python -m pytest` → 285 réussis, 2 sautés (classeurs de `_references/` absents).
- `docs/audit.md`, sections 0.8.12 et 0.8.14 : tableaux sur cinq études, hypothèses 55 à 74.
- **Résultat à garder en tête** : sur les dix groupes, le chauffage est 2 à 26 % sous les études et le froid 1,7 à
  4 fois au-dessus (Paris : 1,5 et 0,6 kWh/m² contre 0,4 et 0,3).
- **Point ouvert** : l'indicateur d'infiltrations d'hiver des études vaut 3 à 6 fois celui de l'outil (voir
  `docs/audit.md`, 0.8.14).
- **Les brasseurs d'air lisent encore la case** pour « 6 < hlég ≤ 22 » : une heure trop tôt (hypothèse 42).

## Prochaine étape

0.8.16 « DH » : degrés-heures de la fiche 13.5 sur le jeu Th-D. Les classeurs horaires de Paris, Sète et Nice et le
module `..\meteo_et_chaleur\calcul\dh_re2020.py` donnent la référence ; voir les points 0.8.16 de `ROADMAP.md`.
Avant de coder : aligner les brasseurs sur `hleg`, ajouter aux protections et aux ouvertures leurs règles du mode
Th-D, proposer la démarche.

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

Seuils de la gestion automatique des volets, à lire dans Climawin ou Pleiades (hypothèse 57) ; lien Streamlit
(0.9.0), extraction OPEE (0.9.8), accord DHUP (avant 1.0.0),
seuils du plan de contrôle.
