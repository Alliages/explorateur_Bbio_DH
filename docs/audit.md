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

## 0.8.2 — solaire

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Soleil dans l'axe de la normale, paroi horizontale, mur sud, mur nord à midi | Annexe III, fiche 3.2, éq. 7 à 11, calcul à la main | identique (< 1 %) |
| Diffus sur un mur = Idi / 2, réfléchi = 0,1 × global horizontal | Fiche 3.2, éq. 9 et 10 | identique |
| Direct + diffus sur une toiture = global horizontal, 8 zones, 8 760 h | Fichiers météo | écart < 0,1 % |
| Irradiation horizontale annuelle (Th-BC) | Ordres de grandeur connus (Trappes, Nice) | 1 140 (H1b) à 1 631 kWh/m² (H3) |
| Débord, joues, plan lointain, tranches : cas géométriques | Fiche 3.2, éq. 19 à 22, calcul à la main | identique (< 1 %) |
| Sf des parois opaques | Règles Th-Bât, fascicule Parois opaques, formules 259-260, calcul à la main | identique |

Irradiation annuelle Th-BC (kWh/m²), sans masque : horizontale / sud / ouest / nord / est.

| Zone | Horiz. | Sud | Ouest | Nord | Est |
|---|---|---|---|---|---|
| H1a | 1 157 | 833 | 693 | 473 | 710 |
| H1b | 1 140 | 813 | 694 | 491 | 697 |
| H1c | 1 240 | 887 | 748 | 485 | 751 |
| H2a | 1 199 | 898 | 736 | 496 | 728 |
| H2b | 1 217 | 872 | 737 | 500 | 761 |
| H2c | 1 368 | 955 | 818 | 513 | 792 |
| H2d | 1 570 | 1 206 | 933 | 491 | 934 |
| H3 | 1 631 | 1 213 | 966 | 524 | 971 |

### Décisions et hypothèses

3. **Convention d'orientation (confirmée).** Fiche 3.2 : azimut de la paroi 0° sud, 90° ouest, 180° nord, 270° est ;
   azimut du soleil compté depuis le sud, sens horaire. L'outil ramène toute orientation dans [−180 ; 180[ (270 → −90),
   comme `Psi` : mêmes résultats. Inclinaison : 0 = horizontale vers le haut, 90 = verticale, 180 = horizontale vers
   le bas.
4. **Direct avec soleil couché.** Les heures où `dirN` > 0 alors que `Gamma` = 0 (H1a : 28 h en Th-BC, 26 h en Th-D ;
   H2d : 30 h et 27 h ; `dirN` jusqu'à 100 W/m²) sont calculées par les formules telles quelles : un mur vertical
   tourné vers le soleil reçoit du direct (cos θ = cos(ψ − α)), une toiture n'en reçoit pas (sin γ = 0). Effet :
   au plus 0,8 kWh/m² par an sur un mur est ou ouest, soit environ 0,16 % de son direct annuel.
5. **Polynôme de l'éclairement direct.** La fiche 3.1 donne EDn = IDn × P(x) sans définir x. Lecture retenue : x =
   hauteur du soleil en degrés. Efficacité obtenue : 104 lm/W à 30°, 108 lm/W à 60°, maximum 109 lm/W vers 70° ;
   valeurs usuelles pour le rayonnement direct.
6. **Masques proches gauche et droite.** La fiche 3.2 applique le masque « gauche » quand φ = ψ − α > 0, soit un
   soleil à l'ouest d'une façade sud : gauche et droite s'entendent pour un observateur dehors, face à la paroi.
7. **Tranches azimutales.** La figure 10 de la fiche n'est pas lisible dans la version texte. Convention de saisie de
   l'outil : la 1re tranche couvre l'azimut relatif du soleil de −180° à −170°, la 19e de 0° à 10°.
8. **Plan vertical lointain, cas d'égalité.** La fiche donne F = 1 si dhE > hpE et F = 0 si dhE < hpE ; l'égalité
   est traitée comme une ombre (F = 0).
9. **Paroi opaque : facteur solaire.** Sans Sf saisi : Sf-c = α × Up-C × 0,04 et Sf-e = α × Up-E × 0,07, avec
   1/Up-E = 1/Up-C + 0,03 (règles Th-Bât ; le signe, illisible dans le texte, est celui qu'imposent Rse-E > Rse-C et
   Rsi-E = Rsi-C). `u` est lu comme Up-C.

### Simplifications de cette version (à lever plus tard)

- Pas de protection mobile (Rprot = 0, module 0.9.4), pas d'espace tampon (bsolaire = bvoute = 1).
- Sw global : la décomposition Sw1 / Sw2 / Sw3 (règles Th-Bât, formules 173 à 176, données de la norme XP P50-777)
  est reportée à 0.8.4. Le facteur de pertes solaires flf, qui ne porte que sur Sw1, est nul (fiche 5.10).
- Rayonnement froid : U saisi, sans la correction d'inclinaison des fiches 5.10 (éq. 207) et 5.17 (éq. 294). Sans
  effet sur les parois verticales, dont le facteur Max(cos β ; 0) est nul.
- Th-D, parois opaques : Sf dépend de la période de confort adaptatif (fiche 5.17, éq. 291-292), calculée en 0.8.10.
  D'ici là, le flux Th-D d'une paroi opaque exige cette période en entrée.
- Arbres à feuilles caduques non traités.

## Brasseurs d'air (anticipé, sans numéro de version)

`moteur/brasseurs.py`, annexe III, fiche 8.32 (éq. 1646 à 1666, tableaux 257 et 258) ; effet sur le DH par la
fiche 13.5, éq. 2547. Le module n'est pas encore branché : il le sera au modèle du groupe (0.8.4) et au DH (0.8.10).

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Δθ à 1 m/s, θrm = θi : 3,0498 °C ; à e m/s avec θrm − θi = 2 °C | Fiche 8.32, éq. 1659, calcul à la main | identique (< 1 %) |
| Débit et puissance corrigés (certifié, justifié, déclaré), régime intermédiaire à 60 % | Fiche 8.32, § Paramètres | identique |
| Ratbr plafonné à 15 m² par brasseur ; test de cohérence avec RatUs (0,54 jour, 0,36 nuit en logement collectif) | Fiche 8.32, tableau 257 | conforme |
| Hystérésis manuelle (arr = V1 − 2, V1 = θiifr+ + Δθconf_adapt + 1, V2 = V1 + 4) sur une suite de températures | Fiche 8.32, éq. 1646, 1648, 1654, tableau 258 | conforme |
| 60 m², 150 m³, 1 brasseur de 5 000 m³/h : v = 0,427 m/s, Δθ_p = 1,489 °C, groupe (jour) 0,689 °C | Fiche 8.32, éq. 1656 à 1660, calcul à la main | identique (< 1 %) |
| Année entière, 2 types de brasseurs | Temps de calcul | 0,07 s |

### Hypothèses de l'outil

10. **hlég = case des scénarios** (heure légale de fin de pas, 1 à 24). « 6 < hlég ≤ 22 » couvre les pas de 6h-7h
    à 21h-22h ; le blocage manuel « hlég > 23h » commence au pas de 23h-24h, qui reprend la position du pas de
    22h-23h. Réglages : `heure_debut_jour`, `heure_fin_jour`, `brasseur_heure_blocage`.
11. **Δθop_3_br_man de nuit = 1 °C.** Le tableau 258 ne donne qu'une valeur, lue comme une cellule fusionnée sur les
    colonnes jour et nuit.
12. **Période d'utilisation en Th-D = période de confort adaptatif** (§ 8.32.3.1), bien que le § 8.32.3.3 parle
    d'Aut_fr_progr (période de refroidissement, propre au mode Th-C).
13. **Test de cohérence lu « ≤ »** : le texte dit « ne peut être supérieure », l'équation écrit « < ». Une surface
    brassée égale à la surface occupée est donc admise.
14. **Consommation × Nbr.** L'éq. 1663 écrit Wabs_BA_p = Pelec_br_p, puissance d'UN brasseur, alors que la
    nomenclature définit Wabs_BA_p comme la consommation de l'ensemble des brasseurs du type. L'outil multiplie par
    Nbr_p. Sans effet sur le DH, sauf par la chaleur dégagée dans le groupe (éq. 1664).
15. **Première heure** : brasseurs à l'arrêt (pas d'heure précédente).
16. **Ordre des règles** : arrêt hors période, hors occupation ou hors plage ; sinon hystérésis ; puis, la nuit en
    habitation, bridage à l'intermédiaire et, en gestion manuelle, blocage sur la position précédente.

### Points de vigilance

- **Saut à 0,2 m/s.** La formule donne +0,10 °C juste au-dessus de 0,2 m/s (θrm = θi) et 0 en dessous ; repris tel
  quel.
- **Brasseur de nuit en gestion manuelle.** Bloqué de 23h à 6h, il ne peut démarrer qu'au pas de 22h-23h : s'il ne
  fait pas assez chaud à cette heure-là, il reste arrêté toute la nuit. Conséquence directe du texte, à montrer dans
  la partie pédagogique.
- **Volume du groupe** : nouveau champ `Groupe.volume_m3`, exigé seulement en présence de brasseurs. Le modèle de la
  fiche 8.32 vaut pour une hauteur sous plafond inférieure à 3 m ; non contrôlé (la surface du groupe n'est pas la
  surface au sol).
- **Groupe climatisé** : brasseurs interdits (fiche 8.32) ; le groupe ne porte pas encore cette information (0.8.4).
- **Autres usages** : RatUs n'est saisi que pour le logement collectif (tableau 257, usage 2).

## 0.8.4 — groupe

`moteur/groupe.py` (annexe III, fiche 5.21, éq. 311 à 373), `moteur/enveloppe.py` (fiches 5.10, 5.17, 5.19).
Les équations ont été relues sur les pages 312 à 320 du PDF de l'annexe III (la version texte perd les symboles).

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| his = 9,1 W/m².K ; Hg_is, Hg_ms, Cmq, ptrm pour 50 m² d'inertie moyenne | Fiche 5.21, éq. 320 à 326, 370, calcul à la main | identique |
| Classes d'inertie quotidienne et séquentielle | Fiche 5.21, tableaux 53 et 54 ; Th-Bât, tableau 89 | identique |
| Régime permanent sans baie : θi = te + Φ / (Hv + 1 / (1/Hg_is + 1/H_TH)) | Réseau RC, calcul à la main | identique (< 1e-6) |
| Régime permanent avec baies : déperditions = apports | Bilan | identique (< 1e-6) |
| Refroidissement de la masse seule : θ = te + Δθ.exp(−t.Hg_em / Cmq) sur 100 h | Solution exacte | écart < 1 % |
| Échangeur d'efficacité 0,5 : déperdition par l'air divisée par deux à l'équilibre | Fiche 6.1, éq. 382 | identique |
| Matrice : l'effet de 10 W/m² ne dépend ni de la météo ni des apports | Linéarité du modèle | identique |
| Chaque heure : chaleur prise par la masse = somme des flux (H1a, H3 en Th-BC ; H2d en Th-D) | Bilan d'énergie | écart < 1e-6 W |
| Année : somme des flux = variation de chaleur de la masse | Plan de contrôle (0,1 %) | conforme |
| U d'un mur couché, d'une toiture relevée, interpolations à 45° et 135° | Fiche 5.17, § 5.17.3.4, calcul à la main | identique |
| Année entière, 2 murs, 2 baies, brasseurs | Temps de calcul | environ 0,2 s |

### Lectures du texte et hypothèses de l'outil

17. **Éq. 366 : terme Hg_es.θes rétabli.** L'équation imprimée de φmtot ne contient pas Hg_es.θes dans le crochet,
    alors que l'éq. 367 (θs) le contient. Sans lui, le bilan d'énergie n'est pas respecté : les déperditions des
    baies agiraient sur θs mais pas sur la masse. L'outil écrit
    φmtot = φmq + Hg_em.θem + U3/U2 × [φs + Hg_es.θes + U1 × ((φi + φsys-conv) / Hg_ei + θeieq)], forme de la
    méthode Th-BCE 2012 ; le bilan horaire est alors exact.
18. **Part radiative frs.** La nomenclature cite frs (« part radiative des apports internes récupérée au nœud θs »)
    et l'éq. 372 l'utilise, mais aucune équation ne la définit ; l'éq. 361 ne donne à θs que la part reçue par les
    baies. L'outil retient le complément, frs = (Atparois − Amq − Abaies) / Atparois (parois légères), si bien que
    tout apport radiatif est distribué : baies (éq. 349, moins la part Hg_es / (Abaies.his) qui repart dehors),
    masse (éq. 350), parois légères. Même répartition que le Prs de la méthode 2012.
19. **Soleil de courte longueur d'onde au nœud θs.** L'éq. 351 est imprimée « frld » ; lue comme frsd (nomenclature :
    part restante du flux solaire transmise au nœud θs). φs reçoit donc frsd × (1 − fsa) × Fs1, que l'éq. 361
    n'écrit pas.
20. **Puissance radiative de l'émetteur** : répartie comme les apports internes radiatifs (baies, masse, parois
    légères). L'éq. 372 n'en donne que les parts frs et frm ; la part des baies serait perdue.
21. **Sw2 par défaut = 0** (`sw2_part_defaut`). Les textes ne donnent pas de répartition de Sw entre Sw1 (courte
    longueur d'onde) et Sw2 (réémis) : elle vient de la norme XP P50-777, produit par produit. Par défaut, tout Sw
    est compté en Sw1 ; `sw2_e` et `sw2_c` permettent de saisir Sw2. Sw3 = 0 sans protection intérieure. Effet de
    Sw2 : sa part entre par la température équivalente des baies θes (éq. 342-343) au lieu d'être répartie entre
    l'air et les parois.
22. **Température initiale du groupe : 18 °C** (`theta_groupe_initiale`). La fiche fixe θms, θma (18 °C) et les
    moyennes glissantes (18 et 19 °C), pas θmq ni θi au premier pas.
23. **Moyennes glissantes.** L'éq. 353 somme de h−1−24 à h−1 (25 termes) et divise par 24 : lue comme la moyenne
    des 24 heures précédentes ; de même 336 heures pour l'éq. 357. Pendant les 24 premières heures (les 14 premiers
    jours), la moyenne vaut 18 °C (19 °C), comme l'indiquent les notes.
24. **Inerties séquentielle et annuelle.** Actives en Th-D seulement (§ 5.21.3.2). ΔHg nul quand les surfaces
    d'échange sont égales (note de la fiche) : avec les classes par défaut du tableau 89 (Ams = 2,5 pour
    « moyenne », comme Amq), l'inertie séquentielle n'a alors aucun effet. Un écart de résistance négatif
    (Ams > Amq), non envisagé par la fiche, est traité comme nul. Une masse lente sans capacité propre (ΔC = 0)
    est découplée. Cms « légère » : 250 kJ/K/m² (annexe III) et non 260 (Th-Bât, tableau 89).
25. **U d'une paroi inclinée, flux descendant.** L'interpolation imprimée entre 120° et 150° (éq. 294) donne
    Uhoriz,des à 120° et Uvert à 150° : inversion corrigée, pour raccorder les plages voisines. Le U saisi est lu
    comme celui de la position du type de la paroi (mur : verticale ; toiture : flux ascendant ; plancher bas :
    flux descendant) ; une paroi garde par défaut l'inclinaison de son type.
26. **Baie horizontale sans `uw_horizontal`** : le Uw vertical est repris. Baie inclinée au-delà de 90° : traitée
    comme verticale (cas non décrit).
27. **Ventilation.** Débit constant saisi sur le groupe ; Hg_ei = 0,34 × débit (fiche 6.1), sans le terme d'humidité
    Cv.ω de l'éq. 333 ; air soufflé à te + ε × (θi de fin d'heure précédente − te), ε = 0,5 par défaut (Bbio),
    y compris en Th-D faute de mieux (à revoir en 0.8.10). Infiltrations nulles.
28. **Chaleur des brasseurs** (Φth-BA-vc, fiche 8.32, éq. 1664) : ajoutée aux apports convectifs du groupe.

### Simplifications de cette version (à lever plus tard)

- Échanges entre groupes nuls (φmig de l'éq. 365 et Hs,ig,eq de l'éq. 367, non définis dans la fiche).
- Ponts thermiques : déperdition l × ψ seule ; ni flux solaire (éq. 300) ni rayonnement froid (éq. 306).
- Parois sur le sol ou sur un local non chauffé : A × b × U avec la température extérieure, b saisi (1 par défaut).
- Apports internes et puissance du système fournis par l'appelant : le lien avec les scénarios et les consignes
  est l'objet de la 0.8.6.
