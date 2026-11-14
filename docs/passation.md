# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 14/11/2026

- Version **0.8.12** (protections et ouvertures), préparée et testée dans le dossier local, **sans commit** : rien
  n'est publié tant que « Push » n'est pas donné. Dernier commit de `travail` : 0.8.10.
- `moteur/protections.py` : ratio de fermeture conventionnel des volets et stores enroulables, flux et
  déperdition des baies heure par heure. Matrices dans `donnees/protections_mobiles_*.csv`.
- `moteur/ouvertures.py` : ouverture des baies du mode Th-B et débit de surventilation.
- `moteur/besoins.py` les applique dès qu'une baie porte une protection ou est ouvrable ; sinon rien ne change.
- `outils/lire_rset.py` lit protections et ouvertures ; `outils/comparer_reference.py --variantes` retire un module
  à la fois.
- Tests : `python -m pytest` → 275 réussis, 2 sautés (classeurs de `_references/` absents).
- `docs/audit.md`, section 0.8.12 : tableau du froid sur cinq études, hypothèses 55 à 65.
- **Résultat à garder en tête** : le froid est passé de 4 à 46 fois celui des études à 1,7 à 4 fois (Paris : 1,6 et
  0,6 kWh/m² contre 0,4 et 0,3). Le chauffage reste 12 à 55 % trop faible, faute d'infiltrations.
- **Les brasseurs d'air lisent encore la case** pour « 6 < hlég ≤ 22 » : une heure trop tôt (hypothèse 42).

## Prochaine étape

0.8.14 « Infiltrations » : débits d'air par les défauts d'étanchéité (perméabilité à l'air, `Q4PaSurf` des études),
pour le besoin de chauffage. Cible chiffrée : le Bch des dix groupes de `docs/audit.md`. Avant de coder : trouver
et relire la fiche de la méthode (débits par les défauts d'étanchéité, vent et tirage), proposer la démarche.

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

Seuils de la gestion automatique des volets, à lire dans Climawin ou Pleiades (hypothèse 57) ; lien Streamlit
(0.9.0), extraction OPEE (0.9.8), accord DHUP (avant 1.0.0),
seuils du plan de contrôle.
