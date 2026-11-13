# Feuille de route — Explorateur Bbio / DH

Seule liste de suivi du projet. Le plan détaillé (limites, plan de contrôle, organigrammes) est dans le document
« plan de bataille » : https://claude.ai/artifact/6joP54tckVZQdM8LYVeLRF

## Versions

| Version | Nom | Contenu | État |
|---|---|---|---|
| 0.8.0 | Socle | Structures multi-groupes, calendrier, météo (8 zones, Th-BC et Th-D), scénarios du logement collectif | fait |
| 0.8.2 | Solaire | Rayonnement sur une paroi orientée, masques simples, facteurs solaires | fait |
| 0.8.4 | Groupe | Modèle thermique horaire du groupe (fiche 5.21) : réseau RC, inertie, température opérative | fait |
| 0.8.6 | Besoins | Besoins de chauffage, de refroidissement et d'éclairage | fait |
| 0.8.8 | Bbio | repartir des 4 points de l'audit, hyp 29,30, 31 et 36. Bbio = 2 × Bch + 2 × Bfr + 5 × Becl, comparaison au Bbio max | à faire |
| 0.8.10 | DH | Degrés-heures d'inconfort (fiche 13.5) sur le jeu Th-D, comparaison au DH max, regarde ..\meteo_et_chaleur\calcul avant  | à faire |
| — | Brasseurs d'air (anticipé pour le DH) | `moteur/brasseurs.py` (fiche 8.32) : régulation, effet ΔθopBA sur le seuil d'inconfort, consommation ; classe `Brasseur`, `Groupe.volume_m3` et `Groupe.brasseurs` ; `tests/test_brasseurs.py` ; branchés sur le groupe en 0.8.4 | fait |
| 0.8.12 | Interface | Streamlit : boîte en axonométrie (style cbsh_visuel), saisie, résultats | à faire |
| 0.9.0 | Fonctionnel | Outil utilisable de bout en bout, déployé | à faire |
| 0.9.2 | Pédagogie | Page d'accueil (comme Météo et Chaleur), équations montrées, explications | à faire |
| 0.9.4 | Protections et ouvertures | Module protections mobiles et ouverture des baies ; catalogue tiré de RSEE | à faire |
| 0.9.6 | Diffusion | Module pédagogique séparé sur la diffusion de la chaleur (sans lien de calcul) | à faire |
| 0.9.8 | Validation | Calage sur plus de 10 RSEE de logements collectifs et sur OPEE ; cible Bbio à ± 10 % | à faire |
| 0.9.10 | Maison individuelle | Second usage | à faire |
| 1.0.0 | Diffusion publique | Version annoncée | à faire |

## En attente

- Lien de déploiement Streamlit (pour la 0.9.0).
- Extraction OPEE en parquet (pour la 0.9.8).
- Accord de la DHUP sur l'usage des fichiers météo (avant la 1.0.0).
- Seuils du plan de contrôle : 1 % sur les cas analytiques, 0,1 % sur le bilan d'énergie, quartiles OPEE.

## Points à reprendre

- 0.8.8 : Bbio = 2 × Bch + 2 × Bfr + 5 × Becl à partir de `besoins.bilan_besoins()`, sommé par zone et par
  bâtiment, comparé au Bbio max.
- 0.8.8 ou 0.9.8 : infiltrations par la perméabilité de l'enveloppe (nulles pour l'instant) ; relances du
  chauffage avant l'occupation (fiche 8.5) ; humidité de l'air (terme Cv.ω de Hg_ei, éq. 333).
- 0.9.4 : sans protections mobiles ni ouverture des baies, le besoin de froid est surestimé (voir `docs/audit.md`,
  résultats de la 0.8.6) : à reprendre avec ce module, avant tout calage.
- 0.9.8 : vérifier sur un RSEE la surface de référence et la surface habitable du groupe (hypothèse 30), et le
  besoin de froid compté d'office (hypothèse 29).
- 0.8.10 : période de confort adaptatif (fiche 3.1), qui choisit Sf-c ou Sf-e des parois opaques en Th-D.
- 0.8.10 : ventilation du calcul Th-D (l'échangeur à 0,5 est celui du Bbio) ; fournir aux brasseurs les entrées
  `actif`, `occupe`, `theta_ifr` et `ecart_conf_adapt` de `simuler_groupe()`.
- 0.8.12 : saisie de Sw2 (défaut : nul, voir `docs/audit.md`, hypothèse 21), de l'inertie, des ponts thermiques et
  du Uw horizontal des baies de toiture.
- 0.9.8 : flux solaires et rayonnement froid des ponts thermiques (fiche 5.19, éq. 300 et 306), parois sur le sol
  (pour l'instant : U saisi × b), échanges entre groupes — à reprendre si le calage sur les RSEE le demande.
- 0.8.10 : ajouter ΔθopBA au seuil d'inconfort, θop_conf_ch_corr = θop_conf_ch + ΔθopBA (fiche 13.5, éq. 2547) ;
  fournir aux brasseurs Is_confort_adaptatif et Δθconf_adapt (éq. 2546).
- 0.8.12 : saisie des brasseurs d'air dans l'interface (nombre, surface desservie, usage, gestion, débit et
  puissance du fabricant).
- 0.9.4 : protections mobiles (fiche 5.9, Rprot, hauteur de soleil corrigée, éq. 3 à 6) et ouverture des baies
  (fiche 5.13).
- 0.9.8 : comparer le rayonnement par orientation à un RSEE (sorties horaires, si disponibles).
- 0.8.12 : palette de l'interface (reçue le 12/11/2026, tirée de celle du HUB) :

  | Rôle | Nom | Code |
  |---|---|---|
  | Jaune HUB (accent4) | Sunflower Gold | `#FABD4A` |
  | Orange HUB (accent5) | — | `#FA9600` |
  | Texte | Noir | `#000000` |
  | Complémentaire | Cherry Blossom | `#FFB5C2` |
  | Complémentaire | Fresh Sky | `#00B0F0` |
  | Complémentaire | Wine Plum | `#6D2E46` |
  | Complémentaire | Deep Space Blue | `#283246` |

## Idées

- Masques lointains constitués d'arbres à feuilles caduques (fiche 3.2) : non traités en 0.8.2.
- Valeurs par défaut de l'absorption des parois opaques (règles Th-Bât, tableau 66 : 0,4 clair, 0,6 moyen, 0,8
  sombre, 1,0 noir) à proposer dans l'interface (0.8.12).

- Autres usages du classeur des scénarios (maison individuelle, bureaux…) : `outils/extraire_donnees.py` est prêt à
  recevoir d'autres onglets.
- Météo et Chaleur (vulgarisateur_DH) : son changement d'heure suit le calendrier civil de 2018, celui de la méthode
  est fixé aux heures 1 896 et 7 032. Écart à examiner.