- Brasseurs : la période d'utilisation, l'occupation, la consigne et l'écart de confort adaptatif sont fournis par
  l'appelant (0.8.10).

### Points de vigilance

- **Changement de comportement** : une `Paroi` de type toiture ou plancher bas créée sans inclinaison était
  verticale ; elle est maintenant horizontale (0° ou 180°). Le rayonnement froid des baies et des parois inclinées
  change avec le U corrigé ; rien ne change pour une paroi dans la position de son type.
- **Limite du modèle** : il faut H_TH,k+pt < Hg_ms (éq. 339) et Amq + Abaies ≤ Atparois = 4,5 × Agr (éq. 351) ;
  sinon l'outil refuse le groupe avec un message clair.
- **Hg_is ne dépend que de la surface du groupe** (Atparois = 4,5 × Agr) : la hauteur sous plafond et la forme du
  logement n'entrent pas dans le modèle.

## 0.8.6 — besoins

`moteur/besoins.py` (annexe III, fiches 4.5, 4.6, 8.1, 13.1), `moteur/apports.py` (fiche 4.1),
`moteur/eclairage.py` (fiches 5.10 et 7.1). Équations relues sur les pages du PDF : 60, 76-77, 86 à 93, 479,
521 à 528.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Nadeq à 8, 30, 50 et 65 m² par logement | Fiche 4.1, éq. 35-36, calcul à la main | identique |
| 650 m², 10 logements : 18,39 adultes équivalents, 1 655 W d'occupants, 3 335 W d'usages au maximum | Fiche 4.1, éq. 33 à 41 ; paramètres du classeur | identique |
| Coefficients d'éclairement K1 = 0,0407, K2 = 0,6033, K3 = 0,7023 | Fiche 7.1, K1vn à K3vn, calcul à la main | identique |
| Courbe C2 résidentielle aux points A, B, G, J et entre eux | Fiche 7.1, figure 86 | identique |
| Groupe sans baie : 0,9 W/m² pendant toutes les heures d'éclairage autorisé | Fiche 7.1, éq. 789 | identique |
| Droite du groupe : 15 °C sans émission, 17 °C à 500 W, consigne 19 °C → 1 000 W | Fiche 8.1, éq. 803 à 807 | identique |
| Heures chauffées (refroidies) : sonde à la consigne | Émetteur de puissance illimitée | écart < 1e-6 °C |
| Automate des saisons sur des journées synthétiques (arrêt, redémarrage unique, été, automne) | Fiche 4.6, éq. 76 à 90 | conforme |
| Chaque heure, émission comprise : chaleur prise par la masse = somme des flux | Bilan d'énergie | écart < 1e-6 W |
| Année entière | Temps de calcul | environ 0,6 s |

Immeuble d'essai (650 m², 10 logements, murs U = 0,25, toiture 0,15, 110 m² de baies Uw = 1,3 et Sw = 0,5 dont
60 m² au sud, ventilation 600 / 1 350 m³/h), altitude 100 m, kWh/m².an :

| Zone | Bch | Bfr | Becl | Chauffage arrêté / repris (jour) | Froid démarré / arrêté (jour) |
|---|---|---|---|---|---|
| H1a | 12,0 | 21,7 | 1,6 | 73 (reprise 80, arrêt 88) / 311 | 111 / 284 |
| H2b | 9,2 | 25,0 | 1,6 | 68 / 321 | 93 / 299 |
| H3 | 2,6 | 46,3 | 1,6 | 57 / 332 | 55 / 322 |

**Le besoin de froid est surestimé** : cette version n'a ni protections mobiles, ni ouverture des baies, ni
by-pass de l'échangeur ; le groupe ne peut évacuer la chaleur du soleil que par le système. Le froid démarre ainsi
dès le printemps. Bch et Becl sont dans les ordres de grandeur attendus pour un immeuble récent. Aucun calage n'a
de sens avant le module 0.9.4.

### Lectures du texte et hypothèses de l'outil

29. **Besoin de froid compté d'office.** La fiche 8.1 parle d'un émetteur de refroidissement « par groupe refroidi
    (iclim = 1) » ; l'outil calcule Bfr pour tout groupe, selon le principe de la RE2020 (un besoin de froid entre
    dans le Bbio que le bâtiment soit climatisé ou non), que je n'ai pas retrouvé écrit dans l'annexe III.
    `calculer_besoins(refroidissement=False)` donne l'autre lecture. `Groupe.climatise` ne sert qu'aux brasseurs.
30. **Surfaces.** `Groupe.surface_m2` est lue à la fois comme surface utile Agr (modèle thermique, apports,
    éclairage) et comme surface de référence des kWh/m². La surface habitable de l'éq. 33 vaut 0,9 × Agr
    (`logements_ratio_surface`) : elle fixe le nombre d'adultes équivalents et porte les 5,7 W/m² d'usages ; les
    10 % de circulation n'ont ni occupant ni usage. À vérifier sur un RSEE (0.9.8).
31. **Relances non traitées** (fiche 8.5) : la consigne est celle du scénario, sans anticipation du retour des
    occupants (θiich_relance de l'éq. 800 ignoré). Les variations spatiale et temporelle sont nulles en Bbio.
32. **Écarts d'inconfort (éq. 60-61).** Les formules du chaud sont imprimées avec l'indicateur du froid
    (i_inconf_cons,ch + 1) / 2 ; lues comme i × (i + 1) / 2 du même indicateur : l'écart vaut |seuil − θop| en
    occupation et en inconfort, zéro sinon.
33. **Inconfort chaud des saisons : catégorie d'ambiance 1** (fiche 4.6, tableaux 9 et 10), donc le seuil
    MAX(consigne de refroidissement ; 0,33 × θrm + 18,8 + 2). Les éq. 82 à 84 écrivent « cons,fr » ; le texte et
    les tableaux renvoient à la catégorie.
34. **θrm nul le premier jour** (éq. 57), appliqué tel quel : la moyenne glissante de la température extérieure
    part de 0 °C et met quelques semaines à rejoindre le climat ; d'ici là le seuil chaud est la consigne.
35. **« hlég = 9 h » = case 9** (même convention que l'hypothèse 10) ; le jour j est le jour légal du calendrier.
    Aux deux changements d'heure, la journée compte 23 ou 25 heures : les moyennes divisent par les heures réelles.
36. **Fenêtres glissantes des saisons.** Cumuls sur 28 jours au plus. L'inconfort froid se cumule à partir du
    lendemain d'un arrêt du chauffage (premier test le surlendemain) et à partir du 253e jour (sur une journée) ;
    l'inconfort chaud à partir du 8e jour (sur une journée) ; le besoin moyen de chauffage repart de zéro à un
    redémarrage, et n'est testé qu'après une semaine de fonctionnement.
37. **Températures de l'heure** : le groupe est recalculé avec la puissance retenue, au lieu des interpolations
    des éq. 825-826 ; résultat identique, le modèle étant linéaire. La droite du groupe est écrite en watts
    (10 W/m² × surface).
38. **Éclairage.** Baies sans protection et non diffusantes, même Tl pour le direct, le diffus et le réfléchi
    (éq. 225-226) ; toute la surface du groupe a accès à la lumière naturelle (Ratio_ecl_nat = 1) et porte le
    1 W/m², circulation comprise. Courbe C2 : celle de l'éclairage résidentiel (figure 86, point G à 200 lux et
    0,05), plus sévère que la ligne « interrupteur manuel » du tableau 79 (700 lux, 0,3).
39. **Ventilation du Bbio** : débit moyen = base + (pointe − base) × 14 / 168 (fiche 6.2, Dugd = 14, Cdep = 1),
    constant sur l'année (le scénario de ventilation du logement vaut 1 en permanence).
40. **Brasseurs d'air** : sans effet sur les besoins (leur chaleur n'est pas comptée en Th-B) ; ils servent au DH.
41. **Format de `hypotheses.csv`** : 12 lignes (dont 2 de la 0.8.4) portaient un « ; » dans leur source ou leur
    commentaire ; le lecteur CSV tronquait alors la source. Remplacé par une virgule, sans changement de valeur.

### Simplifications de cette version (à lever plus tard)

- Pas de protections mobiles, pas d'ouverture des baies, pas de by-pass de l'échangeur (0.9.4).
- Infiltrations nulles ; humidité non traitée (pas de besoin latent).
- Un seul usage : logement collectif.

## 0.8.8 — Bbio

`moteur/bbio.py` (annexe III, fiche 13.1, éq. 2375 à 2386 ; annexe à l'article R. 172-4 du code de la construction
et de l'habitation, chapitres I à III, version du décret n° 2026-200 du 18 mars 2026). Pages relues sur le PDF :
annexe III 86 à 89 (saisons), annexe à l'article R. 172-4 pages 8 et 9 (Bbio max des logements collectifs).

Trois sources nouvelles, toutes gardées hors du dépôt :

- deux **sorties horaires d'un moteur Th-BCE** (8 760 heures, zone H3, jeu Th-D, altitude corrigée 100 m) :
  température extérieure, occupation, températures d'air, radiante et opérative du groupe, θrm, seuils de confort
  et degrés-heures ;
- le module `dh_re2020.py` de Météo et Chaleur, qui recalcule les DH de ces sorties ;
- cinq **études réglementaires de logements collectifs** (13 groupes, zones H1a, H2a et H3) et une étude de maisons
  (4 groupes, H2b), lues dans leurs sorties du mode Th-B.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Bbio max : 13 groupes de logements collectifs (H1a, H2a, H3 ; BR1 à BR3 ; 92 à 4 872 m²) | Sorties Th-B de 5 études | écart ≤ 0,05 point (arrondi des sorties) |
| Mbgéo, Mbsurf_moy, Mbsurf_tot, Mbbruit des mêmes groupes | Sorties Th-B | identiques à l'arrondi |
| Bbio = 2 × Bch + 2 × Bfr + 5 × Becl sur les mêmes groupes | Sorties Th-B (besoins à 0,1 kWh/m²) | écart ≤ 0,3 point (arrondi des besoins) |
| Zone et bâtiment : besoins et Bbio max pondérés par la surface de référence | Étude à deux zones (1 468,5 et 608,4 m²) | identique à l'arrondi |
| Modulations et Bbio max de trois cas | Annexe à l'article R. 172-4, calcul à la main | identique |
| Occupation du logement, 8 760 heures | Sorties horaires (6 748 heures occupées) | identique |
| Météo H3 Th-D, altitude corrigée 100 m | Sorties horaires | identique |
| θrm : jours UTC, nul le premier jour, 0,8 / 0,2 | Sorties horaires | écart < 1e-8 °C |
| Degrés-heures recalculés à partir de la température opérative et du seuil corrigé des sorties | Sorties horaires (399,25 et 1 438,03 °C.h) | écart < 1e-7 °C.h |
| Année entière, trois groupes | Temps de calcul | environ 1,5 s |

### Revue des quatre points de la 0.8.6

- **29, besoin de froid compté d'office : confirmé.** Dans les études, des groupes non climatisés
  (`Is_Climatise` = 0) ont un besoin de froid non nul : 1,3 et 1,7 kWh/m² en logements collectifs H1a, 0,7 à
  4,2 kWh/m² en maisons H2b. Le texte le dit à sa façon, fiche 5.13 : « une exception existe sur le mode de calcul
  Th-B pour calculer le besoin de froid en permettant une surventilation naturelle par ouverture des baies ».
  `refroidissement=True` reste la valeur par défaut.
- **30, surfaces : confirmé.** Un groupe d'habitation ne porte dans les études qu'une surface, la SHAB (sa surface
  utile est nulle), et sa surface de référence lui est égale (fiche 13.1, éq. 2375). `Groupe.surface_m2` est donc
  la surface habitable, pour le modèle thermique comme pour les kWh/m². Le ratio 0,9 de l'éq. 33 ne sert qu'aux
  apports internes (part du local d'habitation). La surface moyenne des logements du Bbio max est Sref / nombre de
  logements, sans ce ratio (annexe à l'article R. 172-4, chapitre I, XI).
- **31, relances : sans objet en Bbio.** Fiche 8.5, introduction : la relance « n'est appliquée que lors d'un calcul
  des consommations ». Les sorties horaires, calculées avec les systèmes du projet, la montrent : en hiver, la
  consigne normale revient deux heures avant les occupants (tableau 92, horloge à heure fixe), et la sonde remonte
  de 0,5 à 0,7 °C sur ces deux heures. À ne traiter que si le calcul Th-D le demande (0.8.10).
- **36, fenêtres glissantes des saisons : lecture maintenue.** Éq. 68 à 81 relues sur le PDF ; aucune des sources
  nouvelles ne donne les dates de saison d'un calcul Th-B, donc rien ne permet de trancher davantage. Seul
  changement : l'heure du test (hypothèse 42).

### Lectures du texte et hypothèses de l'outil

42. **« hlég » = heure légale de début de pas** (Hleg = IHJ + EHLO, fiche 3.1), et non la case des scénarios
    (hypothèses 10 et 35). Preuve : dans les sorties horaires, le seuil de confort passe au régime de jour
    (« 6 < hlég ≤ 22 », fiche 13.5) aux pas de 7h-8h à 22h-23h légales, soit hlég de 7 à 22 compté au début du
    pas ; la lecture « case » place mal 354 et 396 heures sur les deux fichiers. Le calendrier donne désormais
    `hleg` (= case − 1) et les saisons sont testées à hlég = 9 (pas de 9h-10h) au lieu de la case 9. Effet sur
    l'immeuble d'essai : Bch à ± 0,06 kWh/m², un redémarrage d'automne avancé d'un jour en H1a. **Les brasseurs
    d'air lisent encore la case** (hypothèse 10) : à aligner en 0.8.10.
43. **Altitude de 400 m exactement** : ligne « 400 m-800 m » du tableau Mbgéo, dont la première ligne est
    « < 400 m » ; la correction d'altitude de la météo, elle, range 400 m dans la tranche basse (fiche 3.1, « ≤ »).
44. **Bbio max par groupe**, comme dans les sorties des études : exposition au bruit du groupe, surface moyenne des
    logements de la zone, surface de référence de tous les logements collectifs du bâtiment. Zone et bâtiment :
    moyenne pondérée par la surface de référence (chapitre II, V).
45. **Agrégation des besoins.** La fiche 13.1 parle d'une « sommation sur l'ensemble des groupes » ; lue comme la
    somme des kWh rapportée à la somme des surfaces de référence, ce que confirment les études.
46. **Version du texte du Bbio max** : la plus récente (décret du 18 mars 2026), sans condition de date de permis.
    Pour les logements collectifs, les trois versions gardées en local ne diffèrent que par MbHSP, ajouté par ce
    décret. La hauteur sous plafond moyenne se saisit sur la zone ; non renseignée, MbHSP est nul.
47. **Comparaison au Bbio max** (`ecart_pct`, `respecte`) : indicative, sans valeur réglementaire. L'exigence porte
    sur le bâtiment.

### Résultats et limite de cette version

Immeuble d'essai de la 0.8.6 (650 m², 10 logements), altitude 100 m :

| Zone | Bch | Bfr | Becl | Bbio | Bbio max | Bbio sans le froid |
|---|---|---|---|---|---|---|
| H1a | 12,1 | 21,7 | 1,6 | 75,9 | 81,8 | 32,4 |
| H2b | 9,2 | 25,0 | 1,6 | 76,5 | 75,2 | 26,5 |
| H3 | 2,6 | 46,3 | 1,6 | 105,7 | 68,8 | 13,0 |

Dans les études de logements collectifs, Bfr vaut 0 à 0,4 kWh/m² en H2a, 1,3 à 1,7 en H1a et 3,3 à 7 en H3, pour
des Bbio de 17 à 74 points : **le besoin de froid de l'outil est de l'ordre de dix fois trop fort**, et il pèse
plus de la moitié du Bbio. Cause connue (0.8.6) : ni protections mobiles, ni ouverture des baies. La fiche 5.13
décrit pour le mode Th-B une ouverture des baies propre au calcul du besoin de froid : c'est elle qui manque le
plus. Bch (16 à 32 kWh/m² dans les études H1a et H2a hors petits groupes, 1 à 14 en H3) et Becl (1,6 à 2,2) sont
dans les ordres de grandeur. Le Bbio de cette version n'est pas comparable à celui d'une étude tant que le module
0.9.4 n'existe pas.

Autres constats, notés pour la suite dans `ROADMAP.md` : conventions du calcul des DH lues dans les sorties
horaires (seuils, période, correction des brasseurs) ; débit de ventilation du Bbio des études (`Qv_occ_BBIO`,
environ 1,2 à 1,5 m³/h par m² habitable).

## 0.8.10 — cas de référence

`outils/lire_rset.py` et `outils/comparer_reference.py`. Aucune équation nouvelle dans le moteur, sauf la hauteur
sous plafond moyenne du Bbio max (hypothèse 46 revue).

Cinq études de logements collectifs, gardées dans `_sources/` (hors dépôt), dix groupes en tout :

| Étude | Zone | Logiciel, moteur | Groupes (m²) | Parois, baies, ponts |
|---|---|---|---|---|
| Paris | H1a | Pleiades, 2026.E1 | 717 et 4 092 | 511, 317, 1 387 |
| Sète | H3 | Pleiades, 2026.E1 | 2 793 et 2 079 | 489, 299, 619 |
| Nice A (variante climatisée) | H3 | Climawin, 2022.E3 | 1 791 et 291 | 30, 77, 209 |
| Nice A (variante non climatisée) | H3 | Climawin, 2022.E3 | 1 791 et 291 | 30, 77, 209 |
| Nice B | H3 | Climawin, 2022.E3 | 1 488 et 497 | 36, 80, 213 |

Les deux logiciels écrivent le même format (celui du moteur du CSTB) : un seul lecteur suffit. Le fichier `.cwx`
de Climawin, lui, est une base Firebird 3 au schéma en partie chiffré : non utilisé.

### Vérifications : la lecture

| Contrôle | Référence | Résultat |
|---|---|---|
| Déperdition des parois opaques, somme des A × b × U (10 zones) | Indicateur `H_Th_op` des études | identique à 0,01 W/K |
| Surfaces des murs, toitures, planchers bas et baies, longueur des ponts thermiques | `A_opv`, `A_ophh`, `A_ophb`, `A_baies`, `L_PT` | identiques à l'arrondi (0,1 m²) |
| Ponts thermiques, somme des l × ψ sans coefficient b (Paris) | `H_Th_PT` | identique (95,22 et 500,66 W/K) |
| Bbio max des dix groupes | `O_Bbio_Max` | écart ≤ 0,05 point |
| Classe d'inertie, code 4 | Récapitulatif PDF d'une étude : « lourde » | conforme |
| Éclairage Becl des dix groupes | `O_B_Ecl_annuel` (1,6 à 1,9 kWh/m²) | écart ≤ 0,2 kWh/m² |
| Lecture et calcul d'une étude de 800 composants | Temps | 0,5 s et 9 s |

### Écarts constatés entre l'outil et les études

Besoins annuels en kWh/m², outil / étude. Variantes du froid : Sw des baies avec protection toute l'année
(« protections »), 2 volumes par heure en permanence sans échangeur (« surventilation »), les deux ensemble.

| Groupe | Bch | Bfr | Bfr, protections | Bfr, surventilation | Bfr, les deux |
|---|---|---|---|---|---|
| Paris, non traversant | 15,5 / 19,5 | 13,3 / 0,4 | 2,5 | 2,2 | 0,6 |
| Paris, traversant | 21,8 / 33,0 | 13,7 / 0,3 | 1,7 | 2,6 | 0,6 |
| Sète, traversant | 4,7 / 8,7 | 40,1 / 1,9 | 8,3 | 23,7 | 5,6 |
| Sète, non traversant | 3,4 / 4,4 | 31,4 / 3,4 | 8,7 | 17,3 | 5,7 |
| Nice A climatisée, traversant | 8,2 / 10,9 | 31,7 / 4,6 | 11,7 | 19,8 | 8,0 |
| Nice A climatisée, non traversant | 8,4 / 9,5 | 30,1 / 7,1 | 16,5 | 19,5 | 11,0 |
| Nice A non climatisée, traversant | 13,2 / 15,7 | 27,5 / 4,3 | 15,0 | 18,4 | 10,1 |
| Nice A non climatisée, non traversant | 16,1 / 17,1 | 22,9 / 5,6 | 15,0 | 15,7 | 10,7 |
| Nice B, traversant | 9,6 / 15,1 | 34,8 / 5,3 | 11,8 | 22,7 | 8,3 |
| Nice B, non traversant | 8,9 / 13,0 | 28,7 / 6,1 | 16,5 | 18,7 | 10,8 |

Lecture :

- **Froid : 4 à 46 fois trop fort.** Les protections mobiles sont le premier levier (elles divisent Bfr par 1,5 à
  8 à elles seules), l'ouverture des baies le second ; ensemble, ces deux bornes grossières ramènent Bfr à 1,5 à
  3 fois celui des études, et à 0,6 contre 0,3 à 0,4 à Paris. L'ordre de la 0.8.12 s'en déduit : protections
  d'abord. À Nice B, le froid de l'étude n'apparaît que de juin à septembre ; celui de l'outil, d'avril à octobre.
- **Chauffage : 6 à 46 % trop faible.** L'outil n'a pas d'infiltrations ; l'indicateur `H_V_Def_Hiver` des études
  vaut 0,5 à 2,3 fois la déperdition de leur ventilation. Variante « infiltrations de l'étude » (cet indicateur
  ajouté comme un débit constant sans échangeur) : Bch passe au-dessus des études (22,3 contre 15,1 à Nice B, 46,7
  contre 33,0 à Paris, 17,8 contre 8,7 à Sète). Les infiltrations comptent donc, mais l'indicateur d'hiver ne se
  transpose pas en débit constant : il faut le modèle de la méthode.
- **Baies en hiver** : la somme des A × U sans protection de l'outil dépasse `Hg_es_hiver` de 1 à 17 % ; l'étude
  donne aussi un U avec protection, plus faible, que l'outil n'utilise pas encore.
- **Ventilation** : `H_Vent_Hiver` vaut 0,1397 × `Qv_occ_BBIO` dans les dix groupes, contre 0,34 × (1 − 0,5) = 0,17
  dans l'outil (fiche 6.1, éq. 382), soit 22 % de plus dans l'outil. Écart non expliqué.

### Lectures et hypothèses de l'outil

46. **(revue) Hauteur sous plafond moyenne** : moyenne des hauteurs des zones de logements collectifs du bâtiment,
    pondérée par leur surface, et appliquée à toutes. Constat à Paris : zones à 2,65 et 2,71 m, MbHSP = 0,054 pour
    les deux, soit la moyenne pondérée 2,70 m. Les zones sans hauteur saisie ne comptent pas.
48. **Débit du Bbio** : `Qv_occ_BBIO` du groupe, constant sur l'année (le scénario de ventilation du logement vaut
    1 en permanence), avec l'échangeur à 0,5 (fiche 6.1). Remplace, pour une étude lue, le débit moyen de
    l'hypothèse 39.
49. **Baies lues sans protection mobile** : U, Sw (Sw1 + Sw2 + Sw3) et Tl « sp ». Les valeurs avec protection sont
    gardées dans `Reference.baies` pour la 0.8.12. *Levée en 0.8.12* : les valeurs « ap » (Sw1, Sw2, Sw3, U, Tli)
    et Typo_Permea_PM (0.9.10) sont lues dans `Baie` et entrent dans le calcul ; seule Tli « ap » reste inemployée
    (éclairage calculé baies nues).
50. **Espaces tampons** : une paroi opaque sur un espace tampon non solarisé prend son coefficient b et ne reçoit pas
    de soleil ; un pont thermique voit son ψ multiplié par b (fiche 5.19, éq. 304), alors que l'indicateur
    `H_Th_PT` des études ne l'applique pas ; une baie sur un espace tampon est lue comme donnant dehors (4 baies au
    plus par étude).
