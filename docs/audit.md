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
    gardées dans `Reference.baies` pour la 0.8.12.
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
67. **Pas d'entrées d'air en mode Bbio** : la ventilation conventionnelle du Bbio est une double flux (fiche 6.1),
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
