"""Descente de charges (séance 3).

Pour chaque poteau, on cumule les charges des niveaux supportés :

    G = S × g × n_niveaux + forfait_poids_propre
    Q = S × q × n_niveaux
    N_ELU = γG·G + γQ·Q        (1,35 G + 1,5 Q)
    N_ELS = G + Q              (charge « en pied » servant aux semelles)
"""
from __future__ import annotations

from dataclasses import dataclass

from elements import Materiaux, Poteau, Projet, ProjetError


@dataclass(frozen=True)
class ResultatCharges:
    poteau: Poteau
    g: float        # kN
    q: float        # kN
    n_elu: float    # kN
    n_els: float    # kN (G + Q)


def descente_charges(poteau: Poteau, projet: Projet, mat: Materiaux) -> ResultatCharges:
    """Calcule G, Q, N_ELU et N_ELS en pied d'un poteau."""
    if poteau.surface_influence <= 0:
        raise ProjetError(f"Poteau {poteau.ident} : surface d'influence invalide.")
    g = poteau.surface_influence * projet.g_surfacique * projet.niveaux + projet.poids_propre_forfait
    q = poteau.surface_influence * projet.q_surfacique * projet.niveaux
    return ResultatCharges(
        poteau=poteau,
        g=g,
        q=q,
        n_elu=mat.gamma_g * g + mat.gamma_q * q,
        n_els=g + q,
    )


def descente_projet(projet: Projet, mat: Materiaux) -> list[ResultatCharges]:
    """Descente de charges de tous les poteaux du projet."""
    return [descente_charges(p, projet, mat) for p in projet.poteaux]
