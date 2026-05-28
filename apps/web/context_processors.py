from apps.wallet.services import get_balance, get_or_create_wallet


def wallet_balance(request):
    if not request.user.is_authenticated:
        return {}
    try:
        get_or_create_wallet(request.user)
        return {'navbar_balance': get_balance(request.user)}
    except Exception:
        return {'navbar_balance': None}
