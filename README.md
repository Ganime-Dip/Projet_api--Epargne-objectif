# API REST — Épargne à objectif

API de gestion de tirelires d'épargne pour LICELI Technologies. Un client authentifié
crée des tirelires liées à un objectif d'épargne, y effectue des dépôts et des retraits,
et consulte l'historique de ses opérations.

## Prérequis
- Python 3.13
- pip

Vérifier votre version installée :
```bash
python --version
```

## Installation

```bash
git clone https://github.com/Ganime-Dip/Projet_api--Epargne-objectif.git
cd Projet_api--Epargne-objectif
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## Créer des comptes de test

Un script est fourni pour créer deux comptes client de démonstration (`alice` et `bob`,
utilisés dans tous les exemples ci-dessous) :

```bash
python manage.py shell < seed_demo.py
```

Ça crée :
- `alice` / `motdepasse` (mot de passe : `motdepasse`)
- `bob` / `motdepasse` (utilisé pour illustrer le refus d'accès entre clients, RG4)

## Démarrage

```bash
python manage.py runserver
```

## Documentation interactive de l'API

Une fois le serveur lancé, la documentation complète est disponible sur :

- Swagger UI (interactif, permet de tester les routes) : http://127.0.0.1:8000/api/docs/
- Schéma OpenAPI brut : http://127.0.0.1:8000/api/schema/

Pour tester les routes protégées dans Swagger : exécuter `POST /api/auth/login/`, copier le token retourné, cliquer sur **Authorize** et saisir `Token <votre_token>`.



## Lancer les tests (sur le terminal)

```bash
python manage.py test tirelires --verbosity 2
```

Affiche chaque test exécuté avec son résultat (25 tests, couvrant RG1 à RG6 et les 7 cas
d'utilisation).

## Authentification

Toutes les routes, sauf la connexion, exigent un token dans l'en-tête :

```
Authorization: Token <votre_token>
```

## Points d'entrée de l'API

### Connexion

**Cas réussi**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"username\": \"alice\", \"password\": \"motdepasse\"}"
```
Réponse attendue (200) :
```json
{"token": "cae129d8c0a8b3cd7aae37739fd6bd6b939fcf13"}
```

**Cas refusé — mauvais mot de passe**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"username\": \"alice\", \"password\": \"faux\"}"
```
Réponse attendue (400) :
```json
{"erreur": "Identifiants invalides."}
```

---

### Créer une tirelire

Récupère d'abord un token via la connexion, puis remplace `<token>` dans les exemples suivants.


**Cas réussi**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"libelle\": \"Voyage\", \"montant_objectif\": 500000, \"date_echeance\": \"2027-01-01\"}"
```
Réponse attendue (201) :
```json
{"id": 1, "libelle": "Voyage", "montant_objectif": "500000.00", "date_echeance": "2027-01-01", "date_ouverture": "2026-09-24", "solde": "0.00"}
```

**Cas refusé — montant objectif négatif (RG5)**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"libelle\": \"Test\", \"montant_objectif\": -100, \"date_echeance\": \"2027-01-01\"}"
```
Réponse attendue (400) :
```json
{"erreur": "Le montant objectif doit etre positif."}
```

**Cas refusé — montant objectif nul**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"libelle\": \"Test\", \"montant_objectif\": 0, \"date_echeance\": \"2027-01-01\"}"
```
Réponse attendue (400) :
```json
{"erreur": "Le montant objectif doit etre positif."}
```

