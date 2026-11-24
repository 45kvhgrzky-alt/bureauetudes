"""Prédimensionnement des poteaux et des semelles (séances 2 et 3).

Poteau   : A_min = N_ELU / σ_béton ; côté = √A_min arrondi au cm supérieur,
           avec un minimum constructif (20 cm).
Semelle  : (G + Q + p·B²) / B² ≤ σ_sol, avec p = poids du béton × épaisseur
           (12,5 kPa pour 25 kN/m³ × 0,5 m), soit B ≥ √((G+Q) / (σ_sol − p)).
           Pour σ_sol = 200 kPa : B ≥ √((G+Q) / 187,5).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from charges import ResultatCharges
from elements import Materiaux, ProjetError

EPS = 1e-9  # évite qu'un flottant du type 17.000000001 saute au cran supérieur


@dataclass(frozen=True)
class DimPoteau:
    a_min: float          # m², arrondi par excès à 0,001
    cote_calcule: float   # cm
    cote_retenu: float    # cm


@dataclass(frozen=True)
class DimSemelle:
    cote_minimal: float   # m, arrondi à 0,01
    cote_retenu: float    # m, arrondi par excès au pas (5 cm)


def predim_poteau(n_elu: float, mat: Materiaux) -> DimPoteau:
    """Section carrée minimale d'un poteau soumis à ``n_elu`` (kN)."""
    if n_elu <= 0:
        raise ProjetError(f"Effort normal invalide : {n_elu} kN.")
    sigma_kpa = mat.contrainte_beton * 1000.0
    aire = n_elu / sigma_kpa                                   # m²
    a_min = math.ceil(aire * 1000 - EPS) / 1000
    cote_calcule = math.ceil(math.sqrt(aire) * 100 - EPS)      # cm
    return DimPoteau(a_min, cote_calcule, max(cote_calcule, mat.cote_poteau_min))


def predim_semelle(g_plus_q: float, contrainte_sol: float, mat: Materiaux) -> DimSemelle:
    """Côté minimal B d'une semelle carrée sous G+Q (kN) pour σ_sol (kPa)."""
    if g_plus_q <= 0:
        raise ProjetError(f"Charge G+Q invalide : {g_plus_q} kN.")
    poids_propre = mat.densite_beton * mat.epaisseur_semelle   # kPa (12,5)
    portance_nette = contrainte_sol - poids_propre
    if portance_nette <= 0:
        raise ProjetError(
            f"Contrainte du sol ({contrainte_sol} kPa) insuffisante : le poids propre "
            f"de la semelle ({poids_propre} kPa) la consomme entièrement."
        )
    b = math.sqrt(g_plus_q / portance_nette)
    pas = mat.pas_arrondi_semelle
    retenu = round(math.ceil(b / pas - EPS) * pas, 2)
    return DimSemelle(round(b, 2), retenu)


def predim_projet(resultats: list[ResultatCharges], contrainte_sol: float, mat: Materiaux) -> dict:
    """Prédimensionne tous les poteaux et semelles. Clé = identifiant du poteau."""
    return {
        r.poteau.ident: (
            predim_poteau(r.n_elu, mat),
            predim_semelle(r.n_els, contrainte_sol, mat),
        )
        for r in resultats
    }