51. **Inertie** : codes 1 à 5 lus comme très légère à très lourde (seul le code 4 est recoupé) ; code 0 : valeurs
    saisies, l'inertie séquentielle l'étant alors aussi. Sans effet en Bbio pour la séquentielle.
52. **Masques lointains** : les 36 valeurs `Gamma` sont passées telles quelles au masque par tranches, donc comptées
    depuis la normale à la paroi (fiche 3.2, hypothèse 7). Les logiciels donnent pourtant le même horizon à toutes
    les orientations d'un bâtiment : convention à vérifier (0.9.8).
53. **Logements** : le nombre de logements est donné par zone ; avec plusieurs groupes dans une zone (aucun cas dans
    les cinq études), il est réparti au prorata des surfaces.
54. **Non repris**, et compté à chaque lecture : protections mobiles et ouverture des baies, perméabilité à l'air,
    flux solaires et masques des ponts thermiques, parois végétalisées, espaces tampons solarisés, zones d'un autre
    usage.

### Ce que les études apportent encore

- Classeurs horaires de Paris, Sète et Nice (températures et degrés-heures de sept scénarios météo, dont le
  réglementaire Th-D) : référence heure par heure pour le DH (0.8.14). Non exploités dans cette version.
- Période de confort adaptatif et DH réglementaires de chaque groupe (`Reference.confort`).
- Aucune sortie horaire du mode Th-B : les dates de saison (hypothèse 36) restent sans référence.

## 0.8.12 — protections et ouvertures

`moteur/protections.py` (annexe III, fiche 5.9, éq. 175 à 192, figures 34, 35, 38 et 44 ; fiche 4.1, éq. 50 à 53 ;
fiche 5.10, éq. 209 à 211 et 219 à 222) et `moteur/ouvertures.py` (fiche 5.13, éq. 240 à 255, tableaux 41 à 44,
figures 61 à 63). Équations, figures et matrices relues sur les pages du PDF : 62, 194 à 197, 200, 205 à 207,
232, 240, 259, 261, 262 et 267 à 270. Les matrices conventionnelles sont des images dans le PDF : leurs valeurs
ont été recopiées à la main dans les deux fichiers `donnees/protections_mobiles_*.csv`.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Occupation au sens des protections : 6 748 h occupées, 1 844 h d'absence de journée, 168 h de vacances | Fiche 4.1, éq. 50 à 53, compte à la main | identique |
| Ratio de fermeture d'un volet manuel : nuit d'hiver, absence de journée, vacances, jour d'été chaud | Fiche 5.9, figure 35 et éq. 188-189, calcul à la main | identique |
| Volet automatique : part automatique, dérogation (0,7 × 0,25), hystérésis, déperdition | Figure 44, éq. 179 et 186 ; fiche 5.10, éq. 211 | identique |
| Store enroulable extérieur relevé à 10 m/s ; store intérieur maintenu | Fiche 5.9, éq. 192 | conforme |
| Flux solaires et déperdition d'une baie partagée entre parts nue et protégée | Fiche 5.10, éq. 210, 219 et 220 | identique |
| Modération par la température extérieure, seuils et hystérésis d'ouverture, frein du bruit | Fiche 5.13, figures 61 et 62, tableau 42, calcul à la main | identique |
| Débit non traversant (tirage, vent) et traversant ; surface équivalente de deux façades opposées | Fiche 5.13, éq. 251 à 254 | identique |
| Chaque heure, protections et ouvertures actives : chaleur prise par la masse = somme des flux | Bilan d'énergie | écart < 1e-6 W |
| Groupe sans protection ni baie ouvrable | Résultats de la 0.8.10 | inchangés |
| Étude de 317 baies protégées et ouvrables, deux groupes | Temps de calcul | environ 13 s (9 s en 0.8.10) |

### Effet sur les cinq études

Besoin de froid en kWh/m² : étude, outil, puis l'outil privé d'un module à la fois.

| Groupe | Étude | Outil | Sans ouverture | Sans protections | Ni l'un ni l'autre (0.8.10) |
|---|---|---|---|---|---|
| Paris, non traversant | 0,4 | 1,6 | 8,9 | 2,1 | 13,3 |
| Paris, traversant | 0,3 | 0,6 | 7,7 | 0,9 | 13,7 |
| Sète, traversant | 1,9 | 6,1 | 10,8 | 15,9 | 40,1 |
| Sète, non traversant | 3,4 | 6,9 | 11,3 | 13,6 | 31,4 |
| Nice A climatisée, traversant | 4,6 | 10,4 | 19,5 | 15,2 | 31,7 |
| Nice A climatisée, non traversant | 7,1 | 12,3 | 17,9 | 17,8 | 30,1 |
| Nice A non climatisée, traversant | 4,3 | 10,2 | 19,4 | 13,5 | 27,5 |
| Nice A non climatisée, non traversant | 5,6 | 10,7 | 16,2 | 14,0 | 22,9 |
| Nice B, traversant | 5,3 | 11,3 | 21,6 | 16,7 | 34,8 |
| Nice B, non traversant | 6,1 | 12,0 | 17,8 | 17,1 | 28,7 |

Lecture :

- **Le froid passe de 4 à 46 fois celui des études à 1,7 à 4 fois.** L'ouverture des baies pèse plus que les
  protections à Paris ; à Sète ce sont les protections ; à Nice les deux sont du même ordre. La variante « protections fermées toute l'année »
  de la 0.8.10 surestimait leur effet : les matrices conventionnelles ne ferment un volet qu'à 20 à 50 % un jour
  d'été peu éclairé.
- **Paris est le cas le plus sûr** : tous ses volets sont manuels, donc sans seuil inconnu. Le froid y est de 1,6
  et 0,6 kWh/m² contre 0,4 et 0,3, et sa pointe tombe en août comme dans l'étude (1,1 contre 0,4 et 0,5 contre
  0,3 kWh/m²).
- **Sète et Nice restent à un facteur 2 à 3** : volets automatiques (seuils de l'outil, hypothèse 57) et, à Nice, 20
  baies à store vénitien lues sans protection.
- **Chauffage presque inchangé à Paris, un peu plus faible ailleurs** (12 à 55 % sous les études) : les volets fermés la nuit
  réduisent la déperdition des baies ; les infiltrations manquent toujours (0.8.14).
- **Bbio** : 43,5 et 54,0 points à Paris (étude : 49,2 et 75,3), 28,2 et 28,2 à Sète (29,9 et 24,7), 50,2 et 51,0
  à Nice B (49,3 et 47,9). La proximité de certains totaux est fortuite : un chauffage trop faible y compense un
  froid trop fort.

### Lectures du texte et hypothèses de l'outil

55. **Absence de journée** (fiche 4.1, éq. 52) : plage inoccupée comprise entre les cases 7 et 22, précédée et
    suivie d'une heure occupée le même jour ; les protections y gardent leur position de jour. Le produit de
    l'éq. 53 (« algèbre de Bool du tableau 5 », non lisible) est lu ainsi : une semaine de vacances impose
    l'absence longue.
56. **Jour et nuit des protections.** Gestion manuelle : en occupation, il fait jour quand la baie reçoit de la
    lumière (éq. 183). Gestion automatique : toujours jour sans horloge, selon la lumière avec une horloge
    crépusculaire (éq. 182) ; l'horloge personnalisable est lue comme l'absence d'horloge.
57. **Seuils de la gestion automatique : valeurs de l'outil.** L'annexe les donne comme des données d'entrée sans
    valeur conventionnelle, et les fichiers d'étude ne les contiennent pas : éclairement 10 000 lux, ambiance
    chaude au-dessus de 26 °C, fraîche en dessous de 24 °C, hystérésis entre les deux (figure 31). Le vent limite
    de la gestion automatique est pris égal à celui de la gestion manuelle (10 m/s). **À confirmer dans un
    logiciel.**
58. **Température de la veille** (éq. 175) : maximum de la température opérative de fin d'heure sur le jour légal
    précédent ; nulle le premier jour, comme le prévoit la fiche.
59. **Ouverture des baies la nuit.** La fiche 5.13 ne décrit le réglage par les occupants qu'en journée (hlég de
    7 h à 23 h) ; la nuit, l'outil garde le ratio du soir. Hors occupation il est nul (éq. 245).
60. **Écart de confort adaptatif** de l'éq. 242 : seuil d'inconfort chaud de la fiche 4.5 (catégorie 1) moins la
    consigne de refroidissement de confort.
61. **Protection et ouverture** (éq. 248) : la surface ouvrable d'une baie est réduite de sa part protégée,
    Aouvmax × (1 − Rprot) ; le texte ne définit pas cette surface.
62. **Vent** : vitesse du fichier météo, sans la correction « Vvent_c » des fiches 5.9 et 5.13 (revue en 0.8.14 :
    vent corrigé).
63. **Air entrant par les baies** : à la température extérieure, ajouté au débit de la ventilation ; sa masse
    volumique suit l'éq. 255, rapportée à celle du coefficient 0,34 Wh/m³.K.
64. **Sw avec protection** : une seule valeur dans les études, sans distinction des conditions C et E ni des
    composantes directe, diffuse et réfléchie (éq. 214 et 217).
