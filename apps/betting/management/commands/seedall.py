import uuid
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.users.choices import AccountStatus
from apps.users.models import User
from apps.wallet.services import deposit, get_or_create_wallet


class Command(BaseCommand):
    help = 'Seed completo: usuarios, wallets y eventos.'

    def handle(self, *args, **options):
        verified_users = [
            {
                'email': 'admin@gmail.com',
                'dni': '746960471',
                'first_name': 'Adrian',
                'last_name': 'Salazar',
                'birth_date': '1991-04-18',
                'password': '123',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'seed.user1@fairbet.pe',
                'dni': '123456781',
                'first_name': 'Luis',
                'last_name': 'Mendoza',
                'birth_date': '1996-01-10',
                'password': 'Lima2026!',
            },
            {
                'email': 'seed.user2@fairbet.pe',
                'dni': '102687740',
                'first_name': 'Carla',
                'last_name': 'Quispe',
                'birth_date': '1994-03-15',
                'password': 'Cusco2026!',
            },
            {
                'email': 'seed.user3@fairbet.pe',
                'dni': '876543252',
                'first_name': 'Diego',
                'last_name': 'Paredes',
                'birth_date': '1995-08-20',
                'password': 'Arequipa2026!',
            },
        ]
        autoexcluded_user = {
            'email': 'seed.autoexcluded@fairbet.pe',
            'dni': '000000006',
            'first_name': 'Rocio',
            'last_name': 'Cruz',
            'birth_date': '1993-07-11',
            'password': 'Piura2026!',
        }

        for user_data in verified_users:
            password = user_data.pop('password')
            user = User.objects.filter(
                Q(email=user_data['email']) | Q(dni=user_data['dni'])
            ).first()
            created = user is None
            if created:
                user = User.objects.create(
                    **user_data,
                    account_status=AccountStatus.VERIFICADO,
                )

            if created:
                user.set_password(password)
                user.account_status = AccountStatus.VERIFICADO
                user.is_staff = bool(user_data.get('is_staff', False))
                user.is_superuser = bool(user_data.get('is_superuser', False))
                user.save(
                    update_fields=['password', 'account_status', 'is_staff', 'is_superuser'],
                )
                self.stdout.write(self.style.SUCCESS(f'Usuario creado: {user.email}'))
            else:
                user.email = user_data['email']
                user.dni = user_data['dni']
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.birth_date = user_data['birth_date']
                if user.account_status != AccountStatus.VERIFICADO:
                    user.account_status = AccountStatus.VERIFICADO
                user.is_staff = bool(user_data.get('is_staff', False))
                user.is_superuser = bool(user_data.get('is_superuser', False))
                user.set_password(password)
                user.save(
                    update_fields=[
                        'email', 'dni', 'first_name', 'last_name', 'birth_date',
                        'account_status', 'is_staff', 'is_superuser', 'password',
                    ],
                )
                self.stdout.write(f'Usuario ya existe: {user.email}')

            get_or_create_wallet(user)
            deposit(
                user,
                Decimal('500.0000'),
                transaction_id=uuid.uuid5(uuid.NAMESPACE_DNS, f'seedall-deposit-{user.email}'),
            )

        password = autoexcluded_user.pop('password')
        user = User.objects.filter(
            Q(email=autoexcluded_user['email']) | Q(dni=autoexcluded_user['dni'])
        ).first()
        created = user is None
        if created:
            user = User.objects.create(
                **autoexcluded_user,
                account_status=AccountStatus.AUTOEXCLUIDO,
            )
        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f'Usuario autoexcluido creado: {user.email}'))
        else:
            user.email = autoexcluded_user['email']
            user.dni = autoexcluded_user['dni']
            user.first_name = autoexcluded_user['first_name']
            user.last_name = autoexcluded_user['last_name']
            user.birth_date = autoexcluded_user['birth_date']
            user.account_status = AccountStatus.AUTOEXCLUIDO
            user.set_password(password)
            user.save(
                update_fields=[
                    'email', 'dni', 'first_name', 'last_name', 'birth_date',
                    'account_status', 'password',
                ],
            )
            self.stdout.write(f'Usuario autoexcluido ya existe: {user.email}')

        call_command('seed_events')
        self.stdout.write(self.style.SUCCESS('Seed completo finalizado.'))
