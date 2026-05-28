from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.betting.models import Event, Market, Selection


class Command(BaseCommand):
    help = 'Crea eventos semilla con mercados 1X2 y cuotas realistas (mix EN_VIVO + PROGRAMADO).'

    def handle(self, *args, **options):
        fixtures = [
            # EN_VIVO events (started in the past, few minutes ago)
            {
                'name': 'Manchester United vs Liverpool',
                'sport': 'futbol',
                'status': 'en_vivo',
                'starts_at_delta': -30,  # 30 minutos atrás
                'odds': ('2.1000', '3.4000', '3.8000'),
            },
            {
                'name': 'Barcelona vs Bayern Munich',
                'sport': 'futbol',
                'status': 'en_vivo',
                'starts_at_delta': -15,  # 15 minutos atrás
                'odds': ('2.3000', '3.2000', '3.5000'),
            },
            # PROGRAMADO events (future)
            {
                'name': 'Alianza Lima vs Sporting Cristal',
                'sport': 'futbol',
                'status': 'programado',
                'starts_at_delta': 1,  # 1 día adelante
                'odds': ('2.1000', '3.4000', '3.8000'),
            },
            {
                'name': 'Universitario vs Melgar',
                'sport': 'futbol',
                'status': 'programado',
                'starts_at_delta': 2,
                'odds': ('1.9500', '3.2500', '4.1000'),
            },
            {
                'name': 'Peru vs Chile',
                'sport': 'futbol',
                'status': 'programado',
                'starts_at_delta': 3,
                'odds': ('2.4500', '3.1000', '2.9000'),
            },
            {
                'name': 'Argentina vs Brasil',
                'sport': 'futbol',
                'status': 'programado',
                'starts_at_delta': 4,
                'odds': ('2.3000', '3.3000', '3.0000'),
            },
            {
                'name': 'Real Madrid vs Barcelona',
                'sport': 'futbol',
                'status': 'programado',
                'starts_at_delta': 5,
                'odds': ('2.2000', '3.5000', '3.2000'),
            },
        ]

        created = 0
        for fixture in fixtures:
            name = fixture['name']
            sport = fixture['sport']
            status = fixture['status']
            odds = fixture['odds']
            
            # Calcular starts_at
            if status == 'en_vivo':
                # EN_VIVO: pasado (minutos atrás)
                starts_at = timezone.now() + timezone.timedelta(minutes=fixture['starts_at_delta'])
            else:
                # PROGRAMADO: futuro (días adelante)
                starts_at = timezone.now() + timezone.timedelta(days=fixture['starts_at_delta'])
            
            # Usar update_or_create para manejar re-ejecuciones
            event, event_created = Event.objects.update_or_create(
                name=name,
                defaults={
                    'sport': sport,
                    'status': status,
                    'starts_at': starts_at,
                },
            )
            if event_created:
                created += 1

            market, _ = Market.objects.get_or_create(
                event=event,
                name='Resultado final',
                market_type=Market.Type.UNO_X_DOS,
            )
            for selection_name, selection_odds in zip(('local', 'empate', 'visitante'), odds):
                Selection.objects.update_or_create(
                    market=market,
                    name=selection_name,
                    defaults={'odds': Decimal(selection_odds)},
                )

        self.stdout.write(self.style.SUCCESS(f'Seed de eventos completado. Eventos nuevos: {created}'))
