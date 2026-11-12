# Journal des versions — Explorateur Bbio / DH

Règle : `0.8.x` tant que l'outil n'est pas fonctionnel, `0.9.x` quand il fonctionne, `1.0` à la première version
annoncée et diffusée. Dernier chiffre **pair** = évolution, **impair** = correction.

## 0.8.0 — évolution (10/11/2026), socle

Première version : les données d'entrée du futur moteur et leurs contrôles. Aucun calcul thermique, aucune interface.

- **Structures** (`moteur/structures.py`) : Projet → Bâtiment → Zone → Groupe → Parois et Baies. Une zone porte une
  liste de groupes (logements traversants et non traversants).
- **Calendrier conventionnel** (`moteur/calendrier.py`) : heure légale (UTC + 1 l'hiver, UTC + 2 l'été, de l'heure
  1 896 à l'heure 7 031), année débutant un lundi, 52 semaines réparties 4-4-5-4-5-4-4-5-4-4-5-4, case des scénarios.
- **Météo** (`moteur/meteo.py`) : 8 zones climatiques × 2 jeux (Th-BC, Th-D), toutes les colonnes du classeur
  officiel, correction d'altitude (100, 500 ou 900 m).
- **Scénarios du logement collectif** (`moteur/scenarios.py`) : 13 scénarios (occupation, consignes 19/16 °C et
  26/30 °C, apports internes, éclairage, ventilation…), déroulés heure par heure sur l'année.
- **Hypothèses** (`donnees/hypotheses.csv`) : chaque constante avec son unité et sa source.
- **Extraction** (`outils/extraire_donnees.py`) : régénère les CSV de `donnees/` depuis les deux classeurs officiels,
  gardés en local dans `_references/`.
- Deux cas non décrits par les textes sont tranchés par hypothèse et consignés dans `docs/audit.md` : le jour 365 et
  la dernière heure de l'année.
- Tests : 61, dont la comparaison aux classeurs officiels quand ils sont présents en local.
