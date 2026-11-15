# Niveaux d'enveloppe des logements

Trois scripts autonomes qui produisent les niveaux **performant**, **moyen** et **faible** proposés dans le menu
« Enveloppe » de l'interface (`interface/saisie.py`, `NIVEAUX_ENVELOPPE`).

| Fichier | Rôle | Produit |
|---|---|---|
| `calcul_typologies_logements.py` | Quantiles des 13 variables d'enveloppe | `donnees/typologies_logements.csv` |
| `graphique_pedagogique_logements.py` | Graphique pédagogique (palette HUB) : min-max, boîte P25-P75, repères | `docs/graphique_pedagogique_logements.png` |
| `graphique_boxplots_logements.py` | Boîtes à moustaches détaillées, une zone par point (contrôle) | image de travail, hors dépôt |
| `valeurs_3_rset.py` | Valeurs des 13 variables, une ligne par groupe, pour les RSET de `FICHIERS` (par défaut les 3 « scénario 2 » de `_sources`) | CSV de travail, hors dépôt |

## Source

`caracteristiques_rset.csv` : une ligne par zone d'étude RE2020, tirée des RSEE. Ce fichier et les RSEE restent
**hors du dépôt** (`../_RSEE`) : les scripts ne peuvent être relancés qu'en local.

## Méthode

- Logements collectifs et maisons individuelles, doublons stricts écartés, une version par opération
  (`EMPREINTES_RETENUES`) : 18 zones, 6 opérations, 17 305 m² habitables.
- Quantiles pondérés par la surface habitable de la zone : performant = P25 du côté favorable, moyen = P50,
  faible = P75 du côté défavorable ; valeurs arrondies au pas le plus grossier qui garde les niveaux distincts.
- Inertie : classe Th-I, « personnalisée » convertie par Cmq et Amq.
- `psi_moyen` couvre tous les ponts thermiques ; la boîte l'applique aux seules rives des planchers (hypothèse 88
  de `docs/audit.md`).

## Relancer

Les deux graphiques demandent `matplotlib`, absent de `requirements.txt` (l'outil en ligne n'en a pas besoin) :
`pip install matplotlib` une fois.

```powershell
.\.venv\Scripts\Activate.ps1
$source = "..\_RSEE\caracteristiques_rset.csv"     # à adapter
python -I outils\typologies\calcul_typologies_logements.py $source donnees\typologies_logements.csv
python -I outils\typologies\graphique_pedagogique_logements.py $source docs\graphique_pedagogique_logements.png
python -I outils\typologies\graphique_boxplots_logements.py $source _resultats\boxplots_logements.png
python -I outils\typologies\valeurs_3_rset.py $source _resultats\valeurs_typologies_3_rset.csv
python -m pytest tests\test_interface.py
```

Le CSV est lu au démarrage de l'interface ; une colonne source inconnue ou une variable manquante arrête la
lecture avec un message clair (`CHAMPS_TYPOLOGIES` dans `interface/saisie.py`).
