import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from tirelires.models import Client, Tirelire


def access_for(user):
    return str(AccessToken.for_user(user))

class APIIntegrationTests(APITestCase):
    def setUp(self):
        user_a = User.objects.create_user(username='alice', password='pass1234')
        self.client_a = Client.objects.create(
            user=user_a, telephone='70000000', numero_compte='CPT001'
        )
        self.token_a = access_for(user_a)

        user_b = User.objects.create_user(username='bob', password='pass1234')
        Client.objects.create(user=user_b, telephone='71111111', numero_compte='CPT002')
        self.token_b = access_for(user_b)

        self.tirelire_a = Tirelire.objects.create(
            client=self.client_a,
            libelle='Voyage',
            montant_objectif=Decimal(100000),
            date_echeance=timezone.now().date() + timedelta(days=30),
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # 1. Dépôt d'un montant négatif ou nul

    def test_depot_montant_negatif_refuse(self):
        self.auth(self.token_a)
        url = f'/api/tirelires/{self.tirelire_a.id}/depot/'
        response = self.client.post(url, {'montant': '-100'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 2. Retrait supérieur au solde disponible

    def test_retrait_superieur_au_solde_refuse(self):
        self.auth(self.token_a)
        self.tirelire_a.deposer(Decimal(100000))
        url = f'/api/tirelires/{self.tirelire_a.id}/retrait/'
        response = self.client.post(url, {'montant': '999999'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 3. Retrait avant objectif atteint et avant échéance

    def test_retrait_avant_objectif_et_echeance_refuse(self):
        self.auth(self.token_a)
        self.tirelire_a.deposer(Decimal(1000))
        url = f'/api/tirelires/{self.tirelire_a.id}/retrait/'
        response = self.client.post(url, {'montant': '500'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 4. Consulter/modifier la tirelire d'un autre client (RG4)

    def test_consulter_tirelire_autre_client_refuse(self):
        self.auth(self.token_b)
        url = f'/api/tirelires/{self.tirelire_a.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deposer_sur_tirelire_autre_client_refuse(self):
        self.auth(self.token_b)
        url = f'/api/tirelires/{self.tirelire_a.id}/depot/'
        response = self.client.post(url, {'montant': '1000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 5. Déposer sur une tirelire inexistante

    def test_depot_tirelire_inexistante_refuse(self):
        self.auth(self.token_a)
        url = f'/api/tirelires/{uuid.uuid4()}/depot/'
        response = self.client.post(url, {'montant': '1000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Bonus : cas nominal complet, pour vérifier que le chemin heureux marche aussi

    def test_depot_et_retrait_nominal(self):
        self.auth(self.token_a)
        depot_url = f'/api/tirelires/{self.tirelire_a.id}/depot/'
        response = self.client.post(depot_url, {'montant': '100000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        retrait_url = f'/api/tirelires/{self.tirelire_a.id}/retrait/'
        response = self.client.post(retrait_url, {'montant': '30000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['solde']), Decimal(70000))

    def test_acces_sans_authentification_refuse(self):
        response = self.client.get('/api/tirelires/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
        
    # RG5 : montant objectif strictement positif à la création

    def test_creer_tirelire_montant_objectif_negatif_refuse(self):
        self.auth(self.token_a)
        response = self.client.post('/api/tirelires/', {
            'libelle': 'Test',
            'montant_objectif': '-1000',
            'date_echeance': str(timezone.now().date() + timedelta(days=30)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # RG6 : date d'échéance dans le futur

    def test_creer_tirelire_echeance_passee_refuse(self):
        self.auth(self.token_a)
        response = self.client.post('/api/tirelires/', {
            'libelle': 'Test',
            'montant_objectif': '1000',
            'date_echeance': str(timezone.now().date() - timedelta(days=1)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creer_tirelire_donnees_valides_reussit(self):
        self.auth(self.token_a)
        response = self.client.post('/api/tirelires/', {
            'libelle': 'Test',
            'montant_objectif': '1000',
            'date_echeance': str(timezone.now().date() + timedelta(days=30)),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    
        # UC3 : liste des tirelires ne montre que celles du client connecté

    def test_liste_tirelires_ne_montre_que_les_siennes(self):
        self.auth(self.token_b)
        response = self.client.get('/api/tirelires/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # bob n'a aucune tirelire

    # UC4 : consultation du détail d'une tirelire à soi

    def test_consulter_sa_propre_tirelire_reussit(self):
        self.auth(self.token_a)
        response = self.client.get(f'/api/tirelires/{self.tirelire_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['libelle'], 'Voyage')

    # UC7 : historique des opérations

    def test_historique_operations_apres_depot(self):
        self.auth(self.token_a)
        self.client.post(
            f'/api/tirelires/{self.tirelire_a.id}/depot/', {'montant': '5000'}, format='json'
        )
        response = self.client.get(f'/api/tirelires/{self.tirelire_a.id}/operations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type_operation'], 'depot')

    def test_historique_operations_autre_client_refuse(self):
        self.auth(self.token_b)
        response = self.client.get(f'/api/tirelires/{self.tirelire_a.id}/operations/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_compte_sans_profil_client_recoit_403_et_non_500(self):
        admin = User.objects.create_superuser(username='root', password='pass1234')
        self.auth(access_for(admin))
        for response in (
            self.client.get('/api/tirelires/'),
            self.client.post('/api/tirelires/', {}, format='json'),
        ):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            
    def test_identifiant_tirelire_est_un_uuid(self):
        self.auth(self.token_a)
        response = self.client.get(f'/api/tirelires/{self.tirelire_a.id}/')
        uuid.UUID(response.data['id'])  # lève une erreur si ce n'est pas un UUID

    def test_identifiant_entier_refuse(self):
        self.auth(self.token_a)
        response = self.client.get('/api/tirelires/1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_detail_tirelire_contient_la_progression(self):
        self.auth(self.token_a)
        self.tirelire_a.deposer(Decimal(50000))
        response = self.client.get(f'/api/tirelires/{self.tirelire_a.id}/')
        progression = response.data['progression']
        self.assertEqual(progression['montant_epargne'], '50000.00')
        self.assertEqual(progression['montant_objectif'], '100000.00')
        self.assertEqual(progression['montant_restant'], '50000.00')
        self.assertEqual(progression['pourcentage'], '50.00')
        self.assertFalse(progression['retrait_autorise'])