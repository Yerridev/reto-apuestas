from django.db import models


class BetStatus(models.TextChoices):
    ACCEPTED = 'accepted', 'Accepted'
    SETTLED_WON = 'settled_won', 'Settled won'
    SETTLED_LOST = 'settled_lost', 'Settled lost'
    CANCELLED = 'cancelled', 'Cancelled'


VALID_BET_TRANSITIONS = {
    BetStatus.ACCEPTED: {
        BetStatus.SETTLED_WON,
        BetStatus.SETTLED_LOST,
        BetStatus.CANCELLED,
    },
}


def can_transition(origin, target):
    return target in VALID_BET_TRANSITIONS.get(origin, set())
