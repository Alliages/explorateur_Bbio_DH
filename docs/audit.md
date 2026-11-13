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
