"""Métré, devis et rapport (séances 1, 2, 4 et 5)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from elements import Materiaux, Projet, ProjetError


@dataclass(frozen=True)
class Article:
    code: str
    designation: str
    unite: str
    prix_unitaire: float


@dataclass(frozen=True)
class LigneDevis:
    article: Article
    quantite: float

    @property
    def montant(self) -> float:
        return self.quantite * self.article.prix_unitaire


def charger_bordereau(chemin) -> dict[str, Article]:
    """Lit ``bordereau.csv`` (code, designation, unite, prix_unitaire)."""
    chemin = Path(chemin)
    attendues = {"code", "designation", "unite", "prix_unitaire"}
    try:
        with chemin.open(encoding="utf-8", newline="") as f:
            lecteur = csv.DictReader(f)
            if not lecteur.fieldnames or not attendues <= set(lecteur.fieldnames):
                raise ProjetError(f"Colonnes attendues dans {chemin.name} : {', '.join(sorted(attendues))}.")
            articles = {}
            for n, ligne in enumerate(lecteur, start=2):
                try:
                    prix = float(ligne["prix_unitaire"])
                except (TypeError, ValueError):
                    raise ProjetError(f"{chemin.name} ligne {n} : prix invalide « {ligne['prix_unitaire']} ».") from None
                if prix < 0:
                    raise ProjetError(f"{chemin.name} ligne {n} : prix négatif.")
                code = ligne["code"].strip()
                if code in articles:
                    raise ProjetError(f"{chemin.name} ligne {n} : code « {code} » en double.")
                articles[code] = Article(code, ligne["designation"].strip(), ligne["unite"].strip(), prix)
    except FileNotFoundError:
        raise ProjetError(f"Fichier introuvable : {chemin}") from None
    except OSError as exc:
        raise ProjetError(f"Lecture impossible de {chemin} : {exc}") from None
    if not articles:
        raise ProjetError(f"{chemin.name} ne contient aucun article.")
    return articles


def calculer_metre(projet: Projet, mat: Materiaux, dimensions: dict) -> dict[str, float]:
    """Quantités totales à partir des dimensions retenues.

    ``dimensions`` : {id_poteau: (DimPoteau, DimSemelle)}.
    """
    h_tot = projet.hauteur_totale
    h_s = mat.epaisseur_semelle
    m = dict.fromkeys(("fouilles_m3", "beton_poteaux_m3", "beton_semelles_m3",
                       "coffrage_m2", "acier_kg"), 0.0)
    for p in projet.poteaux:
        if p.ident not in dimensions:
            raise ProjetError(f"Dimensions manquantes pour le poteau {p.ident} : lancez le prédimensionnement.")
        dp, ds = dimensions[p.ident]
        c = dp.cote_retenu / 100.0
        b = ds.cote_retenu
        m["fouilles_m3"] += (b + mat.surlargeur_fouille) ** 2 * projet.profondeur_fondation
        v_pot, v_sem = c * c * h_tot, b * b * h_s
        m["beton_poteaux_m3"] += v_pot
        m["beton_semelles_m3"] += v_sem
        m["coffrage_m2"] += 4 * c * h_tot + 4 * b * h_s
        m["acier_kg"] += v_pot * mat.ratio_acier_poteau + v_sem * mat.ratio_acier_semelle
    return {k: round(v, 2) for k, v in m.items()}


def generer_devis(metre: dict[str, float], bordereau: dict[str, Article], tva: float) -> dict:
    """Applique le bordereau de prix au métré. Retourne lignes, HT, TVA, TTC."""
    association = {
        "TER01": metre["fouilles_m3"],
        "BET01": metre["beton_poteaux_m3"] + metre["beton_semelles_m3"],
        "ACI01": metre["acier_kg"],
        "COF01": metre["coffrage_m2"],
    }
    manquants = [c for c in association if c not in bordereau]
    if manquants:
        raise ProjetError(f"Articles absents du bordereau : {', '.join(manquants)}.")
    lignes = [LigneDevis(bordereau[c], round(q, 2)) for c, q in association.items()]
    total_ht = round(sum(l.montant for l in lignes))
    montant_tva = round(total_ht * tva)
    return {"lignes": lignes, "total_ht": total_ht, "tva": montant_tva, "total_ttc": total_ht + montant_tva}


def fcfa(valeur: float) -> str:
    """Formate un montant : 1234567 -> « 1 234 567 FCFA »."""
    return f"{valeur:,.0f}".replace(",", " ") + " FCFA"


def texte_devis(devis: dict, taux_tva: float) -> str:
    lignes = ["DEVIS ESTIMATIF", "-" * 78,
              f"{'Code':<6}{'Désignation':<44}{'Qté':>8} {'U':<3}{'Montant':>15}"]
    for l in devis["lignes"]:
        a = l.article
        lignes.append(f"{a.code:<6}{a.designation[:43]:<44}{l.quantite:>8.2f} {a.unite:<3}{fcfa(l.montant):>15}")
    lignes += ["-" * 78,
               f"{'Total HT':<62}{fcfa(devis['total_ht']):>16}",
               f"{f'TVA ({taux_tva * 100:.0f} %)':<62}{fcfa(devis['tva']):>16}",
               f"{'Total TTC':<62}{fcfa(devis['total_ttc']):>16}"]
    return "\n".join(lignes)


def exporter_rapport(chemin, projet: Projet, resultats, dimensions: dict,
                     metre: dict, devis: dict, taux_tva: float) -> Path:
    """Écrit le rapport complet au format Markdown."""
    chemin = Path(chemin)
    out = [f"# Rapport – {projet.nom}", "",
           f"Bâtiment R+{projet.niveaux - 1} ({projet.niveaux} niveaux, "
           f"{projet.hauteur_etage} m par niveau), sol à {projet.contrainte_sol:g} kPa.", "",
           "## Descente de charges et prédimensionnement", "",
           "| Poteau | Type | G (kN) | Q (kN) | N_ELU (kN) | A_min (m²) | Côté retenu (cm) | G+Q (kN) | B retenu (m) |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in resultats:
        dp, ds = dimensions[r.poteau.ident]
        out.append(f"| {r.poteau.ident} | {r.poteau.type} | {r.g:.1f} | {r.q:.1f} | {r.n_elu:.1f} | "
                   f"{dp.a_min:.3f} | {dp.cote_retenu:g} | {r.n_els:.1f} | {ds.cote_retenu:.2f} |")
    out += ["", "## Métré", ""]
    out += [f"- {k.replace('_', ' ')} : {v}" for k, v in metre.items()]
    out += ["", "## Devis", "", "```", texte_devis(devis, taux_tva), "```", ""]
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("\n".join(out), encoding="utf-8")
    except OSError as exc:
        raise ProjetError(f"Écriture impossible de {chemin} : {exc}") from None
    return chemin
