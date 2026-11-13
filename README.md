# Explorateur Bbio / DH

Outil pédagogique qui recalcule, de façon simplifiée et approchée, le **Bbio** et les **degrés-heures d'inconfort
(DH)** de la RE2020, en suivant la logique de la méthode Th-BCE 2020. Il s'adresse aux architectes et aux ingénieurs,
étudiants ou débutants, pour comprendre et discuter l'inconfort d'été et la RE2020.

**Ce n'est pas un logiciel réglementaire.** Il n'est pas évalué au sens de l'annexe V de l'arrêté du 4 août 2021 et
ses résultats ne peuvent pas servir à une attestation. Cible : un Bbio à ± 10 % d'une étude réglementaire.

Version en cours : voir `VERSION` et `CHANGELOG.md`. Suite prévue : `ROADMAP.md`.

## État (0.8.6)

Socle (structures de projet, calendrier conventionnel, fichiers météo, scénarios du logement collectif), module
solaire (rayonnement et éclairement reçus par une paroi orientée, masques, flux transmis par les baies et les parois
opaques), modèle thermique horaire du groupe (réseau RC de la fiche 5.21) et besoins de chauffage, de
refroidissement et d'éclairage d'un groupe (apports internes, émetteur conventionnel, saisons, lumière naturelle).
Sans protections mobiles ni ouverture des baies (0.9.4), le besoin de froid est encore surestimé. Le Bbio, les DH et
l'interface arrivent dans les versions suivantes.

## Installation (Windows, PowerShell)

```powershell
git clone https://github.com/Alliages/explorateur_Bbio_DH.git
cd explorateur_Bbio_DH
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
```

## Organisation

| Dossier | Contenu |
|---|---|
| `moteur/` | Calcul, sans aucune dépendance à l'interface |
| `donnees/` | Météo, scénarios et hypothèses (CSV : séparateur `;`, virgule décimale, UTF-8) |
| `config/` | Chemins, formats et listes |
| `outils/` | Scripts de préparation des données |
| `tests/` | Tests automatiques |
| `docs/` | Journal d'audit et note de passation |

Données locales, **jamais dans le dépôt** : les études RE2020 de projets réels (RSEE), rangées à côté du dépôt dans
`../RSEE`, et tout dossier dont le nom commence par `_`, dont `_references/` (classeurs
officiels). Un test échoue si l'un de ces fichiers est suivi par git.

## Sources

- Arrêté du 4 août 2021, annexe III (méthode Th-BCE 2020) et annexe IV (règles Th-Bat 2020).
- Classeur « scénarios conventionnels » de la RE2020, version du 29/04/2026.
- Classeur « scénarios météorologiques Th-BC / Th-D » de la RE2020 (DHUP, données Météo-France 2000-2018).

Chaque constante du moteur est citée avec sa source dans `donnees/hypotheses.csv`.

### Fichiers météo

Les fichiers de `donnees/meteo/` sont extraits du classeur officiel, dont la présentation indique que ces données
« ne peuvent être utilisées que pour le calcul réglementaire de la performance énergétique des bâtiments ». Leur
usage dans un outil pédagogique fait l'objet d'une demande d'accord auprès de la DHUP, à obtenir avant la version 1.0.

Pour régénérer les CSV : placer les deux classeurs dans `_references/`, puis

```powershell
python -m outils.extraire_donnees
```

## Licence

GPL 3 — voir `LICENSE`.
