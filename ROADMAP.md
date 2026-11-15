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
| 0.8.12 | Protections et ouvertures | Protections mobiles (fiche 5.9 : volets et stores enroulables, gestion manuelle et automatique) et ouverture des baies du mode Th-B (fiche 5.13) | fait |
| 0.8.14 | Infiltrations | Débits d'air par les défauts d'étanchéité (fiche 5.6) : perméabilité à l'air, vent, tirage thermique, équilibre de pression | fait |
| 0.8.16 | DH | Degrés-heures d'inconfort (fiche 13.5) sur le jeu Th-D, comparaison au DH max ; confort adaptatif, règles Th-D des protections et des ouvertures, brasseurs d'air dans le calcul | fait |
| — | Brasseurs d'air (anticipé pour le DH) | `moteur/brasseurs.py` (fiche 8.32) : régulation, effet ΔθopBA sur le seuil d'inconfort, consommation ; classe `Brasseur`, `Groupe.volume_m3` et `Groupe.brasseurs` ; `tests/test_brasseurs.py` ; branchés sur le groupe en 0.8.4 | fait |
| 0.8.17 | Relecture | Correction : documentation (premier calcul et modules dans le README), avertissement du DH, appariement des études par nom, doublons et noms clarifiés ; résultats inchangés | fait |
| 0.8.18 | Interface | Streamlit : boîte en axonométrie (style cbsh_visuel), saisie, résultats ; briques pédagogiques à deux niveaux (Bbio, DH, semaine chaude) | fait |
| 0.9.0 | Fonctionnel | Outil utilisable de bout en bout : contrôle visuel, balcons, comparaison de deux variantes, calcul plus rapide | fait, hors mise en ligne (accord et lien en attente) |
| 0.9.2 | Pédagogie | Page d'accueil (comme Météo et Chaleur), équations montrées, explications | à faire |
| 0.9.6 | Diffusion | Module pédagogique séparé sur la diffusion de la chaleur (sans lien de calcul) | à faire |
| 0.9.8 | Validation | Calage sur plus de 10 RSEE de logements collectifs et sur OPEE ; cible Bbio à ± 10 % | à faire |
| 0.9.10 | Maison individuelle | Second usage | à faire |
| 1.0.0 | Diffusion publique | Version annoncée | à faire |

## En attente

- Mise en ligne de la 0.9.0 : accord explicite et lien de déploiement Streamlit (l'outil est prêt, voir
  `README.md`, « Mise en ligne »).
- Extraction OPEE en parquet (pour la 0.9.8).
- Accord de la DHUP sur l'usage des fichiers météo (avant la 1.0.0).
- Seuils du plan de contrôle : 1 % sur les cas analytiques, 0,1 % sur le bilan d'énergie, quartiles OPEE.
- Chapitre V de l'annexe à l'article R. 172-4 (catégories de contraintes extérieures), absent de `_sources/` : il
  fixe la colonne du DH max (hypothèse 76 de `docs/audit.md`).
- RSET correspondant aux classeurs horaires de Paris, Sète et Nice : leur DH diffère de celui des RSET présents
  (345,5 contre 372,7 °C.h pour Paris), ce qui interdit de comparer les températures heure par heure.

## Points à reprendre

