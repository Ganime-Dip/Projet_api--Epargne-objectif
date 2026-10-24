# API REST : Épargne à objectif

API de gestion de tirelires d'épargne pour LICELI Technologies. Un client authentifié crée des
tirelires liées à un objectif d'épargne, y effectue des dépôts et des retraits (soumis aux règles
de gestion) et consulte l'historique de ses opérations. Un administrateur gère les comptes clients.

La documentation complète et testable de l'API est disponible sur `/api/docs/` une fois le
serveur lancé.

## Prérequis

- Python 3.13 ([télécharger ici](https://www.python.org/downloads/) si non installé ; cocher
  **"Add python.exe to PATH"** pendant l'installation sur Windows)
- pip (inclus avec Python)

Vérifier votre version : `python --version`

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

`createsuperuser` crée le premier **administrateur** (voir « Rôles » ci-dessous).

> **Mise à jour depuis une version précédente** : le schéma de la base a changé (identifiants
> UUID, numéro de compte unique). Supprimer le fichier `db.sqlite3`, puis relancer
> `python manage.py migrate` et `python manage.py createsuperuser`.

## Démarrage

```bash
python manage.py runserver
```

| Adresse | Contenu |
|---|---|
| http://127.0.0.1:8000/api/docs/ | Documentation interactive (Swagger UI) : toutes les routes, testables |
| http://127.0.0.1:8000/api/schema/ | Schéma OpenAPI brut |
| http://127.0.0.1:8000/admin/ | Site d'administration Django |

## Rôles

Administrateur : Super-utilisateur (`createsuperuser`), sans profil client
                 Crée et désactive des comptes clients
                 Consulte toutes les tirelires, en lecture seule
                 Routes `/api/admin/...`

Client :  Utilisateur avec un profil client
          Gère ses propres tirelires (création, dépôt, retrait, historique)
          Routes `/api/tirelires/...`


Un administrateur ne peut jamais déposer ou retirer à la place d'un client. Les administrateurs ne
se créent pas par l'API, uniquement avec `createsuperuser`.

## Premiers pas dans Swagger

1. Ouvrir `/api/docs/`. Dans `POST /api/auth/login/`, se connecter avec le compte administrateur
   créé à l'installation. Copier l'`access` retourné.
2. Cliquer sur **Authorize**, coller **uniquement l'access token**, valider.
3. Dans le groupe **Administration**, `POST /api/admin/clients/` : créer un compte client
   (le mot de passe doit respecter les règles de validation de Django : 8 caractères minimum,
   pas trop courant, pas entièrement numérique).
4. Se connecter avec ce compte client (login, puis **Authorize** avec son nouvel access token).
5. Créer une tirelire (`POST /api/tirelires/`), y déposer (`.../depot/`), tenter un retrait
   (`.../retrait/`), consulter l'historique (`.../operations/`).

**Raccourci de démonstration (facultatif)** : `python manage.py shell < seed_demo.py` crée deux
comptes clients, `alice` et `bob`, tous deux avec le mot de passe `motdepasse`.

## Authentification

L'API utilise des jetons JWT, au format standard `Authorization: Bearer <access>`.

- **Connexion** (`POST /api/auth/login/`) : retourne un `access` (valable **15 minutes**) et un
  `refresh` (valable **1 jour**). Chaque connexion génère une nouvelle paire.
- **Renouvellement** (`POST /api/auth/refresh/` avec le `refresh`) : retourne un nouvel `access` et
  un nouveau `refresh`. L'ancien `refresh` devient inutilisable.
- **Déconnexion** (`POST /api/auth/logout/` avec le `refresh`, `access` dans l'en-tête) : invalide
  le `refresh`. L'`access` déjà émis reste valable jusqu'à son expiration (15 minutes maximum).

Quand l'`access` expire, les routes répondent `401` : utiliser le renouvellement, ou se reconnecter.

## Routes

| Méthode | URL | Rôle | Description |
|---|---|---|---|
| POST | `/api/auth/login/` | public | Connexion |
| POST | `/api/auth/refresh/` | public (avec refresh token) | Renouveler la session |
| POST | `/api/auth/logout/` | connecté | Déconnexion |
| GET, POST | `/api/tirelires/` | client | Lister (paginé, filtrable) / créer ses tirelires |
| GET | `/api/tirelires/{id}/` | client | Détail, avec la progression |
| POST | `/api/tirelires/{id}/depot/` | client | Effectuer un dépôt |
| POST | `/api/tirelires/{id}/retrait/` | client | Effectuer un retrait |
| GET | `/api/tirelires/{id}/operations/` | client | Historique (paginé, filtrable) |
| GET, POST | `/api/admin/clients/` | administrateur | Lister / créer des comptes clients |
| GET, PATCH | `/api/admin/clients/{id}/` | administrateur | Consulter / activer-désactiver un client |
| GET | `/api/admin/tirelires/` | administrateur | Toutes les tirelires (lecture seule) |

Les identifiants (`{id}`) sont des UUID.

## Pagination, recherche et filtres

Les listes retournent `{"count": ..., "next": ..., "previous": ..., "results": [...]}`.

| Paramètre | Routes | Rôle |
|---|---|---|
| `page`, `page_size` | toutes les listes | Page (10 éléments par défaut, 100 maximum) |
| `search` | tirelires, clients | Recherche textuelle |
| `ordering` | toutes les listes | Tri (préfixe `-` pour décroissant) |
| `montant_objectif_min`, `montant_objectif_max` | tirelires | Plage de montant objectif |
| `echeance_apres`, `echeance_avant` | tirelires | Plage d'échéance (AAAA-MM-JJ) |
| `objectif_atteint`, `echeance_depassee`, `retrait_autorise` | tirelires | `true` ou `false` |
| `type_operation`, `date_apres`, `date_avant`, `montant_min`, `montant_max` | opérations | Filtres de l'historique |
| `client` | admin/tirelires | Identifiant du client |
| `actif` | admin/clients | `true` ou `false` |

Le détail de chaque paramètre est dans Swagger.

## Exemples avec curl

Syntaxe pour `cmd` Windows (sous Linux/Mac, utiliser des apostrophes autour du JSON).
Remplacer `<access>` par l'access token et `<id>` par l'identifiant d'une tirelire.

**Connexion**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"username\": \"alice\", \"password\": \"motdepasse\"}"
```
Succès (200) : `{"refresh": "eyJ...", "access": "eyJ..."}`
Mauvais mot de passe (400) : `{"erreur": "Identifiants invalides."}`

**Créer une tirelire**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"libelle\": \"Voyage\", \"montant_objectif\": 100000, \"date_echeance\": \"2027-01-01\"}"
```
Succès (201) : la tirelire, avec son `id` (UUID) et son bloc `progression`.
Montant objectif négatif (400) : `{"erreur": "Le montant objectif doit être positif."}`

**Effectuer un dépôt**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/<id>/depot/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"montant\": 10000}"
```
Succès (201) : `{"solde": "10000.00"}`
Montant négatif ou nul (400) : `{"erreur": "Le montant doit être strictement positif."}`

**Effectuer un retrait**
```bash
curl -X POST http://127.0.0.1:8000/api/tirelires/<id>/retrait/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"montant\": 5000}"
```
Succès (201) : `{"solde": "5000.00"}` (si l'objectif est atteint ou l'échéance dépassée)
Objectif non atteint et échéance non arrivée (400) : `{"erreur": "Retrait impossible : objectif non atteint et échéance non arrivée."}`
Solde insuffisant (400) : `{"erreur": "Solde insuffisant pour ce retrait."}`

**Tirelire d'un autre client, ou inexistante**
```bash
curl http://127.0.0.1:8000/api/tirelires/<id>/ -H "Authorization: Bearer <access>"
```
Dans les deux cas (404) : `{"erreur": "Tirelire introuvable."}`. Les deux situations sont
volontairement indiscernables, pour ne pas révéler l'existence des tirelires d'autrui.

**Lister avec filtres et pagination**
```bash
curl "http://127.0.0.1:8000/api/tirelires/?search=voyage&retrait_autorise=false&ordering=-solde&page_size=5" -H "Authorization: Bearer <access>"
```

**Renouveler la session, puis se déconnecter**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/refresh/ -H "Content-Type: application/json" -d "{\"refresh\": \"<refresh>\"}"
curl -X POST http://127.0.0.1:8000/api/auth/logout/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"refresh\": \"<refresh>\"}"
```
Renouvellement (200) : nouvelle paire `access` / `refresh`. Déconnexion (204) : pas de contenu.

## Codes de réponse

**Succès**

| Code | Cas |
|---|---|
| 200 | Lecture, connexion, renouvellement, activation/désactivation d'un client |
| 201 | Création (tirelire, compte client), dépôt, retrait |
| 204 | Déconnexion |

**Erreurs**

| Code | Cas |
|---|---|
| 400 | Données invalides, règle de gestion non respectée (RG1 à RG3, RG5, RG6), identifiants invalides |
| 401 | Token absent, invalide ou expiré |
| 403 | Mauvais rôle : compte non client sur `/api/tirelires/...`, non administrateur sur `/api/admin/...` |
| 404 | Tirelire introuvable (inexistante ou appartenant à un autre client), client introuvable |

## Tests

```bash
python manage.py test tirelires --verbosity 2
```

Affiche chaque test avec son résultat (72 tests : règles de gestion, authentification, rôles,
progression, pagination et filtres, documentation).