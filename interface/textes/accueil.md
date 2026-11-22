# Bienvenue dans l'Explorateur Bbio / DH

La [[RE2020]] juge l'enveloppe d'un logement neuf sur deux indicateurs : le **Bbio**, qui note ses besoins d'énergie, et les **degrés-heures d'inconfort ([[DH]])**, qui notent sa chaleur en été. Une étude thermique les calcule sur le projet entier ; on lit le résultat, rarement ce qui le fait bouger.

Cet outil recalcule les deux, de façon approchée, sur une **boîte simple** : un logement ou un immeuble, quatre façades, une enveloppe. On change une saisie, on relance, on lit l'écart. Il s'adresse aux professionnels du bâtiment, sans besoin d'être thermicien.

## Comment s'en servir

1. **Partir d'un bâtiment**, dans le menu de gauche : le bâtiment de départ, son enveloppe (performante, moyenne ou faible, tirée d'études RE2020) et le calcul à lancer.
2. **Modifier la boîte** dans les volets : site, forme, baies, parois, air, confort d'été. Le dessin suit aussitôt. La bulle « ? » de chaque saisie l'explique.
3. **Calculer** (quelques secondes par calcul), puis lire les briques « Comprendre » : le phénomène, un graphique, l'équation, ses références et le code qui la calcule.
4. **Comparer** : « Garder comme référence », changer une saisie, recalculer. Les chiffres clés montrent aussi l'écart avec le calcul précédent.

<!-- bouton_explorer -->

## Trois notions pour lire les résultats

> **Le Bbio** note le bâtiment avant tout équipement : ce qu'il lui faut de chaleur, de froid et de lumière artificielle sur une année moyenne. Chaque besoin, en kWh par m², est pondéré puis additionné : $B_{bio} = 2 \times B_{ch} + 2 \times B_{fr} + 5 \times B_{ecl}$. Il se compare à un Bbio max, modulé selon le climat, l'altitude, la taille des logements et le bruit. Voir [[Besoins (thermiques)]] et [[Bioclimatique]].

> **Les degrés-heures (DH)** mesurent à la fois combien de temps et de combien la [[Température opérative|température ressentie]] dépasse le seuil de confort, aux heures où le logement est occupé : 26 °C la nuit, jusqu'à 28 °C le jour quand il fait chaud depuis plusieurs jours ([[Confort adaptatif|confort adaptatif]]). Deux degrés de trop pendant 50 heures font 100 °C.h. Le calcul porte sur une année avec [[Canicule|canicule]], sans climatisation ; le maximum d'un logement collectif non climatisé, sans contrainte extérieure, est de 1 250 °C.h.

> **Une boîte, pas un projet.** L'outil applique la méthode de la RE2020 (Th-BCE 2020) à un seul volume, aux parois et aux baies moyennes. Il sert à comparer des variantes et à comprendre un ordre de grandeur, pas à vérifier un projet.

<h2 class="alerte">Limites</h2>

- **L'outil n'est pas une étude thermique** et n'a aucune valeur réglementaire.
- Sur 46 groupes de logements de 16 études RE2020 recalculées (dont plusieurs variantes d'un même bâtiment) : le Bbio est à ± 10 % de l'étude dans 30 groupes, avec un écart médian nul, mais le chauffage est parfois beaucoup trop fort (jusqu'à + 50 % environ) ; le DH est à ± 10 % dans 21 groupes sur 37, mais va de près de 40 % sous l'étude à près de 30 % au-dessus.
- Logement collectif seulement, un seul volume, sans masque lointain ni loggia.

<h2 class="liens">Liens utiles</h2>

- [Glossaire du confort dans le bâtiment](GLOSSAIRE) : les mots de l'inconfort d'été, expliqués
- [Météo et Chaleur](https://vulgarisateurdh.streamlit.app/) : les fichiers météo sous l'angle de l'inconfort d'été
- [Les 6 seuils de la RE2020](https://seuils-re2020.streamlit.app/)
- [Carte des zones climatiques RE2020](https://alliages.github.io/zones-climatiques-re2020/)
- [Code de l'outil](https://github.com/Alliages/explorateur_Bbio_DH)