- **Interface, suites de la 0.9.0** :
  - fait en 0.9.0 : contrôle visuel dans un navigateur et capture du `README.md` ; balcons et casquettes ;
    comparaison de deux variantes ;
  - saisies restantes : masque lointain (immeuble en face), joues et loggias, Sw2, gestion des brasseurs par
    thermostat (à attendre le calage du DH de Sète, voir plus bas), plusieurs groupes (traversant et non
    traversant). Le Uw horizontal ne concerne pas la boîte (pas de baie en toiture) ;
  - briques à écrire (0.9.2) : bilan des flux d'une journée (baies, parois, ventilation, apports, inertie),
    effet des protections mobiles, rafraîchissement nocturne, Bbio max et ses modulations, brasseurs d'air,
    effet d'un balcon selon l'orientation ;
  - comparaison : superposer la référence sur les graphiques des briques (aujourd'hui : un tableau d'écarts) ;
  - ouvrir une étude (RSET) dans l'interface, avec `outils/lire_rset.py` ;
  - couleurs des graphiques : passer le validateur de palettes (daltonisme) quand `node` est disponible ;
  - semaine chaude : les protections restent baissées à 75 % jour et nuit sur la boîte de départ ; à expliquer
    dans la brique ou à vérifier dans `moteur/protections.py` ;
  - brique DH : le dernier jour de la période de confort adaptatif est incomplet, son maximum extérieur chute sur
    le graphique ;
  - temps de calcul : 15 s avec les infiltrations et 10 s sans sur le poste chargé (25 s avant la 0.9.0) ; voir
    le point « temps de calcul » plus bas.

- **Ordre des versions revu le 14/11/2026** (deux fois) : « Cas de référence » intercalé en 0.8.10 ; « Protections
  et ouvertures » passe de 0.9.4 à 0.8.12, avant le DH (0.8.16) et l'interface (0.8.18) ; le numéro 0.9.4 n'est
  plus utilisé ; « Infiltrations » ajouté en 0.8.14. Raison : le besoin de froid de l'outil vaut plusieurs fois celui des études, si bien que ni le Bbio
  ni le DH ne sont exploitables sans ces modules. `CHANGELOG.md` (0.8.8 et avant), `docs/audit.md` (0.8.8 et avant)
  et les commentaires du code citent encore les anciens numéros : 0.9.4 pour les protections, 0.8.10 pour le DH,
  0.8.12 pour l'interface. Depuis : DH en 0.8.16 (fait), interface en 0.8.18.
- **Seuils de la gestion automatique des protections** (`gpm_auto_...` de `donnees/hypotheses.csv` : 10 000 lux,
  26 et 24 °C) : valeurs de l'outil, absentes de l'annexe et des fichiers d'étude. À lire dans Climawin ou
  Pleiades (écran de la gestion automatique des volets), puis à corriger. Concernent Sète et Nice.
- 0.9.8 : stores vénitiens (20 baies sur 80 à Nice, lues sans protection), seconde protection mobile, gestion
  automatique de l'ouverture des baies.
- 0.9.8 : éclairage : les protections fermées réduisent la lumière naturelle (fiche 5.10, éq. 235 à 237) ; l'outil
  calcule encore Becl baies nues (écart actuel aux études : 0,1 kWh/m²).
- 0.9.8 : **DH face aux études** (voir `docs/audit.md`, 0.8.16) : 35 à 41 % trop bas à Sète (brasseurs de nuit
  en gestion par thermostat), 28 % trop haut sur le groupe non traversant de Nice. À examiner avec des sorties
  horaires du même calcul que le RSET.
- 0.9.8 : ventilation du calcul Th-D : système du projet (débits, échangeur, surventilation mécanique) au lieu du
  débit du Bbio sans échangeur (hypothèse 75).
- 0.9.8 : chauffage du calcul Th-D : émetteur conventionnel du Bbio, faute du système du projet ; relances du
  chauffage (fiche 8.5, tableau 92), sans effet attendu sur le DH.
- 0.8.18 : saisie du caractère climatisé du groupe (`Groupe.climatise`), pour le DH max.
- 0.9.8 : ouverture des baies la nuit : la fiche 5.13 ne décrit le réglage qu'en journée (7 h à 23 h) ; l'outil
  garde la position du soir (hypothèse 59), ce qui pèse sur le rafraîchissement nocturne.
