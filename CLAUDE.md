# Règles de travail — Explorateur Bbio / DH

Plan de bataille (limites, feuille de route, plan de contrôle, organigrammes) :
https://claude.ai/artifact/6joP54tckVZQdM8LYVeLRF
État courant : `docs/passation.md`. Écarts et hypothèses : `docs/audit.md`. Suivi : `ROADMAP.md`.

## Projet

- Dépôt : https://github.com/Alliages/explorateur_Bbio_DH — licence GPL 3.
- Branches : `travail` pour les versions intermédiaires, `main` pour le déploiement.
- Environnement : Windows (PowerShell, `.venv`, pas d'Anaconda).
- Les RSEE sont hors du dépôt, dans `../_RSEE`, et n'y vont jamais ; les dossiers commençant par `_` (classeurs
  officiels `_references/`, textes `_sources/`) non plus.
- Outil pédagogique, non réglementaire. Le moteur reste cohérent avec la méthode Th-BCE 2020.

## Avant de coder

- Lire les fichiers existants (code, README, CHANGELOG, ROADMAP) ; ne pas relire un fichier inchangé.
- Analyser et proposer une démarche ; « Lance » ou « GO » vaut accord (sauf correction triviale).
- Ne rien faire hors de la demande ; les idées vont dans `ROADMAP.md`.

## Mots d'ordre

- « Lance » ou « GO » : préparer les modifications et les tester, sans commit. Dans Claude Code, pas de zip ; dans
  claude.ai, zip des seuls fichiers modifiés (zip complet si des fichiers disparaissent, en le signalant).
- « Push » : commit + push sur `travail` (message : version + résumé). Rien n'est publié sans ce mot.
- Le passage de `travail` à `main` se fait seulement sur demande explicite.
- Aucune GitHub Action ni aucun déploiement sans accord explicite.
- En fin de tâche : résumé court des modifications et des points restants ; mettre à jour `docs/passation.md`.

## Versions

- Demander le numéro avant « Lance » (en proposer un), sauf consigne de rester sur la version en cours.
- Dernier chiffre pair = évolution, impair = correction.
- 0.8.x tant que l'outil n'est pas fonctionnel, 0.9 quand il fonctionne, 1.0 à la première diffusion.
- Mettre à jour `VERSION`, `CHANGELOG.md` et `ROADMAP.md` à chaque version.

## Code

- Modifier plutôt que réécrire ; préserver le format des fichiers (séparateur `;`, virgule décimale, UTF-8).
- Réglages en tête de fichier ou dans `config/reglages.py` ; constantes physiques et réglementaires dans
  `donnees/hypotheses.csv`, chacune avec sa source (annexe, fiche, équation).
- Noms et commentaires en français ; code bien commenté, surtout les traitements longs.
- Solutions simples ; dépendances minimales. `moteur/` ne dépend jamais de l'interface.
- Commandes Windows prêtes à copier dans PowerShell.
- Vérifier avant de conclure : `python -m pytest`, comparaison à la référence, capture avant/après si l'affichage
  change.

## Réponses

- Concises, sans formule d'introduction ni de conclusion superflue ; raisonnement rigoureux.
