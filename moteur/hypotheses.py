"""
============================================================
 HYPOTHÈSES — constantes du moteur, avec leur source
============================================================
 Toutes les constantes physiques et réglementaires sont lues
 dans donnees/hypotheses.csv (cle ; valeur ; unite ; source ;
 commentaire). Le code ne contient aucune valeur « en dur ».

 Usage :
     from moteur.hypotheses import hyp
     gradient = hyp("gradient_te")
============================================================
"""

import csv
from functools import lru_cache

from config.reglages import CHEMIN_HYPOTHESES, DECIMALE_CSV, ENCODAGE_CSV, SEPARATEUR_CSV


@lru_cache(maxsize=1)
def lire_hypotheses():
    """Table complète des hypothèses : {cle: ligne du CSV}, la valeur étant convertie en nombre."""
    table = {}
    with open(CHEMIN_HYPOTHESES, encoding=ENCODAGE_CSV, newline="") as f:
        for ligne in csv.DictReader(f, delimiter=SEPARATEUR_CSV):
            if ligne["cle"] in table:
                raise ValueError(f"Hypothèse en double : {ligne['cle']}")
            ligne["valeur"] = float(ligne["valeur"].replace(DECIMALE_CSV, "."))
            table[ligne["cle"]] = ligne
    return table


def hyp(cle):
    """Valeur numérique d'une hypothèse ; erreur claire si la clé n'existe pas."""
    table = lire_hypotheses()
    if cle not in table:
        raise KeyError(f"Hypothèse inconnue : « {cle} » (voir donnees/hypotheses.csv)")
    return table[cle]["valeur"]
