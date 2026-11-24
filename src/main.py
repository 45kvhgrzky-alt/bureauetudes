#!/usr/bin/env python3
"""Bureau d'études – menu console réutilisant les séances 1 à 5.

Usage :
    python src/main.py            # menu interactif
    python src/main.py --demo     # exécute tout le flux sans interaction
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from charges import descente_projet
from devis import (calculer_metre, charger_bordereau, exporter_rapport,
                   generer_devis, texte_devis)
from elements import (Projet, ProjetError, charger_materiaux, charger_projet,
                      generer_grille)
from predimensionnement import predim_projet

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "donnees"
SORTIE = RACINE / "sortie"

MENU = """
========== BUREAU D'ÉTUDES ==========
 1. Saisir ou charger le projet
 2. Calculer le métré
 3. Descente de charges
 4. Prédimensionner poteaux et semelles
 5. Générer le devis
 6. Exporter un rapport
 0. Quitter
"""


class Session:
    """État courant du programme : données chargées et résultats calculés."""

    def __init__(self, chemin_projet: Path):
        self.mat = charger_materiaux(DONNEES / "materiaux.json")
        self.bordereau = charger_bordereau(DONNEES / "bordereau.csv")
        self.projet: Projet | None = None
        self.charges = None
        self.dimensions = None
        self.metre = None
        self.devis = None
        self.chemin_projet = chemin_projet

    # -- étapes (chacune déclenche les précédentes si besoin) -------------
    def exiger_projet(self) -> Projet:
        if self.projet is None:
            raise ProjetError("Aucun projet chargé : choisissez d'abord l'option 1.")
        return self.projet

    def definir_projet(self, projet: Projet) -> None:
        self.projet = projet
        self.charges = self.dimensions = self.metre = self.devis = None

    def calculer_charges(self):
        projet = self.exiger_projet()
        self.charges = descente_projet(projet, self.mat)
        return self.charges

    def calculer_dimensions(self):
        projet = self.exiger_projet()
        if self.charges is None:
            self.calculer_charges()
        self.dimensions = predim_projet(self.charges, projet.contrainte_sol, self.mat)
        return self.dimensions

    def calculer_metre(self):
        if self.dimensions is None:
            self.calculer_dimensions()
        self.metre = calculer_metre(self.projet, self.mat, self.dimensions)
        return self.metre

    def calculer_devis(self):
        if self.metre is None:
            self.calculer_metre()
        self.devis = generer_devis(self.metre, self.bordereau, self.mat.tva)
        return self.devis


# -- affichages --------------------------------------------------------------
def afficher_charges(s: Session) -> None:
    print(f"\n{'Poteau':<7}{'Type':<9}{'G (kN)':>10}{'Q (kN)':>10}{'N_ELU (kN)':>12}{'G+Q (kN)':>11}")
    for r in s.charges:
        print(f"{r.poteau.ident:<7}{r.poteau.type:<9}{r.g:>10.1f}{r.q:>10.1f}{r.n_elu:>12.1f}{r.n_els:>11.1f}")


def afficher_dimensions(s: Session) -> None:
    print(f"\n{'Poteau':<7}{'Type':<9}{'N_ELU':>9}{'A_min (m²)':>12}{'Côté (cm)':>11}{'G+Q':>9}{'B min (m)':>11}{'B retenu':>10}")
    for r in s.charges:
        dp, ds = s.dimensions[r.poteau.ident]
        print(f"{r.poteau.ident:<7}{r.poteau.type:<9}{r.n_elu:>9.1f}{dp.a_min:>12.3f}"
              f"{dp.cote_calcule:>6g} → {dp.cote_retenu:<3g}{r.n_els:>9.1f}"
              f"{ds.cote_minimal:>11.2f}{ds.cote_retenu:>10.2f}")


def afficher_metre(s: Session) -> None:
    print("\nMÉTRÉ")
    for cle, val in s.metre.items():
        print(f"  {cle.replace('_', ' '):<22}{val:>12.2f}")


# -- saisie ------------------------------------------------------------------
def demander(question: str, convertir, defaut=None, positif=True):
    """Pose une question jusqu'à obtenir une valeur valide."""
    while True:
        suffixe = f" [{defaut}]" if defaut is not None else ""
        brut = input(f"{question}{suffixe} : ").strip()
        if not brut and defaut is not None:
            return defaut
        try:
            val = convertir(brut.replace(",", "."))
        except ValueError:
            print("  ✗ Valeur invalide, réessayez.")
            continue
        if positif and val <= 0:
            print("  ✗ La valeur doit être strictement positive.")
            continue
        return val


