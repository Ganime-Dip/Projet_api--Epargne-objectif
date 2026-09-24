# API REST — Épargne à objectif

API de gestion de tirelires d'épargne pour LICELI Technologies. Un client authentifié
crée des tirelires liées à un objectif d'épargne, y effectue des dépôts et des retraits,
et consulte l'historique de ses opérations.

## Prérequis
- Python 3.13
- pip

## Installation

\`\`\`bash
git clone <url_du_depot>
cd Projet_API
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
\`\`\`

## Démarrage

\`\`\`bash
python manage.py test tirelires --verbosity 2
\`\`\`

Affiche chaque test exécuté avec son résultat (25 tests, couvrant RG1 à RG6 et les 7 cas d'utilisation).

L'API est disponible sur http://127.0.0.1:8000/api/

## Lancer les tests

\`\`\`bash
python manage.py test tirelires
\`\`\`

## Authentification

Toutes les routes, sauf la connexion, exigent un token dans l'en-tête :

\`\`\`
Authorization: Token <votre_token>
\`\`\`

Un client (`Client`) doit exister en base, lié à un `User` Django, pour pouvoir utiliser
l'API au-delà de la connexion (créable via l'admin `/admin/` ou le shell Django).

## Points d'entrée de l'API

### Connexion

\`\`\`bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\\"username\\": \\"alice\\", \\"password\\": \\"motdepasse\\"}"
\`\`\`
Réponse (200) : `{"token": "cae129d8..."}`
Réponse (400) : `{"erreur": "Identifiants invalides."}`

### Créer une tirelire

\`\`\`bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\\"libelle\\": \\"Voyage\\", \\"montant_objectif\\": 500000, \\"date_echeance\\": \\"2027-01-01\\"}"
\`\`\`
Réponse (201) : la tirelire créée. Réponse (400) si montant objectif ≤ 0 ou échéance passée.

### Lister mes tirelires

\`\`\`bash
curl http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>"
\`\`\`
Réponse (200) : liste des tirelires du client connecté uniquement.

### Consulter une tirelire précise

\`\`\`bash
curl http://127.0.0.1:8000/api/tirelires/1/ -H "Authorization: Token <token>"
\`\`\`
Réponse (200) : détail. Réponse (403) si la tirelire appartient à un autre client.
Réponse (404) si elle n'existe pas.

### Effectuer un dépôt

\`\`\`bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/depot/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\\"montant\\": 10000}"
\`\`\`
Réponse (201) : `{"solde": "10000.00"}`. Réponse (400) si montant ≤ 0.

### Effectuer un retrait

\`\`\`bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/retrait/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\\"montant\\": 5000}"
\`\`\`
Réponse (201) : `{"solde": "5000.00"}`.
Réponse (400) si montant ≤ 0, solde insuffisant, ou objectif non atteint et échéance non arrivée.

### Consulter l'historique des opérations

\`\`\`bash
curl http://127.0.0.1:8000/api/tirelires/1/operations/ -H "Authorization: Token <token>"
\`\`\`
Réponse (200) : liste des dépôts/retraits de la tirelire, du plus ancien au plus récent.

## Résumé des routes

| Méthode | URL | Auth requise |
|---|---|---|
| POST | /api/auth/login/ | Non |
| GET, POST | /api/tirelires/ | Oui |
| GET | /api/tirelires/{id}/ | Oui |
| POST | /api/tirelires/{id}/depot/ | Oui |
| POST | /api/tirelires/{id}/retrait/ | Oui |
| GET | /api/tirelires/{id}/operations/ | Oui |

## Codes d'erreur

| Code | Cas |
|---|---|
| 400 | Données invalides (montant, dates, règles métier RG1-RG3, RG5-RG6) |
| 401 | Absence ou invalidité du token |
| 403 | Accès à une tirelire d'un autre client (RG4) |
| 404 | Tirelire inexistante |