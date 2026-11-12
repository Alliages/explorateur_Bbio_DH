"""Garde-fous du dépôt : aucun RSEE ni classeur de référence publié, version cohérente, hypothèses sourcées."""

import re
import subprocess

import pytest

from config.reglages import RACINE, lire_version
from moteur.hypotheses import hyp, lire_hypotheses

# Fichiers qui ne doivent jamais être suivis par git
MOTIFS_INTERDITS = (re.compile(r"rsee", re.IGNORECASE),          # études RE2020 : données de projets réels
                    re.compile(r"^_rsee/|^_references/"),         # dossiers locaux
                    re.compile(r"\.xlsx?$", re.IGNORECASE))       # classeurs officiels (voir README)


def fichiers_suivis():
    try:
        sortie = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("dépôt git indisponible")
    return sortie.stdout.splitlines()


def test_aucun_rsee_ni_classeur_dans_le_depot():
    interdits = [f for f in fichiers_suivis() if any(motif.search(f) for motif in MOTIFS_INTERDITS)]
    assert interdits == [], f"Fichiers à retirer du dépôt : {interdits}"


def test_version_et_journal():
    version = lire_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    with open(f"{RACINE}/CHANGELOG.md", encoding="utf-8") as f:
        assert f"## {version}" in f.read(), "la version en cours manque dans CHANGELOG.md"


def test_hypotheses_sourcees():
    table = lire_hypotheses()
    assert len(table) >= 10
    for cle, ligne in table.items():
        assert ligne["source"].strip(), f"hypothèse sans source : {cle}"
        assert ligne["unite"].strip(), f"hypothèse sans unité : {cle}"
    with pytest.raises(KeyError):
        hyp("inconnue")
