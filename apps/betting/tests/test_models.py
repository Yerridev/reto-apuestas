from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from hypothesis import given, strategies as st

from apps.betting.choices import BetStatus, can_transition
from apps.betting.models import Bet, Event, Market, Selection
from apps.users.choices import AccountStatus

User = get_user_model()


@pytest.fixture
def usuario_verificado(db):
    return User.objects.create_user(
        email='bet-models@fairbet.pe',
        password='Test1234!',
        dni='102687744',
        first_name='Bet',
        last_name='Models',
        birth_date='1995-01-01',
        account_status=AccountStatus.VERIFICADO,
    )


@pytest.fixture
def market(db):
    event = Event.objects.create(
        name='Alianza Lima vs Sporting Cristal',
        sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    return Market.objects.create(event=event, name='Resultado final', market_type=Market.Type.UNO_X_DOS)


@pytest.fixture
def selection(db, market):
    return Selection.objects.create(market=market, name='local', odds=Decimal('2.1000'))


@pytest.mark.django_db
def test_event_market_selection_se_crean_con_estados_por_defecto(market, selection):
    assert market.event.status == Event.Status.PROGRAMADO
    assert market.status == Market.Status.ABIERTO
    assert selection.odds == Decimal('2.1000')


@pytest.mark.django_db
def test_bet_se_crea_accepted_y_congela_odds(usuario_verificado, market, selection):
    bet = Bet.objects.create(
        user=usuario_verificado,
        market=market,
        selection=selection,
        stake=Decimal('50.0000'),
        odds=selection.odds,
    )

    assert bet.status == BetStatus.ACCEPTED
    assert bet.odds == Decimal('2.1000')


@pytest.mark.django_db
def test_bet_liquidada_no_puede_cambiar_de_estado(usuario_verificado, market, selection):
    bet = Bet.objects.create(
        user=usuario_verificado,
        market=market,
        selection=selection,
        stake=Decimal('50.0000'),
        odds=selection.odds,
        status=BetStatus.SETTLED_WON,
    )

    bet.status = BetStatus.ACCEPTED

    with pytest.raises(ValidationError):
        bet.full_clean()


@given(
    origin=st.sampled_from([choice.value for choice in BetStatus]),
    target=st.sampled_from([choice.value for choice in BetStatus]),
)
def test_transiciones_bet_solo_salen_desde_accepted(origin, target):
    expected = (
        origin == BetStatus.ACCEPTED
        and target in {BetStatus.SETTLED_WON, BetStatus.SETTLED_LOST, BetStatus.CANCELLED}
    )
    assert can_transition(origin, target) is expected