65. **Famille d'usages** : seules les matrices « habitation, hôtellerie et hébergement » sont saisies ; Pocc = 0,7
    et Pderog = 0,25 sont ceux du logement collectif (figure 34).

### Simplifications de cette version (à lever plus tard)

- Stores vénitiens, seconde protection mobile, gestion automatique de l'ouverture des baies.
- Éclairage artificiel calculé baies nues.
- Lignes propres au mode Th-D (protections : tableau 34 ; ouvertures : règle générale de la fiche 5.13) : avec
  le DH (0.8.16).

## 0.8.14 — infiltrations

`moteur/infiltrations.py` (annexe III, fiche 5.6, éq. 131 à 172, tableaux 21 à 24 et 27 à 30 ; fiche 3.1 pour le
vent corrigé ; fiche 13.1, éq. 2407, pour l'indicateur d'hiver). Équations et tableaux relus sur les pages du
PDF : 41, 142, 143, 145, 151, 152, 155 et 1362.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Surfaces perméables : murs et baies en façade, toiture à part, plancher bas exclu | Fiche 5.6, § 5.6.3.1.4 ; indicateur `A_T_perm` d'une étude (1 536,1 m²) | identique |
| Défauts d'un groupe : quatre quarts de façade, toiture entière, altitudes 0,75, 2,25 et 3 m | Tableaux 28 et 29, éq. 150 | identique |
| Vent seul, Cp = ± 0,05, 4 m/s : pression nulle, débit entrant 2 × C × 0,48^(2/3) | Éq. 136, 137 et 151, calcul à la main | identique |
| Tirage seul : l'air entre en bas et sort en haut, masse conservée ; débit proportionnel à la perméabilité | Éq. 167 | conforme |
| Double flux à volumes égaux, air soufflé plus froid : surplus de masse évacué par les défauts | Éq. 156, 157 et 167 | bilan nul à 1e-9 kg/s |
| Chaque heure, infiltrations comprises : chaleur prise par la masse = somme des flux | Bilan d'énergie | écart < 1e-6 W |
| Groupe sans perméabilité renseignée | Résultats de la 0.8.12 | inchangés (au vent corrigé près) |
| Étude de 800 composants | Temps de calcul | environ 20 s (13 s en 0.8.12) |

### Effet sur les cinq études

Besoins en kWh/m² et Bbio en points.

| Groupe | Bch étude | Bch 0.8.12 | Bch 0.8.14 | Bfr étude | Bfr 0.8.14 | Bbio étude | Bbio 0.8.14 |
|---|---|---|---|---|---|---|---|
| Paris, non traversant | 19,5 | 15,7 | 16,9 | 0,4 | 1,5 | 49,2 | 45,8 |
| Paris, traversant | 33,0 | 22,2 | 27,7 | 0,3 | 0,6 | 75,3 | 64,9 |
| Sète, traversant | 8,7 | 3,9 | 7,2 | 1,9 | 6,3 | 29,9 | 35,3 |
| Sète, non traversant | 4,4 | 2,8 | 3,5 | 3,4 | 6,9 | 24,7 | 29,6 |
| Nice A climatisée, traversant | 10,9 | 7,8 | 10,4 | 4,6 | 10,6 | 39,8 | 50,5 |
| Nice A climatisée, non traversant | 9,5 | 7,9 | 8,3 | 7,1 | 12,3 | 42,8 | 50,2 |
| Nice A non climatisée, traversant | 15,7 | 12,3 | 15,4 | 4,3 | 10,3 | 48,3 | 59,5 |
| Nice A non climatisée, non traversant | 17,1 | 15,0 | 15,6 | 5,6 | 10,7 | 54,2 | 61,1 |
| Nice B, traversant | 15,1 | 9,7 | 13,9 | 5,3 | 11,7 | 49,3 | 59,3 |
| Nice B, non traversant | 13,0 | 9,0 | 9,6 | 6,1 | 12,0 | 47,9 | 52,2 |

Lecture :

- **Chauffage : de 12 à 55 % sous les études à 2 à 26 %.** L'effet est fort dans les groupes traversants, exposés
  au vent (Cp de + 0,25 et − 0,5), faible dans les non traversants (± 0,05), où il ne reste que le tirage sur 3 m.
- **Les non traversants restent les plus bas** (Nice B : 9,6 contre 13,0 ; Sète : 3,5 contre 4,4).
- **Bbio** : sous les études à Paris (chauffage encore faible), au-dessus à Nice et à Sète (froid encore fort). Les
  compensations d'erreurs de la 0.8.12 ont en partie disparu : l'écart restant se lit poste par poste.

### Point ouvert : l'indicateur d'hiver des études

Les études donnent par zone `H_V_Def_Hiver`, moyenne de janvier et février de la déperdition par les défauts
d'étanchéité (fiche 13.1, éq. 2407). La même moyenne dans l'outil vaut 26 à 34 % de cet indicateur dans les zones
traversantes et 15 à 18 % dans les autres. Deux constats vont en sens contraire :

- injecté tel quel comme un débit constant (variante de la 0.8.10), cet indicateur faisait dépasser le chauffage
  des études de 3 à 105 % ;
- avec le modèle de la fiche 5.6, le chauffage de l'outil reste sous celui des études.

Essai hors moteur : en ajoutant les entrées d'air du projet (`Entree_Air`, modules de 400 à 5 900 m³/h sous 20 Pa),
la moyenne d'hiver remonte à 43 à 77 % de l'indicateur. Elles en expliquent donc une partie, pas tout. L'outil ne
les compte pas (hypothèse 67) ; la question reste ouverte et figure dans `ROADMAP.md`.

### Lectures du texte et hypothèses de l'outil

62. **(revue) Vent corrigé** : vitesse du fichier météo × 0,9 (fiche 3.1, Cvent), pour les infiltrations, les
    protections mobiles et l'ouverture des baies.
66. **Un bilan par groupe.** La fiche 5.6 équilibre la zone entière, avec une pression commune et des échanges entre
    groupes par un hall ; l'outil équilibre chaque groupe seul. Identique quand la zone n'a qu'un groupe.
67. **(remplacée par la 92 en 0.9.10) Pas d'entrées d'air en mode Bbio** : la ventilation conventionnelle du Bbio est une double flux (fiche 6.1),
    qui n'en a pas besoin ; le texte ne dit pas ce que deviennent celles du projet.
68. **Double flux à débits volumiques égaux** : les masses soufflée et reprise diffèrent par leur température
    (éq. 156-157), ce qui met le groupe en légère surpression en hiver.
69. **Habitation : pas de tirage entre niveaux** (éq. 138) : les altitudes des défauts sont comptées sur 3 m au
    plus (0,75, 2,25 et 3 m), quelle que soit la hauteur de l'immeuble.
70. **Coefficients de pression** : écrantage « normal » et toiture horizontale par convention (tableau 23) ;
    hauteur moyenne de la zone = `Hauteur` + `Hauteur_Zone` / 2 des études (lecture de hmoy = hzone + 0,5 hplafond) ;
    au vent 0,25 sous 15 m, 0,45 au-delà. Une zone non traversante prend ± 0,05 et 0 en toiture (tableau 24).
71. **Caractère traversant** : celui du groupe (`Groupe.traversant`), lu dans `Delta_trav_surv` des études, pour les
    infiltrations comme pour l'ouverture des baies ; la fiche 5.6 distingue en principe un caractère traversant
    « d'hiver », portes fermées.
72. **Humidité ignorée** dans les masses volumiques (éq. 131 à 133) ; masse volumique de référence 1,2 kg/m³ à
    19 °C.
73. **Surfaces perméables** : façade entre 60 et 120° d'inclinaison, toiture en dessous de 60°, parois de type
    plancher bas exclues ; les parois sur un espace tampon comptent, comme dans l'indicateur `A_T_perm` des études.
74. **Perméabilité lue telle quelle** : pas de majoration pour une mesure par échantillonnage ou des travaux restant
    à faire (fiche 5.6) ; les études donnent déjà la valeur de calcul.

## 0.8.16 — DH

`moteur/confort.py` (annexe III, fiche 3.1, éq. 1 et 2 ; fiche 13.5, éq. 2543 à 2546), `moteur/dh.py` (fiche 13.5,
éq. 2547 à 2551 ; annexe à l'article R. 172-4, chapitre II, IV et chapitre III, IV), mode Th-D de
`moteur/besoins.py` (fiche 4.6, éq. 76 à 90), de `moteur/protections.py` (fiche 5.9, § 5.9.3.6 et tableau 34) et
de `moteur/ouvertures.py` (fiche 5.13, § 5.13.3.1). Textes relus sur l'extraction du PDF ; le tableau 34 (page
218) n'a pu être relu qu'en texte, cellule par cellule.

### Vérifications

Les classeurs horaires de Paris, Sète et Nice (onglet `re2020`) donnent, pour cinq groupes, la température
extérieure, l'occupation, la température opérative, θrm, le seuil de confort, le seuil corrigé et les
degrés-heures d'un moteur Th-BCE.

| Contrôle | Référence | Résultat |
|---|---|---|
| θrm : jours de 24 pas depuis l'heure 0 (UTC), nul le premier jour | Colonne θrm des classeurs, cinq groupes | écart maximal 2e-14 °C |
| Période de confort adaptatif : heures de début et de fin | Dix groupes de cinq RSET : 3 480 à 6 167 (H1a), 2 952 à 7 199 (H3) | identique |
| Seuil de confort chaud, heure par heure (jour : hlég de 7 à 22) | Colonne du moteur, en occupation, cinq groupes | écart nul |
| DH à partir de la température opérative et de la correction des brasseurs du moteur | Somme des degrés-heures des classeurs : 345,52 ; 137,38 ; 321,24 ; 454,31 ; 399,25 °C.h | identique à 1e-6 °C.h (1e-14 par heure) |
| DH max | Dix groupes de cinq RSET (1 250 ; 2 100 ; 2 228,4 ; 2 330,5) | identique |
| Effet d'un brasseur (éq. 1656 à 1660), débit « justifié » × 0,9, régime intermédiaire | Correction du seuil des classeurs de Paris et de Sète | écart médian 0,007 à 0,02 °C ; 0,17 à 1 °C avec les coefficients 1 ou 0,8 |
| Chaque heure du calcul Th-D, brasseurs compris : chaleur prise par la masse = somme des flux | Bilan d'énergie | écart < 1e-6 W |
| Mode Th-B après les modifications | Besoins de l'étude de Paris en 0.8.14 (16,9 ; 27,7 ; 1,5 ; 0,6 kWh/m²) et tests de la 0.8.14 | inchangés |
| DH d'une étude de 800 composants (deux groupes) | Temps de calcul | 10 à 45 s selon la charge du poste |

Les classeurs horaires ne viennent pas du même calcul que les RSET présents : leur DH diffère (Paris : 345,5 et
137,4 °C.h dans le classeur, 372,7 et 145,2 dans le RSET). Ils valident donc les formules, pas les températures
de l'outil.

### Effet sur les cinq études

DH en °C.h, heures d'inconfort en heures. « Sans brasseurs » : le même calcul de l'outil, brasseurs retirés.

| Groupe | Brasseurs | DH étude | DH outil | Écart | DH outil sans brasseurs | Heures étude | Heures outil | DH max |
|---|---|---|---|---|---|---|---|---|
| Paris, non traversant | 23 | 372,7 | 435,0 | + 17 % | 610,9 | 160 | 183 | 1 250 |
| Paris, traversant | 113 | 145,2 | 171,4 | + 18 % | 302,7 | 88 | 111 | 1 250 |
| Sète, traversant | 90 | 353,6 | 207,0 | − 41 % | 448,3 | 273 | 189 | 1 250 |
| Sète, non traversant | 56 | 529,7 | 343,8 | − 35 % | 736,4 | 435 | 346 | 1 250 |
| Nice A climatisée, traversant | 0 | 1 076,6 | 1 160,9 | + 8 % | — | 663 | 755 | 2 100 |
| Nice A climatisée, non traversant | 0 | 1 979,2 | 1 938,5 | − 2 % | — | 988 | 1 020 | 2 330,5 |
| Nice A non climatisée, traversant | 74 | 444,4 | 506,1 | + 14 % | 982,8 | 362 | 469 | 1 250 |
| Nice A non climatisée, non traversant | 15 | 486,2 | 624,2 | + 28 % | 1 480,9 | 393 | 564 | 1 250 |
| Nice B, traversant | 0 | 1 069,0 | 1 203,6 | + 13 % | — | 664 | 757 | 2 100 |
| Nice B, non traversant | 0 | 1 919,9 | 2 029,4 | + 6 % | — | 983 | 1 043 | 2 228,4 |

Lecture :

- **Sans brasseurs (quatre groupes de Nice)** : de − 2 à + 13 %. La température de l'année caniculaire est donc
  proche de celle des études, alors que le besoin de froid du Bbio reste 1,7 à 4 fois trop fort.
- **Avec brasseurs** : + 14 à + 28 % à Paris et à Nice, − 35 à − 41 % à Sète. Les brasseurs divisent le DH par
  1,4 à 2,4 : leur régulation pèse autant que le bâtiment. À Sète ils ne servent que la nuit, en gestion par
  thermostat (écarts 0, 2 et 0 °C) : c'est le premier point à examiner.
- **Tous les groupes respectent le DH max**, comme dans les études.

### Lectures du texte et hypothèses de l'outil

10. **(revue) Brasseurs d'air : hlég = heure légale de début de pas**, comme partout ailleurs (hypothèse 42). Le
    jour va du pas de 7h-8h au pas de 22h-23h ; le blocage manuel « hlég > 23 ou hlég ≤ 6 » couvre les pas de 0h
    à 7h, le pas de 23h-24h étant encore régulé.
75. **Ventilation du calcul Th-D : débit du Bbio, sans échangeur.** L'outil ne décrit pas le système de
    ventilation du projet ; l'air neuf entre à la température extérieure (`ventilation_th_d_efficacite` = 0), au
    débit moyen du groupe. Les infiltrations gardent le modèle du Bbio (soufflage et reprise à volumes égaux).
76. **Catégorie de contraintes extérieures : règle observée.** Le chapitre V de l'annexe à l'article R. 172-4
    manque aux sources. Sur dix groupes : catégorie 2 quand le groupe est climatisé et en BR2 ou BR3 (six
    groupes, DH max de 2 100 à 2 330,5), catégorie 1 sinon, y compris un groupe non climatisé en BR2 (1 250).
    Aucune étude ne montre un groupe climatisé en BR1 : la colonne « catégorie 1 climatisée en H2d ou H3 » est
    codée d'après le texte, sans recoupement.
77. **Saison de refroidissement en Th-D pour tous les groupes.** La fiche 4.6 annule l'autorisation de refroidir
    d'un groupe sans système de froid, et la fiche 13.5 désactive la climatisation en Th-D ; mais la même fiche
    4.6 fait démarrer cette saison au premier jour de confort adaptatif « en mode Th-D ». L'outil retient cette
    seconde lecture : la saison existe (elle choisit la ligne « été » des protections mobiles), sans aucune
    puissance de froid.
78. **Chauffage du calcul Th-D** : émetteur conventionnel du Bbio, faute du système du projet ; interdit en
    période de confort adaptatif (éq. 76, 77 et 80). Pas de relance avant le retour des occupants.
79. **Tableau 34, lecture.** Type_GPM = 3 est la gestion manuelle motorisée (éq. 180) : plancher de 80 %, 70 %
    pour les autres, dérogations manuelles de la gestion automatique comprises (« pas d'impact du détecteur de
    présence »). Les lignes « (jour=nuit) » sont lues comme les valeurs de nuit. La « valeur Th-BC » est celle de
    la ligne de saison en cours. La part automatique d'une gestion automatique garde ses valeurs.
80. **Ouverture des baies en Th-D.** Hors occupation les baies sont fermées (éq. 240) et le réglage Rouv_θop des
    occupants est gardé tel quel, alors qu'il est remis à zéro en Th-B (éq. 245). L'écart de confort adaptatif
    est celui de la fiche 13.5 (éq. 2546) : nul la nuit, 2 °C au plus.
81. **Seuil de confort hors occupation** : calculé avec la consigne d'occupation (26 °C), alors qu'un moteur
    affiche MAX(30 ; 0,33 × θrm + 20,8) ; sans effet, le DH ne comptant que l'occupation. L'écart de confort
    adaptatif n'est pas forcé à zéro hors période (il y vaut au plus 0,08 °C).
