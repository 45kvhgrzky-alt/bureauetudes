# Bureau d'études – cahier des charges et prédimensionnement

Projet 1 – Séance 6 (Institut Ivoirien de Technologie). Application console en Python
qui réutilise les séances 1 à 5 : chargement du projet (JSON), métré, descente de charges,
prédimensionnement des poteaux et des semelles, devis (bordereau CSV) et export d'un rapport.

## Lancer le programme

Python 3.9 ou plus récent. Aucune dépendance pour exécuter (bibliothèque standard uniquement).

```bash
python src/main.py          # menu interactif
python src/main.py --demo   # exécute tout le flux et écrit sortie/rapport.md
```

Sous Windows, utilisez `python` ou `py` selon votre installation.

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```

Les tests vérifient les valeurs de contrôle du sujet (voir ci-dessous) et la gestion des erreurs.

## Menu

| # | Fonctionnalité | Module principal |
|---|---|---|
| 1 | Saisir ou charger le projet | `elements.py` (JSON, validation) |
| 2 | Calculer le métré | `devis.py` |
| 3 | Descente de charges | `charges.py` |
| 4 | Prédimensionner poteaux et semelles | `predimensionnement.py` |
| 5 | Générer le devis | `devis.py` + `donnees/bordereau.csv` |
| 6 | Exporter un rapport | `devis.py` → `sortie/rapport.md` |

Les options 2 à 6 déclenchent automatiquement les étapes dont elles dépendent.

## Arborescence

```
bureau-etudes/
├── README.md
├── requirements.txt
├── .gitignore
├── donnees/
│   ├── projet.json        # bâtiment, charges, sol, poteaux
│   ├── materiaux.json     # béton, acier, coefficients, TVA
│   └── bordereau.csv      # prix unitaires (FCFA)
├── src/
│   ├── elements.py        # classes + chargement/validation
│   ├── charges.py         # descente de charges
│   ├── predimensionnement.py
│   ├── devis.py           # métré, devis, rapport
│   └── main.py            # menu console
└── tests/
    ├── conftest.py
    ├── test_charges.py
    └── test_devis.py
```

## Formules

- Descente de charges : G = S·g·n + forfait ; Q = S·q·n ; N_ELU = 1,35·G + 1,5·Q ; N_ELS = G + Q
- Poteau : A_min = N_ELU / σ_béton (10 MPa) ; côté = √A_min arrondi au cm supérieur ; minimum 20 cm
- Semelle : (G + Q + 12,5·B²) / B² ≤ 200 kPa, soit B ≥ √((G + Q) / 187,5), arrondi aux 5 cm supérieurs

## Résultats de contrôle (reproduits par les tests)

| Poteau | N_ELU (kN) | A_min (m²) | Côté (cm) | G+Q (kN) | B min (m) | B retenu (m) |
|---|---:|---:|---|---:|---:|---:|
| Angle | 168,4 | 0,017 | 13 → 20 | 122,1 | 0,81 | 0,85 |
| Rive | 317,8 | 0,032 | 18 → 20 | 230,1 | 1,11 | 1,15 |
| Central | 616,6 | 0,062 | 25 | 446,1 | 1,54 | 1,55 |

## Hypothèses du jeu de données

Les données des séances 1 à 5 de la classe n'étant pas incluses dans ce dépôt, `donnees/projet.json`
a été calibré pour retrouver les valeurs de contrôle : bâtiment R+3 (4 niveaux de 3 m), trame
2 × 2 travées de 4 m (surfaces d'influence 4 / 8 / 16 m²), g = 5,25 kN/m², q = 1,5 kN/m² par niveau,
forfait de 14,1 kN par poteau (poteau + poutres). Remplacez ces valeurs par celles de votre
cours si elles diffèrent. Les prix du bordereau sont indicatifs.

## Gestion des erreurs

Fichier absent ou JSON invalide, clé manquante, valeur négative ou non numérique, identifiants en
double, bordereau mal formé, sol trop faible : chaque cas lève une `ProjetError` avec un message
clair, affiché par le menu sans interrompre le programme. Les saisies du menu sont redemandées
tant qu'elles sont invalides.

## Organisation Git (équipe)

Un module par membre, au moins 5 commits chacun, un travail par branche et une pull request
relue par un coéquipier avant fusion dans `main`.

| Membre | Module | Branche |
|---|---|---|
| 1 | `elements.py` | `feature/elements` |
| 2 | `charges.py` + `tests/test_charges.py` | `feature/charges` |
| 3 | `predimensionnement.py` | `feature/predimensionnement` |
| 4 | `devis.py` + `donnees/bordereau.csv` | `feature/devis` |
| 5 | `main.py` + README | `feature/menu` |

Exemple de commits : `feat(charges): ajoute la descente de charges d'un poteau`,
`test(charges): valeurs de contrôle ELU`, `fix(elements): refuse les surfaces négatives`.

## Plan de la présentation orale (5 minutes)

1. Contexte et objectif (30 s)
2. Démo du menu : chargement, descente de charges, prédimensionnement, devis (2 min)
3. Validation par les valeurs de contrôle et tests (1 min)
4. Gestion des erreurs (30 s)
5. Organisation Git et répartition des modules (1 min)