**Cas refusé — date dans le passé**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"libelle\": \"Test\", \"montant_objectif\": 100, \"date_echeance\": \"2024-01-01\"}"
```
Réponse attendue (400) :
```json
{"erreur": "La date d'échéance doit être future."}
```

---

### Lister mes tirelires

**Cas réussi**
```bash
curl http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Token <token>"
```
Réponse attendue (200) : la liste des tirelires du client connecté (tableau JSON, vide si aucune).

**Cas refusé — sans authentification**
```bash
curl http://127.0.0.1:8000/api/tirelires/
```
Réponse attendue (401) :
```json
{"detail": "Authentication credentials were not provided."}
```

---

### Consulter une tirelire précise

**Cas réussi** (remplace `1` par l'id retourné à la création)
```bash
curl http://127.0.0.1:8000/api/tirelires/1/ -H "Authorization: Token <token>"
```
Réponse attendue (200) : le détail de la tirelire.

**Cas refusé — tirelire inexistante**
```bash
curl http://127.0.0.1:8000/api/tirelires/99999/ -H "Authorization: Token <token>"
```
Réponse attendue (404) :
```json
{"erreur": "Tirelire introuvable."}
```

**Cas refusé — tirelire d'un autre client (RG4)** : connecte-toi avec `bob` pour obtenir un
autre token, puis essaie d'accéder à une tirelire créée par `alice` :
```bash
curl http://127.0.0.1:8000/api/tirelires/1/ -H "Authorization: Token <token_de_bob>"
```
Réponse attendue (403) :
```json
{"erreur": "Tirelire introuvable."}
```

---

### Effectuer un dépôt

**Cas réussi**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/depot/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"montant\": 10000}"
```
Réponse attendue (201) :
```json
{"solde": "10000.00"}
```

**Cas refusé — montant négatif ou nul (RG1)**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/depot/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"montant\": -100}"
```
Réponse attendue (400) :
```json
{"erreur": "Le montant doit etre strictement positif."}
```

---

### Effectuer un retrait

**Cas réussi** (nécessite d'avoir d'abord déposé au moins le montant objectif, ou d'avoir
dépassé la date d'échéance — RG3)
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/retrait/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"montant\": 5000}"
```
Réponse attendue (201) :
```json
{"solde": "5000.00"}
```

**Cas refusé — objectif non atteint et échéance non arrivée (RG3)**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/retrait/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"montant\": 100}"
```
Réponse attendue (400) :
```json
{"erreur": "Retrait impossible : objectif non atteint et echeance non arrivee."}
```

**Cas refusé — solde insuffisant (RG2, après avoir débloqué la tirelire)**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/1/retrait/ -H "Authorization: Token <token>" -H "Content-Type: application/json" -d "{\"montant\": 999999}"
```
Réponse attendue (400) :
```json
{"erreur": "Solde insuffisant pour ce retrait."}
```

---

### Consulter l'historique des opérations

**Cas réussi**
```bash
curl http://127.0.0.1:8000/api/tirelires/1/operations/ -H "Authorization: Token <token>"
```
Réponse attendue (200) : la liste des dépôts/retraits enregistrés, du plus ancien au plus
récent.

**Cas refusé — tirelire d'un autre client**
```bash
curl http://127.0.0.1:8000/api/tirelires/1/operations/ -H "Authorization: Token <token_de_bob>"
```
Réponse attendue (403) :
```json
{"erreur": "Tirelire introuvable."}
```

## Résumé des routes

| Méthode | URL | Auth requise |
|---|---|---|
| POST | /api/auth/login/ | Non |
| GET, POST | /api/tirelires/ | Oui |
| GET | /api/tirelires/{id}/ | Oui |
| POST | /api/tirelires/{id}/depot/ | Oui |
| POST | /api/tirelires/{id}/retrait/ | Oui |
| GET | /api/tirelires/{id}/operations/ | Oui |

## Codes de réponse


### Succès

| Code | Cas |
|---|---|
| 200 | Lecture réussie (connexion, liste des tirelires, détail d'une tirelire, historique des opérations) |
| 201 | Création réussie (nouvelle tirelire, dépôt effectué, retrait effectué) |

### Erreurs

| Code | Cas |
|---|---|
| 400 | Données invalides (montant, dates, règles métier RG1-RG3, RG5-RG6) |
| 401 | Absence ou invalidité du token |
| 403 | Accès à une tirelire d'un autre client (RG4) |
| 404 | Tirelire inexistante |