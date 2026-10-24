from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from tirelires.models import Client, Tirelire


class ListesTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username='alice', password='pass1234')
        self.client_a = Client.objects.create(
            user=user, telephone='70000000', numero_compte='CPT001'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')
        dans_un_mois = date.today() + timedelta(days=30)
        self.voyage = self.creer('Voyage', '100000', dans_un_mois)
        self.voiture = self.creer('Voiture', '500000', dans_un_mois)
        self.mariage = self.creer('Mariage', '1000', date.today() - timedelta(days=1))

    def creer(self, libelle, objectif, echeance, client=None):
        return Tirelire.objects.create(
            client=client or self.client_a,
            libelle=libelle,
            montant_objectif=Decimal(objectif),
            date_echeance=echeance,
        )

    def libelles(self, response):
        return [t['libelle'] for t in response.data['results']]

    def test_liste_paginee_par_defaut(self):
        for i in range(9):
            self.creer(f'Extra {i}', '1000', date.today() + timedelta(days=10))
        response = self.client.get('/api/tirelires/')
        self.assertEqual(response.data['count'], 12)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])

    def test_taille_de_page_personnalisee(self):
        response = self.client.get('/api/tirelires/?page_size=2')
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 2)

    def test_recherche_par_libelle(self):
        response = self.client.get('/api/tirelires/?search=voy')
        self.assertEqual(self.libelles(response), ['Voyage'])

    def test_filtre_montant_objectif_min(self):
        response = self.client.get('/api/tirelires/?montant_objectif_min=200000')
        self.assertEqual(self.libelles(response), ['Voiture'])

    def test_filtre_echeance_depassee(self):
        response = self.client.get('/api/tirelires/?echeance_depassee=true')
        self.assertEqual(self.libelles(response), ['Mariage'])

    def test_filtre_objectif_atteint(self):
        self.voyage.deposer(Decimal(100000))
        response = self.client.get('/api/tirelires/?objectif_atteint=true')
        self.assertEqual(self.libelles(response), ['Voyage'])

    def test_filtre_retrait_autorise(self):
        self.voyage.deposer(Decimal(100000))
        autorises = self.client.get('/api/tirelires/?retrait_autorise=true')
        self.assertEqual(sorted(self.libelles(autorises)), ['Mariage', 'Voyage'])
        bloques = self.client.get('/api/tirelires/?retrait_autorise=false')
        self.assertEqual(self.libelles(bloques), ['Voiture'])

    def test_tri_par_montant_objectif_decroissant(self):
        response = self.client.get('/api/tirelires/?ordering=-montant_objectif')
        self.assertEqual(self.libelles(response), ['Voiture', 'Voyage', 'Mariage'])

    def test_recherche_limitee_aux_tirelires_du_client(self):
        bob = User.objects.create_user(username='bob', password='pass1234')
        client_bob = Client.objects.create(user=bob, telephone='71111111', numero_compte='CPT002')
        self.creer('Voyage de Bob', '1000', date.today() + timedelta(days=10), client=client_bob)
        response = self.client.get('/api/tirelires/?search=voyage')
        self.assertEqual(self.libelles(response), ['Voyage'])

    def test_historique_operations_filtre_par_type(self):
        self.voyage.deposer(Decimal(100000))
        self.voyage.retirer(Decimal(500))
        url = f'/api/tirelires/{self.voyage.id}/operations/'
        retraits = self.client.get(url + '?type_operation=retrait')
        self.assertEqual(retraits.status_code, status.HTTP_200_OK)
        self.assertEqual(retraits.data['count'], 1)
        tout = self.client.get(url)
        self.assertEqual(tout.data['count'], 2)
        
    def test_valeur_numerique_invalide_renvoie_400(self):
        response = self.client.get('/api/tirelires/?montant_objectif_min=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_invalide_renvoie_400(self):
        response = self.client.get('/api/tirelires/?echeance_avant=pas-une-date')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)