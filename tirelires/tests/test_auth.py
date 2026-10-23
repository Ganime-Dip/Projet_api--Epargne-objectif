from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from tirelires.models import Client


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass1234')
        Client.objects.create(user=self.user, telephone='70000000', numero_compte='CPT001')
        self.other = User.objects.create_user(username='bob', password='pass1234')
        Client.objects.create(user=self.other, telephone='71111111', numero_compte='CPT002')

    def login(self, username='alice', password='pass1234'):
        return self.client.post(
            '/api/auth/login/', {'username': username, 'password': password}, format='json'
        )

    def bearer(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_login_reussi_retourne_access_et_refresh(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_mauvais_mot_de_passe_refuse(self):
        response = self.login(password='faux')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['erreur'], 'Identifiants invalides.')

    def test_chaque_connexion_genere_de_nouveaux_tokens(self):
        premiere = self.login().data
        seconde = self.login().data
        self.assertNotEqual(premiere['access'], seconde['access'])
        self.assertNotEqual(premiere['refresh'], seconde['refresh'])

    def test_token_associe_a_l_identite_de_l_utilisateur(self):
        access_alice = AccessToken(self.login().data['access'])
        access_bob = AccessToken(self.login('bob').data['access'])
        self.assertEqual(str(access_alice['user_id']), str(self.user.id))
        self.assertEqual(str(access_bob['user_id']), str(self.other.id))
        self.assertEqual(access_alice['role'], 'client')

    def test_access_token_expire_refuse(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(from_time=timezone.now() - timedelta(hours=1), lifetime=timedelta(minutes=15))
        self.bearer(str(token))
        response = self.client.get('/api/tirelires/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ancien_prefixe_token_refuse(self):
        access = self.login().data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {access}')
        response = self.client.get('/api/tirelires/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_donne_une_nouvelle_paire_et_invalide_l_ancien_refresh(self):
        refresh = self.login().data['refresh']
        response = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotEqual(response.data['refresh'], refresh)
        reutilisation = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(reutilisation.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalide_le_refresh_token(self):
        tokens = self.login().data
        self.bearer(tokens['access'])
        response = self.client.post('/api/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.client.credentials()
        renouvellement = self.client.post(
            '/api/auth/refresh/', {'refresh': tokens['refresh']}, format='json'
        )
        self.assertEqual(renouvellement.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_sans_authentification_refuse(self):
        refresh = self.login().data['refresh']
        response = self.client.post('/api/auth/logout/', {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_avec_refresh_token_d_un_autre_utilisateur_refuse(self):
        refresh_bob = self.login('bob').data['refresh']
        self.bearer(self.login().data['access'])
        response = self.client.post('/api/auth/logout/', {'refresh': refresh_bob}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)