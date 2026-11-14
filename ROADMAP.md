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
| 0.8.8 | Bbio | Revue des hypothèses 29, 30, 31 et 36 de l'audit. Bbio = 2 × Bch + 2 × Bfr + 5 × Becl par groupe, zone et bâtiment, comparaison au Bbio max | fait |
| 0.8.10 | Cas de référence | Lecteur de RSET (`outils/lire_rset.py`), comparaison du Bbio à des études (`outils/comparer_reference.py`), variantes du besoin de froid | fait |
| 0.8.12 | Protections et ouvertures | Ouverture des baies, dont celle du mode Th-B pour le besoin de froid (fiche 5.13), et protections mobiles (fiche 5.9) ; catalogue tiré de RSEE | à faire |
| 0.8.14 | Infiltrations | Débits d'air par les défauts d'étanchéité (perméabilité à l'air), pour le besoin de chauffage | à faire |
| 0.8.16 | DH | Degrés-heures d'inconfort (fiche 13.5) sur le jeu Th-D, comparaison au DH max, regarde ..\meteo_et_chaleur\calcul avant  | à faire |
| — | Brasseurs d'air (anticipé pour le DH) | `moteur/brasseurs.py` (fiche 8.32) : régulation, effet ΔθopBA sur le seuil d'inconfort, consommation ; classe `Brasseur`, `Groupe.volume_m3` et `Groupe.brasseurs` ; `tests/test_brasseurs.py` ; branchés sur le groupe en 0.8.4 | fait |
| 0.8.18 | Interface | Streamlit : boîte en axonométrie (style cbsh_visuel), saisie, résultats | à faire |
| 0.9.0 | Fonctionnel | Outil utilisable de bout en bout, déployé | à faire |
| 0.9.2 | Pédagogie | Page d'accueil (comme Météo et Chaleur), équations montrées, explications | à faire |
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

- **Ordre des versions revu le 14/11/2026** (deux fois) : « Cas de référence » intercalé en 0.8.10 ; « Protections
  et ouvertures » passe de 0.9.4 à 0.8.12, avant le DH (0.8.16) et l'interface (0.8.18) ; le numéro 0.9.4 n'est
  plus utilisé ; « Infiltrations » ajouté en 0.8.14. Raison : le besoin de froid de l'outil vaut plusieurs fois celui des études, si bien que ni le Bbio
  ni le DH ne sont exploitables sans ces modules. `CHANGELOG.md` (0.8.8 et avant), `docs/audit.md` (0.8.8 et avant)
  et les commentaires du code citent encore les anciens numéros : 0.9.4 pour les protections, 0.8.10 pour le DH,
  0.8.12 pour l'interface. Depuis : DH en 0.8.16, interface en 0.8.18.
- 0.8.12 : **commencer par les protections mobiles** (fiche 5.9), premier levier du besoin de froid d'après les
  variantes de la 0.8.10 (voir `docs/audit.md`), puis l'ouverture des baies du mode Th-B (fiche 5.13). Les études
  donnent pour chaque baie Sw, Tl et U avec protection, la gestion de la protection et les réglages d'ouverture par
  saison : `Reference.baies` de `outils/lire_rset.py` les lit déjà ; il reste à les porter dans `Baie`.
- 0.8.14 : **infiltrations par la perméabilité à l'air** (`Q4PaSurf` des études). L'indicateur d'hiver
  des études vaut 0,5 à 2,3 fois la déperdition de la ventilation ; sans infiltrations, l'outil sous-estime le
  chauffage de 6 à 46 %. Mais injecter cet indicateur tel quel fait dépasser le chauffage des études (voir
  `docs/audit.md`, 0.8.10) : il faut le vrai modèle (débits par les défauts d'étanchéité, selon le vent et le tirage),
  pas un débit constant. Version à part, après les protections (décidé le 14/11/2026).
- 0.8.12 : baies sur un espace tampon (coefficient b et soleil), aujourd'hui lues comme donnant sur l'extérieur.
- 0.9.8 : U des baies en hiver : l'indicateur `Hg_es_hiver` des études est 1 à 15 % sous la somme des A × U sans
  protection de l'outil (protections fermées la nuit ?) ; ventilation : `H_Vent_Hiver` des études vaut 0,1397 × débit,
  contre 0,34 × 0,5 = 0,17 dans l'outil (éq. 382) : à comprendre.
- 0.9.8 : masques par tranches azimutales : les études donnent le même horizon à toutes les orientations d'un
  bâtiment, alors que la fiche 3.2 compte les tranches depuis la normale à la paroi (hypothèse 7) : vérifier la
  convention des logiciels.
- 0.8.16 : aligner les brasseurs d'air sur `hleg`, heure légale de début de pas (hypothèse 10 : « 6 < hlég ≤ 22 »
  lu sur la case, soit une heure trop tôt ; sur les sorties horaires d'un moteur Th-BCE, le jour va de hlég 7 à 22).
  Revoir du même coup le blocage manuel « hlég > 23 h ».
- 0.8.16 : constats tirés des sorties horaires d'un moteur Th-BCE (H3, Th-D), à reproduire : θrm par jour UTC, nul
  le premier jour ; seuil en occupation MIN(28 ; MAX(26 ; 0,33 × θrm + 20,8)) le jour, 26 °C la nuit ; hors
  occupation MAX(30 ; 0,33 × θrm + 20,8), sans degré-heure ; DH comptés en occupation et en période de confort
  adaptatif ; seuil corrigé (brasseurs) relevé de 0,5 à 2,5 °C, en occupation seulement. Référence de calcul : 399,25
  et 1 438,03 °C.h recalculés à 1e-7 près à partir des températures opératives de ces fichiers. Le module
  `dh_re2020.py` de Météo et Chaleur suit déjà ces conventions.
- 0.8.16 : relances du chauffage (fiche 8.5, tableau 92 : 2 h avant le retour des occupants avec une horloge),
  visibles dans ces sorties ; sans effet attendu sur le DH (hiver), à ne traiter que si un écart le demande.
- 0.9.8 : débit de ventilation du Bbio : les études donnent environ 1,2 à 1,5 m³/h par m² habitable en occupation
  (`Qv_occ_BBIO`), à comparer au débit moyen de l'hypothèse 39.
- 0.8.18 : saisie de l'exposition au bruit (BR1 à BR3) et de la hauteur sous plafond moyenne, pour le Bbio max.
- 0.9.8 : infiltrations par la perméabilité de l'enveloppe (nulles pour l'instant) ; relances du
  chauffage avant l'occupation (fiche 8.5) ; humidité de l'air (terme Cv.ω de Hg_ei, éq. 333).
- 0.8.12 : sans protections mobiles ni ouverture des baies, le besoin de froid est surestimé (voir `docs/audit.md`,
  résultats de la 0.8.6) : à reprendre avec ce module, avant tout calage.
- 0.8.16 : période de confort adaptatif (fiche 3.1), qui choisit Sf-c ou Sf-e des parois opaques en Th-D.
- 0.8.16 : ventilation du calcul Th-D (l'échangeur à 0,5 est celui du Bbio) ; fournir aux brasseurs les entrées
  `actif`, `occupe`, `theta_ifr` et `ecart_conf_adapt` de `simuler_groupe()`.
- 0.8.18 : saisie de Sw2 (défaut : nul, voir `docs/audit.md`, hypothèse 21), de l'inertie, des ponts thermiques et
  du Uw horizontal des baies de toiture.
- 0.9.8 : flux solaires et rayonnement froid des ponts thermiques (fiche 5.19, éq. 300 et 306), parois sur le sol
  (pour l'instant : U saisi × b), échanges entre groupes — à reprendre si le calage sur les RSEE le demande.
- 0.8.16 : ajouter ΔθopBA au seuil d'inconfort, θop_conf_ch_corr = θop_conf_ch + ΔθopBA (fiche 13.5, éq. 2547) ;
  fournir aux brasseurs Is_confort_adaptatif et Δθconf_adapt (éq. 2546).
- 0.8.18 : saisie des brasseurs d'air dans l'interface (nombre, surface desservie, usage, gestion, débit et
  puissance du fabricant).
- 0.8.12 : protections mobiles (fiche 5.9, Rprot, hauteur de soleil corrigée, éq. 3 à 6) et ouverture des baies
  (fiche 5.13).
- 0.9.8 : comparer le rayonnement par orientation à un RSEE (sorties horaires, si disponibles).
- 0.8.18 : palette de l'interface (reçue le 12/11/2026, tirée de celle du HUB) :

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
  sombre, 1,0 noir) à proposer dans l'interface (0.8.18).

- Autres usages du classeur des scénarios (maison individuelle, bureaux…) : `outils/extraire_donnees.py` est prêt à
  recevoir d'autres onglets.
- Météo et Chaleur (vulgarisateur_DH) : son changement d'heure suit le calendrier civil de 2018, celui de la méthode
  est fixé aux heures 1 896 et 7 032. Écart à examiner.
