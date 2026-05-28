from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.betting.models import Event, Market, Selection


class Command(BaseCommand):
    help = 'Crea eventos semilla con mercados 1X2 y cuotas realistas.'

    def handle(self, *args, **options):
        fixtures = [
            ('Alianza Lima vs Sporting Cristal', 'futbol', 1, ('2.1000', '3.4000', '3.8000')),
            ('Universitario vs Melgar', 'futbol', 2, ('1.9500', '3.2500', '4.1000')),
            ('Peru vs Chile', 'futbol', 3, ('2.4500', '3.1000', '2.9000')),
            ('Argentina vs Brasil', 'futbol', 4, ('2.3000', '3.3000', '3.0000')),
            ('Real Madrid vs Barcelona', 'futbol', 5, ('2.2000', '3.5000', '3.2000')),
        ]

        created = 0
        for name, sport, days, odds in fixtures:
            event, event_created = Event.objects.get_or_create(
                name=name,
                defaults={
                    'sport': sport,
                    'starts_at': timezone.now() + timezone.timedelta(days=days),
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
