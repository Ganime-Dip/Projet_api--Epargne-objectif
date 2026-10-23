from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from tirelires.exceptions import MontantInvalide, RetraitNonAutorise, SoldeInsuffisant
from tirelires.models import Client, Tirelire


class TirelireModelTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='alice', password='pass1234')
        self.client_obj = Client.objects.create(
            user=user, telephone='70000000', numero_compte='CPT001'
        )
        self.tirelire = Tirelire.objects.create(
            client=self.client_obj,
            libelle='Voyage',
            montant_objectif=Decimal(100000),
            date_echeance=timezone.now().date() + timedelta(days=30),
        )
    
    def test_progression_nulle_a_la_creation(self):
        self.assertEqual(self.tirelire.progression_pourcentage(), Decimal(0))
        self.assertEqual(self.tirelire.montant_restant(), Decimal(100000))

    def test_progression_apres_depot_partiel(self):
        self.tirelire.deposer(Decimal(25000))
        self.assertEqual(self.tirelire.progression_pourcentage(), Decimal(25))
        self.assertEqual(self.tirelire.montant_restant(), Decimal(75000))

    def test_progression_plafonnee_a_100_pourcent(self):
        self.tirelire.deposer(Decimal(150000))
        self.assertEqual(self.tirelire.progression_pourcentage(), Decimal(100))
        self.assertEqual(self.tirelire.montant_restant(), Decimal(0))

    def test_retrait_autorise_une_fois_objectif_atteint(self):
        self.assertFalse(self.tirelire.retrait_autorise())
        self.tirelire.deposer(Decimal(100000))
        self.assertTrue(self.tirelire.retrait_autorise())

    def test_retrait_autorise_une_fois_echeance_depassee(self):
        self.tirelire.date_echeance = date.today() - timedelta(days=1)
        self.assertTrue(self.tirelire.retrait_autorise())

    # --- RG1 : montant strictement positif ---

    def test_deposer_montant_negatif_leve_montant_invalide(self):
        with self.assertRaises(MontantInvalide):
            self.tirelire.deposer(Decimal(-100))

    def test_deposer_montant_nul_leve_montant_invalide(self):
        with self.assertRaises(MontantInvalide):
            self.tirelire.deposer(Decimal(0))

    def test_retirer_montant_negatif_leve_montant_invalide(self):
        with self.assertRaises(MontantInvalide):
            self.tirelire.retirer(Decimal(-100))

    def test_deposer_montant_valide_augmente_le_solde(self):
        self.tirelire.deposer(Decimal(5000))
        self.assertEqual(self.tirelire.solde, Decimal(5000))

    # --- RG2 : solde jamais négatif ---

    def test_retirer_plus_que_le_solde_leve_solde_insuffisant(self):
        self.tirelire.deposer(Decimal(100000))  # débloque la tirelire (objectif atteint)
        with self.assertRaises(SoldeInsuffisant):
            self.tirelire.retirer(Decimal(999999))

    # --- RG3 : retrait bloqué tant que ni objectif ni échéance ---

    def test_retirer_avant_objectif_et_avant_echeance_leve_retrait_non_autorise(self):
        self.tirelire.deposer(Decimal(1000))  # solde < objectif, échéance future
        with self.assertRaises(RetraitNonAutorise):
            self.tirelire.retirer(Decimal(500))

    def test_retirer_autorise_une_fois_objectif_atteint(self):
        self.tirelire.deposer(Decimal(100000))  # solde = objectif
        self.tirelire.retirer(Decimal(50000))
        self.assertEqual(self.tirelire.solde, Decimal(50000))

    def test_retirer_autorise_une_fois_echeance_depassee(self):
        self.tirelire.date_echeance = timezone.now().date() - timedelta(days=1)
        self.tirelire.save()
        self.tirelire.deposer(Decimal(1000))  # objectif toujours pas atteint
        self.tirelire.retirer(Decimal(500))
        self.assertEqual(self.tirelire.solde, Decimal(500))

    # --- Traçabilité : une Operation est bien créée à chaque succès ---

    def test_deposer_cree_une_operation(self):
        self.tirelire.deposer(Decimal(5000))
        self.assertEqual(self.tirelire.operations.count(), 1)
        self.assertEqual(self.tirelire.operations.first().type_operation, 'depot')

    def test_operation_non_creee_si_depot_refuse(self):
        with self.assertRaises(MontantInvalide):
            self.tirelire.deposer(Decimal(-100))
        self.assertEqual(self.tirelire.operations.count(), 0)