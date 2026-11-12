# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 10/11/2026

- Version **0.8.0** (socle) : structures, calendrier, météo, scénarios du logement collectif, hypothèses sourcées.
- Tests : `python -m pytest` → 61 réussis (2 comparaisons aux classeurs officiels sautées si `_references/` est vide).
- Aucun calcul thermique ni interface pour l'instant.

## Prochaine étape

0.8.2 « Solaire » : rayonnement reçu par une paroi orientée à partir de `dirN`, `diff`, `Gamma` et `Psi`.
Avant de coder : relire les fiches de l'annexe III sur le rayonnement et les baies (5.9, 5.13), confirmer la
convention d'orientation de `moteur/structures.py`, proposer la démarche et le numéro de version.

## Pour reprendre

```powershell
cd explorateur_Bbio_DH
git checkout travail
git pull
.\.venv\Scripts\Activate.ps1
python -m pytest
```

## Fichiers locaux nécessaires (hors dépôt)

- `_references/4_scenarios_meteorologiques_th-bc_th-d_re2020.xlsx`
- `_references/2026-04-29_scenarios_conventionnels.xlsx`
- `_rsee/` : études de logements collectifs, pour la validation (0.9.8).

## En attente de Guillaume

Palette (0.8.12), lien Streamlit (0.9.0), extraction OPEE (0.9.8), accord DHUP (avant 1.0.0), seuils du plan de
contrôle.
