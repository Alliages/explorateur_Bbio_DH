"""Sorties horaires d'un moteur Th-BCE : lecture (outils/lire_horaires.py) et écarts (outils/comparer_horaires.py).

Les vrais fichiers restent hors du dépôt : les tests écrivent de petits fichiers au même format.
"""

import numpy as np
import pytest

from outils import comparer_horaires as ch
from outils import lire_horaires as lh

ENTETE = [
    ["Cadenceur", "COMETH_Data_Sortie_Groupe:1", "COMETH_Data_Sortie_Groupe:1", "COMETH_Data_Sortie_Groupe:1",
     "COMETH_Data_Sortie_Groupe:1", "COMETH_Data_Sortie_Baie:3", "COMETH_Data_Sortie_Baie:4",
     "COMETH_Data_Sortie_Groupe:1", "COMETH_Data_Sortie_Groupe:1", ""],
    ["T_simul", "O_Temp_op_moy", "O_Relance", "O_Fs2", "O_Ftvc", "O_Rouv", "O_Rouv", "O_Einat", "O_Einat", ""],
    ["Pas de temps", "Température", "Relance", "Fs2", "Ftvc", "Ratio", "Ratio", "Einat", "Einat", ""],
    ["h", "°C", "-", "W", "W", "-", "-", "-", "-", ""],
]
LIGNES = [
    ["0", "19,5", "True", "10", "-2", "0", "0,5", "1", "2", ""],
    ["1", "20,25", "False", "20", "-4", "0,25", "0,75", "3", "4", ""],
    ["2", "21", "False", "0", "0", "1", "1", "5", "6", ""],
]


def ecrire(chemin, entete=ENTETE, lignes=LIGNES):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    texte = "\r\n".join(";".join(l) for l in entete + lignes) + "\r\n"
    chemin.write_bytes(texte.encode("utf-8-sig"))          # fins de ligne CRLF, comme le moteur
    return chemin


@pytest.fixture
def fichier(tmp_path, monkeypatch):
    monkeypatch.setattr(lh, "DOSSIER_CACHE", tmp_path / "cache")
    return ecrire(tmp_path / "calcul" / "Th_B_Bat_1_Zone_1_Groupe_1.csv")


def test_entete(fichier):
    e = lh.lire_entete(fichier)
    assert e["nom"].tolist() == ["T_simul", "O_Temp_op_moy", "O_Relance", "O_Fs2", "O_Ftvc", "O_Rouv", "O_Rouv:4",
                                 "O_Einat", "O_Einat#2"]
    assert e.loc[e["nom"] == "O_Rouv:4", ["type", "numero", "unite"]].values.tolist() == [["Baie", 4, "-"]]
    assert lh.noms_baies(e, "O_Rouv") == ["O_Rouv", "O_Rouv:4"]


def test_lecture_et_cache(fichier):
    t = lh.lire_colonnes(fichier, ["O_Temp_op_moy", "O_Relance"])
    assert t["O_Temp_op_moy"].tolist() == [19.5, 20.25, 21.0]
    assert t["O_Relance"].tolist() == [1, 0, 0]
    # Seconde lecture : les colonnes déjà lues viennent du cache, les nouvelles s'y ajoutent
    t = lh.lire_colonnes(fichier, ["O_Rouv:4", "O_Temp_op_moy"])
    assert t.columns.tolist() == ["O_Rouv:4", "O_Temp_op_moy"] and t["O_Rouv:4"].tolist() == [0.5, 0.75, 1.0]
    assert lh._chemin_cache(fichier).exists()
    with pytest.raises(KeyError, match="O_Inconnue"):
        lh.lire_colonnes(fichier, ["O_Inconnue"])


def test_fichiers_des_groupes(tmp_path):
    for nom in ("Th_B_Bat_1_Zone_2_Groupe_2.csv", "Th_B_Bat_1_Zone_1_Groupe_1.csv", "Th_DC_Bat_1_Zone_1_Groupe_1.csv",
                "Th_B_Impact_Ss_Apports_Sol_Bat_1_Zone_1_Groupe_1.csv", "Th_B_Bat_1_Zone_1.csv"):
        (tmp_path / nom).write_text("", encoding="utf-8")
    assert [f[:3] for f in lh.fichiers_groupes(tmp_path, "B")] == [(1, 1, 1), (1, 2, 2)]
    assert [f[3].name for f in lh.fichiers_groupes(tmp_path, "B", "Impact_Ss_Apports_Sol_")] == [
        "Th_B_Impact_Ss_Apports_Sol_Bat_1_Zone_1_Groupe_1.csv"]
    assert len(lh.fichiers_groupes(tmp_path, "DC")) == 1


def test_resultats_th_dc(tmp_path):
    tableau = [";;;;Degrés-heures d'inconfort  (°C.h); Nombre d'heures", ";Batiment1;;;", ";;Zone1;;",
               ";;;Groupe1;372,7;160;110;90;1250;", ";;Zone2;;", ";;;Groupe1;145,2;88;56;31;1250;", ";", ""]
    (tmp_path / "Resultats_Th_DC.csv").write_text("\n".join([";;;Mode de calcul;;Th_DC"] + tableau + tableau),
                                                  encoding="utf-8-sig")
    assert lh.lire_resultats_th_dc(tmp_path) == [(372.7, 160), (145.2, 88)]


def test_series_du_moteur(fichier):
    grandeurs = [ch.Grandeur("fs2_ftvc", "phi_sl", ("O_Fs2", "O_Ftvc"), True, 1.0, "L4"),
                 ch.Grandeur("ouverture", "rouv_moyen", ("baies:O_Rouv",), False, 0.05, "L3"),
                 ch.Grandeur("absente", "x", ("O_Absente",), False, 0.1, "L1")]
    series, absents = ch.series_moteur(fichier, grandeurs)
    assert series["fs2_ftvc"].tolist() == [8.0, 16.0, 0.0]          # somme des deux colonnes
    assert series["ouverture"].tolist() == [0.25, 0.5, 1.0]         # moyenne simple des baies
    assert "absente" not in series and absents == ["O_Absente"]


def test_ecarts_et_decalage():
    g = ch.Grandeur("besoin", "q_ch_wh", ("O_B_Ch_Horaire",), True, 10.0, "résultat")
    outil, moteur = np.array([1000.0, 2000.0, 3000.0]), np.array([1000.0, 2050.0, 2900.0])
    e = ch.ecarts(outil, moteur, g)
    assert e["outil"] == pytest.approx(6.0) and e["moteur"] == pytest.approx(5.95)          # kWh
    assert e["premiere_heure_au_dela"] == 1 and e["heures_au_dela"] == 2
    assert e["ecart_max"] == pytest.approx(100.0) and e["heure_ecart_max"] == 2
    temperature = np.sin(np.arange(200) / 7.0)
    assert ch.decalage_horaire(temperature[2:], temperature[:-2]) == 2
    assert ch.decalage_horaire(temperature, temperature) == 0


def test_etudes_connues():
    # Chaque étude nomme un dossier de sorties horaires et un RSET du même calcul
    for dossier, rset in ch.ETUDES.values():
        assert dossier.endswith("_scénario_final") and rset.endswith(".xml")