82. **Brasseurs lus dans les RSET** : codes décalés d'un cran par rapport à la fiche 8.32 (Us 0 nuit, 1 jour,
    2 jour et nuit ; mode de gestion 0 manuelle, 1 thermostat, 2 automatique ; caractère 0 certifié, 1 justifié,
    2 déclaré). Seul le code 1 du caractère est recoupé (tableau des vérifications). `Rat_surf` est le ratio de
    surface brassée ; `Rat_Us` du fichier n'est pas repris (valeurs du tableau 257).
83. **DH par groupe**, sans moyenne par zone ni par bâtiment : le texte n'en prévoit pas. La surface moyenne des
    logements du DH max est celle de la zone, comme pour le Bbio max.
84. **Éclairage et apports internes du calcul Th-D** : ceux du mode Th-B, éclairage calculé baies nues.

## 0.8.17 — relecture de la 0.8.16

Relecture du dépôt entier sur cinq axes (sécurité, simplicité, rapidité, efficacité, lisibilité), sans toucher au
calcul. Aucune hypothèse nouvelle.

### Constats et suites données

| N° | Constat | Suite |
|---|---|---|
| 1 | Le README ne montrait aucun appel en Python : il fallait un RSET pour essayer l'outil | Section « Premier calcul » : un projet d'un groupe, `calculer_bbio`, `calculer_dh` |
| 2 | L'annexe R. 172-4 n'était citée que pour le Bbio max ; les hypothèses à valider n'apparaissaient pas | Sources complétées, renvoi aux hypothèses 75 et 76 |
| 3 | En-têtes périmés (`bbio.py`, `solaire.py`, `groupe.py`) | Remis au présent |
| 4 | Le DH importait une fonction privée du Bbio, dont le message ne parlait que du Bbio max | `controler_projet` public, message commun |
| 5 | `est_jour` écrite deux fois (brasseurs, confort) | Une seule, dans `moteur/confort.py` |
| 6 | `theta_rm` désignait deux grandeurs : moyenne glissante extérieure et température radiante moyenne | `theta_rm_ext` pour la première |
| 7 | DH des études apparié par rang dans le fichier | Apparié par nom de groupe |
| 8 | Un groupe sans protection mobile ni baie ouvrable sortait 50 °C et un DH de 38 fois le maximum, sans rien signaler | Colonne `avertissement` |
| 9 | `calculer_besoins` : 230 lignes pour deux modes | `preparer_confort` et `brasseurs_de_l_heure` sortis de la boucle |
| 10 | `KELVIN`, `SECONDES_PAR_HEURE`, `HEURES_PAR_JOUR` définis dans plusieurs modules | Regroupés dans `config/reglages.py` (unités, pas des constantes réglementaires) |
| 11 | `FLUX_DU_BILAN` recopié dans cinq fichiers de tests | Défini dans `moteur/groupe.py` |
| 12 | Deux constantes `JEU` de valeurs différentes (`besoins.py`, `dh.py`) | `dh.py` lit `JEUX_DES_MODES` |
| 13 | Le modèle du groupe est appelé trois à quatre fois par heure | Calcul d'une heure en deux temps (`preparer_pas`, `resoudre_pas`, `temperatures_sonde`) ; gain modeste, voir ci-dessous |
| 14 | Lignes de plus de 120 caractères | Une vingtaine de lignes coupées, code et tests |

Sans suite nécessaire : aucun secret ni fichier d'étude suivi par git (`.gitignore` et `tests/test_depot.py`) ;
toutes les clés de `donnees/hypotheses.csv` sont utilisées et sourcées, aucune clé appelée n'est absente ; `moteur/`
ne dépend ni de `outils/` ni d'une interface. Pas d'interface ni de base de données à ce stade : les axes
correspondants seront à reprendre avec la 0.8.18.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Bbio des dix groupes des cinq études : Bch, Bfr, Becl, Bbio, Bbio max | Même calcul avec le code de la 0.8.16 | écart nul |
| DH des mêmes groupes : DH, trois compteurs d'heures, température maximale, DH max | Même calcul avec le code de la 0.8.16 | écart nul |
| Somme de toutes les colonnes horaires, modes Th-B et Th-D | Même calcul avec le code de la 0.8.16 | écart nul |
| Exemple du README | Exécuté tel quel | Bbio 34,3 points (max 73,5), DH 1 978 °C.h (max 1 250) |
| Groupe d'une baie nue, sans protection ni ouverture | `avertissements_confort` | « aucune protection mobile, aucune baie ouvrable » |
| Groupe inconnu de l'étude dans `comparer_dh` | Test | colonnes de l'étude vides, pas d'erreur |
| `resoudre_pas` après `preparer_pas`, quatre puissances | `pas_groupe` sur les mêmes entrées | égalité stricte |

### Temps de calcul

Le constat 13 visait le modèle du groupe. Mesuré avant de le modifier, il ne pèse lourd que sur un groupe simple :

| Cas | Avant | Après | Part du modèle du groupe avant |
|---|---|---|---|
| Groupe simple (exemple du README), Bbio | 1,0 s | 0,9 s | 45 % |
| Groupe simple, DH | 1,7 s | 1,4 s | 45 % |
| Étude de Paris (800 composants, deux groupes), Bbio ou DH | 10 à 20 s selon la charge du poste | inchangé | 4 % |

Temps processeur, meilleur de cinq essais, ancien et nouveau code alternés. Sur l'étude, le profil donne :
équilibre de pression des infiltrations 35 %, rayonnement reçu par chaque paroi 30 % (calculé plusieurs fois par
composant), protections mobiles 8 %. C'est là qu'est le gain pour les études ; ces deux points sont dans
`ROADMAP.md`, non traités ici.

## 0.9.0 — outil fonctionnel

Interface vue dans un navigateur et complétée (balcons, comparaison de deux variantes) ; recherche de la pression
d'équilibre des infiltrations accélérée. Le calcul des études ne change pas.

### Constats du contrôle visuel et suites données

| N° | Constat | Suite |
|---|---|---|
| 1 | Barre annuelle du Bbio : axe écrasé sous la barre, trait du Bbio max invisible | La hauteur donnée à Streamlit est celle du graphique entier, légende et axes compris : hauteurs revues (`interface/briques/graphiques.py`) |
| 2 | Semaine chaude : graphique des protections et des fenêtres réduit à un trait | Même cause, même suite |
| 3 | Axonométrie : étiquettes des façades écrites à l'horizontale, par-dessus les baies du bas | Étiquettes couchées le long du pied de chaque façade |
| 4 | Bouton « Calculer » hors de vue dès qu'on fait défiler les volets de saisie | Second bouton à côté de l'avertissement « la saisie a changé » |
| 5 | Premier calcul de la boîte : 25 à 35 s sur le poste chargé (navigateur et serveur ouverts), pour 8 s annoncés | Voir « Temps de calcul » |

Vu sans défaut : thème, chiffres clés, brique DH, températures de la semaine chaude, volet « équation, référence et
code », changement de point de vue. Console du navigateur : aucune erreur de la page.

### Temps de calcul

