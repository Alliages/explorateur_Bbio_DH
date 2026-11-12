# Feuille de route — Explorateur Bbio / DH

Seule liste de suivi du projet. Le plan détaillé (limites, plan de contrôle, organigrammes) est dans le document
« plan de bataille » : https://claude.ai/artifact/6joP54tckVZQdM8LYVeLRF

## Versions

| Version | Nom | Contenu | État |
|---|---|---|---|
| 0.8.0 | Socle | Structures multi-groupes, calendrier, météo (8 zones, Th-BC et Th-D), scénarios du logement collectif | fait |
| 0.8.2 | Solaire | Rayonnement sur une paroi orientée, masques simples, facteurs solaires | à faire |
| 0.8.4 | Groupe | Modèle thermique horaire du groupe (fiche 5.21) : réseau RC, inertie, température opérative | à faire |
| 0.8.6 | Besoins | Besoins de chauffage, de refroidissement et d'éclairage | à faire |
| 0.8.8 | Bbio | Bbio = 2 × Bch + 2 × Bfr + 5 × Becl, comparaison au Bbio max | à faire |
| 0.8.10 | DH | Degrés-heures d'inconfort (fiche 13.5) sur le jeu Th-D, comparaison au DH max | à faire |
| 0.8.12 | Interface | Streamlit : boîte en axonométrie (style cbsh_visuel), saisie, résultats | à faire |
| 0.9.0 | Fonctionnel | Outil utilisable de bout en bout, déployé | à faire |
| 0.9.2 | Pédagogie | Page d'accueil (comme Météo et Chaleur), équations montrées, explications | à faire |
| 0.9.4 | Protections et ouvertures | Module protections mobiles et ouverture des baies ; catalogue tiré de RSEE | à faire |
| 0.9.6 | Diffusion | Module pédagogique séparé sur la diffusion de la chaleur (sans lien de calcul) | à faire |
| 0.9.8 | Validation | Calage sur plus de 10 RSEE de logements collectifs et sur OPEE ; cible Bbio à ± 10 % | à faire |
| 0.9.10 | Maison individuelle | Second usage | à faire |
| 1.0.0 | Diffusion publique | Version annoncée | à faire |

## En attente

- Palette de couleurs, à partir de celle du HUB (pour la 0.8.12).
- Lien de déploiement Streamlit (pour la 0.9.0).
- Extraction OPEE en parquet (pour la 0.9.8).
- Accord de la DHUP sur l'usage des fichiers météo (avant la 1.0.0).
- Seuils du plan de contrôle : 1 % sur les cas analytiques, 0,1 % sur le bilan d'énergie, quartiles OPEE.

## Points à reprendre

- 0.8.2 : confirmer la convention d'orientation de `moteur/structures.py` (0 = sud, 90 = ouest, comme Psi).
- 0.8.4 : ajouter au groupe l'inertie, les ponts thermiques et la ventilation.
- Relire les fiches 5.9 et 5.13 de l'annexe III au moment de coder le solaire et les baies.

## Idées

- Autres usages du classeur des scénarios (maison individuelle, bureaux…) : `outils/extraire_donnees.py` est prêt à
  recevoir d'autres onglets.
- Météo et Chaleur (vulgarisateur_DH) : son changement d'heure suit le calendrier civil de 2018, celui de la méthode
  est fixé aux heures 1 896 et 7 032. Écart à examiner.
