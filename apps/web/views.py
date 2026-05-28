import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.audit.services import dashboard_metrics
from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Event, Market, Selection
from apps.users.choices import AccountStatus, ExclusionType
from apps.users.serializers import DepositLimitSerializer, RegisterSerializer, SelfExclusionSerializer
from apps.wallet.models import AccountType, LedgerEntry
from apps.wallet.services import SaldoInsuficiente, deposit, get_balance, get_or_create_wallet, reserve_for_bet, withdraw


def _decimal_from_post(value):
    try:
        return Decimal(value).quantize(Decimal('0.0001'))
    except (InvalidOperation, TypeError):
        raise ValueError('Monto invalido.')


def home(request):
    events = (
        Event.objects.filter(status=Event.Status.PROGRAMADO)
        .prefetch_related('markets__selections')
        .order_by('starts_at')
    )
    return render(request, 'betting/home.html', {'events': events})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, email=request.POST.get('email'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('web-home')
        messages.error(request, 'Credenciales invalidas.')
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('web-home')


def register_view(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            get_or_create_wallet(user)
            login(request, user)
            return redirect('web-home')
        return render(request, 'auth/register.html', {'errors': serializer.errors, 'form': request.POST})
    return render(request, 'auth/register.html')


@login_required(login_url='web-login')
def bet_view(request, selection_id):
    selection = get_object_or_404(Selection.objects.select_related('market__event'), pk=selection_id)
    balance = get_balance(request.user)

    if request.method == 'POST':
        if request.user.account_status != AccountStatus.VERIFICADO:
            messages.error(request, 'Tu cuenta debe estar verificada para apostar.')
            return redirect('web-home')

        market = selection.market
        event = market.event

        if event.status != Event.Status.PROGRAMADO:
            messages.error(request, 'El evento no esta programado para recibir apuestas.')
            return redirect('web-home')
        if event.starts_at <= timezone.now():
            messages.error(request, 'El evento ya inicio.')
            return redirect('web-home')
        if market.status != Market.Status.ABIERTO:
            messages.error(request, 'El mercado no esta abierto.')
            return redirect('web-home')

        try:
            stake = _decimal_from_post(request.POST.get('stake'))

            if stake > settings.MAX_BET_STAKE:
                raise ValueError('El monto supera el limite maximo por apuesta.')

            reserve_for_bet(request.user, stake, transaction_id=uuid.uuid4())
            Bet.objects.create(
                user=request.user,
                market=selection.market,
                selection=selection,
                stake=stake,
                odds=selection.odds,
            )
            messages.success(request, 'Apuesta registrada con moneda virtual.')
            return redirect('web-historial')
        except (SaldoInsuficiente, ValueError) as exc:
            messages.error(request, str(exc))
    return render(request, 'betting/bet.html', {'selection': selection, 'balance': balance})


@login_required(login_url='web-login')
def wallet_view(request):
    get_or_create_wallet(request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            amount = _decimal_from_post(request.POST.get('amount'))
            if action == 'deposit':
                if request.user.account_status != AccountStatus.VERIFICADO:
                    raise ValueError('Tu cuenta debe estar verificada para realizar depositos.')

                limit_map = {
                    'deposit_limit_daily': 'diario',
                    'deposit_limit_weekly': 'semanal',
                    'deposit_limit_monthly': 'mensual',
                }
                for field, label in limit_map.items():
                    limit = getattr(request.user, field)
                    if limit is not None and amount > limit:
                        raise ValueError(f'El monto supera tu limite {label} de deposito ({limit}).')

                deposit(request.user, amount, transaction_id=uuid.uuid4())
                messages.success(request, 'Deposito virtual realizado correctamente.')
            elif action == 'withdraw':
                withdraw(request.user, amount, transaction_id=uuid.uuid4())
                messages.success(request, 'Retiro virtual realizado correctamente.')
            return redirect('web-wallet')
        except (SaldoInsuficiente, ValueError) as exc:
            messages.error(request, str(exc))

    wallet = get_or_create_wallet(request.user)
    entries = LedgerEntry.objects.filter(account=wallet).order_by('-created_at')[:10]
    return render(
        request,
        'wallet/wallet.html',
        {'balance': get_balance(request.user), 'entries': entries},
    )


@login_required(login_url='web-login')
def historial_view(request):
    bets = Bet.objects.filter(user=request.user).select_related('market__event', 'selection').order_by('-created_at')[:20]
    return render(request, 'betting/historial.html', {'bets': bets, 'BetStatus': BetStatus})


@login_required(login_url='web-login')
def dashboard_view(request):
    if not request.user.is_staff:
        return redirect('web-login')
    return render(request, 'dashboard/dashboard.html', {'metrics': dashboard_metrics()})


@login_required(login_url='web-login')
def perfil_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'limits':
            serializer = DepositLimitSerializer(data=request.POST, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                messages.success(request, 'Limite actualizado.')
                return redirect('web-perfil')
            messages.error(request, serializer.errors)
        elif action == 'self_exclusion':
            if request.POST.get('confirm') != 'on':
                messages.error(request, 'Debes confirmar explicitamente la autoexclusion.')
            else:
                serializer = SelfExclusionSerializer(
                    data={'exclusion_type': request.POST.get('exclusion_type')},
                    context={'request': request},
                )
                if serializer.is_valid():
                    serializer.save()
                    messages.success(request, 'Autoexclusion registrada.')
                    return redirect('web-perfil')
                messages.error(request, serializer.errors)

    return render(
        request,
        'auth/perfil.html',
        {'exclusion_types': ExclusionType.choices},
    )
