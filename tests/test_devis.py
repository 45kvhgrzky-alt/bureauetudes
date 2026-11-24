"""Tests du métré, du devis et de la robustesse du chargement."""
import json
from pathlib import Path

import pytest

from charges import descente_projet
from devis import calculer_metre, charger_bordereau, fcfa, generer_devis
from elements import ProjetError, charger_materiaux, charger_projet
from predimensionnement import predim_projet

DONNEES = Path(__file__).resolve().parent.parent / "donnees"


@pytest.fixture(scope="module")
def chaine():
    mat = charger_materiaux(DONNEES / "materiaux.json")
    projet = charger_projet(DONNEES / "projet.json")
    dims = predim_projet(descente_projet(projet, mat), projet.contrainte_sol, mat)
    metre = calculer_metre(projet, mat, dims)
    return mat, projet, dims, metre


def test_metre_beton(chaine):
    mat, projet, dims, metre = chaine
    # 4 angles 20 cm / 0,85 m ; 4 rives 20 cm / 1,15 m ; 1 central 25 cm / 1,55 m ; H = 12 m
    poteaux = (8 * 0.2 ** 2 + 0.25 ** 2) * 12
    semelles = (4 * 0.85 ** 2 + 4 * 1.15 ** 2 + 1.55 ** 2) * 0.5
    assert metre["beton_poteaux_m3"] == pytest.approx(poteaux, abs=0.01)
    assert metre["beton_semelles_m3"] == pytest.approx(semelles, abs=0.01)


def test_devis_coherent(chaine):
    mat, _, _, metre = chaine
    devis = generer_devis(metre, charger_bordereau(DONNEES / "bordereau.csv"), mat.tva)
    assert devis["total_ht"] == round(sum(l.montant for l in devis["lignes"]))
    assert devis["total_ttc"] == devis["total_ht"] + devis["tva"]
    assert devis["tva"] == round(devis["total_ht"] * 0.18)


def test_format_fcfa():
    assert fcfa(1234567) == "1 234 567 FCFA"


def test_bordereau_introuvable(tmp_path):
    with pytest.raises(ProjetError, match="introuvable"):
        charger_bordereau(tmp_path / "absent.csv")


def test_bordereau_prix_invalide(tmp_path):
    f = tmp_path / "b.csv"
    f.write_text("code,designation,unite,prix_unitaire\nTER01,Fouilles,m3,abc\n", encoding="utf-8")
    with pytest.raises(ProjetError, match="prix invalide"):
        charger_bordereau(f)


def test_bordereau_colonne_manquante(tmp_path):
    f = tmp_path / "b.csv"
    f.write_text("code,designation\nTER01,Fouilles\n", encoding="utf-8")
    with pytest.raises(ProjetError, match="Colonnes attendues"):
        charger_bordereau(f)


def test_json_invalide(tmp_path):
    f = tmp_path / "p.json"
    f.write_text("{pas du json", encoding="utf-8")
    with pytest.raises(ProjetError, match="JSON invalide"):
        charger_projet(f)


def test_projet_cle_manquante(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"nom": "x", "poteaux": [{"id": "P1", "type": "angle", "surface_influence_m2": 4}]}),
                 encoding="utf-8")
    with pytest.raises(ProjetError, match="Clé manquante"):
        charger_projet(f)


def test_projet_introuvable(tmp_path):
    with pytest.raises(ProjetError, match="introuvable"):
        charger_projet(tmp_path / "rien.json")


def test_poteaux_en_double(tmp_path):
    brut = json.loads((DONNEES / "projet.json").read_text(encoding="utf-8"))
    brut["poteaux"].append(dict(brut["poteaux"][0]))
    f = tmp_path / "p.json"
    f.write_text(json.dumps(brut), encoding="utf-8")
    with pytest.raises(ProjetError, match="double"):
        charger_projet(f)


def test_metre_sans_predimensionnement(chaine):
    mat, projet, _, _ = chaine
    with pytest.raises(ProjetError, match="Dimensions manquantes"):
        calculer_metre(projet, mat, {})
