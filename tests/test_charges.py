"""Valeurs de contrôle du sujet (séance 6, §6.3) : descente de charges,
prédimensionnement des poteaux et des semelles."""
from pathlib import Path

import pytest

from charges import descente_projet
from elements import (Materiaux, Poteau, ProjetError, charger_materiaux,
                      charger_projet, generer_grille)
from predimensionnement import predim_poteau, predim_projet, predim_semelle

DONNEES = Path(__file__).resolve().parent.parent / "donnees"


@pytest.fixture(scope="module")
def mat() -> Materiaux:
    return charger_materiaux(DONNEES / "materiaux.json")


@pytest.fixture(scope="module")
def projet():
    return charger_projet(DONNEES / "projet.json")


@pytest.fixture(scope="module")
def resultats(projet, mat):
    return {r.poteau.type: r for r in descente_projet(projet, mat)}


# type : (N_ELU, A_min, côté retenu cm, G+Q, B minimal, B retenu)
CONTROLE = {
    "angle":   (168.4, 0.017, 20, 122.1, 0.81, 0.85),
    "rive":    (317.8, 0.032, 20, 230.1, 1.11, 1.15),
    "central": (616.6, 0.062, 25, 446.1, 1.54, 1.55),
}


@pytest.mark.parametrize("type_", CONTROLE)
def test_descente_de_charges(resultats, type_):
    n_elu, _, _, g_plus_q, *_ = CONTROLE[type_]
    r = resultats[type_]
    assert round(r.n_elu, 1) == n_elu
    assert round(r.n_els, 1) == g_plus_q


@pytest.mark.parametrize("type_", CONTROLE)
def test_predimensionnement_poteau(resultats, mat, type_):
    _, a_min, cote, *_ = CONTROLE[type_]
    dim = predim_poteau(resultats[type_].n_elu, mat)
    assert dim.a_min == pytest.approx(a_min)
    assert dim.cote_retenu == cote


@pytest.mark.parametrize("type_", CONTROLE)
def test_predimensionnement_semelle(resultats, projet, mat, type_):
    *_, b_min, b_retenu = CONTROLE[type_]
    dim = predim_semelle(resultats[type_].n_els, projet.contrainte_sol, mat)
    assert dim.cote_minimal == pytest.approx(b_min)
    assert dim.cote_retenu == pytest.approx(b_retenu)


def test_cotes_poteaux_calcules(resultats, mat):
    """Colonne « côté retenu » du sujet : 13 → 20, 18 → 20, 25."""
    attendu = {"angle": 13, "rive": 18, "central": 25}
    for type_, cote in attendu.items():
        assert predim_poteau(resultats[type_].n_elu, mat).cote_calcule == cote


def test_la_semelle_respecte_la_contrainte_du_sol(resultats, projet, mat):
    """Vérifie (G+Q+12,5·B²)/B² ≤ 200 kPa avec le côté retenu."""
    for r in resultats.values():
        b = predim_semelle(r.n_els, projet.contrainte_sol, mat).cote_retenu
        assert (r.n_els + 12.5 * b * b) / (b * b) <= projet.contrainte_sol


def test_tous_les_poteaux_sont_dimensionnes(projet, mat):
    dims = predim_projet(descente_projet(projet, mat), projet.contrainte_sol, mat)
    assert len(dims) == 9


def test_effort_invalide(mat):
    with pytest.raises(ProjetError):
        predim_poteau(-5, mat)
    with pytest.raises(ProjetError):
        predim_semelle(0, 200, mat)


def test_sol_trop_faible(mat):
    with pytest.raises(ProjetError, match="insuffisante"):
        predim_semelle(100, 10, mat)


def test_grille_reproduit_les_surfaces_du_projet():
    grille = generer_grille(2, 2, 4.0, 4.0)
    surfaces = {p.type: p.surface_influence for p in grille}
    assert surfaces == {"angle": 4.0, "rive": 8.0, "central": 16.0}
    assert len(grille) == 9


def test_poteau_invalide():
    with pytest.raises(ProjetError):
        Poteau("P1", "inconnu", 4.0)
    with pytest.raises(ProjetError):
        Poteau("P1", "angle", -1.0)
