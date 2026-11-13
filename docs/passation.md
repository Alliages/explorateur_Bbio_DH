# Passation

Note courte, tenue à jour en fin de tâche, pour reprendre le travail depuis claude.ai ou Claude Code.

## État au 13/11/2026

- Version **0.8.6** (besoins), préparée et testée, **sans commit**, à la suite de la 0.8.4 elle aussi non publiée :
  rien n'est publié tant que « Push » n'est pas donné.
- `moteur/besoins.py` : `calculer_besoins()` (année, mode Th-B : émetteur conventionnel, saisons, consignes) et
  `bilan_besoins()` (Bch, Bfr, Becl mensuels et annuels en kWh/m²). Une année : environ 0,6 s.
- `moteur/apports.py` : apports internes du logement collectif (fiche 4.1). `moteur/eclairage.py` : lumière
  naturelle et consommation d'éclairage (fiches 5.10 et 7.1).
- `moteur/groupe.py` (0.8.4) : modèle thermique horaire du groupe ; `debit_ventilation()` ajouté (base et pointe).
- `structures.py` : `nb_logements` et `debit_ventilation_pointe_m3h` sur `Groupe`.
- Tests : `python -m pytest` → 226 réussis, 3 sautés (comparaisons aux classeurs si `_references/` est vide, test
  git hors dépôt).
- Lectures du texte et simplifications : `docs/audit.md`, hypothèses 17 à 28 (0.8.4) et 29 à 41 (0.8.6). À relire en
  priorité : le besoin de froid compté d'office (29), la surface habitable du groupe (30), les relances non
  traitées (31), les fenêtres glissantes des saisons (36).
- **Résultat à garder en tête** : sur un immeuble d'essai, Bch ≈ 12 kWh/m² en H1a et Bfr ≈ 22 kWh/m². Le froid est
  surestimé tant que les protections mobiles et l'ouverture des baies ne sont pas modélisées (0.9.4).
- **Le dossier de travail local n'est pas un dépôt git** (`git status` échoue) : à cloner ou à rattacher au dépôt
  avant « Push ».

## Prochaine étape

0.8.8 « Bbio » : Bbio = 2 × Bch + 2 × Bfr + 5 × Becl (fiche 13.1, éq. 2385), sommé sur les groupes d'une zone et
d'un bâtiment, comparé au Bbio max (annexe de l'arrêté : modulations selon la zone climatique, l'altitude, la
surface). Avant de coder : relire la fiche 13.1 et le texte du Bbio max, proposer la démarche et le numéro de
version.

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
- `../RSEE` (à côté du dépôt) : études de logements collectifs, pour la validation (0.9.8).
- `_sources/` : annexes de l'arrêté et règles Th-Bât (PDF), pour relire la méthode.
- Tout dossier commençant par `_` est exclu de git (`.gitignore`).

## En attente de Guillaume

Lien Streamlit (0.9.0), extraction OPEE (0.9.8), accord DHUP (avant 1.0.0), seuils du plan de
contrôle.
