from django.contrib.auth.models import User
from tirelires.models import Client

# Compte "alice" — utilisée dans les exemples du README
user_alice, _ = User.objects.get_or_create(username='alice')
user_alice.set_password('motdepasse')
user_alice.save()
Client.objects.get_or_create(
    user=user_alice,
    defaults={'telephone': '70000000', 'numero_compte': 'CPT001'},
)

# Compte "bob" — pour tester le cloisonnement RG4 (accès à une tirelire d'un autre client)
user_bob, _ = User.objects.get_or_create(username='bob')
user_bob.set_password('motdepasse')
user_bob.save()
Client.objects.get_or_create(
    user=user_bob,
    defaults={'telephone': '71111111', 'numero_compte': 'CPT002'},
)

print("Comptes de test prets : alice / motdepasse, bob / motdepasse")