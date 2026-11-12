# Journal d'audit

Écarts aux textes, hypothèses de l'outil et vérifications faites, version par version.

## 0.8.0 — socle

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Correspondance heure de simulation → case des scénarios | Annexe III, fiche 4.1, tableau (heures 0, 1, 1 895, 1 896, 7 031, 7 032) | identique |
| Semaines par mois, 4e semaine de décembre = jours 358 à 364 | Annexe III, fiche 4.1 | identique |
| Météo : 16 fichiers de 8 760 heures, 10 colonnes, sans vide | Classeur officiel | conforme |
| Météo : onglets H2d Th-D et H3 Th-BC relus en entier | Classeur officiel | écart maximal < 1e-9 |
| Correction d'altitude | Annexe III, fiche 3.1, calcul à la main (H1a, 650 m) | identique |
| Occupation du logement, heure par heure | Reconstruction indépendante (absences 9h-17h, 9h-13h le mercredi) | identique |
| Heures inoccupées dans l'année | Compte à la main : 51 × 36 + 8 + 168 = 2 012 h | identique |
| Tableau d'occupation | Classeur des scénarios, onglet LC, lignes 31 à 37 | identique |

### Hypothèses de l'outil (cas non décrits par les textes)

1. **Jour 365.** L'année conventionnelle compte 52 semaines, soit 364 jours ; la simulation en compte 365. L'outil
   traite le jour 365 comme un lundi (suite du cycle) et lui applique les valeurs hebdomadaires de la 1re semaine de
   décembre : logement occupé, consignes normales. Même choix que Météo et Chaleur 0.9.18.
   Réglage : `jour_365_mois`, `jour_365_semaine` dans `donnees/hypotheses.csv`.
2. **Dernière heure de l'année (8 759).** UTC 23h-0h, donc 0h-1h légal le lendemain du jour 365. L'outil la reporte
   sur le 1er janvier (case 1 du lundi), l'année étant traitée comme un cycle. Le tableau de la fiche 4.1 indique
   pour cette heure « 1H-2H, case 2 », ce qui contredit la formule Hleg = IHJ + EHLO de la fiche 3.1 (23 + 1 = 24,
   soit 0h) : lecture retenue = la formule. Effet : une heure de nuit, occupée dans les deux lectures.

### Points de vigilance

- **Correction d'altitude au niveau de la mer.** La méthode retient 100 m pour tout site jusqu'à 400 m : la
  température extérieure est abaissée de 0,5 °C même à l'altitude 0. Appliqué tel quel.
- **Humidité.** `we0` est en g/kg dans les fichiers ; `we` corrigé est en kg/kg (division par 1 000 de la formule).
- **Clause d'usage des fichiers météo.** Voir README ; accord de la DHUP à obtenir avant la 1.0.
- **Rayonnement direct avec soleil couché.** Dans le classeur officiel, quelques heures ont `dirN` > 0 alors que
  `Gamma` = 0 : 28 heures en H1a, 30 en H2d (Th-BC), aucune dans les six autres zones. Données reprises telles
  quelles ; à traiter dans le module solaire (0.8.2).
- **Th-BC et Th-D.** Les deux jeux diffèrent sur environ 900 heures (la séquence caniculaire), sauf en H1c où la
  température diffère sur les 8 760 heures. En H2c, le maximum est le même dans les deux jeux (40,89 °C).
- **Convention d'orientation** des structures : provisoire, à confirmer en 0.8.2.