Profil de la boîte de départ (Bbio et DH, 17 520 heures) : 62 % du temps dans le bilan aéraulique des
infiltrations, évalué 62 fois par heure par la dichotomie (1,1 million d'évaluations). La dichotomie est remplacée
par une fausse position bornée (variante « Illinois »), avec un pas de dichotomie quand l'encadrement se resserre
mal : même équation (éq. 167), même encadrement de départ, arrêt quand deux essais successifs diffèrent de moins
de 1e-12 Pa. Le bilan est évalué 12 fois par heure en moyenne, au lieu de 62.

| Cas (poste chargé) | Avant | Après |
|---|---|---|
| Boîte de départ, Bbio et DH, avec infiltrations | 25 s | 15 s |
| Même boîte, enveloppe étanche (pas d'infiltrations) | 10 s | inchangé |
| Bbio de la boîte de départ | 62,328 731 621 906 | 62,328 731 621 907 |
| DH de la boîte de départ (°C.h) | 1 777,122 607 884 7 | 1 777,122 607 885 7 |

Le reste du temps (protections mobiles, ouvertures, modèle du groupe) reste au point « temps de calcul » de
`ROADMAP.md`.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Bilan aéraulique à la pression trouvée, 14 cas (vent nul à 12 m/s, − 8 à 35 °C, ventilation jusqu'à 5 000 m³/h, traversant ou non) | Zéro (éq. 167) | écart < 1e-9 kg/s |
| Bbio et DH de la boîte de départ | Valeurs de la 0.8.18 | égaux à 12 chiffres |
| Étude de Paris (`outils.comparer_reference --dh`) | Mêmes besoins mensuels et même DH qu'avant | DH 435,0 et 171,4 °C.h (études : 372,7 et 145,2) |
| Balcons de 1,2 m sur la façade sud de la boîte de départ | Sens attendu : moins de soleil en été, un peu moins en hiver, moins de lumière | froid 15,6 → 12,3 kWh/m², chauffage 11,6 → 12,5, éclairage 1,6 → 1,7, DH 1 777 → 1 477 °C.h |
| Page entière (`AppTest`) : référence gardée, balcon saisi, second bouton « Calculer », tableau des écarts, référence oubliée | — | aucune erreur |
| Page dans un navigateur (Chrome, 1 440 × 900) : les trois briques, un balcon, la comparaison | — | conforme, capture dans `docs/capture_interface.jpg` |

### Lectures du texte et hypothèses de l'outil

85. **Balcons et casquettes de la boîte** : un débord horizontal de longueur infinie (fiche 3.2, éq. 20 et 21),
    placé au nu du plancher haut de chaque niveau, donc à la hauteur d'un linteau au-dessus de la baie. La hauteur
    de la baie et celle du linteau viennent du gabarit du dessin (`interface.saisie.gabarit_baie` : la baie occupe
    45 à 92 % de la hauteur d'étage, 45 % du vide restant est au-dessus). Le débord ne masque que les baies, pas
    les murs ; le dernier niveau est supposé couvert comme les autres (casquette en toiture).
86. **Recherche de Pib** : la tolérance de 1e-12 Pa et la méthode sont des choix numériques de l'outil ; la fiche
    5.6 ne prescrit que l'équation à résoudre.

## 0.9.1 — choix du calcul et bâtiment de départ

L'interface ne lance que le calcul demandé (DH, Bbio ou les deux) et part d'un logement de 70 m². Le moteur ne
change pas.

### Temps de calcul

| Cas (poste peu chargé, avec infiltrations) | Bbio | DH | Les deux |
|---|---|---|---|
| Immeuble de 9 logements, 0.9.0 | — | — | 4,0 s |
| Immeuble de 9 logements, 0.9.1 | 1,8 s | 2,0 s | — |
| Logement de 70 m², 0.9.1 | 2,0 s | 1,9 s | — |

Les deux calculs pèsent autant : n'en lancer qu'un divise le temps par deux.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Bbio et DH de l'immeuble de 9 logements | 0.9.0 : 62,3 et 1 777 °C.h | 62,3 et 1 777 °C.h |
| Logement de 70 m² | — | Bbio 114,7 (max 78,0) ; DH 1 964 °C.h (max 1 250) |
| Page entière (`AppTest`) : DH seul, puis les deux sans recalcul du DH, retour au DH seul, changement de bâtiment | Appels comptés | un calcul par demande nouvelle, aucune erreur |
| Page dans Chrome : DH seul, Bbio seul, les deux ; saisie modifiée puis changement de bâtiment, aller et retour | — | conforme |

Constat du contrôle visuel : effacer les clés des widgets au changement de bâtiment laissait les curseurs sur
l'ancienne valeur à l'écran (l'`AppTest` ne le voyait pas). Chaque widget reçoit maintenant la valeur du bâtiment
choisi. Le chiffre clé « 114,7 points » était coupé : l'unité passe dans le libellé.

### Lectures du texte et hypothèses de l'outil

87. **Logement de 70 m²** : un petit bâtiment isolé à un niveau (quatre façades, toiture et plancher bas sur le
    sol), calculé avec les scénarios, le Bbio max et le DH max du logement collectif, faute de l'usage maison
    individuelle (0.9.10). Son Bbio élevé (114,7) vient de sa forme : beaucoup de paroi par m² habitable. Un
    appartement au milieu d'un immeuble est un autre cas, inscrit dans `ROADMAP.md`.

## 0.9.2 — niveaux d'enveloppe

La page part d'un bâtiment (la forme) et d'un niveau d'enveloppe (performant, moyen, faible) tiré de
`donnees/typologies_logements.csv` (méthode : `outils/typologies/README.md`). Le moteur ne change pas.

### Vérifications

| Bâtiment | Niveau | Bbio (max) | DH °C.h (max) |
|---|---|---|---|
| Logement de 70 m², `Boite()` (0.9.1) | — | 114,7 (78,0) | 1 964 (1 250) |
| Logement de 70 m² | Performant | 78,5 (78,0) | 858 (1 250) |
| Logement de 70 m² | Moyen | 99,1 (78,0) | 1 308 (1 250) |
| Logement de 70 m² | Faible | 116,3 (78,0) | 1 756 (1 250) |
| Immeuble de 9 logements | Performant | 46,6 (69,8) | 746 (1 250) |
| Immeuble de 9 logements | Moyen | 54,9 (69,8) | 1 125 (1 250) |
| Immeuble de 9 logements | Faible | 63,1 (69,8) | 1 541 (1 250) |

Les deux indicateurs suivent le niveau dans le sens attendu. L'immeuble moyen respecte les deux seuils, le
faible dépasse le DH max ; le logement isolé ne respecte le Bbio max qu'au niveau performant, à peine.
Temps : 3 s par bâtiment et par niveau, Bbio et DH (poste chargé).

### Lectures et hypothèses de l'outil

88. **Ponts thermiques des niveaux d'enveloppe** : le CSV donne un ψ moyen sur tous les ponts thermiques des
    études (planchers, refends, menuiseries…). La boîte le place sur ses seules liaisons linéiques, les rives des
    planchers (périmètre × (niveaux + 1)). La longueur réelle des ponts d'une étude étant plus grande, la boîte
    sous-estime probablement leur déperdition. Suite inscrite dans `ROADMAP.md`.
89. **Niveaux tirés de 6 opérations** (18 zones, 17 305 m²) : repères indicatifs, non représentatifs du parc. Le
    niveau « performant » d'une variable vient de quantiles calculés variable par variable : les 13 valeurs
    ne décrivent aucune étude réelle prise en entier.

## 0.9.4 — bâtiments de départ en CSV

Les bâtiments de départ sont lus dans `donnees/batiments/` (un CSV par bâtiment). Le logement de 70 m² change :
H1a, façade principale 7 m sur 10 m de profondeur, baies 25 % devant et derrière, pignons aveugles, gestion
manuelle motorisée des volets ; l'immeuble prend les mêmes valeurs hors forme. Le moteur ne change pas.

### Vérifications

| Bâtiment | Niveau | Bbio (max) | DH °C.h (max) |
|---|---|---|---|
| Logement de 70 m², `Boite()` | — | 121,2 (91,0) | 1 062 (1 250) |
| Logement de 70 m² | Performant | 90,7 (91,0) | 609 (1 250) |
| Logement de 70 m² | Moyen | 114,8 (91,0) | 786 (1 250) |
| Logement de 70 m² | Faible | 135,5 (91,0) | 991 (1 250) |
| Immeuble de 9 logements | Performant | 48,7 (82,8) | 511 (1 250) |
| Immeuble de 9 logements | Moyen | 58,2 (82,8) | 675 (1 250) |
| Immeuble de 9 logements | Faible | 65,8 (82,8) | 859 (1 250) |

En H1a, le Bbio max monte (91,0 et 82,8 contre 78,0 et 69,8 en H3) et le Bbio aussi (chauffage plus fort) ; le
DH baisse nettement (climat plus frais, pignons aveugles, volets motorisés). Les six cas respectent le DH max ;
le logement isolé ne respecte le Bbio max qu'au niveau performant, à peine, comme en 0.9.2. Temps : 4 à 7 s par
cas, Bbio et DH (poste chargé).


## 0.9.8 — validation

`outils/valider.py` passe dans `outils/comparer_reference.py` tous les XML de `../_RSEE` et de `_sources`, sans
doublon de contenu, et écarte ceux qui n'ont aucune zone de logement collectif. Une correction du moteur : les
parois à U = 0 (hypothèse 90).

### Les études disponibles

26 fichiers, dont 14 écartés : bureaux (usage 3 : dossier AREP, Eugène, Hayet, La Poste, Arkéa) et maison
individuelle (usage 1 : SPGL). Restent 10 études et 23 groupes, mais 5 bâtiments distincts seulement : Paris
(scénario 2) et Hébert sont deux versions du même immeuble, Sète en a trois (scénario 2, RSEE 8619, RSENV), Nice A
trois (V5, 04-2026, sans climatisation), Nice B une, et `rsee.xml` (H2a, trois bâtiments, six groupes) est
nouveau. La cible « plus de 10 RSEE » demande d'autres études ou l'extraction OPEE.

### Vérifications

| Contrôle | Référence | Résultat |
|---|---|---|
| Déperdition des parois de `rsee.xml`, 6 zones, dont 192 parois à U = 0 | `H_Th_op` | identique (à 0,7 % près dans une zone de 0,3 W/K) |
| Surfaces et longueurs de ponts de `rsee.xml` | `A_opv`, `A_ophh`, `A_ophb`, `A_baies`, `L_PT` | identiques à l'arrondi |
| Bbio max des 23 groupes | `O_Bbio_Max` | écart ≤ 0,05 point |
| Études en double (même contenu, deux dossiers) | Empreinte SHA-1 | comptées une fois |

### Résultats

Besoins en kWh/m², Bbio en points, DH en °C.h ; écart du Bbio de l'outil à celui de l'étude.

| Étude | Zone | Groupe | Bch outil / étude | Bfr outil / étude | Bbio outil / étude | Écart Bbio | DH outil / étude |
|---|---|---|---|---|---|---|---|
| Sète (RSEE 8619) | H3 | Groupe 1 | 0,7 / 1,1 | 7,0 / 3,3 | 24,1 / 18,0 | +34 % | 332 / 415 |
| Nice A (RSEE V5) | H3 | Groupe Traversant_Groupe CE2 | 12,1 / 13,8 | 11,6 / 4,4 | 55,8 / 45,1 | +24 % | 1 302 / 1 083 |
| Nice A (RSEE V5) | H3 | Groupe Non Traversant_Groupe CE2 | 7,2 / 6,7 | 10,2 / 7,0 | 43,7 / 36,7 | +19 % | 1 709 / 2 141 |
| Hébert (Paris, variante) | H1a | Groupe 1 | 13,3 / 15,9 | 3,0 / 1,7 | 41,2 / 44,2 | − 7 % | 786 / 853 |
| Hébert (Paris, variante) | H1a | Groupe 2 | 22,4 / 27,4 | 1,6 / 1,3 | 55,9 / 65,6 | − 15 % | 395 / 387 |
| Nice A (sans clim) | H3 | Groupe Traversant_Groupe CE1 non climatisé - BR23 | 15,4 / 15,7 | 10,3 / 4,3 | 59,5 / 48,3 | +23 % | 506 / 444 |
| Nice A (sans clim) | H3 | Groupe Non Traversant_Groupe CE1 non climatisé - BR23 | 15,6 / 17,1 | 10,8 / 5,6 | 61,1 / 54,2 | +13 % | 624 / 486 |
| Nice B | H3 | Groupe Traversant_Groupe CE2 | 13,9 / 15,1 | 11,7 / 5,3 | 59,3 / 49,3 | +20 % | 1 204 / 1 069 |
| Nice B | H3 | Groupe Non Traversant_Groupe CE2 | 9,6 / 13,0 | 12,0 / 6,1 | 52,2 / 47,9 | +9 % | 2 029 / 1 920 |
| Sète (RSENV) | H3 | Groupe 1 | 9,6 / 10,1 | 9,4 / 4,4 | 46,5 / 37,9 | +23 % | 583 / 636 |
| Sète (RSENV) | H3 | Groupe 2 | 5,0 / 5,7 | 11,0 / 5,7 | 41,1 / 32,3 | +27 % | 1 267 / 1 305 |
| rsee.xml (H2a) | H2a | Groupe BAT A - T | 15,9 / 17,8 | 0,4 / 0,0 | 41,9 / 45,6 | − 8 % | 32 / 33 |
| rsee.xml (H2a) | H2a | Groupe BAT A - NT | 2,6 / 2,8 | 0,2 / 0,1 | 16,2 / 16,8 | − 4 % | 77 / 113 |
| rsee.xml (H2a) | H2a | Groupe BAT B - T | 17,6 / 20,1 | 0,6 / 0,1 | 45,5 / 49,8 | − 9 % | 33 / 36 |
| rsee.xml (H2a) | H2a | Groupe BAT B - NT | 5,4 / 5,9 | 0,3 / 0,2 | 21,8 / 23,3 | − 6 % | 105 / 155 |
| rsee.xml (H2a) | H2a | Groupe BAT C - NT Clim | 15,7 / 17,3 | 0,9 / 0,4 | 42,9 / 45,6 | − 6 % | 194 / 308 |
| rsee.xml (H2a) | H2a | Groupe BAT C - T Clim | 31,8 / 32,3 | 0,2 / 0,1 | 73,0 / 74,3 | − 2 % | 56 / 82 |
| Nice A (04-2026) | H3 | Groupe Traversant_Groupe CE2 | 10,4 / 10,9 | 10,6 / 4,6 | 50,5 / 39,8 | +27 % | 1 161 / 1 077 |
| Nice A (04-2026) | H3 | Groupe Non Traversant_Groupe CE2 | 8,3 / 9,5 | 12,3 / 7,1 | 50,2 / 42,8 | +17 % | 1 939 / 1 979 |
| Paris (scénario 2) | H1a | Groupe 1 | 16,9 / 19,5 | 1,5 / 0,4 | 45,8 / 49,2 | − 7 % | 435 / 373 |
| Paris (scénario 2) | H1a | Groupe 2 | 27,7 / 33,0 | 0,6 / 0,3 | 64,9 / 75,3 | − 14 % | 171 / 145 |
| Sète (scénario 2) | H3 | Groupe 1 | 7,2 / 8,7 | 6,3 / 1,9 | 35,3 / 29,9 | +18 % | 207 / 354 |
| Sète (scénario 2) | H3 | Groupe 2 | 3,5 / 4,4 | 6,9 / 3,4 | 29,6 / 24,7 | +20 % | 344 / 530 |

| Zone | Groupes | Dans ± 10 % | Écart du Bbio (médiane, étendue) | Chauffage (médiane) | Froid, outil / étude (médiane) |
|---|---|---|---|---|---|
| H1a | 4 | 2 | − 10 % (− 15 à − 7 %) | − 16 % | 1,8 |
| H2a | 6 | 6 | − 6 % (− 9 à − 2 %) | − 9 % | 2,4 (sur moins de 1 kWh/m²) |
| H3 | 13 | 1 | + 20 % (+ 9 à + 34 %) | − 11 % | 2,1 |

Lecture :

- **H2a : dans la cible**, parce que le froid y pèse peu (moins de 1 kWh/m²). Le chauffage y est 9 % trop faible.
- **H1a : chauffage trop faible** (11 à 20 %), qui tire le Bbio vers le bas.
- **H3 : froid environ deux fois trop fort** (1,2 à 3,8 fois), qui tire le Bbio vers le haut malgré un chauffage
  un peu faible. C'est l'écart principal, inchangé depuis la 0.8.14.
- **DH** : de − 42 à + 28 %. Les quatre groupes de H2a aux DH faibles (77 à 308 °C.h) sortent 31 à 37 % sous
  l'étude.
- **Aucun réglage n'a été fait pour coller aux études.** Les écarts restants viennent de points de méthode
  ouverts (ci-dessous) ; les corriger demande de les comprendre, pas d'ajuster un coefficient.

### Points ouverts relevés

- **Ventilation d'hiver** : `H_Vent_Hiver` vaut 0,1397 × `Qv_occ_BBIO` dans les 23 groupes (déjà vu sur dix
  groupes en 0.8.10), contre 0,34 × (1 − 0,5) = 0,17 dans l'outil, soit + 22 %. L'occupation n'est pas en cause :
  sa moyenne de janvier et février vaut 0,79, pas 0,82. Les équations de l'indicateur (fiche 13.1, éq. 2404 à
  2408) sont des images dans le PDF : elles n'ont pas pu être relues.
- **Infiltrations d'hiver** : 15 à 44 % de l'indicateur `H_V_Def_Hiver` selon les zones ; les entrées d'air ne
  sont pas comptées (hypothèse 67). Elles expliquent sans doute une part du chauffage trop faible.
- **Froid en H3** : voir les variantes de la 0.8.10 et de la 0.8.12 ; à reprendre poste par poste, mois par mois.

### Lectures du texte et hypothèses de l'outil

90. **Paroi à U = 0 : adiabatique.** Certaines études (192 parois de `rsee.xml`) écrivent U = 0, avec Sf = 0 :
    l'outil n'y compte ni transmission ni apport solaire, quelle que soit l'inclinaison. Le U « vertical » de la
    fiche 5.17 (éq. 294) n'est pas défini pour U = 0 (division par zéro) ; l'indicateur `H_Th_op` de l'étude
    confirme la lecture.

## 0.9.9 — comparaison heure par heure à un moteur Th-BCE

Sorties horaires d'un moteur réglementaire (COMETH, version 2025.E1) pour Paris, Sète et Nice A, rangées hors du
dépôt dans `../_RSEE/Horaires`. Il y a un dossier par calcul : modes Th-B, Th-C et Th-D, et les deux variantes Th-B
sans soleil. Pour chaque groupe, environ 140 grandeurs heure par heure, plus 12 par baie. S'y ajoute le fichier
d'entrée du moteur (`Entree.xml`). `outils/comparer_horaires.py` refait chaque calcul avec l'outil et compare
33 grandeurs (tables dans `_resultats/horaires/`, hors dépôt).

### Appariement

| Calcul horaire | RSET du même calcul | Contrôle |
|---|---|---|
| Paris | `_sources/paris_scenario2_resultats_groupes_occ.xml` | Bch 19,5 / 33,0 ; DH 372,7 / 145,2 : identiques |
| Sète | `_sources/sete_scenario2_resultats_groupes_occ.xml` | Bch 8,7 / 4,4 ; DH 353,6 / 529,7 : identiques |
| Nice A | `../_RSEE/RSET/CW2020_…_2026-10-12 - sans clim.xml` | Bch 15,7 / 17,1 ; DH 444,4 / 486,2 : identiques |

Le numéro de groupe du moteur (`Zone_2_Groupe_2`) court sur tout le bâtiment ; l'ordre est celui du RSET. Le DH
recalculé à partir des colonnes horaires du moteur (`NbDegresHeures`) redonne celui de ses résultats.

### Ce qui est identique

| Grandeur | Résultat |
|---|---|
| Température extérieure, Th-B et Th-D (jeu, altitude, heure) | identique, sans décalage |
| Occupation, consignes de chauffage et de refroidissement | identiques heure par heure |
| Moyenne glissante θrm, seuil de confort chaud en occupation (Th-D) | identiques |
| Calcul du DH : θop de fin d'heure du moteur et son seuil corrigé | 372,7 °C.h, comme le moteur |
| Protections mobiles (moyenne des baies) | Paris à 2 % près (Th-B et Th-D) ; Sète + 14 % en Th-B, + 2 à 4 % en Th-D ; Nice voir point 6 |
| Transmission des baies de l'heure (`O_Hges`) | à 0,1 % près (Nice : 2 %) |
| Apports des occupants | identiques |
| Air entrant en Th-D (`O_Temp_eieq`) | égal à la température extérieure chez le moteur aussi (hypothèse 75, pour ces trois études) |
| Saison de chauffage | à 1 à 4 % des heures près en Th-B |

### Écarts, du plus fort au plus faible

Écart = outil / moteur − 1, sur l'année, groupe par groupe (Paris, Sète, Nice).

| Grandeur | Th-B | Th-D | Lot |
|---|---|---|---|
| Ouverture des baies (moyenne) | − 48 à − 88 % | − 31 à − 52 % | L3 |
| Renouvellement d'air `O_Hgei` | − 23 à − 79 % | − 6 à − 45 % | L3, L5 |
| Heures de refroidissement autorisé | + 56 à + 122 % | (sans objet) | L2 |
| Flux des parois opaques Φsh | − 37 à − 92 % | − 19 à − 87 % | L4 |
| Éclairement naturel | + 20 à + 30 % | + 33 à + 83 % | L4 |
| Apports des usages (`O_Phiint_*_Proc`) | − 7 % | − 7 % | L4 |
| Flux solaire des baies Fs1 | − 30 à + 19 % | − 9 à + 41 % | L4 |
| Besoin de chauffage | − 2 à − 21 % | | résultat |
| Besoin de refroidissement | + 77 à + 263 % | | résultat |
| Degrés-heures | | − 41 à + 28 % | résultat |

**1. Ouverture des baies en Th-B, hors saison de froid (L2, L3).** Le moteur ouvre les baies à la mi-saison,
d'avril à juin et de septembre à octobre, jamais en saison de chauffage. Sur le groupe 1 : 946 heures à Paris,
1 929 à Sète, 1 605 à Nice. L'outil n'ouvre qu'en saison de refroidissement, comme le dit l'annexe III, fiche 5.13,
§ 5.13.3.1.2 : « Hors période d'autorisation de refroidissement (Autfr,pro(j) = 0) : Mod_ext_man(h) = 0 »
(éq. 244). Sans cet air frais, la mi-saison de l'outil est plus chaude de 0,4 à 1,1 °C (mai, juin, septembre). Le
cumul d'inconfort chaud atteint alors le seuil de la fiche 4.6 dès mai. La saison de froid de l'outil commence
aux jours 126 à 148 et finit aux jours 246 à 267, soit 98 à 140 jours. Celle du moteur commence au jour 176
ou 183 (le refroidissement d'office) et finit au jour 246 ou 250, soit 63 à 74 jours. D'où un froid 1,8 à
3,6 fois trop fort. C'est l'écart principal du Bbio en H3. **Décision du 19/11/2026 : l'outil suit le moteur**
(hypothèse 91, correction ci-dessous).

**2. Infiltrations d'hiver (L5).** En janvier et février, le renouvellement d'air effectif du moteur,
Hgei × (θi − θeieq) / (θi − θe), est retrouvé à 1-2 % près en prenant la ventilation de l'outil (débit du
Bbio, échangeur à 0,5) plus des infiltrations égales à Hgei − 0,34 × débit :

| Étude | Groupe | Débit (m³/h) | Infiltrations outil (W/K) | Infiltrations moteur (W/K) | Rapport | H effectif prévu / moteur (W/K) |
|---|---|---|---|---|---|---|
| Paris | 1 | 1 040 | 19 | 68 | 3,5 | 245 / 241 |
| Paris | 2 | 6 008 | 503 | 990 | 2,0 | 2 011 / 1 988 |
| Sète | 1 | 3 827 | 415 | 617 | 1,5 | 1 268 / 1 259 |
| Sète | 2 | 3 066 | 64 | 187 | 2,9 | 708 / 701 |
| Nice A | 1 | 2 193 | 151 | 237 | 1,6 | 609 / 605 |
| Nice A | 2 | 422 | 5 | 15 | 3,3 | 87 / 86 |

La ventilation du Bbio de l'outil est donc juste. Les infiltrations sont 1,5 à 3,5 fois trop faibles, ce qui
explique le chauffage trop faible (− 2 à − 21 %). Piste déjà notée : les entrées d'air du projet (hypothèse 67).
L'indicateur `H_Vent_Hiver` des RSET (0,1397 × débit, 0.9.8) ne correspond donc pas au calcul horaire du
moteur. C'est un indicateur de sortie, pas un terme du bilan.

**3. Flux des parois opaques Φsh (L4).** Le moteur en compte 1,2 à 13 fois plus. Ses colonnes `O_Fsh_s_pt` et
`O_Fsh_vc_pt` (flux solaire et voûte céleste des ponts thermiques) montrent ce qui manque à l'outil (fiche 5.19,
éq. 300 et 306, « non repris » dans `comparer_reference`).

**4. Apports des usages et éclairement naturel (L4).** Les apports « Proc » du moteur dépassent ceux de l'outil
de 7 %, avec une part qui varie selon le mois (+ 11 % en hiver, + 3 % en été) : un terme est à identifier. Les
pertes récupérées (`O_Pertes_Recup_*`) sont à examiner. L'éclairement naturel de l'outil est 20 à 80 % plus fort
(`O_Einat`, définition à vérifier). Le besoin d'éclairage reste à − 2 à − 5 %.

**5. Th-D (L6).** Le seuil de confort et le calcul du DH sont ceux du moteur. L'écart du DH vient entièrement
de la température opérative : par exemple, à Paris, la θop de l'outil avec le seuil du moteur donne 434 °C.h,
contre 372,7. En été, l'outil ouvre 31 à 52 % moins que le moteur ; un jour chaud d'août à Paris, le moteur
ouvre à 0,49 ou 0,70 selon la baie, l'outil à 0,20. Le débit de ventilation hors occupation du moteur est plus
faible (Paris : 270 contre 360 W/K ; ventilation du projet, hypothèse 75).

**6. Divers.** À Nice A, groupe 2, les protections de l'outil sont fermées 47 % plus souvent en Th-B (stores
vénitiens, 0.9.8). L'autorisation de refroidissement de Th-D (`O_Auth_fr`) vient de la génération et vaut 0 :
elle ne se compare pas à la saison propre de l'outil.

Les chiffres ci-dessus sont ceux d'avant la correction de l'ouverture en Th-B.

### Correction : ouverture des baies en Th-B, l'outil suit le moteur (hypothèse 91)

**L'outil s'écarte ici volontairement du texte de l'annexe pour suivre le moteur réglementaire.** Pour savoir ce
que fait le moteur en Th-B, on a relevé ses colonnes `O_Rouv` (baie par baie), `O_Auth_fr`, `O_Auth_ch`,
`O_Ind_occ`, `O_Temp_ext` et `O_Temp_Cons_Init_Fr` sur les 6 groupes :

| Constat sur le moteur (6 groupes, mode Th-B) | Heures |
|---|---|
| Baies ouvertes hors occupation | 0 |
| Baies ouvertes en saison de chauffage | 0 (θop occupée ≤ 21,0 à 23,5 °C, sous θouv1 = 25 °C) |
| Baies ouvertes à la mi-saison (ni chauffage ni froid) | 564 à 2 297 par groupe |
| En période de refroidissement, ouvertes avec θe > consigne − 1 °C | 0 sur 128 à 545 heures possibles |
| À la mi-saison, ouvertes avec θe > consigne − 1 °C | 59 à 252 sur 75 à 265 heures possibles |

Le moteur applique donc :

- en période de refroidissement, la règle du § 5.13.3.1.2 : Mod_ext plafonné à la consigne − 1 °C ;
- hors de cette période, la règle générale de la gestion manuelle (Mod_ext de la figure 61, sans plafond), au
  lieu de Mod_ext_man = 0 (éq. 244) ;
- dans tous les cas, baies fermées et Rouv_op remis à zéro hors occupation (éq. 245).

L'outil fait de même (`moteur/ouvertures.py`, réglage `OUVERTURE_TH_B_COMME_LE_MOTEUR = True` ; `False` rend la
lecture du texte). Effet, outil face au moteur (Th-B ; écarts outil / moteur − 1) :

