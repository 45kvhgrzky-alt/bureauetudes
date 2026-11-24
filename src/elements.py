"""Éléments du projet : poteaux, paramètres du bâtiment et des matériaux.

Ce module contient les classes de données et le chargement/validation des
fichiers JSON (séance 4). Toute donnée invalide lève une ``ProjetError``
avec un message lisible : le programme ne plante jamais sur une saisie.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

TYPES_POTEAU = ("angle", "rive", "central")


class ProjetError(Exception):
    """Erreur de donnée ou de fichier du projet."""


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def _nombre(valeur, nom: str, *, strict: bool = True) -> float:
    """Valide un nombre réel (strictement positif par défaut)."""
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ProjetError(f"« {nom} » doit être un nombre (reçu : {valeur!r}).")
    if strict and valeur <= 0:
        raise ProjetError(f"« {nom} » doit être strictement positif (reçu : {valeur}).")
    if not strict and valeur < 0:
        raise ProjetError(f"« {nom} » ne peut pas être négatif (reçu : {valeur}).")
    return float(valeur)


def _entier(valeur, nom: str) -> int:
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur <= 0:
        raise ProjetError(f"« {nom} » doit être un entier strictement positif (reçu : {valeur!r}).")
    return valeur


def _lire_json(chemin) -> dict:
    chemin = Path(chemin)
    try:
        with chemin.open(encoding="utf-8") as f:
            donnees = json.load(f)
    except FileNotFoundError:
        raise ProjetError(f"Fichier introuvable : {chemin}") from None
    except json.JSONDecodeError as exc:
        raise ProjetError(f"JSON invalide dans {chemin} (ligne {exc.lineno}) : {exc.msg}") from None
    except OSError as exc:
        raise ProjetError(f"Lecture impossible de {chemin} : {exc}") from None
    if not isinstance(donnees, dict):
        raise ProjetError(f"{chemin} doit contenir un objet JSON à la racine.")
    return donnees


def _cle(dico: dict, *chemin: str):
    """Accède à une clé imbriquée en signalant précisément ce qui manque."""
    courant = dico
    for i, k in enumerate(chemin):
        if not isinstance(courant, dict) or k not in courant:
            raise ProjetError(f"Clé manquante : « {'.'.join(chemin[: i + 1])} ».")
        courant = courant[k]
    return courant


# --------------------------------------------------------------------------
# Classes de données
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Poteau:
    """Un poteau avec sa surface d'influence (m²)."""

    ident: str
    type: str
    surface_influence: float

    def __post_init__(self):
        if not self.ident or not isinstance(self.ident, str):
            raise ProjetError("Un poteau doit avoir un identifiant non vide.")
        if self.type not in TYPES_POTEAU:
            raise ProjetError(
                f"Poteau {self.ident} : type « {self.type} » inconnu "
                f"(attendu : {', '.join(TYPES_POTEAU)})."
            )
        _nombre(self.surface_influence, f"surface d'influence de {self.ident}")


@dataclass
class Projet:
    """Données du bâtiment (séances 1 à 3)."""

    nom: str
    niveaux: int
    hauteur_etage: float          # m
    g_surfacique: float           # kN/m² par niveau
    q_surfacique: float           # kN/m² par niveau
    poids_propre_forfait: float   # kN par poteau (poteau + poutres, forfait)
    contrainte_sol: float         # kPa
    profondeur_fondation: float   # m
    poteaux: list[Poteau] = field(default_factory=list)

    @property
    def hauteur_totale(self) -> float:
        return self.niveaux * self.hauteur_etage


@dataclass
class Materiaux:
    """Paramètres des matériaux et hypothèses de calcul (séance 4)."""

    densite_beton: float          # kN/m³
    contrainte_beton: float       # MPa
    epaisseur_semelle: float      # m
    cote_poteau_min: float        # cm
    pas_arrondi_semelle: float    # m
    ratio_acier_poteau: float     # kg/m³
    ratio_acier_semelle: float    # kg/m³
    surlargeur_fouille: float     # m
    gamma_g: float
    gamma_q: float
    tva: float


