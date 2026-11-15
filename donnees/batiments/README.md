# Bâtiments de départ

Chaque fichier `.csv` de ce dossier est un bâtiment du menu « Bâtiment de départ » de l'interface. Les fichiers
sont lus au lancement, par ordre alphabétique : le numéro en tête du nom fixe l'ordre du menu, et le premier
bâtiment est celui de la page à son ouverture.

## Ajouter un bâtiment

1. Copier un fichier existant, par exemple `02_immeuble_9_logements.csv`, sous un nouveau nom
   (`03_mon_batiment.csv`).
2. Changer le `nom` (il doit différer de celui des autres bâtiments) et les valeurs voulues.
3. Relancer l'interface (`streamlit run app.py`).

## Format

Séparateur `;`, virgule décimale, UTF-8. Quatre colonnes : `champ;valeur;unite;description`. Seules `champ` et
`valeur` sont lues ; les deux autres servent au lecteur.

| Type de champ | Écriture | Exemple |
|---|---|---|
| Nombre | virgule décimale | `2,8` |
| Entier | sans décimale | `3` |
| Oui / non | `oui` ou `non` | `traversant;oui` |
| Liste de façades | clés séparées par une virgule | `principale, arriere` |
| Texte | tel quel | `H1a`, `volet` |

- La ligne `nom` est obligatoire.
- Un champ absent prend la valeur par défaut de la boîte (`Boite` dans `interface/saisie.py`, égale au logement
  de 70 m²).
- L'enveloppe n'est pas décrite ici : Uw, Sw, TL, Uw et Sw protection baissée, part ouvrante, U des murs, de la
  toiture et du plancher bas, ψ, inertie, ventilation et perméabilité viennent du niveau choisi (« Performant »,
  « Moyen », « Faible », `donnees/typologies_logements.csv`). Ces champs sont refusés.
- Un champ inconnu, une valeur illisible ou hors bornes arrêtent la lecture avec un message qui nomme le fichier
  et la ligne.
