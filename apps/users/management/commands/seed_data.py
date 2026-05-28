import uuid
from decimal import Decimal

from django.core.management import BaseCommand, call_command

from apps.users.choices import AccountStatus
from apps.users.models import User
from apps.wallet.services import deposit, get_or_create_wallet


class Command(BaseCommand):
    help = 'Carga datos semilla de usuarios, wallets y eventos.'

    def handle(self, *args, **options):
        users_seed = [
            {
                'email': 'admin@fairbet.pe',
                'dni': '746960471',
                'first_name': 'Admin',
                'last_name': 'FairBet',
                'birth_date': '1990-01-01',
                'password': 'SecurePass123!',
                'is_superuser': True,
                'is_staff': True,
                'account_status': AccountStatus.VERIFICADO,
            },
            {
                'email': 'player1@fairbet.pe',
                'dni': '876543252',
                'first_name': 'Player',
                'last_name': 'One',
                'birth_date': '1997-05-10',
                'password': 'SecurePass123!',
                'account_status': AccountStatus.VERIFICADO,
            },
            {
                'email': 'player2@fairbet.pe',
                'dni': '102687740',
                'first_name': 'Player',
                'last_name': 'Two',
                'birth_date': '1996-09-22',
                'password': 'SecurePass123!',
                'account_status': AccountStatus.PENDIENTE_VERIFICACION,
            },
        ]

        for data in users_seed:
            password = data.pop('password')
            email = data['email']
            user, created = User.objects.get_or_create(email=email, defaults=data)
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Usuario creado: {email}'))
            else:
                self.stdout.write(f'Usuario ya existe: {email}')

        for email, amount in [('player1@fairbet.pe', Decimal('500.0000'))]:
            user = User.objects.get(email=email)
            get_or_create_wallet(user)
            deposit(
                user,
                amount,
                transaction_id=uuid.uuid5(uuid.NAMESPACE_DNS, f'seed-deposit-{email}'),
            )
            self.stdout.write(self.style.SUCCESS(f'Wallet fondeado: {email} +{amount}'))

        call_command('seed_events')
        self.stdout.write(self.style.SUCCESS('Seed de eventos ejecutado.'))
        self.stdout.write(self.style.SUCCESS('Seed completado.'))