- 0.9.8 : **indicateur d'infiltrations d'hiver** (`H_V_Def_Hiver`) : celui des études vaut 3 à 6 fois la moyenne de
  janvier et février de l'outil, alors que le chauffage, lui, est proche. Pistes : les entrées d'air du projet
  gardées dans le calcul du Bbio (un essai hors moteur remonte l'outil à 43 à 77 % de l'indicateur) ; la définition
  même de l'indicateur, que la version texte de l'annexe ne donne pas ; le tirage thermique sur toute la hauteur
  de la zone. À trancher avec une sortie horaire d'un moteur, ou une étude sans entrée d'air.
- 0.9.8 : bilan aéraulique par zone (une pression commune à tous les groupes, échanges par le hall), au lieu d'un
  bilan par groupe ; sans effet sur les cinq études, qui n'ont qu'un groupe par zone.
- 0.9.8 (ou 0.8.18 si l'interface le demande) : **temps de calcul d'une étude** (800 composants, deux groupes :
  10 à 20 s pour le Bbio, autant pour le DH). Profil mesuré en 0.8.17 sur l'étude de Paris : équilibre de pression
  des infiltrations 35 % (`infiltrations.equilibre` : 62 évaluations du bilan par heure, en Python) ; rayonnement
  reçu par chaque paroi 30 % (`solaire.environnement_proche`, appelé 1 105 fois : chaque baie est recalculée par
  les sollicitations, les protections et l'éclairage) ; protections mobiles 8 % ; modèle du groupe 4 %. Pistes :
  résoudre l'équilibre par une méthode de Newton ou en numpy, calculer le rayonnement une fois par composant.
  Fait en 0.9.0 : équilibre de pression par fausse position bornée (cinq fois moins d'évaluations du bilan). Reste, sur la boîte :
  ouvertures et protections mobiles (15 % du temps), boucle horaire de `calculer_besoins`.
- Fait en 0.8.17 : calcul d'une heure du groupe en deux temps (`preparer_pas`, `resoudre_pas`) ; gain de 10 à 15 %
  sur un groupe simple, nul sur une étude.
- 0.9.8 : baies sur un espace tampon (coefficient b et soleil), aujourd'hui lues comme donnant sur l'extérieur.
- 0.9.8 : U des baies en hiver : l'indicateur `Hg_es_hiver` des études est 1 à 15 % sous la somme des A × U sans
  protection de l'outil (protections fermées la nuit ?) ; ventilation : `H_Vent_Hiver` des études vaut 0,1397 × débit,
  contre 0,34 × 0,5 = 0,17 dans l'outil (éq. 382) : à comprendre.
- 0.9.8 : masques par tranches azimutales : les études donnent le même horizon à toutes les orientations d'un
  bâtiment, alors que la fiche 3.2 compte les tranches depuis la normale à la paroi (hypothèse 7) : vérifier la
  convention des logiciels.
- 0.9.8 : débit de ventilation du Bbio : les études donnent environ 1,2 à 1,5 m³/h par m² habitable en occupation
  (`Qv_occ_BBIO`), à comparer au débit moyen de l'hypothèse 39.
- 0.8.18 : saisie de l'exposition au bruit (BR1 à BR3) et de la hauteur sous plafond moyenne, pour le Bbio max.
- 0.9.8 : infiltrations par la perméabilité de l'enveloppe (nulles pour l'instant) ; relances du
  chauffage avant l'occupation (fiche 8.5) ; humidité de l'air (terme Cv.ω de Hg_ei, éq. 333).
- 0.8.12 : sans protections mobiles ni ouverture des baies, le besoin de froid est surestimé (voir `docs/audit.md`,
  résultats de la 0.8.6) : à reprendre avec ce module, avant tout calage.
- 0.8.18 : saisie de Sw2 (défaut : nul, voir `docs/audit.md`, hypothèse 21), de l'inertie, des ponts thermiques et
  du Uw horizontal des baies de toiture.
- 0.9.8 : flux solaires et rayonnement froid des ponts thermiques (fiche 5.19, éq. 300 et 306), parois sur le sol
  (pour l'instant : U saisi × b), échanges entre groupes — à reprendre si le calage sur les RSEE le demande.
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