def saisir_projet() -> Projet:
    print("\nSaisie d'un projet (trame régulière). Entrée = valeur par défaut.")
    nom = input("Nom du projet [Projet saisi] : ").strip() or "Projet saisi"
    niveaux = demander("Nombre de niveaux", int, 4)
    hauteur = demander("Hauteur d'étage (m)", float, 3.0)
    g = demander("Charge permanente (kN/m² par niveau)", float, 5.25)
    q = demander("Charge d'exploitation (kN/m² par niveau)", float, 1.5)
    forfait = demander("Poids propre forfaitaire par poteau (kN)", float, 14.1, positif=False)
    sol = demander("Contrainte admissible du sol (kPa)", float, 200.0)
    prof = demander("Profondeur de fondation (m)", float, 1.5)
    nx = demander("Nombre de travées en x", int, 2)
    ny = demander("Nombre de travées en y", int, 2)
    px = demander("Portée en x (m)", float, 4.0)
    py = demander("Portée en y (m)", float, 4.0)
    return Projet(nom, niveaux, hauteur, g, q, forfait, sol, prof, generer_grille(nx, ny, px, py))


def option_projet(s: Session) -> None:
    choix = input("Charger donnees/projet.json (c) ou saisir un nouveau projet (s) ? [c] : ").strip().lower()
    if choix == "s":
        s.definir_projet(saisir_projet())
    else:
        s.definir_projet(charger_projet(s.chemin_projet))
    print(f"✓ Projet « {s.projet.nom} » : {len(s.projet.poteaux)} poteaux, {s.projet.niveaux} niveaux.")


def option_rapport(s: Session) -> None:
    s.calculer_devis()
    chemin = exporter_rapport(SORTIE / "rapport.md", s.projet, s.charges, s.dimensions,
                              s.metre, s.devis, s.mat.tva)
    print(f"✓ Rapport écrit : {chemin}")


def executer(s: Session, choix: str) -> None:
    if choix == "1":
        option_projet(s)
    elif choix == "2":
        s.exiger_projet(); s.calculer_metre(); afficher_metre(s)
    elif choix == "3":
        s.exiger_projet(); s.calculer_charges(); afficher_charges(s)
    elif choix == "4":
        s.exiger_projet(); s.calculer_dimensions(); afficher_dimensions(s)
    elif choix == "5":
        s.exiger_projet(); s.calculer_devis(); print("\n" + texte_devis(s.devis, s.mat.tva))
    elif choix == "6":
        s.exiger_projet(); option_rapport(s)
    else:
        print("Choix inconnu : entrez un chiffre de 0 à 6.")


def boucle(s: Session) -> int:
    while True:
        print(MENU)
        try:
            choix = input("Votre choix : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            return 0
        if choix == "0":
            print("Au revoir.")
            return 0
        try:
            executer(s, choix)
        except ProjetError as exc:
            print(f"✗ {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nOpération annulée.")


def demo(s: Session) -> int:
    s.definir_projet(charger_projet(s.chemin_projet))
    print(f"Projet : {s.projet.nom}")
    s.calculer_devis()
    afficher_charges(s); afficher_dimensions(s); afficher_metre(s)
    print("\n" + texte_devis(s.devis, s.mat.tva))
    option_rapport(s)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bureau d'études – cahier des charges et prédimensionnement")
    parser.add_argument("--projet", type=Path, default=DONNEES / "projet.json", help="fichier projet JSON")
    parser.add_argument("--demo", action="store_true", help="exécute le flux complet sans menu")
    args = parser.parse_args(argv)
    try:
        session = Session(args.projet)
        return demo(session) if args.demo else boucle(session)
    except ProjetError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
