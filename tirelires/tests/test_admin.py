import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from tirelires.models import Client, Tirelire

NOUVEAU_CLIENT = {
    'username': 'charlie',
    'password': 'Sup3r-Secret!2026',
    'email': 'charlie@example.com',
    'telephone': '72222222',
    'numero_compte': 'CPT003',
}


class AdministrationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='root', password='pass1234')
        self.user_alice = User.objects.create_user(username='alice', password='pass1234')
        self.client_alice = Client.objects.create(
            user=self.user_alice, telephone='70000000', numero_compte='CPT001'
        )
        self.user_bob = User.objects.create_user(username='bob', password='pass1234')
        self.client_bob = Client.objects.create(
            user=self.user_bob, telephone='71111111', numero_compte='CPT002'
        )
        echeance = date.today() + timedelta(days=30)
        self.voyage = self.creer_tirelire(self.client_alice, 'Voyage', echeance)
        self.voiture = self.creer_tirelire(self.client_alice, 'Voiture', echeance)
        self.mariage = self.creer_tirelire(self.client_bob, 'Mariage', echeance)

    def creer_tirelire(self, client, libelle, echeance):
        return Tirelire.objects.create(
            client=client, libelle=libelle,
            montant_objectif=Decimal('100000'), date_echeance=echeance,
        )

    def auth_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')

    def test_admin_liste_les_clients(self):
        self.auth_as(self.admin)
        response = self.client.get('/api/admin/clients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_admin_cree_un_compte_client_qui_peut_se_connecter(self):
        self.auth_as(self.admin)
        response = self.client.post('/api/admin/clients/', NOUVEAU_CLIENT, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'charlie')
        self.assertNotIn('password', response.data)
        self.assertFalse(User.objects.get(username='charlie').is_staff)
        self.client.credentials()
        connexion = self.client.post(
            '/api/auth/login/',
            {'username': 'charlie', 'password': NOUVEAU_CLIENT['password']},
            format='json',
        )
        self.assertEqual(connexion.status_code, status.HTTP_200_OK)

    def test_creation_client_mot_de_passe_trop_court_refusee(self):
        self.auth_as(self.admin)
        donnees = {**NOUVEAU_CLIENT, 'password': '123'}
        response = self.client.post('/api/admin/clients/', donnees, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_creation_client_nom_d_utilisateur_deja_pris_refusee(self):
        self.auth_as(self.admin)
        donnees = {**NOUVEAU_CLIENT, 'username': 'alice'}
        response = self.client.post('/api/admin/clients/', donnees, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_creation_client_numero_de_compte_deja_pris_refusee(self):
        self.auth_as(self.admin)
        donnees = {**NOUVEAU_CLIENT, 'numero_compte': 'CPT001'}
        response = self.client.post('/api/admin/clients/', donnees, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero_compte', response.data)

    def test_client_n_a_pas_acces_aux_routes_admin(self):
        self.auth_as(self.user_alice)
        for reponse in (
            self.client.get('/api/admin/clients/'),
            self.client.post('/api/admin/clients/', NOUVEAU_CLIENT, format='json'),
            self.client.get('/api/admin/tirelires/'),
            self.client.get(f'/api/admin/clients/{self.client_bob.id}/'),
        ):
            self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_acces_admin_sans_authentification_refuse(self):
        response = self.client.get('/api/admin/clients/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_liste_toutes_les_tirelires(self):
        self.auth_as(self.admin)
        response = self.client.get('/api/admin/tirelires/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        proprietaires = {t['client_username'] for t in response.data['results']}
        self.assertEqual(proprietaires, {'alice', 'bob'})

    def test_admin_filtre_les_tirelires_par_client(self):
        self.auth_as(self.admin)
        response = self.client.get(f'/api/admin/tirelires/?client={self.client_alice.id}')
        self.assertEqual(response.data['count'], 2)

    def test_admin_recherche_les_tirelires_par_nom_de_client(self):
        self.auth_as(self.admin)
        response = self.client.get('/api/admin/tirelires/?search=bob')
        self.assertEqual([t['libelle'] for t in response.data['results']], ['Mariage'])

    def test_admin_desactive_un_client(self):
        access_alice = str(AccessToken.for_user(self.user_alice))
        self.auth_as(self.admin)
        response = self.client.patch(
            f'/api/admin/clients/{self.client_alice.id}/', {'actif': False}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['actif'])
        self.client.credentials()
        connexion = self.client.post(
            '/api/auth/login/', {'username': 'alice', 'password': 'pass1234'}, format='json'
        )
        self.assertEqual(connexion.status_code, status.HTTP_400_BAD_REQUEST)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_alice}')
        self.assertEqual(
            self.client.get('/api/tirelires/').status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_admin_client_introuvable(self):
        self.auth_as(self.admin)
        response = self.client.get(f'/api/admin/clients/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['erreur'], 'Client introuvable.')

    def test_admin_ne_peut_pas_deposer_sur_une_tirelire(self):
        self.auth_as(self.admin)
        response = self.client.post(
            f'/api/tirelires/{self.voyage.id}/depot/', {'montant': '1000'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_token_administrateur_porte_le_role_administrateur(self):
        connexion = self.client.post(
            '/api/auth/login/', {'username': 'root', 'password': 'pass1234'}, format='json'
        )
        self.assertEqual(AccessToken(connexion.data['access'])['role'], 'administrateur')