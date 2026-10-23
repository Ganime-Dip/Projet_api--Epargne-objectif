import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone

from .exceptions import MontantInvalide, RetraitNonAutorise, SoldeInsuffisant


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_inscription = models.DateField(auto_now_add=True)
    telephone = models.CharField(max_length=20)
    numero_compte = models.CharField(max_length=30)
    
    def __str__(self):
        return self.user.username
    
class Tirelire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='tirelires')
    libelle = models.CharField(max_length=100)
    montant_objectif = models.DecimalField(max_digits=12, decimal_places=2)
    date_echeance = models.DateField()
    date_ouverture = models.DateField(auto_now_add=True)
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.libelle} ({self.client})"
    
    def objectif_atteint(self) -> bool:
        return self.solde >= self.montant_objectif
    
    def echeance_depassee(self) -> bool:
        return timezone.now().date() > self.date_echeance
    
    def retrait_autorise(self) -> bool:
        return self.objectif_atteint() or self.echeance_depassee()

    def montant_restant(self) -> Decimal:
        return max(self.montant_objectif - self.solde, Decimal(0))

    def progression_pourcentage(self) -> Decimal:
        if self.montant_objectif <= 0:
            return Decimal(0)
        return min(self.solde / self.montant_objectif * 100, Decimal(100))
    
    def deposer(self, montant: Decimal) -> None:
        if montant <= 0:
            raise MontantInvalide("Le montant doit être strictement positif.")
        
        with transaction.atomic():
            self.solde += montant
            self.save()
            self.operations.create(montant=montant, type_operation=Operation.DEPOT)
    
    def retirer(self, montant: Decimal) -> None:
        if montant <= 0:
            raise MontantInvalide("Le montant doit être strictement positif.")
        if montant > self.solde:
            raise SoldeInsuffisant("Solde insuffisant pour ce retrait.")
        if not self.retrait_autorise():
            raise RetraitNonAutorise(
                "Retrait impossible : objectif non atteint et échéance non arrivée."
            )
        
        with transaction.atomic():
            self.solde -= montant
            self.save()
            self.operations.create(montant=montant, type_operation=Operation.RETRAIT)
    
class Operation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    DEPOT = 'depot'
    RETRAIT = 'retrait'
    TYPE_CHOICES = ((DEPOT, 'Dépôt'), (RETRAIT, 'Retrait'))
    
    tirelire = models.ForeignKey(Tirelire, on_delete=models.CASCADE, related_name='operations')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    type_operation = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date_operation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.type_operation} {self.montant} sur {self.tirelire}"