| Étude | Groupe | Saison de froid, outil avant → après (jours ; moteur) | Froid avant → après | θop mai, juin, sept. avant → après |
|---|---|---|---|---|
| Paris | 1 | 147-246 → 183-246 (183-246) | + 263 % → + 167 % | + 1,10 → + 0,07 °C |
| Paris | 2 | 148-246 → 183-246 (183-246) | + 77 % → + 47 % | + 0,61 → − 0,25 °C |
| Sète | 1 | 126-259 → 174-259 (183-246) | + 228 % → + 210 % | + 0,62 → + 0,50 °C |
| Sète | 2 | 127-262 → 175-262 (176-246) | + 106 % → + 107 % | + 0,49 → + 0,59 °C |
| Nice A | 1 | 126-266 → 175-266 (183-246) | + 140 % → + 111 % | + 0,41 → + 0,35 °C |
| Nice A | 2 | 127-267 → 174-267 (176-250) | + 93 % → + 82 % | + 0,46 → + 0,55 °C |

La saison de froid de Paris est maintenant celle du moteur, au jour près. À Sète et Nice, elle commence au bon
moment mais finit 13 à 21 jours trop tard : le besoin de froid d'août et de septembre reste au-dessus du seuil
d'arrêt (2 Wh/m² par heure sur 4 semaines). Le froid reste trop fort, parce que l'outil ouvre encore 23 à 64 % moins
que le moteur (mi-saison : 0,5 à 0,9 fois son renouvellement d'air), comme en Th-D. Le chauffage et le DH ne
changent pas.

Bbio des 23 groupes de la validation de la 0.9.8 (`python -m outils.valider --dh`), avant → après :

| Zone | Groupes | Dans ± 10 % | Écart du Bbio (médiane, étendue) | Froid, outil / étude (médiane) |
|---|---|---|---|---|
| H1a | 4 | 2 → 2 | − 10 % → − 11 % (− 16 à − 8 %) | 1,8 → 1,6 |
| H2a | 6 | 6 → 5 | − 6 % → − 7 % (− 11 à − 2 %) | 2,4 → 1,4 (sur moins de 1 kWh/m²) |
| H3 | 13 | 1 → 1 | + 20 % → + 17 % (+ 3 à + 22 %) | 2,1 → 1,9 |

En H3, l'écart du Bbio baisse de 2 à 14 points sur 12 groupes (Sète RSEE 8619 : + 34 → + 20 %) ; Sète
scénario 2, groupe 2, reste à + 20 %. En H1a et H2a, il baisse aussi
un peu, ce qui creuse l'écart déjà négatif dû au chauffage trop faible : le groupe BAT B - T de `rsee.xml` passe
de − 8,6 à − 10,6 %. Le DH ne change pas (− 41 à + 28 %).

Depuis la 0.9.8, `../_RSEE` compte de nouvelles études (Strasbourg et ses variantes de climat) : la validation porte
maintenant sur 16 études et 58 groupes, dont 13 dans ± 10 % (écart médian du Bbio + 15 %, `_resultats/validation.csv`).
Ces études n'ont pas encore été examinées.

Cas non vérifié : en saison de chauffage, un groupe surchauffé (θop ≥ 25 °C, petit bâtiment de test en H3) ouvre
aussi ses baies avec la règle générale (Cpr = 0,3). Les études du moteur n'atteignent jamais ce seuil en hiver :
elles ne disent pas si le moteur ouvre alors.

### Suites proposées

Dans l'ordre : le ratio d'ouverture des baies, encore 23 à 64 % sous le moteur en Th-B et 31 à 52 % en Th-D
(valeurs baie par baie de `O_Rouv` : 0,49 ou 0,70 un jour chaud) ; les infiltrations (point 2) ; Φsh des ponts
thermiques (point 3). Chaque correction se vérifie avec `python -m outils.comparer_horaires tous`.

### Lectures du texte et hypothèses de l'outil

91. **Ouverture des baies en Th-B hors période de refroidissement : comme le moteur, pas comme le texte.** La
    fiche 5.13 (§ 5.13.3.1.2, éq. 244) annule l'ouverture hors période d'autorisation de refroidissement. Le moteur
    réglementaire COMETH 2025.E1, relevé heure par heure sur 6 groupes (Paris, Sète, Nice A), applique à la place la
    règle générale de la gestion manuelle. Le plafond « consigne de froid − 1 °C » ne vaut qu'en période de
    refroidissement, et rien ne s'ouvre hors occupation. L'outil suit le moteur (décision du 19/11/2026), avec le
    réglage `OUVERTURE_TH_B_COMME_LE_MOTEUR` de `moteur/ouvertures.py` pour revenir au texte. Le sens de
    « Autfr,pro(j) » dans l'annexe reste à éclaircir.

## 0.9.10 — ouverture des baies et infiltrations

Deux corrections guidées par les sorties horaires du moteur (0.9.9). Aucun coefficient n'est ajusté : l'une
applique un tableau du texte que l'outil ignorait, l'autre suit le moteur sur un point que le texte ne tranche pas.

### Protection mobile devant une baie ouverte (fiche 5.12)

L'outil considérait qu'une protection fermée bloque tout l'air (hypothèse de la 0.8.12) : une baie protégée à
70 % ne pouvait plus s'ouvrir qu'à 30 %. La fiche 5.12 (tableau 40, éq. 239) donne un taux de passage de l'air
selon la typologie de la protection (`Typo_Permea_PM` des études) : 0 % (typologie 0, par défaut), 10 % (1 : tablier
peu ajouré, le cas des volets roulants), 25 % (2), 50 % (3) et 75 % (4 : très ajourée, stores vénitiens) :

    Aouvmax_ac_PM = Aouvmax × (Rprot × Taux_passage + 1 − Rprot)
    Aouv = MIN(Aouvmax_ac_PM ; Rouv × Aouvmax)                    (éq. 248-249)

Contrôle sur le moteur (Paris, groupe 1, Th-D, une nuit d'août, protections fermées à 70 %) : sa colonne
`O_Rouv_corrige` vaut 0,568 sur les baies de typologie 1, soit 0,21 / (0,7 × 0,1 + 0,3), et 0,848 sur celles de
typologie 4, soit 0,7 / (0,7 × 0,75 + 0,3). Les études lues : typologies 1 (254 baies), 3 (49) et 4 (14) à Paris.

### Entrées d'air dans les infiltrations du Bbio (hypothèse 92)

En hiver, le renouvellement d'air du moteur se retrouve à 1-2 % près avec la ventilation de l'outil plus des
infiltrations 1,5 à 3,5 fois plus fortes que les siennes (0.9.9). Les entrées d'air du projet (`Entree_Air`,
module en m³/h sous 20 Pa, par groupe) expliquent l'écart. Essai hors moteur, avec les températures du moteur
(janvier et février, m³/h) :

| Étude | Groupe | Module | Moteur | Outil sans entrées d'air | Outil avec |
|---|---|---|---|---|---|
| Paris | 1 | 1 397 | 201 | 57 | 143 |
| Paris | 2 | 5 182 | 2 912 | 1 479 | 2 347 |
| Sète | 1 | 5 871 | 1 815 | 1 221 | 2 703 |
| Sète | 2 | 2 662 | 549 | 187 | 418 |
| Nice A | 1 | 1 795 | 696 | 443 | 846 |
| Nice A | 2 | 389 | 45 | 14 | 47 |

Avec les entrées d'air, le total des six groupes vaut 1,05 fois celui du moteur, contre 0,55 sans elles ; groupe
par groupe, 0,7 à 1,5 fois. L'altitude des entrées d'air pèse peu : 0,68 au lieu de 0,92 change moins de 10 %.

### Résultats face au moteur (écarts outil / moteur − 1, 0.9.9 → 0.9.10)

| Étude | Groupe | Chauffage | Froid | Ouverture Th-B | Ouverture Th-D | DH |
|---|---|---|---|---|---|---|
| Paris | 1 | − 14 → − 4 % | + 167 → + 135 % | − 23 → − 20 % | − 40 → − 27 % | + 17 → − 6 % |
| Paris | 2 | − 16 → − 6 % | + 47 → + 25 % | − 37 → − 28 % | − 50 → − 32 % | + 18 → + 6 % |
| Sète | 1 | − 17 → + 47 % | + 210 → + 189 % | − 63 → − 54 % | − 47 → − 26 % | − 41 → − 33 % |
| Sète | 2 | − 21 → − 3 % | + 107 → + 71 % | − 64 → − 48 % | − 52 → − 31 % | − 35 → − 37 % |
| Nice A | 1 | − 2 → + 15 % | + 111 → + 83 % | − 56 → − 48 % | − 31 → − 20 % | + 14 → + 17 % |
| Nice A | 2 | − 9 → − 1 % | + 82 → + 71 % | − 57 → − 46 % | − 36 → − 16 % | + 28 → + 30 % |

- Le chauffage est maintenant à ± 6 % du moteur dans quatre groupes sur six. Il dépasse dans les deux groupes
  traversants du sud (Sète 1 : + 47 %, Nice A 1 : + 15 %), où l'outil fait entrer trop d'air en hiver (Sète 1 :
  2 221 contre 1 918 W/K). La répartition des entrées d'air et les coefficients de pression des zones traversantes
  sont à revoir (tableau 23).
- Le froid baisse partout, mais reste 1,3 à 2,9 fois trop fort. L'ouverture des baies reste 20 à 54 % sous le
  moteur en Th-B, et le renouvellement d'air de mi-saison 0,6 à 0,9 fois le sien.
- Le DH de Paris est à ± 6 % ; celui de Sète reste 33 à 37 % trop bas (brasseurs de nuit), celui de Nice 17 à
  30 % trop haut.

### Lectures du texte et hypothèses de l'outil

92. **Entrées d'air du projet gardées en mode Bbio** (remplace la 67), comme le moteur réglementaire. Le texte ne
    dit pas ce qu'elles deviennent sous la double flux conventionnelle du Bbio. Lois : entrée fixe, q = M ×
    (|ΔP| / 20 Pa)^0,5 (éq. 141, tableau 21), sans autoréglage ni anti-retour (les modules autoréglables de Nice
    ne changent de comportement qu'au-delà de 20 Pa). Répartition du tableau 25 : un quart au vent et sous le
    vent, en haut et en bas, à une seule altitude en logement, 0,92 × MIN(h ; 3). Cette valeur est lue dans un
    tableau mal extrait du PDF (0,92 ou 0,68) ; l'écart est faible. Les entrées d'air d'un groupe sont la somme de
    ses `Entree_Air` dans le RSET ; l'interface n'en saisit pas.

### Bbio des 23 groupes de la validation (0.9.9 → 0.9.10)

| Zone | Groupes | Dans ± 10 % | Écart du Bbio (médiane ; étendue après) | Chauffage (médiane ; étendue après) | Froid, outil / étude |
|---|---|---|---|---|---|
| H1a | 4 | 2 → 4 | − 11 → − 4 % (− 6 à 0 %) | − 16 → − 6 % (− 7 à − 4 %) | 1,6 → 1,4 |
| H2a | 6 | 5 → 3 | − 7 → + 10 % (− 4 à + 18 %) | − 9 → + 17 % (− 4 à + 45 %) | 1,4 → 1,4 |
| H3 | 13 | 1 → 0 | + 17 → + 23 % (+ 11 à + 50 %) | − 11 → + 7 % (− 12 à + 53 %) | 1,9 → 1,7 |

Le DH va de − 37 à + 30 %. Sur les 58 groupes de 16 études : 18 dans ± 10 % (13 avant), écart médian + 22 % (+ 15 %).

Lecture :

- **H1a : dans la cible**, chauffage à − 4 à − 7 %, comme les sorties horaires de Paris le laissaient prévoir.
- **H2a et H3 : chauffage parfois trop fort.** Les entrées d'air font entrer trop d'air dans certains groupes :
  Sète (RSENV et scénario 2, zone traversante) + 46 à + 53 %, `rsee.xml` BAT A - NT (92 m²) + 45 %. L'hypothèse 92
  est juste en moyenne sur les six groupes horaires mais trop forte là. Pistes : coefficients de pression des zones
  traversantes, partage des entrées d'air entre façades, anti-retour et autoréglage, bilan par zone (hypothèse 66).
- **H3 : le froid reste l'écart principal** (1,7 fois l'étude). Le chauffage ne le compense plus : le Bbio s'écarte
  davantage, alors que chacun des deux postes se rapproche du moteur.
- La version 0.9.9 de la table : `_resultats/validation_0.9.9.csv` ; celle de la 0.9.8 :
  `_resultats/validation_0.9.8_avant_ouverture.csv` (hors dépôt).

## 0.9.11 — relecture indépendante de la 0.9.8

Relecture faite dans claude.ai sur la 0.9.8 (commit `acab5fb`), fiche `relecture_0.9.8.md` (à la racine, non
suivie par git) : un relecteur par module, avec `moteur/`, `donnees/hypotheses.csv` et l'annexe III seulement, sans
CHANGELOG, ROADMAP, audit ni tests. Les commentaires du code et les sources des hypothèses y sont pris pour des
affirmations à vérifier. Le moteur n'avait pas tourné : les effets annoncés étaient estimés. Ils sont mesurés ici,
sur la version 0.9.10, face au moteur COMETH (sorties horaires de Paris, Sète et Nice A, 0.9.9) et face aux études
(`outils/valider.py`). Tables dans `_resultats/mesures_0.9.11/` (hors dépôt).

### Décompte de la relecture

| Module | Fiches | Conformes | Écarts | Simplifications | Non vérifiables |
|---|---|---|---|---|---|
| `groupe.py` | 5.21 (+ 6.1, 6.2) | 40 | 2 | 8 | 4 |
| constantes de `groupe.py` | 5.21, 6.1, 6.2, 4.1, 8.1 | 30 | 0 | — | 4 |
| `besoins.py` | 13.1, 6.1, 4.6, 4.5, 8.1 (+ 5.13, 13.5, 8.5) | 28 | 3 | 1 | 4 |
| `ouvertures.py` | 5.13 (+ 3.1, 13.5) | 22 | 2 | 3 | 2 |
| `protections.py` + deux CSV | 5.9 (+ 4.1, 5.10) | 28 | 1 | 10 | 2 |
| `solaire.py` | 3.2, 3.1 (+ 5.10, 5.17) | 24 | 1 | 6 | 3 |
| `infiltrations.py` | 5.6 (+ 5.21, 6.1, 3.2) | 18 | 1 | 7 | 4 |

Restent à relire : `enveloppe.py`, `apports.py`, `eclairage.py`, `bbio.py`, `dh.py`, `confort.py`, `brasseurs.py`,
`meteo.py`, `scenarios.py`, `calendrier.py`, `masques.py`.

Résultat principal de la relecture : le noyau est juste (réseau RC concordant à 4·10⁻¹⁴ près avec une résolution
directe, bilan d'énergie fermé, constantes conformes, 54 lignes des tables de protections conformes).

### Mesures et décisions

Écarts outil / moteur − 1 (Th-B, 6 groupes) ; « avant » = 0.9.10, « après » = 0.9.11.

| Étude | Groupe | Froid avant → après | Ouverture des baies avant → après | Saison de froid de l'outil, avant → après (moteur) |
|---|---|---|---|---|
| Paris | 1 | + 135 → − 10 % | − 20 → + 6 % | jours 183-246 → 183-246 (183-246) |
| Paris | 2 | + 25 → − 33 % | − 28 → + 7 % | 183-246 → 183-246 (183-246) |
| Sète | 1 | + 189 → − 11 % | − 54 → + 6 % | 176-259 → 183-246 (183-246) |
| Sète | 2 | + 71 → − 34 % | − 48 → + 6 % | 183-262 → 183-246 (176-246) |
| Nice A | 1 | + 83 → − 10 % | − 48 → + 5 % | 183-266 → 183-246 (183-246) |
| Nice A | 2 | + 71 → − 2 % | − 46 → + 10 % | 176-267 → 176-257 (176-250) |

Le chauffage (− 6 à + 48 % ; Sète 1 et Nice A 1 trop forts, entrées d'air) et le DH (− 37 à + 30 %) ne changent
pas.

| Point | Mesure | Décision (19/11/2026) |
|---|---|---|
| **T1** Δθconf_adapt dans les seuils d'ouverture en Th-B | L'outil prenait 0,33 θrm + 18,8 + 2 − θiifr (sans plafond ni règle de nuit) : en été, θouv dépassait la consigne et les baies ne s'ouvraient presque plus. À 0 : tableau ci-dessus ; validation, H3 de 0 à 9 groupes sur 13 dans ± 10 % | **corrigé** : nul en Th-B (fiche 13.5, éq. 2546 ; fiche 5.13, éq. 242), hypothèse 93 |
| **T2** facteur 0,5 de l'éq. 61 | Saison de froid de Nice A, groupe 2 : début au jour 183 au lieu de 176 (moteur : 176) ; validation, H3 + 1 groupe dans la cible | **gardé à 1** (hypothèse 94) |
| **T3.1** Q4Pa absente | Les 46 groupes de la validation donnent tous Q4Pa (0,5 à 1,0) | défaut du tableau 30 (1 m³/(h.m²)) à la lecture d'un RSET qui n'en donne pas, signalé ; sans effet sur la validation |
| **T3.2** entrées d'air | — | déjà fait en 0.9.10 (hypothèse 92) |
| **T3.3** traversant d'hiver | Diffère du traversant d'été dans 4 groupes : Vélizy cage B (traversant l'été, pas l'hiver), chauffage + 55 → + 32 % ; Saint-Ouen (zone traversante, groupes non traversants l'été), + 22 → + 38 % | **celui de la zone** (`Is_Traversant`) pour les infiltrations (hypothèse 95) |
| **T3.4** hmoy absente | Toujours donnée par les RSET et l'interface | avertissement si elle manque (zone traversante) |
| **T6** ventilation d'hiver 0,1397 | 0,1397 = 1006 × 0,5 / 3600 : éq. 382 de la fiche 6.1, indicateur de sortie (débit en m³/h, 1 kg/m³) ; le bilan (éq. 333) prend 0,34, comme l'outil | piste close |
| **T9** heure légale | Face au moteur, heure par heure (Paris, Th-D) : le seuil de confort de nuit (éq. 2544) bascule aux mêmes heures légales (7 h et 23 h de début de pas), le Cpr de nuit de l'ouverture des baies aussi (22 h) | **inchangé** : même convention que le moteur (hypothèse 42) |
| **T11** Sw2 = 0,2 × Sw | Aucun effet : les études donnent Sw2 (`Sw2_sp_e`, 15 à 20 % de Sw) ; le défaut ne sert qu'à l'interface | inchangé ; noté dans `ROADMAP.md` |

Validation (`python -m outils.valider --dh`), avant → après :

| Groupes | Dans ± 10 % | Écart du Bbio, médiane (étendue après) | Chauffage, médiane (étendue) | Froid, outil / étude (médiane) |
|---|---|---|---|---|
| H1a (4) | 4 → 4 | − 4 → − 5 % (− 7 à − 4) | − 6 % (− 7 à − 4) | 1,43 → 0,83 |
| H2a (6) | 3 → 3 | + 10 → + 9 % (− 4 à + 18) | + 17 % (− 4 à + 45) | 1,40 → 0,73 |
| H3 (13) | 0 → 9 | + 23 → − 2 % (− 12 à + 27) | + 7 % (− 12 à + 53) | 1,73 → 0,97 |
| 23 groupes de la 0.9.8 | 7 → 16 | + 16 → − 2 % | + 7 % | 1,70 → 0,90 |
| 46 groupes de 16 études | 18 → 29 | + 16 → − 2 % (− 12 à + 47) | + 5 % | 1,73 → 0,89 |

- **Le froid de H3 n'est plus l'écart principal** : 0,97 fois l'étude en médiane (0,65 à 1,24). Face au moteur, il
  est maintenant un peu faible (− 2 à − 34 %) ; les baies s'ouvrent 5 à 10 % de plus que chez le moteur.
- **Écart principal restant : le chauffage trop fort de certains groupes** (entrées d'air, 0.9.10) : Sète traversant
  (+ 47 à + 53 %, Bbio + 25 à + 27 %), `rsee.xml` (jusqu'à + 45 %), les études récentes (Vélizy, Saint-Ouen).
- **Comptage des groupes** : `outils/valider.py` joignait le DH par le seul nom du groupe. Vélizy répète ses noms
  d'une zone à l'autre : ses 6 groupes comptaient pour 18 lignes, avec des DH mêlés. Les « 58 groupes » des 0.9.9
  et 0.9.10 sont en fait 46 (en 0.9.10, 18 sur 46 dans ± 10 %). Jointure corrigée (bâtiment, zone, groupe) ; les
  chiffres ci-dessus sont dédoublonnés.

### Autres suites données à la relecture

| Point | Suite |
|---|---|
| T4 frs, frsd | déjà documenté (hypothèses 18 et 19) ; c'est un choix de formule, pas une constante : pas de ligne dans `hypotheses.csv` |
| T5 Hg_es.θes (éq. 366) | gardé (hypothèse 17) ; test ajouté : groupe avec baies, sans apport, à température uniforme, stable heure après heure |
| T5 froid pour tous les groupes | gardé (hypothèse 29) |
| T5 seuil C1 de l'inconfort chaud | gardé et documenté (hypothèse 96) |
| T7 `chaleur_volumique_air` | source corrigée : éq. 377 et 379 ; l'éq. 382 prend Cpa = 1006 J/(kg.K) |
| T7 `debit_ventilation` | renvoi corrigé (éq. 403, débit moyen avec Dugd = 14) ; règle du non résidentiel notée (la zone n'admet que le logement collectif) |
| T7 3,6 kJ par Wh | en-tête de `moteur/hypotheses.py` : les conversions d'unités restent dans le code |
| T3.7 Cvent = 0,9 | source corrigée : fiche 3.2, p. 40 |
| T10 store enroulable par grand vent | **corrigé** : en gestion manuelle, remonté seulement en occupation (éq. 192-193) ; en gestion automatique, occupé ou non (éq. 190-191) ; test ajouté. Sans effet visible sur la validation |
| T10 citations de la fiche 5.9 | en-tête et docstrings : éq. 188-189 (volets), 190-193 (stores), fiche jusqu'à l'éq. 205 |
| T10 Httf | garde : saisi seulement au-delà de 4 m, 15 m au plus (`Groupe` refuse ; la lecture d'un RSET ramène à 1,5 m ou plafonne à 15 m, et le signale). Aucun groupe de logement des études n'a de Httf saisi |
| T10 θop(h−1), β ≥ 60° | lectures de l'outil, notées dans l'en-tête de `ouvertures.py` (hypothèse 97) |
| T11 coefficients EDn | déjà exacts depuis la 0.9.8 (−1,03753210E-08, −3,31804423E-04, −6,72171072E-01) : la remarque ne s'appliquait pas |
| T11 variable du polynôme EDn | commentaire corrigé : le « x » est un signe de multiplication, la variable est γ, lue en degrés (hypothèse 98) ; EDn borné à 0 (aucune heure concernée dans les fichiers météo) |
| T8, T10, T11, T3.6 : simplifications et points mineurs | inscrits dans `ROADMAP.md` (« Relecture indépendante de la 0.9.8 ») |

### Lectures du texte et hypothèses de l'outil

93. **Δθconf_adapt nul en Th-B** (lecture du texte ; l'outil prenait l'écart de la fiche 4.5). La fiche 13.5 ne le définit
    qu'en Th-D (éq. 2542 à 2546) ; en Th-B, θouv2 = θiifr − 1 (fiche 5.13, éq. 242). Confirmé par le moteur :
    ouverture des baies et fin de saison de froid retrouvées.
94. **Facteur de l'éq. 61 lu égal à 1.** Le texte imprime (iinconf_cons,ch + 1) / 2, qui vaut 0,5 en inconfort chaud
    occupé. La structure de l'éq. 60 (même indice dans les deux facteurs, le second ne servant qu'à annuler
    l'inoccupation, où iinconf = −1) fait lire (iinconf_C1,fr + 1) / 2 = 1 : coquille probable. Le moteur va dans
    ce sens : avec 0,5, Nice A, groupe 2, démarrerait son froid au jour 183 au lieu de 176, celui du moteur.
95. **Caractère traversant des infiltrations : celui de la zone au sens des conditions d'hiver** (fiche 5.6,
    tableau 22 : traversant au sens du confort d'été et portes intérieures détalonnées), lu dans `Is_Traversant`
    de la zone (`Groupe.traversant_hiver`) ; l'ouverture des baies garde le traversant d'été du groupe
    (`Delta_trav_surv`, tableau 43). À confirmer sur une sortie horaire d'une étude où les deux diffèrent.
96. **Seuil d'inconfort chaud du démarrage du froid : C1** (fiche 4.6) : les tableaux 9-10 imposent C1, les éq. 82-84
    écrivent « cons » ; l'outil suit les tableaux.
97. **Ouverture des baies : θop(h−1) et β ≥ 60°.** L'hystérésis lit θop(h−1), comme la figure 62 (la nomenclature,
    tableau 41, cite θop,fin(h−2)) ; une baie est en façade si β ≥ 60°, comme la prose de la p. 269 (l'éq. 253
    imprime « β < 60° »).
98. **Polynôme EDn en γ, en degrés** (fiche 3.1, p. 32). La nomenclature donne γ en radians ; seule la lecture en
    degrés est plausible (environ 105 lm/W, contre 20 lm/W au plus en radians).

## 0.9.13 — protections mobiles de la boîte (guide Actibaie)

Source : *Les protections solaires dans la RE 2020*, groupement Actibaie (avec FFB, AICVF et Pouget Consultants),
version 8, mars 2024, guide professionnel non réglementaire. Le PDF et sa note d'analyse
(`_sources/guide_protections_solaires_re2020.md`, avec les tableaux transcrits) restent hors du dépôt. Ce qui en
était déjà dans le moteur : perméabilité des protections fermées (p. 27 = fiche 5.12, tableau 40, fait en 0.9.10),
Sw1, Sw2, Sw3 et U de la baie protégée (fait en 0.8.12, lus dans les RSET).

### Hypothèse

99. **Protection de la boîte : perméabilité et part réémise selon le type** (`interface/saisie.py`,
    `_conventions_protection` ; clés `boite_…` de `donnees/hypotheses.csv`). La boîte ne fait saisir ni la typologie
    Typo_PM ni Sw2 protégé. Jusqu'en 0.9.11, un volet était étanche (Typo_PM 0, défaut de la méthode) et son Sw
    protégé entrait tout en Sw1 (transmis). Désormais : Typo_PM 1 (10 % de l'air, volets roulants et battants, stores
    enroulables guidés, p. 27) ; Sw protégé tout en Sw2 pour un volet (protection extérieure opaque : Sw1 = 0,
    p. 46), à 40 % pour un store enroulable (toile claire, Sw1 0,08 et Sw2 0,05, p. 47). Le Sw protégé lui-même
    reste celui du niveau d'enveloppe (0,03 / 0,07 / 0,10, tiré des études), plus haut que celui du guide pour un
    volet opaque (0,02 à 0,04). Sans effet sur une étude lue (RSET), qui donne ces grandeurs.

### Effet sur les bâtiments de départ (DH, °C.h ; Bbio à ± 0,4 point)

| Bâtiment | Performant | Moyen | Faible |
|---|---|---|---|
| Logement de 70 m² (H1a) | 639 → 559 | 804 → 728 | 969 → 883 |
| Immeuble de 9 logements (H1a) | 524 → 454 | 685 → 601 | 848 → 744 |

En 0.9.11, sur le logement de 70 m² (niveau moyen), les volets motorisés **augmentaient** le DH (808 contre 790 sans
protection) : la fermeture de nuit coupait l'aération par les baies plus que le volet ne coupait le soleil.

### Tendances du guide sur la boîte (niveau moyen, volets motorisés sauf mention)

| Cas | H1a DH | H1a Bbio | H3 DH | H3 Bbio | H3 froid |
|---|---|---|---|---|---|
| Sans protection | 790 | 118,6 | 1 572 | 88,9 | 6,3 |
| Volet, manuelle non motorisée | 741 | 121,2 | 1 441 | 91,9 | 5,9 |
| Volet, manuelle motorisée | 728 | 119,7 | 1 395 | 92,2 | 6,7 |
| Volet, automatique | 558 | 118,2 | 995 | 84,0 | 3,6 |
| Volet motorisé, Typo_PM 0 | 808 | 119,9 | 1 605 | 94,5 | 7,8 |
| Volet motorisé, Typo_PM 4 | 531 | 119,3 | 1 007 | 88,2 | 4,7 |
| Store enroulable motorisé | 618 | 121,0 | 1 137 | 88,2 | 4,5 |

- **Reproduit** (testé, `tests/test_tendances.py`) : ordre des gestions sur le DH, sans protection > manuelle non
  motorisée > manuelle motorisée > automatique (pp. 28-29).
- **Non reproduit 1 : effet des protections sur le DH.** Le guide divise le DH par environ 2 (maison individuelle H3 :
  1 842 → 950 en gestion motorisée, p. 28 ; immeuble H2b : 1 262 → 763 en non traversant, p. 29) ; la boîte en H3
  ne gagne que 11 % (1 572 → 1 395).
- **Non reproduit 2 : effet de la typologie Typo_PM.** Faible et de signe variable dans le guide (10 à 60 °C.h entre
  10 et 75 %, pp. 28-29 ; Bbio identique, p. 7) ; fort dans l'outil (H3 : 1 605 à 1 007 °C.h de Typo_PM 0 à 4, Bbio
  94,5 à 88,2). L'outil réduit l'ouverture de la baie de Rprot × (1 − passage d'air) (fiche 5.12, éq. 239), avec
  des volets fermés la nuit à 70 % ou plus : l'aération nocturne en dépend fortement. Piste à rapprocher du ratio
  d'ouverture en Th-D, 16 à 32 % sous celui du moteur (0.9.11) : comparer, heure par heure, ouverture et Rprot
  des études de Paris, Sète et Nice A (`outils/comparer_horaires.py`).
- **Non reproduit 3 : Bbio.** Le guide range le Bbio comme le DH (H3 : 79 sans protection, 65 à 66 en manuel, 54
  en automatique, p. 7) ; dans l'outil, les volets manuels l'augmentent en H3 (88,9 → 92,2) : le froid ne baisse
  pas (6,3 → 6,7). Même cause probable que le point 2.
- Les cas du guide sont décrits sommairement (« conformes RT 2012 », sans géométrie) : ces écarts sont des signaux,
  pas des mesures. Ils ne sont pas testés.
