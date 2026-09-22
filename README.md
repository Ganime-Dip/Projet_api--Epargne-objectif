# API REST — Épargne à objectif

API de gestion de tirelires d'épargne pour LICELI Technologies.

## Prérequis
- Python 3.13
- pip

## Installation

\`\`\`bash
git clone <url_du_depot>
cd Projet_API
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
\`\`\`

## Démarrage

\`\`\`bash
python manage.py runserver
\`\`\`

L'API est disponible sur http://127.0.0.1:8000/api/

## Lancer les tests

\`\`\`bash
python manage.py test tirelires
\`\`\`

## Points d'entrée de l'API

| Méthode | URL | Description | Authentification |
|---|---|---|---|
| POST | /api/auth/login/ | Connexion | Non |
| GET | /api/tirelires/ | Liste des tirelires du client | Oui |
| POST | /api/tirelires/ | Créer une tirelire | Oui |
| GET | /api/tirelires/{id}/ | Détail d'une tirelire | Oui |
| POST | /api/tirelires/{id}/depot/ | Effectuer un dépôt | Oui |
| POST | /api/tirelires/{id}/retrait/ | Effectuer un retrait | Oui |
| GET | /api/tirelires/{id}/operations/ | Historique des opérations | Oui |

L'authentification se fait par token (header `Authorization: Token <token>`), obtenu via `/api/auth/login/`.