# --------------------------------------------------------------------------
# Chargement
# --------------------------------------------------------------------------
def charger_projet(chemin) -> Projet:
    """Charge et valide ``projet.json``."""
    d = _lire_json(chemin)
    brut = _cle(d, "poteaux")
    if not isinstance(brut, list) or not brut:
        raise ProjetError("« poteaux » doit être une liste non vide.")
    poteaux = []
    for i, p in enumerate(brut, start=1):
        if not isinstance(p, dict):
            raise ProjetError(f"Poteau n°{i} : objet JSON attendu.")
        poteaux.append(
            Poteau(
                ident=_cle(p, "id"),
                type=_cle(p, "type"),
                surface_influence=_nombre(_cle(p, "surface_influence_m2"), f"surface du poteau n°{i}"),
            )
        )
    idents = [p.ident for p in poteaux]
    doublons = {i for i in idents if idents.count(i) > 1}
    if doublons:
        raise ProjetError(f"Identifiants de poteaux en double : {', '.join(sorted(doublons))}.")
    return Projet(
        nom=str(_cle(d, "nom")),
        niveaux=_entier(_cle(d, "niveaux"), "niveaux"),
        hauteur_etage=_nombre(_cle(d, "hauteur_etage_m"), "hauteur_etage_m"),
        g_surfacique=_nombre(_cle(d, "charge_permanente_kn_m2"), "charge_permanente_kn_m2"),
        q_surfacique=_nombre(_cle(d, "charge_exploitation_kn_m2"), "charge_exploitation_kn_m2"),
        poids_propre_forfait=_nombre(_cle(d, "poids_propre_forfait_kn"), "poids_propre_forfait_kn", strict=False),
        contrainte_sol=_nombre(_cle(d, "contrainte_sol_kpa"), "contrainte_sol_kpa"),
        profondeur_fondation=_nombre(_cle(d, "profondeur_fondation_m"), "profondeur_fondation_m"),
        poteaux=poteaux,
    )


def charger_materiaux(chemin) -> Materiaux:
    """Charge et valide ``materiaux.json``."""
    d = _lire_json(chemin)
    n = lambda *c: _nombre(_cle(d, *c), ".".join(c))  # noqa: E731
    return Materiaux(
        densite_beton=n("beton", "densite_kn_m3"),
        contrainte_beton=n("beton", "contrainte_calcul_mpa"),
        epaisseur_semelle=n("beton", "epaisseur_semelle_m"),
        cote_poteau_min=n("poteau", "cote_minimal_cm"),
        pas_arrondi_semelle=n("semelle", "pas_arrondi_m"),
        ratio_acier_poteau=n("acier", "ratio_poteau_kg_m3"),
        ratio_acier_semelle=n("acier", "ratio_semelle_kg_m3"),
        surlargeur_fouille=_nombre(_cle(d, "fouille", "surlargeur_m"), "fouille.surlargeur_m", strict=False),
        gamma_g=n("coefficients", "gamma_g"),
        gamma_q=n("coefficients", "gamma_q"),
        tva=_nombre(_cle(d, "tva"), "tva", strict=False),
    )


def generer_grille(nx: int, ny: int, portee_x: float, portee_y: float) -> list[Poteau]:
    """Génère les poteaux d'une trame régulière (nx × ny travées).

    La surface d'influence d'un poteau est le produit des largeurs
    d'influence : une demi-portée sur un bord, une portée entière à l'intérieur.
    """
    _entier(nx, "nombre de travées en x")
    _entier(ny, "nombre de travées en y")
    _nombre(portee_x, "portée en x")
    _nombre(portee_y, "portée en y")

    def largeur(i: int, n: int, portee: float) -> float:
        return portee / 2 if i in (0, n) else portee

    poteaux = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            bords = (i in (0, nx)) + (j in (0, ny))
            type_ = {2: "angle", 1: "rive", 0: "central"}[bords]
            surface = largeur(i, nx, portee_x) * largeur(j, ny, portee_y)
            poteaux.append(Poteau(f"P{j * (nx + 1) + i + 1}", type_, surface))
    return poteaux
